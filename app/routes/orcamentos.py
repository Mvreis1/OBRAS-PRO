"""
Rotas de orçamentos
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime, date
from app.models import db, Empresa, ItemOrcamento
from app.models.orcamentos import Orcamento
from app.routes.auth import login_required
from app.utils.sanitize import sanitize_int, sanitize_float

orcamentos_bp = Blueprint('orcamentos', __name__)


@orcamentos_bp.route('/orcamentos')
@login_required
def orcamentos():
    """Lista orçamentos"""
    empresa_id = session.get('empresa_id')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status_filter = request.args.get('status')

    from app.utils.paginacao import Paginacao
    
    query = Orcamento.query.filter_by(empresa_id=empresa_id).order_by(Orcamento.created_at.desc())
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    paginacao = Paginacao(query, page=page, per_page=per_page)
    
    filter_args = {}
    if status_filter: filter_args['status'] = status_filter

    return render_template('main/orcamentos.html', orcamentos=paginacao.items, paginacao=paginacao, page_args=filter_args, status_filter=status_filter)


@orcamentos_bp.route('/orcamento/novo', methods=['GET', 'POST'])
@login_required
def novo_orcamento():
    """Novo orçamento"""
    empresa_id = session.get('empresa_id')
    
    if request.method == 'POST':
        orcamento = Orcamento(
            empresa_id=empresa_id,
            cliente=request.form.get('cliente'),
            cliente_email=request.form.get('cliente_email'),
            cliente_telefone=request.form.get('cliente_telefone'),
            cliente_endereco=request.form.get('cliente_endereco'),
            titulo=request.form.get('titulo'),
            descricao=request.form.get('descricao'),
            valor_materiais=sanitize_float(request.form.get('valor_materiais')),
            valor_mao_obra=sanitize_float(request.form.get('valor_mao_obra')),
            valor_equipamentos=sanitize_float(request.form.get('valor_equipamentos')),
            valor_outros=sanitize_float(request.form.get('valor_outros')),
            desconto=sanitize_float(request.form.get('desconto')),
            prazo_execucao=sanitize_int(request.form.get('prazo_execucao')) or None,
            validade=sanitize_int(request.form.get('validade'), default=30),
            status=request.form.get('status'),
            forma_pagamento=request.form.get('forma_pagamento'),
            observacoes=request.form.get('observacoes')
        )
        db.session.add(orcamento)
        db.session.commit()
        
        itens_json = request.form.get('itens_json')
        if itens_json:
            import json
            try:
                itens = json.loads(itens_json)
                for item in itens:
                    novo_item = ItemOrcamento(
                        orcamento_id=orcamento.id,
                        categoria=item.get('categoria'),
                        descricao=item.get('descricao'),
                        unidade=item.get('unidade', 'un'),
                        quantidade=float(item.get('quantidade', 1)),
                        valor_unitario=float(item.get('valor_unitario', 0))
                    )
                    db.session.add(novo_item)
                db.session.commit()
            except:
                pass
        
        flash('Orçamento criado!', 'success')
        log_atividade('Criar orçamento', 'Orcamento', orcamento.id, orcamento.titulo)
        return redirect(url_for('orcamentos.orcamentos'))
    
    return render_template('main/orcamento_form.html', orcamento=None)


@orcamentos_bp.route('/orcamento/<int:orcamento_id>')
@login_required
def orcamento_detalhe(orcamento_id):
    """Detalhes do orçamento"""
    empresa_id = session.get('empresa_id')
    orcamento = Orcamento.query.filter_by(id=orcamento_id, empresa_id=empresa_id).first_or_404()
    
    if not orcamento.visualizado:
        orcamento.visualizado = True
        db.session.commit()
    
    return render_template('main/orcamento_detalhe.html', orcamento=orcamento)


@orcamentos_bp.route('/orcamento/<int:orcamento_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_orcamento(orcamento_id):
    """Editar orçamento"""
    empresa_id = session.get('empresa_id')
    orcamento = Orcamento.query.filter_by(id=orcamento_id, empresa_id=empresa_id).first_or_404()
    
    if request.method == 'POST':
        orcamento.cliente = request.form.get('cliente')
        orcamento.cliente_email = request.form.get('cliente_email')
        orcamento.cliente_telefone = request.form.get('cliente_telefone')
        orcamento.cliente_endereco = request.form.get('cliente_endereco')
        orcamento.titulo = request.form.get('titulo')
        orcamento.descricao = request.form.get('descricao')
        orcamento.valor_materiais = sanitize_float(request.form.get('valor_materiais'))
        orcamento.valor_mao_obra = sanitize_float(request.form.get('valor_mao_obra'))
        orcamento.valor_equipamentos = sanitize_float(request.form.get('valor_equipamentos'))
        orcamento.valor_outros = sanitize_float(request.form.get('valor_outros'))
        orcamento.desconto = sanitize_float(request.form.get('desconto'))
        orcamento.prazo_execucao = sanitize_int(request.form.get('prazo_execucao')) or None
        orcamento.validade = sanitize_int(request.form.get('validade'), default=30)
        orcamento.status = request.form.get('status')
        orcamento.forma_pagamento = request.form.get('forma_pagamento')
        orcamento.observacoes = request.form.get('observacoes')
        
        db.session.commit()
        flash('Orçamento atualizado!', 'success')
        return redirect(url_for('orcamentos.orcamento_detalhe', orcamento_id=orcamento_id))
    
    return render_template('main/orcamento_form.html', orcamento=orcamento)


@orcamentos_bp.route('/orcamento/<int:orcamento_id>/excluir', methods=['POST'])
@login_required
def excluir_orcamento(orcamento_id):
    """Excluir orçamento"""
    empresa_id = session.get('empresa_id')
    orcamento = Orcamento.query.filter_by(id=orcamento_id, empresa_id=empresa_id).first_or_404()
    db.session.delete(orcamento)
    db.session.commit()
    flash('Orçamento excluído!', 'success')
    return redirect(url_for('orcamentos.orcamentos'))


@orcamentos_bp.route('/orcamento/<int:orcamento_id>/duplicar')
@login_required
def duplicar_orcamento(orcamento_id):
    """Duplicar orçamento"""
    empresa_id = session.get('empresa_id')
    original = Orcamento.query.filter_by(id=orcamento_id, empresa_id=empresa_id).first_or_404()
    
    novo = Orcamento(
        empresa_id=empresa_id,
        cliente=original.cliente,
        cliente_email=original.cliente_email,
        cliente_telefone=original.cliente_telefone,
        cliente_endereco=original.cliente_endereco,
        titulo=f"{original.titulo} (Cópia)",
        descricao=original.descricao,
        valor_materiais=original.valor_materiais,
        valor_mao_obra=original.valor_mao_obra,
        valor_equipamentos=original.valor_equipamentos,
        valor_outros=original.valor_outros,
        desconto=original.desconto,
        prazo_execucao=original.prazo_execucao,
        validade=original.validade,
        status='Rascunho',
        forma_pagamento=original.forma_pagamento,
        observacoes=original.observacoes
    )
    db.session.add(novo)
    db.session.commit()
    
    for item in original.itens:
        novo_item = ItemOrcamento(
            orcamento_id=novo.id,
            categoria=item.categoria,
            descricao=item.descricao,
            unidade=item.unidade,
            quantidade=item.quantidade,
            valor_unitario=item.valor_unitario
        )
        db.session.add(novo_item)
    db.session.commit()
    
    flash('Orçamento duplicado!', 'success')
    return redirect(url_for('orcamentos.editar_orcamento', orcamento_id=novo.id))


@orcamentos_bp.route('/orcamento/<int:orcamento_id>/enviar', methods=['GET', 'POST'])
@login_required
def enviar_orcamento(orcamento_id):
    """Enviar orçamento por email"""
    empresa_id = session.get('empresa_id')
    orcamento = Orcamento.query.filter_by(id=orcamento_id, empresa_id=empresa_id).first_or_404()
    
    if request.method == 'POST':
        email_destino = request.form.get('email')
        
        if not email_destino:
            flash('Informe o email de destino', 'danger')
            return redirect(url_for('orcamentos.enviar_orcamento', orcamento_id=orcamento_id))
        
        orcamento.enviado = True
        orcamento.data_envio = date.today()
        db.session.commit()
        
        flash(f'Orçamento enviado para {email_destino}!', 'success')
        return redirect(url_for('orcamentos.orcamento_detalhe', orcamento_id=orcamento_id))
    
    return render_template('main/orcamento_enviar.html', orcamento=orcamento)


@orcamentos_bp.route('/orcamento/<int:orcamento_id>/gerar-contrato')
@login_required
def gerar_contrato(orcamento_id):
    """Converter orçamento em contrato"""
    from app.models.contratos import Contrato
    
    empresa_id = session.get('empresa_id')
    orcamento = Orcamento.query.filter_by(id=orcamento_id, empresa_id=empresa_id).first_or_404()
    
    contrato = Contrato(
        empresa_id=empresa_id,
        cliente=orcamento.cliente,
        cliente_email=orcamento.cliente_email,
        cliente_telefone=orcamento.cliente_telefone,
        cliente_endereco=orcamento.cliente_endereco,
        titulo=f"Contrato - {orcamento.titulo}",
        descricao=orcamento.descricao,
        valor=orcamento.valor_total,
        data_inicio=date.today(),
        tipo='Obra'
    )
    db.session.add(contrato)
    db.session.commit()
    
    orcamento.status = 'Aprovado'
    db.session.commit()
    
    flash('Contrato criado a partir do orçamento!', 'success')
    return redirect(url_for('contratos.editar_contrato', contrato_id=contrato.id))


@orcamentos_bp.route('/orcamento/<int:orcamento_id>/item/novo', methods=['POST'])
@login_required
def novo_item(orcamento_id):
    """Adicionar item ao orçamento"""
    empresa_id = session.get('empresa_id')
    orcamento = Orcamento.query.filter_by(id=orcamento_id, empresa_id=empresa_id).first_or_404()
    
    item = ItemOrcamento(
        orcamento_id=orcamento_id,
        categoria=request.form.get('categoria'),
        descricao=request.form.get('descricao'),
        unidade=request.form.get('unidade'),
        quantidade=sanitize_float(request.form.get('quantidade'), default=1, allow_zero=False),
        valor_unitario=sanitize_float(request.form.get('valor_unitario'))
    )
    db.session.add(item)
    db.session.commit()
    
    flash('Item adicionado!', 'success')
    return redirect(url_for('orcamentos.orcamento_detalhe', orcamento_id=orcamento_id))


@orcamentos_bp.route('/item/<int:item_id>/excluir', methods=['POST'])
@login_required
def excluir_item(item_id):
    """Excluir item"""
    empresa_id = session.get('empresa_id')
    item = db.session.get(ItemOrcamento, item_id)
    if not item or item.orcamento.empresa_id != empresa_id:
        return jsonify({'error': 'Item não encontrado'}), 404
    
    orcamento_id = item.orcamento_id
    db.session.delete(item)
    db.session.commit()
    
    return jsonify({'success': True})


@orcamentos_bp.route('/api/orcamento/<int:orcamento_id>/dados')
@login_required
def api_orcamento_dados(orcamento_id):
    """API para dados do orçamento"""
    empresa_id = session.get('empresa_id')
    orcamento = Orcamento.query.filter_by(id=orcamento_id, empresa_id=empresa_id).first_or_404()
    
    return jsonify({
        'orcamento': orcamento.to_dict(),
        'itens': [i.to_dict() for i in orcamento.itens]
    })