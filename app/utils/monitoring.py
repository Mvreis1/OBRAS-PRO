"""
Monitoramento e métricas do sistema OBRAS PRO
"""
import time
import psutil
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from app.routes.auth import login_required

monitor_bp = Blueprint('monitor', __name__)


class MetricsCollector:
    """Coletor de métricas do sistema"""
    
    @staticmethod
    def get_system_metrics():
        """Métricas do sistema"""
        return {
            'cpu_percent': psutil.cpu_percent(interval=0.1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
        }
    
    @staticmethod
    def get_app_metrics():
        """Métricas da aplicação"""
        from app.models import db
        from app.models import Obra, Lancamento, Usuario, Empresa
        
        # Contagens
        try:
            obras_count = Obra.query.count()
            lancamentos_count = Lancamento.query.count()
            usuarios_count = Usuario.query.count()
            empresas_count = Empresa.query.count()
            
            return {
                'obras': obras_count,
                'lancamentos': lancamentos_count,
                'usuarios': usuarios_count,
                'empresas': empresas_count,
                'database_connected': True
            }
        except:
            return {
                'database_connected': False
            }
    
    @staticmethod
    def get_request_stats():
        """Estatísticas de requisições (simples)"""
        from flask import g
        
        # Armazenar em g para tracking por request
        if not hasattr(g, 'request_start'):
            return {'status': 'no_data'}
        
        duration = time.time() - g.request_start
        return {
            'duration_ms': round(duration * 1000, 2)
        }


def require_admin(f):
    """Decorator para rotas de admin"""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import session
        if session.get('usuario_role') != 'admin':
            return jsonify({'error': 'Acesso restrito'}), 403
        return f(*args, **kwargs)
    return decorated


@monitor_bp.route('/health')
def health_check():
    """
    Health check da aplicação
    ---
    tags:
      - Monitoramento
    responses:
      200:
        description: Status de saúde
    """
    from app.models import db
    
    # Verificar banco de dados
    try:
        db.session.execute(db.text('SELECT 1'))
        db_status = 'healthy'
    except:
        db_status = 'unhealthy'
    
    return jsonify({
        'status': 'ok' if db_status == 'healthy' else 'degraded',
        'timestamp': datetime.utcnow().isoformat(),
        'services': {
            'database': db_status,
            'api': 'ok'
        }
    })


@monitor_bp.route('/metrics')
@login_required
def metrics():
    """
    Métricas do sistema
    ---
    tags:
      - Monitoramento
    responses:
      200:
        description: Métricas atuais
    """
    return jsonify({
        'system': MetricsCollector.get_system_metrics(),
        'app': MetricsCollector.get_app_metrics(),
        'timestamp': datetime.utcnow().isoformat()
    })


@monitor_bp.route('/metrics/requests')
@login_required
def request_metrics():
    """
    Métricas de requisições
    ---
    tags:
      - Monitoramento
    responses:
      200:
        description: Métricas de requests
    """
    return jsonify({
        'stats': MetricsCollector.get_request_stats(),
        'timestamp': datetime.utcnow().isoformat()
    })


@monitor_bp.route('/metrics/database')
@login_required
def database_metrics():
    """
    Métricas do banco de dados
    ---
    tags:
      - Monitoramento
    responses:
      200:
        description: Estatísticas do banco
    """
    from app.models import db
    
    try:
        # Queries lentas (simples)
        result = db.session.execute(db.text(
            "SELECT COUNT(*) as total FROM obras"
        )).fetchone()
        
        return jsonify({
            'tables': {
                'obras': result[0] if result else 0
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Middleware para trackar tempo de request
def init_monitoring(app):
    """Inicializa monitoramento na app"""
    from flask import g
    
    @app.before_request
    def start_timer():
        g.request_start = time.time()
    
    # Registrar blueprint
    app.register_blueprint(monitor_bp, url_prefix='/monitor')
    
    return app