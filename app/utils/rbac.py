"""
Decoradores e helpers para controle de acesso (RBAC)
"""

from functools import wraps

from flask import abort, flash, redirect, request, session, url_for

_usuario_cache = {}


def get_usuario_atual():
    """Retorna o usuário logado (com cache por request)"""
    from flask import g

    if hasattr(g, 'usuario_cache'):
        return g.usuario_cache

    usuario_id = session.get('usuario_id')
    if not usuario_id:
        return None

    # Import tardio para evitar import circular
    from app.models import Usuario, db

    usuario = db.session.get(Usuario, usuario_id)

    # Armazenar em g para evitar múltiplas queries na mesma request
    g.usuario_cache = usuario
    return usuario


def usuario_tem_permissao(modulo, acao=None):
    """Verifica se o usuário logado tem permissão"""
    usuario = get_usuario_atual()
    if not usuario:
        return False
    return usuario.has_permission(modulo, acao)


def require_permission(modulo, acao=None, redirect_url='main.dashboard'):
    """
    Decorator para proteger rotas com permissões.

    Uso:
        @require_permission('obras', 'ver')
        def minha_rota():
            ...

    Args:
        modulo: Nome do módulo (dashboard, obras, lancamentos, contratos, etc.)
        acao: Ação específica (ver, criar, editar, excluir, exportar) ou None para qualquer ação
        redirect_url: URL para redirecionar se não tiver permissão
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            usuario = get_usuario_atual()
            if not usuario:
                flash('Faça login para acessar esta página.', 'warning')
                return redirect(url_for('auth.login'))

            if not usuario.has_permission(modulo, acao):
                is_api = request.is_json or request.headers.get('Accept') == 'application/json'
                if is_api:
                    abort(403, description='Você não tem permissão para acessar este recurso.')
                flash('Você não tem permissão para acessar esta página.', 'danger')
                return redirect(url_for(redirect_url))

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def require_any_permission(permissions, redirect_url='main.dashboard'):
    """
    Decorator que requer QUALQUER UMA das permissões listadas.

    Uso:
        @require_any_permission([('obras', 'ver'), ('obras', 'criar')])
        def minha_rota():
            ...
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            usuario = get_usuario_atual()
            if not usuario:
                flash('Faça login para acessar esta página.', 'warning')
                return redirect(url_for('auth.login'))

            has_any = any(usuario.has_permission(mod, act) for mod, act in permissions)
            if not has_any:
                flash('Você não tem permissão para acessar esta página.', 'danger')
                return redirect(url_for(redirect_url))

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def require_all_permissions(permissions, redirect_url='main.dashboard'):
    """
    Decorator que requer TODAS as permissões listadas.
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            usuario = get_usuario_atual()
            if not usuario:
                flash('Faça login para acessar esta página.', 'warning')
                return redirect(url_for('auth.login'))

            has_all = all(usuario.has_permission(mod, act) for mod, act in permissions)
            if not has_all:
                flash('Você não tem permissão para acessar esta página.', 'danger')
                return redirect(url_for(redirect_url))

            return f(*args, **kwargs)

        return decorated_function

    return decorator


class Modulos:
    """Constantes de módulos do sistema"""

    DASHBOARD = 'dashboard'
    OBRAS = 'obras'
    LANCAMENTOS = 'lancamentos'
    CONTRATOS = 'contratos'
    ORCAMENTOS = 'orcamentos'
    FORNECEDORES = 'fornecedores'
    BANCOS = 'bancos'
    RELATORIOS = 'relatorios'
    USUARIOS = 'usuarios'
    ROLES = 'roles'
    CONFIGURACOES = 'configuracoes'
    NOTIFICACOES = 'notificacoes'
    AUDITORIA = 'auditoria'
    IA = 'ia'


class Acoes:
    """Constantes de ações do sistema"""

    VER = 'ver'
    CRIAR = 'criar'
    EDITAR = 'editar'
    EXCLUIR = 'excluir'
    EXPORTAR = 'exportar'
    APROVAR = 'aprovar'
    CANCELAR = 'cancelar'
    GERENCIAR_PERMISSOES = 'gerenciar_permissoes'
    TODAS = '*'  # Todas as ações
