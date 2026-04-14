"""
Configurações centralizadas do sistema
"""
import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"

INSTANCE_DIR.mkdir(exist_ok=True)

DB_PATH = os.environ.get('DATABASE_URL', str(INSTANCE_DIR / "obras_financeiro.db"))

# SECRET_KEY: Obrigatória em produção, usa chave temporária em desenvolvimento
_secret_key = os.environ.get("SECRET_KEY")
if not _secret_key:
    if os.environ.get('FLASK_ENV') == 'production':
        raise RuntimeError(
            "SECRET_KEY deve ser definida como variável de ambiente em produção! "
            "Execute: export SECRET_KEY='sua-chave-secreta-aqui'"
        )
    _secret_key = secrets.token_hex(32)
    print("AVISO: Usando SECRET_KEY temporária. Defina SECRET_KEY para produção.")

SECRET_KEY = _secret_key

VERSAO_SISTEMA = "1.0.0"
NOME_SISTEMA = "OBRAS PRO"
SLOGAN = "Gestao Financeira Professional"
SITE_OFICIAL = "https://obraspro.com.br"
EMAIL_SUPORTE = "suporte@obraspro.com.br"

# Configuracoes de IA
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")

# Configuracoes de Email (Mailgun/SendGrid/etc)
MAIL_SERVER = os.environ.get("MAIL_SERVER", "")
MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@obraspro.com.br")

CATEGORIAS_DESPESA = [
    "Materiais de Construção",
    "Mão de Obra",
    "Equipamentos",
    "Serviços Profissionais",
    "Transporte",
    "Aluguel de Equipamentos",
    "Licenças e Permissões",
    "Seguros",
    "Energia Elétrica",
    "Água",
    "Combustível",
    "Alimentação",
    "Uniformes e EPIs",
    "Manutenção",
    "Outros"
]

CATEGORIAS_RECEITA = [
    "Receita de Vendas",
    "Financiamento",
    "Investimento",
    "Adiantamento de Cliente",
    "Outros"
]

STATUS_OBRA = [
    "Planejamento",
    "Em Execução",
    "Paralisada",
    "Concluída",
    "Entregue"
]

FORMAS_PAGAMENTO = [
    "Dinheiro",
    "PIX",
    "Transferência",
    "Débito",
    "Crédito",
    "Boleto",
    "Cheque"
]

STATUS_PAGAMENTO = [
    "Pago",
    "Pendente",
    "Atrasado",
    "Cancelado"
]

# Configurações de Segurança
SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
PERMANENT_SESSION_LIFETIME = int(os.environ.get('SESSION_LIFETIME', 86400))  # 24 horas padrão
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
UPLOAD_ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx'}

# Rate Limiting
RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')
RATELIMIT_DEFAULT = os.environ.get('RATELIMIT_DEFAULT', '100 per hour')
RATELIMIT_LOGIN = os.environ.get('RATELIMIT_LOGIN', '10 per minute')

# Validação de produção
def validate_production_config():
    """Valida configurações obrigatórias em produção"""
    if os.environ.get('FLASK_ENV') == 'production':
        errors = []
        if not os.environ.get('SECRET_KEY'):
            errors.append("SECRET_KEY é obrigatória em produção")
        if not os.environ.get('RATELIMIT_STORAGE_URL'):
            errors.append("Configure RATELIMIT_STORAGE_URL para produção")
        
        # Verificar se está usando chave temporária
        _secret = os.environ.get("SECRET_KEY")
        if not _secret:
            print("AVISO: Usando SECRET_KEY temporária em desenvolvimento.")
        
        if errors:
            raise RuntimeError("Erros de configuração em produção:\n" + "\n".join(errors))
