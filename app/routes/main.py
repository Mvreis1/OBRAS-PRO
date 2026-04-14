"""
Rotas principais do sistema
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, make_response
from datetime import datetime, date, timedelta
from sqlalchemy.orm import joinedload
from app.models import db, Empresa, Obra, Lancamento, Categoria, LogAtividade
from app.constants import StatusObra
from app.routes.auth import login_required
from app.utils.excel_export import ExcelExport
from app.utils import get_empresa_id
from app.utils.sanitize import sanitize_int, sanitize_float

main_bp = Blueprint('main', __name__)


def log_atividade(acao, entidade=None, entidade_id=None, detalhes=None):
    """Registra atividade no log de auditoria"""
    try:
        from flask import request
        empresa_id = session.get('empresa_id')
        log = LogAtividade(
            usuario_id=session.get('usuario_id'),
            empresa_id=empresa_id,
            acao=acao,
            entidade=entidade,
            entidade_id=entidade_id,
            detalhes=detalhes,
            ip=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()

        # Invalida cache ao alterar dados
        try:
            from flask_caching import cache
            cache.delete('dashboard_data')
        except:
            pass
    except:
        pass


@main_bp.route('/')
@login_required
def index():
    return redirect(url_for('main.dashboard'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard simplificado para evitar timeouts no Render"""
    empresa_id = session.get('empresa_id')
    
    # Queries otimizadas com limites
    obras = Obra.query.filter_by(empresa_id=empresa_id).limit(10).all()
    
    orcamento_total = sum(o.orcamento_previsto for o in obras)
    
    # Usar SQL direto para agregacoes - mais rapido
    from sqlalchemy import func, case
    
    result = db.session.query(
        func.sum(case((Lancamento.tipo == 'Despesa', Lancamento.valor), else_=0)).label('despesas'),
        func.sum(case((Lancamento.tipo == 'Receita', Lancamento.valor), else_=0)).label('receitas')
    ).filter(Lancamento.empresa_id == empresa_id).first()
    
    despesas_mes = result.despesas or 0
    receitas_mes = result.receitas or 0
    saldo_atual = receitas_mes - despesas_mes
    
    ultimos_lancamentos = Lancamento.query.filter_by(empresa_id=empresa_id).order_by(Lancamento.data.desc()).limit(5).all()
    
    # Dados simplificados para grafico
    dados_grafico_mes = [{'mes': 'Jan/2026', 'despesa': despesas_mes * 0.8, 'receita': receitas_mes * 0.9}]
    dados_pizza = [{'categoria': 'Geral', 'valor': despesas_mes}]
    
    alertas = []
    alertas_criticos = []
    alertas_alertas = []

    return render_template(
        'main/dashboard.html',
        orcamento_total=orcamento_total,
        despesas_mes=despesas_mes,
        receitas_mes=receitas_mes,
        saldo_atual=saldo_atual,
        obras=obras,
        ultimos_lancamentos=ultimos_lancamentos,
        dados_grafico_mes=dados_grafico_mes,
        dados_pizza=dados_pizza,
        alertas=alertas,
        alertas_criticos=alertas_criticos,
        alertas_alertas=alertas_alertas
    )


@main_bp.route('/obras')
@login_required
def obras():
    empresa_id = session.get('empresa_id')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    from app.utils.paginacao import Paginacao
    paginacao = Paginacao(
        Obra.query.filter_by(empresa_id=empresa_id).order_by(Obra.created_at.desc()),
        page=page,
        per_page=per_page
    )
    
    obras_list = paginacao.items

    alertas = []
    for obra in obras_list:
        lancamentos_obra = Lancamento.query.filter_by(obra_id=obra.id, empresa_id=empresa_id).all()
        total_despesas_obra = sum(l.valor for l in lancamentos_obra if l.tipo == 'Despesa')
        total_receitas_obra = sum(l.valor for l in lancamentos_obra if l.tipo == 'Receita')

        percentual_gasto = (total_despesas_obra / obra.orcamento_previsto * 100) if obra.orcamento_previsto > 0 else 0

        nivel = None
        if percentual_gasto >= 90:
            nivel = 'critico'
            icon = 'bi bi-exclamation-octagon-fill'
            cor = '#ef4444'
            msg = f'Estouro! {percentual_gasto|int}%'
        elif percentual_gasto >= 70:
            nivel = 'alerta'
            icon = 'bi bi-exclamation-triangle-fill'
            cor = '#f59e0b'
            msg = f'Atenção! {percentual_gasto|int}%'

        if obra.data_fim_prevista and obra.data_fim_prevista < date.today() and obra.status != 'Concluída':
            nivel = 'critico'
            icon = 'bi bi-exclamation-octagon-fill'
            cor = '#ef4444'
            msg = 'Atrasada'

        if obra.status == 'Paralisada':
            nivel = 'alerta'
            icon = 'bi bi-pause-circle-fill'
            cor = '#f59e0b'
            msg = 'Paralisada'

        if nivel:
            alertas.append({
                'obra_id': obra.id,
                'obra_nome': obra.nome,
                'nivel': nivel,
                'icon': icon,
                'cor': cor,
                'mensagem': msg,
                'percentual': percentual_gasto
            })

    return render_template('main/obras.html', obras=obras_list, paginacao=paginacao, alertas=alertas)


