"""
Rotas de gerenciamento de controle de acesso (RBAC)
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app.models import db, Usuario
from app.models.acesso import Permissao, Role, RolePermissao, PermissaoUsuario
from app.routes.auth import login_required
from app.utils.rbac import require_permission, Modulos, Acoes

rbac_bp = Blueprint('rbac', __name__)


def get_usuario_id():
    return session.get('usuario_id')


@rbac_bp.route('/roles')
@login_required
@require_permission(Modulos.ROLES, Acoes.VER)
def listar_roles():
    """Lista todos os roles da empresa"""
    empresa_id = session.get('empresa_id')
    
    # Roles globais (sistema) + roles da empresa
    roles = Role.query.filter(
        db.or_(
            Role.empresa_id.is_(None),
            Role.empresa_id == empresa_id
        )
    ).order_by(Role.is_system.desc(), Role.nome).all()
    
    return render_template('rbac/roles.html', roles=roles)


@rbac_bp.route('/role/novo', methods=['GET', 'POST'])
@login_required
@require_permission(Modulos.ROLES, Acoes.CRIAR)
def novo_role():
    """Cria novo role"""
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        descricao = request.form.get('descricao', '').strip()
        permissoes = request.form.getlist('permissoes')
        
        if not nome:
            flash('Nome do perfil é obrigatório.', 'danger')
            return redirect(url_for('rbac.novo_role'))
        
        if Role.query.filter_by(nome=nome).first():
            flash('Nome de perfil já existe.', 'danger')
            return redirect(url_for('rbac.novo_role'))
        
        role = Role(
            nome=nome,
            descricao=descricao,
            empresa_id=session.get('empresa_id')
        )
        db.session.add(role)
        db.session.flush()
        
        # Adicionar permissões
        for perm_id in permissoes:
            assoc = RolePermissao(role_id=role.id, permissao_id=int(perm_id))
            db.session.add(assoc)
        
        db.session.commit()
        flash('Perfil criado com sucesso!', 'success')
        return redirect(url_for('rbac.listar_roles'))
    
    # GET: mostrar formulário
    permissoes = Permissao.query.order_by(Permissao.modulo, Permissao.acao).all()
    
    # Agrupar por módulo
    permissoes_por_modulo = {}
    for perm in permissoes:
        if perm.modulo not in permissoes_por_modulo:
            permissoes_por_modulo[perm.modulo] = []
        permissoes_por_modulo[perm.modulo].append(perm)
    
    return render_template('rbac/role_form.html', role=None, permissoes_por_modulo=permissoes_por_modulo)


@rbac_bp.route('/role/<int:role_id>/editar', methods=['GET', 'POST'])
@login_required
@require_permission(Modulos.ROLES, Acoes.EDITAR)
def editar_role(role_id):
    """Edita role existente"""
    empresa_id = session.get('empresa_id')
    
    # Query simplificada: busca role global (empresa_id IS NULL) ou da empresa atual
    role = Role.query.filter(
        db.or_(
            db.and_(Role.id == role_id, Role.empresa_id.is_(None)),
            db.and_(Role.id == role_id, Role.empresa_id == empresa_id)
        )
    ).first_or_404()
    
    if role.is_system and role.empresa_id is None:
        flash('Roles do sistema não podem ser editados. Crie um novo role baseado neste.', 'warning')
        return redirect(url_for('rbac.listar_roles'))
    
    if request.method == 'POST':
        role.nome = request.form.get('nome', '').strip()
        role.descricao = request.form.get('descricao', '').strip()
        permissoes = request.form.getlist('permissoes')
        
        # Remover permissões existentes
        RolePermissao.query.filter_by(role_id=role.id).delete()
        
        # Adicionar novas permissões
        for perm_id in permissoes:
            assoc = RolePermissao(role_id=role.id, permissao_id=int(perm_id))
            db.session.add(assoc)
        
        db.session.commit()
        flash('Perfil atualizado com sucesso!', 'success')
        return redirect(url_for('rbac.listar_roles'))
    
    # GET
    permissoes = Permissao.query.order_by(Permissao.modulo, Permissao.acao).all()
    permissoes_por_modulo = {}
    for perm in permissoes:
        if perm.modulo not in permissoes_por_modulo:
            permissoes_por_modulo[perm.modulo] = []
        permissoes_por_modulo[perm.modulo].append(perm)
    
    role_perm_ids = [p.id for p in role.permissoes]
    
    return render_template('rbac/role_form.html', role=role, 
                         permissoes_por_modulo=permissoes_por_modulo,
                         role_perm_ids=role_perm_ids)


@rbac_bp.route('/role/<int:role_id>/excluir', methods=['POST'])
@login_required
@require_permission(Modulos.ROLES, Acoes.EXCLUIR)
def excluir_role(role_id):
    """Exclui role"""
    empresa_id = session.get('empresa_id')
    role = Role.query.filter(
        Role.id == role_id, 
        Role.empresa_id == empresa_id
    ).first_or_404()
    
    if role.is_system:
        flash('Roles do sistema não podem ser excluídos.', 'danger')
        return redirect(url_for('rbac.listar_roles'))
    
    if role.usuarios and role.usuarios.count() > 0:
        flash('Não é possível excluir um perfil que possui usuários.', 'danger')
        return redirect(url_for('rbac.listar_roles'))
    
    db.session.delete(role)
    db.session.commit()
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
        db.or_(
            Role.empresa_id.is_(None),
            Role.empresa_id == empresa_id
        )
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
                    usuario_id=usuario.id,
                    permissao_id=permissao_id,
                    tipo=tipo
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
        db.or_(
            Role.empresa_id.is_(None),
            Role.empresa_id == empresa_id
        )
    ).all()
    
    permissoes = Permissao.query.order_by(Permissao.modulo, Permissao.acao).all()
    permissoes_por_modulo = {}
    for perm in permissoes:
        if perm.modulo not in permissoes_por_modulo:
            permissoes_por_modulo[perm.modulo] = []
        permissoes_por_modulo[perm.modulo].append(perm)
    
    permissoes_individuais = {pu.permissao_id: pu for pu in usuario.permissoes_individuais}
    
    return render_template('rbac/usuario_permissoes.html', 
                         usuario=usuario, roles=roles,
                         permissoes_por_modulo=permissoes_por_modulo,
                         permissoes_individuais=permissoes_individuais)


@rbac_bp.route('/api/roles')
@login_required
def api_roles():
    """API para listar roles"""
    empresa_id = session.get('empresa_id')
    roles = Role.query.filter(
        db.or_(
            Role.empresa_id.is_(None),
            Role.empresa_id == empresa_id
        )
    ).all()
    return jsonify([r.to_dict() for r in roles])


@rbac_bp.route('/api/usuario/<int:usuario_id>/permissoes')
@login_required
def api_usuario_permissoes(usuario_id):
    """API para permissões de um usuário"""
    empresa_id = session.get('empresa_id')
    usuario = Usuario.query.filter_by(id=usuario_id, empresa_id=empresa_id).first_or_404()
    
    return jsonify({
        'usuario': usuario.to_dict(),
        'permissoes': list(usuario.get_permissoes())
    })
