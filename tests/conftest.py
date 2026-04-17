"""
Configuracao de teste para o OBRAS FINANCEIRO
"""

import os

import pytest

from app import create_app
from app.models import db
from app.models.acesso import Role
from seed_rbac import seed_permissoes, seed_roles


@pytest.fixture(scope='session')
def app():
    """Cria app de teste com banco em memoria"""
    os.environ['SECRET_KEY'] = 'test-secret-key'
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_ECHO'] = False
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SERVER_NAME'] = 'localhost.localdomain'

    with app.app_context():
        db.create_all()
        seed_roles()
        seed_permissoes()

    yield app


@pytest.fixture
def app_context(app):
    """Fornece app context para os testes"""
    with app.app_context():
        yield


@pytest.fixture
def client(app):
    """Client HTTP para testes"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """CLI runner para testes"""
    return app.test_cli_runner()


@pytest.fixture
def admin_user(app_context, request):
    """Cria empresa e usuario admin para testes"""
    from app.models import Empresa, Usuario
    import uuid

    unique_slug = f'empresa-teste-{uuid.uuid4().hex[:8]}'

    empresa = Empresa(
        nome='Empresa Teste',
        slug=unique_slug,
        cnpj='12345678000190',
        email='teste@empresa.com',
        plano='free',
        max_usuarios=10,
        max_obras=50,
    )
    db.session.add(empresa)
    db.session.flush()

    admin_role = Role.query.filter_by(nome='Administrador', is_system=True).first()
    if not admin_role:
        admin_role = Role(nome='Administrador', descricao='Admin', is_system=True)
        db.session.add(admin_role)
        db.session.flush()

    from app.models.acesso import Permissao, RolePermissao

    perm = Permissao.query.filter_by(modulo='*', acao='*').first()
    if not perm:
        perm = Permissao(nome='Acesso Total', modulo='*', acao='*')
        db.session.add(perm)
        db.session.flush()

    existing_link = RolePermissao.query.filter_by(
        role_id=admin_role.id, permissao_id=perm.id
    ).first()
    if not existing_link:
        db.session.add(RolePermissao(role_id=admin_role.id, permissao_id=perm.id))

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

    db.session.refresh(usuario)
    return usuario


@pytest.fixture
def obra_teste(app_context, admin_user):
    """Cria uma obra de teste"""
    from app.models import Obra
    from datetime import date

    obra = Obra(
        empresa_id=admin_user.empresa_id,
        nome='Obra Teste',
        descricao='Obra para testes',
        orcamento_previsto=100000.00,
        data_inicio=date.today(),
        data_fim_prevista=date.today(),
        status='ativa',
    )
    db.session.add(obra)
    db.session.commit()
    db.session.refresh(obra)
    return obra


@pytest.fixture
def viewer_user(app_context):
    """Cria usuario viewer para testes de permissao"""
    from app.models import Empresa, Usuario
    import uuid

    unique_slug = f'empresa-viewer-{uuid.uuid4().hex[:8]}'

    empresa = Empresa(
        nome='Empresa Viewer',
        slug=unique_slug,
        email='viewer@empresa.com',
        plano='free',
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

    db.session.refresh(usuario)
    return usuario


@pytest.fixture
def admin_session(client, admin_user):
    """Faz login como admin e retorna session"""
    from app.models import Empresa

    empresa = db.session.get(Empresa, admin_user.empresa_id)
    with client.session_transaction() as sess:
        sess['usuario_id'] = admin_user.id
        sess['empresa_id'] = admin_user.empresa_id
        sess['empresa_nome'] = empresa.nome
        sess['empresa_slug'] = empresa.slug
        sess['usuario_nome'] = admin_user.nome
        sess['usuario_username'] = admin_user.username
        sess['usuario_role'] = admin_user.role
    return client


@pytest.fixture
def viewer_session(client, viewer_user):
    """Faz login como viewer e retorna session"""
    from app.models import Empresa

    empresa = db.session.get(Empresa, viewer_user.empresa_id)
    with client.session_transaction() as sess:
        sess['usuario_id'] = viewer_user.id
        sess['empresa_id'] = viewer_user.empresa_id
        sess['empresa_nome'] = empresa.nome
        sess['empresa_slug'] = empresa.slug
        sess['usuario_nome'] = viewer_user.nome
        sess['usuario_username'] = viewer_user.username
        sess['usuario_role'] = viewer_user.role
    return client
