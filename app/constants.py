"""
Constantes do sistema OBRAS PRO
Usar estas constantes em vez de strings hardcoded
"""

from enum import StrEnum


class StatusObra(StrEnum):
    """Status padronizados de obras"""

    PLANEJAMENTO = 'Planejamento'
    EM_EXECUCAO = 'Em Execução'
    CONCLUIDA = 'Concluída'
    ENTREGUE = 'Entregue'
    PARALISADA = 'Paralisada'
    CANCELADA = 'Cancelada'

    @classmethod
    def listar(cls):
        return [e.value for e in cls]


class TipoLancamento(StrEnum):
    """Tipos de lançamento financeiro"""

    RECEITA = 'Receita'
    DESPESA = 'Despesa'


class StatusPagamento(StrEnum):
    """Status de pagamento"""

    PAGO = 'Pago'
    PENDENTE = 'Pendente'
    VENCIDO = 'Vencido'
    CANCELADO = 'Cancelado'


class StatusContrato(StrEnum):
    """Status de contratos"""

    ATIVO = 'Ativo'
    EXPIRADO = 'Expirado'
    CANCELADO = 'Cancelado'
    RENOVADO = 'Renovado'


# Mapeamento para display (labels amigáveis)
STATUS_DISPLAY = {
    'Planejamento': 'Em Planejamento',
    'Em Execução': 'Em Execução',
    'Concluída': 'Concluída',
    'Entregue': 'Entregue',
    'Paralisada': 'Paralisada',
    'Cancelada': 'Cancelada',
}

# Cores para badges (usar em templates)
STATUS_CORES = {
    'Planejamento': 'secondary',
    'Em Execução': 'primary',
    'Concluída': 'success',
    'Entregue': 'success',
    'Paralisada': 'warning',
    'Cancelada': 'danger',
}


def normalizar_status(status):
    """Normaliza status para formato padrão"""
    if not status:
        return StatusObra.PLANEJAMENTO.value

    # Mapa de variações comuns
    variacoes = {
        'em execucao': 'Em Execução',
        'em execução': 'Em Execução',
        'Em execucao': 'Em Execução',
        'execucao': 'Em Execução',
        'concluida': 'Concluída',
        'concluído': 'Concluída',
        'entregue': 'Entregue',
        'paralisada': 'Paralisada',
        'cancelada': 'Cancelada',
        'planejamento': 'Planejamento',
        'planejada': 'Planejamento',
    }

    status_lower = status.lower().strip()
    return variacoes.get(status_lower, status)
