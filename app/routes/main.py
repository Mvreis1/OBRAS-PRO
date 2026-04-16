"""
Rotas principais do sistema
"""

from datetime import date, datetime, timedelta

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

from app.constants import StatusObra
from app.models import ConfigIA, Empresa, Lancamento, LogAtividade, Obra, db
from app.routes.auth import login_required
from app.services.audit_service import AuditService
from app.services.obra_alerta_service import ObraAlertaService
from app.services.relatorio_service import RelatorioService
from app.services.storage_service import StorageService
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
    """Dashboard simplificado para evitar timeouts no Render"""
    empresa_id = session.get('empresa_id')

    # Queries otimizadas com limites
    obras = Obra.query.filter_by(empresa_id=empresa_id).limit(10).all()

    orcamento_total = sum(o.orcamento_previsto for o in obras)

    # Usar SQL direto para agregacoes - mais rapido
    from sqlalchemy import case, func

    result = (
        db.session.query(
            func.sum(case((Lancamento.tipo == 'Despesa', Lancamento.valor), else_=0)).label(
                'despesas'
            ),
            func.sum(case((Lancamento.tipo == 'Receita', Lancamento.valor), else_=0)).label(
                'receitas'
            ),
        )
        .filter(Lancamento.empresa_id == empresa_id)
        .first()
    )

    despesas_mes = result.despesas or 0
    receitas_mes = result.receitas or 0
    saldo_atual = receitas_mes - despesas_mes

    ultimos_lancamentos = (
        Lancamento.query.filter_by(empresa_id=empresa_id)
        .order_by(Lancamento.data.desc())
        .limit(5)
        .all()
    )

    # Dados simplificados para grafico
    dados_grafico_mes = [
        {'mes': 'Jan/2026', 'despesa': despesas_mes * 0.8, 'receita': receitas_mes * 0.9}
    ]
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
        alertas_alertas=alertas_alertas,
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

    # Use service to generate alerts
    alertas = ObraAlertaService.gerar_alertas_obras(obras_list, empresa_id)

    return render_template(
        'main/obras.html', obras=obras_list, paginacao=paginacao, alertas=alertas
    )


@main_bp.route('/obra/<int:obra_id>')
@login_required
def obra_detalhe(obra_id):
    empresa_id = session.get('empresa_id')
    obra = Obra.query.filter_by(id=obra_id, empresa_id=empresa_id).first_or_404()
    lancamentos = (
        Lancamento.query.filter_by(obra_id=obra_id, empresa_id=empresa_id)
        .order_by(Lancamento.data.desc())
        .all()
    )

    total_despesas = sum(l.valor for l in lancamentos if l.tipo == 'Despesa')
    total_receitas = sum(l.valor for l in lancamentos if l.tipo == 'Receita')

    categorias = (
        db.session.query(Lancamento.categoria, db.func.sum(Lancamento.valor))
        .filter(Lancamento.obra_id == obra_id, Lancamento.tipo == 'Despesa')
        .group_by(Lancamento.categoria)
        .all()
    )

    dados_obra = {
        'orcamento': obra.orcamento_previsto,
        'gasto': total_despesas,
        'receita': total_receitas,
        'saldo': total_receitas - total_despesas,
        'percentual': (total_despesas / obra.orcamento_previsto * 100)
        if obra.orcamento_previsto > 0
        else 0,
        'percentual_receita': (total_receitas / obra.orcamento_previsto * 100)
        if obra.orcamento_previsto > 0
        else 0,
    }

    return render_template(
        'main/obra_detalhe.html',
        obra=obra,
        lancamentos=lancamentos,
        total_despesas=total_despesas,
        total_receitas=total_receitas,
        categorias=categorias,
        dados_obra=dados_obra,
    )


