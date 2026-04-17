"""
Testes de Autenticacao em Duas Etapas (2FA)
"""

import pyotp


class Test2FAModel:
    """Testes dos metodos 2FA no modelo Usuario"""

    def test_enable_2fa_gera_secret(self, app):
        """Testa que enable_2fa gera secret e backup codes"""
        with app.app_context():
            from app.models import Usuario, Empresa, db
            from app.models.acesso import Role

            empresa = Empresa(nome='Teste', slug='teste', email='teste@test.com', plano='free')
            db.session.add(empresa)
            db.session.flush()

            role = Role.query.filter_by(nome='Administrador', is_system=True).first()
            usuario = Usuario(
                empresa_id=empresa.id,
                nome='Test',
                email='test@test.com',
                username='test',
                role='admin',
                role_id=role.id if role else None,
            )
            usuario.set_senha('test123')
            db.session.add(usuario)
            db.session.commit()

            secret = pyotp.random_base32()
            usuario.enable_2fa(secret)
            db.session.commit()

            assert usuario.totp_secret == secret
            assert usuario.two_factor_enabled is True
            assert usuario.backup_codes is not None

    def test_enable_2fa_gera_10_backup_codes(self, app):
        """Testa que enable_2fa gera exatamente 10 codigos de backup"""
        import json

        with app.app_context():
            from app.models import Usuario, Empresa, db
            from app.models.acesso import Role

            empresa = Empresa(nome='Test2', slug='teste2', email='teste2@test.com', plano='free')
            db.session.add(empresa)
            db.session.flush()

            role = Role.query.filter_by(nome='Administrador', is_system=True).first()
            usuario = Usuario(
                empresa_id=empresa.id,
                nome='Test',
                email='test2@test.com',
                username='test2',
                role='admin',
                role_id=role.id if role else None,
            )
            usuario.set_senha('test123')
            db.session.add(usuario)
            db.session.commit()

            secret = pyotp.random_base32()
            usuario.enable_2fa(secret)
            db.session.commit()

            codes = json.loads(usuario.backup_codes)
            assert len(codes) == 10
            assert all(len(code) == 10 for code in codes)

    def test_disable_2fa_remove_configuracao(self, app):
        """Testa que disable_2fa remove todas as configuracoes"""
        with app.app_context():
            from app.models import Usuario, Empresa, db
            from app.models.acesso import Role

            empresa = Empresa(nome='Test3', slug='teste3', email='teste3@test.com', plano='free')
            db.session.add(empresa)
            db.session.flush()

            role = Role.query.filter_by(nome='Administrador', is_system=True).first()
            usuario = Usuario(
                empresa_id=empresa.id,
                nome='Test',
                email='test3@test.com',
                username='test3',
                role='admin',
                role_id=role.id if role else None,
            )
            usuario.set_senha('test123')
            db.session.add(usuario)
            db.session.commit()

            secret = pyotp.random_base32()
            usuario.enable_2fa(secret)
            db.session.commit()

            usuario.disable_2fa()
            db.session.commit()

            assert usuario.totp_secret is None
            assert usuario.two_factor_enabled is False
            assert usuario.backup_codes is None

    def test_verify_2fa_token_valido(self, app):
        """Testa verificacao com token TOTP valido"""
        with app.app_context():
            from app.models import Usuario, Empresa, db
            from app.models.acesso import Role

            empresa = Empresa(nome='Test4', slug='teste4', email='teste4@test.com', plano='free')
            db.session.add(empresa)
            db.session.flush()

            role = Role.query.filter_by(nome='Administrador', is_system=True).first()
            usuario = Usuario(
                empresa_id=empresa.id,
                nome='Test',
                email='test4@test.com',
                username='test4',
                role='admin',
                role_id=role.id if role else None,
            )
            usuario.set_senha('test123')
            db.session.add(usuario)
            db.session.commit()

            secret = pyotp.random_base32()
            usuario.enable_2fa(secret)
            db.session.commit()

            totp = pyotp.TOTP(secret)
            token = totp.now()

            assert usuario.verify_2fa(token) is True

    def test_verify_2fa_token_invalido(self, app):
        """Testa verificacao com token TOTP invalido"""
        with app.app_context():
            from app.models import Usuario, Empresa, db
            from app.models.acesso import Role

            empresa = Empresa(nome='Test5', slug='teste5', email='teste5@test.com', plano='free')
            db.session.add(empresa)
            db.session.flush()

            role = Role.query.filter_by(nome='Administrador', is_system=True).first()
            usuario = Usuario(
                empresa_id=empresa.id,
                nome='Test',
                email='test5@test.com',
                username='test5',
                role='admin',
                role_id=role.id if role else None,
            )
            usuario.set_senha('test123')
            db.session.add(usuario)
            db.session.commit()

            secret = pyotp.random_base32()
            usuario.enable_2fa(secret)
            db.session.commit()

            assert usuario.verify_2fa('000000') is False

    def test_verify_2fa_backup_code_valido(self, app):
        """Testa verificacao com codigo de backup valido"""
        import json

        with app.app_context():
            from app.models import Usuario, Empresa, db
            from app.models.acesso import Role

            empresa = Empresa(nome='Test6', slug='teste6', email='teste6@test.com', plano='free')
            db.session.add(empresa)
            db.session.flush()

            role = Role.query.filter_by(nome='Administrador', is_system=True).first()
            usuario = Usuario(
                empresa_id=empresa.id,
                nome='Test',
                email='test6@test.com',
                username='test6',
                role='admin',
                role_id=role.id if role else None,
            )
            usuario.set_senha('test123')
            db.session.add(usuario)
            db.session.commit()

            secret = pyotp.random_base32()
            usuario.enable_2fa(secret)
            db.session.commit()

            codes = json.loads(usuario.backup_codes)
            backup_code = codes[0]

            assert usuario.verify_2fa(backup_code) is True

    def test_verify_2fa_backup_code_consumido(self, app):
        """Testa que.codigo de backup e consumido apos uso"""
        import json

        with app.app_context():
            from app.models import Usuario, Empresa, db
            from app.models.acesso import Role

            empresa = Empresa(nome='Test7', slug='teste7', email='teste7@test.com', plano='free')
            db.session.add(empresa)
            db.session.flush()

            role = Role.query.filter_by(nome='Administrador', is_system=True).first()
            usuario = Usuario(
                empresa_id=empresa.id,
                nome='Test',
                email='test7@test.com',
                username='test7',
                role='admin',
                role_id=role.id if role else None,
            )
            usuario.set_senha('test123')
            db.session.add(usuario)
            db.session.commit()

            secret = pyotp.random_base32()
            usuario.enable_2fa(secret)
            db.session.commit()

            codes = json.loads(usuario.backup_codes)
            backup_code = codes[0]

            usuario.verify_2fa(backup_code)

            codes_atualizado = json.loads(usuario.backup_codes)
            assert backup_code not in codes_atualizado

    def test_verify_2fa_sem_2fa_habilitado(self, app):
        """Testa que verificacao retorna False quando 2FA nao habilitado"""
        with app.app_context():
            from app.models import Usuario, Empresa, db
            from app.models.acesso import Role

            empresa = Empresa(nome='Test8', slug='teste8', email='teste8@test.com', plano='free')
            db.session.add(empresa)
            db.session.flush()

            role = Role.query.filter_by(nome='Administrador', is_system=True).first()
            usuario = Usuario(
                empresa_id=empresa.id,
                nome='Test',
                email='test8@test.com',
                username='test8',
                role='admin',
                role_id=role.id if role else None,
            )
            usuario.set_senha('test123')
            db.session.add(usuario)
            db.session.commit()

            usuario.two_factor_enabled = False
            db.session.commit()

            assert usuario.verify_2fa('anycode') is False

    def test_get_backup_codes_retorna_lista(self, app):
        """Testa que get_backup_codes retorna lista"""
        with app.app_context():
            from app.models import Usuario, Empresa, db
            from app.models.acesso import Role

            empresa = Empresa(nome='Test9', slug='teste9', email='teste9@test.com', plano='free')
            db.session.add(empresa)
            db.session.flush()

            role = Role.query.filter_by(nome='Administrador', is_system=True).first()
            usuario = Usuario(
                empresa_id=empresa.id,
                nome='Test',
                email='test9@test.com',
                username='test9',
                role='admin',
                role_id=role.id if role else None,
            )
            usuario.set_senha('test123')
            db.session.add(usuario)
            db.session.commit()

            secret = pyotp.random_base32()
            usuario.enable_2fa(secret)
            db.session.commit()

            codes = usuario.get_backup_codes()
            assert isinstance(codes, list)
            assert len(codes) == 10


class Test2FARoutes:
    """Testes das rotas 2FA"""

    def test_verificar_2fa_sem_sessao(self, client):
        """Testa que verificar_2fa sem sessao redireciona para login"""
        response = client.get('/auth/2fa/verificar', follow_redirects=True)
        assert response.status_code == 200

    def test_configurar_2fa_sem_login(self, client):
        """Testa que configurar_2fa sem login redireciona para login"""
        response = client.get('/auth/2fa/configurar', follow_redirects=True)
        assert response.status_code == 200
