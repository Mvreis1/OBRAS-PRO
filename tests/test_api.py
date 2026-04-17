"""
Testes de API REST
"""

import pytest

from app import create_app
from app.models import Empresa, Usuario, db


@pytest.fixture
def app():
    """Create application for testing"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client"""
    return app.test_client()


@pytest.fixture
def empresa(app):
    """Create test company"""
    empresa = Empresa(nome='Test Corp', slug='test', cnpj='12345678901', ativo=True)
    db.session.add(empresa)
    db.session.commit()
    return empresa


@pytest.fixture
def usuario(app, empresa):
    """Create test user"""
    usuario = Usuario(
        empresa_id=empresa.id,
        nome='Test User',
        email='test@test.com',
        username='testuser',
        senha_hash='hashed',
        cargo='Admin',
    )
    db.session.add(usuario)
    db.session.commit()
    return usuario


class TestHealthCheck:
    """Test health check endpoint"""

    def test_health_check_retorna_status_ok(self, client):
        """Health check deve retornar status ok"""
        response = client.get('/monitor/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] in ['ok', 'degraded']
        assert 'services' in data

    def test_health_check_inclui_timestamp(self, client):
        """Health check deve incluir timestamp"""
        response = client.get('/monitor/health')
        data = response.get_json()
        assert 'timestamp' in data

    def test_health_check_inclui_database_status(self, client):
        """Health check deve incluir status do banco"""
        response = client.get('/monitor/health')
        data = response.get_json()
        assert 'services' in data
        assert 'database' in data['services']


class TestAPIAuth:
    """Test API authentication"""

    def test_api_obras_sem_autenticacao_redireciona(self, client):
        """API sem autenticacao deve redirecionar para login"""
        response = client.get('/api/obras')
        assert response.status_code == 302
        assert '/auth/login' in response.location

    def test_api_lancamentos_sem_autenticacao_redireciona(self, client):
        """API lancamentos sem autenticacao deve redirecionar"""
        response = client.get('/api/lancamentos')
        assert response.status_code == 302
        assert '/auth/login' in response.location


class TestHealthEndpoint:
    """Test health endpoints"""

    def test_healthz_existe_e_responde(self, client):
        """Endpoint de health deve existir e responder"""
        response = client.get('/healthz')
        assert response.status_code == 200
        data = response.get_json()
        assert 'status' in data
        assert data['status'] == 'ok'

    def test_healthz_retorna_json_valido(self, client):
        """Health endpoint deve retornar JSON valido"""
        response = client.get('/healthz')
        assert response.status_code == 200
        assert response.content_type == 'application/json'
        data = response.get_json()
        assert isinstance(data, dict)


class TestMetrics:
    """Test monitoring endpoints"""

    def test_metrics_sem_login_redireciona(self, client):
        """Metrics sem login deve redirecionar para login"""
        response = client.get('/monitor/metrics')
        assert response.status_code == 302
        assert '/auth/login' in response.location

    def test_health_sem_login_responde(self, client):
        """Health check deve funcionar sem login (para load balancers)"""
        response = client.get('/healthz')
        assert response.status_code == 200


class TestBackupAPI:
    """Test backup endpoints"""

    def test_backup_list_sem_login_redireciona(self, client):
        """Backup list sem login deve redirecionar"""
        response = client.get('/api/backup/list')
        assert response.status_code == 302
        assert '/auth/login' in response.location


class TestAuditAPI:
    """Test audit endpoints"""

    def test_audit_sem_login_redireciona(self, client):
        """Audit sem login deve redirecionar"""
        response = client.get('/audit/historico')
        assert response.status_code == 302
        assert '/auth/login' in response.location

    def test_audit_com_login_retorna_200(self, client, app, empresa, usuario):
        """Audit com login deve retornar 200"""
        with client.session_transaction() as sess:
            sess['usuario_id'] = usuario.id
            sess['empresa_id'] = empresa.id

        response = client.get('/audit/historico')
        assert response.status_code == 200


class TestAPIResponseFormat:
    """Test API response format"""

    def test_health_retorna_json_valido(self, client):
        """Health endpoint deve retornar JSON valido"""
        response = client.get('/monitor/health')
        assert response.status_code == 200
        assert response.content_type == 'application/json'
        data = response.get_json()
        assert isinstance(data, dict)
        assert 'status' in data
        assert 'services' in data
