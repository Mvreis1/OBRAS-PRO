"""
Rotas de fornecedores
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime, date
from app.models import db, Empresa, Obra
from app.models.fornecedores import Fornecedor, CompraFornecedor
from app.routes.auth import login_required
from app.utils.sanitize import sanitize_float

fornecedores_bp = Blueprint('fornecedores', __name__)


@fornecedores_bp.route('/fornecedores')
@login_required
def fornecedores():
    """Lista fornecedores"""
    empresa_id = session.get('empresa_id')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    categoria = request.args.get('categoria')

    from app.utils.paginacao import Paginacao

    query = Fornecedor.query.filter_by(empresa_id=empresa_id, ativo=True)
    if categoria:
        query = query.filter_by(categoria=categoria)
    
    paginacao = Paginacao(query.order_by(Fornecedor.nome), page=page, per_page=per_page)

    categorias = db.session.query(
        Fornecedor.categoria,
        db.func.count(Fornecedor.id)
    ).filter(
        Fornecedor.empresa_id == empresa_id,
        Fornecedor.ativo == True  # noqa: E712
    ).group_by(Fornecedor.categoria).all()
    
    filter_args = {}
    if categoria: filter_args['categoria'] = categoria

    return render_template(
        'main/fornecedores.html',
        fornecedores=paginacao.items,
        paginacao=paginacao,
        page_args=filter_args,
        categorias=categorias,
        categoria=categoria
    )


@fornecedores_bp.route('/fornecedor/novo', methods=['GET', 'POST'])
@login_required
def novo_fornecedor():
    """Novo fornecedor"""
    empresa_id = session.get('empresa_id')
    
    if request.method == 'POST':
        fornecedor = Fornecedor(
            empresa_id=empresa_id,
            nome=request.form.get('nome'),
            razao_social=request.form.get('razao_social'),
            cnpj=request.form.get('cnpj'),
            cpf=request.form.get('cpf'),
            email=request.form.get('email'),
            telefone=request.form.get('telefone'),
            telefone_2=request.form.get('telefone_2'),
            endereco=request.form.get('endereco'),
            cidade=request.form.get('cidade'),
            estado=request.form.get('estado'),
            cep=request.form.get('cep'),
            contato=request.form.get('contato'),
            categoria=request.form.get('categoria'),
            observacoes=request.form.get('observacoes')
        )
        db.session.add(fornecedor)
        db.session.commit()
        
        flash('Fornecedor cadastrado!', 'success')
        return redirect(url_for('fornecedores.fornecedores'))
    
    return render_template('main/fornecedor_form.html', fornecedor=None)


@fornecedores_bp.route('/fornecedor/<int:fornecedor_id>')
@login_required
def fornecedor_detalhe(fornecedor_id):
    """Detalhes do fornecedor"""
    empresa_id = session.get('empresa_id')
    fornecedor = Fornecedor.query.filter_by(id=fornecedor_id, empresa_id=empresa_id).first_or_404()

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    from app.utils.paginacao import Paginacao
    paginacao = Paginacao(
        CompraFornecedor.query.filter_by(fornecedor_id=fornecedor_id).order_by(CompraFornecedor.data.desc()),
        page=page,
        per_page=per_page
    )

    compras = paginacao.items

    total_compras = db.session.query(
        db.func.sum(CompraFornecedor.valor)
    ).filter(
        CompraFornecedor.fornecedor_id == fornecedor_id
    ).scalar() or 0

    compras_ano = db.session.query(
        db.func.sum(CompraFornecedor.valor)
    ).filter(
        CompraFornecedor.fornecedor_id == fornecedor_id,
        CompraFornecedor.data >= date.today().replace(month=1, day=1)
    ).scalar() or 0

    return render_template(
        'main/fornecedor_detalhe.html',
        fornecedor=fornecedor,
        compras=compras,
        paginacao=paginacao,
        total_compras=total_compras,
        compras_ano=compras_ano
    )


@fornecedores_bp.route('/fornecedor/<int:fornecedor_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_fornecedor(fornecedor_id):
    """Editar fornecedor"""
    empresa_id = session.get('empresa_id')
    fornecedor = Fornecedor.query.filter_by(id=fornecedor_id, empresa_id=empresa_id).first_or_404()
    
    if request.method == 'POST':
        fornecedor.nome = request.form.get('nome')
        fornecedor.razao_social = request.form.get('razao_social')
        fornecedor.cnpj = request.form.get('cnpj')
        fornecedor.cpf = request.form.get('cpf')
        fornecedor.email = request.form.get('email')
        fornecedor.telefone = request.form.get('telefone')
        fornecedor.telefone_2 = request.form.get('telefone_2')
        fornecedor.endereco = request.form.get('endereco')
        fornecedor.cidade = request.form.get('cidade')
        fornecedor.estado = request.form.get('estado')
        fornecedor.cep = request.form.get('cep')
        fornecedor.contato = request.form.get('contato')
        fornecedor.categoria = request.form.get('categoria')
        fornecedor.observacoes = request.form.get('observacoes')
        
        db.session.commit()
        flash('Fornecedor atualizado!', 'success')
        return redirect(url_for('fornecedores.fornecedor_detalhe', fornecedor_id=fornecedor_id))
    
    return render_template('main/fornecedor_form.html', fornecedor=fornecedor)


@fornecedores_bp.route('/fornecedor/<int:fornecedor_id>/excluir', methods=['POST'])
@login_required
def excluir_fornecedor(fornecedor_id):
    """Excluir fornecedor (desativar)"""
    empresa_id = session.get('empresa_id')
    fornecedor = Fornecedor.query.filter_by(id=fornecedor_id, empresa_id=empresa_id).first_or_404()
    fornecedor.ativo = False
    db.session.commit()
    flash('Fornecedor desativado!', 'success')
    return redirect(url_for('fornecedores.fornecedores'))


@fornecedores_bp.route('/fornecedor/<int:fornecedor_id>/compra/nova', methods=['GET', 'POST'])
@login_required
def nova_compra(fornecedor_id):
    """Nova compra/fornecimento"""
    empresa_id = session.get('empresa_id')
    fornecedor = Fornecedor.query.filter_by(id=fornecedor_id, empresa_id=empresa_id).first_or_404()
    obras = Obra.query.filter_by(empresa_id=empresa_id).all()
    
    if request.method == 'POST':
        compra = CompraFornecedor(
            empresa_id=empresa_id,
            fornecedor_id=fornecedor_id,
            obra_id=request.form.get('obra_id') or None,
            descricao=request.form.get('descricao'),
            valor=sanitize_float(request.form.get('valor')),
            data=datetime.strptime(request.form.get('data'), '%Y-%m-%d').date() if request.form.get('data') else date.today(),
            status=request.form.get('status'),
            observacoes=request.form.get('observacoes')
        )
        db.session.add(compra)
        db.session.commit()
        
        flash('Compra registrada!', 'success')
        return redirect(url_for('fornecedores.fornecedor_detalhe', fornecedor_id=fornecedor_id))
    
    return render_template('main/compra_form.html', fornecedor=fornecedor, compra=None, obras=obras)


@fornecedores_bp.route('/fornecedor/<int:fornecedor_id>/compra/<int:compra_id>/pagar', methods=['POST'])
@login_required
def pagar_compra(fornecedor_id, compra_id):
    """Registrar pagamento"""
    empresa_id = session.get('empresa_id')
    compra = CompraFornecedor.query.filter_by(
        id=compra_id,
        fornecedor_id=fornecedor_id,
        empresa_id=empresa_id
    ).get_or_404()
    
    compra.status = 'Pago'
    db.session.commit()
    
    flash('Pagamento registrado!', 'success')
    return redirect(url_for('fornecedores.fornecedor_detalhe', fornecedor_id=fornecedor_id))


@fornecedores_bp.route('/api/fornecedores')
@login_required
def api_fornecedores():
    """API para listar fornecedores"""
    empresa_id = session.get('empresa_id')
    fornecedores = Fornecedor.query.filter_by(
        empresa_id=empresa_id,
        ativo=True
    ).order_by(Fornecedor.nome).all()
    
    return jsonify([f.to_dict() for f in fornecedores])


@fornecedores_bp.route('/api/fornecedor/<int:fornecedor_id>')
@login_required
def api_fornecedor(fornecedor_id):
    """API para dados do fornecedor"""
    empresa_id = session.get('empresa_id')
    fornecedor = Fornecedor.query.filter_by(
        id=fornecedor_id,
        empresa_id=empresa_id
    ).get_or_404()
    
    return jsonify(fornecedor.to_dict())