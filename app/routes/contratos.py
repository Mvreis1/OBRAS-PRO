"""
Rotas de contratos
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime, date
from app.models import db, Empresa, Obra
from app.models.contratos import Contrato, ParcelaContrato
from app.routes.auth import login_required
from app.routes.main import log_atividade
from app.utils.contratos import parse_date, validar_datas_contrato, gerar_parcelas
from app.utils.sanitize import sanitize_int, sanitize_float

contratos_bp = Blueprint('contratos', __name__)


@contratos_bp.route('/contratos')
@login_required
def contratos():
    """Lista contratos"""
    empresa_id = session.get('empresa_id')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status_filter = request.args.get('status')

    from app.utils.paginacao import Paginacao
    
    query = Contrato.query.filter_by(empresa_id=empresa_id).order_by(Contrato.created_at.desc())
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    paginacao = Paginacao(query, page=page, per_page=per_page)
    
    filter_args = {}
    if status_filter: filter_args['status'] = status_filter

    return render_template('main/contratos.html', contratos=paginacao.items, paginacao=paginacao, page_args=filter_args, status_filter=status_filter)


@contratos_bp.route('/contrato/novo', methods=['GET', 'POST'])
@login_required
def novo_contrato():
    """Novo contrato"""
    empresa_id = session.get('empresa_id')
    obras = Obra.query.filter_by(empresa_id=empresa_id).all()
    
    if request.method == 'POST':
        data_inicio = parse_date(request.form.get('data_inicio'))
        data_fim = parse_date(request.form.get('data_fim'))
        
        # Validar datas
        valido, erro = validar_datas_contrato(data_inicio, data_fim)
        if not valido:
            flash(erro, 'danger')
            return render_template('main/contrato_form.html', contrato=None, obras=obras)
        
        contrato = Contrato(
            empresa_id=empresa_id,
            obra_id=request.form.get('obra_id') or None,
            cliente=request.form.get('cliente'),
            cliente_cnpj=request.form.get('cliente_cnpj'),
            cliente_email=request.form.get('cliente_email'),
            cliente_telefone=request.form.get('cliente_telefone'),
            cliente_endereco=request.form.get('cliente_endereco'),
            titulo=request.form.get('titulo'),
            descricao=request.form.get('descricao'),
            valor=sanitize_float(request.form.get('valor')),
            data_inicio=data_inicio,
            data_fim=data_fim,
            data_assinatura=parse_date(request.form.get('data_assinatura')),
            status=request.form.get('status'),
            tipo=request.form.get('tipo'),
            observacoes=request.form.get('observacoes')
        )
        db.session.add(contrato)
        db.session.commit()
        
        num_parcelas = sanitize_int(request.form.get('num_parcelas'), min_val=1)
        if num_parcelas > 1:
            gerar_parcelas(contrato, num_parcelas)
        
        flash('Contrato criado com sucesso!', 'success')
        log_atividade('Criar contrato', 'Contrato', contrato.id, f'{contrato.titulo}')
        return redirect(url_for('contratos.contratos'))
    
    return render_template('main/contrato_form.html', contrato=None, obras=obras)


@contratos_bp.route('/contrato/<int:contrato_id>')
@login_required
def contrato_detalhe(contrato_id):
    """Detalhes do contrato"""
    empresa_id = session.get('empresa_id')
    contrato = Contrato.query.filter_by(id=contrato_id, empresa_id=empresa_id).first_or_404()
    
    parcelas = ParcelaContrato.query.filter_by(contrato_id=contrato_id).order_by(ParcelaContrato.numero).all()
    
    total_pago = sum(p.valor for p in parcelas if p.status == 'Pago')
    total_pendente = sum(p.valor for p in parcelas if p.status == 'Pendente')
    
    hoje = date.today()
    vencidas = [p for p in parcelas if p.status == 'Pendente' and p.data_vencimento < hoje]
    
    return render_template(
        'main/contrato_detalhe.html',
        contrato=contrato,
        parcelas=parcelas,
        total_pago=total_pago,
        total_pendente=total_pendente,
        vencidas=vencidas
    )


@contratos_bp.route('/contrato/<int:contrato_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_contrato(contrato_id):
    """Editar contrato"""
    empresa_id = session.get('empresa_id')
    contrato = Contrato.query.filter_by(id=contrato_id, empresa_id=empresa_id).first_or_404()
    obras = Obra.query.filter_by(empresa_id=empresa_id).all()
    
    if request.method == 'POST':
        contrato.obra_id = request.form.get('obra_id') or None
        contrato.cliente = request.form.get('cliente')
        contrato.cliente_cnpj = request.form.get('cliente_cnpj')
        contrato.cliente_email = request.form.get('cliente_email')
        contrato.cliente_telefone = request.form.get('cliente_telefone')
        contrato.cliente_endereco = request.form.get('cliente_endereco')
        contrato.titulo = request.form.get('titulo')
        contrato.descricao = request.form.get('descricao')
        contrato.valor = sanitize_float(request.form.get('valor'))
        contrato.valor_aditivo = sanitize_float(request.form.get('valor_aditivo'))
        
        # Usar parse_date com tratamento de erros
        data_inicio = parse_date(request.form.get('data_inicio'))
        data_fim = parse_date(request.form.get('data_fim'))
        
        # Validar datas
        valido, erro = validar_datas_contrato(data_inicio, data_fim)
        if not valido:
            flash(erro, 'danger')
            return render_template('main/contrato_form.html', contrato=contrato, obras=obras)
        
        contrato.data_inicio = data_inicio
        contrato.data_fim = data_fim
        contrato.data_assinatura = parse_date(request.form.get('data_assinatura'))
        
        contrato.status = request.form.get('status')
        contrato.tipo = request.form.get('tipo')
        contrato.observacoes = request.form.get('observacoes')
        
        db.session.commit()
        flash('Contrato atualizado!', 'success')
        return redirect(url_for('contratos.contrato_detalhe', contrato_id=contrato_id))
    
    return render_template('main/contrato_form.html', contrato=contrato, obras=obras)


@contratos_bp.route('/contrato/<int:contrato_id>/excluir', methods=['POST'])
@login_required
def excluir_contrato(contrato_id):
    """Excluir contrato"""
    empresa_id = session.get('empresa_id')
    contrato = Contrato.query.filter_by(id=contrato_id, empresa_id=empresa_id).first_or_404()
    db.session.delete(contrato)
    db.session.commit()
    flash('Contrato excluído!', 'success')
    return redirect(url_for('contratos.contratos'))


@contratos_bp.route('/contrato/<int:contrato_id>/parcela/novo', methods=['POST'])
@login_required
def nova_parcela(contrato_id):
    """Adicionar parcela"""
    empresa_id = session.get('empresa_id')
    contrato = Contrato.query.filter_by(id=contrato_id, empresa_id=empresa_id).first_or_404()
    
    ultima = ParcelaContrato.query.filter_by(contrato_id=contrato_id).order_by(ParcelaContrato.numero.desc()).first()
    numero = (ultima.numero + 1) if ultima else 1
    
    parcela = ParcelaContrato(
        empresa_id=empresa_id,
        contrato_id=contrato_id,
        numero=numero,
        valor=sanitize_float(request.form.get('valor')),
        data_vencimento=datetime.strptime(request.form.get('data_vencimento'), '%Y-%m-%d').date(),
        descricao=request.form.get('descricao')
    )
    db.session.add(parcela)
    db.session.commit()
    
    flash('Parcela adicionada!', 'success')
    return redirect(url_for('contratos.contrato_detalhe', contrato_id=contrato_id))


@contratos_bp.route('/parcela/<int:parcela_id>/pagar', methods=['POST'])
@login_required
def pagar_parcela(parcela_id):
    """Registrar pagamento de parcela"""
    empresa_id = session.get('empresa_id')
    parcela = ParcelaContrato.query.filter_by(id=parcela_id, empresa_id=empresa_id).first_or_404()
    
    parcela.status = 'Pago'
    parcela.data_pagamento = date.today()
    db.session.commit()
    
    flash('Pagamento registrado!', 'success')
    return redirect(url_for('contratos.contrato_detalhe', contrato_id=parcela.contrato_id))


@contratos_bp.route('/parcela/<int:parcela_id>/excluir', methods=['POST'])
@login_required
def excluir_parcela(parcela_id):
    """Excluir parcela"""
    empresa_id = session.get('empresa_id')
    parcela = ParcelaContrato.query.filter_by(id=parcela_id, empresa_id=empresa_id).first_or_404()
    contrato_id = parcela.contrato_id
    db.session.delete(parcela)
    db.session.commit()
    
    flash('Parcela excluída!', 'success')
    return redirect(url_for('contratos.contrato_detalhe', contrato_id=contrato_id))


@contratos_bp.route('/api/contrato/<int:contrato_id>/dados')
@login_required
def api_contrato_dados(contrato_id):
    """API para dados do contrato"""
    empresa_id = session.get('empresa_id')
    contrato = Contrato.query.filter_by(id=contrato_id, empresa_id=empresa_id).first_or_404()
    
    parcelas = ParcelaContrato.query.filter_by(contrato_id=contrato_id).all()
    
    return jsonify({
        'contrato': contrato.to_dict(),
        'parcelas': [p.to_dict() for p in parcelas]
    })