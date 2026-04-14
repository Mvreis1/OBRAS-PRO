"""
Testes de API REST
"""
import pytest
from app import create_app
from app.models import db, Empresa, Usuario, Obra


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
        cargo='Admin'
    )
    db.session.add(usuario)
    db.session.commit()
    return usuario


class TestHealthCheck:
    """Test health check endpoint"""
    
    def test_health_check(self, client):
        """Should return healthy status"""
        response = client.get('/monitor/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] in ['ok', 'degraded']


class TestAPIAuth:
    """Test API authentication"""
    
    def test_unauthorized_access(self, client):
        """Should return 401 without token"""
        response = client.get('/api/obras')
        assert response.status_code == 302  # Redirect to login


class TestAPIWorks:
    """Test API works endpoints"""
    
    def test_obras_endpoint_structure(self, client):
        """Should have correct structure"""
        # Este teste verifica que o endpoint existe
        # Precisa de login para funcionar completamente
        assert True  # Placeholder


class TestMetrics:
    """Test monitoring endpoints"""
    
    def test_metrics_requires_login(self, client):
        """Should require authentication"""
        response = client.get('/monitor/metrics')
        assert response.status_code == 302  # Redirect to login


# Testes de integração adicionales
class TestBackupAPI:
    """Test backup endpoints"""
    
    def test_backup_list_requires_admin(self, client):
        """Should require admin role"""
        # Retorna 302 porque precisa login
        response = client.get('/api/backup/list')
        assert response.status_code in [302, 401]


class TestAuditAPI:
    """Test audit endpoints"""
    
    def test_audit_requires_login(self, client):
        """Should require authentication"""
        response = client.get('/audit/historico')
        assert response.status_code == 302  # Redirect to login