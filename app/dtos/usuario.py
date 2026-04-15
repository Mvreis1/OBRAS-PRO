"""DTOs para Usuario e Empresa (User and Company)"""

from dataclasses import dataclass
from datetime import datetime

from app.dtos.base import BaseDTO


@dataclass
class UsuarioCreateDTO(BaseDTO):
    """DTO for creating a new user"""

    nome: str
    email: str
    username: str
    senha: str
    cargo: str | None = 'Administrador'
    role_id: int | None = None

    def validate(self) -> str | None:
        """Validate DTO fields. Returns error message or None"""
        if not self.nome or not self.nome.strip():
            return 'Nome é obrigatório.'
        if not self.email or not self.email.strip():
            return 'Email é obrigatório.'
        if '@' not in self.email:
            return 'Email inválido.'
        if not self.username or not self.username.strip():
            return 'Username é obrigatório.'
        if not self.senha:
            return 'Senha é obrigatória.'
        if len(self.senha) < 6:
            return 'Senha deve ter pelo menos 6 caracteres.'
        return None


@dataclass
class UsuarioUpdateDTO(BaseDTO):
    """DTO for updating an existing user"""

    nome: str | None = None
    email: str | None = None
    username: str | None = None
    senha: str | None = None
    cargo: str | None = None
    role_id: int | None = None
    ativo: bool | None = None

    def validate(self) -> str | None:
        """Validate DTO fields. Returns error message or None"""
        if self.nome is not None and not self.nome.strip():
            return 'Nome não pode ser vazio.'
        if self.email is not None and '@' not in self.email:
            return 'Email inválido.'
        if self.username is not None and not self.username.strip():
            return 'Username não pode ser vazio.'
        if self.senha is not None and len(self.senha) < 6:
            return 'Senha deve ter pelo menos 6 caracteres.'
        return None


@dataclass
class UsuarioResponseDTO(BaseDTO):
    """DTO for user response data (excludes sensitive fields)"""

    id: int
    empresa_id: int
    nome: str
    email: str
    username: str
    cargo: str | None = None
    role_id: int | None = None
    ativo: bool = True
    two_factor_enabled: bool = False
    created_at: str | None = None

    @classmethod
    def from_model(cls, usuario) -> 'UsuarioResponseDTO':
        """Create DTO from Usuario model instance"""
        usuario.to_dict()
        return cls(
            id=usuario.id,
            empresa_id=usuario.empresa_id,
            nome=usuario.nome,
            email=usuario.email,
            username=usuario.username,
            cargo=usuario.cargo,
            role_id=usuario.role_id,
            ativo=usuario.ativo if usuario.ativo is not None else True,
            two_factor_enabled=usuario.two_factor_enabled
            if usuario.two_factor_enabled is not None
            else False,
            created_at=usuario.created_at.isoformat() if usuario.created_at else None,
        )


@dataclass
class LoginDTO(BaseDTO):
    """DTO for user login"""

    username: str
    senha: str
    totp_token: str | None = None

    def validate(self) -> str | None:
        """Validate DTO fields. Returns error message or None"""
        if not self.username or not self.username.strip():
            return 'Username é obrigatório.'
        if not self.senha:
            return 'Senha é obrigatória.'
        return None


@dataclass
class EmpresaCreateDTO(BaseDTO):
    """DTO for creating a new company"""

    nome: str
    slug: str
    cnpj: str | None = None
    telefone: str | None = None
    email: str | None = None
    endereco: str | None = None
    plano: str = 'free'
    max_usuarios: int = 1
    max_obras: int = 5

    def validate(self) -> str | None:
        """Validate DTO fields. Returns error message or None"""
        if not self.nome or not self.nome.strip():
            return 'Nome é obrigatório.'
        if not self.slug or not self.slug.strip():
            return 'Slug é obrigatório.'
        if self.max_usuarios < 1:
            return 'Máximo de usuários deve ser pelo menos 1.'
        if self.max_obras < 1:
            return 'Máximo de obras deve ser pelo menos 1.'
        return None


@dataclass
class EmpresaUpdateDTO(BaseDTO):
    """DTO for updating an existing company"""

    nome: str | None = None
    slug: str | None = None
    cnpj: str | None = None
    telefone: str | None = None
    email: str | None = None
    endereco: str | None = None
    logo: str | None = None
    plano: str | None = None
    max_usuarios: int | None = None
    max_obras: int | None = None
    ativo: bool | None = None

    def validate(self) -> str | None:
        """Validate DTO fields. Returns error message or None"""
        if self.nome is not None and not self.nome.strip():
            return 'Nome não pode ser vazio.'
        if self.max_usuarios is not None and self.max_usuarios < 1:
            return 'Máximo de usuários deve ser pelo menos 1.'
        if self.max_obras is not None and self.max_obras < 1:
            return 'Máximo de obras deve ser pelo menos 1.'
        return None


@dataclass
class EmpresaResponseDTO(BaseDTO):
    """DTO for company response data"""

    id: int
    nome: str
    slug: str
    cnpj: str | None = None
    telefone: str | None = None
    email: str | None = None
    endereco: str | None = None
    logo: str | None = None
    plano: str = 'free'
    max_usuarios: int = 1
    max_obras: int = 5
    ativo: bool = True
    trial_ativo: bool = True
    trial_expira: str | None = None
    created_at: str | None = None

    @classmethod
    def from_model(cls, empresa) -> 'EmpresaResponseDTO':
        """Create DTO from Empresa model instance"""
        return cls(
            id=empresa.id,
            nome=empresa.nome,
            slug=empresa.slug,
            cnpj=empresa.cnpj,
            telefone=empresa.telefone,
            email=empresa.email,
            endereco=empresa.endereco,
            logo=empresa.logo,
            plano=empresa.plano or 'free',
            max_usuarios=empresa.max_usuarios or 1,
            max_obras=empresa.max_obras or 5,
            ativo=empresa.ativo if empresa.ativo is not None else True,
            trial_ativo=empresa.trial_ativo if empresa.trial_ativo is not None else True,
            trial_expira=empresa.trial_expira.isoformat() if empresa.trial_expira else None,
            created_at=empresa.created_at.isoformat() if empresa.created_at else None,
        )


@dataclass
class RoleCreateDTO(BaseDTO):
    """DTO for creating a new role"""

    nome: str
    descricao: str | None = None
    permissoes: list[int] | None = None  # list of permissao IDs

    def validate(self) -> str | None:
        """Validate DTO fields. Returns error message or None"""
        if not self.nome or not self.nome.strip():
            return 'Nome é obrigatório.'
        return None


@dataclass
class RoleResponseDTO(BaseDTO):
    """DTO for role response data"""

    id: int
    nome: str
    descricao: str | None = None
    empresa_id: int | None = None
    is_system: bool = False
    permissoes: list[dict] | None = None
    created_at: str | None = None

    @classmethod
    def from_model(cls, role) -> 'RoleResponseDTO':
        """Create DTO from Role model instance"""
        role_dict = role.to_dict()
        return cls(
            id=role.id,
            nome=role.nome,
            descricao=role.descricao,
            empresa_id=role.empresa_id,
            is_system=role.is_system if role.is_system is not None else False,
            permissoes=role_dict.get('permissoes'),
            created_at=role.created_at.isoformat() if role.created_at else None,
        )
