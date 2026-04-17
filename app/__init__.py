"""
Aplicação principal
"""

import os

from flasgger import Swagger
from flask import Flask, request, session
from jinja2 import ChoiceLoader, FileSystemLoader

from app.blueprints import register_blueprints, setup_template_utils
from app.config import FLASK_ENV, config
from app.config_loader import configure_app
from app.extensions import init_extensions
from app.models import db


def create_app():
    """Factory para criar a aplicação Flask"""
    app = Flask(__name__)

    # Template loaders
    _configure_templates(app)

    # Configurações
    configure_app(app)

    # Inicializar extensões
    init_extensions(app)

    # Security headers
    _add_security_headers(app)

    # Logging
    _setup_logging(app)

    # Monitoring
    _setup_monitoring(app)

    # Inicializa extensions
    from app.models.models import init_db

    init_db(app)

    # Backups
    _setup_backups(app)

    # Swagger (não produção)
    _setup_swagger(app)

    # Blueprints
    register_blueprints(app)
    setup_template_utils(app)

    # Uploads
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Criar tabelas
    _create_tables(app)

    # Inicializar seed data
    _seed_data(app)

    # Rotas especiais
    _register_special_routes(app)

    return app


def _configure_templates(app):
    """Configura loaders de template"""
    template_dirs = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'),
    ]
    app.jinja_loader = ChoiceLoader(
        [
            FileSystemLoader(template_dirs),
            app.jinja_loader,
        ]
    )


def _add_security_headers(app):
    """Adiciona headers de segurança"""

    @app.after_request
    def add_security_headers(response):
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        if FLASK_ENV == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            response.headers['Content-Security-Policy'] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdn.tailwindcss.com; "
                "font-src 'self' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https: blob:; "
                "connect-src 'self' https:; "
                "frame-ancestors 'none';"
            )
        return response


def _setup_logging(app):
    """Configura logging estruturado"""
    try:
        from app.utils.logging_utils import setup_logging

        setup_logging(app)
    except Exception as e:
        print(f'Logging nao inicializado: {e}')


def _setup_monitoring(app):
    """Configura monitoramento"""
    try:
        from app.utils.monitoring import init_monitoring

        init_monitoring(app)
    except Exception as e:
        print(f'Monitoramento nao inicializado: {e}')


def _setup_backups(app):
    """Configura backups automáticos"""
    try:
        from app.utils.backup import setup_scheduled_backups

        setup_scheduled_backups(app)
    except Exception as e:
        app.logger.warning(f'Backup automatico nao inicializado: {e}')


def _setup_swagger(app):
    """Configura Swagger (apenas desenvolvimento)"""
    if FLASK_ENV != 'production':
        try:
            from app.routes.api import swagger_template

            Swagger(app, template=swagger_template)
        except Exception as e:
            app.logger.warning(f'Swagger nao inicializado: {e}')


def _create_tables(app):
    """Cria tabelas do banco"""
    with app.app_context():
        try:
            db.create_all()
            app.logger.info('Tabelas do banco de dados criadas/verificadas')
        except Exception:
            pass


def _seed_data(app):
    """Inicializa dados básicos"""
    try:
        with app.app_context():
            from app.models.acesso import Role
            from app.models import Usuario, Empresa
            from seed_rbac import seed_permissoes, seed_roles

            if not Role.query.first():
                app.logger.info('Inicializando roles e permissoes...')
                seed_permissoes()
                seed_roles()
                db.session.commit()

            # Criar admin se não existir
            if not Usuario.query.filter_by(email='admin@demo.com').first():
                app.logger.info('Criando usuario admin...')
                empresa = Empresa.query.first() or Empresa(
                    nome='Demo Construções',
                    slug='demo',
                    email='admin@demo.com',
                    plano='enterprise',
                    max_usuarios=100,
                    max_obras=1000,
                )
                if not Empresa.query.first():
                    db.session.add(empresa)
                    db.session.flush()

                admin_role = Role.query.filter_by(nome='Administrador', is_system=True).first()
                admin = Usuario(
                    empresa_id=empresa.id,
                    nome='Admin Demo',
                    email='admin@demo.com',
                    username='admin',
                    cargo='Administrador',
                    role='admin',
                    role_id=admin_role.id if admin_role else None,
                )
                admin.set_senha('admin123')
                db.session.add(admin)
                db.session.commit()
                app.logger.info('Admin criado com sucesso')

    except Exception:
        pass


