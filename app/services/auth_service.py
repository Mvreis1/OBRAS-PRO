"""Auth service - Authentication and session management"""

from datetime import datetime, timedelta

from flask import current_app, session

from app.models import Empresa, Usuario, db


class AuthService:
    """Service for authentication, login flow, and session management"""

    @staticmethod
    def authenticate(email, senha):
        """Authenticate user and return (usuario, empresa, error_message)"""
        usuario = Usuario.query.filter_by(email=email, ativo=True).first()

        if not usuario:
            return None, None, 'Email ou senha inválidos.'

        # Check if account is locked
        if usuario.bloqueado_ate and usuario.bloqueado_ate > datetime.now():
            return None, None, 'Conta temporariamente bloqueada. Tente novamente mais tarde.'

        if not usuario.verificar_senha(senha):
            # Increment failed attempts
            usuario.tentativas_login += 1
            if usuario.tentativas_login >= 5:
                usuario.bloqueado_ate = datetime.now() + timedelta(minutes=15)
                db.session.commit()
                return None, None, 'Muitas tentativas falhas. Conta bloqueada por 15 minutos.'
            db.session.commit()
            return None, None, 'Email ou senha inválidos.'

        # Successful login - reset attempts
        usuario.tentativas_login = 0
        usuario.bloqueado_ate = None
        db.session.commit()

        empresa = db.session.get(Empresa, usuario.empresa_id)
        if not empresa or not empresa.ativo:
            return None, None, 'Empresa inativa ou não encontrada.'

        return usuario, empresa, None

    @staticmethod
    def create_authenticated_session(usuario, empresa, lembrar=False):
        """Create full authenticated session"""
        AuthService._regenerate_session()

        session['usuario_id'] = usuario.id
        session['empresa_id'] = usuario.empresa_id
        session['empresa_nome'] = empresa.nome
        session['empresa_slug'] = empresa.slug
        session['usuario_nome'] = usuario.nome
        session['usuario_username'] = usuario.username
        session['usuario_role'] = usuario.role

        if lembrar:
            session.permanent = True
            current_app.permanent_session_lifetime = timedelta(days=30)

    @staticmethod
    def create_temp_2fa_session(usuario, empresa, lembrar=False):
        """Create temporary session for 2FA verification"""
        AuthService._regenerate_session()

        session.clear()
        session['temp_usuario_id'] = usuario.id
        session['temp_empresa_id'] = usuario.empresa_id
        session['temp_empresa_nome'] = empresa.nome
        session['temp_empresa_slug'] = empresa.slug
        session['temp_usuario_nome'] = usuario.nome
        session['temp_usuario_username'] = usuario.username
        session['temp_usuario_role'] = usuario.role

        if lembrar:
            session['temp_lembra'] = True

    @staticmethod
    def complete_2fa_login(usuario):
        """Complete login after successful 2FA verification"""
        temp_data = {
            'empresa_id': session.get('temp_empresa_id'),
            'empresa_nome': session.get('temp_empresa_nome'),
            'empresa_slug': session.get('temp_empresa_slug'),
            'usuario_username': session.get('temp_usuario_username'),
            'usuario_role': session.get('temp_usuario_role'),
            'lembrar': session.get('temp_lembra'),
        }

        session.clear()
        session['usuario_id'] = usuario.id
        session['empresa_id'] = temp_data['empresa_id'] or usuario.empresa_id
        session['empresa_nome'] = temp_data['empresa_nome']
        session['empresa_slug'] = temp_data['empresa_slug']
        session['usuario_nome'] = usuario.nome
        session['usuario_username'] = temp_data['usuario_username'] or usuario.username
        session['usuario_role'] = temp_data['usuario_role'] or usuario.role

        if temp_data['lembrar']:
            session.permanent = True
            current_app.permanent_session_lifetime = timedelta(days=30)

        # Clean up temp keys
        for key in list(session.keys()):
            if key.startswith('temp_'):
                session.pop(key, None)

    @staticmethod
    def _regenerate_session():
        """Regenerate session ID to prevent fixation"""
        import secrets

        dados_temp = {}
        keys_para_preservar = [
            '_csrf_token',
            '_user_id',
            'usuario_id',
            'empresa_id',
            'empresa_nome',
            'empresa_slug',
            'usuario_nome',
            'usuario_username',
            'usuario_role',
        ]

        for key in keys_para_preservar:
            if key in session:
                dados_temp[key] = session[key]

        session['_session_id'] = secrets.token_hex(32)
        session.permanent = True

        for key, value in dados_temp.items():
            session[key] = value

    @staticmethod
    def create_empresa_session(admin, empresa):
        """Create session after empresa registration"""
        session.clear()
        session['usuario_id'] = admin.id
        session['empresa_id'] = empresa.id
        session['empresa_nome'] = empresa.nome
        session['empresa_slug'] = empresa.slug
        session['usuario_nome'] = admin.nome
        session['usuario_username'] = admin.username
        session['usuario_role'] = admin.role
