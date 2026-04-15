"""Contrato service - Contract management"""

from datetime import date, datetime
from typing import Optional

from app.models import db
from app.models.contratos import Contrato, ParcelaContrato
from app.services.base_service import BaseService
from app.utils.contratos import gerar_parcelas, validar_datas_contrato


class ContratoService(BaseService):
    """Service for contract management"""

    @staticmethod
    def criar_contrato(empresa_id: int, dados: dict) -> tuple[Contrato | None, str | None]:
        """Create new contract. Returns (contrato, error_message)"""
        # Validate dates
        from app.utils.dates import parse_date

        data_inicio = parse_date(dados.get('data_inicio'))
        data_fim = parse_date(dados.get('data_fim'))

        valido, erro = validar_datas_contrato(data_inicio, data_fim)
        if not valido:
            return None, erro

        # Validate required fields
        if not dados.get('cliente', '').strip():
            return None, 'Nome do cliente é obrigatório.'
        if not dados.get('titulo', '').strip():
            return None, 'Título do contrato é obrigatório.'

        valor = dados.get('valor', 0)
        if valor < 0:
            return None, 'Valor não pode ser negativo.'

        contrato = Contrato(
            empresa_id=empresa_id,
            obra_id=dados.get('obra_id'),
            cliente=dados.get('cliente', '').strip(),
            cliente_cnpj=dados.get('cliente_cnpj'),
            cliente_email=dados.get('cliente_email'),
            cliente_telefone=dados.get('cliente_telefone'),
            cliente_endereco=dados.get('cliente_endereco'),
            titulo=dados.get('titulo', '').strip(),
            descricao=dados.get('descricao'),
            valor=valor,
            data_inicio=data_inicio,
            data_fim=data_fim,
            data_assinatura=parse_date(dados.get('data_assinatura')),
            status=dados.get('status') or 'Rascunho',
            tipo=dados.get('tipo'),
            observacoes=dados.get('observacoes'),
        )
        db.session.add(contrato)
        db.session.commit()

        # Generate installments if requested
        num_parcelas = dados.get('num_parcelas', 0)
        if num_parcelas > 1:
            gerar_parcelas(contrato, num_parcelas)

        return contrato, None

    @staticmethod
    def editar_contrato(
        contrato_id: int, empresa_id: int, dados: dict
    ) -> tuple[Contrato | None, str | None]:
        """Update contract. Returns (contrato, error_message)"""
        contrato = Contrato.query.filter_by(id=contrato_id, empresa_id=empresa_id).first()
        if not contrato:
            return None, 'Contrato não encontrado.'

        from app.utils.dates import parse_date

        # Update fields
        if 'cliente' in dados:
            if not dados['cliente'].strip():
                return None, 'Nome do cliente é obrigatório.'
            contrato.cliente = dados['cliente'].strip()
        if 'cliente_cnpj' in dados:
            contrato.cliente_cnpj = dados['cliente_cnpj']
        if 'cliente_email' in dados:
            contrato.cliente_email = dados['cliente_email']
        if 'cliente_telefone' in dados:
            contrato.cliente_telefone = dados['cliente_telefone']
        if 'cliente_endereco' in dados:
            contrato.cliente_endereco = dados['cliente_endereco']
        if 'titulo' in dados:
            if not dados['titulo'].strip():
                return None, 'Título é obrigatório.'
            contrato.titulo = dados['titulo'].strip()
        if 'descricao' in dados:
            contrato.descricao = dados['descricao']
        if 'valor' in dados:
            if dados['valor'] < 0:
                return None, 'Valor não pode ser negativo.'
            contrato.valor = dados['valor']
        if 'status' in dados:
            contrato.status = dados['status']
        if 'tipo' in dados:
            contrato.tipo = dados['tipo']
        if 'observacoes' in dados:
            contrato.observacoes = dados['observacoes']

        # Validate and update dates
        if dados.get('data_inicio') or dados.get('data_fim'):
            data_inicio = parse_date(dados.get('data_inicio')) or contrato.data_inicio
            data_fim = parse_date(dados.get('data_fim')) or contrato.data_fim

            valido, erro = validar_datas_contrato(data_inicio, data_fim)
            if not valido:
                return None, erro

            contrato.data_inicio = data_inicio
            contrato.data_fim = data_fim

        if dados.get('data_assinatura'):
            data = parse_date(dados['data_assinatura'])
            if data:
                contrato.data_assinatura = data

        db.session.commit()
        return contrato, None

    @staticmethod
    def excluir_contrato(contrato_id: int, empresa_id: int) -> tuple[bool, str | None]:
        """Delete contract. Returns (success, error_message)"""
        contrato = Contrato.query.filter_by(id=contrato_id, empresa_id=empresa_id).first()
        if not contrato:
            return False, 'Contrato não encontrado.'

        db.session.delete(contrato)
        db.session.commit()
        return True, None

    @staticmethod
    def get_contrato_detalhado(contrato_id: int, empresa_id: int) -> dict | None:
        """Get contract with installments summary. Returns dict or None"""
        contrato = Contrato.query.filter_by(id=contrato_id, empresa_id=empresa_id).first()
        if not contrato:
            return None

        parcelas = (
            ParcelaContrato.query.filter_by(contrato_id=contrato_id)
            .order_by(ParcelaContrato.numero)
            .all()
        )

        total_pago = sum(p.valor for p in parcelas if p.status == 'Pago')
        total_pendente = sum(p.valor for p in parcelas if p.status == 'Pendente')
        total_vencidas = sum(
            p.valor for p in parcelas if p.status == 'Pendente' and p.data_vencimento < date.today()
        )

        return {
            'contrato': contrato,
            'parcelas': parcelas,
            'total_pago': total_pago,
            'total_pendente': total_pendente,
            'total_vencidas': total_vencidas,
            'progresso_pagamento': (total_pago / contrato.valor * 100) if contrato.valor > 0 else 0,
        }

    @staticmethod
    def pagar_parcela(parcela_id: int, empresa_id: int) -> tuple[bool, str | None]:
        """Mark installment as paid. Returns (success, error_message)"""
        parcela = (
            ParcelaContrato.query.join(Contrato)
            .filter(ParcelaContrato.id == parcela_id, Contrato.empresa_id == empresa_id)
            .first()
        )
        if not parcela:
            return False, 'Parcela não encontrada.'

        if parcela.status == 'Pago':
            return False, 'Parcela já está paga.'

        parcela.status = 'Pago'
        parcela.data_pagamento = date.today()
        db.session.commit()

        # Update contract status if all paid
        ContratoService._update_contrato_status(parcela.contrato_id)

        return True, None

    @staticmethod
    def _update_contrato_status(contrato_id: int):
        """Update contract status based on payment progress"""
        contrato = Contrato.query.get(contrato_id)
        if not contrato:
            return

        parcelas = ParcelaContrato.query.filter_by(contrato_id=contrato_id).all()
        if not parcelas:
            return

        pagas = sum(1 for p in parcelas if p.status == 'Pago')
        total = len(parcelas)

        if pagas == total:
            contrato.status = 'Concluído'
        elif pagas > 0:
            contrato.status = 'Em Pagamento'

        db.session.commit()

    @staticmethod
    def get_contratos_por_status(empresa_id: int) -> dict[str, int]:
        """Get count of contracts grouped by status"""
        results = (
            db.session.query(Contrato.status, db.func.count(Contrato.id))
            .filter_by(empresa_id=empresa_id)
            .group_by(Contrato.status)
            .all()
        )
        return dict(results)

    @staticmethod
    def get_contratos_vencendo(empresa_id: int, dias: int = 30) -> list[Contrato]:
        """Get contracts expiring within N days"""
        data_limite = (
            date.today().replace(day=date.today().day + dias)
            if date.today().day + dias <= 28
            else date.today()
        )

        return (
            Contrato.query.filter(
                Contrato.empresa_id == empresa_id,
                Contrato.data_fim <= data_limite,
                Contrato.data_fim >= date.today(),
                Contrato.status.notin_(['Concluído', 'Cancelado']),
            )
            .order_by(Contrato.data_fim)
            .all()
        )

    @staticmethod
    def duplicar_contrato(contrato_id: int, empresa_id: int) -> tuple[Contrato | None, str | None]:
        """Duplicate contract with all installments. Returns (new_contrato, error_message)"""
        original = Contrato.query.filter_by(id=contrato_id, empresa_id=empresa_id).first()
        if not original:
            return None, 'Contrato não encontrado.'

        novo = Contrato(
            empresa_id=empresa_id,
            obra_id=original.obra_id,
            cliente=original.cliente,
            cliente_cnpj=original.cliente_cnpj,
            cliente_email=original.cliente_email,
            cliente_telefone=original.cliente_telefone,
            cliente_endereco=original.cliente_endereco,
            titulo=f'{original.titulo} (Cópia)',
            descricao=original.descricao,
            valor=original.valor,
            data_inicio=original.data_inicio,
            data_fim=original.data_fim,
            status='Rascunho',
            tipo=original.tipo,
            observacoes=original.observacoes,
        )
        db.session.add(novo)
        db.session.flush()

        # Copy installments
        parcelas_originais = ParcelaContrato.query.filter_by(contrato_id=contrato_id).all()
        for parcela in parcelas_originais:
            nova_parcela = ParcelaContrato(
                empresa_id=empresa_id,
                contrato_id=novo.id,
                numero=parcela.numero,
                valor=parcela.valor,
                data_vencimento=parcela.data_vencimento,
                descricao=parcela.descricao,
            )
            db.session.add(nova_parcela)

        db.session.commit()
        return novo, None
