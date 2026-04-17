"""
Testes de autenticacao
"""

from app.models import Empresa


class TestLogin:
    """Testes de login"""

    def test_login_sucesso(self, client, admin_user):
        """Testa login com credenciais validas e redireciona para dashboard"""
        response = client.post(
            '/auth/login',
            data={'email': 'admin@teste.com', 'senha': 'admin123'},
            follow_redirects=True,
        )

        assert response.status_code == 200
        # Verifica que foi para dashboard (não ficou na página de login)
        assert b'/dashboard' in response.data or b'Dashboard' in response.data
        # Verifica que há elementos do dashboard
        assert b'obras' in response.data.lower() or b'Obras' in response.data

    def test_login_senha_invalida(self, client, admin_user):
        """Testa login com senha errada mostra mensagem de erro"""
        response = client.post(
            '/auth/login', data={'email': 'admin@teste.com', 'senha': 'senhaerrada'}
        )

        assert response.status_code == 200
        # Deve mostrar mensagem de erro específica
        assert b'invalido' in response.data.lower() or b'incorreta' in response.data.lower()
        # Não deve redirecionar para dashboard
        assert b'/dashboard' not in response.data.decode()

    def test_login_email_invalido(self, client):
        """Testa login com email inexistente"""
        response = client.post(
            '/auth/login', data={'email': 'naoexiste@teste.com', 'senha': 'qualquer'}
        )

        assert response.status_code == 200
        # Deve permanecer na página de login
        assert b'/auth/login' in response.data or b'<form' in response.data
        # Deve mostrar erro específico
        assert b'encontrado' in response.data.lower() or b'invalido' in response.data.lower()

    def test_login_campos_vazios(self, client):
        """Testa login sem preencher campos retorna erro"""
        response = client.post('/auth/login', data={'email': '', 'senha': ''})

        assert response.status_code == 200
        # Não deve autenticar
        assert b'/dashboard' not in response.data.decode()

    def test_logout(self, client, admin_session):
        """Testa logout limpa sessão e redireciona para login"""
        response = client.get('/auth/logout', follow_redirects=True)

        assert response.status_code == 200
        # Deve redirecionar para página de login
        assert b'/auth/login' in response.data or b'login' in response.data.lower()


class TestCadastro:
    """Testes de cadastro de empresa"""

    def test_cadastro_empresa_sucesso(self, client, app):
        """Testa cadastro completo de empresa cria empresa no banco"""
        response = client.post(
            '/auth/empresa/nova',
            data={
                'nome': 'Nova Empresa LTDA',
                'slug': 'nova-empresa-unique',
                'cnpj': '12345678000190',
                'email': 'contato@novaempresatest.com',
                'senha': 'senha123',
                'telefone': '(11) 99999-9999',
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        # Verifica que empresa foi criada no banco
        with app.app_context():
            empresa = Empresa.query.filter_by(slug='nova-empresa-unique').first()
            assert empresa is not None
            assert empresa.nome == 'Nova Empresa LTDA'
            assert empresa.email == 'contato@novaempresatest.com'

    def test_cadastro_empresa_slug_duplicado(self, client, admin_user):
        """Testa cadastro com slug duplicado mostra erro"""
        response = client.post(
            '/auth/empresa/nova',
            data={
                'nome': 'Outra Empresa',
                'slug': 'empresa-teste',
                'cnpj': '98765432000190',
                'email': 'outra@empresa.com',
                'senha': 'senha123',
            },
        )

        assert response.status_code == 200
        # Deve mostrar erro específico de slug duplicado
        assert b'duplicado' in response.data.lower() or b'existe' in response.data.lower()
        # Não deve criar empresa com mesmo slug
        assert response.data.count(b'empresa-teste') > 1  # Form e erro

    def test_cadastro_senha_fraca(self, client):
        """Testa cadastro com senha fraca mostra erro de validação"""
        response = client.post(
            '/auth/empresa/nova',
            data={
                'nome': 'Empresa Senha Fraca',
                'slug': 'senha-fraca-unique',
                'cnpj': '11111111000111',
                'email': 'senha@fracatest.com',
                'senha': '123',
            },
        )

        assert response.status_code == 200
        # Deve mostrar erro de validacao de senha
        assert b'senha' in response.data.lower() and (
            b'curta' in response.data.lower()
            or b'fraca' in response.data.lower()
            or b'minimo' in response.data.lower()
        )

    def test_cadastro_email_invalido(self, client):
        """Testa cadastro com email invalido mostra erro"""
        response = client.post(
            '/auth/empresa/nova',
            data={
                'nome': 'Empresa Email Invalido',
                'slug': 'email-invalido-unique',
                'cnpj': '22222222000122',
                'email': 'email-invalido',
                'senha': 'senha123',
            },
        )

        assert response.status_code == 200
        # Deve mostrar erro de email invalido
        assert b'email' in response.data.lower() and (
            b'invalido' in response.data.lower() or b'incorreto' in response.data.lower()
        )


class TestProtecaoRotas:
    """Testa proteção de rotas sem autenticação"""

    def test_dashboard_sem_login(self, client):
        """Dashboard sem login redireciona para login"""
        response = client.get('/dashboard', follow_redirects=True)

        assert response.status_code == 200
        # Deve estar na página de login
        assert b'/auth/login' in response.data or (
            b'login' in response.data.lower() and b'<form' in response.data
        )

    def test_obras_sem_login(self, client):
        """Obras sem login redireciona para login"""
        response = client.get('/obras', follow_redirects=True)

        assert response.status_code == 200
        # Deve redirecionar para login
        assert b'/auth/login' in response.data or (
            b'login' in response.data.lower() and b'<form' in response.data
        )

    def test_lancamentos_sem_login(self, client):
        """Lancamentos sem login redireciona para login"""
        response = client.get('/lancamentos', follow_redirects=True)

        assert response.status_code == 200
        # Deve redirecionar para login
        assert b'/auth/login' in response.data or (
            b'login' in response.data.lower() and b'<form' in response.data
        )

    def test_dashboard_com_login(self, admin_session):
        """Dashboard funciona corretamente com login"""
        response = admin_session.get('/dashboard')

        assert response.status_code == 200
        # Verifica que é realmente o dashboard
        assert b'Obras' in response.data or b'obras' in response.data.lower()
        # Não deve ter formulário de login
        assert b'/auth/login' not in response.data.decode()
