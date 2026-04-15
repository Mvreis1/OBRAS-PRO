# Utils package
from flask import session

from app.utils.dates import (
    FormatoData,
    format_date_br,
    format_date_iso,
    format_datetime_br,
    format_datetime_iso,
    get_date_range,
    parse_date,
    parse_datetime,
)
from app.utils.excel_export import (  # format_date_br já importado de dates
    ExcelExport,
    format_currency_br,
)

# Helpers financeiros
from app.utils.financeiro import (
    calcular_despesas_por_categoria,
    calcular_gastos_por_obra,
    calcular_totais_empresa,
    calcular_totais_obra,
    get_lancamentos_por_periodo,
    get_obras_com_maior_gasto,
    get_obras_por_status,
)

# Helpers de rotas (get_current_empresa_id, get_owned_or_404, etc.)
from app.utils.helpers import (
    cache_empresa_context,
    get_current_empresa,
    get_current_empresa_id,
    get_owned_or_404,
    get_user_context,
)

# Helpers de logging
from app.utils.logging_utils import log_acao, log_acesso, log_erro, log_performance, log_seguranca
from app.utils.paginacao import Paginacao, paginar_query

# Helpers de segurança e sanitização
from app.utils.sanitize import (
    sanitize_date,
    sanitize_email,
    sanitize_float,
    sanitize_int,
    sanitize_search_query,
    sanitize_string,
)
from app.utils.two_factor import generate_qr_code, generate_secret, verify_token

# Helpers de validação
from app.utils.validacao import (
    formatar_cnpj,
    formatar_cpf,
    get_empresa_ativa,
    get_obra_ativa,
    get_usuario_ativo,
    validar_cnpj,
    validar_cpf,
    validar_documento,
    verificar_empresa_ativa,
)
