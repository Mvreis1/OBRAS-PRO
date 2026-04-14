"""
Rotas da aplicação
"""
from app.routes.auth import auth_bp
from app.routes.main import main_bp
from app.routes.ia import ia_bp
from app.routes.banco import banco_bp

__all__ = ['auth_bp', 'main_bp', 'ia_bp', 'banco_bp']
