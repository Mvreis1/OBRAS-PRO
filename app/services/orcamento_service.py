"""Orcamento service - Budget management"""

import json

from app.models import ItemOrcamento, Orcamento, db


class OrcamentoService:
    """Service for budget CRUD and operations"""

    @staticmethod
    def criar_orcamento(empresa_id, dados, itens_json):
        """Create new budget with items. Returns (orcamento, error_message)"""
        try:
            # Parse dates
            data_validade = None
            if dados.get('data_validade'):
                from datetime import datetime

                try:
                    data_validade = datetime.strptime(dados['data_validade'], '%Y-%m-%d').date()
                except ValueError:
                    return None, 'Data de validade inválida.'

            # Create budget
            orcamento = Orcamento(
                empresa_id=empresa_id,
                cliente=dados.get('cliente', 'Cliente sem nome'),
                titulo=dados.get('titulo') or dados.get('descricao') or 'Orçamento sem título',
                descricao=dados.get('descricao'),
                status=dados.get('status') or 'Rascunho',
                validade=data_validade,
                observacoes=dados.get('observacoes'),
            )
            db.session.add(orcamento)
            db.session.flush()

            # Add items from JSON
            if itens_json:
                OrcamentoService.adicionar_itens(orcamento.id, itens_json)

            # Calculate total
            OrcamentoService.calcular_valor_total(orcamento)
            db.session.commit()

            return orcamento, None
        except Exception as e:
            db.session.rollback()
            return None, f'Erro ao criar orçamento: {e!s}'

    @staticmethod
    def adicionar_itens(orcamento_id, itens_json):
        """Add items to budget from JSON string. Returns list of items"""
        itens = json.loads(itens_json)
        itens_criados = []

        for item_data in itens:
            item = ItemOrcamento(
                orcamento_id=orcamento_id,
                descricao=item_data.get('descricao', ''),
                quantidade=float(item_data.get('quantidade', 0)),
                valor_unitario=float(item_data.get('valor_unitario', 0)),
            )
            db.session.add(item)
            itens_criados.append(item)

        return itens_criados

    @staticmethod
    def calcular_valor_total(orcamento):
        """Calculate budget total from items. Returns total value"""
        total = (
            db.session.query(db.func.sum(ItemOrcamento.quantidade * ItemOrcamento.valor_unitario))
            .filter(ItemOrcamento.orcamento_id == orcamento.id)
            .scalar()
            or 0
        )

        return total

    @staticmethod
    def duplicar_orcamento(orcamento_id, empresa_id):
        """Duplicate budget with all items. Returns (new_orcamento, error_message)"""
        orcamento = Orcamento.query.filter_by(id=orcamento_id, empresa_id=empresa_id).first()
        if not orcamento:
            return None, 'Orçamento não encontrado.'

        # Create copy
        novo_orcamento = Orcamento(
            empresa_id=empresa_id,
            cliente=orcamento.cliente,
            titulo=f'Cópia de {orcamento.titulo}',
            descricao=orcamento.descricao,
            status='Rascunho',
            validade=orcamento.validade,
            observacoes=orcamento.observacoes,
            valor_materiais=orcamento.valor_materiais,
            valor_mao_obra=orcamento.valor_mao_obra,
            valor_equipamentos=orcamento.valor_equipamentos,
            valor_outros=orcamento.valor_outros,
            desconto=orcamento.desconto,
        )
        db.session.add(novo_orcamento)
        db.session.flush()

        # Copy items
        itens_originais = ItemOrcamento.query.filter_by(orcamento_id=orcamento.id).all()

        for item_original in itens_originais:
            novo_item = ItemOrcamento(
                orcamento_id=novo_orcamento.id,
                descricao=item_original.descricao,
                quantidade=item_original.quantidade,
                valor_unitario=item_original.valor_unitario,
            )
            db.session.add(novo_item)

        # Calculate total
        OrcamentoService.calcular_valor_total(novo_orcamento)
        db.session.commit()

        return novo_orcamento, None

    @staticmethod
    def converter_em_contrato(orcamento_id, empresa_id):
        """Convert budget to contract. Returns (contrato, error_message)"""
        from app.models import Contrato

        orcamento = Orcamento.query.filter_by(id=orcamento_id, empresa_id=empresa_id).first()
        if not orcamento:
            return None, 'Orçamento não encontrado.'

        if orcamento is None or orcamento.obra_id is None:
            return None, 'Orçamento precisa estar vinculado a uma obra.'

        contrato = Contrato(
            empresa_id=empresa_id,
            obra_id=orcamento.obra_id,
            descricao=orcamento.descricao or 'Contrato gerado a partir de orçamento',
            valor_total=orcamento.valor_total,
            status='Ativo',
            observacoes=orcamento.observacoes,
        )
        db.session.add(contrato)
        db.session.commit()

        return contrato, None
