"""
Helpers para validações comuns
"""
import re
from app.models import db


def validate_email(email):
    """Valida formato de email"""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password(password):
    """Valida força da senha: mínimo 8 caracteres, 1 letra e 1 número"""
    if not password:
        return False, "Senha é obrigatória."
    if len(password) < 8:
        return False, "A senha deve ter pelo menos 8 caracteres."
    if not re.search(r'[A-Za-z]', password):
        return False, "A senha deve conter pelo menos uma letra."
    if not re.search(r'[0-9]', password):
        return False, "A senha deve conter pelo menos um número."
    return True, ""


def validate_cnpj_format(cnpj):
    """Valida formato básico de CNPJ (apenas formato, não dígitos verificadores)"""
    if not cnpj:
        return False
    cnpj_clean = re.sub(r'[^0-9]', '', cnpj)
    return len(cnpj_clean) == 14


def get_empresa_ativa(empresa_id):
    """Busca empresa ativa pelo ID"""
    from app.models import Empresa
    return Empresa.query.filter_by(id=empresa_id, ativo=True).first()


def verificar_empresa_ativa(empresa_id):
    """Verifica se empresa está ativa"""
    empresa = get_empresa_ativa(empresa_id)
    return empresa is not None


def get_usuario_ativo(usuario_id, empresa_id):
    """Busca usuário ativo de uma empresa"""
    from app.models import Usuario
    return Usuario.query.filter_by(
        id=usuario_id, 
        empresa_id=empresa_id, 
        ativo=True
    ).first()


def get_obra_ativa(obra_id, empresa_id):
    """Busca obra ativa de uma empresa"""
    from app.models import Obra
    return Obra.query.filter_by(id=obra_id, empresa_id=empresa_id).first()


def validar_cpf(cpf):
    """Valida CPF brasileiro"""
    if not cpf:
        return False
    cpf = ''.join(filter(str.isdigit, cpf))
    if len(cpf) != 11:
        return False
    if cpf == cpf[0] * 11:
        return False
    for i in range(9):
        if cpf[i] != cpf[i+1]:
            break
    else:
        return False
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    return cpf[-2:] == f'{digito1}{digito2}'


def validar_cnpj(cnpj):
    """Valida CNPJ brasileiro"""
    if not cnpj:
        return False
    cnpj = ''.join(filter(str.isdigit, cnpj))
    if len(cnpj) != 14:
        return False
    if cnpj == cnpj[0] * 14:
        return False
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos1[i] for i in range(12))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    soma = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    return cnpj[-2:] == f'{digito1}{digito2}'


def validar_documento(documento):
    """Valida CPF ou CNPJ"""
    documento = ''.join(filter(str.isdigit, documento))
    if len(documento) == 11:
        return validar_cpf(documento)
    elif len(documento) == 14:
        return validar_cnpj(documento)
    return False


def formatar_cpf(cpf):
    """Formata CPF (XXX.XXX.XXX-XX)"""
    cpf = ''.join(filter(str.isdigit, cpf))
    if len(cpf) == 11:
        return f'{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}'
    return cpf


def formatar_cnpj(cnpj):
    """Formata CNPJ (XX.XXX.XXX/XXXX-XX)"""
    cnpj = ''.join(filter(str.isdigit, cnpj))
    if len(cnpj) == 14:
        return f'{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}'
    return cnpj