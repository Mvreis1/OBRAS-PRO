"""DTOs para Lancamento (Financial Transaction)"""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.dtos.base import BaseDTO


@dataclass
class LancamentoCreateDTO(BaseDTO):
    """DTO for creating a new lancamento"""

    obra_id: int
    descricao: str
    categoria: str
    tipo: str  # 'Receita' or 'Despesa'
    valor: float
    data: str
    forma_pagamento: str | None = None
    status_pagamento: str = 'Pago'
    parcelas: int = 1
    observacoes: str | None = None
    documento: str | None = None

    def validate(self) -> str | None:
        """Validate DTO fields. Returns error message or None"""
        if not self.descricao or not self.descricao.strip():
            return 'Descrição é obrigatória.'
        if not self.categoria or not self.categoria.strip():
            return 'Categoria é obrigatória.'
        if self.tipo not in ['Receita', 'Despesa']:
            return 'Tipo deve ser Receita ou Despesa.'
        if self.valor <= 0:
            return 'Valor deve ser positivo.'
        if self.parcelas < 1:
            return 'Parcelas deve ser maior que zero.'
        return None


@dataclass
class LancamentoUpdateDTO(BaseDTO):
    """DTO for updating an existing lancamento"""

    descricao: str | None = None
    categoria: str | None = None
    tipo: str | None = None
    valor: float | None = None
    data: str | None = None
    forma_pagamento: str | None = None
    status_pagamento: str | None = None
    parcelas: int | None = None
    observacoes: str | None = None
    documento: str | None = None

    def validate(self) -> str | None:
        """Validate DTO fields. Returns error message or None"""
        if self.descricao is not None and not self.descricao.strip():
            return 'Descrição não pode ser vazia.'
        if self.tipo is not None and self.tipo not in ['Receita', 'Despesa']:
            return 'Tipo deve ser Receita ou Despesa.'
        if self.valor is not None and self.valor <= 0:
            return 'Valor deve ser positivo.'
        if self.parcelas is not None and self.parcelas < 1:
            return 'Parcelas deve ser maior que zero.'
        if self.status_pagamento is not None and self.status_pagamento not in [
            'Pago',
            'Pendente',
            'Atrasado',
        ]:
            return 'Status de pagamento inválido.'
        return None


@dataclass
class LancamentoResponseDTO(BaseDTO):
    """DTO for lancamento response data"""

    id: int
    empresa_id: int
    obra_id: int
    obra_nome: str
    descricao: str
    categoria: str
    tipo: str
    valor: float
    data: str
    forma_pagamento: str | None = None
    status_pagamento: str = 'Pago'
    parcelas: int = 1
    observacoes: str | None = None
    documento: str | None = None
    created_at: str | None = None

    @classmethod
    def from_model(cls, lancamento) -> 'LancamentoResponseDTO':
        """Create DTO from Lancamento model instance"""
        lanc_dict = lancamento.to_dict()
        return cls(
            id=lancamento.id,
            empresa_id=lancamento.empresa_id,
            obra_id=lancamento.obra_id,
            obra_nome=lanc_dict.get('obra_nome', ''),
            descricao=lancamento.descricao,
            categoria=lancamento.categoria,
            tipo=lancamento.tipo,
            valor=lancamento.valor,
            data=lancamento.data.isoformat() if lancamento.data else None,
            forma_pagamento=lancamento.forma_pagamento,
            status_pagamento=lancamento.status_pagamento or 'Pago',
            parcelas=lancamento.parcelas or 1,
            observacoes=lancamento.observacoes,
            documento=lancamento.documento,
            created_at=lancamento.created_at.isoformat() if lancamento.created_at else None,
        )


@dataclass
class LancamentoFiltrosDTO(BaseDTO):
    """DTO for lancamento search/filter parameters"""

    obra_id: int | None = None
    tipo: str | None = None
    categoria: str | None = None
    status_pagamento: str | None = None
    data_inicio: str | None = None
    data_fim: str | None = None
    search_term: str | None = None
    page: int = 1
    per_page: int = 20


@dataclass
class LancamentoResumoDTO(BaseDTO):
    """DTO for financial summary of a period/obra"""

    total_receitas: float = 0.0
    total_despesas: float = 0.0
    saldo: float = 0.0
    qtd_receitas: int = 0
    qtd_despesas: int = 0
    qtd_pendentes: int = 0
    qtd_atrasadas: int = 0