def _register_special_routes(app):
    """Registra rotas especiais (debug, health, etc.)"""
    _register_health_routes(app)
    _register_debug_routes(app)
    _register_demo_routes(app)


def _register_health_routes(app):
    """Rotas de health check"""

    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        from flask import send_from_directory

        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    @app.route('/healthz')
    def healthz_root():
        return {'status': 'ok', 'service': 'obras-pro'}, 200

    @app.route('/test')
    def test_page():
        return {'status': 'ok', 'message': 'Servidor funcionando'}, 200

    @app.route('/test-db')
    def test_db():
        try:
            from app.models import Empresa

            count = Empresa.query.count()
            return {'status': 'ok', 'empresas': count}, 200
        except Exception as e:
            return {'status': 'error', 'error': str(e)}, 500


def _register_debug_routes(app):
    """Rotas de debug (protegidas)"""

    @app.route('/debug/db')
    def debug_db():
        if FLASK_ENV == 'production':
            debug_key = config('DEBUG_SECRET_KEY', default=None)
            if not debug_key or request.args.get('key') != debug_key:
                return {'error': 'Forbidden'}, 403

        try:
            from app.models import Empresa, Usuario
            from app.models.acesso import Permissao, Role

            tables = {
                'roles': Role.query.count(),
                'permissoes': Permissao.query.count(),
                'empresas': Empresa.query.count(),
                'usuarios': Usuario.query.count(),
            }
            return {'status': 'ok', 'tables': tables}, 200
        except Exception as e:
            import traceback

            return {'status': 'error', 'error': str(e), 'traceback': traceback.format_exc()}, 500

    @app.route('/debug/user/<email>')
    def debug_user(email):
        if FLASK_ENV == 'production':
            debug_key = config('DEBUG_SECRET_KEY', default=None)
            if not debug_key or request.args.get('key') != debug_key:
                return {'error': 'Forbidden'}, 403

        try:
            from app.models import Usuario

            usuario = Usuario.query.filter_by(email=email).first()
            if usuario:
                return {
                    'status': 'ok',
                    'usuario': {
                        'id': usuario.id,
                        'email': usuario.email,
                        'username': usuario.username,
                        'ativo': usuario.ativo,
                        'empresa_id': usuario.empresa_id,
                        'role_id': usuario.role_id,
                        'two_factor_enabled': usuario.two_factor_enabled,
                    },
                }, 200
            else:
                usuarios = Usuario.query.all()
                return {
                    'status': 'not_found',
                    'email_procurado': email,
                    'usuarios_existentes': [{'id': u.id, 'email': u.email} for u in usuarios],
                }, 404
        except Exception as e:
            import traceback

            return {'status': 'error', 'error': str(e), 'traceback': traceback.format_exc()}, 500

    @app.route('/debug/config')
    def debug_config():
        if FLASK_ENV == 'production':
            debug_key = config('DEBUG_SECRET_KEY', default=None)
            if not debug_key or request.args.get('key') != debug_key:
                return {'error': 'Forbidden'}, 403

        try:
            from app.config import SQLALCHEMY_DATABASE_URI

            db_type = 'postgresql' if 'postgresql' in SQLALCHEMY_DATABASE_URI else 'sqlite'
            return {
                'status': 'ok',
                'config': {
                    'env': FLASK_ENV,
                    'db_type': db_type,
                    'has_secret_key': bool(app.config.get('SECRET_KEY')),
                },
            }, 200
        except Exception as e:
            import traceback

            return {'status': 'error', 'error': str(e), 'traceback': traceback.format_exc()}, 500