@main_bp.route('/obra/<int:obra_id>')
@login_required
def obra_detalhe(obra_id):
    empresa_id = session.get('empresa_id')
    obra = Obra.query.filter_by(id=obra_id, empresa_id=empresa_id).first_or_404()
    lancamentos = Lancamento.query.filter_by(obra_id=obra_id, empresa_id=empresa_id).order_by(Lancamento.data.desc()).all()
    
    total_despesas = sum(l.valor for l in lancamentos if l.tipo == 'Despesa')
    total_receitas = sum(l.valor for l in lancamentos if l.tipo == 'Receita')
    
    categorias = db.session.query(
        Lancamento.categoria,
        db.func.sum(Lancamento.valor)
    ).filter(
        Lancamento.obra_id == obra_id,
        Lancamento.tipo == 'Despesa'
    ).group_by(Lancamento.categoria).all()
    
    dados_obra = {
        'orcamento': obra.orcamento_previsto,
        'gasto': total_despesas,
        'receita': total_receitas,
        'saldo': total_receitas - total_despesas,
        'percentual': (total_despesas / obra.orcamento_previsto * 100) if obra.orcamento_previsto > 0 else 0,
        'percentual_receita': (total_receitas / obra.orcamento_previsto * 100) if obra.orcamento_previsto > 0 else 0
    }
    
    return render_template(
        'main/obra_detalhe.html',
        obra=obra,
        lancamentos=lancamentos,
        total_despesas=total_despesas,
        total_receitas=total_receitas,
        categorias=categorias,
        dados_obra=dados_obra
    )


@main_bp.route('/obra/nova', methods=['GET', 'POST'])
@login_required
def nova_obra():
    empresa_id = session.get('empresa_id')
    empresa = db.session.get(Empresa, empresa_id)
    
    if empresa.obras.count() >= empresa.max_obras:
        flash('Limite de obras atingido. Faça upgrade do plano.', 'warning')
        return redirect(url_for('main.obras'))
    
    if request.method == 'POST':
        obra = Obra(
            empresa_id=empresa_id,
            nome=request.form.get('nome'),
            descricao=request.form.get('descricao'),
            endereco=request.form.get('endereco'),
            orcamento_previsto=sanitize_float(request.form.get('orcamento_previsto')),
            data_inicio=datetime.strptime(request.form.get('data_inicio'), '%Y-%m-%d').date() if request.form.get('data_inicio') else None,
            data_fim_prevista=datetime.strptime(request.form.get('data_fim_prevista'), '%Y-%m-%d').date() if request.form.get('data_fim_prevista') else None,
            status=request.form.get('status'),
            progresso=sanitize_int(request.form.get('progresso'), min_val=0, max_val=100),
            responsavel=request.form.get('responsavel'),
            cliente=request.form.get('cliente')
        )
        db.session.add(obra)
        db.session.commit()
        log_atividade('Criar obra', 'Obra', obra.id, f'Nova obra: {obra.nome}')
        flash('Obra cadastrada com sucesso!', 'success')
        return redirect(url_for('main.obras'))
    
    return render_template('main/obra_form.html', obra=None)


