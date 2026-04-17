"""Obra service - Project management business logic"""

from datetime import date, datetime
from typing import Optional

from app.models import Empresa, Lancamento, Obra, db
from app.services.base_service import BaseService


class ObraService(BaseService):
    """Service for project CRUD, limits, and queries"""

    @staticmethod
    def verificar_limite_obras(empresa_id: int) -> tuple[bool, int, int]:
        """Check if empresa can create more projects. Returns (can_create, current, max)"""
        empresa = db.session.get(Empresa, empresa_id)
        if not empresa:
            return False, 0, 0

        current = empresa.obras.count()
        max_obras = empresa.max_obras

        return current < max_obras, current, max_obras

    @staticmethod
    def criar_obra(empresa_id: int, dados: dict) -> tuple[Obra | None, str | None]:
        """Create new project. Returns (obra, error_message)"""
        # Check limits
        can_create, _current, max_obras = ObraService.verificar_limite_obras(empresa_id)
        if not can_create:
            return None, f'Limite de obras ({max_obras}) atingido. Faça upgrade do plano.'

        # Parse dates using parse_date helper
        from app.utils.dates import parse_date

        data_inicio = parse_date(dados.get('data_inicio'))
        data_fim_prevista = parse_date(dados.get('data_fim_prevista'))

        # Validate required date
        if dados.get('data_inicio') and not data_inicio:
            return None, 'Data de início inválida.'

        # Validate budget
        orcamento_previsto = dados.get('orcamento_previsto', 0)
        if orcamento_previsto < 0:
            return None, 'Orçamento não pode ser negativo.'

        obra = Obra(
            empresa_id=empresa_id,
            nome=dados.get('nome', '').strip(),
            descricao=dados.get('descricao'),
            endereco=dados.get('endereco'),
            orcamento_previsto=orcamento_previsto,
            data_inicio=data_inicio,
            data_fim_prevista=data_fim_prevista,
            status=dados.get('status') or 'Planejamento',
            progresso=dados.get('progresso', 0),
            responsavel=dados.get('responsavel'),
            cliente=dados.get('cliente'),
        )
        db.session.add(obra)
        db.session.commit()

        return obra, None

    @staticmethod
    def editar_obra(obra_id: int, empresa_id: int, dados: dict) -> tuple[Obra | None, str | None]:
        """Update project. Returns (obra, error_message)"""
        obra = Obra.query.filter_by(id=obra_id, empresa_id=empresa_id).first()
        if not obra:
            return None, 'Obra não encontrada.'

        from app.utils.dates import parse_date

        # Update fields
        if dados.get('nome'):
            obra.nome = dados['nome'].strip()
        if 'descricao' in dados:
            obra.descricao = dados['descricao']
        if 'endereco' in dados:
            obra.endereco = dados['endereco']
        if 'orcamento_previsto' in dados:
            orc = dados['orcamento_previsto']
            if orc < 0:
                return None, 'Orçamento não pode ser negativo.'
            obra.orcamento_previsto = orc
        if 'status' in dados:
            obra.status = dados['status']
        if 'progresso' in dados:
            obra.progresso = dados['progresso']
        if 'responsavel' in dados:
            obra.responsavel = dados['responsavel']
        if 'cliente' in dados:
            obra.cliente = dados['cliente']

        # Parse and update dates
        if dados.get('data_inicio'):
            data = parse_date(dados['data_inicio'])
            if data:
                obra.data_inicio = data
        if dados.get('data_fim_prevista'):
            data = parse_date(dados['data_fim_prevista'])
            if data:
                obra.data_fim_prevista = data

        db.session.commit()
        return obra, None

    @staticmethod
    def excluir_obra(obra_id: int, empresa_id: int) -> tuple[bool, str | None]:
        """Delete project. Returns (success, error_message)"""
        obra = Obra.query.filter_by(id=obra_id, empresa_id=empresa_id).first()
        if not obra:
            return False, 'Obra não encontrada.'

        db.session.delete(obra)
        db.session.commit()
        return True, None

    @staticmethod
    def get_obra_completa(obra_id: int, empresa_id: int) -> dict | None:
        """Get obra with full financial data"""
        obra = Obra.query.filter_by(id=obra_id, empresa_id=empresa_id).first()
        if not obra:
            return None

        # Calculate totals using SQL aggregation (efficient)
        totals = (
            db.session.query(
                db.func.sum(
                    db.case((Lancamento.tipo == 'Receita', Lancamento.valor), else_=0)
                ).label('total_receitas'),
                db.func.sum(
                    db.case((Lancamento.tipo == 'Despesa', Lancamento.valor), else_=0)
                ).label('total_despesas'),
            )
            .filter(Lancamento.obra_id == obra_id)
            .first()
        )

        total_receitas = totals.total_receitas or 0
        total_despesas = totals.total_despesas or 0
        saldo = total_receitas - total_despesas

        return {
            'obra': obra,
            'total_receitas': total_receitas,
            'total_despesas': total_despesas,
            'saldo': saldo,
            'margem': (saldo / total_receitas * 100) if total_receitas > 0 else 0,
        }

    @staticmethod
    def get_obras_por_status(empresa_id: int) -> dict[str, int]:
        """Get count of obras grouped by status"""
        results = (
            db.session.query(Obra.status, db.func.count(Obra.id))
            .filter_by(empresa_id=empresa_id)
            .group_by(Obra.status)
            .all()
        )
        return dict(results)

    @staticmethod
    def get_obras_atrasadas(empresa_id: int) -> list[Obra]:
        """Get obras that are past their end date"""
        return (
            Obra.query.filter(
                Obra.empresa_id == empresa_id,
                Obra.data_fim_prevista < date.today(),
                Obra.status.notin_(['Concluída', 'Entregue']),
            )
            .order_by(Obra.data_fim_prevista)
            .all()
        )

    @staticmethod
    def get_obras_com_orcamento_estourado(empresa_id: int) -> list[dict]:
        """Get obras where expenses exceed budget"""
        from sqlalchemy import select

        # Query to get obras with their total expenses
        query = (
            db.session.query(
                Obra,
                db.func.coalesce(
                    db.func.sum(db.case((Lancamento.tipo == 'Despesa', Lancamento.valor), else_=0)),
                    0,
                ).label('total_despesas'),
            )
            .outerjoin(Lancamento, Lancamento.obra_id == Obra.id)
            .filter(Obra.empresa_id == empresa_id)
            .group_by(Obra.id)
            .having(
                db.func.sum(db.case((Lancamento.tipo == 'Despesa', Lancamento.valor), else_=0))
                > Obra.orcamento_previsto
            )
            .all()
        )

        return [
            {
                'obra': obra,
                'total_despesas': total_despesas,
                'estourado_por': total_despesas - obra.orcamento_previsto,
            }
            for obra, total_despesas in query
        ]
