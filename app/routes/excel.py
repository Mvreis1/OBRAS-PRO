"""
Rotas de exportacao Excel para o sistema OBRAS PRO
"""
from flask import Blueprint, request, session
from datetime import datetime, date, timedelta
from app.routes.auth import login_required
from app.models import db, Obra, Lancamento
from app.constants import StatusObra
from app.utils.excel_export import ExcelExport

excel_bp = Blueprint('excel', __name__)


@excel_bp.route('/lancamentos/exportar/excel')
@login_required
def exportar_lancamentos_excel():
    """Exporta lancamentos para Excel"""
    from app.utils.rbac import require_permission, Modulos, Acoes
    
    # Verificar permissão
    from app.models import Usuario
    usuario = db.session.get(Usuario, session.get('usuario_id'))
    if not usuario or not usuario.has_permission(Modulos.LANCAMENTOS, Acoes.EXPORTAR):
        return "Acesso negado", 403
    
    empresa_id = session.get('empresa_id')
    obra_id = request.args.get('obra_id')
    tipo = request.args.get('tipo')
    categoria = request.args.get('categoria')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    query = Lancamento.query.filter_by(empresa_id=empresa_id)
    if obra_id:
        query = query.filter_by(obra_id=obra_id)
    if tipo:
        query = query.filter_by(tipo=tipo)
    if categoria:
        query = query.filter_by(categoria=categoria)
    if data_inicio:
        query = query.filter(Lancamento.data >= datetime.strptime(data_inicio, '%Y-%m-%d').date())
    if data_fim:
        query = query.filter(Lancamento.data <= datetime.strptime(data_fim, '%Y-%m-%d').date())
    
    lancamentos = query.order_by(Lancamento.data.desc()).all()
    
    cabecalhos = [
        ('Data', 'date'),
        ('Obra', 'text'),
        ('Descricao', 'text'),
        ('Categoria', 'text'),
        ('Tipo', 'text'),
        ('Valor (R$)', 'currency'),
        ('Forma Pagamento', 'text'),
        ('Status', 'text'),
        ('Documento', 'text'),
    ]
    
    dados = []
    for lanc in lancamentos:
        dados.append([
            lanc.data,
            lanc.obra.nome if lanc.obra else '-',
            lanc.descricao,
            lanc.categoria,
            lanc.tipo,
            lanc.valor if lanc.tipo == 'Receita' else -lanc.valor,
            lanc.forma_pagamento or '-',
            lanc.status_pagamento or '-',
            lanc.documento or '-',
        ])
    
    total_receitas = sum(l.valor for l in lancamentos if l.tipo == 'Receita')
    total_despesas = sum(l.valor for l in lancamentos if l.tipo == 'Despesa')
    
    exporter = ExcelExport()
    exporter.add_sheet('Lancamentos', cabecalhos, dados)
    exporter.add_summary('Lancamentos', {  # Corrigido: add_summary_row -> add_summary
        'Total Receitas:': total_receitas,
        'Total Despesas:': total_despesas,
        'Saldo:': total_receitas - total_despesas,
        'Qtd Lancamentos:': len(lancamentos),
    })
    
    filename = f'lancamentos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    return exporter.to_response(filename)


@excel_bp.route('/obras/exportar/excel')
@login_required
def exportar_obras_excel():
    """Exporta obras para Excel"""
    empresa_id = session.get('empresa_id')
    obras = Obra.query.filter_by(empresa_id=empresa_id).order_by(Obra.created_at.desc()).all()
    
    cabecalhos = [
        ('Obra', 'text'),
        ('Cliente', 'text'),
        ('Status', 'text'),
        ('Orcamento Previsto (R$)', 'currency'),
        ('Total Gasto (R$)', 'currency'),
        ('Saldo (R$)', 'currency'),
        ('% Utilizado', 'percent'),
        ('Progresso (%)', 'percent'),
        ('Data Inicio', 'date'),
        ('Previsao Fim', 'date'),
        ('Responsavel', 'text'),
    ]
    
    dados = []
    for obra in obras:
        total_gasto = sum(l.valor for l in obra.lancamentos if l.tipo == 'Despesa')
        total_receita = sum(l.valor for l in obra.lancamentos if l.tipo == 'Receita')
        pct_utilizado = (total_gasto / obra.orcamento_previsto) if obra.orcamento_previsto > 0 else 0
        
        dados.append([
            obra.nome,
            obra.cliente or '-',
            obra.status,
            obra.orcamento_previsto,
            -total_gasto,
            total_receita - total_gasto,
            pct_utilizado,
            obra.progresso,
            obra.data_inicio,
            obra.data_fim_prevista,
            obra.responsavel or '-',
        ])
    
    exporter = ExcelExport()
    exporter.add_sheet('Obras', cabecalhos, dados)
    
    total_geral = sum(o.orcamento_previsto for o in obras)
    exporter.add_summary('Obras', {
        'Total Obras:': len(obras),
        'Orcamento Total:': total_geral,

        'Em Execução:': sum(1 for o in obras if o.status == StatusObra.EM_EXECUCAO.value),
        'Concluídas:': sum(1 for o in obras if o.status == StatusObra.CONCLUIDA.value),
    })
    
    filename = f'obras_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    return exporter.to_response(filename)