@main_bp.route('/obra/<int:obra_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_obra(obra_id):
    empresa_id = session.get('empresa_id')
    obra = Obra.query.filter_by(id=obra_id, empresa_id=empresa_id).first_or_404()
    
    if request.method == 'POST':
        obra.nome = request.form.get('nome')
        obra.descricao = request.form.get('descricao')
        obra.endereco = request.form.get('endereco')
        obra.orcamento_previsto = sanitize_float(request.form.get('orcamento_previsto'))
        obra.data_inicio = datetime.strptime(request.form.get('data_inicio'), '%Y-%m-%d').date() if request.form.get('data_inicio') else None
        obra.data_fim_prevista = datetime.strptime(request.form.get('data_fim_prevista'), '%Y-%m-%d').date() if request.form.get('data_fim_prevista') else None
        obra.status = request.form.get('status')
        obra.progresso = sanitize_int(request.form.get('progresso'), min_val=0, max_val=100)
        obra.responsavel = request.form.get('responsavel')
        obra.cliente = request.form.get('cliente')
        
        db.session.commit()
        flash('Obra atualizada com sucesso!', 'success')
        return redirect(url_for('main.obra_detalhe', obra_id=obra.id))
    
    return render_template('main/obra_form.html', obra=obra)


@main_bp.route('/obra/<int:obra_id>/upload-imagem', methods=['POST'])
@login_required
def upload_imagem_obra(obra_id):
    empresa_id = session.get('empresa_id')
    obra = Obra.query.filter_by(id=obra_id, empresa_id=empresa_id).first_or_404()
    
    if 'imagem' in request.files:
        arquivo = request.files['imagem']
        if arquivo.filename:
            obra.imagem = f"/uploads/{arquivo.filename}"
            db.session.commit()
    
    return redirect(url_for('main.obra_detalhe', obra_id=obra_id))


@main_bp.route('/obra/<int:obra_id>/excluir', methods=['POST'])
@login_required
def excluir_obra(obra_id):
    empresa_id = session.get('empresa_id')
    obra = Obra.query.filter_by(id=obra_id, empresa_id=empresa_id).first_or_404()
    db.session.delete(obra)
    db.session.commit()
    flash('Obra excluída com sucesso!', 'success')
    return redirect(url_for('main.obras'))


@main_bp.route('/lancamentos')
@login_required
def lancamentos():
    """Lista de lancamentos - simplificado para evitar timeouts"""
    empresa_id = session.get('empresa_id')
    
    # Limitar a 50 lancamentos mais recentes
    lancamentos = Lancamento.query.filter_by(empresa_id=empresa_id).order_by(Lancamento.data.desc()).limit(50).all()
    obras = Obra.query.filter_by(empresa_id=empresa_id).all()

    return render_template(
        'main/lancamentos.html',
        lancamentos=lancamentos,
        paginacao=None,
        page_args={},
        obras=obras,
        obra_selecionada=None,
        tipo_selecionado=None,
        categoria_selecionada=None,
        data_inicio=None,
        data_fim=None
    )


@main_bp.route('/lancamento/novo', methods=['GET', 'POST'])
@login_required
def novo_lancamento():
    empresa_id = session.get('empresa_id')
    
    if request.method == 'POST':
        lancamento = Lancamento(
            empresa_id=empresa_id,
            obra_id=sanitize_int(request.form.get('obra_id')),
            descricao=request.form.get('descricao'),
            categoria=request.form.get('categoria'),
            tipo=request.form.get('tipo'),
            valor=sanitize_float(request.form.get('valor')),
            data=datetime.strptime(request.form.get('data'), '%Y-%m-%d').date(),
            forma_pagamento=request.form.get('forma_pagamento'),
            status_pagamento=request.form.get('status_pagamento'),
            parcelas=sanitize_int(request.form.get('parcelas'), min_val=1),
            observacoes=request.form.get('observacoes'),
            documento=request.form.get('documento')
        )
        db.session.add(lancamento)
        db.session.commit()
        log_atividade('Criar lançamento', 'Lancamento', lancamento.id, f'{lancamento.tipo}: {lancamento.descricao} - R$ {lancamento.valor}')
        flash('Lançamento cadastrado com sucesso!', 'success')
        return redirect(url_for('main.lancamentos'))
    
    obras = Obra.query.filter_by(empresa_id=empresa_id).all()
    return render_template('main/lancamento_form.html', lancamento=None, obras=obras)


@main_bp.route('/lancamento/<int:lancamento_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_lancamento(lancamento_id):
    empresa_id = session.get('empresa_id')
    lancamento = Lancamento.query.filter_by(id=lancamento_id, empresa_id=empresa_id).first_or_404()
    
    if request.method == 'POST':
        lancamento.obra_id = sanitize_int(request.form.get('obra_id'))
        lancamento.descricao = request.form.get('descricao')
        lancamento.categoria = request.form.get('categoria')
        lancamento.tipo = request.form.get('tipo')
        lancamento.valor = sanitize_float(request.form.get('valor'))
        lancamento.data = datetime.strptime(request.form.get('data'), '%Y-%m-%d').date()
        lancamento.forma_pagamento = request.form.get('forma_pagamento')
        lancamento.status_pagamento = request.form.get('status_pagamento')
        lancamento.parcelas = sanitize_int(request.form.get('parcelas'), min_val=1)
        lancamento.observacoes = request.form.get('observacoes')
        lancamento.documento = request.form.get('documento')
        
        db.session.commit()
        flash('Lançamento atualizado com sucesso!', 'success')
        return redirect(url_for('main.lancamentos'))
    
    obras = Obra.query.filter_by(empresa_id=empresa_id).all()
    return render_template('main/lancamento_form.html', lancamento=lancamento, obras=obras)


@main_bp.route('/lancamento/<int:lancamento_id>/excluir', methods=['POST'])
@login_required
def excluir_lancamento(lancamento_id):
    empresa_id = session.get('empresa_id')
    lancamento = Lancamento.query.filter_by(id=lancamento_id, empresa_id=empresa_id).first_or_404()
    db.session.delete(lancamento)
    db.session.commit()
    flash('Lançamento excluído com sucesso!', 'success')
    return redirect(url_for('main.lancamentos'))


@main_bp.route('/api/dashboard')
@login_required
def api_dashboard():
    """API para dados do dashboard"""
    empresa_id = session.get('empresa_id')
    obras = Obra.query.filter_by(empresa_id=empresa_id).all()

    mes_atual = date.today().replace(day=1)
    proximo_mes = mes_atual + timedelta(days=32)
    proximo_mes = proximo_mes.replace(day=1)

    lancamentos_mes = Lancamento.query.filter(
        Lancamento.empresa_id == empresa_id,
        Lancamento.data >= mes_atual,
        Lancamento.data < proximo_mes
    ).all()

    despesas_mes = sum(l.valor for l in lancamentos_mes if l.tipo == 'Despesa')
    receitas_mes = sum(l.valor for l in lancamentos_mes if l.tipo == 'Receita')

    todas_despesas = db.session.query(db.func.sum(Lancamento.valor)).filter(
        Lancamento.empresa_id == empresa_id,
        Lancamento.tipo == 'Despesa'
    ).scalar() or 0

    todas_receitas = db.session.query(db.func.sum(Lancamento.valor)).filter(
        Lancamento.empresa_id == empresa_id,
        Lancamento.tipo == 'Receita'
    ).scalar() or 0

    return jsonify({
        'orcamento_total': sum(o.orcamento_previsto for o in obras),
        'despesas_mes': despesas_mes,
        'receitas_mes': receitas_mes,
        'saldo_atual': todas_receitas - todas_despesas,
        'qtd_obras': len(obras)
    })


@main_bp.route('/api/obra/<int:obra_id>/dados')
@login_required
def api_obra_dados(obra_id):
    """API para dados de uma obra específica"""
    empresa_id = session.get('empresa_id')
    obra = Obra.query.filter_by(id=obra_id, empresa_id=empresa_id).first_or_404()
    lancamentos = Lancamento.query.filter_by(obra_id=obra_id, empresa_id=empresa_id).all()
    
    total_despesas = sum(l.valor for l in lancamentos if l.tipo == 'Despesa')
    total_receitas = sum(l.valor for l in lancamentos if l.tipo == 'Receita')
    
    categorias = db.session.query(
        Lancamento.categoria,
        db.func.sum(Lancamento.valor)
    ).filter(
        Lancamento.obra_id == obra_id,
        Lancamento.tipo == 'Despesa'
    ).group_by(Lancamento.categoria).all()
    
    return jsonify({
        'obra': obra.to_dict(),
        'total_despesas': total_despesas,
        'total_receitas': total_receitas,
        'saldo': total_receitas - total_despesas,
        'percentual_orcamento': (total_despesas / obra.orcamento_previsto * 100) if obra.orcamento_previsto > 0 else 0,
        'categorias': [{'categoria': c[0], 'valor': c[1]} for c in categorias]
    })


@main_bp.route('/obra/<int:obra_id>/exportar/pdf')
@login_required
def exportar_obra_pdf(obra_id):
    """Exportar dados da obra para PDF profissional"""
    from flask import make_response
    from app.utils.pdf_export import exportar_obra_pdf as gerar_pdf
    
    empresa_id = session.get('empresa_id')
    obra = Obra.query.filter_by(id=obra_id, empresa_id=empresa_id).first_or_404()
    lancamentos = Lancamento.query.filter_by(obra_id=obra_id, empresa_id=empresa_id).order_by(Lancamento.data.desc()).all()
    
    total_despesas = sum(l.valor for l in lancamentos if l.tipo == 'Despesa')
    total_receitas = sum(l.valor for l in lancamentos if l.tipo == 'Receita')
    saldo = total_receitas - total_despesas
    
    pdf_content = gerar_pdf(obra, lancamentos, total_despesas, total_receitas, saldo)
    
    response = make_response(pdf_content)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=obra_{obra.nome.replace(" ", "_")}.pdf'
    
    return response


@main_bp.route('/obra/<int:obra_id>/exportar')
@login_required
def exportar_obra(obra_id):
    """Exportar dados da obra para Excel usando utils existente"""
    from flask import make_response
    from datetime import datetime
    from app.utils.excel_export import ExcelExport
    
    empresa_id = session.get('empresa_id')
    obra = Obra.query.filter_by(id=obra_id, empresa_id=empresa_id).first_or_404()
    lancamentos = Lancamento.query.filter_by(obra_id=obra_id, empresa_id=empresa_id).order_by(Lancamento.data.desc()).all()
    
    total_despesas = sum(l.valor for l in lancamentos if l.tipo == 'Despesa')
    total_receitas = sum(l.valor for l in lancamentos if l.tipo == 'Receita')
    
    # Usar ExcelExport existente
    exporter = ExcelExport()
    
    # Sheet 1: Dados da Obra
    dados_obra = [
        ['Nome:', obra.nome],
        ['Cliente:', obra.cliente or '-'],
        ['Endereço:', obra.endereco or '-'],
        ['Status:', obra.status],
        ['Orçamento:', obra.orcamento_previsto],
        ['Progresso:', obra.progresso],
    ]
    exporter.add_sheet('Dados', [('Campo', 'text'), ('Valor', 'text')], dados_obra)
    
    # Sheet 2: Lançamentos
    cabecalhos = [
        ('Data', 'date'),
        ('Descrição', 'text'),
        ('Categoria', 'text'),
        ('Tipo', 'text'),
        ('Valor', 'currency'),
        ('Status', 'text'),
    ]
    dados = []
    for lanc in lancamentos:
        dados.append([
            lanc.data,
            lanc.descricao,
            lanc.categoria,
            lanc.tipo,
            lanc.valor if lanc.tipo == 'Receita' else -lanc.valor,
            lanc.status_pagamento
        ])
    
    exporter.add_sheet('Lançamentos', cabecalhos, dados)
    
    # Adicionar resumo
    exporter.add_summary('Lançamentos', {
        'Total Receitas:': total_receitas,
        'Total Despesas:': total_despesas,
        'Saldo:': total_receitas - total_despesas,
    })
    
    filename = f"obra_{obra.nome.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return exporter.to_response(filename)


@main_bp.route('/relatorios')
@login_required
def relatorios():
    """Relatórios avançados"""
    empresa_id = session.get('empresa_id')
    
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    obra_id = request.args.get('obra_id')
    
    obras = Obra.query.filter_by(empresa_id=empresa_id).all()
    
    query = Lancamento.query.filter_by(empresa_id=empresa_id)
    query_obra = None
    
    if obra_id:
        query = query.filter_by(obra_id=int(obra_id))
        query_obra = query.filter_by(obra_id=int(obra_id))
    
    if data_inicio:
        query = query.filter(Lancamento.data >= datetime.strptime(data_inicio, '%Y-%m-%d').date())
        if not obra_id:
            query_obra = query
        else:
            query_obra = Lancamento.query.filter(
                Lancamento.empresa_id == empresa_id,
                Lancamento.obra_id == int(obra_id),
                Lancamento.data >= datetime.strptime(data_inicio, '%Y-%m-%d').date()
            )
    
    if data_fim:
        query = query.filter(Lancamento.data <= datetime.strptime(data_fim, '%Y-%m-%d').date())
        if not obra_id:
            query_obra = query
        else:
            query_obra = query_obra.filter(
                Lancamento.data <= datetime.strptime(data_fim, '%Y-%m-%d').date()
            )
    
    lancamentos = query.all()
    total_receitas = sum(l.valor for l in lancamentos if l.tipo == 'Receita')
    total_despesas = sum(l.valor for l in lancamentos if l.tipo == 'Despesa')
    lucro_prejuizo = total_receitas - total_despesas
    
    if total_receitas > 0:
        margem_geral = (lucro_prejuizo / total_receitas) * 100
    else:
        margem_geral = None
    
    lucro_obras = []
    for obra in obras:
        lancs_obra = Lancamento.query.filter(
            Lancamento.obra_id == obra.id,
            Lancamento.empresa_id == empresa_id
        ).all()
        
        if data_inicio:
            lancs_obra = [l for l in lancs_obra if l.data >= datetime.strptime(data_inicio, '%Y-%m-%d').date()]
        if data_fim:
            lancs_obra = [l for l in lancs_obra if l.data <= datetime.strptime(data_fim, '%Y-%m-%d').date()]
        
        receita = sum(l.valor for l in lancs_obra if l.tipo == 'Receita')
        despesa = sum(l.valor for l in lancs_obra if l.tipo == 'Despesa')
        saldo = receita - despesa
        
        if receita > 0:
            margem = (saldo / receita) * 100
        else:
            margem = None
        
        lucro_obras.append({
            'obra': obra,
            'receita': receita,
            'despesa': despesa,
            'saldo': saldo,
            'margem': margem
        })
    
    lucro_obras = [l for l in lucro_obras if l['receita'] > 0 or l['despesa'] > 0]
    
    evolucao_mensal = []
    for i in range(11, -1, -1):
        mes = (date.today().replace(day=1) - timedelta(days=i*30)).replace(day=1)
        mes_fim = (mes + timedelta(days=32)).replace(day=1)
        
        lancs_mes = Lancamento.query.filter(
            Lancamento.empresa_id == empresa_id,
            Lancamento.data >= mes,
            Lancamento.data < mes_fim
        ).all()
        
        receita = sum(l.valor for l in lancs_mes if l.tipo == 'Receita')
        despesa = sum(l.valor for l in lancs_mes if l.tipo == 'Despesa')
        
        nome_mes = mes.strftime('%b/%Y')
        evolucao_mensal.append({
            'mes': nome_mes,
            'receita': receita,
            'despesa': despesa,
            'saldo': receita - despesa
        })
    
    orcamento_obras = []
    total_orcamento = 0
    total_realizado = 0
    grafico_labels = []
    grafico_orcamento = []
    grafico_realizado = []
    
    for obra in obras:
        lancs = Lancamento.query.filter(
            Lancamento.obra_id == obra.id,
            Lancamento.empresa_id == empresa_id,
            Lancamento.tipo == 'Despesa'
        ).all()
        
        if data_inicio:
            lancs = [l for l in lancs if l.data >= datetime.strptime(data_inicio, '%Y-%m-%d').date()]
        if data_fim:
            lancs = [l for l in lancs if l.data <= datetime.strptime(data_fim, '%Y-%m-%d').date()]
        
        realizado = sum(l.valor for l in lancs)
        orcamento = obra.orcamento_previsto
        diferenca = orcamento - realizado
        
        if orcamento > 0:
            percentual = (realizado / orcamento) * 100
        else:
            percentual = 0
        
        if orcamento > 0 or realizado > 0:
            orcamento_obras.append({
                'obra': obra,
                'orcamento': orcamento,
                'realizado': realizado,
                'diferenca': diferenca,
                'percentual': percentual
            })
            grafico_labels.append(obra.nome[:15])
            grafico_orcamento.append(orcamento)
            grafico_realizado.append(realizado)
        
        total_orcamento += orcamento
        total_realizado += realizado
    
    diferenca_total = total_orcamento - total_realizado
    percentual_geral = (total_realizado / total_orcamento * 100) if total_orcamento > 0 else 0
    
    categorias = db.session.query(
        Lancamento.categoria,
        db.func.sum(Lancamento.valor)
    ).filter(
        Lancamento.empresa_id == empresa_id,
        Lancamento.tipo == 'Despesa'
    ).group_by(Lancamento.categoria).all()
    
    if total_realizado > 0:
        categorias = [{'categoria': c[0], 'valor': c[1], 'percentual': (c[1]/total_realizado)*100} for c in categorias]
    else:
        categorias = []
    
    obras_ativas = Obra.query.filter_by(empresa_id=empresa_id, status=StatusObra.EM_EXECUCAO.value).count()
    lancamentos_count = Lancamento.query.filter_by(empresa_id=empresa_id).count()
    categorias_count = len(set(Lancamento.query.filter_by(empresa_id=empresa_id).with_entities(Lancamento.categoria).all()))
    
    obras_por_status = db.session.query(
        Obra.status,
        db.func.count(Obra.id)
    ).filter(
        Obra.empresa_id == empresa_id
    ).group_by(Obra.status).all()
    
    top_despesas = Lancamento.query.filter_by(
        empresa_id=empresa_id,
        tipo='Despesa'
    ).order_by(Lancamento.valor.desc()).limit(5).all()
    
    return render_template(
        'main/relatorios.html',
        data_inicio=data_inicio,
        data_fim=data_fim,
        obra_id=obra_id,
        obras=obras,
        total_receitas=total_receitas,
        total_despesas=total_despesas,
        lucro_prejuizo=lucro_prejuizo,
        margem_geral=margem_geral,
        lucro_obras=lucro_obras,
        evolucao_mensal=evolucao_mensal,
        orcamento_obras=orcamento_obras,
        total_orcamento=total_orcamento,
        total_realizado=total_realizado,
        diferenca_total=diferenca_total,
        percentual_geral=percentual_geral,
        categorias=categorias,
        grafico_labels=grafico_labels,
        grafico_orcamento=grafico_orcamento,
        grafico_realizado=grafico_realizado,
        obras_ativas=obras_ativas,
        lancamentos_count=lancamentos_count,
        categorias_count=categorias_count,
        obras_por_status=obras_por_status,
        top_despesas=top_despesas
    )


@main_bp.route('/relatorios/exportar/pdf')
@login_required
def exportar_relatorio_pdf():
    """Exportar relatório para PDF"""
    from flask import make_response
    from app.utils.pdf_export import exportar_relatorio_pdf as gerar_pdf
    from datetime import datetime
    
    empresa_id = session.get('empresa_id')
    
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    obra_id = request.args.get('obra_id')
    
    query = Lancamento.query.filter_by(empresa_id=empresa_id)
    
    if obra_id:
        query = query.filter_by(obra_id=int(obra_id))
    
    if data_inicio:
        query = query.filter(Lancamento.data >= datetime.strptime(data_inicio, '%Y-%m-%d').date())
    if data_fim:
        query = query.filter(Lancamento.data <= datetime.strptime(data_fim, '%Y-%m-%d').date())
    
    lancamentos = query.all()
    total_receitas = sum(l.valor for l in lancamentos if l.tipo == 'Receita')
    total_despesas = sum(l.valor for l in lancamentos if l.tipo == 'Despesa')
    lucro_prejuizo = total_receitas - total_despesas
    
    obras = Obra.query.filter_by(empresa_id=empresa_id).all()
    
    pdf_content = gerar_pdf(lancamentos, total_receitas, total_despesas, lucro_prejuizo, obras, data_inicio, data_fim)
    
    response = make_response(pdf_content)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=relatorio_{datetime.now().strftime("%Y%m%d")}.pdf'
    
    return response


@main_bp.route('/logs')
@login_required
def ver_logs():
    """Visualizar logs de auditoria"""
    from flask import render_template
    logs = LogAtividade.query.order_by(LogAtividade.created_at.desc()).limit(100).all()
    return render_template('main/logs.html', logs=logs)


