"""
Helpers para sanitização de inputs
"""

import re
from datetime import datetime


def sanitize_string(value, max_length=None, allow_html=False):
    """Sanitiza string de input"""
    if value is None:
        return None

    value = str(value).strip()

    if not allow_html:
        # Remover tags HTML
        value = re.sub(r'<[^>]+>', '', value)

    if max_length:
        value = value[:max_length]

    return value


def sanitize_int(value, default=0, min_val=None, max_val=None):
    """Sanitiza input inteiro"""
    try:
        result = int(value)
        if min_val is not None and result < min_val:
            return min_val
        if max_val is not None and result > max_val:
            return max_val
        return result
    except (ValueError, TypeError):
        return default


def sanitize_float(value, default=0.0, allow_zero=True):
    """Sanitiza input float"""
    try:
        result = float(str(value).replace(',', '.'))
        if not allow_zero and result == 0:
            return default
        return result
    except (ValueError, TypeError):
        return default


def sanitize_date(value, formato='%Y-%m-%d'):
    """Sanitiza data"""
    if not value:
        return None
    try:
        return datetime.strptime(str(value), formato).date()
    except (ValueError, TypeError):
        return None


def sanitize_email(email):
    """Sanitiza email"""
    if not email:
        return None
    email = str(email).strip().lower()
    # Regex básica para email
    if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return email
    return None


def sanitize_search_query(query, max_length=100):
    """Sanitiza query de busca"""
    if not query:
        return None
    query = str(query).strip()[:max_length]
    # Apenas caracteres permitidos
    query = re.sub(r'[^\w\s\-_@.]', '', query)
    return query or None
