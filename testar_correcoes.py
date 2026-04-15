#!/usr/bin/env python3
"""
Script para testar as correções feitas no código
Verifica se os imports estão corretos e a sintaxe está válida
"""

import os
import sys

# Adicionar diretório ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print('=' * 60)
print('[TEST] TESTANDO CORRECOES')
print('=' * 60)

resultados = {'passou': [], 'falhou': []}


def testar(descricao, func):
    """Função helper para testar"""
    try:
        func()
        resultados['passou'].append(descricao)
        print(f'[PASS] {descricao}')
        return True
    except Exception as e:
        resultados['falhou'].append((descricao, str(e)))
        print(f'[FAIL] {descricao}')
        print(f'   Erro: {e}')
        return False


print('\n[TEST] Teste 1: Imports corrigidos')
print('-' * 60)


# Teste 1: main.py - current_app importado
def test_main_imports():
    with open('app/routes/main.py', encoding='utf-8') as f:
        content = f.read()

    # Verificar se current_app está nos imports
    if 'from flask import' in content and 'current_app' in content:
        # Verificar se está sendo usado
        if 'current_app.logger.error' in content:
            # Verificar sintaxe compilando
            compile(content, 'main.py', 'exec')
        else:
            raise Exception('current_app não está sendo usado')
    else:
        raise Exception('current_app não está importado')


testar('main.py - current_app importado', test_main_imports)


# Teste 2: audit.py - db importado
def test_audit_imports():
    with open('app/routes/audit.py', encoding='utf-8') as f:
        content = f.read()

    if 'from app.models' in content and 'import db' in content:
        # Verificar se está sendo usado
        if 'db.session.query' in content:
            compile(content, 'audit.py', 'exec')
        else:
            raise Exception('db não está sendo usado')
    else:
        raise Exception('db não está importado')


testar('audit.py - db importado', test_audit_imports)


# Teste 3: auth.py - validate_password não faz self-import
def test_auth_validate_password():
    with open('app/routes/auth.py', encoding='utf-8') as f:
        content = f.read()

    # Verificar se não há self-import
    if 'from app.routes.auth import validate_password' in content:
        raise Exception('Ainda faz self-import de validate_password')

    # Verificar se validate_password está importado corretamente de app.utils.validacao
    if 'from app.utils.validacao import' in content and 'validate_password' in content:
        compile(content, 'auth.py', 'exec')
    else:
        raise Exception('validate_password não está importado corretamente')


testar('auth.py - validate_password import correto', test_auth_validate_password)


# Teste 4: auth.py - sem check_password_hash não utilizado
def test_auth_unused_imports():
    with open('app/routes/auth.py', encoding='utf-8') as f:
        content = f.read()

    if 'from werkzeug.security import check_password_hash' in content:
        raise Exception('Import não utilizado check_password_hash ainda presente')

    compile(content, 'auth.py', 'exec')


testar('auth.py - sem imports não utilizados', test_auth_unused_imports)


# Teste 5: auth.py - validação de senha consistente
def test_auth_password_validation():
    with open('app/routes/auth.py', encoding='utf-8') as f:
        content = f.read()

    # Verificar se não há validação de 6 caracteres
    if 'len(nova_senha) < 6' in content:
        raise Exception('Ainda há validação de 6 caracteres')

    # Verificar se usa validate_password no definir_nova_senha
    if 'valido, msg = validate_password(nova_senha)' in content:
        compile(content, 'auth.py', 'exec')
    else:
        raise Exception('Não está usando validate_password corretamente')


testar('auth.py - validação de senha consistente', test_auth_password_validation)


# Teste 6: orcamentos.py - null check em ItemOrcamento
def test_orcamentos_null_check():
    with open('app/routes/orcamentos.py', encoding='utf-8') as f:
        content = f.read()

    # Verificar se tem null check
    if 'not item.orcamento' in content or 'item.orcamento is None' in content:
        compile(content, 'orcamentos.py', 'exec')
    else:
        raise Exception('Null check não adicionado para item.orcamento')


testar('orcamentos.py - null check em ItemOrcamento', test_orcamentos_null_check)

print('\n[TEST] Teste 2: Sintaxe dos arquivos')
print('-' * 60)

# Testar sintaxe de todos os arquivos modificados
arquivos_para_testar = [
    'app/routes/main.py',
    'app/routes/audit.py',
    'app/routes/auth.py',
    'app/routes/orcamentos.py',
]

for arquivo in arquivos_para_testar:

    def test_sintaxe(arquivo=arquivo):
        with open(arquivo, encoding='utf-8') as f:
            content = f.read()
        compile(content, arquivo, 'exec')

    testar(f'{arquivo} - sintaxe válida', test_sintaxe)

print('\n[TEST] Teste 3: Estrutura do projeto')
print('-' * 60)


# Verificar se arquivos essenciais existem
def test_estrutura():
    arquivos_essenciais = [
        'app/__init__.py',
        'app/models/__init__.py',
        'app/models/orcamentos.py',
        'app/routes/main.py',
        'app/routes/audit.py',
        'app/routes/auth.py',
        'app/routes/orcamentos.py',
        'run.py',
    ]

    for arquivo in arquivos_essenciais:
        if not os.path.exists(arquivo):
            raise Exception(f'Arquivo essencial não encontrado: {arquivo}')


testar('Estrutura de arquivos completa', test_estrutura)

# Relatorio final
print('\n' + '=' * 60)
print('[REPORT] RELATORIO FINAL')
print('=' * 60)

total_passou = len(resultados['passou'])
total_falhou = len(resultados['falhou'])
total = total_passou + total_falhou

print(f'\n[PASS] Testes que passaram: {total_passou}')
print(f'[FAIL] Testes que falharam: {total_falhou}')
print(f'[RATE] Taxa de sucesso: {(total_passou / total * 100) if total > 0 else 0:.1f}%')

if resultados['falhou']:
    print('\n[ERROR] ERROS ENCONTRADOS:')
    for descricao, erro in resultados['falhou']:
        print(f'   - {descricao}: {erro}')
else:
    print('\n[OK] TODOS OS TESTES PASSARAM!')
    print('\nAs correcoes foram aplicadas com sucesso!')
    print('Os erros criticos identificados foram resolvidos.')

# Salvar relatorio
with open('resultado_correcoes.txt', 'w', encoding='utf-8') as f:
    f.write('=' * 60 + '\n')
    f.write('RESULTADO DOS TESTES DE CORRECAO\n')
    f.write('=' * 60 + '\n\n')

    f.write(f'Total de testes: {total}\n')
    f.write(f'Passaram: {total_passou}\n')
    f.write(f'Falharam: {total_falhou}\n')
    f.write(f'Taxa de sucesso: {(total_passou / total * 100) if total > 0 else 0:.1f}%\n\n')

    f.write('TESTES:\n')
    for descricao in resultados['passou']:
        f.write(f'  [PASS] {descricao}\n')

    if resultados['falhou']:
        f.write('\nERROS:\n')
        for descricao, erro in resultados['falhou']:
            f.write(f'  [FAIL] {descricao}: {erro}\n')

print('\n[FILE] Relatorio salvo em: resultado_correcoes.txt')

# Exit code
sys.exit(0 if total_falhou == 0 else 1)
