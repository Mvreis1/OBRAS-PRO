"""DTOs para Banco (Bank Account)"""

from dataclasses import dataclass

from app.dtos.base import BaseDTO


@dataclass
class ContaBancariaCreateDTO(BaseDTO):
    """DTO for creating a new bank account"""

    nome: str
    banco: str | None = None
    agencia: str | None = None
    conta: str | None = None
    tipo: str = 'Corrente'
    titular: str | None = None
    saldo_inicial: float = 0.0
    observacoes: str | None = None

    def validate(self) -> str | None:
        """Validate DTO fields. Returns error message or None"""
        if not self.nome or not self.nome.strip():
            return 'Nome da conta é obrigatório.'
        return None


@dataclass
class ContaBancariaUpdateDTO(BaseDTO):
    """DTO for updating an existing bank account"""

    nome: str | None = None
    banco: str | None = None
    agencia: str | None = None
    conta: str | None = None
    tipo: str | None = None
    titular: str | None = None
    observacoes: str | None = None
    ativo: bool | None = None

    def validate(self) -> str | None:
        """Validate DTO fields. Returns error message or None"""
        if self.nome is not None and not self.nome.strip():
            return 'Nome da conta não pode ser vazio.'
        return None


@dataclass
class ContaBancariaResponseDTO(BaseDTO):
    """DTO for bank account response data"""

    id: int
    empresa_id: int
    nome: str
    banco: str | None = None
    agencia: str | None = None
    conta: str | None = None
    tipo: str = 'Corrente'
    titular: str | None = None
    saldo_inicial: float = 0.0
    saldo_atual: float = 0.0
    ativo: bool = True
    observacoes: str | None = None
    created_at: str | None = None

    @classmethod
    def from_model(cls, conta) -> 'ContaBancariaResponseDTO':
        """Create DTO from ContaBancaria model instance"""
        conta.to_dict()
        return cls(
            id=conta.id,
            empresa_id=conta.empresa_id,
            nome=conta.nome,
            banco=conta.banco,
            agencia=conta.agencia,
            conta=conta.conta,
            tipo=conta.tipo or 'Corrente',
            titular=conta.titular,
            saldo_inicial=conta.saldo_inicial or 0.0,
            saldo_atual=conta.saldo_atual or 0.0,
            ativo=conta.ativo if conta.ativo is not None else True,
            observacoes=conta.observacoes,
            created_at=conta.created_at.isoformat() if conta.created_at else None,
        )


@dataclass
class ContaBancariaResumoDTO(BaseDTO):
    """DTO for bank account with balance summary"""

    id: int
    nome: str
    banco: str | None = None
    agencia: str | None = None
    conta: str | None = None
    tipo: str = 'Corrente'
    saldo_inicial: float = 0.0
    saldo_atual: float = 0.0
    total_entradas: float = 0.0
    total_saidas: float = 0.0


@dataclass
class LancamentoContaCreateDTO(BaseDTO):
    """DTO for creating a bank account transaction"""

    conta_id: int
    descricao: str
    tipo: str  # 'entrada' or 'saida'
    valor: float
    data: str
    categoria: str | None = None
    documento: str | None = None
    forma_pagamento: str | None = None

    def validate(self) -> str | None:
        """Validate DTO fields. Returns error message or None"""
        if not self.descricao or not self.descricao.strip():
            return 'Descrição é obrigatória.'
        if self.tipo not in ['entrada', 'saida']:
            return 'Tipo deve ser entrada ou saida.'
        if self.valor <= 0:
            return 'Valor deve ser positivo.'
        return None


@dataclass
class LancamentoContaResponseDTO(BaseDTO):
    """DTO for bank account transaction response"""

    id: int
    empresa_id: int
    conta_id: int
    conta_nome: str
    descricao: str
    tipo: str
    valor: float
    data: str
    documento: str | None = None
    categoria: str | None = None
    created_at: str | None = None

    @classmethod
    def from_model(cls, lancamento) -> 'LancamentoContaResponseDTO':
        """Create DTO from LancamentoConta model instance"""
        lanc_dict = lancamento.to_dict()
        return cls(
            id=lancamento.id,
            empresa_id=lancamento.empresa_id,
            conta_id=lancamento.conta_id,
            conta_nome=lanc_dict.get('conta_nome', ''),
            descricao=lancamento.descricao,
            tipo=lancamento.tipo,
            valor=lancamento.valor,
            data=lancamento.data.isoformat() if lancamento.data else None,
            documento=lancamento.documento,
            categoria=lancamento.categoria,
            created_at=lancamento.created_at.isoformat() if lancamento.created_at else None,
        )


@dataclass
class TransferenciaCreateDTO(BaseDTO):
    """DTO for creating a transfer between bank accounts"""

    conta_origem_id: int
    conta_destino_id: int
    valor: float
    descricao: str
    data: str | None = None

    def validate(self) -> str | None:
        """Validate DTO fields. Returns error message or None"""
        if self.conta_origem_id == self.conta_destino_id:
            return 'Contas devem ser diferentes.'
        if self.valor <= 0:
            return 'Valor deve ser positivo.'
        if not self.descricao or not self.descricao.strip():
            return 'Descrição é obrigatória.'
        return None


@dataclass
class ExtratoDTO(BaseDTO):
    """DTO for bank statement entry"""

    id: int
    descricao: str
    tipo: str
    valor: float
    data: str
    saldo_apos: float
    documento: str | None = None
    categoria: str | None = None
