# Utils package
from flask import session

def get_empresa_id():
    """Retorna o empresa_id da sessão atual"""
    return session.get('empresa_id')

from app.utils.paginacao import Paginacao, paginar_query
from app.utils.two_factor import generate_secret, generate_qr_code, verify_token
from app.utils.excel_export import ExcelExport, format_currency_br, format_date_br

# Helpers financeiros
from app.utils.financeiro import (
    calcular_totais_obra,
    calcular_totais_empresa,
    calcular_despesas_por_categoria,
    calcular_gastos_por_obra,
    get_obras_com_maior_gasto,
    get_obras_por_status,
    get_lancamentos_por_periodo
)

# Helpers de data
from app.utils.dates import (
    FormatoData,
    parse_date,
    parse_datetime,
    format_date_br,
    format_datetime_br,
    format_date_iso,
    format_datetime_iso,
    get_date_range
)

# Helpers de validação
from app.utils.validacao import (
    get_empresa_ativa,
    verificar_empresa_ativa,
    get_usuario_ativo,
    get_obra_ativa,
    validar_cpf,
    validar_cnpj,
    validar_documento,
    formatar_cpf,
    formatar_cnpj
)

# Helpers de segurança e sanitização
from app.utils.sanitize import (
    sanitize_string,
    sanitize_int,
    sanitize_float,
    sanitize_date,
    sanitize_email,
    sanitize_search_query
)

# Helpers de logging
from app.utils.logging_utils import (
    log_acao,
    log_acesso,
    log_erro,
    log_performance,
    log_seguranca
)