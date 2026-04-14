"""
Helpers para parsing de datas
"""
from datetime import datetime, date

# Constantes de formato padronizadas
class FormatoData:
    """Constantes de formato de data"""
    # ISO (para APIs/JSON/banco)
    ISO = '%Y-%m-%d'
    ISO_DATETIME = '%Y-%m-%d %H:%M:%S'
    
    # Brasileiro (para UI/exibição)
    BR = '%d/%m/%Y'
    BR_DATETIME = '%d/%m/%Y %H:%M'
    
    # Curto
    BR_SHORT = '%d/%m/%y'


def parse_date(date_str, formato='%Y-%m-%d'):
    """Parse de data com tratamento de erros"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, formato).date()
    except (ValueError, TypeError):
        return None


def parse_datetime(datetime_str, formato='%Y-%m-%d %H:%M:%S'):
    """Parse de datetime com tratamento de erros"""
    if not datetime_str:
        return None
    try:
        return datetime.strptime(datetime_str, formato)
    except (ValueError, TypeError):
        return None


def format_date_br(data):
    """Formata data para padrão brasileiro (DD/MM/AAAA)"""
    if not data:
        return ''
    if isinstance(data, str):
        return data
    return data.strftime(FormatoData.BR)


def format_datetime_br(data):
    """Formata datetime para padrão brasileiro (DD/MM/AAAA HH:MM)"""
    if not data:
        return ''
    if isinstance(data, str):
        return data
    return data.strftime(FormatoData.BR_DATETIME)


def format_date_iso(data):
    """Formata data para ISO (YYYY-MM-DD)"""
    if not data:
        return None
    if isinstance(data, str):
        return data
    return data.strftime(FormatoData.ISO)


def format_datetime_iso(data):
    """Formata datetime para ISO"""
    if not data:
        return None
    if isinstance(data, str):
        return data
    return data.strftime(FormatoData.ISO_DATETIME)


def get_date_range(periodo, referencia=None):
    """Retorna início e fim de um período"""
    if referencia is None:
        referencia = date.today()
    
    if periodo == 'hoje':
        return referencia, referencia
    elif periodo == 'semana':
        from datetime import timedelta
        inicio = referencia - timedelta(days=referencia.weekday())
        return inicio, referencia
    elif periodo == 'mes':
        inicio = referencia.replace(day=1)
        return inicio, referencia
    elif periodo == 'ano':
        inicio = referencia.replace(month=1, day=1)
        return inicio, referencia
    else:
        return None, None