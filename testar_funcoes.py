#!/usr/bin/env python3
"""
Testes unitários para funções internas do OBRAS-PRO
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configuração para testes
os.environ['FLASK_ENV'] = 'testing'

from datetime import date, datetime

# Resultados dos testes
TEST_RESULTS = {'testados': 0, 'passou': [], 'falhou': []}


def testar(descricao):
    """Decorador para marcar funções de teste"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            TEST_RESULTS['testados'] += 1
            try:
                func(*args, **kwargs)
                TEST_RESULTS['passou'].append(descricao)
                print(f'[PASS] {descricao}')
                return True
            except AssertionError as e:
                TEST_RESULTS['falhou'].append((descricao, str(e)))
                print(f'[FAIL] {descricao}: {e}')
                return False
            except Exception as e:
                TEST_RESULTS['falhou'].append((descricao, f'Erro: {e!s}'))
                print(f'[FAIL] {descricao}: Erro - {e}')
                return False

        return wrapper

    return decorator


# =========================
# TESTES DE UTILITÁRIOS
# =========================
class TesteUtils:

    @testar('Sanitize - Inteiro válido')
    def test_sanitize_int_valido(self):
        from app.utils.sanitize import sanitize_int
        assert sanitize_int('123') == 123
        assert sanitize_int(456) == 456

    @testar('Sanitize - Inteiro inválido')
    def test_sanitize_int_invalido(self):
        from app.utils.sanitize import sanitize_int
        assert sanitize_int('abc', default=0) == 0

    @testar('Sanitize - Float válido')
    def test_sanitize_float(self):
        from app.utils.sanitize import sanitize_float
        assert sanitize_float('123,45') == 123.45

    @testar('Sanitize - Email válido')
    def test_email(self):
        from app.utils.sanitize import sanitize_email
        assert sanitize_email('Teste@Email.com') == 'teste@email.com'


# =========================
# TESTES DE MODELS
# =========================
class TesteModels:

    @testar('Orcamento - valor total')
    def test_orcamento_valor(self):
        from app.models.orcamentos import Orcamento

        orc = Orcamento(
            valor_materiais=1000,
            valor_mao_obra=500,
            valor_equipamentos=200,
            valor_outros=100,
            desconto=200,
        )

        assert orc.valor_total == 1600


# =========================
# TESTES DE CONTRATOS
# =========================
class TesteContratos:

    @testar('Parse date válido')
    def test_parse_date(self):
        from app.utils.contratos import parse_date

        resultado = parse_date('2024-03-15')
        assert resultado == date(2024, 3, 15)


# =========================
# TESTES DE PAGINAÇÃO
# =========================
class TestePaginacao:

    @testar('Paginação básica')
    def test_paginacao(self):
        from app.utils.paginacao import Paginacao

        class MockQuery:
            def count(self):
                return 100

            def offset(self, n):
                return self

            def limit(self, n):
                return self

            def all(self):
                return []

        pag = Paginacao(MockQuery(), page=2, per_page=20)

        assert pag.total == 100
        assert pag.pages == 5


# =========================
# TESTES DE EXCEL
# =========================
class TesteExcel:

    @testar('Formatar moeda')
    def test_excel(self):
        from app.utils.excel_export import formatar_moeda

        assert formatar_moeda(1234.56) == 'R$ 1.234,56'


# =========================
# TESTES DE FORMATAÇÃO
# =========================
class TesteFormatacao:

    @testar('Format currency')
    def test_currency(self):
        from app.utils.templates import format_currency

        assert format_currency(1500.50) == 'R$ 1.500,50'


# =========================
# EXECUÇÃO DOS TESTES
# =========================
def executar_testes():
    print('=' * 60)
    print('[TEST] TESTES UNITARIOS - OBRAS-PRO')
    print('=' * 60)

    from app import create_app

    app = create_app()

    with app.app_context():

        classes_teste = [
            TesteUtils(),
            TesteModels(),
            TesteContratos(),
            TestePaginacao(),
            TesteExcel(),
            TesteFormatacao(),
        ]

        for classe in classes_teste:
            print(f'\n[MODULE] {classe.__class__.__name__}')
            print('-' * 40)

            for metodo_nome in sorted(dir(classe)):
                if metodo_nome.startswith('test_'):
                    metodo = getattr(classe, metodo_nome)
                    metodo()

    # RELATÓRIO FINAL
    print('\n' + '=' * 60)
    print('[REPORT]')
    print('=' * 60)

    total = TEST_RESULTS['testados']
    passou = len(TEST_RESULTS['passou'])
    falhou = len(TEST_RESULTS['falhou'])

    print(f'Total: {total}')
    print(f'Passou: {passou}')
    print(f'Falhou: {falhou}')

    return falhou == 0


if __name__ == '__main__':
    executar_testes()
