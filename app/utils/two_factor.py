"""
Helper para autenticação de dois fatores (2FA)
"""
import pyotp
import qrcode
import io
import base64
import json


def generate_secret():
    """Gera um novo segredo TOTP"""
    return pyotp.random_base32()


def generate_qr_code(secret, email, nome_sistema="OBRAS PRO"):
    """Gera QR code para configuração do autenticador"""
    # URI para Google Authenticator
    uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=email,
        issuer_name=nome_sistema
    )
    
    # Gerar QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Converter para base64
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{img_base64}"


def verify_token(secret, token):
    """Verifica um token TOTP"""
    totp = pyotp.TOTP(secret)
    return totp.verify(token, valid_window=1)
