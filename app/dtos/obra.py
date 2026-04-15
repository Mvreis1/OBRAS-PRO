"""DTOs para Obra (Project/Construction Site)"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from app.dtos.base import BaseDTO


@dataclass
class ObraCreateDTO(BaseDTO):
    """DTO for creating a new obra"""

    nome: str
    descricao: str | None = None
    endereco: str | None = None
    orcamento_previsto: float = 0.0
    data_inicio: str | None = None
    data_fim_prevista: str | None = None
    status: str = 'Planejamento'
    responsavel: str | None = None
    cliente: str | None = None

    def validate(self) -> str | None:
        """Validate DTO fields. Returns error message or None"""
        if not self.nome or not self.nome.strip():
            return 'Nome é obrigatório.'
        if self.orcamento_previsto < 0:
            return 'Orçamento não pode ser negativo.'
        if self.status not in ['Planejamento', 'Em Andamento', 'Concluída', 'Paralisada']:
            return 'Status inválido.'
        return None


@dataclass
class ObraUpdateDTO(BaseDTO):
    """DTO for updating an existing obra"""

    nome: str | None = None
    descricao: str | None = None
    endereco: str | None = None
    orcamento_previsto: float | None = None
    data_inicio: str | None = None
    data_fim_prevista: str | None = None
    data_fim_real: str | None = None
    status: str | None = None
    progresso: int | None = None
    responsavel: str | None = None
    cliente: str | None = None

    def validate(self) -> str | None:
        """Validate DTO fields. Returns error message or None"""
        if self.nome is not None and not self.nome.strip():
            return 'Nome não pode ser vazio.'
        if self.orcamento_previsto is not None and self.orcamento_previsto < 0:
            return 'Orçamento não pode ser negativo.'
        if self.progresso is not None and not (0 <= self.progresso <= 100):
            return 'Progresso deve estar entre 0 e 100.'
        if self.status is not None and self.status not in [
            'Planejamento',
            'Em Andamento',
            'Concluída',
            'Paralisada',
        ]:
            return 'Status inválido.'
        return None


@dataclass
class ObraResponseDTO(BaseDTO):
    """DTO for obra response data"""

    id: int
    empresa_id: int
    nome: str
    descricao: str | None = None
    endereco: str | None = None
    orcamento_previsto: float = 0.0
    data_inicio: str | None = None
    data_fim_prevista: str | None = None
    data_fim_real: str | None = None
    status: str = 'Planejamento'
    progresso: int = 0
    responsavel: str | None = None
    cliente: str | None = None
    total_gasto: float = 0.0
    total_receita: float = 0.0
    saldo: float = 0.0
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_model(cls, obra, include_totals: bool = True) -> 'ObraResponseDTO':
        """Create DTO from Obra model instance"""
        data = {
            'id': obra.id,
            'empresa_id': obra.empresa_id,
            'nome': obra.nome,
            'descricao': obra.descricao,
            'endereco': obra.endereco,
            'orcamento_previsto': obra.orcamento_previsto or 0.0,
            'data_inicio': obra.data_inicio.isoformat() if obra.data_inicio else None,
            'data_fim_prevista': obra.data_fim_prevista.isoformat()
            if obra.data_fim_prevista
            else None,
            'data_fim_real': obra.data_fim_real.isoformat() if obra.data_fim_real else None,
            'status': obra.status or 'Planejamento',
            'progresso': obra.progresso or 0,
            'responsavel': obra.responsavel,
            'cliente': obra.cliente,
            'created_at': obra.created_at.isoformat() if obra.created_at else None,
            'updated_at': obra.updated_at.isoformat() if obra.updated_at else None,
        }

        if include_totals:
            # Try to get computed values from obra.to_dict()
            obra_dict = obra.to_dict(include_totals=True)
            data['total_gasto'] = obra_dict.get('total_gasto', 0.0)
            data['total_receita'] = obra_dict.get('total_receita', 0.0)
            data['saldo'] = obra_dict.get('saldo', 0.0)
        else:
            data['total_gasto'] = 0.0
            data['total_receita'] = 0.0
            data['saldo'] = 0.0

        return cls(**data)


@dataclass
class ObraResumoDTO(BaseDTO):
    """DTO for obra summary/list view (lighter weight)"""

    id: int
    nome: str
    status: str
    progresso: int
    orcamento_previsto: float
    data_fim_prevista: str | None = None
    responsavel: str | None = None
    cliente: str | None = None
    total_gasto: float = 0.0
    saldo: float = 0.0

    @classmethod
    def from_model(cls, obra) -> 'ObraResumoDTO':
        """Create DTO from Obra model instance"""
        obra_dict = obra.to_dict(include_totals=True)
        return cls(
            id=obra.id,
            nome=obra.nome,
            status=obra.status or 'Planejamento',
            progresso=obra.progresso or 0,
            orcamento_previsto=obra.orcamento_previsto or 0.0,
            data_fim_prevista=obra.data_fim_prevista.isoformat()
            if obra.data_fim_prevista
            else None,
            responsavel=obra.responsavel,
            cliente=obra.cliente,
            total_gasto=obra_dict.get('total_gasto', 0.0),
            saldo=obra_dict.get('saldo', 0.0),
        )


@dataclass
class ObraFiltrosDTO(BaseDTO):
    """DTO for obra search/filter parameters"""

    status: str | None = None
    responsavel: str | None = None
    cliente: str | None = None
    data_inicio: str | None = None
    data_fim: str | None = None
    search_term: str | None = None
    page: int = 1
    per_page: int = 20
