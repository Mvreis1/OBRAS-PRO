"""Empresa service - Company management"""

import re

from app.models import Empresa, Usuario, db


class EmpresaService:
    """Service for company creation and management"""

    @staticmethod
    def validar_slug(slug):
        """Validate slug format. Returns (valid, error_message)"""
        if not slug:
            return False, 'URL é obrigatória.'
        if not re.match(r'^[a-z0-9-]+$', slug):
            return False, 'URL deve conter apenas letras, números e hífen.'
        return True, None

    @staticmethod
    def verificar_slug_disponivel(slug):
        """Check if slug is available. Returns (available, error_message)"""
        if Empresa.query.filter_by(slug=slug).first():
            return False, 'URL já está em uso. Escolha outro.'
        return True, None

    @staticmethod
    def criar_empresa(nome, slug, cnpj, telefone, email, senha):
        """Create empresa and admin user. Returns (empresa, admin_user, error_message)"""
        # Validate slug
        valid, error = EmpresaService.validar_slug(slug)
        if not valid:
            return None, None, error

        # Check slug availability
        available, error = EmpresaService.verificar_slug_disponivel(slug)
        if not available:
            return None, None, error

        # Create empresa
        empresa = Empresa(
            nome=nome,
            slug=slug,
            cnpj=cnpj,
            telefone=telefone,
            email=email,
            plano='free',
            max_usuarios=1,
            max_obras=5,
        )
        db.session.add(empresa)
        db.session.flush()

        # Create admin user
        admin = EmpresaService.criar_admin_padrao(empresa, email, senha, nome)
        db.session.commit()

        return empresa, admin, None

    @staticmethod
    def criar_admin_padrao(empresa, email, senha, nome_empresa):
        """Create default admin user for empresa"""
        from app.models.acesso import Role

        admin_role = Role.query.filter_by(nome='Administrador', is_system=True).first()
        if not admin_role:
            admin_role = Role.query.filter_by(is_system=True).first()

        admin = Usuario(
            empresa_id=empresa.id,
            nome=nome_empresa,
            email=email,
            username=email.split('@')[0][:50],
            cargo='Administrador',
            role='admin',
            role_id=admin_role.id if admin_role else None,
        )
        admin.set_senha(senha)
        db.session.add(admin)
        return admin
