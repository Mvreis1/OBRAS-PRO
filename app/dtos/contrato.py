"""DTOs para Contrato (Contract)"""

from dataclasses import dataclass
from datetime import date

from app.dtos.base import BaseDTO


@dataclass
class ContratoCreateDTO(BaseDTO):
    """DTO for creating a new contract"""

    titulo: str
    cliente: str
    cliente_cnpj: str | None = None
    cliente_email: str | None = None
    cliente_telefone: str | None = None
    cliente_endereco: str | None = None
    descricao: str | None = None
    valor: float = 0.0
    valor_aditivo: float = 0.0
    data_inicio: str | None = None
    data_fim: str | None = None
    data_assinatura: str | None = None
    status: str = 'Rascunho'
    tipo: str = 'Prestacao de Servicos'
    obra_id: int | None = None
    observacoes: str | None = None
    num_parcelas: int = 1

    def validate(self) -> str | None:
        """Validate DTO fields. Returns error message or None"""
        if not self.titulo or not self.titulo.strip():
            return 'Título é obrigatório.'
        if not self.cliente or not self.cliente.strip():
            return 'Cliente é obrigatório.'
        if self.valor < 0:
            return 'Valor não pode ser negativo.'
        if self.num_parcelas < 1:
            return 'Número de parcelas deve ser maior que zero.'
        return None


@dataclass
class ContratoUpdateDTO(BaseDTO):
    """DTO for updating an existing contract"""

    titulo: str | None = None
    cliente: str | None = None
    cliente_cnpj: str | None = None
    cliente_email: str | None = None
    cliente_telefone: str | None = None
    cliente_endereco: str | None = None
    descricao: str | None = None
    valor: float | None = None
    valor_aditivo: float | None = None
    data_inicio: str | None = None
    data_fim: str | None = None
    data_assinatura: str | None = None
    status: str | None = None
    tipo: str | None = None
    obra_id: int | None = None
    observacoes: str | None = None

    def validate(self) -> str | None:
        """Validate DTO fields. Returns error message or None"""
        if self.titulo is not None and not self.titulo.strip():
            return 'Título não pode ser vazio.'
        if self.valor is not None and self.valor < 0:
            return 'Valor não pode ser negativo.'
        if self.status is not None and self.status not in [
            'Rascunho',
            'Ativo',
            'Concluído',
            'Cancelado',
            'Suspenso',
        ]:
            return 'Status inválido.'
        return None


@dataclass
class ContratoResponseDTO(BaseDTO):
    """DTO for contract response data"""

    id: int
    empresa_id: int
    titulo: str
    cliente: str
    cliente_cnpj: str | None = None
    cliente_email: str | None = None
    cliente_telefone: str | None = None
    valor: float = 0.0
    valor_aditivo: float = 0.0
    valor_total: float = 0.0
    data_inicio: str | None = None
    data_fim: str | None = None
    data_assinatura: str | None = None
    status: str = 'Rascunho'
    tipo: str = 'Prestacao de Servicos'
    obra_id: int | None = None
    obra_nome: str | None = None
    observacoes: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_model(cls, contrato) -> 'ContratoResponseDTO':
        """Create DTO from Contrato model instance"""
        contrato_dict = contrato.to_dict()
        return cls(
            id=contrato.id,
            empresa_id=contrato.empresa_id,
            titulo=contrato.titulo,
            cliente=contrato.cliente,
            cliente_cnpj=contrato.cliente_cnpj,
            cliente_email=contrato.cliente_email,
            cliente_telefone=contrato.cliente_telefone,
            valor=contrato.valor or 0.0,
            valor_aditivo=contrato.valor_aditivo or 0.0,
            valor_total=contrato_dict.get('valor_total', 0.0),
            data_inicio=contrato.data_inicio.isoformat() if contrato.data_inicio else None,
            data_fim=contrato.data_fim.isoformat() if contrato.data_fim else None,
            data_assinatura=contrato.data_assinatura.isoformat()
            if contrato.data_assinatura
            else None,
            status=contrato.status or 'Rascunho',
            tipo=contrato.tipo or 'Prestacao de Servicos',
            obra_id=contrato.obra_id,
            obra_nome=contrato.obra.nome if contrato.obra else None,
            observacoes=contrato.observacoes,
            created_at=contrato.created_at.isoformat() if contrato.created_at else None,
            updated_at=contrato.updated_at.isoformat() if contrato.updated_at else None,
        )


@dataclass
class ContratoResumoDTO(BaseDTO):
    """DTO for contract summary/list view"""

    id: int
    titulo: str
    cliente: str
    valor: float
    valor_total: float
    status: str
    data_inicio: str | None = None
    data_fim: str | None = None
    parcelas_total: int = 0
    parcelas_pagas: int = 0

    @classmethod
    def from_model(cls, contrato, parcelas_info: dict | None = None) -> 'ContratoResumoDTO':
        """Create DTO from Contrato model instance"""
        contrato_dict = contrato.to_dict()
        parcelas = parcelas_info or {}
        return cls(
            id=contrato.id,
            titulo=contrato.titulo,
            cliente=contrato.cliente,
            valor=contrato.valor or 0.0,
            valor_total=contrato_dict.get('valor_total', 0.0),
            status=contrato.status or 'Rascunho',
            data_inicio=contrato.data_inicio.isoformat() if contrato.data_inicio else None,
            data_fim=contrato.data_fim.isoformat() if contrato.data_fim else None,
            parcelas_total=parcelas.get('total', 0),
            parcelas_pagas=parcelas.get('pagas', 0),
        )


@dataclass
class ParcelaContratoResponseDTO(BaseDTO):
    """DTO for contract installment response"""

    id: int
    empresa_id: int
    contrato_id: int
    numero: int
    valor: float
    data_vencimento: str
    data_pagamento: str | None = None
    status: str = 'Pendente'
    descricao: str | None = None

    @classmethod
    def from_model(cls, parcela) -> 'ParcelaContratoResponseDTO':
        """Create DTO from ParcelaContrato model instance"""
        parcela.to_dict()
        return cls(
            id=parcela.id,
            empresa_id=parcela.empresa_id,
            contrato_id=parcela.contrato_id,
            numero=parcela.numero,
            valor=parcela.valor,
            data_vencimento=parcela.data_vencimento.isoformat()
            if parcela.data_vencimento
            else None,
            data_pagamento=parcela.data_pagamento.isoformat() if parcela.data_pagamento else None,
            status=parcela.status or 'Pendente',
            descricao=parcela.descricao,
        )


@dataclass
class ContratoFiltrosDTO(BaseDTO):
    """DTO for contract search/filter parameters"""

    status: str | None = None
    tipo: str | None = None
    cliente: str | None = None
    obra_id: int | None = None
    data_inicio: str | None = None
    data_fim: str | None = None
    search_term: str | None = None
    page: int = 1
    per_page: int = 20


@dataclass
class ContratoVencimentoDTO(BaseDTO):
    """DTO for contracts nearing expiration"""

    id: int
    titulo: str
    cliente: str
    data_fim: str
    dias_restantes: int
    valor: float
