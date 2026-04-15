"""
Helpers utilitários para rotas Flask
"""

from flask import abort, g, session

from app.models import Empresa


def get_current_empresa_id(require=True):
    """
    Obtém o empresa_id da sessão atual.

    Args:
        require: Se True, aborta com 401 se não houver empresa_id na sessão.
                 Se False, retorna None se não houver.

    Returns:
        int: empresa_id da sessão ou None

    Raises:
        401: Se require=True e empresa_id não estiver na sessão
    """
    empresa_id = session.get('empresa_id')
    if require and not empresa_id:
        abort(401, description='Usuário não autenticado')
    return empresa_id


def get_current_empresa(require=True):
    """
    Obtém o objeto Empresa da sessão atual.

    Args:
        require: Se True, aborta com 401/404 se não houver empresa.

    Returns:
        Empresa: objeto Empresa ou None

    Raises:
        401: Se require=True e empresa_id não estiver na sessão
        404: Se require=True e empresa não existir no banco
    """
    empresa_id = get_current_empresa_id(require=require)
    if not empresa_id:
        return None

    empresa = Empresa.query.get(empresa_id)
    if require and not empresa:
        abort(404, description='Empresa não encontrada')
    return empresa


def get_owned_or_404(model, id, empresa_id=None):
    """
    Obtém um objeto do modelo filtrando por empresa_id (ownership check).

    Previne acesso a dados de outras empresas.

    Args:
        model: Classe do modelo SQLAlchemy
        id: ID do objeto
        empresa_id: empresa_id para filtrar (usa sessão se None)

    Returns:
        Objeto do modelo

    Raises:
        404: Se objeto não existir ou não pertencer à empresa
    """
    if empresa_id is None:
        empresa_id = get_current_empresa_id()

    obj = model.query.filter_by(id=id, empresa_id=empresa_id).first()
    if not obj:
        abort(404, description='Recurso não encontrado')
    return obj


def get_user_context():
    """
    Obtém contexto completo do usuário atual.

    Returns:
        dict: Com usuario_id, usuario_nome, usuario_email, empresa_id
    """
    return {
        'usuario_id': session.get('usuario_id'),
        'usuario_nome': session.get('usuario_nome'),
        'usuario_email': session.get('usuario_email'),
        'empresa_id': session.get('empresa_id'),
    }


def cache_empresa_context(func):
    """
    Decorator para cachear empresa_id no objeto Flask g.

    Evita múltiplas chamadas a session.get('empresa_id').
    """

    def wrapper(*args, **kwargs):
        if not hasattr(g, '_empresa_id'):
            g._empresa_id = session.get('empresa_id')
        return func(*args, **kwargs)

    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper
