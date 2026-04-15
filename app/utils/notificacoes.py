"""
Helpers para notificações e alertas
"""

from datetime import date

from sqlalchemy import func

from app.models import Lancamento, Notificacao, db


def gerar_alertas(empresa_id):
    """Gera alertas para uma empresa - otimizado para evitar N+1"""

    # Buscar obras com seus totais em uma query agregada
    from sqlalchemy import case

    obras_data = (
        db.session.query(
            Lancamento.obra_id,
            func.sum(case((Lancamento.tipo == 'Despesa', Lancamento.valor), else_=0)).label(
                'despesas'
            ),
            func.sum(case((Lancamento.tipo == 'Receita', Lancamento.valor), else_=0)).label(
                'receitas'
            ),
        )
        .filter(Lancamento.empresa_id == empresa_id, Lancamento.obra_id.isnot(None))
        .group_by(Lancamento.obra_id)
        .all()
    )

    # Criar dicionário de totais por obra
    totais_obra = {
        od[0]: {'despesas': float(od[1] or 0), 'receitas': float(od[2] or 0)} for od in obras_data
    }

    # Buscar todas as obras da empresa
    from app.models import Obra

    obras = Obra.query.filter_by(empresa_id=empresa_id).all()

    hoje = date.today()

    for obra in obras:
        totais = totais_obra.get(obra.id, {'despesas': 0, 'receitas': 0})
        total_despesas = totais['despesas']

        # Verificar orçamento estourado
        if obra.orcamento_previsto > 0:
            percentual = (total_despesas / obra.orcamento_previsto) * 100

            if percentual >= 90:
                existing = Notificacao.query.filter_by(
                    empresa_id=empresa_id, obra_id=obra.id, tipo='orcamento_estourado'
                ).first()

                if not existing:
                    notif = Notificacao(
                        empresa_id=empresa_id,
                        obra_id=obra.id,
                        tipo='orcamento_estourado',
                        titulo=f'Orçamento estourado: {obra.nome}',
                        mensagem=f'A obra "{obra.nome}" atingiu {percentual:.0f}% do orçamento previsto.',
                    )
                    db.session.add(notif)

        # Verificar obra atrasada
        if obra.data_fim_prevista and obra.data_fim_prevista < hoje:
            if obra.status not in ['Concluída', 'Entregue']:
                existing = Notificacao.query.filter_by(
                    empresa_id=empresa_id, obra_id=obra.id, tipo='obra_atrasada'
                ).first()

                if not existing:
                    notif = Notificacao(
                        empresa_id=empresa_id,
                        obra_id=obra.id,
                        tipo='obra_atrasada',
                        titulo=f'Obra atrasada: {obra.nome}',
                        mensagem=f'A obra "{obra.nome}" está atrasada. Prazo: {obra.data_fim_prevista.strftime("%d/%m/%Y")}',
                    )
                    db.session.add(notif)

    # Verificar pagamentos atrasados
    lancamentos_pendentes = (
        Lancamento.query.filter_by(empresa_id=empresa_id, status_pagamento='Pendente')
        .filter(Lancamento.data < hoje)
        .all()
    )

    for lanc in lancamentos_pendentes:
        existing = Notificacao.query.filter_by(
            empresa_id=empresa_id, lancamento_id=lanc.id, tipo='pagamento_atrasado'
        ).first()

        if not existing:
            notif = Notificacao(
                empresa_id=empresa_id,
                obra_id=lanc.obra_id,
                lancamento_id=lanc.id,
                tipo='pagamento_atrasado',
                titulo=f'Pagamento atrasado: {lanc.descricao}',
                mensagem=f'O pagamento de R$ {lanc.valor:,.2f} para "{lanc.descricao}" está atrasado desde {lanc.data.strftime("%d/%m/%Y")}',
            )
            db.session.add(notif)

    db.session.commit()


def send_email(config, subject, body, to_email=None):
    """Helper genérico para enviar emails"""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    try:
        import ssl
    except ImportError:
        pass

    if not config.smtp_host or not (to_email or config.email_destino):
        return False

    destino = to_email or config.email_destino

    msg = MIMEMultipart()
    msg['From'] = config.smtp_user or destino
    msg['To'] = destino
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        import ssl as ssl_module

        port = config.smtp_port or 587
        host = config.smtp_host

        if port == 465:
            context = ssl_module.create_default_context()
            server = smtplib.SMTP_SSL(host, port, context=context)
        else:
            server = smtplib.SMTP(host, port)
            if config.smtp_usar_tls:
                server.starttls()

        if config.smtp_user and config.smtp_password:
            server.login(config.smtp_user, config.smtp_password)

        server.sendmail(config.smtp_user or destino, destino, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f'Erro ao enviar email: {e}')
        return False


def testar_email_config(config):
    """Testa configuração de email"""
    return send_email(config, 'Teste - OBRAS PRO', 'Email de teste enviado com sucesso!')


def enviar_alertas_email(empresa_id):
    """Envia alertas por email"""
    from app.models import ConfigEmail, Empresa

    config = ConfigEmail.query.filter_by(empresa_id=empresa_id, alertas_ativos=True).first()

    if not config or not config.smtp_host or not config.email_destino:
        return

    empresa = db.session.get(Empresa, empresa_id)
    if not empresa:
        return

    notifs = Notificacao.query.filter_by(empresa_id=empresa_id, enviada_email=False).limit(10).all()

    if not notifs:
        return

    corpo = 'Olá!\n\nVocê tem novos alertas do OBRAS PRO:\n\n'
    for n in notifs:
        corpo += f'• {n.titulo}\n  {n.mensagem}\n\n'

    if send_email(config, f'OBRAS PRO - Alertas ({len(notifs)})', corpo):
        for n in notifs:
            n.enviada_email = True
        config.ultimo_envio = db.func.now()
        db.session.commit()
