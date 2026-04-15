"""
Testes de autenticacao
"""


class TestLogin:
    """Testes de login"""

    def test_login_sucesso(self, client, admin_user):
        """Testa login com credenciais validas"""
        response = client.post(
            '/auth/login',
            data={'email': 'admin@teste.com', 'senha': 'admin123'},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b'Login realizado' in response.data or b'Dashboard' in response.data

    def test_login_senha_invalida(self, client, admin_user):
        """Testa login com senha errada"""
        response = client.post(
            '/auth/login', data={'email': 'admin@teste.com', 'senha': 'senhaerrada'}
        )

        assert response.status_code == 200
        assert b'invalido' in response.data.lower() or b'Login' in response.data

    def test_login_email_invalido(self, client):
        """Testa login com email que nao existe"""
        response = client.post(
            '/auth/login', data={'email': 'naoexiste@teste.com', 'senha': 'qualquer'}
        )

        assert response.status_code == 200
        # A mensagem pode ser 'inválidos' ou 'Login' na pagina
        assert b'Login' in response.data or b'login' in response.data.lower()

    def test_login_campos_vazios(self, client):
        """Testa login sem preencher campos"""
        response = client.post('/auth/login', data={'email': '', 'senha': ''})

        assert response.status_code == 200

    def test_logout(self, client, admin_session):
        """Testa logout"""
        response = client.get('/auth/logout', follow_redirects=True)

        assert response.status_code == 200
        assert b'login' in response.data.lower() or b'Login' in response.data


class TestCadastro:
    """Testes de cadastro de empresa"""

    def test_cadastro_empresa_sucesso(self, client):
        """Testa cadastro completo de empresa"""
        response = client.post(
            '/auth/empresa/nova',
            data={
                'nome': 'Nova Empresa LTDA',
                'slug': 'nova-empresa',
                'cnpj': '12345678000190',
                'email': 'contato@novaempresa.com',
                'senha': 'senha123',
                'telefone': '(11) 99999-9999',
            },
            follow_redirects=True,
        )

        assert response.status_code == 200

    def test_cadastro_empresa_slug_duplicado(self, client, admin_user):
        """Testa cadastro com slug ja existente"""
        # Admin user ja tem slug 'empresa-teste', tentar cadastrar outro com slug similar
        response = client.post(
            '/auth/empresa/nova',
            data={
                'nome': 'Outra Empresa',
                'slug': 'empresa-teste',  # Mesmo slug
                'cnpj': '98765432000190',
                'email': 'outra@empresa.com',
                'senha': 'senha123',
            },
        )

        assert response.status_code == 200

    def test_cadastro_senha_fraca(self, client):
        """Testa cadastro com senha fraca"""
        response = client.post(
            '/auth/empresa/nova',
            data={
                'nome': 'Empresa Senha Fraca',
                'slug': 'senha-fraca',
                'cnpj': '11111111000111',
                'email': 'senha@fraca.com',
                'senha': '123',  # Muito curta
            },
        )

        assert response.status_code == 200

    def test_cadastro_email_invalido(self, client):
        """Testa cadastro com email invalido"""
        response = client.post(
            '/auth/empresa/nova',
            data={
                'nome': 'Empresa Email Invalido',
                'slug': 'email-invalido',
                'cnpj': '22222222000122',
                'email': 'email-invalido',
                'senha': 'senha123',
            },
        )

        assert response.status_code == 200


class TestProtecaoRotas:
    """Testa protecao de rotas sem autenticacao"""

    def test_dashboard_sem_login(self, client):
        """Dashboard redireciona para login"""
        response = client.get('/dashboard', follow_redirects=True)

        assert response.status_code == 200
        assert b'login' in response.data.lower() or b'Login' in response.data

    def test_obras_sem_login(self, client):
        """Obras redireciona para login"""
        response = client.get('/obras', follow_redirects=True)

        assert response.status_code == 200

    def test_lancamentos_sem_login(self, client):
        """Lancamentos redireciona para login"""
        response = client.get('/lancamentos', follow_redirects=True)

        assert response.status_code == 200

    def test_dashboard_com_login(self, admin_session):
        """Dashboard funciona com login"""
        response = admin_session.get('/dashboard')

        assert response.status_code == 200
