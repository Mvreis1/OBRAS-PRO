"""
Aplicação principal
"""

import os

from flasgger import Swagger
from flask import Flask, request, session
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from jinja2 import ChoiceLoader, FileSystemLoader

from app.config import (
    CACHE_TYPE,
    DB_PATH,
    FLASK_ENV,
    PERMANENT_SESSION_LIFETIME,
    RATELIMIT_DEFAULT,
    RATELIMIT_STORAGE_URL,
    REDIS_URL,
    SECRET_KEY,
    SESSION_COOKIE_HTTPONLY,
    SESSION_COOKIE_SAMESITE,
    SESSION_COOKIE_SECURE,
    config,
)
from app.models import db


def create_app():
    """Factory para criar a aplicação Flask"""
    app = Flask(__name__)

    # Configurar loader para incluir pasta de macros
    template_dirs = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'),
    ]
    app.jinja_loader = ChoiceLoader(
        [
            FileSystemLoader(template_dirs),
            app.jinja_loader,
        ]
    )

    # Configurações de segurança
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['SESSION_COOKIE_SECURE'] = SESSION_COOKIE_SECURE
    app.config['SESSION_COOKIE_HTTPONLY'] = SESSION_COOKIE_HTTPONLY
    app.config['SESSION_COOKIE_SAMESITE'] = SESSION_COOKIE_SAMESITE
    app.config['PERMANENT_SESSION_LIFETIME'] = PERMANENT_SESSION_LIFETIME
    app.config['UPLOAD_FOLDER'] = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'uploads'
    )
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

    # Cache configuration
    app.config['CACHE_TYPE'] = CACHE_TYPE
    if CACHE_TYPE == 'redis':
        app.config['CACHE_REDIS_URL'] = REDIS_URL
    app.config['CACHE_DEFAULT_TIMEOUT'] = 300

    Cache(app)

    # Rate Limiter - habilitado em todos os ambientes
    # Em produção, usar Redis se disponível para rate limiting distribuído
    limiter = None
    try:
        # Em produção com Redis, usar storage distribuído
        use_redis = CACHE_TYPE == 'redis'

        limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            default_limits=[RATELIMIT_DEFAULT],
            storage_uri=RATELIMIT_STORAGE_URL if not use_redis else REDIS_URL,
            enabled=True,
            headers_enabled=True,
        )
    except Exception as e:
        app.logger.warning(f'Rate limiter nao inicializado: {e}')
        limiter = None

    # Armazenar limiter no app para uso nas rotas
    app.limiter = limiter

    db_url = (
        config.DATABASE_URL
        if hasattr(config, 'DATABASE_URL')
        else config('DATABASE_URL', default=None)
    )
    if db_url:
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = False

    # Configurações de pool para PostgreSQL
    from app.config import SQLALCHEMY_ENGINE_OPTIONS

    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = SQLALCHEMY_ENGINE_OPTIONS

    db.init_app(app)

    # Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import Usuario

        return Usuario.query.get(int(user_id))

    # Flask-Migrate (Alembic) para gerenciamento de migrations
    Migrate(app, db)

    # CSRF Protection global
    csrf = CSRFProtect(app)

    # Exempt login from CSRF (necessário para APIs externas)
    from app.routes.auth import auth_bp

    csrf.exempt(auth_bp)

    # Security Headers - proteger contra XSS, clickjacking, etc.
    @app.after_request
    def add_security_headers(response):
        """Adicionar headers de segurança em todas as respostas"""
        # Prevenir clickjacking
        response.headers['X-Frame-Options'] = 'DENY'
        # Prevenir MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        # Habilitar XSS filter em browsers antigos
        response.headers['X-XSS-Protection'] = '1; mode=block'
        # Forçar HTTPS em produção
        if FLASK_ENV == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        # Prevenir vazamento de referrer
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        # Content Security Policy básica
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://cdn.jsdelivr.net;"
        )
        # Prevenir cache de páginas sensíveis
        if 'text/html' in response.headers.get('Content-Type', ''):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
        return response

    # CORS Configuration
    @app.after_request
    def add_cors_headers(response):
        """Configurar CORS para APIs"""
        # Permitir CORS apenas para origens específicas em produção
        allowed_origins = config(
            'ALLOWED_ORIGINS', default='', cast=lambda s: s.split(',') if s else []
        )
        origin = request.headers.get('Origin', '')

        if origin and origin in allowed_origins:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Max-Age'] = '3600'

        return response

    # Configurar logging estruturado - habilitado em todos os ambientes
    # Em produção, usar formato JSON para integração com ELK/Datadog
    try:
        from app.utils.logging_utils import setup_logging

        setup_logging(app)
    except Exception as e:
        print(f'Logging nao inicializado: {e}')

    # Configurar monitoramento - sempre registrar health check (necessário para Render)
    try:
        from app.utils.monitoring import init_monitoring

        init_monitoring(app)
    except Exception as e:
        print(f'Monitoramento nao inicializado: {e}')

    # Configurar backup automático - habilitado em todos os ambientes
    try:
        from app.utils.backup import setup_scheduled_backups

        setup_scheduled_backups(app)
    except Exception as e:
        app.logger.warning(f'Backup automatico nao inicializado: {e}')

    # Swagger para documentação da API - apenas em desenvolvimento
    if FLASK_ENV != 'production':
        try:
            from app.routes.api import swagger_template

            Swagger(app, template=swagger_template)
        except Exception as e:
            app.logger.warning(f'Swagger nao inicializado: {e}')

    # Registrar blueprints
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
    from app.utils.templates import setup_context_processors, setup_filters

    setup_filters(app)
    setup_context_processors(app)

    with app.app_context():
        # Criar tabelas se não existirem (necessário para deploy no Render)
        try:
            db.create_all()
            app.logger.info('Tabelas do banco de dados criadas/verificadas')
        except Exception as e:
            app.logger.error(f'Erro ao criar tabelas: {e}')
            import traceback

            app.logger.error(traceback.format_exc())

        # Inicializar dados básicos (roles, permissões)
        try:
            from app.models.acesso import Role
            from seed_rbac import seed_permissoes, seed_roles

            # Verificar se já existe roles
            if not Role.query.first():
                app.logger.info('Inicializando roles e permissoes...')
                seed_permissoes()
                seed_roles()
                db.session.commit()
                app.logger.info('Dados iniciais criados')
        except Exception as e:
            app.logger.error(f'Erro ao inicializar dados: {e}')
            import traceback

            app.logger.error(traceback.format_exc())
            db.session.rollback()

    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        from flask import send_from_directory

        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # Rota raiz simples para health check básico (sem banco de dados)
    @app.route('/healthz')
    def healthz_root():
        """Health check para Render - sem dependência de banco"""
        return {'status': 'ok', 'service': 'obras-pro'}, 200

    # Rota de diagnóstico do banco de dados - protegida em produção
    @app.route('/debug/db')
    def debug_db():
        """Diagnóstico do banco de dados - apenas desenvolvimento"""
        # Proteger em produção com secret key
        if FLASK_ENV == 'production':
            from flask import request

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

    # Rota de diagnóstico de usuário específico - protegida em produção
    @app.route('/debug/user/<email>')
    def debug_user(email):
        """Diagnóstico de usuário específico - apenas desenvolvimento"""
        # Proteger em produção com secret key
        if FLASK_ENV == 'production':
            from flask import request

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
                        # Removido senha_hash_prefix por segurança
                        'two_factor_enabled': usuario.two_factor_enabled,
                    },
                }, 200
            else:
                # Listar todos os usuários
                usuarios = Usuario.query.all()
                return {
                    'status': 'not_found',
                    'email_procurado': email,
                    'usuarios_existentes': [{'id': u.id, 'email': u.email} for u in usuarios],
                }, 404
        except Exception as e:
            import traceback

            return {'status': 'error', 'error': str(e), 'traceback': traceback.format_exc()}, 500

    # Rota para criar conta de teste - APENAS desenvolvimento
    @app.route('/setup-demo')
    def setup_demo():
        """Cria conta de demonstração com seed simplificado - DESABILITADO EM PRODUÇÃO"""
        # DESABILITADO EM PRODUÇÃO - risco de segurança
        if FLASK_ENV == 'production':
            return {'error': 'Not available in production'}, 403

        try:
            from app.models import Empresa, Usuario, db
            from app.models.acesso import Permissao, Role, RolePermissao

            # Criar role Administrador básico se não existir
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

            # Associar permissão ao role
            assoc = RolePermissao.query.filter_by(
                role_id=admin_role.id, permissao_id=perm.id
            ).first()
            if not assoc:
                assoc = RolePermissao(role_id=admin_role.id, permissao_id=perm.id)
                db.session.add(assoc)

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
            usuario = Usuario.query.filter_by(email='admin@demo.com').first()
            if not usuario:
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
                'message': 'Conta de demonstração criada!',
                'login_url': '/auth/login',
                'credentials': {'email': 'admin@demo.com', 'senha': 'demo123', 'empresa': 'demo'},
            }, 200

        except Exception as e:
            import traceback

            return {'status': 'error', 'error': str(e), 'traceback': traceback.format_exc()}, 500

    # Rota para popular dados fictícios de teste - APENAS desenvolvimento
    @app.route('/setup-dados-teste')
    def setup_dados_teste():
        """Popula o banco com dados fictícios minimos para demonstração - DESABILITADO EM PRODUÇÃO"""
        # DESABILITADO EM PRODUÇÃO - risco de segurança
        if FLASK_ENV == 'production':
            return {'error': 'Not available in production'}, 403

        try:
            from datetime import date

            from app.models import Empresa, Lancamento, Obra, db

            # Buscar empresa demo
            empresa = Empresa.query.filter_by(slug='demo').first()
            if not empresa:
                return {
                    'status': 'error',
                    'message': 'Empresa demo nao encontrada. Execute /setup-demo primeiro',
                }, 400

            # Verificar se já existem obras
            if Obra.query.filter_by(empresa_id=empresa.id).first():
                return {
                    'status': 'ok',
                    'message': 'Dados de teste ja existem para esta empresa',
                }, 200

            # Criar apenas 1 obra simples
            obra = Obra(
                empresa_id=empresa.id,
                nome='Obra Demo',
                descricao='Obra de demonstração',
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

            # Criar apenas 2 lançamentos simples
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

    # Rota para criar dados completos de demonstração - APENAS desenvolvimento
    @app.route('/setup-demo-completo')
    def setup_demo_completo():
        """Cria dados completos de demonstração - DESABILITADO EM PRODUÇÃO"""
        # DESABILITADO EM PRODUÇÃO - risco de segurança
        if FLASK_ENV == 'production':
            return {'error': 'Not available in production'}, 403

        try:
            from app.models import Empresa
            from app.utils.demo_data import criar_dados_demo_completos

            # Buscar empresa demo
            empresa = Empresa.query.filter_by(slug='demo').first()
            if not empresa:
                return {
                    'status': 'error',
                    'message': 'Empresa demo não encontrada. Execute /setup-demo primeiro',
                }, 400

            resultado = criar_dados_demo_completos(empresa.id)
            return resultado, 200 if resultado['status'] == 'ok' else 400

        except Exception as e:
            import traceback

            return {'status': 'error', 'error': str(e), 'traceback': traceback.format_exc()}, 500

    # Rota de teste simples (sem banco de dados)
    @app.route('/test')
    def test_page():
        """Rota de teste - sem dependencias"""
        return {'status': 'ok', 'message': 'Servidor funcionando'}, 200

    # Rota de teste com banco (simples)
    @app.route('/test-db')
    def test_db():
        """Rota de teste com banco - query simples"""
        try:
            from app.models import Empresa

            count = Empresa.query.count()
            return {'status': 'ok', 'empresas': count}, 200
        except Exception as e:
            return {'status': 'error', 'error': str(e)}, 500

    # Rota para verificar configuração do banco - protegida em produção
    @app.route('/debug/config')
    def debug_config():
        """Verifica configuração do banco - apenas desenvolvimento"""
        # Proteger em produção com secret key
        if FLASK_ENV == 'production':
            from flask import request

            debug_key = config('DEBUG_SECRET_KEY', default=None)
            if not debug_key or request.args.get('key') != debug_key:
                return {'error': 'Forbidden'}, 403

        db_url = config('DATABASE_URL', default=None)
        # Ocultar senha da URL
        if db_url:
            if '://' in db_url:
                parts = db_url.split('@')
                if len(parts) > 1:
                    db_url_display = parts[0].split('://')[0] + '://***@' + parts[1]
                else:
                    db_url_display = db_url
            else:
                db_url_display = db_url
        else:
            db_url_display = 'NÃO CONFIGURADO'

        return {
            'status': 'ok',
            'database_url_configured': db_url is not None,
            'database_url': db_url_display,
            'sqlalchemy_database_uri': app.config.get('SQLALCHEMY_DATABASE_URI', 'NÃO CONFIGURADO'),
            'flask_env': FLASK_ENV,
        }, 200

    # Rota para testar login via API - protegida em produção
    @app.route('/test-login', methods=['POST'])
    def test_login():
        """Testa login e retorna diagnóstico - apenas desenvolvimento"""
        # Proteger em produção com secret key
        if FLASK_ENV == 'production':
            from flask import request

            debug_key = config('DEBUG_SECRET_KEY', default=None)
            if not debug_key or request.args.get('key') != debug_key:
                return {'error': 'Forbidden'}, 403

        try:
            from flask import request

            from app.models import Usuario

            data = request.get_json() or request.form
            email = data.get('email', '').strip().lower()
            senha = data.get('senha', '')

            usuario = Usuario.query.filter_by(email=email, ativo=True).first()

            if not usuario:
                return {
                    'status': 'error',
                    'message': 'Usuario nao encontrado',
                    'email': email,
                    'total_usuarios': Usuario.query.count(),
                }, 404

            senha_ok = usuario.verificar_senha(senha)

            return {
                'status': 'ok' if senha_ok else 'senha_incorreta',
                'usuario_encontrado': True,
                'senha_correta': senha_ok,
                'usuario': {
                    'id': usuario.id,
                    'email': usuario.email,
                    'ativo': usuario.ativo,
                    'empresa_id': usuario.empresa_id,
                },
            }, 200
        except Exception as e:
            import traceback

            return {'status': 'error', 'error': str(e), 'traceback': traceback.format_exc()}, 500

    # Exempt rotas de debug do CSRF (deve ser feito após definir as rotas)
    csrf.exempt(test_login)
    csrf.exempt(debug_config)

    # Rota raiz para verificar se app está rodando
    @app.route('/')
    def root():
        """Rota raiz - redireciona para dashboard ou login"""
        from flask import redirect, url_for

        if 'usuario_id' in session:
            return redirect(url_for('main.dashboard'))
        return redirect(url_for('auth.login'))

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
