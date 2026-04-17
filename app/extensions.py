"""
Extensões Flask centralizadas
"""

from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

from app.config import (
    CACHE_TYPE,
    RATELIMIT_DEFAULT,
    RATELIMIT_STORAGE_URL,
    REDIS_URL,
)


def init_extensions(app):
    """Inicializa todas as extensões Flask"""
    # Cache
    app.cache = Cache(app)

    # Rate Limiter
    app.limiter = _init_limiter(app)

    # Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import Usuario

        return Usuario.query.get(int(user_id))

    # Flask-Migrate
    from app.models import db

    app.migrate = Migrate(app, db)

    # CSRF Protection
    csrf = CSRFProtect(app)
    _init_csrf(app, csrf)

    return app


def _init_limiter(app):
    """Inicializa o rate limiter"""
    try:
        use_redis = CACHE_TYPE == 'redis'
        limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            default_limits=[RATELIMIT_DEFAULT],
            storage_uri=RATELIMIT_STORAGE_URL if not use_redis else REDIS_URL,
            enabled=True,
            headers_enabled=True,
        )
        return limiter
    except Exception as e:
        app.logger.warning(f'Rate limiter nao inicializado: {e}')
        return None


def _init_csrf(app, csrf):
    """Configura CSRF protection com exceptions granulares"""
    from app.routes.api import api_bp
    from app.routes.audit import audit_bp
    from app.routes.excel import excel_bp
    from app.routes.extrato import extrato_bp

    csrf.exempt(api_bp)
    csrf.exempt(audit_bp)
    csrf.exempt(excel_bp)
    csrf.exempt(extrato_bp)
