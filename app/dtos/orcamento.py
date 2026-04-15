"""DTOs para Orcamento (Budget/Quote)"""

from dataclasses import dataclass
from datetime import date

from app.dtos.base import BaseDTO


@dataclass
class OrcamentoCreateDTO(BaseDTO):
    """DTO for creating a new orcamento"""

    titulo: str
    cliente: str
    cliente_email: str | None = None
    cliente_telefone: str | None = None
    cliente_endereco: str | None = None
    descricao: str | None = None
    observacoes: str | None = None
    valor_materiais: float = 0.0
    valor_mao_obra: float = 0.0
    valor_equipamentos: float = 0.0
    valor_outros: float = 0.0
    desconto: float = 0.0
    prazo_execucao: int | None = None
    validade: int = 30
    forma_pagamento: str | None = None
    status: str = 'Rascunho'

    def validate(self) -> str | None:
        """Validate DTO fields. Returns error message or None"""
        if not self.titulo or not self.titulo.strip():
            return 'Título é obrigatório.'
        if not self.cliente or not self.cliente.strip():
            return 'Cliente é obrigatório.'
        if self.valor_materiais < 0:
            return 'Valor de materiais não pode ser negativo.'
        if self.valor_mao_obra < 0:
            return 'Valor de mão de obra não pode ser negativo.'
        if self.valor_equipamentos < 0:
            return 'Valor de equipamentos não pode ser negativo.'
        if self.valor_outros < 0:
            return 'Valor de outros não pode ser negativo.'
        if self.desconto < 0:
            return 'Desconto não pode ser negativo.'
        return None


@dataclass
class OrcamentoUpdateDTO(BaseDTO):
    """DTO for updating an existing orcamento"""

    titulo: str | None = None
    cliente: str | None = None
    cliente_email: str | None = None
    cliente_telefone: str | None = None
    cliente_endereco: str | None = None
    descricao: str | None = None
    observacoes: str | None = None
    valor_materiais: float | None = None
    valor_mao_obra: float | None = None
    valor_equipamentos: float | None = None
    valor_outros: float | None = None
    desconto: float | None = None
    prazo_execucao: int | None = None
    validade: int | None = None
    forma_pagamento: str | None = None
    status: str | None = None

    def validate(self) -> str | None:
        """Validate DTO fields. Returns error message or None"""
        if self.titulo is not None and not self.titulo.strip():
            return 'Título não pode ser vazio.'
        if self.valor_materiais is not None and self.valor_materiais < 0:
            return 'Valor de materiais não pode ser negativo.'
        if self.valor_mao_obra is not None and self.valor_mao_obra < 0:
            return 'Valor de mão de obra não pode ser negativo.'
        if self.valor_equipamentos is not None and self.valor_equipamentos < 0:
            return 'Valor de equipamentos não pode ser negativo.'
        if self.valor_outros is not None and self.valor_outros < 0:
            return 'Valor de outros não pode ser negativo.'
        if self.desconto is not None and self.desconto < 0:
            return 'Desconto não pode ser negativo.'
        return None


@dataclass
class OrcamentoResponseDTO(BaseDTO):
    """DTO for orcamento response data"""

    id: int
    empresa_id: int
    titulo: str
    cliente: str
    cliente_email: str | None = None
    cliente_telefone: str | None = None
    valor_materiais: float = 0.0
    valor_mao_obra: float = 0.0
    valor_equipamentos: float = 0.0
    valor_outros: float = 0.0
    desconto: float = 0.0
    valor_total: float = 0.0
    prazo_execucao: int | None = None
    validade: int = 30
    status: str = 'Rascunho'
    forma_pagamento: str | None = None
    enviado: bool = False
    data_envio: str | None = None
    visualizado: bool = False
    observacoes: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_model(cls, orcamento) -> 'OrcamentoResponseDTO':
        """Create DTO from Orcamento model instance"""
        orc_dict = orcamento.to_dict()
        return cls(
            id=orcamento.id,
            empresa_id=orcamento.empresa_id,
            titulo=orcamento.titulo,
            cliente=orcamento.cliente,
            cliente_email=orcamento.cliente_email,
            cliente_telefone=orcamento.cliente_telefone,
            valor_materiais=orcamento.valor_materiais or 0.0,
            valor_mao_obra=orcamento.valor_mao_obra or 0.0,
            valor_equipamentos=orcamento.valor_equipamentos or 0.0,
            valor_outros=orcamento.valor_outros or 0.0,
            desconto=orcamento.desconto or 0.0,
            valor_total=orc_dict.get('valor', 0.0),
            prazo_execucao=orcamento.prazo_execucao,
            validade=orcamento.validade or 30,
            status=orcamento.status or 'Rascunho',
            forma_pagamento=orcamento.forma_pagamento,
            enviado=orcamento.enviado if orcamento.enviado is not None else False,
            data_envio=orcamento.data_envio.isoformat() if orcamento.data_envio else None,
            visualizado=orcamento.visualizado if orcamento.visualizado is not None else False,
            observacoes=orcamento.observacoes,
            created_at=orcamento.created_at.isoformat() if orcamento.created_at else None,
            updated_at=orcamento.updated_at.isoformat() if orcamento.updated_at else None,
        )


@dataclass
class OrcamentoResumoDTO(BaseDTO):
    """DTO for orcamento summary/list view"""

    id: int
    titulo: str
    cliente: str
    valor_total: float
    status: str
    enviado: bool
    data_envio: str | None = None
    visualizado: bool = False
    prazo_execucao: int | None = None


@dataclass
class ItemOrcamentoCreateDTO(BaseDTO):
    """DTO for creating a budget item"""

    orcamento_id: int
    descricao: str
    categoria: str | None = None
    unidade: str = 'un'
    quantidade: float = 1.0
    valor_unitario: float = 0.0

    def validate(self) -> str | None:
        """Validate DTO fields. Returns error message or None"""
        if not self.descricao or not self.descricao.strip():
            return 'Descrição é obrigatória.'
        if self.quantidade <= 0:
            return 'Quantidade deve ser positiva.'
        if self.valor_unitario < 0:
            return 'Valor unitário não pode ser negativo.'
        return None


@dataclass
class ItemOrcamentoResponseDTO(BaseDTO):
    """DTO for budget item response"""

    id: int
    orcamento_id: int
    descricao: str
    categoria: str | None = None
    unidade: str = 'un'
    quantidade: float = 1.0
    valor_unitario: float = 0.0
    valor_total: float = 0.0

    @classmethod
    def from_model(cls, item) -> 'ItemOrcamentoResponseDTO':
        """Create DTO from ItemOrcamento model instance"""
        return cls(
            id=item.id,
            orcamento_id=item.orcamento_id,
            descricao=item.descricao,
            categoria=item.categoria,
            unidade=item.unidade or 'un',
            quantidade=item.quantidade or 1.0,
            valor_unitario=item.valor_unitario or 0.0,
            valor_total=item.valor_total
            if hasattr(item, 'valor_total')
            else (item.quantidade or 1.0) * (item.valor_unitario or 0.0),
        )


@dataclass
class OrcamentoFiltrosDTO(BaseDTO):
    """DTO for orcamento search/filter parameters"""

    status: str | None = None
    cliente: str | None = None
    enviado: bool | None = None
    search_term: str | None = None
    page: int = 1
    per_page: int = 20
