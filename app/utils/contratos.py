"""
Helpers para contratos
"""

from datetime import date
from decimal import Decimal

from app.models import db
from app.models.contratos import ParcelaContrato


def validar_datas_contrato(data_inicio, data_fim):
    """Valida datas do contrato"""
    if data_inicio and data_fim and data_fim < data_inicio:
        return False, 'Data fim não pode ser anterior à data início'
    return True, None


def gerar_parcelas(contrato, num_parcelas):
    """Gera parcelas automaticamente para um contrato"""
    from datetime import timedelta

    valor_parcela = contrato.valor / num_parcelas
    valor_parcela = float(Decimal(str(valor_parcela)).quantize(Decimal('0.01')))

    data = contrato.data_inicio or date.today()
    dia_vencimento = min(data.day, 28)
    data = data.replace(day=dia_vencimento)

    for i in range(1, num_parcelas + 1):
        parcela = ParcelaContrato(
            empresa_id=contrato.empresa_id,
            contrato_id=contrato.id,
            numero=i,
            valor=valor_parcela,
            data_vencimento=data,
            descricao=f'{i}ª parcela',
        )
        db.session.add(parcela)
        data = data + timedelta(days=31)

    db.session.commit()


def parse_date():
    return None
