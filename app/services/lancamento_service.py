"""Lancamento service - Financial entry management with optimized queries"""

from datetime import datetime
from typing import Optional

from app.models import Lancamento, db
from app.services.base_service import BaseService
from app.utils.dates import parse_date


class LancamentoService(BaseService):
    """Service for financial entry CRUD and optimized queries"""

    @staticmethod
    def criar_lancamento(empresa_id: int, dados: dict) -> tuple[Lancamento | None, str | None]:
        """Create new financial entry. Returns (lancamento, error_message)"""
        try:
            # Validate valor
            valor = dados.get('valor', 0)
            if valor < 0:
                return None, 'Valor não pode ser negativo.'

            # Parse date using helper
            data = parse_date(dados.get('data'))

            lancamento = Lancamento(
                empresa_id=empresa_id,
                obra_id=dados.get('obra_id'),
                descricao=dados.get('descricao', '').strip(),
                categoria=dados.get('categoria'),
                tipo=dados.get('tipo'),
                valor=valor,
                data=data,
                forma_pagamento=dados.get('forma_pagamento'),
                status_pagamento=dados.get('status_pagamento'),
                parcelas=dados.get('parcelas'),
                observacoes=dados.get('observacoes'),
                documento=dados.get('documento'),
            )
            db.session.add(lancamento)
            db.session.commit()
            return lancamento, None
        except Exception as e:
            db.session.rollback()
            return None, f'Erro ao criar lançamento: {e!s}'

    @staticmethod
    def editar_lancamento(
        lancamento_id: int, empresa_id: int, dados: dict
    ) -> tuple[Lancamento | None, str | None]:
        """Update financial entry. Returns (lancamento, error_message)"""
        lancamento = Lancamento.query.filter_by(id=lancamento_id, empresa_id=empresa_id).first()
        if not lancamento:
            return None, 'Lançamento não encontrado.'

        # Validate valor if provided
        if 'valor' in dados:
            if dados['valor'] < 0:
                return None, 'Valor não pode ser negativo.'
            lancamento.valor = dados['valor']

        # Update fields
        if 'obra_id' in dados:
            lancamento.obra_id = dados['obra_id']
        if 'descricao' in dados:
            lancamento.descricao = dados['descricao'].strip()
        if 'categoria' in dados:
            lancamento.categoria = dados['categoria']
        if 'tipo' in dados:
            lancamento.tipo = dados['tipo']
        if 'forma_pagamento' in dados:
            lancamento.forma_pagamento = dados['forma_pagamento']
        if 'status_pagamento' in dados:
            lancamento.status_pagamento = dados['status_pagamento']
        if 'parcelas' in dados:
            lancamento.parcelas = dados['parcelas']
        if 'observacoes' in dados:
            lancamento.observacoes = dados['observacoes']
        if 'documento' in dados:
            lancamento.documento = dados['documento']

        # Parse and update date
        if dados.get('data'):
            data = parse_date(dados['data'])
            if data:
                lancamento.data = data

        db.session.commit()
        return lancamento, None

    @staticmethod
    def excluir_lancamento(lancamento_id: int, empresa_id: int) -> tuple[bool, str | None]:
        """Delete financial entry. Returns (success, error_message)"""
        lancamento = Lancamento.query.filter_by(id=lancamento_id, empresa_id=empresa_id).first()
        if not lancamento:
            return False, 'Lançamento não encontrado.'

        db.session.delete(lancamento)
        db.session.commit()
        return True, None

    @staticmethod
    def build_filtered_query(empresa_id: int, filtros: dict | None = None):
        """Build query with filters applied. Returns query object"""
        if filtros is None:
            filtros = {}

        query = Lancamento.query.filter_by(empresa_id=empresa_id)

        if filtros.get('obra_id'):
            query = query.filter_by(obra_id=int(filtros['obra_id']))
        if filtros.get('tipo'):
            query = query.filter_by(tipo=filtros['tipo'])
        if filtros.get('categoria'):
            query = query.filter_by(categoria=filtros['categoria'])
        if filtros.get('status_pagamento'):
            query = query.filter_by(status_pagamento=filtros['status_pagamento'])
        if filtros.get('data_inicio'):
            data = parse_date(filtros['data_inicio'])
            if data:
                query = query.filter(Lancamento.data >= data)
        if filtros.get('data_fim'):
            data = parse_date(filtros['data_fim'])
            if data:
                query = query.filter(Lancamento.data <= data)
        if filtros.get('busca'):
            query = query.filter(Lancamento.descricao.ilike(f'%{filtros["busca"]}%'))

        return query.order_by(Lancamento.data.desc())

    @staticmethod
    def get_financial_summary(
        empresa_id: int,
        data_inicio: str | None = None,
        data_fim: str | None = None,
        obra_id: int | None = None,
    ) -> dict:
        """
        Get financial summary using SQL aggregation (efficient).
        Returns dict with receitas, despesas, saldo
        """
        query = Lancamento.query.filter_by(empresa_id=empresa_id)

        if obra_id:
            query = query.filter_by(obra_id=obra_id)
        if data_inicio:
            data = parse_date(data_inicio)
            if data:
                query = query.filter(Lancamento.data >= data)
        if data_fim:
            data = parse_date(data_fim)
            if data:
                query = query.filter(Lancamento.data <= data)

        # Use SQL aggregation instead of Python sum (much more efficient)
        result = (
            db.session.query(
                db.func.sum(
                    db.case((Lancamento.tipo == 'Receita', Lancamento.valor), else_=0)
                ).label('total_receitas'),
                db.func.sum(
                    db.case((Lancamento.tipo == 'Despesa', Lancamento.valor), else_=0)
                ).label('total_despesas'),
            )
            .filter(Lancamento.id.in_(query.with_entities(Lancamento.id).subquery()))
            .first()
        )

        receitas = result.total_receitas or 0
        despesas = result.total_despesas or 0

        return {
            'receitas': receitas,
            'despesas': despesas,
            'saldo': receitas - despesas,
        }

    @staticmethod
    def get_by_categoria(
        empresa_id: int, data_inicio: str | None = None, data_fim: str | None = None
    ) -> list[dict]:
        """Get expenses grouped by categoria using SQL aggregation"""
        query = Lancamento.query.filter_by(empresa_id=empresa_id, tipo='Despesa')

        if data_inicio:
            data = parse_date(data_inicio)
            if data:
                query = query.filter(Lancamento.data >= data)
        if data_fim:
            data = parse_date(data_fim)
            if data:
                query = query.filter(Lancamento.data <= data)

        results = (
            db.session.query(
                Lancamento.categoria,
                db.func.count(Lancamento.id).label('quantidade'),
                db.func.sum(Lancamento.valor).label('total'),
            )
            .filter(Lancamento.id.in_(query.with_entities(Lancamento.id).subquery()))
            .group_by(Lancamento.categoria)
            .order_by(db.func.sum(Lancamento.valor).desc())
            .all()
        )

        return [
            {
                'categoria': row.categoria or 'Sem categoria',
                'quantidade': row.quantidade,
                'total': row.total,
            }
            for row in results
        ]

    @staticmethod
    def get_pending_payments(empresa_id: int) -> list[Lancamento]:
        """Get lancamentos with pending payment status"""
        return (
            Lancamento.query.filter_by(empresa_id=empresa_id, status_pagamento='Pendente')
            .order_by(Lancamento.data)
            .all()
        )

    @staticmethod
    def get_overdue_payments(empresa_id: int) -> list[Lancamento]:
        """Get payments that are past due date"""
        from datetime import date

        return (
            Lancamento.query.filter(
                Lancamento.empresa_id == empresa_id,
                Lancamento.status_pagamento == 'Pendente',
                Lancamento.data < date.today(),
            )
            .order_by(Lancamento.data)
            .all()
        )
