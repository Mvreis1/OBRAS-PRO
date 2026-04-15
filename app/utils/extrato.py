"""
Helpers para importação de extrato bancário
"""

import re
from datetime import date

from app.models import ContaBancaria, LancamentoConta, db


def recalcular_saldo_conta(conta_id, empresa_id):
    """Recalcula o saldo atual de uma conta baseado em todos os lançamentos"""
    result = (
        db.session.query(
            db.func.sum(
                db.case(
                    (LancamentoConta.tipo == 'Credito', LancamentoConta.valor),
                    else_=-LancamentoConta.valor,
                )
            ).label('saldo')
        )
        .filter(LancamentoConta.conta_id == conta_id, LancamentoConta.empresa_id == empresa_id)
        .scalar()
    )

    conta = db.session.get(ContaBancaria, conta_id)
    if conta:
        conta.saldo_atual = conta.saldo_inicial + (result or 0)
        db.session.commit()


def processar_ofx(conteudo, empresa_id, conta_id):
    """Processa arquivo OFX"""
    lancamentos = []
    erros = []

    # Extrair todas as transações do OFX
    transacoes = re.findall(r'<STMTTRN>(.*?)</STMTTRN>', conteudo, re.DOTALL)

    for transacao in transacoes:
        try:
            # Extrair campos do OFX (formato XML-like)
            def get_tag(tag, text, default=''):
                match = re.search(rf'<{tag}>([^<\n]+)', text)
                return match.group(1).strip() if match else default

            data_str = get_tag('DTPOSTED', transacao, '')
            if data_str:
                data = date.fromisoformat(data_str[:8].replace('/', '-'))
            else:
                data = date.today()

            descricao = get_tag('NAME', transacao, get_tag('MEMO', transacao, 'Transação OFX'))
            valor_str = get_tag('TRNAMT', transacao, '0').replace(',', '.')
            valor = float(valor_str)

            if valor > 0:
                tipo = 'Credito'
            else:
                tipo = 'Debito'
                valor = abs(valor)

            lancamento = LancamentoConta(
                empresa_id=empresa_id,
                conta_id=conta_id,
                descricao=descricao[:200],
                tipo=tipo,
                valor=valor,
                data=data,
                documento=get_tag('REFNUM', transacao, ''),
            )
            db.session.add(lancamento)
            lancamentos.append(lancamento)
        except Exception as e:
            erros.append(f'Erro ao processar transação OFX: {e!s}')

    recalcular_saldo_conta(conta_id, empresa_id)
    return len(lancamentos), erros


def processar_csv(conteudo, empresa_id, conta_id):
    """Processa arquivo CSV (formato genérico)"""
    import csv
    import io

    lancamentos = []
    erros = []

    reader = csv.reader(io.StringIO(conteudo), delimiter=';')

    for i, row in enumerate(reader):
        if i == 0:
            continue

        try:
            if len(row) < 3:
                continue

            data_str = row[0].strip()
            descricao = row[1].strip()
            valor_str = row[2].strip().replace('.', '').replace(',', '.')

            if '/' in data_str:
                from datetime import datetime

                data = datetime.strptime(data_str, '%d/%m/%Y').date()
            else:
                data = date.today()

            valor = float(valor_str)

            if valor > 0:
                tipo = 'Credito'
            else:
                tipo = 'Debito'
                valor = abs(valor)

            documento = row[3].strip() if len(row) > 3 else ''

            lancamento = LancamentoConta(
                empresa_id=empresa_id,
                conta_id=conta_id,
                descricao=descricao[:200],
                tipo=tipo,
                valor=valor,
                data=data,
                documento=documento,
            )
            db.session.add(lancamento)
            lancamentos.append(lancamento)
        except Exception as e:
            erros.append(f'Linha {i + 1}: {e!s}')

    recalcular_saldo_conta(conta_id, empresa_id)
    return len(lancamentos), erros


def processar_cnab(conteudo, empresa_id, conta_id):
    """Processa arquivo CNAB 240 (formato brasileiro)"""
    lancamentos = []
    erros = []

    linhas = conteudo.split('\n')

    for i, linha in enumerate(linhas):
        if len(linha) < 240:
            continue

        tipo_reg = linha[7:8]

        if tipo_reg == '3':
            try:
                data_str = linha[110:118]
                linha[118:122]

                if data_str.isdigit():
                    dia = int(data_str[0:2])
                    mes = int(data_str[2:4])
                    ano = int(data_str[4:8])
                    data = date(ano, mes, dia)
                else:
                    data = date.today()

                valor_int = int(linha[119:134])
                valor = valor_int / 100

                tipo_ocorrencia = linha[15:17]

                if tipo_ocorrencia in ['02', '06', '09', '10', '11']:
                    tipo = 'Credito'
                elif tipo_ocorrencia in ['03', '05']:
                    tipo = 'Debito'
                else:
                    tipo = 'Credito'

                descricao = linha[82:122].strip()
                documento = linha[37:62].strip()

                if valor > 0:
                    lancamento = LancamentoConta(
                        empresa_id=empresa_id,
                        conta_id=conta_id,
                        descricao=descricao[:200] or 'Lançamento CNAB',
                        tipo=tipo,
                        valor=valor,
                        data=data,
                        documento=documento,
                    )
                    db.session.add(lancamento)
                    lancamentos.append(lancamento)
            except Exception as e:
                erros.append(f'Linha {i + 1}: {e!s}')

    recalcular_saldo_conta(conta_id, empresa_id)
    return len(lancamentos), erros
