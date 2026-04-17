"""
Configuração da aplicação
"""

import os


def configure_app(app):
    """Aplica todas as configurações ao app"""
    from app.config import (
        CACHE_TYPE,
        DB_PATH,
        PERMANENT_SESSION_LIFETIME,
        REDIS_URL,
        SECRET_KEY,
        SESSION_COOKIE_HTTPONLY,
        SESSION_COOKIE_SAMESITE,
        SESSION_COOKIE_SECURE,
        SQLALCHEMY_ENGINE_OPTIONS,
        config,
    )

    # Configurações de segurança
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['SESSION_COOKIE_SECURE'] = SESSION_COOKIE_SECURE
    app.config['SESSION_COOKIE_HTTPONLY'] = SESSION_COOKIE_HTTPONLY
    app.config['SESSION_COOKIE_SAMESITE'] = SESSION_COOKIE_SAMESITE
    app.config['PERMANENT_SESSION_LIFETIME'] = PERMANENT_SESSION_LIFETIME

    # Upload
    app.config['UPLOAD_FOLDER'] = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'uploads'
    )
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

    # Cache
    app.config['CACHE_TYPE'] = CACHE_TYPE
    if CACHE_TYPE == 'redis':
        app.config['CACHE_REDIS_URL'] = REDIS_URL
    app.config['CACHE_DEFAULT_TIMEOUT'] = 300

    # Database
    _configure_database(app)

    return app


def _configure_database(app):
    """Configura conexão com banco de dados"""
    from app.config import config as config_func

    db_url = (
        config_func.DATABASE_URL
        if hasattr(config_func, 'DATABASE_URL')
        else config_func('DATABASE_URL', default=None)
    )

    if db_url:
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    else:
        from app.config import DB_PATH

        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = False

    from app.config import SQLALCHEMY_ENGINE_OPTIONS

    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = SQLALCHEMY_ENGINE_OPTIONS