@main_bp.route('/obra/nova', methods=['GET', 'POST'])
@login_required
def nova_obra():
    empresa_id = session.get('empresa_id')
    empresa = db.session.get(Empresa, empresa_id)

    if not empresa:
        flash('Empresa não encontrada.', 'danger')
        return redirect(url_for('auth.login'))

    if empresa.obras.count() >= empresa.max_obras:
        flash('Limite de obras atingido. Faça upgrade do plano.', 'warning')
        return redirect(url_for('main.obras'))

    if request.method == 'POST':
        try:
            nome = request.form.get('nome', '').strip()
            if not nome:
                flash('Nome da obra é obrigatório.', 'danger')
                return render_template('main/obra_form.html', obra=None)

            obra = Obra(
                empresa_id=empresa_id,
                nome=nome,
                descricao=request.form.get('descricao'),
                endereco=request.form.get('endereco'),
                orcamento_previsto=sanitize_float(request.form.get('orcamento_previsto')),
                data_inicio=datetime.strptime(request.form.get('data_inicio'), '%Y-%m-%d').date()
                if request.form.get('data_inicio')
                else None,
                data_fim_prevista=datetime.strptime(
                    request.form.get('data_fim_prevista'), '%Y-%m-%d'
                ).date()
                if request.form.get('data_fim_prevista')
                else None,
                status=request.form.get('status') or 'Planejamento',
                progresso=sanitize_int(request.form.get('progresso'), min_val=0, max_val=100) or 0,
                responsavel=request.form.get('responsavel'),
                cliente=request.form.get('cliente'),
            )
            db.session.add(obra)
            db.session.commit()
            AuditService.log('Criar obra', 'Obra', obra.id, f'Nova obra: {obra.nome}')
            flash('Obra cadastrada com sucesso!', 'success')
            return redirect(url_for('main.obras'))
        except Exception as e:
            db.session.rollback()
            import traceback

            current_app.logger.error(f'Erro ao criar obra: {e}')
            current_app.logger.error(traceback.format_exc())
            flash(f'Erro ao cadastrar obra: {e!s}', 'danger')
            return render_template('main/obra_form.html', obra=None)

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
        obra.data_inicio = (
            datetime.strptime(request.form.get('data_inicio'), '%Y-%m-%d').date()
            if request.form.get('data_inicio')
            else None
        )
        obra.data_fim_prevista = (
            datetime.strptime(request.form.get('data_fim_prevista'), '%Y-%m-%d').date()
            if request.form.get('data_fim_prevista')
            else None
        )
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

    if 'imagem' not in request.files:
        flash('Nenhum arquivo enviado.', 'warning')
        return redirect(url_for('main.obra_detalhe', obra_id=obra_id))

    arquivo = request.files['imagem']

    if arquivo.filename == '':
        flash('Nenhum arquivo selecionado.', 'warning')
        return redirect(url_for('main.obra_detalhe', obra_id=obra_id))

    if arquivo:
        # Verificar extensão permitida
        extensoes_permitidas = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        extensao = arquivo.filename.rsplit('.', 1)[1].lower() if '.' in arquivo.filename else ''

        if extensao not in extensoes_permitidas:
            flash('Formato de arquivo não suportado. Use: PNG, JPG, JPEG, GIF ou WEBP.', 'danger')
            return redirect(url_for('main.obra_detalhe', obra_id=obra_id))

        try:
            # Remover imagem anterior se existir
            if obra.imagem:
                if obra.imagem.startswith('http'):
                    # Imagem no S3
                    StorageService.delete_file(obra.imagem)
                else:
                    # Imagem local
                    StorageService.delete_local_file(obra.imagem)

            # Tentar upload para S3 primeiro
            if current_app.config.get('USE_S3_STORAGE'):
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                filename = f'obra_{obra_id}_{timestamp}.{extensao}'
                
                url_imagem, error = StorageService.upload_file(
                    arquivo,
                    folder='obras',
                    filename=filename
                )

                if error:
                    flash(f'Erro no upload: {error}', 'danger')
                    return redirect(url_for('main.obra_detalhe', obra_id=obra_id))

                # Salvar URL no banco
                obra.imagem = url_imagem
                db.session.commit()
                flash('Imagem atualizada com sucesso (cloud storage)!', 'success')
            else:
                # Fallback: storage local
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                filename = f'obra_{obra_id}_{timestamp}.{extensao}'
                
                relative_url, error = StorageService.save_local_file(
                    arquivo,
                    folder='obras',
                    filename=filename
                )

                if error:
                    flash(f'Erro ao salvar: {error}', 'danger')
                    return redirect(url_for('main.obra_detalhe', obra_id=obra_id))

                obra.imagem = relative_url
                db.session.commit()
                flash('Imagem atualizada com sucesso!', 'success')

        except Exception as e:
            flash(f'Erro ao processar imagem: {e!s}', 'danger')
            current_app.logger.error(f'Erro no upload: {e}')

    return redirect(url_for('main.obra_detalhe', obra_id=obra_id))


