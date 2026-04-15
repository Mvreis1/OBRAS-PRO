"""Banco service - Bank account management"""

from datetime import date, datetime
from typing import Optional

from app.models import db
from app.models.banco import ContaBancaria, LancamentoConta
from app.services.base_service import BaseService


class BancoService(BaseService):
    """Service for bank account management"""

    @staticmethod
    def criar_conta(empresa_id: int, dados: dict) -> tuple[ContaBancaria | None, str | None]:
        """Create new bank account. Returns (conta, error_message)"""
        # Validate unique account number per bank
        if dados.get('banco') and dados.get('agencia') and dados.get('conta'):
            _is_unique, _error = BancoService.validate_unique(
                ContaBancaria,
                'banco',
                dados['banco'],
            )
            # Check for duplicate account
            existing = ContaBancaria.query.filter_by(
                empresa_id=empresa_id,
                banco=dados['banco'],
                agencia=dados['agencia'],
                conta=dados['conta'],
            ).first()

            if existing:
                return None, 'Conta bancária já cadastrada.'

        conta = ContaBancaria(
            empresa_id=empresa_id,
            banco=dados.get('banco', '').strip(),
            agencia=dados.get('agencia'),
            conta=dados.get('conta', '').strip(),
            tipo=dados.get('tipo', 'Corrente'),
            titular=dados.get('titular'),
            saldo_inicial=dados.get('saldo_inicial', 0),
        )
        db.session.add(conta)
        db.session.commit()

        return conta, None

    @staticmethod
    def editar_conta(
        conta_id: int, empresa_id: int, dados: dict
    ) -> tuple[ContaBancaria | None, str | None]:
        """Update bank account. Returns (conta, error_message)"""
        conta = ContaBancaria.query.filter_by(id=conta_id, empresa_id=empresa_id).first()
        if not conta:
            return None, 'Conta bancária não encontrada.'

        if 'banco' in dados:
            conta.banco = dados['banco'].strip()
        if 'agencia' in dados:
            conta.agencia = dados['agencia']
        if 'conta' in dados:
            conta.conta = dados['conta'].strip()
        if 'tipo' in dados:
            conta.tipo = dados['tipo']
        if 'titular' in dados:
            conta.titular = dados['titular']

        db.session.commit()
        return conta, None

    @staticmethod
    def excluir_conta(conta_id: int, empresa_id: int) -> tuple[bool, str | None]:
        """Delete bank account. Returns (success, error_message)"""
        conta = ContaBancaria.query.filter_by(id=conta_id, empresa_id=empresa_id).first()
        if not conta:
            return False, 'Conta bancária não encontrada.'

        db.session.delete(conta)
        db.session.commit()
        return True, None

    @staticmethod
    def get_contas_resumo(empresa_id: int) -> list[dict]:
        """Get all bank accounts with balance summary"""
        contas = ContaBancaria.query.filter_by(empresa_id=empresa_id).all()

        resumo = []
        for conta in contas:
            # Calculate current balance from transactions
            entradas = (
                db.session.query(db.func.sum(LancamentoConta.valor))
                .filter_by(conta_id=conta.id, tipo='entrada')
                .scalar()
                or 0
            )

            saidas = (
                db.session.query(db.func.sum(LancamentoConta.valor))
                .filter_by(conta_id=conta.id, tipo='saida')
                .scalar()
                or 0
            )

            saldo_atual = conta.saldo_inicial + entradas - saidas

            resumo.append(
                {
                    'conta': conta,
                    'saldo_atual': saldo_atual,
                    'entradas': entradas,
                    'saidas': saidas,
                }
            )

        return resumo

    @staticmethod
    def get_saldo_conta(conta_id: int, empresa_id: int) -> dict:
        """Get current balance for a bank account"""
        conta = ContaBancaria.query.filter_by(id=conta_id, empresa_id=empresa_id).first()
        if not conta:
            return {'error': 'Conta não encontrada'}

        entradas = (
            db.session.query(db.func.sum(LancamentoConta.valor))
            .filter_by(conta_id=conta_id, tipo='entrada')
            .scalar()
            or 0
        )

        saidas = (
            db.session.query(db.func.sum(LancamentoConta.valor))
            .filter_by(conta_id=conta_id, tipo='saida')
            .scalar()
            or 0
        )

        return {
            'conta': conta,
            'saldo_inicial': conta.saldo_inicial,
            'entradas': entradas,
            'saidas': saidas,
            'saldo_atual': conta.saldo_inicial + entradas - saidas,
        }

    @staticmethod
    def criar_lancamento_banco(
        conta_id: int, empresa_id: int, dados: dict
    ) -> tuple[LancamentoConta | None, str | None]:
        """Create bank transaction. Returns (lancamento, error_message)"""
        conta = ContaBancaria.query.filter_by(id=conta_id, empresa_id=empresa_id).first()
        if not conta:
            return None, 'Conta bancária não encontrada.'

        valor = dados.get('valor', 0)
        if valor <= 0:
            return None, 'Valor deve ser positivo.'

        data = None
        if dados.get('data'):
            from app.utils.dates import parse_date

            data = parse_date(dados['data'])

        lancamento = LancamentoConta(
            conta_id=conta_id,
            empresa_id=empresa_id,
            tipo=dados.get('tipo', 'saida'),  # 'entrada' or 'saida'
            valor=valor,
            descricao=dados.get('descricao', '').strip(),
            categoria=dados.get('categoria'),
            data=data or date.today(),
            forma_pagamento=dados.get('forma_pagamento'),
        )
        db.session.add(lancamento)
        db.session.commit()

        return lancamento, None

    @staticmethod
    def criar_transferencia(
        empresa_id: int,
        conta_origem_id: int,
        conta_destino_id: int,
        valor: float,
        descricao: str,
        data: str | None = None,
    ) -> tuple[bool, str | None]:
        """Create transfer between bank accounts. Returns (success, error_message)"""
        if conta_origem_id == conta_destino_id:
            return False, 'Contas devem ser diferentes.'

        conta_origem = ContaBancaria.query.filter_by(
            id=conta_origem_id, empresa_id=empresa_id
        ).first()
        conta_destino = ContaBancaria.query.filter_by(
            id=conta_destino_id, empresa_id=empresa_id
        ).first()

        if not conta_origem or not conta_destino:
            return None, 'Conta origem ou destino não encontrada.'

        if valor <= 0:
            return False, 'Valor deve ser positivo.'

        # Check if origin account has enough balance
        saldo = BancoService.get_saldo_conta(conta_origem_id, empresa_id)
        if saldo.get('saldo_atual', 0) < valor:
            return False, f'Saldo insuficiente. Saldo atual: R$ {saldo.get("saldo_atual", 0):.2f}'

        data_obj = None
        if data:
            from app.utils.dates import parse_date

            data_obj = parse_date(data) or date.today()
        else:
            data_obj = date.today()

        # Create transactions for both accounts
        lanc_origem = LancamentoConta(
            conta_id=conta_origem_id,
            empresa_id=empresa_id,
            tipo='saida',
            valor=valor,
            descricao=f'Transferência para {conta_destino.banco} - {descricao}',
            data=data_obj,
        )

        lanc_destino = LancamentoConta(
            conta_id=conta_destino_id,
            empresa_id=empresa_id,
            tipo='entrada',
            valor=valor,
            descricao=f'Transferência de {conta_origem.banco} - {descricao}',
            data=data_obj,
        )

        db.session.add(lanc_origem)
        db.session.add(lanc_destino)
        db.session.commit()

        return True, None

    @staticmethod
    def get_extrato(
        conta_id: int,
        empresa_id: int,
        data_inicio: str | None = None,
        data_fim: str | None = None,
    ) -> list[dict]:
        """Get bank statement with all transactions"""
        query = LancamentoConta.query.filter_by(conta_id=conta_id, empresa_id=empresa_id)

        if data_inicio:
            from app.utils.dates import parse_date

            data = parse_date(data_inicio)
            if data:
                query = query.filter(LancamentoConta.data >= data)

        if data_fim:
            from app.utils.dates import parse_date

            data = parse_date(data_fim)
            if data:
                query = query.filter(LancamentoConta.data <= data)

        lancamentos = query.order_by(LancamentoConta.data.desc()).all()

        # Calculate running balance
        conta = ContaBancaria.query.get(conta_id)
        saldo = conta.saldo_inicial if conta else 0

        extrato = []
        for lanc in sorted(lancamentos, key=lambda x: x.data):
            if lanc.tipo == 'entrada':
                saldo += lanc.valor
            else:
                saldo -= lanc.valor

            extrato.append(
                {
                    'lancamento': lanc,
                    'saldo_apos': saldo,
                }
            )

        return list(reversed(extrato))  # Most recent first
