"""
Rotas para Histórico de Alterações
"""

from datetime import datetime, timedelta

from flask import Blueprint, jsonify, render_template, request, session

from app.models.models import db
from app.routes.auth import login_required
from app.utils.audit import AuditTrail

audit_bp = Blueprint('audit', __name__, url_prefix='/audit')


@audit_bp.route('/historico')
@login_required
def historico_geral():
    """Página de histórico geral"""
    empresa_id = session.get('empresa_id')

    # Filtros
    entidade = request.args.get('entidade')
    usuario_id = request.args.get('usuario_id', type=int)
    periodo = request.args.get('periodo', '30')  # dias

    # Calcular data início
    data_fim = datetime.now()
    data_inicio = data_fim - timedelta(days=int(periodo))

    paginacao = AuditTrail.get_historico_empresa(
        empresa_id=empresa_id,
        entidade=entidade,
        usuario_id=usuario_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        page=request.args.get('page', 1, type=int),
        per_page=50,
    )

    return render_template(
        'main/logs.html',
        logs=paginacao.items,
        paginacao=paginacao,
        filtros={'entidade': entidade, 'usuario_id': usuario_id, 'periodo': periodo},
    )


@audit_bp.route('/historico/<entidade>/<int:entidade_id>')
@login_required
def historico_entidade(entidade, entidade_id):
    """Histórico de uma entidade específica"""
    logs = AuditTrail.get_historico_entidade(entidade, entidade_id)
    return jsonify({'logs': logs})


@audit_bp.route('/api/historico')
@login_required
def api_historico():
    """API para histórico com filtros"""
    empresa_id = session.get('empresa_id')

    periodo = request.args.get('periodo', '30', type=int)
    entidade = request.args.get('entidade')
    page = request.args.get('page', 1, type=int)

    data_fim = datetime.now()
    data_inicio = data_fim - timedelta(days=periodo)

    paginacao = AuditTrail.get_historico_empresa(
        empresa_id=empresa_id,
        entidade=entidade,
        data_inicio=data_inicio,
        data_fim=data_fim,
        page=page,
        per_page=30,
    )

    return jsonify(
        {
            'logs': [log.to_dict() for log in paginacao.items],
            'page': paginacao.page,
            'pages': paginacao.pages,
            'total': paginacao.total,
        }
    )


@audit_bp.route('/estatisticas')
@login_required
def estatisticas():
    """Estatísticas de ações por período"""
    empresa_id = session.get('empresa_id')

    periodo = request.args.get('periodo', '30', type=int)
    data_fim = datetime.now()
    data_inicio = data_fim - timedelta(days=periodo)

    from sqlalchemy import func

    from app.models.models import LogAtividade

    # Ações por tipo
    por_acao = (
        db.session.query(LogAtividade.acao, func.count(LogAtividade.id))
        .filter(LogAtividade.empresa_id == empresa_id, LogAtividade.created_at >= data_inicio)
        .group_by(LogAtividade.acao)
        .all()
    )

    # Ações por entidade
    por_entidade = (
        db.session.query(LogAtividade.entidade, func.count(LogAtividade.id))
        .filter(LogAtividade.empresa_id == empresa_id, LogAtividade.created_at >= data_inicio)
        .group_by(LogAtividade.entidade)
        .all()
    )

    return jsonify(
        {'por_acao': dict(por_acao), 'por_entidade': dict(por_entidade), 'periodo_dias': periodo}
    )


@audit_bp.route('/timeline/<entidade>/<int:entidade_id>')
@login_required
def timeline(entidade, entidade_id):
    """Timeline de alterações de uma entidade"""
    logs = AuditTrail.get_historico_entidade(entidade, entidade_id, limite=100)

    return render_template(
        'main/timeline.html', logs=logs, entidade=entidade, entidade_id=entidade_id
    )
