"""
Rotas de gestão bancária
"""
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import db, ContaBancaria, LancamentoConta
from app.routes.auth import login_required
from app.utils.sanitize import sanitize_int, sanitize_float

banco_bp = Blueprint('banco', __name__)


@banco_bp.route('/bancos')
@login_required
def bancos():
    """Lista todas as contas bancárias"""
    empresa_id = session.get('empresa_id')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    from app.utils.paginacao import Paginacao
    paginacao = Paginacao(
        ContaBancaria.query.filter_by(empresa_id=empresa_id, ativo=True).order_by(ContaBancaria.nome),
        page=page,
        per_page=per_page
    )
    
    return render_template('banco/bancos.html', contas=paginacao.items, paginacao=paginacao)


@banco_bp.route('/banco/novo', methods=['GET', 'POST'])
@login_required
def novo_banco():
    """Cadastrar nova conta bancária"""
    empresa_id = session.get('empresa_id')
    
    if request.method == 'POST':
        saldo_inicial = sanitize_float(request.form.get('saldo_inicial'))
        conta = ContaBancaria(
            empresa_id=empresa_id,
            nome=request.form.get('nome'),
            banco=request.form.get('banco'),
            agencia=request.form.get('agencia'),
            conta=request.form.get('conta'),
            tipo=request.form.get('tipo'),
            saldo_inicial=saldo_inicial,
            saldo_atual=saldo_inicial,  # Saldo inicial = saldo atual na criação
            observacoes=request.form.get('observacoes')
        )
        db.session.add(conta)
        db.session.commit()
        flash('Conta bancária cadastrada com sucesso!', 'success')
        return redirect(url_for('banco.bancos'))
    
    return render_template('banco/banco_form.html', conta=None)


@banco_bp.route('/banco/<int:conta_id>')
@login_required
def banco_detalhe(conta_id):
    """Detalhes de uma conta bancária"""
    empresa_id = session.get('empresa_id')
    conta = ContaBancaria.query.filter_by(id=conta_id, empresa_id=empresa_id).first_or_404()
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    from app.utils.paginacao import Paginacao
    paginacao = Paginacao(
        LancamentoConta.query.filter_by(conta_id=conta_id, empresa_id=empresa_id).order_by(LancamentoConta.data.desc()),
        page=page,
        per_page=per_page
    )

    # Totais usando query agregada (evita N+1)
    from sqlalchemy import func, case
    result = db.session.query(
        func.sum(case((LancamentoConta.tipo == 'Credito', LancamentoConta.valor), else_=0)).label('credito'),
        func.sum(case((LancamentoConta.tipo == 'Debito', LancamentoConta.valor), else_=0)).label('debito')
    ).filter(
        LancamentoConta.conta_id == conta_id,
        LancamentoConta.empresa_id == empresa_id
    ).first()

    return render_template(
        'banco/banco_detalhe.html',
        conta=conta,
        lancamentos=paginacao.items,
        paginacao=paginacao,
        total_credito=result.credito or 0,
        total_debito=result.debito or 0
    )


