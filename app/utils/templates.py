"""
Filtros customizados para templates Jinja2
"""

from functools import wraps


def setup_filters(app):
    """Registra todos os filtros Jinja2 no app"""

    @app.template_filter('format_currency')
    def format_currency(value):
        """Filtro para formatar valores em moeda brasileira"""
        if value is None:
            return 'R$ 0,00'
        return f'R$ {value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

    @app.template_filter('format_date')
    def format_date(value):
        """Filtro para formatar datas"""
        if value is None:
            return '-'
        if hasattr(value, 'strftime'):
            return value.strftime('%d/%m/%Y')
        return str(value)

    @app.template_filter('int')
    def to_int(value):
        """Filtro para converter para inteiro"""
        try:
            return int(value)
        except:
            return 0

    @app.template_filter('number_format')
    def number_format(value, decimals=2):
        """Filtro para formatar números no padrão brasileiro"""
        if value is None:
            return '0,00'
        try:
            return f'{float(value):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
        except:
            return '0,00'


def csrf_inject(f):
    """Decorator para injetar token CSRF automaticamente nas respostas"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask_wtf.csrf import generate_csrf

        result = f(*args, **kwargs)
        if hasattr(result, '__dict__'):
            result.csrf_token = generate_csrf()
        return result

    return decorated_function


def setup_context_processors(app):
    """Registra context processors globais"""
    from flask import session

    from app.config import EMAIL_SUPORTE, NOME_SISTEMA, SITE_OFICIAL, SLOGAN

    @app.context_processor
    def inject_csrf():
        """Injeta token CSRF nos templates"""
        from flask_wtf.csrf import generate_csrf

        return {'csrf_token': generate_csrf}

    @app.context_processor
    def inject_paginacao():
        """Injeta função de paginação nos templates"""
        from app.utils.paginacao import Paginacao

        return {'Paginacao': Paginacao}

    @app.context_processor
    def inject_user():
        """Injeta variáveis globais nos templates"""
        return {
            'nome_sistema': NOME_SISTEMA,
            'slogan': SLOGAN,
            'site_oficial': SITE_OFICIAL,
            'email_suporte': EMAIL_SUPORTE,
            'usuario_nome': session.get('usuario_nome'),
            'usuario_username': session.get('usuario_username'),
            'empresa_nome': session.get('empresa_nome'),
            'empresa_slug': session.get('empresa_slug'),
        }


def format_currency():
    return None
