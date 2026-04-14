"""
API Documentation com Swagger/OpenAPI
"""
from flask import Blueprint, jsonify, request, session
from app.routes.auth import login_required
from app.models import db, Obra, Lancamento, Usuario
from sqlalchemy import func, case
from flask_login import current_user

api_bp = Blueprint('api', __name__, url_prefix='/api')

# Swagger template (definido aqui mas usado em __init__.py)
swagger_template = {
    "info": {
        "title": "OBRAS PRO API",
        "description": "API REST para Gestão Financeira de Obras",
        "version": "1.0.0",
        "contact": {
            "name": "Suporte",
            "email": "suporte@obraspro.com.br"
        }
    },
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT Authorization header using the Bearer scheme"
        }
    },
    "security": [{"Bearer": []}]
}


@api_bp.route('/obra/<int:obra_id>')
@login_required
def api_obra_detalhe(obra_id):
    """
    Detalhes de uma obra
    ---
    tags:
      - Obras
    parameters:
      - name: obra_id
        in: path
        type: integer
        required: true
        description: ID da obra
    responses:
      200:
        description: Dados da obra
      404:
        description: Obra não encontrada
    """
    empresa_id = session.get('empresa_id')
    obra = Obra.query.filter_by(id=obra_id, empresa_id=empresa_id).first_or_404()
    
    # Calcular totais
    from app.utils.financeiro import calcular_totais_obra
    totais = calcular_totais_obra(obra.id, empresa_id)
    
    return jsonify({
        'id': obra.id,
        'nome': obra.nome,
        'descricao': obra.descricao,
        'status': obra.status,
        'orcamento_previsto': obra.orcamento_previsto,
        'progresso': obra.progresso,
        'total_despesas': totais['despesas'],
        'total_receitas': totais['receitas'],
        'saldo': totais['saldo'],
        'data_inicio': obra.data_inicio.isoformat() if obra.data_inicio else None,
        'data_fim_prevista': obra.data_fim_prevista.isoformat() if obra.data_fim_prevista else None,
    })


@api_bp.route('/obras')
@login_required
def api_obras():
    """
    Listar obras da empresa
    ---
    tags:
      - Obras
    parameters:
      - name: status
        in: query
        type: string
        required: false
        description: Filtrar por status
      - name: page
        in: query
        type: integer
        required: false
        description: Número da página
      - name: per_page
        in: query
        type: integer
        required: false
        description: Itens por página
    responses:
      200:
        description: Lista de obras
    """
    empresa_id = session.get('empresa_id')
    status = request.args.get('status')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = Obra.query.filter_by(empresa_id=empresa_id)
    if status:
        query = query.filter_by(status=status)
    
    from app.utils.paginacao import Paginacao
    paginacao = Paginacao(query.order_by(Obra.created_at.desc()), page=page, per_page=per_page)
    
    return jsonify({
        'obras': [o.to_dict(include_totals=False) for o in paginacao.items],
        'page': paginacao.page,
        'pages': paginacao.pages,
        'total': paginacao.total
    })


@api_bp.route('/lancamentos')
@login_required
def api_lancamentos():
    """
    Listar lançamentos financeiros
    ---
    tags:
      - Lançamentos
    parameters:
      - name: obra_id
        in: query
        type: integer
        required: false
        description: Filtrar por obra
      - name: tipo
        in: query
        type: string
        required: false
        description: Tipo (Receita/Despesa)
      - name: data_inicio
        in: query
        type: string
        format: date
        required: false
        description: Data inicial (YYYY-MM-DD)
      - name: data_fim
        in: query
        type: string
        format: date
        required: false
        description: Data final (YYYY-MM-DD)
    responses:
      200:
        description: Lista de lançamentos
    """
    empresa_id = session.get('empresa_id')
    obra_id = request.args.get('obra_id', type=int)
    tipo = request.args.get('tipo')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    query = Lancamento.query.filter_by(empresa_id=empresa_id)
    
    if obra_id:
        query = query.filter_by(obra_id=obra_id)
    if tipo:
        query = query.filter_by(tipo=tipo)
    if data_inicio:
        from datetime import datetime
        query = query.filter(Lancamento.data >= datetime.strptime(data_inicio, '%Y-%m-%d').date())
    if data_fim:
        from datetime import datetime
        query = query.filter(Lancamento.data <= datetime.strptime(data_fim, '%Y-%m-%d').date())
    
    lancamentos = query.order_by(Lancamento.data.desc()).limit(100).all()
    
    return jsonify({
        'lancamentos': [l.to_dict() for l in lancamentos],
        'total': len(lancamentos)
    })