@main_bp.route('/obra/<int:obra_id>/remover-imagem', methods=['POST'])
@login_required
def remover_imagem_obra(obra_id):
    """Remove a imagem da obra"""
    empresa_id = session.get('empresa_id')
    obra = Obra.query.filter_by(id=obra_id, empresa_id=empresa_id).first_or_404()

    if obra.imagem:
        try:
            if obra.imagem.startswith('http'):
                # Imagem no S3
                success, error = StorageService.delete_file(obra.imagem)
                if not success:
                    current_app.logger.warning(f'Erro ao remover S3: {error}')
            else:
                # Imagem local
                success, error = StorageService.delete_local_file(obra.imagem)
                if not success:
                    current_app.logger.warning(f'Erro ao remover local: {error}')
        except Exception as e:
            current_app.logger.warning(f'Erro ao remover imagem: {e}')

        # Remover referência do banco
        obra.imagem = None
        db.session.commit()
        flash('Imagem removida com sucesso!', 'success')
    else:
        flash('Nenhuma imagem para remover.', 'warning')

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
    """Lista de lancamentos com filtros e paginação"""
    empresa_id = session.get('empresa_id')

    # Obter parâmetros de filtro
    obra_id = request.args.get('obra_id', '')
    tipo = request.args.get('tipo', '')
    categoria = request.args.get('categoria', '')
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')
    busca = request.args.get('busca', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # Construir query base
    query = Lancamento.query.filter_by(empresa_id=empresa_id)

    # Aplicar filtros
    if obra_id:
        query = query.filter_by(obra_id=int(obra_id))
    if tipo:
        query = query.filter_by(tipo=tipo)
    if categoria:
        query = query.filter_by(categoria=categoria)
    if data_inicio:
        query = query.filter(Lancamento.data >= datetime.strptime(data_inicio, '%Y-%m-%d').date())
    if data_fim:
        query = query.filter(Lancamento.data <= datetime.strptime(data_fim, '%Y-%m-%d').date())
    if busca:
        query = query.filter(Lancamento.descricao.ilike(f'%{busca}%'))

    # Ordenar
    query = query.order_by(Lancamento.data.desc())

    # Aplicar paginação
    from app.utils.paginacao import Paginacao

    paginacao = Paginacao(query, page=page, per_page=per_page)
    obras = Obra.query.filter_by(empresa_id=empresa_id).all()

    # Construir page_args para paginação
    page_args = {}
    if obra_id:
        page_args['obra_id'] = obra_id
    if tipo:
        page_args['tipo'] = tipo
    if categoria:
        page_args['categoria'] = categoria
    if data_inicio:
        page_args['data_inicio'] = data_inicio
    if data_fim:
        page_args['data_fim'] = data_fim
    if busca:
        page_args['busca'] = busca

    return render_template(
        'main/lancamentos.html',
        lancamentos=paginacao.items,
        paginacao=paginacao,
        page_args=page_args,
        obras=obras,
        obra_selecionada=obra_id,
        tipo_selecionado=tipo,
        categoria_selecionada=categoria,
        data_inicio=data_inicio,
        data_fim=data_fim,
        busca=busca,
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
            documento=request.form.get('documento'),
        )
        db.session.add(lancamento)
        db.session.commit()
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
        Lancamento.data < proximo_mes,
    ).all()

    despesas_mes = sum(l.valor for l in lancamentos_mes if l.tipo == 'Despesa')
    receitas_mes = sum(l.valor for l in lancamentos_mes if l.tipo == 'Receita')

    todas_despesas = (
        db.session.query(db.func.sum(Lancamento.valor))
        .filter(Lancamento.empresa_id == empresa_id, Lancamento.tipo == 'Despesa')
        .scalar()
        or 0
    )

    todas_receitas = (
        db.session.query(db.func.sum(Lancamento.valor))
        .filter(Lancamento.empresa_id == empresa_id, Lancamento.tipo == 'Receita')
        .scalar()
        or 0
    )

    return jsonify(
        {
            'orcamento_total': sum(o.orcamento_previsto for o in obras),
            'despesas_mes': despesas_mes,
            'receitas_mes': receitas_mes,
            'saldo_atual': todas_receitas - todas_despesas,
            'qtd_obras': len(obras),
        }
    )


