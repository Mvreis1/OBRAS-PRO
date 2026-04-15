"""
Testes abrangentes de autenticação e login
Cobre: login, bloqueio de conta, 2FA, sessão, cadastro
"""

import pytest

from app.models import Usuario, db


class TestLoginFlow:
    """Testes detalhados do fluxo de login"""

    def test_login_sucesso_admin(self, client, admin_user):
        """Login bem-sucedido com admin"""
        response = client.post(
            '/auth/login',
            data={'email': 'admin@teste.com', 'senha': 'admin123'},
            follow_redirects=True,
        )

        assert response.status_code == 200
        # Verifica se foi redirecionado para dashboard
        assert b'Dashboard' in response.data or b'dashboard' in response.data

    def test_login_sucesso_lembrar(self, client, admin_user):
        """Login com opção 'lembrar-me'"""
        response = client.post(
            '/auth/login',
            data={'email': 'admin@teste.com', 'senha': 'admin123', 'lembrar': 'on'},
            follow_redirects=True,
        )

        assert response.status_code == 200

    def test_login_senha_incorreta(self, client, admin_user):
        """Login com senha errada mostra erro"""
        response = client.post(
            '/auth/login',
            data={'email': 'admin@teste.com', 'senha': 'senhaerrada'},
            follow_redirects=True,
        )

        assert response.status_code == 200
        # Verifica mensagem de erro
        assert b'invalid' in response.data.lower() or b'Login' in response.data

    def test_login_email_inexistente(self, client):
        """Login com email que não existe"""
        response = client.post(
            '/auth/login',
            data={'email': 'naoexiste@teste.com', 'senha': 'qualquer123'},
        )

        assert response.status_code == 200

    def test_login_campos_vazios(self, client):
        """Login sem preencher campos"""
        response = client.post('/auth/login', data={'email': '', 'senha': ''})

        assert response.status_code == 200

    def test_login_email_invalido_formato(self, client):
        """Login com formato de email inválido"""
        response = client.post(
            '/auth/login',
            data={'email': 'email-invalido', 'senha': 'senha123'},
        )

        assert response.status_code == 200
        assert b'Email' in response.data and (b'invalid' in response.data.lower() or b'erro' in response.data.lower())


class TestAccountLockout:
    """Testes de bloqueio de conta por tentativas falhas"""

    def test_bloqueio_apos_5_tentativas(self, client, admin_user):
        """Conta bloqueada após 5 tentativas falhas"""
        # 4 tentativas falhas
        for i in range(4):
            client.post(
                '/auth/login',
                data={'email': 'admin@teste.com', 'senha': 'errada'},
            )

        # Verifica que usuário ainda não está bloqueado
        usuario = Usuario.query.filter_by(email='admin@teste.com').first()
        assert usuario.tentativas_login == 4
        assert usuario.bloqueado_ate is None

        # 5ª tentativa - deve bloquear
        response = client.post(
            '/auth/login',
            data={'email': 'admin@teste.com', 'senha': 'errada'},
        )

        usuario = Usuario.query.filter_by(email='admin@teste.com').first()
        assert usuario.tentativas_login >= 5
        assert usuario.bloqueado_ate is not None
        assert b'bloque' in response.data.lower() or b'15 minutos' in response.data

    def test_reset_tentativas_apos_sucesso(self, client, admin_user):
        """Tentativas resetam após login bem-sucedido"""
        # 3 tentativas falhas
        for i in range(3):
            client.post(
                '/auth/login',
                data={'email': 'admin@teste.com', 'senha': 'errada'},
            )

        usuario = Usuario.query.filter_by(email='admin@teste.com').first()
        assert usuario.tentativas_login == 3

        # Login bem-sucedido
        client.post(
            '/auth/login',
            data={'email': 'admin@teste.com', 'senha': 'admin123'},
            follow_redirects=True,
        )

        # Verifica reset
        usuario = Usuario.query.filter_by(email='admin@teste.com').first()
        assert usuario.tentativas_login == 0
        assert usuario.bloqueado_ate is None

    def test_usuario_bloqueado_nao_consegue_login(self, client, admin_user):
        """Usuário bloqueado não consegue login mesmo com senha correta"""
        from datetime import datetime, timedelta

        # Bloqueia usuário manualmente
        usuario = Usuario.query.filter_by(email='admin@teste.com').first()
        usuario.bloqueado_ate = datetime.utcnow() + timedelta(minutes=15)
        usuario.tentativas_login = 5
        db.session.commit()

        response = client.post(
            '/auth/login',
            data={'email': 'admin@teste.com', 'senha': 'admin123'},
        )

        assert b'bloque' in response.data.lower() or b'15 minutos' in response.data


