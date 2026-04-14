"""
Rotas de autenticação
"""
import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from datetime import timedelta
from werkzeug.security import check_password_hash
from app.models import db, Empresa, Usuario
from app.utils import get_empresa_id
from app.utils.validacao import validate_email, validate_password, validate_cnpj_format
import pyotp


def login_required(f):
    """Decorator para rotas que exigem login"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Faça login para acessar esta página.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Rate limiting via Flask-Limiter configurado no app
    if request.method == 'POST':
        from datetime import datetime, timedelta
        
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')
        lembrar = request.form.get('lembrar')

        # Validação básica de input
        if not email or not senha:
            flash('Preencha todos os campos.', 'danger')
            return render_template('auth/login.html')

        if not validate_email(email):
            flash('Email inválido.', 'danger')
            return render_template('auth/login.html')

        # Limitar tamanho do input para prevenir ataques
        if len(email) > 120 or len(senha) > 128:
            flash('Dados inválidos.', 'danger')
            return render_template('auth/login.html')

        usuario = Usuario.query.filter_by(email=email, ativo=True).first()

        if usuario:
            # Verificar se usuário está bloqueado
            if usuario.bloqueado_ate and usuario.bloqueado_ate > datetime.utcnow():
                flash('Conta temporariamente bloqueada. Tente novamente mais tarde.', 'danger')
                return render_template('auth/login.html')
            
            if usuario and usuario.verificar_senha(senha):
                # Login bem-sucedido - resetar tentativas
                usuario.tentativas_login = 0
                usuario.bloqueado_ate = None
                db.session.commit()
                
                empresa = db.session.get(Empresa, usuario.empresa_id)
                if not empresa or not empresa.ativo:
                    flash('Empresa inativa ou não encontrada.', 'danger')
                    return render_template('auth/login.html')

                # Se 2FA está habilitado, gerar novo session ID para evitar fixation
                if usuario.two_factor_enabled:
                    # Regenerar sessão completamente (nova session ID)
                    session_regenerate()
                    
                    # Usar temporary session para 2FA (não autenticado ainda)
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
                    
                    flash('Insira o código de verificação do seu autenticador.', 'info')
                    return redirect(url_for('auth.verificar_2fa'))

                # Login normal (sem 2FA)
                session_regenerate()
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

                flash('Login realizado com sucesso!', 'success')

                from app.routes.notificacoes import gerar_alertas
                gerar_alertas(usuario.empresa_id)

                return redirect(url_for('main.dashboard'))
            else:
                # Login falhou - incrementar tentativas
                if usuario:
                    usuario.tentativas_login += 1
                    if usuario.tentativas_login >= 5:
                        usuario.bloqueado_ate = datetime.utcnow() + timedelta(minutes=15)
                        db.session.commit()
                        flash('Muitas tentativas falhas. Conta bloqueada por 15 minutos.', 'danger')
                        return render_template('auth/login.html')
                    db.session.commit()
                
                flash('Email ou senha inválidos.', 'danger')
        else:
            flash('Email ou senha inválidos.', 'danger')

    return render_template('auth/login.html')


def session_regenerate():
    """Regenera ID de sessão para prevenir fixation"""
    session.clear()


@auth_bp.route('/empresa/nova', methods=['GET', 'POST'])
def nova_empresa():
    """Criar nova empresa (cadastro inicial)"""
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()[:200]
        slug = request.form.get('slug', '').lower().strip().replace(' ', '-')[:50]
        cnpj = request.form.get('cnpj', '').strip()[:20]
        telefone = request.form.get('telefone', '').strip()[:20]
        email = request.form.get('email', '').strip().lower()[:120]
        senha = request.form.get('senha', '')
        
        # Validações
        if not all([nome, slug, email, senha]):
            flash('Preencha todos os campos obrigatórios.', 'danger')
            return render_template('auth/nova_empresa.html')
        
        if not validate_email(email):
            flash('Email inválido.', 'danger')
            return render_template('auth/nova_empresa.html')
        
        valid_pwd, pwd_msg = validate_password(senha)
        if not valid_pwd:
            flash(pwd_msg, 'danger')
            return render_template('auth/nova_empresa.html')
        
        # Validar slug (apenas letras, números e hífen)
        if not re.match(r'^[a-z0-9-]+$', slug):
            flash('URL deve conter apenas letras, números e hífen.', 'danger')
            return render_template('auth/nova_empresa.html')
        
        if Empresa.query.filter_by(slug=slug).first():
            flash('URL já está em uso. Escolha outro.', 'danger')
            return render_template('auth/nova_empresa.html')
        
        empresa = Empresa(
            nome=nome,
            slug=slug,
            cnpj=cnpj,
            telefone=telefone,
            email=email,
            plano='free',
            max_usuarios=1,
            max_obras=5
        )
        db.session.add(empresa)
        db.session.flush()

        # Find Admin role or fallback to first system role
        from app.models.acesso import Role
        admin_role = Role.query.filter_by(nome='Administrador', is_system=True).first()
        if not admin_role:
            admin_role = Role.query.filter_by(is_system=True).first()

        admin = Usuario(
            empresa_id=empresa.id,
            nome=nome,
            email=email,
            username=email.split('@')[0][:50],
            cargo='Administrador',
            role='admin',
            role_id=admin_role.id if admin_role else None
        )
        admin.set_senha(senha)
        db.session.add(admin)
        db.session.commit()
        
        session.clear()
        session['usuario_id'] = admin.id
        session['empresa_id'] = empresa.id
        session['empresa_nome'] = empresa.nome
        session['empresa_slug'] = empresa.slug
        session['usuario_nome'] = admin.nome
        session['usuario_username'] = admin.username
        session['usuario_role'] = admin.role
        
        flash('Empresa cadastrada com sucesso!', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('auth/nova_empresa.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))


@auth_bp.route('/recuperar-senha', methods=['POST'])
def recuperar_senha():
    import secrets
    import string
    from datetime import datetime, timedelta
    
    email = request.form.get('email')
    empresa_slug = request.form.get('empresa')
    
    empresa = Empresa.query.filter_by(slug=empresa_slug).first()
    if not empresa:
        flash('Empresa não encontrada.', 'danger')
        return redirect(url_for('auth.login'))
    
    usuario = Usuario.query.filter_by(empresa_id=empresa.id, email=email).first()
    if not usuario:
        # Não revelar se email existe ou não (segurança)
        flash('Se o email existir, você receberá instruções de recuperação.', 'info')
        return redirect(url_for('auth.login'))
    
    # Gerar token de recuperação seguro
    token = secrets.token_urlsafe(32)
    expiry = datetime.utcnow() + timedelta(hours=1)
    
    # Armazenar token temporariamente no usuário (em produção, usar tabela separada)
    usuario.token_recuperacao = token
    usuario.token_expiry = expiry
    db.session.commit()
    
    # Em produção: enviar email com link de recuperação
    # Por agora, apenas notificar (implementar com token em mão)
    flash(f'Se o email existir, você receberá instruções de recuperação.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/recuperar-senha/definir/<token>', methods=['GET', 'POST'])
def definir_nova_senha(token):
    """Define nova senha usando token de recuperação"""
    usuario = Usuario.query.filter_by(token_recuperacao=token).first()
    
    if not usuario or not usuario.token_expiry:
        flash('Token inválido ou expirado.', 'danger')
        return redirect(url_for('auth.login'))
    
    if datetime.utcnow() > usuario.token_expiry:
        flash('Token expirado. Solicite novamente.', 'danger')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        nova_senha = request.form.get('senha')
        confirmar = request.form.get('confirmar')
        
        if nova_senha != confirmar:
            flash('As senhas não conferem.', 'danger')
            return render_template('auth/definir_senha.html')
        
        if len(nova_senha) < 6:
            flash('Senha deve ter pelo menos 6 caracteres.', 'danger')
            return render_template('auth/definir_senha.html')
        
        # Validar senha
        from app.routes.auth import validate_password
        valido, msg = validate_password(nova_senha)
        if not valido:
            flash(msg, 'danger')
            return render_template('auth/definir_senha.html')
        
        usuario.set_senha(nova_senha)
        usuario.token_recuperacao = None
        usuario.token_expiry = None
        db.session.commit()
        
        flash('Senha redefinida com sucesso! Faça login.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/definir_senha.html')


@auth_bp.route('/usuario/novo', methods=['GET', 'POST'])
@login_required
def novo_usuario():
    """Criar novo usuário na empresa"""
    empresa_id = session.get('empresa_id')
    empresa = db.session.get(Empresa, empresa_id)
    
    if empresa.usuarios.count() >= empresa.max_usuarios:
        flash('Limite de usuários atingido. Faça upgrade do plano.', 'warning')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        username = request.form.get('username')
        senha = request.form.get('senha')
        cargo = request.form.get('cargo')
        role = request.form.get('role')
        
        if Usuario.query.filter_by(empresa_id=empresa_id, email=email).first():
            flash('Email já cadastrado nesta empresa.', 'danger')
            return render_template('auth/novo_usuario.html')
        
        if Usuario.query.filter_by(empresa_id=empresa_id, username=username).first():
            flash('Username já existe.', 'danger')
            return render_template('auth/novo_usuario.html')
        
        usuario = Usuario(
            empresa_id=empresa_id,
            nome=nome,
            email=email,
            username=username,
            cargo=cargo,
            role=role
        )
        usuario.set_senha(senha)
        db.session.add(usuario)
        db.session.commit()
        
        flash(f'Usuário {nome} criado com sucesso!', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('auth/novo_usuario.html')


@auth_bp.route('/usuarios')
@login_required
def listar_usuarios():
    """Lista usuários da empresa"""
    empresa_id = session.get('empresa_id')
    usuarios = Usuario.query.filter_by(empresa_id=empresa_id).all()
    return render_template('auth/usuarios.html', usuarios=usuarios)


# ========================
# Rotas de 2FA
# ========================

@auth_bp.route('/2fa/verificar', methods=['GET', 'POST'])
def verificar_2fa():
    """Verifica código 2FA após login"""
    usuario_id = session.get('temp_usuario_id')
    if not usuario_id:
        flash('Faça login primeiro.', 'warning')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        token = request.form.get('token', '').strip()
        usar_backup = request.form.get('usar_backup')
        
        usuario = db.session.get(Usuario, usuario_id)
        if not usuario:
            flash('Usuário não encontrado.', 'danger')
            session.clear()
            return redirect(url_for('auth.login'))
        
        # Verificar token ou backup code
        if usuario.verify_2fa(token):
            # Login bem-sucedido
            session.clear()
            session['usuario_id'] = usuario.id
            session['empresa_id'] = session.get('temp_empresa_id') or usuario.empresa_id
            session['empresa_nome'] = session.get('temp_empresa_nome')
            session['empresa_slug'] = session.get('temp_empresa_slug')
            session['usuario_nome'] = usuario.nome
            session['usuario_username'] = session.get('temp_usuario_username') or usuario.username
            session['usuario_role'] = session.get('temp_usuario_role') or usuario.role
            
            if session.get('temp_lembra'):
                session.permanent = True
                current_app.permanent_session_lifetime = timedelta(days=30)
            
            # Limpar variáveis temporárias
            for key in list(session.keys()):
                if key.startswith('temp_'):
                    session.pop(key, None)
            
            flash('Login realizado com sucesso!', 'success')
            
            from app.routes.notificacoes import gerar_alertas
            gerar_alertas(usuario.empresa_id)
            
            return redirect(url_for('main.dashboard'))
        else:
            flash('Código inválido. Tente novamente.', 'danger')
    
    return render_template('auth/verificar_2fa.html')


@auth_bp.route('/2fa/configurar', methods=['GET', 'POST'])
@login_required
def configurar_2fa():
    """Configura 2FA para o usuário"""
    usuario = db.session.get(Usuario, session['usuario_id'])
    
    if request.method == 'POST':
        acao = request.form.get('acao')
        
        if acao == 'ativar':
            # Gerar novo segredo e confirmar na mesma página
            secret = session.get('temp_2fa_secret') or pyotp.random_base32()
            token = request.form.get('token', '').strip()
            
            if token and pyotp.TOTP(secret).verify(token, valid_window=1):
                usuario.enable_2fa(secret)
                db.session.commit()
                session.pop('temp_2fa_secret', None)
                flash('2FA ativado com sucesso!', 'success')
            else:
                flash('Código inválido. Tente novamente.', 'danger')
        
        elif acao == 'desativar':
            senha = request.form.get('senha_atual', '')
            if usuario.verificar_senha(senha):
                usuario.disable_2fa()
                db.session.commit()
                flash('Autenticação de dois fatores desativada.', 'success')
            else:
                flash('Senha incorreta.', 'danger')
    
    # Gerar QR code se ainda não estiver habilitado
    qr_code = None
    secret_display = None
    if not usuario.two_factor_enabled:
        import io
        import base64
        import qrcode
        
        secret = session.get('temp_2fa_secret') or pyotp.random_base32()
        session['temp_2fa_secret'] = secret
        
        # Gerar QR code como imagem base64
        uri = pyotp.totp.TOTP(secret).provisioning_uri(name=usuario.email, issuer_name='OBRAS PRO')
        qr = qrcode.make(uri)
        buffer = io.BytesIO()
        qr.save(buffer, format='PNG')
        qr_code = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
        secret_display = secret
    
    return render_template('auth/configurar_2fa.html', 
                         usuario=usuario,
                         qr_code=qr_code,
                         secret_display=secret_display)


@auth_bp.route('/2fa/confirmar', methods=['GET', 'POST'])
@login_required
def confirmar_2fa():
    """Confirma ativação de 2FA"""
    usuario = db.session.get(Usuario, session['usuario_id'])
    secret = session.get('temp_2fa_secret')
    
    if not secret:
        flash('Configure o 2FA primeiro.', 'warning')
        return redirect(url_for('auth.configurar_2fa'))
    
    if request.method == 'POST':
        token = request.form.get('token', '').strip()
        
        if pyotp.TOTP(secret).verify(token, valid_window=1):
            # Ativar 2FA
            usuario.enable_2fa(secret)
            db.session.commit()
            
            # Limpar sessão temporária
            session.pop('temp_2fa_secret', None)
            
            flash('Autenticação de dois fatores ativada com sucesso!', 'success')
            return redirect(url_for('auth.configurar_2fa'))
        else:
            flash('Código inválido. Verifique e tente novamente.', 'danger')
    
    return render_template('auth/confirmar_2fa.html', secret=secret)


@auth_bp.route('/2fa/backup-codes')
@login_required
def backup_codes_2fa():
    """Mostra códigos de backup do 2FA"""
    usuario = db.session.get(Usuario, session['usuario_id'])
    
    if not usuario.two_factor_enabled:
        flash('Habilite o 2FA primeiro.', 'warning')
        return redirect(url_for('auth.configurar_2fa'))
    
    return render_template('auth/backup_codes.html', 
                         codes=usuario.get_backup_codes())

