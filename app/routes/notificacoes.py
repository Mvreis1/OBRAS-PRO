"""
Rotas de notificações e alertas
"""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from app.models import ConfigEmail, Notificacao, db
from app.routes.auth import login_required

# Importar helpers otimizados
from app.utils.notificacoes import gerar_alertas as _gerar_alertas

notif_bp = Blueprint('notificacoes', __name__)


@notif_bp.route('/notificacoes')
@login_required
def notificacoes():
    """Lista notificações"""
    empresa_id = session.get('empresa_id')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    from app.utils.paginacao import Paginacao

    paginacao = Paginacao(
        Notificacao.query.filter_by(empresa_id=empresa_id).order_by(Notificacao.created_at.desc()),
        page=page,
        per_page=per_page,
    )

    nao_lidas = Notificacao.query.filter_by(empresa_id=empresa_id, lida=False).count()

    return render_template(
        'main/notificacoes.html',
        notificacoes=paginacao.items,
        paginacao=paginacao,
        nao_lidas=nao_lidas,
    )


@notif_bp.route('/notificacoes/marcar-lida/<int:notif_id>')
@login_required
def marcar_lida(notif_id):
    """Marca notificação como lida"""
    empresa_id = session.get('empresa_id')
    notif = Notificacao.query.filter_by(id=notif_id, empresa_id=empresa_id).first_or_404()
    notif.lida = True
    db.session.commit()
    return redirect(url_for('notificacoes.notificacoes'))


@notif_bp.route('/notificacoes/marcar-todas-lida')
@login_required
def marcar_todas_lida():
    """Marca todas como lidas"""
    empresa_id = session.get('empresa_id')
    Notificacao.query.filter_by(empresa_id=empresa_id, lida=False).update({'lida': True})
    db.session.commit()
    flash('Todas as notificações marcadas como lidas!', 'success')
    return redirect(url_for('notificacoes.notificacoes'))


@notif_bp.route('/config/email', methods=['GET', 'POST'])
@login_required
def config_email():
    """Configurações de email para alertas"""
    empresa_id = session.get('empresa_id')

    config = ConfigEmail.query.filter_by(empresa_id=empresa_id).first()

    if request.method == 'POST':
        if not config:
            config = ConfigEmail(empresa_id=empresa_id)
            db.session.add(config)

        config.smtp_host = request.form.get('smtp_host')
        config.smtp_port = int(request.form.get('smtp_port') or 587)
        config.smtp_user = request.form.get('smtp_user')
        config.smtp_password = request.form.get('smtp_password')
        config.smtp_usar_tls = request.form.get('smtp_usar_tls') == 'on'
        config.email_destino = request.form.get('email_destino')
        config.alertas_ativos = request.form.get('alertas_ativos') == 'on'

        db.session.commit()

        if request.form.get('testar_email'):
            from app.utils.notificacoes import send_email

            if send_email(config, 'Teste - OBRAS PRO', 'Email de teste enviado com sucesso!'):
                flash('Email de teste enviado com sucesso!', 'success')
            else:
                flash('Erro ao enviar email de teste. Verifique as configurações.', 'danger')

        flash('Configurações salvas!', 'success')
        return redirect(url_for('notificacoes.config_email'))

    return render_template('main/config_email.html', config=config)


@notif_bp.route('/api/notificacoes/nao-lidas')
@login_required
def api_nao_lidas():
    """API para verificar notificações não lidas"""
    empresa_id = session.get('empresa_id')
    count = Notificacao.query.filter_by(empresa_id=empresa_id, lida=False).count()
    return jsonify({'count': count})


@notif_bp.route('/api/alertas/gerar')
@login_required
def api_gerar_alertas():
    """API para gerar alertas manualmente"""
    empresa_id = session.get('empresa_id')
    _gerar_alertas(empresa_id)
    return jsonify({'success': True})
