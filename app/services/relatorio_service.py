"""Relatorio service - Financial reporting com otimizacoes SQL"""

from datetime import date, datetime, timedelta

from sqlalchemy import case, func

from app.models import Lancamento, Obra, db


class RelatorioService:
    """Service for financial reports and analytics - OPTIMIZED"""

    @staticmethod
    def get_relatorio_geral(empresa_id, data_inicio=None, data_fim=None, obra_id=None):
        """Get general financial report using SQL aggregation. Returns dict with all report data"""
        query = Lancamento.query.filter_by(empresa_id=empresa_id)

        if obra_id:
            query = query.filter_by(obra_id=int(obra_id))
        if data_inicio:
            query = query.filter(
                Lancamento.data >= datetime.strptime(data_inicio, '%Y-%m-%d').date()
            )
        if data_fim:
            query = query.filter(Lancamento.data <= datetime.strptime(data_fim, '%Y-%m-%d').date())

        result = (
            db.session.query(
                func.sum(case((Lancamento.tipo == 'Receita', Lancamento.valor), else_=0)).label(
                    'receita'
                ),
                func.sum(case((Lancamento.tipo == 'Despesa', Lancamento.valor), else_=0)).label(
                    'despesa'
                ),
            )
            .filter(Lancamento.id.in_(query.with_entities(Lancamento.id).subquery()))
            .first()
        )

        total_receitas = result.receita or 0
        total_despesas = result.despesa or 0
        lucro_prejuizo = total_receitas - total_despesas
        margem_geral = (lucro_prejuizo / total_receitas) * 100 if total_receitas > 0 else None

        return {
            'total_receitas': total_receitas,
            'total_despesas': total_despesas,
            'lucro_prejuizo': lucro_prejuizo,
            'margem_geral': margem_geral,
        }

    @staticmethod
    def calcular_lucro_por_obra(empresa_id, data_inicio=None, data_fim=None):
        """Calculate profitability per project using SQL JOIN. Returns list of dicts"""
        obras = Obra.query.filter_by(empresa_id=empresa_id).all()

        if not obras:
            return []

        obra_ids = [o.id for o in obras]

        query = db.session.query(
            Lancamento.obra_id,
            func.sum(case((Lancamento.tipo == 'Receita', Lancamento.valor), else_=0)).label(
                'receita'
            ),
            func.sum(case((Lancamento.tipo == 'Despesa', Lancamento.valor), else_=0)).label(
                'despesa'
            ),
        ).filter(
            Lancamento.empresa_id == empresa_id,
            Lancamento.obra_id.in_(obra_ids),
        )

        if data_inicio:
            query = query.filter(
                Lancamento.data >= datetime.strptime(data_inicio, '%Y-%m-%d').date()
            )
        if data_fim:
            query = query.filter(Lancamento.data <= datetime.strptime(data_fim, '%Y-%m-%d').date())

        query = query.group_by(Lancamento.obra_id)
        resultados = query.all()

        resultados_dict = {
            r.obra_id: {'receita': r.receita or 0, 'despesa': r.despesa or 0} for r in resultados
        }

        lucro_obras = []
        for obra in obras:
            dados = resultados_dict.get(obra.id, {'receita': 0, 'despesa': 0})
            receita = dados['receita']
            despesa = dados['despesa']
            saldo = receita - despesa
            margem = (saldo / receita) * 100 if receita > 0 else None

            if receita > 0 or despesa > 0:
                lucro_obras.append(
                    {
                        'obra': obra,
                        'receita': receita,
                        'despesa': despesa,
                        'saldo': saldo,
                        'margem': margem,
                    }
                )

        return lucro_obras

    @staticmethod
    def calcular_evolucao_mensal(empresa_id, meses=12):
        """Calculate monthly evolution using single SQL query. Returns list of dicts"""
        hoje = date.today()
        data_inicio = hoje.replace(day=1) - timedelta(days=(meses - 1) * 30)

        query = (
            db.session.query(
                func.strftime('%Y-%m', Lancamento.data).label('ano_mes'),
                func.sum(case((Lancamento.tipo == 'Receita', Lancamento.valor), else_=0)).label(
                    'receita'
                ),
                func.sum(case((Lancamento.tipo == 'Despesa', Lancamento.valor), else_=0)).label(
                    'despesa'
                ),
            )
            .filter(
                Lancamento.empresa_id == empresa_id,
                Lancamento.data >= data_inicio,
            )
            .group_by(func.strftime('%Y-%m', Lancamento.data))
            .order_by(func.strftime('%Y-%m', Lancamento.data))
        )

        resultados = query.all()
        resultados_dict = {
            r.ano_mes: {'receita': r.receita or 0, 'despesa': r.despesa or 0} for r in resultados
        }

        evolucao_mensal = []
        for i in range(meses):
            mes = (date.today().replace(day=1) - timedelta(days=i * 30)).replace(day=1)
            ano_mes = mes.strftime('%Y-%m')
            nome_mes = mes.strftime('%b/%Y')

            dados = resultados_dict.get(ano_mes, {'receita': 0, 'despesa': 0})
            receita = dados['receita']
            despesa = dados['despesa']

            evolucao_mensal.append(
                {
                    'mes': nome_mes,
                    'receita': receita,
                    'despesa': despesa,
                    'saldo': receita - despesa,
                }
            )

        evolucao_mensal.reverse()
        return evolucao_mensal

    @staticmethod
    def calcular_orcamento_vs_realizado(empresa_id, data_inicio=None, data_fim=None):
        """Compare budget vs actual per project using SQL. Returns dict with data"""
        obras = Obra.query.filter_by(empresa_id=empresa_id).all()

        if not obras:
            return {
                'orcamento_obras': [],
                'total_orcamento': 0,
                'total_realizado': 0,
                'diferenca_total': 0,
                'percentual_geral': 0,
                'grafico_labels': [],
                'grafico_orcamento': [],
                'grafico_realizado': [],
            }

        obra_ids = [o.id for o in obras]
        obra_dict = {o.id: o for o in obras}

        query = db.session.query(
            Lancamento.obra_id,
            func.sum(Lancamento.valor).label('realizado'),
        ).filter(
            Lancamento.empresa_id == empresa_id,
            Lancamento.obra_id.in_(obra_ids),
            Lancamento.tipo == 'Despesa',
        )

        if data_inicio:
            query = query.filter(
                Lancamento.data >= datetime.strptime(data_inicio, '%Y-%m-%d').date()
            )
        if data_fim:
            query = query.filter(Lancamento.data <= datetime.strptime(data_fim, '%Y-%m-%d').date())

        query = query.group_by(Lancamento.obra_id)
        realizados = query.all()
        realizados_dict = {r.obra_id: r.realizado or 0 for r in realizados}

        orcamento_obras = []
        total_orcamento = 0
        total_realizado = 0
        grafico_labels = []
        grafico_orcamento = []
        grafico_realizado = []

        for obra_id in obra_ids:
            obra = obra_dict[obra_id]
            realizado = realizados_dict.get(obra_id, 0)
            orcamento = obra.orcamento_previsto
            diferenca = orcamento - realizado
            percentual = (realizado / orcamento) * 100 if orcamento > 0 else 0

            if orcamento > 0 or realizado > 0:
                orcamento_obras.append(
                    {
                        'obra': obra,
                        'orcamento': orcamento,
                        'realizado': realizado,
                        'diferenca': diferenca,
                        'percentual': percentual,
                    }
                )
                grafico_labels.append(obra.nome[:15])
                grafico_orcamento.append(orcamento)
                grafico_realizado.append(realizado)

            total_orcamento += orcamento
            total_realizado += realizado

        diferenca_total = total_orcamento - total_realizado
        percentual_geral = (total_realizado / total_orcamento) * 100 if total_orcamento > 0 else 0

        return {
            'orcamento_obras': orcamento_obras,
            'total_orcamento': total_orcamento,
            'total_realizado': total_realizado,
            'diferenca_total': diferenca_total,
            'percentual_geral': percentual_geral,
            'grafico_labels': grafico_labels,
            'grafico_orcamento': grafico_orcamento,
            'grafico_realizado': grafico_realizado,
        }

    @staticmethod
    def calcular_despesas_por_categoria(empresa_id, data_inicio=None, data_fim=None):
        """Calculate expenses by category using SQL. Returns list of dicts"""
        query = (
            db.session.query(
                Lancamento.categoria,
                func.sum(Lancamento.valor).label('total'),
            )
            .filter(Lancamento.empresa_id == empresa_id, Lancamento.tipo == 'Despesa')
            .group_by(Lancamento.categoria)
        )

        if data_inicio:
            query = query.filter(
                Lancamento.data >= datetime.strptime(data_inicio, '%Y-%m-%d').date()
            )
        if data_fim:
            query = query.filter(Lancamento.data <= datetime.strptime(data_fim, '%Y-%m-%d').date())

        categorias_db = query.all()
        total_realizado = sum(c.total for c in categorias_db)

        if total_realizado > 0:
            return [
                {
                    'categoria': c.categoria,
                    'valor': c.total,
                    'percentual': (c.total / total_realizado) * 100,
                }
                for c in categorias_db
            ]
        return []

    @staticmethod
    def get_estatisticas_gerais(empresa_id):
        """Get general statistics using optimized queries. Returns dict"""
        from app.constants import StatusObra

        obras_ativas = Obra.query.filter_by(
            empresa_id=empresa_id, status=StatusObra.EM_EXECUCAO.value
        ).count()

        lancamentos_count = Lancamento.query.filter_by(empresa_id=empresa_id).count()

        categorias_count = (
            db.session.query(func.count(func.distinct(Lancamento.categoria)))
            .filter(Lancamento.empresa_id == empresa_id)
            .scalar()
            or 0
        )

        obras_por_status = (
            db.session.query(Obra.status, func.count(Obra.id))
            .filter(Obra.empresa_id == empresa_id)
            .group_by(Obra.status)
            .all()
        )

        top_despesas = (
            Lancamento.query.filter_by(empresa_id=empresa_id, tipo='Despesa')
            .order_by(Lancamento.valor.desc())
            .limit(5)
            .all()
        )

        return {
            'obras_ativas': obras_ativas,
            'lancamentos_count': lancamentos_count,
            'categorias_count': categorias_count,
            'obras_por_status': obras_por_status,
            'top_despesas': top_despesas,
        }