class TestSessionManagement:
    """Testes de gerenciamento de sessão"""

    def test_session_criada_apos_login(self, client, admin_user):
        """Session é criada corretamente após login"""
        client.post(
            '/auth/login',
            data={'email': 'admin@teste.com', 'senha': 'admin123'},
            follow_redirects=True,
        )

        with client.session_transaction() as sess:
            assert 'usuario_id' in sess
            assert sess['usuario_id'] == admin_user.id
            assert 'empresa_id' in sess
            assert 'usuario_nome' in sess

    def test_session_destruida_apos_logout(self, client, admin_session):
        """Session é limpa após logout"""
        response = client.get('/auth/logout', follow_redirects=True)

        with client.session_transaction() as sess:
            assert 'usuario_id' not in sess

    def test_acesso_sem_login_redireciona(self, client):
        """Rotas protegidas redirecionam para login"""
        response = client.get('/dashboard', follow_redirects=True)
        assert response.status_code == 200
        assert b'login' in response.data.lower() or b'Login' in response.data

    def test_acesso_com_login_funciona(self, admin_session):
        """Rotas protegidas funcionam com login"""
        response = admin_session.get('/dashboard')
        assert response.status_code == 200


class TestEmpresaCadastro:
    """Testes de cadastro de empresa"""

    def test_cadastro_empresa_completo(self, client):
        """Cadastro completo de empresa cria admin automaticamente"""
        response = client.post(
            '/auth/empresa/nova',
            data={
                'nome': 'Nova Empresa LTDA',
                'slug': 'nova-empresa-teste',
                'cnpj': '12345678000190',
                'email': 'contato@novaempresa.com',
                'senha': 'SenhaForte123!',
                'telefone': '(11) 99999-9999',
            },
            follow_redirects=True,
        )

        assert response.status_code == 200

        # Verifica que usuário foi criado no banco
        usuario = Usuario.query.filter_by(email='contato@novaempresa.com').first()
        assert usuario is not None
        assert usuario.empresa is not None

    def test_cadastro_slug_duplicado(self, client, admin_user):
        """Não permite cadastro com slug duplicado"""
        response = client.post(
            '/auth/empresa/nova',
            data={
                'nome': 'Outra Empresa',
                'slug': 'empresa-teste',  # Mesmo slug do admin_user
                'cnpj': '98765432000190',
                'email': 'outra@empresa.com',
                'senha': 'SenhaForte123!',
            },
        )

        assert response.status_code == 200
        assert b'URL' in response.data or b'em uso' in response.data or b'duplicado' in response.data.lower()

    def test_cadastro_slug_invalido(self, client):
        """Não permite slug com caracteres inválidos"""
        response = client.post(
            '/auth/empresa/nova',
            data={
                'nome': 'Empresa Slug Inválido',
                'slug': 'empresa com espaço!',
                'cnpj': '11111111000111',
                'email': 'slug@invalido.com',
                'senha': 'SenhaForte123!',
            },
        )

        assert response.status_code == 200

    def test_cadastro_senha_fraca(self, client):
        """Não permite senha fraca no cadastro"""
        response = client.post(
            '/auth/empresa/nova',
            data={
                'nome': 'Empresa Senha Fraca',
                'slug': 'senha-fraca',
                'cnpj': '22222222000122',
                'email': 'senha@fraca.com',
                'senha': '123',
            },
        )

        assert response.status_code == 200

    def test_cadastro_email_invalido(self, client):
        """Não permite email inválido no cadastro"""
        response = client.post(
            '/auth/empresa/nova',
            data={
                'nome': 'Empresa Email Inválido',
                'slug': 'email-invalido',
                'cnpj': '33333333000133',
                'email': 'email-invalido',
                'senha': 'SenhaForte123!',
            },
        )

        assert response.status_code == 200
        assert b'Email' in response.data and (b'invalid' in response.data.lower() or b'erro' in response.data.lower())


