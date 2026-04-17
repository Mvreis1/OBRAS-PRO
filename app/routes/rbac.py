"""
Rotas de gerenciamento de controle de acesso (RBAC)
"""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from app.models import Usuario, db
from app.models.acesso import Permissao, PermissaoUsuario, Role, RolePermissao
from app.routes.auth import login_required
from app.services.rbac_service import RBACService
from app.utils.rbac import Acoes, Modulos, require_permission

rbac_bp = Blueprint('rbac', __name__)


def get_usuario_id():
    return session.get('usuario_id')


@rbac_bp.route('/roles')
@login_required
@require_permission(Modulos.ROLES, Acoes.VER)
def listar_roles():
    """Lista todos os roles da empresa usando RBACService"""
    empresa_id = session.get('empresa_id')
    roles = RBACService.get_roles_empresa(empresa_id)
    return render_template('rbac/roles.html', roles=roles)


@rbac_bp.route('/role/novo', methods=['GET', 'POST'])
@login_required
@require_permission(Modulos.ROLES, Acoes.CRIAR)
def novo_role():
    """Cria novo role usando RBACService"""
    empresa_id = session.get('empresa_id')

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        descricao = request.form.get('descricao', '').strip()
        permissoes_ids = [int(p) for p in request.form.getlist('permissoes')]

        _, erro = RBACService.criar_role(empresa_id, nome, descricao, permissoes_ids)

        if erro:
            flash(erro, 'danger')
            return redirect(url_for('rbac.novo_role'))

        flash('Perfil criado com sucesso!', 'success')
        return redirect(url_for('rbac.listar_roles'))

    # GET: mostrar formulário usando RBACService
    permissoes_por_modulo = RBACService.get_permissoes_agrupadas()

    return render_template(
        'rbac/role_form.html', role=None, permissoes_por_modulo=permissoes_por_modulo
    )


@rbac_bp.route('/role/<int:role_id>/editar', methods=['GET', 'POST'])
@login_required
@require_permission(Modulos.ROLES, Acoes.EDITAR)
def editar_role(role_id):
    """Edita role existente usando RBACService"""
    empresa_id = session.get('empresa_id')

    # GET: buscar role para exibição
    role = Role.query.filter(
        db.or_(
            db.and_(Role.id == role_id, Role.empresa_id.is_(None)),
            db.and_(Role.id == role_id, Role.empresa_id == empresa_id),
        )
    ).first_or_404()

    if role.is_system and role.empresa_id is None:
        flash(
            'Roles do sistema não podem ser editados. Crie um novo role baseado neste.', 'warning'
        )
        return redirect(url_for('rbac.listar_roles'))

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        descricao = request.form.get('descricao', '').strip()
        permissoes_ids = [int(p) for p in request.form.getlist('permissoes')]

        role, erro = RBACService.editar_role(role_id, empresa_id, nome, descricao, permissoes_ids)

        if erro:
            flash(erro, 'danger')
        else:
            flash('Perfil atualizado com sucesso!', 'success')
            return redirect(url_for('rbac.listar_roles'))

    # GET: carregar permissões para formulário usando RBACService
    permissoes_por_modulo = RBACService.get_permissoes_agrupadas()
    role_perm_ids = [p.id for p in role.permissoes]

    return render_template(
        'rbac/role_form.html',
        role=role,
        permissoes_por_modulo=permissoes_por_modulo,
        role_perm_ids=role_perm_ids,
    )


@rbac_bp.route('/role/<int:role_id>/excluir', methods=['POST'])
@login_required
@require_permission(Modulos.ROLES, Acoes.EXCLUIR)
def excluir_role(role_id):
    """Exclui role usando RBACService"""
    empresa_id = session.get('empresa_id')

    _, erro = RBACService.excluir_role(role_id, empresa_id)

    if erro:
        flash(erro, 'danger')
    else:
        flash('Perfil excluído com sucesso!', 'success')

    return redirect(url_for('rbac.listar_roles'))


