#!/usr/bin/env python3
"""
Script de teste completo para o OBRAS-PRO
Testa todas as funcionalidades principais do sistema
"""

import json
import sys
import time
from datetime import date, datetime

import requests

# Configurações
BASE_URL = 'http://localhost:5000'
TEST_RESULTS = {'passou': [], 'falhou': [], 'avisos': []}


def log_sucesso(funcao, mensagem):
    """Registra um teste que passou"""
    TEST_RESULTS['passou'].append({'funcao': funcao, 'mensagem': mensagem})
    print(f'✅ SUCESSO - {funcao}: {mensagem}')


def log_erro(funcao, mensagem, erro=None):
    """Registra um teste que falhou"""
    TEST_RESULTS['falhou'].append(
        {'funcao': funcao, 'mensagem': mensagem, 'erro': str(erro) if erro else None}
    )
    print(f'❌ ERRO - {funcao}: {mensagem}')
    if erro:
        print(f'   Detalhes: {erro}')


def log_aviso(funcao, mensagem):
    """Registra um aviso"""
    TEST_RESULTS['avisos'].append({'funcao': funcao, 'mensagem': mensagem})
    print(f'⚠️  AVISO - {funcao}: {mensagem}')


def print_secao(titulo):
    """Imprime uma seção de teste"""
    print('\n' + '=' * 60)
    print(f'📋 {titulo}')
    print('=' * 60)