def _register_demo_routes(app):
    """Rotas de demo (desenvolvimento apenas)"""

    @app.route('/setup-demo')
    def setup_demo():
        if FLASK_ENV == 'production':
            return {'error': 'Not available in production'}, 403

        try:
            from app.models import Empresa, Usuario, db
            from app.models.acesso import Permissao, Role, RolePermissao

            # Criar role Administrador
            admin_role = Role.query.filter_by(nome='Administrador').first()
            if not admin_role:
                admin_role = Role(
                    nome='Administrador', descricao='Acesso total ao sistema', is_system=True
                )
                db.session.add(admin_role)
                db.session.flush()

            # Criar permissão básica
            perm = Permissao.query.filter_by(nome='Acesso Total').first()
            if not perm:
                perm = Permissao(
                    nome='Acesso Total',
                    descricao='Acesso completo ao sistema',
                    modulo='*',
                    acao='*',
                )
                db.session.add(perm)
                db.session.flush()

            # Associar
            if not RolePermissao.query.filter_by(
                role_id=admin_role.id, permissao_id=perm.id
            ).first():
                db.session.add(RolePermissao(role_id=admin_role.id, permissao_id=perm.id))

            # Criar empresa demo
            empresa = Empresa.query.filter_by(slug='demo').first()
            if not empresa:
                empresa = Empresa(
                    nome='Empresa Demo',
                    slug='demo',
                    cnpj='12345678000190',
                    email='demo@obraspro.com',
                    plano='pro',
                    max_usuarios=10,
                    max_obras=100,
                )
                db.session.add(empresa)
                db.session.flush()

            # Criar usuário admin
            if not Usuario.query.filter_by(email='admin@demo.com').first():
                usuario = Usuario(
                    empresa_id=empresa.id,
                    nome='Admin Demo',
                    email='admin@demo.com',
                    username='admin',
                    cargo='Administrador',
                    role='admin',
                    role_id=admin_role.id,
                    ativo=True,
                )
                usuario.set_senha('demo123')
                db.session.add(usuario)
                db.session.commit()

            return {
                'status': 'ok',
                'message': 'Conta de demonstracao criada!',
                'login_url': '/auth/login',
                'credentials': {'email': 'admin@demo.com', 'senha': 'demo123', 'empresa': 'demo'},
            }, 200

        except Exception as e:
            import traceback

            return {'status': 'error', 'error': str(e), 'traceback': traceback.format_exc()}, 500

    @app.route('/setup-dados-teste')
    def setup_dados_teste():
        if FLASK_ENV == 'production':
            return {'error': 'Not available in production'}, 403

        try:
            from datetime import date

            from app.models import Empresa, Lancamento, Obra, db

            empresa = Empresa.query.filter_by(slug='demo').first()
            if not empresa:
                return {
                    'status': 'error',
                    'message': 'Empresa demo nao encontrada. Execute /setup-demo primeiro',
                }, 400

            if Obra.query.filter_by(empresa_id=empresa.id).first():
                return {
                    'status': 'ok',
                    'message': 'Dados de teste ja existem para esta empresa',
                }, 200

            obra = Obra(
                empresa_id=empresa.id,
                nome='Obra Demo',
                descricao='Obra de demonstracao',
                endereco='Rua Demo, 123',
                orcamento_previsto=100000,
                data_inicio=date(2025, 1, 1),
                data_fim_prevista=date(2025, 12, 31),
                status='Em Execucao',
                progresso=50,
                responsavel='Eng. Demo',
                cliente='Cliente Demo',
            )
            db.session.add(obra)
            db.session.flush()

            lanc1 = Lancamento(
                empresa_id=empresa.id,
                obra_id=obra.id,
                descricao='Material de construcao',
                categoria='Materiais',
                tipo='Despesa',
                valor=5000,
                data=date(2025, 1, 15),
                forma_pagamento='Transferencia',
                status_pagamento='Pago',
                parcelas=1,
            )
            lanc2 = Lancamento(
                empresa_id=empresa.id,
                obra_id=obra.id,
                descricao='Receita de vendas',
                categoria='Vendas',
                tipo='Receita',
                valor=15000,
                data=date(2025, 1, 20),
                forma_pagamento='Transferencia',
                status_pagamento='Pago',
                parcelas=1,
            )
            db.session.add(lanc1)
            db.session.add(lanc2)
            db.session.commit()

            return {
                'status': 'ok',
                'message': 'Dados de teste criados com sucesso!',
                'dados_criados': {'obras': 1, 'lancamentos': 2},
            }, 200

        except Exception as e:
            import traceback

            return {'status': 'error', 'error': str(e), 'traceback': traceback.format_exc()}, 500

    @app.route('/setup-demo-completo')
    def setup_demo_completo():
        if FLASK_ENV == 'production':
            return {'error': 'Not available in production'}, 403

        try:
            from app.models import Empresa
            from app.utils.demo_data import criar_dados_demo_completos

            empresa = Empresa.query.filter_by(slug='demo').first()
            if not empresa:
                return {
                    'status': 'error',
                    'message': 'Empresa demo nao encontrada. Execute /setup-demo primeiro',
                }, 400

            resultado = criar_dados_demo_completos(empresa.id)
            return resultado, 200 if resultado['status'] == 'ok' else 400

        except Exception as e:
            import traceback

            return {'status': 'error', 'error': str(e), 'traceback': traceback.format_exc()}, 500
