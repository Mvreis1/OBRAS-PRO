"""Dashboard Service - Aggregated data and statistics for dashboards"""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import case, func

from app.models import Lancamento, Obra, db
from app.services.lancamento_service import LancamentoService
from app.services.obra_service import ObraService
from app.utils.dates import parse_date


class DashboardService:
    """Service for dashboard data aggregation and statistics"""

    @staticmethod
    def get_dashboard_resumo(
        empresa_id: int, mes: int | None = None, ano: int | None = None
    ) -> dict:
        """
        Get complete dashboard summary with financial data.

        Args:
            empresa_id: Empresa ID
            mes: Filter by month (1-12), defaults to current month
            ano: Filter by year, defaults to current year

        Returns:
            Dict with receitas, despesas, saldo, obras stats, etc.
        """
        now = datetime.now()
        mes = mes or now.month
        ano = ano or now.year

        # Financial summary using SQL aggregation (efficient)
        financial = LancamentoService.get_financial_summary(empresa_id)

        # Monthly summary
        mes_inicio = date(ano, mes, 1)
        if mes == 12:
            mes_fim = date(ano + 1, 1, 1)
        else:
            mes_fim = date(ano, mes + 1, 1)

        mes_financial = LancamentoService.get_financial_summary(
            empresa_id,
            data_inicio=mes_inicio.strftime('%Y-%m-%d'),
            data_fim=mes_fim.strftime('%Y-%m-%d'),
        )

        # Obras statistics
        obras_stats = ObraService.get_obras_por_status(empresa_id)
        obras_atrasadas = ObraService.get_obras_atrasadas(empresa_id)
        obras_estouradas = ObraService.get_obras_com_orcamento_estourado(empresa_id)

        # Expenses by category
        despesas_categoria = LancamentoService.get_by_categoria(empresa_id)

        # Top obras by expenses
        top_obras = DashboardService._get_top_obras_by_despesas(empresa_id, limit=5)

        return {
            'total_receitas': financial['receitas'],
            'total_despesas': financial['despesas'],
            'saldo': financial['saldo'],
            'margem': (financial['saldo'] / financial['receitas'] * 100)
            if financial['receitas'] > 0
            else 0,
            'receitas_mes': mes_financial['receitas'],
            'despesas_mes': mes_financial['despesas'],
            'saldo_mes': mes_financial['saldo'],
            'obras_status': obras_stats,
            'obras_atrasadas': obras_atrasadas,
            'obras_estouradas': obras_estouradas,
            'despesas_por_categoria': despesas_categoria,
            'top_obras': top_obras,
            'mes_referencia': mes,
            'ano_referencia': ano,
        }

    @staticmethod
    def _get_top_obras_by_despesas(empresa_id: int, limit: int = 5) -> list[dict]:
        """Get top obras by expenses using SQL aggregation"""
        results = (
            db.session.query(
                Obra,
                func.sum(case((Lancamento.tipo == 'Despesa', Lancamento.valor), else_=0)).label(
                    'total_despesas'
                ),
            )
            .outerjoin(Lancamento, Lancamento.obra_id == Obra.id)
            .filter(Obra.empresa_id == empresa_id)
            .group_by(Obra.id)
            .order_by(
                func.sum(case((Lancamento.tipo == 'Despesa', Lancamento.valor), else_=0)).desc()
            )
            .limit(limit)
            .all()
        )

        return [
            {
                'obra': obra,
                'total_despesas': total_despesas or 0,
            }
            for obra, total_despesas in results
        ]

    @staticmethod
    def get_dashboard_chart_data(
        empresa_id: int, meses: int = 12, data_fim: date | None = None
    ) -> list[dict]:
        """
        Get monthly chart data for the last N months.

        Args:
            empresa_id: Empresa ID
            meses: Number of months (default 12)
            data_fim: End date (default today)

        Returns:
            List of dicts with mes, receitas, despesas, saldo
        """
        if data_fim is None:
            data_fim = date.today()

        chart_data = []

        # Calculate data for each month
        for i in range(meses - 1, -1, -1):
            # Calculate month/year for this iteration
            mes = data_fim.month - i
            ano = data_fim.year
            while mes <= 0:
                mes += 12
                ano -= 1

            mes_inicio = date(ano, mes, 1)
            if mes == 12:
                mes_fim = date(ano + 1, 1, 1)
            else:
                mes_fim = date(ano, mes + 1, 1)

            month_data = LancamentoService.get_financial_summary(
                empresa_id,
                data_inicio=mes_inicio.strftime('%Y-%m-%d'),
                data_fim=mes_fim.strftime('%Y-%m-%d'),
            )

            mes_nome = mes_inicio.strftime('%b/%Y')

            chart_data.append(
                {
                    'mes': mes_nome,
                    'receitas': month_data['receitas'],
                    'despesas': month_data['despesas'],
                    'saldo': month_data['saldo'],
                }
            )

        return chart_data

    @staticmethod
    def get_obra_dashboard_data(obra_id: int, empresa_id: int) -> dict | None:
        """
        Get complete dashboard data for a specific obra.

        Args:
            obra_id: Obra ID
            empresa_id: Empresa ID

        Returns:
            Dict with obra data, financials, categories, etc.
        """
        obra_data = ObraService.get_obra_completa(obra_id, empresa_id)
        if not obra_data:
            return None

        obra = obra_data['obra']

        # Get expenses by category for this obra
        LancamentoService.get_by_categoria(empresa_id)

        # Filter only for this obra
        despesas_categoria_obra = (
            db.session.query(
                Lancamento.categoria,
                func.count(Lancamento.id).label('quantidade'),
                func.sum(Lancamento.valor).label('total'),
            )
            .filter(
                Lancamento.empresa_id == empresa_id,
                Lancamento.obra_id == obra_id,
                Lancamento.tipo == 'Despesa',
            )
            .group_by(Lancamento.categoria)
            .order_by(func.sum(Lancamento.valor).desc())
            .all()
        )

        # Monthly chart data for this obra
        chart_data = DashboardService.get_dashboard_chart_data(empresa_id, meses=12)

        # Budget usage
        orcamento = obra.orcamento_previsto or 0
        total_despesas = obra_data['total_despesas']
        percentual_orcamento = (total_despesas / orcamento * 100) if orcamento > 0 else 0

        # Revenue vs Expenses
        total_receitas = obra_data['total_receitas']
        percentual_receita = (total_despesas / total_receitas * 100) if total_receitas > 0 else 0

        return {
            'obra': obra,
            'total_receitas': total_receitas,
            'total_despesas': total_despesas,
            'saldo': obra_data['saldo'],
            'margem': obra_data['margem'],
            'orcamento_previsto': orcamento,
            'percentual_orcamento': percentual_orcamento,
            'percentual_receita': percentual_receita,
            'despesas_por_categoria': [
                {
                    'categoria': row.categoria or 'Sem categoria',
                    'quantidade': row.quantidade,
                    'total': row.total,
                }
                for row in despesas_categoria_obra
            ],
            'chart_data': chart_data,
        }

    @staticmethod
    def get_kpi_tendencias(empresa_id: int, meses: int = 6) -> dict:
        """
        Get KPI trends for the last N months.

        Args:
            empresa_id: Empresa ID
            meses: Number of months (default 6)

        Returns:
            Dict with trend data for key metrics
        """
        chart_data = DashboardService.get_dashboard_chart_data(empresa_id, meses=meses)

        if len(chart_data) < 2:
            return {
                'receitas_tendencia': 'stable',
                'despesas_tendencia': 'stable',
                'margem_tendencia': 'stable',
            }

        # Calculate trends
        def calcular_tendencia(values):
            """Simple trend calculation"""
            if len(values) < 2:
                return 'stable'

            recent = values[-1]
            previous = values[-2]

            if previous == 0:
                return 'stable' if recent == 0 else 'up'

            change = (recent - previous) / previous * 100

            if change > 5:
                return 'up'
            elif change < -5:
                return 'down'
            else:
                return 'stable'

        receitas = [d['receitas'] for d in chart_data]
        despesas = [d['despesas'] for d in chart_data]
        margens = [
            (d['saldo'] / d['receitas'] * 100) if d['receitas'] > 0 else 0 for d in chart_data
        ]

        return {
            'receitas_tendencia': calcular_tendencia(receitas),
            'despesas_tendencia': calcular_tendencia(despesas),
            'margem_tendencia': calcular_tendencia(margens),
            'chart_data': chart_data,
        }
