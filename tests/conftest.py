"""
Configuracao de teste para o OBRAS FINANCEIRO
"""

import os

import pytest

from app import create_app
from app.models import db
from app.models.acesso import Role
from seed_rbac import seed_permissoes, seed_roles


@pytest.fixture
def app():
    """Cria app de teste com banco em memoria"""
    os.environ['SECRET_KEY'] = 'test-secret-key'
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

    # Desabilitar CSRF para testes
    app = create_app()
    app.config.update(
        {
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'SQLALCHEMY_ECHO': False,
            'WTF_CSRF_ENABLED': False,
            'SECRET_KEY': 'test-secret-key',
        }
    )

    with app.app_context():
        db.create_all()

        # Seed RBAC
        seed_permissoes()
        seed_roles()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Client HTTP para testes"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """CLI runner para testes"""
    return app.test_cli_runner()


@pytest.fixture
def admin_user(app):
    """Cria empresa e usuario admin para testes"""

    from app.models import Empresa, Usuario

    empresa = Empresa(
        nome='Empresa Teste',
        slug='empresa-teste',
        cnpj='12345678000190',
        email='teste@empresa.com',
        plano='free',
        max_usuarios=10,
        max_obras=50,
    )
    db.session.add(empresa)
    db.session.flush()

    admin_role = Role.query.filter_by(nome='Administrador', is_system=True).first()

    usuario = Usuario(
        empresa_id=empresa.id,
        nome='Admin Teste',
        email='admin@teste.com',
        username='admin',
        cargo='Administrador',
        role='admin',
        role_id=admin_role.id if admin_role else None,
    )
    usuario.set_senha('admin123')
    db.session.add(usuario)
    db.session.commit()

    return usuario


@pytest.fixture
def viewer_user(app):
    """Cria usuario viewer para testes de permissao"""
    from app.models import Empresa, Usuario

    empresa = Empresa.query.first()
    if not empresa:
        empresa = Empresa(
            nome='Empresa Viewer', slug='empresa-viewer', email='viewer@empresa.com', plano='free'
        )
        db.session.add(empresa)
        db.session.flush()

    viewer_role = Role.query.filter_by(nome='Visitante', is_system=True).first()

    usuario = Usuario(
        empresa_id=empresa.id,
        nome='Viewer Teste',
        email='viewer@teste.com',
        username='viewer',
        cargo='Visitante',
        role='viewer',
        role_id=viewer_role.id if viewer_role else None,
    )
    usuario.set_senha('viewer123')
    db.session.add(usuario)
    db.session.commit()

    return usuario


@pytest.fixture
def admin_session(client, admin_user):
    """Faz login como admin e retorna session"""
    with client.session_transaction() as sess:
        sess['usuario_id'] = admin_user.id
        sess['empresa_id'] = admin_user.empresa_id
        sess['empresa_nome'] = 'Empresa Teste'
        sess['empresa_slug'] = 'empresa-teste'
        sess['usuario_nome'] = admin_user.nome
        sess['usuario_username'] = admin_user.username
        sess['usuario_role'] = admin_user.role
    return client


@pytest.fixture
def viewer_session(client, viewer_user):
    """Faz login como viewer e retorna session"""
    with client.session_transaction() as sess:
        sess['usuario_id'] = viewer_user.id
        sess['empresa_id'] = viewer_user.empresa_id
        sess['empresa_nome'] = 'Empresa Viewer'
        sess['empresa_slug'] = 'empresa-viewer'
        sess['usuario_nome'] = viewer_user.nome
        sess['usuario_username'] = viewer_user.username
        sess['usuario_role'] = viewer_user.role
    return client