class TesteObrasPro:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.csrf_token = None
        self.empresa_id = None
        self.obra_id = None
        self.lancamento_id = None
        self.orcamento_id = None
        self.contrato_id = None
        self.fornecedor_id = None

    def get_csrf_token(self):
        """Obtém o token CSRF da página de login"""
        try:
            response = self.session.get(f'{self.base_url}/login')
            # Procura pelo token CSRF no HTML
            import re

            match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', response.text)
            if match:
                self.csrf_token = match.group(1)
                return True
            # Tenta outro formato
            match = re.search(r'value="([^"]+)"[^>]*name="csrf_token"', response.text)
            if match:
                self.csrf_token = match.group(1)
                return True
            return False
        except Exception as e:
            log_erro('CSRF', 'Erro ao obter token CSRF', e)
            return False

    def testar_login(self, email, senha):
        """Testa o login no sistema"""
        print_secao('Testando Autenticação')

        try:
            # Obtém CSRF token
            if not self.get_csrf_token():
                log_aviso('Login', 'Não foi possível obter CSRF token, tentando sem...')

            # Tenta fazer login
            data = {'email': email, 'senha': senha, 'csrf_token': self.csrf_token}

            response = self.session.post(f'{self.base_url}/login', data=data, allow_redirects=True)

            if response.status_code == 200:
                # Verifica se está logado (procura por elemento que só aparece logado)
                if 'dashboard' in response.url or 'logout' in response.text.lower():
                    log_sucesso('Login', f'Login realizado com sucesso para {email}')
                    return True
                else:
                    log_erro('Login', 'Possível falha no login - não redirecionou para dashboard')
                    return False
            else:
                log_erro('Login', f'Status code inesperado: {response.status_code}')
                return False

        except Exception as e:
            log_erro('Login', 'Erro ao tentar login', e)
            return False

    def testar_dashboard(self):
        """Testa acesso ao dashboard"""
        print_secao('Testando Dashboard')

        try:
            response = self.session.get(f'{self.base_url}/dashboard')

            if response.status_code == 200:
                log_sucesso('Dashboard', 'Dashboard carregado com sucesso')

                # Verifica elementos esperados
                if 'Orçamento Total' in response.text:
                    log_sucesso('Dashboard', 'Cards de resumo encontrados')
                else:
                    log_aviso('Dashboard', 'Cards de resumo não encontrados')

                return True
            else:
                log_erro('Dashboard', f'Status code: {response.status_code}')
                return False

        except Exception as e:
            log_erro('Dashboard', 'Erro ao acessar dashboard', e)
            return False

    def testar_obras(self):
        """Testa funcionalidades de obras"""
        print_secao('Testando Obras')

        try:
            # Lista obras
            response = self.session.get(f'{self.base_url}/obras')
            if response.status_code == 200:
                log_sucesso('Obras - Listar', 'Lista de obras carregada')
            else:
                log_erro('Obras - Listar', f'Status code: {response.status_code}')
                return False

            # Formulário nova obra
            response = self.session.get(f'{self.base_url}/obra/nova')
            if response.status_code == 200:
                log_sucesso('Obras - Formulário', 'Formulário de nova obra carregado')

                # Extrai CSRF token
                import re

                match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', response.text)
                if match:
                    self.csrf_token = match.group(1)
            else:
                log_erro('Obras - Formulário', f'Status code: {response.status_code}')
                return False

            # Cria nova obra
            obra_data = {
                'csrf_token': self.csrf_token,
                'nome': f'Obra Teste {datetime.now().strftime("%Y%m%d_%H%M%S")}',
                'cliente': 'Cliente Teste',
                'descricao': 'Descrição da obra de teste',
                'endereco': 'Rua Teste, 123',
                'orcamento_previsto': '50000.00',
                'data_inicio': date.today().strftime('%Y-%m-%d'),
                'status': 'Planejamento',
                'progresso': '0',
            }

            response = self.session.post(
                f'{self.base_url}/obra/nova', data=obra_data, allow_redirects=True
            )

            if response.status_code == 200 and 'obras' in response.url:
                log_sucesso('Obras - Criar', 'Obra criada com sucesso')

                # Tenta extrair ID da obra criada
                import re

                match = re.search(r'obra/(\d+)', response.text)
                if match:
                    self.obra_id = match.group(1)
                    log_sucesso('Obras', f'ID da obra criada: {self.obra_id}')
            else:
                log_erro('Obras - Criar', f'Falha ao criar obra. Status: {response.status_code}')

            return True

        except Exception as e:
            log_erro('Obras', 'Erro nos testes de obras', e)
            return False

    def testar_lancamentos(self):
        """Testa funcionalidades de lançamentos"""
        print_secao('Testando Lançamentos')

        try:
            # Lista lançamentos
            response = self.session.get(f'{self.base_url}/lancamentos')
            if response.status_code == 200:
                log_sucesso('Lançamentos - Listar', 'Lista de lançamentos carregada')
            else:
                log_erro('Lançamentos - Listar', f'Status code: {response.status_code}')
                return False

            # Formulário novo lançamento
            response = self.session.get(f'{self.base_url}/lancamento/novo')
            if response.status_code == 200:
                log_sucesso('Lançamentos - Formulário', 'Formulário de novo lançamento carregado')

                # Extrai CSRF token
                import re

                match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', response.text)
                if match:
                    self.csrf_token = match.group(1)
            else:
                log_erro('Lançamentos - Formulário', f'Status code: {response.status_code}')
                return False

            # Cria novo lançamento
            lanc_data = {
                'csrf_token': self.csrf_token,
                'descricao': f'Lançamento Teste {datetime.now().strftime("%Y%m%d_%H%M%S")}',
                'tipo': 'Despesa',
                'categoria': 'Material',
                'valor': '1500.00',
                'data': date.today().strftime('%Y-%m-%d'),
                'status_pagamento': 'Pendente',
                'forma_pagamento': 'Transferência',
            }

            if self.obra_id:
                lanc_data['obra_id'] = self.obra_id

            response = self.session.post(
                f'{self.base_url}/lancamento/novo', data=lanc_data, allow_redirects=True
            )

            if response.status_code == 200 and 'lancamentos' in response.url:
                log_sucesso('Lançamentos - Criar', 'Lançamento criado com sucesso')
            else:
                log_erro(
                    'Lançamentos - Criar',
                    f'Falha ao criar lançamento. Status: {response.status_code}',
                )

            # Testa filtros
            response = self.session.get(f'{self.base_url}/lancamentos?tipo=Despesa')
            if response.status_code == 200:
                log_sucesso('Lançamentos - Filtro', 'Filtro por tipo funcionando')

            return True

        except Exception as e:
            log_erro('Lançamentos', 'Erro nos testes de lançamentos', e)
            return False

    def testar_orcamentos(self):
        """Testa funcionalidades de orçamentos"""
        print_secao('Testando Orçamentos')

        try:
            # Lista orçamentos
            response = self.session.get(f'{self.base_url}/orcamentos')
            if response.status_code == 200:
                log_sucesso('Orçamentos - Listar', 'Lista de orçamentos carregada')
            else:
                log_erro('Orçamentos - Listar', f'Status code: {response.status_code}')
                return False

            # Formulário novo orçamento
            response = self.session.get(f'{self.base_url}/orcamento/novo')
            if response.status_code == 200:
                log_sucesso('Orçamentos - Formulário', 'Formulário de novo orçamento carregado')

                # Extrai CSRF token
                import re

                match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', response.text)
                if match:
                    self.csrf_token = match.group(1)
            else:
                log_erro('Orçamentos - Formulário', f'Status code: {response.status_code}')
                return False

            # Cria novo orçamento
            orc_data = {
                'csrf_token': self.csrf_token,
                'cliente': f'Cliente Teste {datetime.now().strftime("%Y%m%d_%H%M%S")}',
                'cliente_email': 'teste@email.com',
                'titulo': f'Orçamento Teste {datetime.now().strftime("%Y%m%d_%H%M%S")}',
                'descricao': 'Descrição do orçamento de teste',
                'valor_materiais': '10000.00',
                'valor_mao_obra': '5000.00',
                'valor_equipamentos': '2000.00',
                'valor_outros': '1000.00',
                'desconto': '500.00',
                'prazo_execucao': '30',
                'validade': '15',
                'status': 'Rascunho',
                'forma_pagamento': '50% entrada + 50% na entrega',
                'observacoes': 'Observações de teste',
                'itens_json': json.dumps(
                    [
                        {
                            'categoria': 'Material',
                            'descricao': 'Item de teste 1',
                            'unidade': 'un',
                            'quantidade': 10,
                            'valor_unitario': 100.00,
                        },
                        {
                            'categoria': 'Mão de Obra',
                            'descricao': 'Item de teste 2',
                            'unidade': 'h',
                            'quantidade': 20,
                            'valor_unitario': 50.00,
                        },
                    ]
                ),
            }

            response = self.session.post(
                f'{self.base_url}/orcamento/novo', data=orc_data, allow_redirects=True
            )

            if response.status_code == 200 and 'orcamentos' in response.url:
                log_sucesso('Orçamentos - Criar', 'Orçamento criado com sucesso')

                # Tenta extrair ID do orçamento criado
                import re

                match = re.search(r'orcamento/(\d+)', response.text)
                if match:
                    self.orcamento_id = match.group(1)
                    log_sucesso('Orçamentos', f'ID do orçamento criado: {self.orcamento_id}')
            else:
                log_erro(
                    'Orçamentos - Criar',
                    f'Falha ao criar orçamento. Status: {response.status_code}',
                )
                # Tenta identificar erro
                if 'erro' in response.text.lower() or 'error' in response.text.lower():
                    log_aviso('Orçamentos', 'Possível mensagem de erro na resposta')

            # Testa filtros
            response = self.session.get(f'{self.base_url}/orcamentos?status=Rascunho')
            if response.status_code == 200:
                log_sucesso('Orçamentos - Filtro', 'Filtro por status funcionando')

            # Testa busca
            response = self.session.get(f'{self.base_url}/orcamentos?busca=teste')
            if response.status_code == 200:
                log_sucesso('Orçamentos - Busca', 'Busca por texto funcionando')

            return True

        except Exception as e:
            log_erro('Orçamentos', 'Erro nos testes de orçamentos', e)
            return False

    def testar_contratos(self):
        """Testa funcionalidades de contratos"""
        print_secao('Testando Contratos')

        try:
            # Lista contratos
            response = self.session.get(f'{self.base_url}/contratos')
            if response.status_code == 200:
                log_sucesso('Contratos - Listar', 'Lista de contratos carregada')
            else:
                log_erro('Contratos - Listar', f'Status code: {response.status_code}')
                return False

            # Formulário novo contrato
            response = self.session.get(f'{self.base_url}/contrato/novo')
            if response.status_code == 200:
                log_sucesso('Contratos - Formulário', 'Formulário de novo contrato carregado')

                # Extrai CSRF token
                import re

                match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', response.text)
                if match:
                    self.csrf_token = match.group(1)
            else:
                log_erro('Contratos - Formulário', f'Status code: {response.status_code}')
                return False

            # Cria novo contrato
            data_fim = date.today()
            data_fim = data_fim.replace(year=data_fim.year + 1)

            contrato_data = {
                'csrf_token': self.csrf_token,
                'cliente': f'Cliente Contrato {datetime.now().strftime("%Y%m%d_%H%M%S")}',
                'cliente_email': 'contrato@email.com',
                'titulo': f'Contrato Teste {datetime.now().strftime("%Y%m%d_%H%M%S")}',
                'descricao': 'Descrição do contrato de teste',
                'valor': '25000.00',
                'data_inicio': date.today().strftime('%Y-%m-%d'),
                'data_fim': data_fim.strftime('%Y-%m-%d'),
                'status': 'Rascunho',
                'tipo': 'Obra',
                'observacoes': 'Observações do contrato',
            }

            response = self.session.post(
                f'{self.base_url}/contrato/novo', data=contrato_data, allow_redirects=True
            )

            if response.status_code == 200 and 'contratos' in response.url:
                log_sucesso('Contratos - Criar', 'Contrato criado com sucesso')
            else:
                log_erro(
                    'Contratos - Criar', f'Falha ao criar contrato. Status: {response.status_code}'
                )

            # Testa filtros
            response = self.session.get(f'{self.base_url}/contratos?status=Rascunho')
            if response.status_code == 200:
                log_sucesso('Contratos - Filtro', 'Filtro por status funcionando')

            return True

        except Exception as e:
            log_erro('Contratos', 'Erro nos testes de contratos', e)
            return False

    def testar_fornecedores(self):
        """Testa funcionalidades de fornecedores"""
        print_secao('Testando Fornecedores')

        try:
            # Lista fornecedores
            response = self.session.get(f'{self.base_url}/fornecedores')
            if response.status_code == 200:
                log_sucesso('Fornecedores - Listar', 'Lista de fornecedores carregada')
            else:
                log_erro('Fornecedores - Listar', f'Status code: {response.status_code}')
                return False

            # Formulário novo fornecedor
            response = self.session.get(f'{self.base_url}/fornecedor/novo')
            if response.status_code == 200:
                log_sucesso('Fornecedores - Formulário', 'Formulário de novo fornecedor carregado')

                # Extrai CSRF token
                import re

                match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', response.text)
                if match:
                    self.csrf_token = match.group(1)
            else:
                log_erro('Fornecedores - Formulário', f'Status code: {response.status_code}')
                return False

            # Cria novo fornecedor
            forn_data = {
                'csrf_token': self.csrf_token,
                'nome': f'Fornecedor Teste {datetime.now().strftime("%Y%m%d_%H%M%S")}',
                'razao_social': 'Razão Social Teste LTDA',
                'cnpj': '12.345.678/0001-90',
                'email': 'fornecedor@email.com',
                'telefone': '(11) 1234-5678',
                'contato': 'Contato Teste',
                'categoria': 'Material',
                'endereco': 'Rua Fornecedor, 456',
                'cidade': 'São Paulo',
                'estado': 'SP',
            }

            response = self.session.post(
                f'{self.base_url}/fornecedor/novo', data=forn_data, allow_redirects=True
            )

            if response.status_code == 200 and 'fornecedores' in response.url:
                log_sucesso('Fornecedores - Criar', 'Fornecedor criado com sucesso')
            else:
                log_erro(
                    'Fornecedores - Criar',
                    f'Falha ao criar fornecedor. Status: {response.status_code}',
                )

            # Testa filtros
            response = self.session.get(f'{self.base_url}/fornecedores?categoria=Material')
            if response.status_code == 200:
                log_sucesso('Fornecedores - Filtro', 'Filtro por categoria funcionando')

            return True

        except Exception as e:
            log_erro('Fornecedores', 'Erro nos testes de fornecedores', e)
            return False

    def testar_relatorios(self):
        """Testa funcionalidades de relatórios"""
        print_secao('Testando Relatórios')

        try:
            # Acessa página de relatórios
            response = self.session.get(f'{self.base_url}/relatorios')
            if response.status_code == 200:
                log_sucesso('Relatórios', 'Página de relatórios carregada')
            else:
                log_erro('Relatórios', f'Status code: {response.status_code}')
                return False

            # Testa com filtros de data
            data_inicio = date.today().replace(day=1).strftime('%Y-%m-%d')
            response = self.session.get(f'{self.base_url}/relatorios?data_inicio={data_inicio}')
            if response.status_code == 200:
                log_sucesso('Relatórios - Filtro Data', 'Filtro por data funcionando')

            return True

        except Exception as e:
            log_erro('Relatórios', 'Erro nos testes de relatórios', e)
            return False

    def testar_api(self):
        """Testa endpoints da API"""
        print_secao('Testando API')

        try:
            # API Dashboard
            response = self.session.get(f'{self.base_url}/api/dashboard')
            if response.status_code == 200:
                try:
                    data = response.json()
                    log_sucesso('API - Dashboard', f'Dados recebidos: {list(data.keys())}')
                except:
                    log_aviso('API - Dashboard', 'Resposta não é JSON válido')
            else:
                log_erro('API - Dashboard', f'Status code: {response.status_code}')

            # API Obras
            if self.obra_id:
                response = self.session.get(f'{self.base_url}/api/obra/{self.obra_id}/dados')
                if response.status_code == 200:
                    log_sucesso('API - Obra', 'Dados da obra recebidos via API')

            return True

        except Exception as e:
            log_erro('API', 'Erro nos testes de API', e)
            return False

    def gerar_relatorio(self):
        """Gera relatório final dos testes"""
        print_secao('RELATÓRIO FINAL DOS TESTES')

        total_passou = len(TEST_RESULTS['passou'])
        total_falhou = len(TEST_RESULTS['falhou'])
        total_avisos = len(TEST_RESULTS['avisos'])
        total = total_passou + total_falhou

        print('\n📊 Resumo:')
        print(f'   ✅ Testes que passaram: {total_passou}')
        print(f'   ❌ Testes que falharam: {total_falhou}')
        print(f'   ⚠️  Avisos: {total_avisos}')
        print(f'   📈 Taxa de sucesso: {(total_passou / total * 100) if total > 0 else 0:.1f}%')

        if TEST_RESULTS['falhou']:
            print('\n❌ FUNÇÕES QUE FALHARAM:')
            for erro in TEST_RESULTS['falhou']:
                print(f'   - {erro["funcao"]}: {erro["mensagem"]}')

        if TEST_RESULTS['avisos']:
            print('\n⚠️  AVISOS:')
            for aviso in TEST_RESULTS['avisos']:
                print(f'   - {aviso["funcao"]}: {aviso["mensagem"]}')

        # Salva relatório em arquivo
        with open('relatorio_testes.txt', 'w', encoding='utf-8') as f:
            f.write('=' * 60 + '\n')
            f.write('RELATÓRIO DE TESTES - OBRAS-PRO\n')
            f.write(f'Data: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
            f.write('=' * 60 + '\n\n')

            f.write('RESUMO:\n')
            f.write(f'  Total de testes: {total}\n')
            f.write(f'  Passaram: {total_passou}\n')
            f.write(f'  Falharam: {total_falhou}\n')
            f.write(f'  Avisos: {total_avisos}\n')
            f.write(
                f'  Taxa de sucesso: {(total_passou / total * 100) if total > 0 else 0:.1f}%\n\n'
            )

            f.write('SUCESSOS:\n')
            for sucesso in TEST_RESULTS['passou']:
                f.write(f'  ✓ {sucesso["funcao"]}: {sucesso["mensagem"]}\n')

            if TEST_RESULTS['falhou']:
                f.write('\nFALHAS:\n')
                for erro in TEST_RESULTS['falhou']:
                    f.write(f'  ✗ {erro["funcao"]}: {erro["mensagem"]}\n')
                    if erro['erro']:
                        f.write(f'     Erro: {erro["erro"]}\n')

            if TEST_RESULTS['avisos']:
                f.write('\nAVISOS:\n')
                for aviso in TEST_RESULTS['avisos']:
                    f.write(f'  ! {aviso["funcao"]}: {aviso["mensagem"]}\n')

        print('\n💾 Relatório salvo em: relatorio_testes.txt')

        return total_falhou == 0


def main():
    """Função principal"""
    print('=' * 60)
    print('🧪 TESTADOR OBRAS-PRO')
    print('=' * 60)
    print('\nEste script testa todas as funcionalidades do sistema.')
    print(f'URL base: {BASE_URL}')
    print('\nCertifique-se de que:')
    print('  1. O servidor Flask está rodando')
    print('  2. Você tem um usuário válido para testes')
    print('=' * 60)

    # Pede credenciais
    print('\nCredenciais de teste:')
    email = input('Email [teste@exemplo.com]: ').strip() or 'teste@exemplo.com'
    senha = input('Senha [senha123]: ').strip() or 'senha123'

    # Cria instância do testador
    testador = TesteObrasPro(BASE_URL)

    # Executa testes
    print('\n' + '=' * 60)
    print('INICIANDO TESTES...')
    print('=' * 60)

    inicio = time.time()

    # Testes de autenticação
    if not testador.testar_login(email, senha):
        print('\n❌ Não foi possível fazer login. Verifique as credenciais.')
        sys.exit(1)

    # Testes das funcionalidades
    testador.testar_dashboard()
    testador.testar_obras()
    testador.testar_lancamentos()
    testador.testar_orcamentos()
    testador.testar_contratos()
    testador.testar_fornecedores()
    testador.testar_relatorios()
    testador.testar_api()

    # Gera relatório
    sucesso = testador.gerar_relatorio()

    tempo_total = time.time() - inicio
    print(f'\n⏱️  Tempo total de execução: {tempo_total:.2f} segundos')

    if sucesso:
        print('\n🎉 TODOS OS TESTES PASSARAM!')
        sys.exit(0)
    else:
        print('\n⚠️  ALGUNS TESTES FALHARAM. Verifique o relatório acima.')
        sys.exit(1)


if __name__ == '__main__':
    main()
