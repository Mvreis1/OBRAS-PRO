"""
Registro de Blueprints
"""


def register_blueprints(app):
    """Registra todos os blueprints da aplicação"""

    from app.routes import auth_bp, banco_bp, ia_bp, main_bp
    from app.routes.api import api_bp
    from app.routes.audit import audit_bp
    from app.routes.contratos import contratos_bp
    from app.routes.excel import excel_bp
    from app.routes.extrato import extrato_bp
    from app.routes.fornecedores import fornecedores_bp
    from app.routes.notificacoes import notif_bp
    from app.routes.orcamentos import orcamentos_bp
    from app.routes.rbac import rbac_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(api_bp, url_prefix='/api')
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
    app.register_blueprint(audit_bp, url_prefix='/audit')


def setup_template_utils(app):
    """Configura utilitários de template"""
    from app.utils.templates import setup_context_processors, setup_filters

    setup_filters(app)
    setup_context_processors(app)