@excel_bp.route('/relatorio-financeiro/exportar/excel')
@login_required
def exportar_relatorio_financeiro_excel():
    """Exporta relatorio financeiro completo para Excel (multi-sheet)"""
    empresa_id = session.get('empresa_id')
    obras = Obra.query.filter_by(empresa_id=empresa_id).all()
    
    # Sheet 1: Resumo Geral
    cabecalhos_resumo = [
        ('Obra', 'text'),
        ('Orcamento (R$)', 'currency'),
        ('Receitas (R$)', 'currency'),
        ('Despesas (R$)', 'currency'),
        ('Saldo (R$)', 'currency'),
        ('% Utilizado', 'percent'),
        ('Status', 'text'),
    ]
    
    dados_resumo = []
    total_orcamento = 0
    total_receitas = 0
    total_despesas = 0
    
    for obra in obras:
        receitas = sum(l.valor for l in obra.lancamentos if l.tipo == 'Receita')
        despesas = sum(l.valor for l in obra.lancamentos if l.tipo == 'Despesa')
        pct = (despesas / obra.orcamento_previsto) if obra.orcamento_previsto > 0 else 0
        
        dados_resumo.append([
            obra.nome,
            obra.orcamento_previsto,
            receitas,
            despesas,
            receitas - despesas,
            pct,
            obra.status,
        ])
        
        total_orcamento += obra.orcamento_previsto
        total_receitas += receitas
        total_despesas += despesas
    
    dados_resumo.append([
        'TOTAL GERAL',
        total_orcamento,
        total_receitas,
        total_despesas,
        total_receitas - total_despesas,
        (total_despesas / total_orcamento) if total_orcamento > 0 else 0,
        '-',
    ])
    
    exporter = ExcelExport()
    exporter.add_sheet('Resumo Financeiro', cabecalhos_resumo, dados_resumo)
    
    # Sheet 2: Fluxo de Caixa por Mes (12 meses)
    cabecalhos_fluxo = [
        ('Mes/Ano', 'text'),
        ('Receitas (R$)', 'currency'),
        ('Despesas (R$)', 'currency'),
        ('Saldo do Mes (R$)', 'currency'),
        ('Saldo Acumulado (R$)', 'currency'),
    ]
    
    dados_fluxo = []
    acumulado = 0
    
    for i in range(11, -1, -1):
        mes_ref = date.today().replace(day=1)
        for _ in range(i):
            if mes_ref.month == 1:
                mes_ref = mes_ref.replace(year=mes_ref.year - 1, month=12)
            else:
                mes_ref = mes_ref.replace(month=mes_ref.month - 1)
        mes_fim = (mes_ref.replace(day=28) + timedelta(days=4)).replace(day=1)
        
        lancs_mes = Lancamento.query.filter(
            Lancamento.empresa_id == empresa_id,
            Lancamento.data >= mes_ref,
            Lancamento.data < mes_fim
        ).all()
        
        receitas = sum(l.valor for l in lancs_mes if l.tipo == 'Receita')
        despesas = sum(l.valor for l in lancs_mes if l.tipo == 'Despesa')
        acumulado += receitas - despesas
        
        dados_fluxo.append([
            mes_ref.strftime('%m/%Y'),
            receitas,
            despesas,
            receitas - despesas,
            acumulado,
        ])
    
    exporter.add_sheet('Fluxo de Caixa (12m)', cabecalhos_fluxo, dados_fluxo)
    
    # Sheet 3: Despesas por Categoria
    cabecalhos_cat = [
        ('Categoria', 'text'),
        ('Total Despesas (R$)', 'currency'),
        ('% do Total', 'percent'),
        ('Qtd Lancamentos', 'number'),
    ]
    
    dados_cat = []
    categorias = db.session.query(
        Lancamento.categoria,
        db.func.sum(Lancamento.valor).label('total'),
        db.func.count(Lancamento.id).label('qtd')
    ).filter(
        Lancamento.empresa_id == empresa_id,
        Lancamento.tipo == 'Despesa'
    ).group_by(Lancamento.categoria).order_by(db.desc('total')).all()
    
    for cat in categorias:
        dados_cat.append([
            cat[0],
            cat[1],
            (cat[1] / total_despesas) if total_despesas > 0 else 0,
            cat[2],
        ])
    
    exporter.add_sheet('Despesas por Categoria', cabecalhos_cat, dados_cat)
    exporter.add_summary('Despesas por Categoria', {
        'Total Despesas:': total_despesas,
        'Total Receitas:': total_receitas,
        'Saldo Geral:': total_receitas - total_despesas,
        'Margem (%):': ((total_receitas - total_despesas) / total_receitas * 100) if total_receitas > 0 else 0,
    })
    
    filename = f'relatorio_financeiro_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    return exporter.to_response(filename)
