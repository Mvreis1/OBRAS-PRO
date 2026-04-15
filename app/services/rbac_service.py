"""RBAC Service - Role-Based Access Control management"""

from typing import Optional

from sqlalchemy import or_

from app.models import Usuario, db
from app.models.acesso import Permissao, PermissaoUsuario, Role, RolePermissao


class RBACService:
    """Service for managing roles, permissions and user access control"""

    @staticmethod
    def get_roles_empresa(empresa_id: int) -> list[Role]:
        """
        Get all roles for a company (including system roles).

        Args:
            empresa_id: Empresa ID

        Returns:
            List of Role objects
        """
        return (
            Role.query.filter(or_(Role.empresa_id.is_(None), Role.empresa_id == empresa_id))
            .order_by(Role.is_system.desc(), Role.nome)
            .all()
        )

    @staticmethod
    def criar_role(
        empresa_id: int, nome: str, descricao: str, permissoes_ids: list[int]
    ) -> tuple[Role | None, str | None]:
        """
        Create new role with permissions.

        Args:
            empresa_id: Empresa ID
            nome: Role name
            descricao: Role description
            permissoes_ids: List of permission IDs

        Returns:
            Tuple (role, error_message)
        """
        # Validate name
        if not nome or not nome.strip():
            return None, 'Nome do perfil é obrigatório.'

        nome = nome.strip()

        # Check uniqueness
        if Role.query.filter_by(nome=nome).first():
            return None, 'Nome de perfil já existe.'

        # Create role
        role = Role(
            nome=nome, descricao=descricao.strip() if descricao else '', empresa_id=empresa_id
        )
        db.session.add(role)
        db.session.flush()

        # Add permissions
        for perm_id in permissoes_ids:
            assoc = RolePermissao(role_id=role.id, permissao_id=int(perm_id))
            db.session.add(assoc)

        db.session.commit()
        return role, None

    @staticmethod
    def editar_role(
        role_id: int, empresa_id: int, nome: str, descricao: str, permissoes_ids: list[int]
    ) -> tuple[Role | None, str | None]:
        """
        Update existing role.

        Args:
            role_id: Role ID
            empresa_id: Empresa ID
            nome: New name
            descricao: New description
            permissoes_ids: New list of permission IDs

        Returns:
            Tuple (role, error_message)
        """
        # Get role (system or company-specific)
        role = Role.query.filter(
            or_(
                db.and_(Role.id == role_id, Role.empresa_id.is_(None)),
                db.and_(Role.id == role_id, Role.empresa_id == empresa_id),
            )
        ).first()

        if not role:
            return None, 'Perfil não encontrado.'

        # System roles cannot be edited
        if role.is_system and role.empresa_id is None:
            return None, 'Roles do sistema não podem ser editados.'

        # Update fields
        role.nome = nome.strip()
        role.descricao = descricao.strip() if descricao else ''

        # Remove existing permissions
        RolePermissao.query.filter_by(role_id=role.id).delete()

        # Add new permissions
        for perm_id in permissoes_ids:
            assoc = RolePermissao(role_id=role.id, permissao_id=int(perm_id))
            db.session.add(assoc)

        db.session.commit()
        return role, None

    @staticmethod
    def excluir_role(role_id: int, empresa_id: int) -> tuple[bool, str | None]:
        """
        Delete role.

        Args:
            role_id: Role ID
            empresa_id: Empresa ID

        Returns:
            Tuple (success, error_message)
        """
        role = Role.query.filter(Role.id == role_id, Role.empresa_id == empresa_id).first()

        if not role:
            return False, 'Perfil não encontrado.'

        if role.is_system:
            return False, 'Roles do sistema não podem ser excluídos.'

        if role.usuarios and role.usuarios.count() > 0:
            return False, 'Não é possível excluir um perfil que possui usuários.'

        db.session.delete(role)
        db.session.commit()
        return True, None

    @staticmethod
    def get_permissoes_agrupadas() -> dict[str, list[Permissao]]:
        """
        Get all permissions grouped by module.

        Returns:
            Dict with module name as key and list of permissions as value
        """
        permissoes = Permissao.query.order_by(Permissao.modulo, Permissao.acao).all()

        permissoes_por_modulo = {}
        for perm in permissoes:
            if perm.modulo not in permissoes_por_modulo:
                permissoes_por_modulo[perm.modulo] = []
            permissoes_por_modulo[perm.modulo].append(perm)

        return permissoes_por_modulo

    @staticmethod
    def get_usuario_permissoes(usuario_id: int, empresa_id: int) -> dict | None:
        """
        Get user with their permissions.

        Args:
            usuario_id: User ID
            empresa_id: Empresa ID

        Returns:
            Dict with user data and permissions
        """
        usuario = Usuario.query.filter_by(id=usuario_id, empresa_id=empresa_id).first()

        if not usuario:
            return None

        return {
            'usuario': usuario,
            'role': usuario.role_obj,
            'permissoes_individuais': {
                pu.permissao_id: pu for pu in usuario.permissoes_individuais
            },
            'all_permissoes': list(usuario.get_permissoes()),
        }

    @staticmethod
    def usuario_alterar_role(
        usuario_id: int, empresa_id: int, role_id: int | None
    ) -> tuple[bool, str | None]:
        """
        Change user's role.

        Args:
            usuario_id: User ID
            empresa_id: Empresa ID
            role_id: New role ID (None to remove)

        Returns:
            Tuple (success, error_message)
        """
        usuario = Usuario.query.filter_by(id=usuario_id, empresa_id=empresa_id).first()

        if not usuario:
            return False, 'Usuário não encontrado.'

        # Validate role exists
        if role_id:
            role = Role.query.filter(
                or_(
                    Role.id == role_id,
                    db.and_(Role.id == role_id, Role.empresa_id == empresa_id),
                )
            ).first()

            if not role:
                return False, 'Perfil não encontrado.'

        usuario.role_id = role_id
        db.session.commit()
        return True, None

    @staticmethod
    def usuario_add_permissao(
        usuario_id: int, empresa_id: int, permissao_id: int, tipo: str = 'allow'
    ) -> tuple[bool, str | None]:
        """
        Add individual permission to user.

        Args:
            usuario_id: User ID
            empresa_id: Empresa ID
            permissao_id: Permission ID
            tipo: Permission type (allow/deny)

        Returns:
            Tuple (success, error_message)
        """
        usuario = Usuario.query.filter_by(id=usuario_id, empresa_id=empresa_id).first()

        if not usuario:
            return False, 'Usuário não encontrado.'

        # Check if permission already exists
        existing = PermissaoUsuario.query.filter_by(
            usuario_id=usuario.id, permissao_id=permissao_id
        ).first()

        if existing:
            return False, 'Permissão já existe para este usuário.'

        # Add permission
        perm_user = PermissaoUsuario(usuario_id=usuario.id, permissao_id=permissao_id, tipo=tipo)
        db.session.add(perm_user)
        db.session.commit()
        return True, None

    @staticmethod
    def usuario_remover_permissao(
        usuario_id: int, empresa_id: int, permissao_id: int
    ) -> tuple[bool, str | None]:
        """
        Remove individual permission from user.

        Args:
            usuario_id: User ID
            empresa_id: Empresa ID
            permissao_id: Permission ID

        Returns:
            Tuple (success, error_message)
        """
        usuario = Usuario.query.filter_by(id=usuario_id, empresa_id=empresa_id).first()

        if not usuario:
            return False, 'Usuário não encontrado.'

        # Remove permission
        deleted = PermissaoUsuario.query.filter_by(
            usuario_id=usuario.id, permissao_id=permissao_id
        ).delete()

        if deleted == 0:
            return False, 'Permissão não encontrada para este usuário.'

        db.session.commit()
        return True, None

    @staticmethod
    def get_usuarios_permissoes(empresa_id: int) -> dict:
        """
        Get all users with their roles and permissions for a company.

        Args:
            empresa_id: Empresa ID

        Returns:
            Dict with users and roles
        """
        usuarios = Usuario.query.filter_by(empresa_id=empresa_id).all()
        roles = RBACService.get_roles_empresa(empresa_id)

        return {
            'usuarios': usuarios,
            'roles': roles,
        }

    @staticmethod
    def validate_role_form(nome: str, permissoes_ids: list[int]) -> list[str]:
        """
        Validate role form data.

        Args:
            nome: Role name
            permissoes_ids: List of permission IDs

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        if not nome or not nome.strip():
            errors.append('Nome do perfil é obrigatório.')

        if not permissoes_ids or len(permissoes_ids) == 0:
            errors.append('Selecione pelo menos uma permissão.')

        return errors