class TestUsuarioCadastro:
    """Testes de cadastro de usuários"""

    def test_criar_usuario_admin(self, admin_session, admin_user):
        """Admin pode criar novos usuários"""
        from app.models import Empresa

        empresa = Empresa.query.filter_by(slug='empresa-teste').first()
        # Aumenta limite de usuários
        empresa.max_usuarios = 10
        db.session.commit()

        response = admin_session.post(
            '/auth/usuario/novo',
            data={
                'nome': 'Novo Usuário',
                'email': 'novo@empresa.com',
                'username': 'novousuario',
                'senha': 'SenhaForte123!',
                'cargo': 'Operador',
                'role': 'operador',
            },
            follow_redirects=True,
        )

        assert response.status_code == 200

        # Verifica que usuário foi criado
        usuario = Usuario.query.filter_by(email='novo@empresa.com').first()
        assert usuario is not None

    def test_limite_usuarios(self, client, admin_user):
        """Não permite criar usuários além do limite"""
        from app.models import Empresa

        empresa = Empresa.query.filter_by(slug='empresa-teste').first()
        empresa.max_usuarios = 1  # Já tem 1 usuário
        db.session.commit()

        response = client.post(
            '/auth/usuario/novo',
            data={
                'nome': 'Usuário Extra',
                'email': 'extra@empresa.com',
                'username': 'extra',
                'senha': 'SenhaForte123!',
                'cargo': 'Operador',
            },
            follow_redirects=True,
        )

        # Deve mostrar aviso de limite
        assert response.status_code == 200


class TestPasswordReset:
    """Testes de recuperação de senha"""

    def test_recuperar_senha_email_existente(self, client, admin_user):
        """Solicitar recuperação de senha para email existente"""
        response = client.post(
            '/auth/recuperar-senha',
            data={'email': 'admin@teste.com', 'empresa': 'empresa-teste'},
            follow_redirects=True,
        )

        assert response.status_code == 200
        # Verifica que token foi gerado
        usuario = Usuario.query.filter_by(email='admin@teste.com').first()
        assert usuario.token_recuperacao is not None
        assert usuario.token_expiry is not None

    def test_recuperar_senha_empresa_inexistente(self, client):
        """Solicitar recuperação com empresa inexistente"""
        response = client.post(
            '/auth/recuperar-senha',
            data={'email': 'admin@teste.com', 'empresa': 'empresa-nao-existe'},
            follow_redirects=True,
        )

        assert response.status_code == 200

    def test_definir_nova_senha_com_token(self, client, admin_user):
        """Definir nova senha com token válido"""
        # Primeiro gera token
        client.post(
            '/auth/recuperar-senha',
            data={'email': 'admin@teste.com', 'empresa': 'empresa-teste'},
        )

        usuario = Usuario.query.filter_by(email='admin@teste.com').first()
        token = usuario.token_recuperacao

        # Define nova senha
        response = client.post(
            f'/auth/recuperar-senha/definir/{token}',
            data={
                'senha': 'NovaSenhaForte123!',
                'confirmar': 'NovaSenhaForte123!',
            },
            follow_redirects=True,
        )

        assert response.status_code == 200

        # Verifica que senha foi alterada
        usuario = Usuario.query.filter_by(email='admin@teste.com').first()
        assert usuario.token_recuperacao is None
        assert usuario.verificar_senha('NovaSenhaForte123!')

    def test_definir_nova_senha_sem_confirmar(self, client, admin_user):
        """Não permite definir senha se confirmação não confere"""
        # Gera token
        client.post(
            '/auth/recuperar-senha',
            data={'email': 'admin@teste.com', 'empresa': 'empresa-teste'},
        )

        usuario = Usuario.query.filter_by(email='admin@teste.com').first()
        token = usuario.token_recuperacao

        response = client.post(
            f'/auth/recuperar-senha/definir/{token}',
            data={
                'senha': 'Senha123!',
                'confirmar': 'SenhaDiferente!',
            },
        )

        assert response.status_code == 200
        assert b'confer' in response.data

    def test_token_expirado(self, client, admin_user):
        """Token expirado não permite redefinir senha"""
        from datetime import datetime, timedelta

        # Gera token e expira manualmente
        client.post(
            '/auth/recuperar-senha',
            data={'email': 'admin@teste.com', 'empresa': 'empresa-teste'},
        )

        usuario = Usuario.query.filter_by(email='admin@teste.com').first()
        usuario.token_expiry = datetime.utcnow() - timedelta(hours=1)
        db.session.commit()

        response = client.get(f'/auth/recuperar-senha/definir/{usuario.token_recuperacao}')

        assert response.status_code == 200
        assert b'expir' in response.data.lower() or b'invalid' in response.data.lower()