@api_bp.route('/lancamento', methods=['POST'])
@login_required
def api_lancamento_criar():
    """
    Criar novo lançamento
    ---
    tags:
      - Lançamentos
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - obra_id
            - descricao
            - tipo
            - valor
            - data
          properties:
            obra_id:
              type: integer
            descricao:
              type: string
            tipo:
              type: string
              enum: [Receita, Despesa]
            valor:
              type: number
            data:
              type: string
              format: date
            categoria:
              type: string
            forma_pagamento:
              type: string
            documento:
              type: string
    responses:
      201:
        description: Lançamento criado
      400:
        description: Erro na validação
    """
    data = request.get_json()
    
    from app.utils.sanitize import sanitize_string, sanitize_float, sanitize_date
    from app.utils.dates import parse_date
    
    obra_id = data.get('obra_id')
    descricao = sanitize_string(data.get('descricao'), max_length=200)
    tipo = data.get('tipo')
    valor = sanitize_float(data.get('valor'))
    data_lanc = parse_date(data.get('data'))
    
    if not all([obra_id, descricao, tipo, valor, data_lanc]):
        return jsonify({'erro': 'Dados obrigatórios faltando'}), 400
    
    empresa_id = session.get('empresa_id')
    
    lancamento = Lancamento(
        empresa_id=empresa_id,
        obra_id=obra_id,
        descricao=descricao,
        tipo=tipo,
        valor=valor,
        data=data_lanc,
        categoria=data.get('categoria'),
        forma_pagamento=data.get('forma_pagamento'),
        documento=data.get('documento'),
        status_pagamento=data.get('status_pagamento', 'Pago')
    )
    
    db.session.add(lancamento)
    db.session.commit()
    
    return jsonify(lancamento.to_dict()), 201


@api_bp.route('/financeiro/resumo')
@login_required
def api_financeiro_resumo():
    """
    Resumo financeiro da empresa
    ---
    tags:
      - Financeiro
    responses:
      200:
        description: Resumo financeiro
    """
    empresa_id = session.get('empresa_id')
    
    from app.utils.financeiro import calcular_totais_empresa
    totais = calcular_totais_empresa(empresa_id)
    
    # Obras por status
    from app.utils.financeiro import get_obras_por_status
    obras_status = get_obras_por_status(empresa_id)
    
    return jsonify({
        'total_receitas': totais['receitas'],
        'total_despesas': totais['despesas'],
        'saldo': totais['saldo'],
        'obras_por_status': {s.status: s.qtd for s in obras_status}
    })


@api_bp.route('/usuario/atual')
@login_required
def api_usuario_atual():
    """
    Dados do usuário logado
    ---
    tags:
      - Usuário
    responses:
      200:
        description: Dados do usuário
    """
    usuario_id = session.get('usuario_id')
    usuario = db.session.get(Usuario, usuario_id)
    
    return jsonify({
        'id': usuario.id,
        'nome': usuario.nome,
        'email': usuario.email,
        'cargo': usuario.cargo,
        'two_factor_enabled': usuario.two_factor_enabled,
        'empresa': {
            'id': usuario.empresa_id,
            'nome': session.get('empresa_nome'),
            'slug': session.get('empresa_slug')
        }
    })