@rbac_bp.route('/usuarios-permissoes')
@login_required
@require_permission(Modulos.USUARIOS, Acoes.GERENCIAR_PERMISSOES)
def gerenciar_usuarios_permissoes():
    """Lista usuários para gerenciar permissões"""
    empresa_id = session.get('empresa_id')
    usuarios = Usuario.query.filter_by(empresa_id=empresa_id).all()
    roles = Role.query.filter(
        db.or_(Role.empresa_id.is_(None), Role.empresa_id == empresa_id)
    ).all()

    return render_template('rbac/usuarios_permissoes.html', usuarios=usuarios, roles=roles)


@rbac_bp.route('/usuario/<int:usuario_id>/permissoes', methods=['GET', 'POST'])
@login_required
@require_permission(Modulos.USUARIOS, Acoes.GERENCIAR_PERMISSOES)
def editar_permissoes_usuario(usuario_id):
    """Edita permissões individuais de um usuário"""
    empresa_id = session.get('empresa_id')
    usuario = Usuario.query.filter_by(id=usuario_id, empresa_id=empresa_id).first_or_404()

    if request.method == 'POST':
        acao = request.form.get('acao')

        if acao == 'alterar_role':
            role_id = request.form.get('role_id')
            usuario.role_id = int(role_id) if role_id else None

        elif acao == 'add_permissao':
            permissao_id = int(request.form.get('permissao_id'))
            tipo = request.form.get('tipo', 'allow')

            # Verificar se já existe
            existing = PermissaoUsuario.query.filter_by(
                usuario_id=usuario.id, permissao_id=permissao_id
            ).first()
            if not existing:
                perm_user = PermissaoUsuario(
                    usuario_id=usuario.id, permissao_id=permissao_id, tipo=tipo
                )
                db.session.add(perm_user)

        elif acao == 'remover_permissao':
            permissao_id = int(request.form.get('permissao_id'))
            PermissaoUsuario.query.filter_by(
                usuario_id=usuario.id, permissao_id=permissao_id
            ).delete()

        db.session.commit()
        flash('Permissões atualizadas!', 'success')
        return redirect(url_for('rbac.editar_permissoes_usuario', usuario_id=usuario_id))

    # GET
    roles = Role.query.filter(
        db.or_(Role.empresa_id.is_(None), Role.empresa_id == empresa_id)
    ).all()

    permissoes = Permissao.query.order_by(Permissao.modulo, Permissao.acao).all()
    permissoes_por_modulo = {}
    for perm in permissoes:
        if perm.modulo not in permissoes_por_modulo:
            permissoes_por_modulo[perm.modulo] = []
        permissoes_por_modulo[perm.modulo].append(perm)

    permissoes_individuais = {pu.permissao_id: pu for pu in usuario.permissoes_individuais}

    return render_template(
        'rbac/usuario_permissoes.html',
        usuario=usuario,
        roles=roles,
        permissoes_por_modulo=permissoes_por_modulo,
        permissoes_individuais=permissoes_individuais,
    )


@rbac_bp.route('/api/roles')
@login_required
def api_roles():
    """API para listar roles"""
    empresa_id = session.get('empresa_id')
    roles = Role.query.filter(
        db.or_(Role.empresa_id.is_(None), Role.empresa_id == empresa_id)
    ).all()
    return jsonify([r.to_dict() for r in roles])


@rbac_bp.route('/api/usuario/<int:usuario_id>/permissoes')
@login_required
def api_usuario_permissoes(usuario_id):
    """API para permissões de um usuário"""
    empresa_id = session.get('empresa_id')
    usuario = Usuario.query.filter_by(id=usuario_id, empresa_id=empresa_id).first_or_404()

    return jsonify({'usuario': usuario.to_dict(), 'permissoes': list(usuario.get_permissoes())})
