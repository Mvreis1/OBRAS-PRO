"""Relatorio service - Financial reporting"""

from datetime import date, datetime, timedelta

from sqlalchemy import func

from app.models import Lancamento, Obra, db


class RelatorioService:
    """Service for financial reports and analytics"""

    @staticmethod
    def get_relatorio_geral(empresa_id, data_inicio=None, data_fim=None, obra_id=None):
        """Get general financial report. Returns dict with all report data"""
        query = Lancamento.query.filter_by(empresa_id=empresa_id)

        if obra_id:
            query = query.filter_by(obra_id=int(obra_id))
        if data_inicio:
            query = query.filter(
                Lancamento.data >= datetime.strptime(data_inicio, '%Y-%m-%d').date()
            )
        if data_fim:
            query = query.filter(Lancamento.data <= datetime.strptime(data_fim, '%Y-%m-%d').date())

        lancamentos = query.all()
        total_receitas = sum(l.valor for l in lancamentos if l.tipo == 'Receita')
        total_despesas = sum(l.valor for l in lancamentos if l.tipo == 'Despesa')
        lucro_prejuizo = total_receitas - total_despesas

        margem_geral = (lucro_prejuizo / total_receitas) * 100 if total_receitas > 0 else None

        return {
            'lancamentos': lancamentos,
            'total_receitas': total_receitas,
            'total_despesas': total_despesas,
            'lucro_prejuizo': lucro_prejuizo,
            'margem_geral': margem_geral,
        }

    @staticmethod
    def calcular_lucro_por_obra(empresa_id, data_inicio=None, data_fim=None):
        """Calculate profitability per project. Returns list of dicts"""
        obras = Obra.query.filter_by(empresa_id=empresa_id).all()
        lucro_obras = []

        for obra in obras:
            lancs_obra = Lancamento.query.filter(
                Lancamento.obra_id == obra.id, Lancamento.empresa_id == empresa_id
            )

            if data_inicio:
                lancs_obra = lancs_obra.filter(
                    Lancamento.data >= datetime.strptime(data_inicio, '%Y-%m-%d').date()
                )
            if data_fim:
                lancs_obra = lancs_obra.filter(
                    Lancamento.data <= datetime.strptime(data_fim, '%Y-%m-%d').date()
                )

            lancamentos = lancs_obra.all()
            receita = sum(l.valor for l in lancamentos if l.tipo == 'Receita')
            despesa = sum(l.valor for l in lancamentos if l.tipo == 'Despesa')
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
        """Calculate monthly evolution. Returns list of dicts for last N months"""
        evolucao_mensal = []

        for i in range(meses - 1, -1, -1):
            mes = (date.today().replace(day=1) - timedelta(days=i * 30)).replace(day=1)
            mes_fim = (mes + timedelta(days=32)).replace(day=1)

            lancs_mes = Lancamento.query.filter(
                Lancamento.empresa_id == empresa_id,
                Lancamento.data >= mes,
                Lancamento.data < mes_fim,
            ).all()

            receita = sum(l.valor for l in lancs_mes if l.tipo == 'Receita')
            despesa = sum(l.valor for l in lancs_mes if l.tipo == 'Despesa')

            nome_mes = mes.strftime('%b/%Y')
            evolucao_mensal.append(
                {
                    'mes': nome_mes,
                    'receita': receita,
                    'despesa': despesa,
                    'saldo': receita - despesa,
                }
            )

        return evolucao_mensal

    @staticmethod
    def calcular_orcamento_vs_realizado(empresa_id, data_inicio=None, data_fim=None):
        """Compare budget vs actual per project. Returns dict with data"""
        obras = Obra.query.filter_by(empresa_id=empresa_id).all()

        orcamento_obras = []
        total_orcamento = 0
        total_realizado = 0
        grafico_labels = []
        grafico_orcamento = []
        grafico_realizado = []

        for obra in obras:
            lancs = Lancamento.query.filter(
                Lancamento.obra_id == obra.id,
                Lancamento.empresa_id == empresa_id,
                Lancamento.tipo == 'Despesa',
            )

            if data_inicio:
                lancs = lancs.filter(
                    Lancamento.data >= datetime.strptime(data_inicio, '%Y-%m-%d').date()
                )
            if data_fim:
                lancs = lancs.filter(
                    Lancamento.data <= datetime.strptime(data_fim, '%Y-%m-%d').date()
                )

            lancamentos = lancs.all()
            realizado = sum(l.valor for l in lancamentos)
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
        """Calculate expenses by category. Returns list of dicts"""
        query = (
            db.session.query(Lancamento.categoria, func.sum(Lancamento.valor).label('total'))
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
        total_realizado = sum(c[1] for c in categorias_db)

        if total_realizado > 0:
            return [
                {
                    'categoria': c[0],
                    'valor': c[1],
                    'percentual': (c[1] / total_realizado) * 100,
                }
                for c in categorias_db
            ]
        return []

    @staticmethod
    def get_estatisticas_gerais(empresa_id):
        """Get general statistics. Returns dict"""
        from app.constants import StatusObra

        obras_ativas = Obra.query.filter_by(
            empresa_id=empresa_id, status=StatusObra.EM_EXECUCAO.value
        ).count()

        lancamentos_count = Lancamento.query.filter_by(empresa_id=empresa_id).count()

        categorias_count = (
            len(
                set(
                    Lancamento.query.filter_by(empresa_id=empresa_id)
                    .with_entities(Lancamento.categoria)
                    .all()
                )
            )
            if lancamentos_count > 0
            else 0
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