@banco_bp.route('/banco/<int:conta_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_banco(conta_id):
    """Editar conta bancária"""
    empresa_id = session.get('empresa_id')
    conta = ContaBancaria.query.filter_by(id=conta_id, empresa_id=empresa_id).first_or_404()
    
    if request.method == 'POST':
        conta.nome = request.form.get('nome')
        conta.banco = request.form.get('banco')
        conta.agencia = request.form.get('agencia')
        conta.conta = request.form.get('conta')
        conta.tipo = request.form.get('tipo')
        conta.observacoes = request.form.get('observacoes')
        
        db.session.commit()
        flash('Conta atualizada com sucesso!', 'success')
        return redirect(url_for('banco.bancos'))
    
    return render_template('banco/banco_form.html', conta=conta)


@banco_bp.route('/banco/<int:conta_id>/excluir', methods=['POST'])
@login_required
def excluir_banco(conta_id):
    """Excluir (desativar) conta bancária"""
    empresa_id = session.get('empresa_id')
    conta = ContaBancaria.query.filter_by(id=conta_id, empresa_id=empresa_id).first_or_404()
    conta.ativo = False
    db.session.commit()
    flash('Conta desativada com sucesso!', 'success')
    return redirect(url_for('banco.bancos'))


@banco_bp.route('/banco/<int:conta_id>/lancamento/novo', methods=['GET', 'POST'])
@login_required
def novo_lancamento_conta(conta_id):
    """Novo lançamento na conta"""
    empresa_id = session.get('empresa_id')
    conta = ContaBancaria.query.filter_by(id=conta_id, empresa_id=empresa_id).first_or_404()
    
    if request.method == 'POST':
        valor = float(request.form.get('valor'))
        tipo = request.form.get('tipo')
        
        if tipo == 'Credito':
            novo_saldo = conta.saldo_atual + valor
        else:
            novo_saldo = conta.saldo_atual - valor
        
        lancamento = LancamentoConta(
            empresa_id=empresa_id,
            conta_id=conta_id,
            descricao=request.form.get('descricao'),
            tipo=tipo,
            valor=valor,
            data=datetime.strptime(request.form.get('data'), '%Y-%m-%d').date(),
            documento=request.form.get('documento'),
            categoria=request.form.get('categoria')
        )
        
        conta.saldo_atual = novo_saldo
        db.session.add(lancamento)
        db.session.commit()
        
        flash('Lançamento cadastrado com sucesso!', 'success')
        return redirect(url_for('banco.banco_detalhe', conta_id=conta_id))
    
    return render_template('banco/lancamento_form.html', conta=conta, lancamento=None, data=datetime.now())


@banco_bp.route('/banco/transferencia', methods=['GET', 'POST'])
@login_required
def transferencia():
    """Transferência entre contas"""
    empresa_id = session.get('empresa_id')
    contas = ContaBancaria.query.filter_by(empresa_id=empresa_id, ativo=True).all()
    
    if request.method == 'POST':
        conta_origem_id = sanitize_int(request.form.get('conta_origem'))
        conta_destino_id = sanitize_int(request.form.get('conta_destino'))
        valor = sanitize_float(request.form.get('valor'))
        
        if conta_origem_id == conta_destino_id:
            flash('Não é possível transferir para a mesma conta.', 'danger')
            return render_template('banco/transferencia.html', contas=contas, data=datetime.now())
        
        # Recarregar contas dentro da transação para evitar race conditions
        conta_origem = db.session.get(ContaBancaria, conta_origem_id)
        conta_destino = db.session.get(ContaBancaria, conta_destino_id)
        
        if not conta_origem or not conta_destino:
            flash('Conta não encontrada.', 'danger')
            return render_template('banco/transferencia.html', contas=contas, data=datetime.now())
        
        if conta_origem.empresa_id != empresa_id:
            flash('Conta não pertence à sua empresa.', 'danger')
            return render_template('banco/transferencia.html', contas=contas, data=datetime.now())
        
        if conta_origem.saldo_atual < valor:
            flash('Saldo insuficiente para transferência!', 'danger')
            return render_template('banco/transferencia.html', contas=contas, data=datetime.now())
        
        from app.models.banco import LancamentoConta
        
        lancamento_debito = LancamentoConta(
            empresa_id=empresa_id,
            conta_id=conta_origem_id,
            descricao=f'Transferência para {conta_destino.nome}',
            tipo='Debito',
            valor=valor,
            data=datetime.now().date()
        )
        
        lancamento_credito = LancamentoConta(
            empresa_id=empresa_id,
            conta_id=conta_destino_id,
            descricao=f'Transferência de {conta_origem.nome}',
            tipo='Credito',
            valor=valor,
            data=datetime.now().date()
        )
        
        conta_origem.saldo_atual -= valor
        conta_destino.saldo_atual += valor
        
        db.session.add(lancamento_debito)
        db.session.add(lancamento_credito)
        db.session.commit()
        
        flash('Transferência realizada com sucesso!', 'success')
        return redirect(url_for('banco.bancos'))
    
    return render_template('banco/transferencia.html', contas=contas, data=datetime.now())


@banco_bp.route('/api/bancos')
@login_required
def api_bancos():
    """API para listar contas"""
    from flask import jsonify
    
    empresa_id = session.get('empresa_id')
    contas = ContaBancaria.query.filter_by(empresa_id=empresa_id, ativo=True).all()
    return jsonify([c.to_dict() for c in contas])


@banco_bp.route('/api/banco/<int:conta_id>/extrato')
@login_required
def api_extrato(conta_id):
    """API para extrato da conta"""
    from flask import jsonify
    from datetime import datetime, timedelta
    
    empresa_id = session.get('empresa_id')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    query = LancamentoConta.query.filter_by(conta_id=conta_id, empresa_id=empresa_id)
    
    if data_inicio:
        query = query.filter(LancamentoConta.data >= datetime.strptime(data_inicio, '%Y-%m-%d').date())
    if data_fim:
        query = query.filter(LancamentoConta.data <= datetime.strptime(data_fim, '%Y-%m-%d').date())
    
    lancamentos = query.order_by(LancamentoConta.data.desc()).all()
    
    return jsonify({
        'conta': ContaBancaria.query.filter_by(id=conta_id, empresa_id=empresa_id).first().to_dict(),
        'lancamentos': [l.to_dict() for l in lancamentos]
    })