@main_bp.route('/api/obra/<int:obra_id>/dados')
@login_required
def api_obra_dados(obra_id):
    """API para dados de uma obra específica"""
    empresa_id = session.get('empresa_id')
    obra = Obra.query.filter_by(id=obra_id, empresa_id=empresa_id).first_or_404()
    lancamentos = Lancamento.query.filter_by(obra_id=obra_id, empresa_id=empresa_id).all()

    total_despesas = sum(l.valor for l in lancamentos if l.tipo == 'Despesa')
    total_receitas = sum(l.valor for l in lancamentos if l.tipo == 'Receita')

    categorias = (
        db.session.query(Lancamento.categoria, db.func.sum(Lancamento.valor))
        .filter(Lancamento.obra_id == obra_id, Lancamento.tipo == 'Despesa')
        .group_by(Lancamento.categoria)
        .all()
    )

    return jsonify(
        {
            'obra': obra.to_dict(),
            'total_despesas': total_despesas,
            'total_receitas': total_receitas,
            'saldo': total_receitas - total_despesas,
            'percentual_orcamento': (total_despesas / obra.orcamento_previsto * 100)
            if obra.orcamento_previsto > 0
            else 0,
            'categorias': [{'categoria': c[0], 'valor': c[1]} for c in categorias],
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
    """Exportar dados da obra para Excel usando utils existente"""
    from datetime import datetime

    empresa_id = session.get('empresa_id')
    obra = Obra.query.filter_by(id=obra_id, empresa_id=empresa_id).first_or_404()
    lancamentos = (
        Lancamento.query.filter_by(obra_id=obra_id, empresa_id=empresa_id)
        .order_by(Lancamento.data.desc())
        .all()
    )

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

    # Adicionar resumo
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
    relatorio = RelatorioService.get_relatorio_geral(empresa_id, data_inicio, data_fim, obra_id)

    # Use service for profitability per project
    lucro_obras = RelatorioService.calcular_lucro_por_obra(empresa_id, data_inicio, data_fim)

    # Use service for monthly evolution
    evolucao_mensal = RelatorioService.calcular_evolucao_mensal(empresa_id, meses=12)

    # Use service for budget vs actual
    orcamento_data = RelatorioService.calcular_orcamento_vs_realizado(
        empresa_id, data_inicio, data_fim
    )

    # Use service for category breakdown
    categorias = RelatorioService.calcular_despesas_por_categoria(empresa_id, data_inicio, data_fim)

    # Use service for statistics
    estatisticas = RelatorioService.get_estatisticas_gerais(empresa_id)

    return render_template(
        'main/relatorios.html',
        data_inicio=data_inicio,
        data_fim=data_fim,
        obra_id=obra_id,
        obras=obras,
        total_receitas=relatorio['total_receitas'],
        total_despesas=relatorio['total_despesas'],
        lucro_prejuizo=relatorio['lucro_prejuizo'],
        margem_geral=relatorio['margem_geral'],
        lucro_obras=lucro_obras,
        evolucao_mensal=evolucao_mensal,
        orcamento_obras=orcamento_data['orcamento_obras'],
        total_orcamento=orcamento_data['total_orcamento'],
        total_realizado=orcamento_data['total_realizado'],
        diferenca_total=orcamento_data['diferenca_total'],
        percentual_geral=orcamento_data['percentual_geral'],
        categorias=categorias,
        grafico_labels=orcamento_data['grafico_labels'],
        grafico_orcamento=orcamento_data['grafico_orcamento'],
        grafico_realizado=orcamento_data['grafico_realizado'],
        obras_ativas=estatisticas['obras_ativas'],
        lancamentos_count=estatisticas['lancamentos_count'],
        categorias_count=estatisticas['categorias_count'],
        obras_por_status=estatisticas['obras_por_status'],
        top_despesas=estatisticas['top_despesas'],
    )


@main_bp.route('/relatorios/exportar/pdf')
@login_required
def exportar_relatorio_pdf():
    """Exportar relatório para PDF"""
    from datetime import datetime

    from app.utils.pdf_export import exportar_relatorio_pdf as gerar_pdf

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

    pdf_content = gerar_pdf(
        lancamentos, total_receitas, total_despesas, lucro_prejuizo, obras, data_inicio, data_fim
    )

    response = make_response(pdf_content)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = (
        f'attachment; filename=relatorio_{datetime.now().strftime("%Y%m%d")}.pdf'
    )

    return response


@main_bp.route('/logs')
@login_required
def ver_logs():
    """Visualizar logs de auditoria"""
    from flask import render_template

    logs = LogAtividade.query.order_by(LogAtividade.created_at.desc()).limit(100).all()
    return render_template('main/logs.html', logs=logs)


@main_bp.route('/configuracoes/ia', methods=['GET', 'POST'])
@login_required
def config_ia():
    """Configurações de IA - API Keys"""
    empresa_id = session.get('empresa_id')

    # Buscar configuração existente ou criar nova
    config = ConfigIA.query.filter_by(empresa_id=empresa_id).first()

    if request.method == 'POST':
        try:
            if not config:
                config = ConfigIA(empresa_id=empresa_id)
                db.session.add(config)

            # Atualizar campos
            config.openai_api_key = request.form.get('openai_api_key', '').strip() or None
            config.openai_model = request.form.get('openai_model', 'gpt-3.5-turbo')
            config.gemini_api_key = request.form.get('gemini_api_key', '').strip() or None
            config.claude_api_key = request.form.get('claude_api_key', '').strip() or None
            config.ia_padrao = request.form.get('ia_padrao', 'local')

            db.session.commit()
            flash('Configurações de IA salvas com sucesso!', 'success')
            return redirect(url_for('main.config_ia'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao salvar configurações: {e!s}', 'danger')

    return render_template('main/config_ia.html', config=config)