# ==================== CRUD OBRAS ====================

@api_bp.route('/obra', methods=['POST'])
@login_required
def api_obra_criar():
    """
    Criar nova obra
    ---
    tags:
      - Obras
    """
    from app.models import Obra
    from app.utils.sanitize import sanitize_string, sanitize_float, sanitize_date
    from app.utils.dates import parse_date
    
    data = request.get_json()
    empresa_id = session.get('empresa_id')
    
    obra = Obra(
        empresa_id=empresa_id,
        nome=sanitize_string(data.get('nome'), max_length=200),
        descricao=sanitize_string(data.get('descricao'), max_length=1000),
        endereco=sanitize_string(data.get('endereco'), max_length=300),
        orcamento_previsto=sanitize_float(data.get('orcamento_previsto')),
        data_inicio=parse_date(data.get('data_inicio')),
        data_fim_prevista=parse_date(data.get('data_fim_prevista')),
        status=data.get('status', 'Planejamento'),
        responsavel=sanitize_string(data.get('responsavel'), max_length=100),
        cliente=sanitize_string(data.get('cliente'), max_length=200)
    )
    
    db.session.add(obra)
    db.session.commit()
    
    return jsonify(obra.to_dict(include_totals=False)), 201


@api_bp.route('/obra/<int:obra_id>', methods=['PUT'])
@login_required
def api_obra_editar(obra_id):
    """
    Editar obra
    ---
    tags:
      - Obras
    """
    from app.models import Obra
    from app.utils.sanitize import sanitize_string, sanitize_float, sanitize_date
    from app.utils.dates import parse_date
    
    empresa_id = session.get('empresa_id')
    obra = Obra.query.filter_by(id=obra_id, empresa_id=empresa_id).first_or_404()
    data = request.get_json()
    
    if 'nome' in data:
        obra.nome = sanitize_string(data.get('nome'), max_length=200)
    if 'descricao' in data:
        obra.descricao = sanitize_string(data.get('descricao'), max_length=1000)
    if 'endereco' in data:
        obra.endereco = sanitize_string(data.get('endereco'), max_length=300)
    if 'orcamento_previsto' in data:
        obra.orcamento_previsto = sanitize_float(data.get('orcamento_previsto'))
    if 'data_inicio' in data:
        obra.data_inicio = parse_date(data.get('data_inicio'))
    if 'data_fim_prevista' in data:
        obra.data_fim_prevista = parse_date(data.get('data_fim_prevista'))
    if 'status' in data:
        obra.status = data.get('status')
    if 'progresso' in data:
        obra.progresso = min(max(int(data.get('progresso', 0)), 0), 100)
    
    db.session.commit()
    return jsonify(obra.to_dict(include_totals=False))


@api_bp.route('/obra/<int:obra_id>', methods=['DELETE'])
@login_required
def api_obra_excluir(obra_id):
    """
    Excluir obra
    ---
    tags:
      - Obras
    """
    from app.models import Obra
    
    empresa_id = session.get('empresa_id')
    obra = Obra.query.filter_by(id=obra_id, empresa_id=empresa_id).first_or_404()
    
    db.session.delete(obra)
    db.session.commit()
    
    return jsonify({'message': 'Obra excluída'})


# ==================== CRUDS RELACIONADOS ====================

@api_bp.route('/lancamento/<int:lancamento_id>', methods=['GET'])
@login_required
def api_lancamento_detalhe(lancamento_id):
    """
    Detalhes de um lançamento
    ---
    tags:
      - Lançamentos
    """
    empresa_id = session.get('empresa_id')
    lancamento = Lancamento.query.filter_by(id=lancamento_id, empresa_id=empresa_id).first_or_404()
    return jsonify(lancamento.to_dict())


