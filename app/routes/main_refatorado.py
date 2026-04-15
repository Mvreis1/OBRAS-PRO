"""
Rotas principais do sistema - VERSÃO REFATORADA
Usando serviços para lógica de negócio
"""

from datetime import datetime

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.models import Empresa, Lancamento, Obra, db
from app.routes.auth import login_required
from app.services.audit_service import AuditService
from app.services.dashboard_service import DashboardService
from app.services.lancamento_service import LancamentoService
from app.services.obra_alerta_service import ObraAlertaService
from app.services.obra_service import ObraService
from app.utils.excel_export import ExcelExport
from app.utils.sanitize import sanitize_float, sanitize_int

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def index():
    return redirect(url_for('main.dashboard'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard usando DashboardService"""
    empresa_id = session.get('empresa_id')

    # Usar DashboardService para agregar dados
    dashboard_data = DashboardService.get_dashboard_resumo(empresa_id)

    # Gerar alertas
    obras = Obra.query.filter_by(empresa_id=empresa_id).limit(10).all()
    alertas = ObraAlertaService.gerar_alertas_obras(obras, empresa_id)

    return render_template(
        'main/dashboard.html',
        orcamento_total=sum(o.orcamento_previsto for o in obras),
        despesas_mes=dashboard_data['despesas_mes'],
        receitas_mes=dashboard_data['receitas_mes'],
        saldo_atual=dashboard_data['saldo_mes'],
        obras=obras,
        ultimos_lancamentos=Lancamento.query.filter_by(empresa_id=empresa_id)
        .order_by(Lancamento.data.desc())
        .limit(5)
        .all(),
        dados_grafico_mes=DashboardService.get_dashboard_chart_data(empresa_id, meses=6),
        dados_pizza=dashboard_data['despesas_por_categoria'],
        alertas=alertas,
        alertas_criticos=[a for a in alertas if a.get('tipo') == 'critico'],
        alertas_alertas=[a for a in alertas if a.get('tipo') == 'alerta'],
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
        per_page=per_page,
    )

    obras_list = paginacao.items
    alertas = ObraAlertaService.gerar_alertas_obras(obras_list, empresa_id)

    return render_template(
        'main/obras.html', obras=obras_list, paginacao=paginacao, alertas=alertas
    )


@main_bp.route('/obra/<int:obra_id>')
@login_required
def obra_detalhe(obra_id):
    empresa_id = session.get('empresa_id')

    # Usar ObraService para dados completos
    obra_data = DashboardService.get_obra_dashboard_data(obra_id, empresa_id)
    if not obra_data:
        from flask import abort

        return abort(404)

    lancamentos = (
        Lancamento.query.filter_by(obra_id=obra_id, empresa_id=empresa_id)
        .order_by(Lancamento.data.desc())
        .all()
    )

    return render_template(
        'main/obra_detalhe.html',
        obra=obra_data['obra'],
        lancamentos=lancamentos,
        total_despesas=obra_data['total_despesas'],
        total_receitas=obra_data['total_receitas'],
        categorias=obra_data['despesas_por_categoria'],
        dados_obra={
            'orcamento': obra_data['orcamento_previsto'],
            'gasto': obra_data['total_despesas'],
            'receita': obra_data['total_receitas'],
            'saldo': obra_data['saldo'],
            'percentual': obra_data['percentual_orcamento'],
            'percentual_receita': obra_data['percentual_receita'],
        },
    )


@main_bp.route('/obra/nova', methods=['GET', 'POST'])
@login_required
def nova_obra():
    empresa_id = session.get('empresa_id')
    empresa = db.session.get(Empresa, empresa_id)

    if not empresa:
        flash('Empresa não encontrada.', 'danger')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        # Preparar dados do form
        dados = {
            'nome': request.form.get('nome', '').strip(),
            'descricao': request.form.get('descricao'),
            'endereco': request.form.get('endereco'),
            'orcamento_previsto': sanitize_float(request.form.get('orcamento_previsto')),
            'data_inicio': request.form.get('data_inicio'),
            'data_fim_prevista': request.form.get('data_fim_prevista'),
            'status': request.form.get('status') or 'Planejamento',
            'progresso': sanitize_int(request.form.get('progresso'), min_val=0, max_val=100) or 0,
            'responsavel': request.form.get('responsavel'),
            'cliente': request.form.get('cliente'),
        }

        # Usar ObraService
        obra, erro = ObraService.criar_obra(empresa_id, dados)

        if erro:
            flash(erro, 'danger')
            return render_template('main/obra_form.html', obra=None)

        AuditService.log('Criar obra', 'Obra', obra.id, f'Nova obra: {obra.nome}')
        flash('Obra cadastrada com sucesso!', 'success')
        return redirect(url_for('main.obras'))

    return render_template('main/obra_form.html', obra=None)


@main_bp.route('/obra/<int:obra_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_obra(obra_id):
    empresa_id = session.get('empresa_id')

    if request.method == 'POST':
        dados = {
            'nome': request.form.get('nome'),
            'descricao': request.form.get('descricao'),
            'endereco': request.form.get('endereco'),
            'orcamento_previsto': sanitize_float(request.form.get('orcamento_previsto')),
            'data_inicio': request.form.get('data_inicio'),
            'data_fim_prevista': request.form.get('data_fim_prevista'),
            'status': request.form.get('status'),
            'progresso': sanitize_int(request.form.get('progresso'), min_val=0, max_val=100),
            'responsavel': request.form.get('responsavel'),
            'cliente': request.form.get('cliente'),
        }

        obra, erro = ObraService.editar_obra(obra_id, empresa_id, dados)

        if erro:
            flash(erro, 'danger')
            return redirect(url_for('main.editar_obra', obra_id=obra_id))

        flash('Obra atualizada com sucesso!', 'success')
        return redirect(url_for('main.obra_detalhe', obra_id=obra_id))

    obra = Obra.query.filter_by(id=obra_id, empresa_id=empresa_id).first_or_404()
    return render_template('main/obra_form.html', obra=obra)


@main_bp.route('/obra/<int:obra_id>/excluir', methods=['POST'])
@login_required
def excluir_obra(obra_id):
    empresa_id = session.get('empresa_id')

    _sucesso, erro = ObraService.excluir_obra(obra_id, empresa_id)

    if erro:
        flash(erro, 'danger')
    else:
        flash('Obra excluída com sucesso!', 'success')

    return redirect(url_for('main.obras'))


@main_bp.route('/lancamentos')
@login_required
def lancamentos():
    """Lista de lançamentos com filtros usando LancamentoService"""
    empresa_id = session.get('empresa_id')

    # Obter parâmetros de filtro
    filtros = {
        'obra_id': request.args.get('obra_id', ''),
        'tipo': request.args.get('tipo', ''),
        'categoria': request.args.get('categoria', ''),
        'data_inicio': request.args.get('data_inicio', ''),
        'data_fim': request.args.get('data_fim', ''),
        'busca': request.args.get('busca', ''),
    }

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # Usar LancamentoService para query filtrada
    from app.utils.paginacao import Paginacao

    query = LancamentoService.build_filtered_query(empresa_id, filtros)
    paginacao = Paginacao(query, page=page, per_page=per_page)

    obras = Obra.query.filter_by(empresa_id=empresa_id).all()

    return render_template(
        'main/lancamentos.html',
        lancamentos=paginacao.items,
        paginacao=paginacao,
        page_args={k: v for k, v in filtros.items() if v},
        obras=obras,
        obra_selecionada=filtros['obra_id'],
        tipo_selecionado=filtros['tipo'],
        categoria_selecionada=filtros['categoria'],
        data_inicio=filtros['data_inicio'],
        data_fim=filtros['data_fim'],
        busca=filtros['busca'],
    )


@main_bp.route('/lancamento/novo', methods=['GET', 'POST'])
@login_required
def novo_lancamento():
    empresa_id = session.get('empresa_id')

    if request.method == 'POST':
        dados = {
            'obra_id': sanitize_int(request.form.get('obra_id')),
            'descricao': request.form.get('descricao'),
            'categoria': request.form.get('categoria'),
            'tipo': request.form.get('tipo'),
            'valor': sanitize_float(request.form.get('valor')),
            'data': request.form.get('data'),
            'forma_pagamento': request.form.get('forma_pagamento'),
            'status_pagamento': request.form.get('status_pagamento'),
            'parcelas': sanitize_int(request.form.get('parcelas'), min_val=1),
            'observacoes': request.form.get('observacoes'),
            'documento': request.form.get('documento'),
        }

        lancamento, erro = LancamentoService.criar_lancamento(empresa_id, dados)

        if erro:
            flash(erro, 'danger')
            return render_template('main/lancamento_form.html', lancamento=None)

        AuditService.log(
            'Criar lançamento',
            'Lancamento',
            lancamento.id,
            f'{lancamento.tipo}: {lancamento.descricao} - R$ {lancamento.valor}',
        )
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
        dados = {
            'obra_id': sanitize_int(request.form.get('obra_id')),
            'descricao': request.form.get('descricao'),
            'categoria': request.form.get('categoria'),
            'tipo': request.form.get('tipo'),
            'valor': sanitize_float(request.form.get('valor')),
            'data': request.form.get('data'),
            'forma_pagamento': request.form.get('forma_pagamento'),
            'status_pagamento': request.form.get('status_pagamento'),
            'parcelas': sanitize_int(request.form.get('parcelas'), min_val=1),
            'observacoes': request.form.get('observacoes'),
            'documento': request.form.get('documento'),
        }

        _lanc_atual, erro = LancamentoService.editar_lancamento(lancamento_id, empresa_id, dados)

        if erro:
            flash(erro, 'danger')
            return redirect(url_for('main.editar_lancamento', lancamento_id=lancamento_id))

        flash('Lançamento atualizado com sucesso!', 'success')
        return redirect(url_for('main.lancamentos'))

    obras = Obra.query.filter_by(empresa_id=empresa_id).all()
    return render_template('main/lancamento_form.html', lancamento=lancamento, obras=obras)


@main_bp.route('/lancamento/<int:lancamento_id>/excluir', methods=['POST'])
@login_required
def excluir_lancamento(lancamento_id):
    empresa_id = session.get('empresa_id')

    _sucesso, erro = LancamentoService.excluir_lancamento(lancamento_id, empresa_id)

    if erro:
        flash(erro, 'danger')
    else:
        flash('Lançamento excluído com sucesso!', 'success')

    return redirect(url_for('main.lancamentos'))


@main_bp.route('/api/dashboard')
@login_required
def api_dashboard():
    """API para dados do dashboard usando DashboardService"""
    empresa_id = session.get('empresa_id')

    dashboard_data = DashboardService.get_dashboard_resumo(empresa_id)
    obras = Obra.query.filter_by(empresa_id=empresa_id).all()

    return jsonify(
        {
            'orcamento_total': sum(o.orcamento_previsto for o in obras),
            'despesas_mes': dashboard_data['despesas_mes'],
            'receitas_mes': dashboard_data['receitas_mes'],
            'saldo_atual': dashboard_data['saldo'],
            'qtd_obras': len(obras),
        }
    )


@main_bp.route('/api/obra/<int:obra_id>/dados')
@login_required
def api_obra_dados(obra_id):
    """API para dados de uma obra específica usando DashboardService"""
    empresa_id = session.get('empresa_id')

    obra_data = DashboardService.get_obra_dashboard_data(obra_id, empresa_id)
    if not obra_data:
        from flask import abort

        return abort(404)

    return jsonify(
        {
            'obra': obra_data['obra'].to_dict(),
            'total_despesas': obra_data['total_despesas'],
            'total_receitas': obra_data['total_receitas'],
            'saldo': obra_data['saldo'],
            'percentual_orcamento': obra_data['percentual_orcamento'],
            'categorias': obra_data['despesas_por_categoria'],
        }
    )


@main_bp.route('/obra/<int:obra_id>/exportar/pdf')
@login_required
def exportar_obra_pdf(obra_id):
    """Exportar dados da obra para PDF profissional"""
    from app.utils.pdf_export import exportar_obra_pdf as gerar_pdf

    empresa_id = session.get('empresa_id')
    obra = Obra.query.filter_by(id=obra_id, empresa_id=empresa_id).first_or_404()
    lancamentos = (
        Lancamento.query.filter_by(obra_id=obra_id, empresa_id=empresa_id)
        .order_by(Lancamento.data.desc())
        .all()
    )

    total_despesas = sum(l.valor for l in lancamentos if l.tipo == 'Despesa')
    total_receitas = sum(l.valor for l in lancamentos if l.tipo == 'Receita')
    saldo = total_receitas - total_despesas

    pdf_content = gerar_pdf(obra, lancamentos, total_despesas, total_receitas, saldo)

    response = make_response(pdf_content)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = (
        f'attachment; filename=obra_{obra.nome.replace(" ", "_")}.pdf'
    )

    return response


@main_bp.route('/obra/<int:obra_id>/exportar')
@login_required
def exportar_obra(obra_id):
    """Exportar dados da obra para Excel"""
    empresa_id = session.get('empresa_id')
    obra = Obra.query.filter_by(id=obra_id, empresa_id=empresa_id).first_or_404()
    lancamentos = (
        Lancamento.query.filter_by(obra_id=obra_id, empresa_id=empresa_id)
        .order_by(Lancamento.data.desc())
        .all()
    )

    total_despesas = sum(l.valor for l in lancamentos if l.tipo == 'Despesa')
    total_receitas = sum(l.valor for l in lancamentos if l.tipo == 'Receita')

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
        dados.append(
            [
                lanc.data,
                lanc.descricao,
                lanc.categoria,
                lanc.tipo,
                lanc.valor if lanc.tipo == 'Receita' else -lanc.valor,
                lanc.status_pagamento,
            ]
        )

    exporter.add_sheet('Lançamentos', cabecalhos, dados)
    exporter.add_summary(
        'Lançamentos',
        {
            'Total Receitas:': total_receitas,
            'Total Despesas:': total_despesas,
            'Saldo:': total_receitas - total_despesas,
        },
    )

    filename = f'obra_{obra.nome.replace(" ", "_")}_{datetime.now().strftime("%Y%m%d")}.xlsx'
    return exporter.to_response(filename)


@main_bp.route('/relatorios')
@login_required
def relatorios():
    """Relatórios avançados usando RelatorioService"""
    empresa_id = session.get('empresa_id')

    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    obra_id = request.args.get('obra_id')

    obras = Obra.query.filter_by(empresa_id=empresa_id).all()

    # Use service for general report
    from app.services.relatorio_service import RelatorioService

    relatorio = RelatorioService.get_relatorio_geral(empresa_id, data_inicio, data_fim, obra_id)
    lucro_obras = RelatorioService.calcular_lucro_por_obra(empresa_id, data_inicio, data_fim)
    evolucao_mensal = RelatorioService.calcular_evolucao_mensal(empresa_id, meses=12)
    orcamento_data = RelatorioService.calcular_orcamento_vs_realizado(
        empresa_id, data_inicio, data_fim
    )
    despesas_categoria = RelatorioService.calcular_despesas_por_categoria(
        empresa_id, data_inicio, data_fim
    )

    return render_template(
        'main/relatorios.html',
        relatorio=relatorio,
        lucro_obras=lucro_obras,
        evolucao_mensal=evolucao_mensal,
        orcamento_data=orcamento_data,
        despesas_categoria=despesas_categoria,
        obras=obras,
    )
