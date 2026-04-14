"""
Modelos de controle de acesso (RBAC)
"""
from app.models import db
from datetime import datetime


class Permissao(db.Model):
    """Permissões individuais do sistema"""
    __tablename__ = 'permissoes'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    descricao = db.Column(db.String(200))
    modulo = db.Column(db.String(50), nullable=False, index=True)
    acao = db.Column(db.String(50), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.Index('idx_permissao_modulo_acao', 'modulo', 'acao'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao,
            'modulo': self.modulo,
            'acao': self.acao
        }


class Role(db.Model):
    """Perfil de acesso (conjunto de permissões)"""
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True, nullable=False)
    descricao = db.Column(db.String(200))
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=True, index=True)
    is_system = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships - usando lazy='select' para evitar carregamento excessivo
    permissoes = db.relationship('Permissao', secondary='role_permissoes', lazy='select',
                                 backref=db.backref('roles', lazy='select'))

    __table_args__ = (
        db.Index('idx_role_empresa_nome', 'empresa_id', 'nome'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao,
            'empresa_id': self.empresa_id,
            'is_system': self.is_system,
            'permissoes': [p.to_dict() for p in self.permissoes]
        }


class RolePermissao(db.Model):
    """Tabela de associação entre Roles e Permissoes"""
    __tablename__ = 'role_permissoes'

    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), primary_key=True)
    permissao_id = db.Column(db.Integer, db.ForeignKey('permissoes.id'), primary_key=True)


class PermissaoUsuario(db.Model):
    """Permissões individuais de um usuário (override do role)"""
    __tablename__ = 'permissoes_usuarios'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    permissao_id = db.Column(db.Integer, db.ForeignKey('permissoes.id'), nullable=False, index=True)
    tipo = db.Column(db.String(10), default='allow')  # 'allow' ou 'deny'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('usuario_id', 'permissao_id', name='unique_usuario_permissao'),
        db.Index('idx_permissao_usuario_tipo', 'usuario_id', 'tipo'),
    )
    
    usuario = db.relationship('Usuario', backref='permissoes_individuais')
    permissao = db.relationship('Permissao')

    def to_dict(self):
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'permissao': self.permissao.to_dict(),
            'tipo': self.tipo
        }
