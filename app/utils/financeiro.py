"""
Helpers para cálculos financeiros recorrentes
"""
from app.models import db, Lancamento
from sqlalchemy import func, case


def calcular_totais_obra(obra_id, empresa_id=None):
    """Calcula total de receitas e despesas de uma obra"""
    result = db.session.query(
        func.sum(case((Lancamento.tipo == 'Despesa', Lancamento.valor), else_=0)).label('despesas'),
        func.sum(case((Lancamento.tipo == 'Receita', Lancamento.valor), else_=0)).label('receitas')
    ).filter(Lancamento.obra_id == obra_id).first()
    
    return {
        'despesas': result.despesas or 0,
        'receitas': result.receitas or 0,
        'saldo': (result.receitas or 0) - (result.despesas or 0)
    }


def calcular_totais_empresa(empresa_id):
    """Calcula total de receitas e despesas de uma empresa"""
    result = db.session.query(
        func.sum(case((Lancamento.tipo == 'Despesa', Lancamento.valor), else_=0)).label('despesas'),
        func.sum(case((Lancamento.tipo == 'Receita', Lancamento.valor), else_=0)).label('receitas')
    ).filter(Lancamento.empresa_id == empresa_id).first()
    
    return {
        'despesas': result.despesas or 0,
        'receitas': result.receitas or 0,
        'saldo': (result.receitas or 0) - (result.despesas or 0)
    }


def calcular_despesas_por_categoria(empresa_id, obra_id=None):
    """Calcula despesas grouped por categoria"""
    query = db.session.query(
        Lancamento.categoria,
        func.sum(Lancamento.valor).label('total')
    ).filter(
        Lancamento.empresa_id == empresa_id,
        Lancamento.tipo == 'Despesa'
    )
    
    if obra_id:
        query = query.filter(Lancamento.obra_id == obra_id)
    
    return query.group_by(Lancamento.categoria).all()


def calcular_gastos_por_obra(empresa_id):
    """Calcula total de gastos por obra (ordenado por maior gasto)"""
    return db.session.query(
        Lancamento.obra_id,
        func.sum(case((Lancamento.tipo == 'Despesa', Lancamento.valor), else_=0)).label('total_gasto')
    ).filter(
        Lancamento.empresa_id == empresa_id
    ).group_by(Lancamento.obra_id).order_by(func.sum(Lancamento.valor).desc()).all()


def get_obras_com_maior_gasto(empresa_id, limite=5):
    """Retorna as obras com maior gasto"""
    from app.models import Obra
    
    subquery = db.session.query(
        Lancamento.obra_id,
        func.sum(case((Lancamento.tipo == 'Despesa', Lancamento.valor), else_=0)).label('total')
    ).filter(
        Lancamento.empresa_id == empresa_id
    ).group_by(Lancamento.obra_id).subquery()
    
    return db.session.query(Obra).join(
        subquery, Obra.id == subquery.c.obra_id
    ).order_by(subquery.c.total.desc()).limit(limite).all()


def get_obras_por_status(empresa_id):
    """Contagem de obras por status"""
    from app.models import Obra
    
    return db.session.query(
        Obra.status,
        func.count(Obra.id).label('qtd')
    ).filter(Obra.empresa_id == empresa_id).group_by(Obra.status).all()


def get_lancamentos_por_periodo(empresa_id, data_inicio, data_fim):
    """Busca lançamentos filtrados por período"""
    query = Lancamento.query.filter(
        Lancamento.empresa_id == empresa_id,
        Lancamento.data >= data_inicio,
        Lancamento.data <= data_fim
    )
    return query.order_by(Lancamento.data.desc()).all()