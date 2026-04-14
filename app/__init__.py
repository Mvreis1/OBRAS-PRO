"""
Aplicação principal
"""
import os
from flask import Flask, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from jinja2 import ChoiceLoader, FileSystemLoader
from app.models import db
from flask_caching import Cache
from flasgger import Swagger

from app.config import (
    SECRET_KEY, SESSION_COOKIE_SECURE, SESSION_COOKIE_HTTPONLY,
    SESSION_COOKIE_SAMESITE, PERMANENT_SESSION_LIFETIME,
    RATELIMIT_STORAGE_URL, RATELIMIT_DEFAULT, DB_PATH
)


def create_app():
    """Factory para criar a aplicação Flask"""
    app = Flask(__name__)

    # Configurar loader para incluir pasta de macros
    template_dirs = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'),
    ]
    app.jinja_loader = ChoiceLoader([
        FileSystemLoader(template_dirs),
        app.jinja_loader,
    ])
    
    # Configurações de segurança
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['SESSION_COOKIE_SECURE'] = SESSION_COOKIE_SECURE
    app.config['SESSION_COOKIE_HTTPONLY'] = SESSION_COOKIE_HTTPONLY
    app.config['SESSION_COOKIE_SAMESITE'] = SESSION_COOKIE_SAMESITE
    app.config['PERMANENT_SESSION_LIFETIME'] = PERMANENT_SESSION_LIFETIME
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    
    # Cache configuration
    cache_type = os.environ.get('CACHE_TYPE', 'simple')
    app.config['CACHE_TYPE'] = cache_type
    if cache_type == 'redis':
        app.config['CACHE_REDIS_URL'] = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    app.config['CACHE_DEFAULT_TIMEOUT'] = 300
    
    cache = Cache(app)
    
    # Rate Limiter
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=[RATELIMIT_DEFAULT],
        storage_uri=RATELIMIT_STORAGE_URL,
    )
    
    # Armazenar limiter no app para uso nas rotas
    app.limiter = limiter
    
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = False
    
    db.init_app(app)
    
    # Flask-Migrate (Alembic) para gerenciamento de migrations
    migrate = Migrate(app, db)
    
    # CSRF Protection global
    csrf = CSRFProtect(app)
    
    # Exempt login from CSRF
    from app.routes.auth import auth_bp
    csrf.exempt(auth_bp)
    
    # Configurar logging estruturado
    from app.utils.logging_utils import setup_logging
    setup_logging(app)
    
    # Configurar monitoramento
    from app.utils.monitoring import init_monitoring
    init_monitoring(app)
    
    # Configurar backup automático
    from app.utils.backup import setup_scheduled_backups
    setup_scheduled_backups(app)
    
    # Swagger para documentação da API
    from app.routes.api import swagger_template
    Swagger(app, template=swagger_template)
    
    # Registrar blueprints
    from app.routes import auth_bp, main_bp, ia_bp, banco_bp
    from app.routes.api import api_bp
    from app.routes.notificacoes import notif_bp
    from app.routes.extrato import extrato_bp
    from app.routes.contratos import contratos_bp
    from app.routes.orcamentos import orcamentos_bp
    from app.routes.fornecedores import fornecedores_bp
    from app.routes.rbac import rbac_bp
    from app.routes.excel import excel_bp
    from app.routes.audit import audit_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(api_bp, url_prefix='/api')  # API REST
    app.register_blueprint(main_bp)
    app.register_blueprint(ia_bp, url_prefix='/ia')
    app.register_blueprint(banco_bp, url_prefix='/banco')
    app.register_blueprint(notif_bp, url_prefix='/notificacoes')
    app.register_blueprint(extrato_bp, url_prefix='/extrato')
    app.register_blueprint(contratos_bp, url_prefix='/contrato')
    app.register_blueprint(orcamentos_bp, url_prefix='/orcamento')
    app.register_blueprint(fornecedores_bp, url_prefix='/fornecedor')
    app.register_blueprint(rbac_bp, url_prefix='/rbac')
    app.register_blueprint(excel_bp)
    app.register_blueprint(audit_bp, url_prefix='/audit')  # Histórico
    
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Registrar filtros e context processors
    from app.utils.templates import setup_filters, setup_context_processors
    setup_filters(app)
    setup_context_processors(app)
    
    with app.app_context():
        # Verifica se migrations existe e está configurado
        migrations_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'migrations')
        if os.path.exists(migrations_path) and os.path.exists(os.path.join(migrations_path, 'env.py')):
            # Migrations configurado - usar Alembic para gerenciar schema
            # db.create_all() não é necessário quando usando migrations
            pass
        else:
            # Sem migrations ainda - criar tabelas básicas (apenas dev/primeira vez)
            db.create_all()
    
    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        from flask import send_from_directory
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
