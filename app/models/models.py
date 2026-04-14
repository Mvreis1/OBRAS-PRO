"""
Modelos do banco de dados
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class SoftDeleteMixin:
    """Mixin para soft delete - adiciona campo deleted_at"""
    deleted_at = db.Column(db.DateTime, nullable=True, default=None)
    
    def soft_delete(self):
        """Marca registro como excluído"""
        self.deleted_at = datetime.utcnow()
    
    def restore(self):
        """Restaura registro excluído"""
        self.deleted_at = None
    
    @classmethod
    def active(cls):
        """QueryBuilder para buscar apenas registros ativos"""
        return cls.query.filter(cls.deleted_at.is_(None))


class Empresa(db.Model):
    """Empresas (multi-tenant) - cada empresa tem seus próprios dados isolados"""
    __tablename__ = 'empresas'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    cnpj = db.Column(db.String(20))
    telefone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    endereco = db.Column(db.String(300))
    logo = db.Column(db.String(500))
    plano = db.Column(db.String(30), default="free")
    max_usuarios = db.Column(db.Integer, default=1)
    max_obras = db.Column(db.Integer, default=5)
    ativo = db.Column(db.Boolean, default=True)
    trial_ativo = db.Column(db.Boolean, default=True)
    trial_expira = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    usuarios = db.relationship('Usuario', backref='empresa', lazy='dynamic')
    obras = db.relationship('Obra', backref='empresa', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'slug': self.slug,
            'cnpj': self.cnpj,
            'telefone': self.telefone,
            'email': self.email,
            'plano': self.plano,
            'max_usuarios': self.max_usuarios,
            'max_obras': self.max_obras,
            'ativo': self.ativo,
            'trial_ativo': self.trial_ativo
        }


class Usuario(db.Model):
    """Usuario do sistema"""
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False, index=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(50), nullable=False)
    senha_hash = db.Column(db.String(256), nullable=False)
    cargo = db.Column(db.String(50), default="Administrador")
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=True, index=True)
    # Legacy field - deprecated: use role_id instead
    role = db.Column(db.String(20), default="admin")
    ativo = db.Column(db.Boolean, default=True, index=True)
    
    # 2FA fields
    totp_secret = db.Column(db.String(32), unique=True, nullable=True)
    two_factor_enabled = db.Column(db.Boolean, default=False)
    backup_codes = db.Column(db.Text, nullable=True)
    
    # Password recovery
    token_recuperacao = db.Column(db.String(64), nullable=True)
    token_expiry = db.Column(db.DateTime, nullable=True)
    tentativas_login = db.Column(db.Integer, default=0)
    bloqueado_ate = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('empresa_id', 'username', name='unique_username_empresa'),
        db.UniqueConstraint('empresa_id', 'email', name='unique_email_empresa'),
        db.Index('idx_usuario_empresa_ativo', 'empresa_id', 'ativo'),
    )
    
    # RBAC relationship
    role_obj = db.relationship('Role', backref='usuarios', lazy='select')

    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)
    
    def has_permission(self, modulo, acao=None):
        """Verifica se usuário tem permissão para um módulo/ação"""
        from app.models.acesso import Permissao, PermissaoUsuario
        
        # Check individual denials first (highest priority)
        deny = PermissaoUsuario.query.filter_by(
            usuario_id=self.id, 
            tipo='deny'
        ).join(Permissao).filter(
            Permissao.modulo == modulo
        ).all()
        for d in deny:
            if acao is None or d.permissao.acao == acao or d.permissao.acao == '*':
                return False
        
        # Check individual allows
        if acao:
            allow = PermissaoUsuario.query.filter_by(
                usuario_id=self.id, 
                tipo='allow'
            ).join(Permissao).filter(
                (Permissao.modulo == modulo) & 
                ((Permissao.acao == acao) | (Permissao.acao == '*'))
            ).first()
            if allow:
                return True
        
        # Check role permissions - eager load no role_obj
        if self.role_id:
            from app.models.acesso import RolePermissao, Permissao as PermissaoModel
            role_perms = db.session.query(RolePermissao).join(PermissaoModel).filter(
                RolePermissao.role_id == self.role_id,
                PermissaoModel.modulo == modulo
            ).all()
            
            for rp in role_perms:
                perm = db.session.get(PermissaoModel, rp.permissao_id)
                if acao is None or perm.acao == acao or perm.acao == '*':
                    return True
        
        return False
    
    def get_permissoes(self):
        """Retorna todas as permissões do usuário (role + individuais)"""
        from app.models.acesso import PermissaoUsuario
        
        perms = set()
        
        # Role permissions
        if self.role_obj and self.role_obj.permissoes:
            for p in self.role_obj.permissoes:
                perms.add((p.modulo, p.acao))
        
        # Individual permissions
        for pu in self.permissoes_individuais:
            if pu.tipo == 'allow':
                perms.add((pu.permissao.modulo, pu.permissao.acao))
            elif pu.tipo == 'deny' and (pu.permissao.modulo, pu.permissao.acao) in perms:
                perms.remove((pu.permissao.modulo, pu.permissao.acao))
        
        return perms
    
    def enable_2fa(self, secret):
        """Habilita 2FA para o usuário"""
        import pyotp
        import json
        self.totp_secret = secret
        self.two_factor_enabled = True
        # Generate 10 backup codes
        self.backup_codes = json.dumps([pyotp.random_base32()[:10].lower() for _ in range(10)])
    
    def disable_2fa(self):
        """Desabilita 2FA"""
        self.totp_secret = None
        self.two_factor_enabled = False
        self.backup_codes = None
    
    def verify_2fa(self, token):
        """Verifica token 2FA"""
        import pyotp
        import json
        if not self.two_factor_enabled or not self.totp_secret:
            return False
        
        # Check TOTP
        totp = pyotp.TOTP(self.totp_secret)
        if totp.verify(token, valid_window=1):
            return True
        
        # Check backup codes
        if self.backup_codes:
            codes = json.loads(self.backup_codes)
            if token.lower() in codes:
                codes.remove(token.lower())
                self.backup_codes = json.dumps(codes)
                from app.models import db
                db.session.commit()
                return True
        
        return False
    
    def get_backup_codes(self):
        """Retorna lista de códigos de backup"""
        import json
        if self.backup_codes:
            return json.loads(self.backup_codes)
        return []

    def to_dict(self):
        return {
            'id': self.id,
            'empresa_id': self.empresa_id,
            'nome': self.nome,
            'email': self.email,
            'username': self.username,
            'cargo': self.cargo,
            'role': self.role,
            'role_id': self.role_id,
            'ativo': self.ativo,
            'two_factor_enabled': self.two_factor_enabled
        }


class Obra(db.Model, SoftDeleteMixin):
    """Obras do sistema"""
    __tablename__ = 'obras'
    
    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False, index=True)
    nome = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text)
    endereco = db.Column(db.String(300))
    orcamento_previsto = db.Column(db.Float, default=0)
    data_inicio = db.Column(db.Date, index=True)
    data_fim_prevista = db.Column(db.Date, index=True)
    data_fim_real = db.Column(db.Date)
    status = db.Column(db.String(50), default="Planejamento", index=True)
    progresso = db.Column(db.Integer, default=0)
    responsavel = db.Column(db.String(100))
    cliente = db.Column(db.String(200))
    imagem = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    lancamentos = db.relationship('Lancamento', backref='obra', lazy='dynamic', cascade='all, delete-orphan')
    
    __table_args__ = (
        db.Index('idx_obra_empresa_status', 'empresa_id', 'status'),
        db.Index('idx_obra_empresa_data', 'empresa_id', 'data_fim_prevista'),
    )
    
    def to_dict(self, include_totals=True):
        if not include_totals:
            return {
                'id': self.id,
                'nome': self.nome,
                'descricao': self.descricao,
                'endereco': self.endereco,
                'orcamento_previsto': self.orcamento_previsto,
                'data_inicio': self.data_inicio.strftime('%Y-%m-%d') if self.data_inicio else None,
                'data_fim_prevista': self.data_fim_prevista.strftime('%Y-%m-%d') if self.data_fim_prevista else None,
                'data_fim_real': self.data_fim_real.strftime('%Y-%m-%d') if self.data_fim_real else None,
                'status': self.status,
                'progresso': self.progresso,
                'responsavel': self.responsavel,
                'cliente': self.cliente,
            }
        
        # Usar agregação SQL para evitar N+1
        from sqlalchemy import func, case
        from app.models import db
        
        result = db.session.query(
            func.sum(case((Lancamento.tipo == 'Despesa', Lancamento.valor), else_=0)).label('total_despesa'),
            func.sum(case((Lancamento.tipo == 'Receita', Lancamento.valor), else_=0)).label('total_receita')
        ).filter(Lancamento.obra_id == self.id).first()
        
        total_gasto = result.total_despesa or 0
        total_receita = result.total_receita or 0
        
        return {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao,
            'endereco': self.endereco,
            'orcamento_previsto': self.orcamento_previsto,
            'data_inicio': self.data_inicio.strftime('%Y-%m-%d') if self.data_inicio else None,
            'data_fim_prevista': self.data_fim_prevista.strftime('%Y-%m-%d') if self.data_fim_prevista else None,
            'data_fim_real': self.data_fim_real.strftime('%Y-%m-%d') if self.data_fim_real else None,
            'status': self.status,
            'progresso': self.progresso,
            'responsavel': self.responsavel,
            'cliente': self.cliente,
            'total_gasto': total_gasto,
            'total_receita': total_receita,
            'saldo': total_receita - total_gasto
        }


class Lancamento(db.Model, SoftDeleteMixin):
    """Lancamentos financeiros"""
    __tablename__ = 'lancamentos'
    
    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False, index=True)
    obra_id = db.Column(db.Integer, db.ForeignKey('obras.id'), nullable=False, index=True)
    descricao = db.Column(db.String(200), nullable=False)
    categoria = db.Column(db.String(100), nullable=False, index=True)
    tipo = db.Column(db.String(20), nullable=False, index=True)
    valor = db.Column(db.Float, nullable=False)
    data = db.Column(db.Date, nullable=False, index=True)
    forma_pagamento = db.Column(db.String(50))
    status_pagamento = db.Column(db.String(20), default="Pago", index=True)
    parcelas = db.Column(db.Integer, default=1)
    observacoes = db.Column(db.Text)
    documento = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.Index('idx_lancamento_empresa_data', 'empresa_id', 'data'),
        db.Index('idx_lancamento_obra_tipo', 'obra_id', 'tipo'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'empresa_id': self.empresa_id,
            'obra_id': self.obra_id,
            'obra_nome': self.obra.nome if self.obra else '',
            'descricao': self.descricao,
            'categoria': self.categoria,
            'tipo': self.tipo,
            'valor': self.valor,
            'data': self.data.strftime('%Y-%m-%d') if self.data else None,
            'forma_pagamento': self.forma_pagamento,
            'status_pagamento': self.status_pagamento,
            'parcelas': self.parcelas,
            'observacoes': self.observacoes,
            'documento': self.documento
        }


class LogAtividade(db.Model):
    """Log de auditoria - registra todas as ações dos usuários"""
    __tablename__ = 'logs_atividade'
    
    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False, index=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    acao = db.Column(db.String(100), nullable=False)
    entidade = db.Column(db.String(50))
    entidade_id = db.Column(db.Integer)
    detalhes = db.Column(db.Text)
    ip = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    usuario = db.relationship('Usuario', backref='logs')
    
    def to_dict(self):
        return {
            'id': self.id,
            'usuario': self.usuario.nome if self.usuario else 'Sistema',
            'acao': self.acao,
            'entidade': self.entidade,
            'entidade_id': self.entidade_id,
            'detalhes': self.detalhes,
            'ip': self.ip,
            'created_at': self.created_at.strftime('%d/%m/%Y %H:%M')
        }


class Categoria(db.Model):
    """Categorias personalizadas"""
    __tablename__ = 'categorias'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    tipo = db.Column(db.String(20), nullable=False)
    cor = db.Column(db.String(20), default="#6c757d")
    icone = db.Column(db.String(50), default="bi-tag")
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'tipo': self.tipo,
            'cor': self.cor,
            'icone': self.icone
        }
