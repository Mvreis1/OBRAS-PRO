"""Obra Alerta service - Project alert generation"""

from datetime import date

from app.models import Lancamento


class ObraAlertaService:
    """Service for generating project alerts based on budget and schedule"""

    NIVEL_CRITICO_ORCAMENTO = 90  # 90% budget spent
    NIVEL_ALERTA_ORCAMENTO = 70  # 70% budget spent

    @staticmethod
    def gerar_alertas_obras(obras, empresa_id):
        """Generate alerts for a list of obras. Returns list of alert dicts"""
        alertas = []

        for obra in obras:
            # Calculate totals efficiently with single query
            result = (
                Lancamento.query.with_entities(
                    Lancamento.tipo,
                    Lancamento.valor,
                )
                .filter(Lancamento.obra_id == obra.id, Lancamento.empresa_id == empresa_id)
                .all()
            )

            total_despesas = sum(l.valor for l in result if l.tipo == 'Despesa')

            alertas_obra = ObraAlertaService._avaliar_obra(obra, total_despesas)
            alertas.extend(alertas_obra)

        return alertas

    @staticmethod
    def _avaliar_obra(obra, total_despesas):
        """Evaluate single obra and return alerts"""
        alertas = []

        # Budget overrun alert
        percentual_gasto = (
            (total_despesas / obra.orcamento_previsto * 100) if obra.orcamento_previsto > 0 else 0
        )

        if percentual_gasto >= ObraAlertaService.NIVEL_CRITICO_ORCAMENTO:
            alertas.append(
                {
                    'obra_id': obra.id,
                    'obra_nome': obra.nome,
                    'nivel': 'critico',
                    'icon': 'bi bi-exclamation-octagon-fill',
                    'cor': '#ef4444',
                    'mensagem': f'Estouro! {percentual_gasto:.0f}%',
                    'percentual': percentual_gasto,
                }
            )
        elif percentual_gasto >= ObraAlertaService.NIVEL_ALERTA_ORCAMENTO:
            alertas.append(
                {
                    'obra_id': obra.id,
                    'obra_nome': obra.nome,
                    'nivel': 'alerta',
                    'icon': 'bi bi-exclamation-triangle-fill',
                    'cor': '#f59e0b',
                    'mensagem': f'Atenção! {percentual_gasto:.0f}%',
                    'percentual': percentual_gasto,
                }
            )

        # Overdue project alert
        if (
            obra.data_fim_prevista
            and obra.data_fim_prevista < date.today()
            and obra.status != 'Concluída'
        ):
            alertas.append(
                {
                    'obra_id': obra.id,
                    'obra_nome': obra.nome,
                    'nivel': 'critico',
                    'icon': 'bi bi-exclamation-octagon-fill',
                    'cor': '#ef4444',
                    'mensagem': 'Atrasada',
                    'percentual': percentual_gasto,
                }
            )

        # Suspended project alert
        if obra.status == 'Paralisada':
            alertas.append(
                {
                    'obra_id': obra.id,
                    'obra_nome': obra.nome,
                    'nivel': 'alerta',
                    'icon': 'bi bi-pause-circle-fill',
                    'cor': '#f59e0b',
                    'mensagem': 'Paralisada',
                    'percentual': percentual_gasto,
                }
            )

        return alertas

    @staticmethod
    def avaliar_status_orcamentario(obra, total_despesas):
        """Return budget status dict for single obra"""
        percentual_gasto = (
            (total_despesas / obra.orcamento_previsto * 100) if obra.orcamento_previsto > 0 else 0
        )

        if percentual_gasto >= ObraAlertaService.NIVEL_CRITICO_ORCAMENTO:
            nivel = 'critico'
        elif percentual_gasto >= ObraAlertaService.NIVEL_ALERTA_ORCAMENTO:
            nivel = 'alerta'
        else:
            nivel = 'normal'

        return {
            'percentual': percentual_gasto,
            'nivel': nivel,
            'total_despesas': total_despesas,
        }