@api_bp.route('/lancamento/<int:lancamento_id>', methods=['PUT'])
@login_required
def api_lancamento_editar(lancamento_id):
    """
    Editar lançamento
    ---
    tags:
      - Lançamentos
    """
    empresa_id = session.get('empresa_id')
    lancamento = Lancamento.query.filter_by(id=lancamento_id, empresa_id=empresa_id).first_or_404()
    data = request.get_json()
    
    from app.utils.sanitize import sanitize_string, sanitize_float
    from app.utils.dates import parse_date
    
    if 'descricao' in data:
        lancamento.descricao = sanitize_string(data.get('descricao'), max_length=200)
    if 'valor' in data:
        lancamento.valor = sanitize_float(data.get('valor'))
    if 'data' in data:
        lancamento.data = parse_date(data.get('data'))
    if 'categoria' in data:
        lancamento.categoria = data.get('categoria')
    if 'tipo' in data:
        lancamento.tipo = data.get('tipo')
    if 'status_pagamento' in data:
        lancamento.status_pagamento = data.get('status_pagamento')
    
    db.session.commit()
    return jsonify(lancamento.to_dict())


@api_bp.route('/lancamento/<int:lancamento_id>', methods=['DELETE'])
@login_required
def api_lancamento_excluir(lancamento_id):
    """
    Excluir lançamento
    ---
    tags:
      - Lançamentos
    """
    empresa_id = session.get('empresa_id')
    lancamento = Lancamento.query.filter_by(id=lancamento_id, empresa_id=empresa_id).first_or_404()
    
    db.session.delete(lancamento)
    db.session.commit()
    
    return jsonify({'message': 'Lançamento excluído'})


# ==================== RELATÓRIOS ====================

@api_bp.route('/relatorio/obras')
@login_required
def api_relatorio_obras():
    """
    Relatório de obras com custos
    ---
    tags:
      - Relatórios
    """
    from app.utils.financeiro import get_obras_com_maior_gasto, get_obras_por_status
    
    empresa_id = session.get('empresa_id')
    
    # Obras por status
    obras_status = get_obras_por_status(empresa_id)
    
    # Maiores custos
    obras_custos = db.session.query(
        Obra.id, Obra.nome, Obra.status,
        func.sum(case((Lancamento.tipo == 'Despesa', Lancamento.valor), else_=0)).label('gasto')
    ).outerjoin(Lancamento).filter(
        Obra.empresa_id == empresa_id
    ).group_by(Obra.id).all()
    
    return jsonify({
        'por_status': {s.status: s.qtd for s in obras_status},
        'obras': [
            {'id': o.id, 'nome': o.nome, 'status': o.status, 'gasto': float(o.gasto or 0)}
            for o in obras_custos
        ]
    })


@api_bp.route('/relatorio/categorias')
@login_required
def api_relatorio_categorias():
    """
    Despesas por categoria
    ---
    tags:
      - Relatórios
    """
    from app.utils.financeiro import calcular_despesas_por_categoria
    
    empresa_id = session.get('empresa_id')
    obra_id = request.args.get('obra_id', type=int)
    
    categorias = calcular_despesas_por_categoria(empresa_id, obra_id)
    
    return jsonify({
        'categorias': [{'categoria': c[0], 'total': float(c[1])} for c in categorias]
    })


@api_bp.route('/backup/list')
@login_required
def list_backups():
    """
    Lista backups disponíveis
    ---
    tags:
      - Backup
    responses:
      200:
        description: Lista de backups
    """
    from app.models.acesso import Permissao
    
    if not current_user.has_permission('backup', 'ver'):
        return jsonify({'error': 'Sem permissao'}), 403
    
    import os
    backup_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backups')
    backups = []
    
    if os.path.exists(backup_dir):
        for f in os.listdir(backup_dir):
            if f.endswith('.zip'):
                path = os.path.join(backup_dir, f)
                backups.append({
                    'nome': f,
                    'tamanho': os.path.getsize(path),
                    'data': os.path.getmtime(path)
                })
    
    return jsonify({'backups': backups})