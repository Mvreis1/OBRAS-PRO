#!/usr/bin/env python3
"""
Script de teste para verificar todas as rotas do OBRAS PRO
"""

import sys

import requests

BASE_URL = 'https://obras-financeiro.onrender.com'

# Rotas públicas (sem login)
PUBLIC_ROUTES = [
    ('/healthz', 'GET', 200),
    ('/test', 'GET', 200),
    ('/test-db', 'GET', 200),
    ('/debug/db', 'GET', 200),
    ('/debug/config', 'GET', 200),
    ('/setup-demo', 'GET', 200),
    ('/auth/login', 'GET', 200),
]

# Rotas que requerem login
PROTECTED_ROUTES_GET = [
    ('/', 'GET', 302),  # Redireciona para login
    ('/dashboard', 'GET', 302),
    ('/obras', 'GET', 302),
    ('/obra/nova', 'GET', 302),
    ('/lancamentos', 'GET', 302),
    ('/lancamento/novo', 'GET', 302),
    ('/relatorios', 'GET', 302),
    ('/fornecedor/fornecedores', 'GET', 302),
    ('/fornecedor/fornecedor/novo', 'GET', 302),
    ('/contrato/contratos', 'GET', 302),
    ('/orcamento/orcamentos', 'GET', 302),
    ('/banco/contas', 'GET', 302),
    ('/api/dashboard', 'GET', 302),
]

# Rotas POST que requerem login
PROTECTED_ROUTES_POST = [
    ('/obra/nova', 'POST', 302),
    ('/lancamento/novo', 'POST', 302),
]


def test_route(url, method, expected_status):
    """Testa uma rota específica"""
    full_url = f'{BASE_URL}{url}'
    try:
        if method == 'GET':
            response = requests.get(full_url, timeout=10, allow_redirects=False)
        elif method == 'POST':
            response = requests.post(full_url, timeout=10, allow_redirects=False, data={})
        else:
            return False, f'Método {method} não suportado'

        status = response.status_code
        if status == expected_status:
            return True, f'OK (HTTP {status})'
        else:
            return False, f'ERRO: Esperado {expected_status}, obtido {status}'
    except requests.exceptions.Timeout:
        return False, 'TIMEOUT'
    except requests.exceptions.ConnectionError:
        return False, 'CONNECTION ERROR'
    except Exception as e:
        return False, f'EXCEPTION: {e!s}'


def main():
    print('=' * 70)
    print('TESTE DE ROTAS - OBRAS PRO')
    print('=' * 70)
    print()

    # Testar rotas públicas
    print('Rotas Públicas:')
    print('-' * 70)
    public_ok = 0
    public_fail = 0
    for route, method, expected in PUBLIC_ROUTES:
        success, msg = test_route(route, method, expected)
        status = '✅' if success else '❌'
        print(f'{status} {method:6} {route:40} -> {msg}')
        if success:
            public_ok += 1
        else:
            public_fail += 1

    print()
    print('Rotas Protegidas (GET):')
    print('-' * 70)
    protected_ok = 0
    protected_fail = 0
    for route, method, expected in PROTECTED_ROUTES_GET:
        success, msg = test_route(route, method, expected)
        status = '✅' if success else '❌'
        print(f'{status} {method:6} {route:40} -> {msg}')
        if success:
            protected_ok += 1
        else:
            protected_fail += 1

    print()
    print('Rotas Protegidas (POST):')
    print('-' * 70)
    for route, method, expected in PROTECTED_ROUTES_POST:
        success, msg = test_route(route, method, expected)
        status = '✅' if success else '❌'
        print(f'{status} {method:6} {route:40} -> {msg}')
        if success:
            protected_ok += 1
        else:
            protected_fail += 1

    print()
    print('=' * 70)
    print('RESUMO:')
    print('=' * 70)
    print(f'Rotas públicas OK: {public_ok}/{len(PUBLIC_ROUTES)}')
    print(f'Rotas públicas FALHAS: {public_fail}')
    print(
        f'Rotas protegidas OK: {protected_ok}/{len(PROTECTED_ROUTES_GET) + len(PROTECTED_ROUTES_POST)}'
    )
    print(f'Rotas protegidas FALHAS: {protected_fail}')
    print()

    if public_fail > 0 or protected_fail > 0:
        print('❌ ALGUNS TESTES FALHARAM')
        return 1
    else:
        print('✅ TODOS OS TESTES PASSARAM')
        return 0


if __name__ == '__main__':
    sys.exit(main())
