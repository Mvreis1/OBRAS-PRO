"""
Configurações centralizadas do sistema com python-decouple
"""

import secrets
from pathlib import Path

from decouple import AutoConfig

# Setup decouple: auto-detecta .env no projeto
config = AutoConfig(search_path=str(Path(__file__).resolve().parent.parent))

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / 'instance'

INSTANCE_DIR.mkdir(exist_ok=True)

# Banco de dados
DB_PATH = config('DATABASE_URL', default=str(INSTANCE_DIR / 'obras_financeiro.db'))

# SECRET_KEY: Obrigatória em produção, usa chave temporária em desenvolvimento
_secret_key = config('SECRET_KEY', default=None)
if not _secret_key:
    if config('FLASK_ENV', default='development') == 'production':
        raise RuntimeError(
            'SECRET_KEY deve ser definida como variável de ambiente em produção! '
            "Execute: export SECRET_KEY='sua-chave-secreta-aqui'"
        )
    _secret_key = secrets.token_hex(32)
    print('AVISO: Usando SECRET_KEY temporária. Defina SECRET_KEY para produção.')

SECRET_KEY = _secret_key

VERSAO_SISTEMA = '1.0.0'
NOME_SISTEMA = 'OBRAS PRO'
SLOGAN = 'Gestao Financeira Professional'
SITE_OFICIAL = 'https://obraspro.com.br'
EMAIL_SUPORTE = 'suporte@obraspro.com.br'

# Configuracoes de IA
OPENAI_API_KEY = config('OPENAI_API_KEY', default='')
OPENAI_MODEL = config('OPENAI_MODEL', default='gpt-3.5-turbo')
GEMINI_API_KEY = config('GEMINI_API_KEY', default='')
CLAUDE_API_KEY = config('CLAUDE_API_KEY', default='')

# Configuracoes de Email (SMTP)
MAIL_SERVER = config('MAIL_SERVER', default='')
MAIL_PORT = config('MAIL_PORT', default=587, cast=int)
MAIL_USE_TLS = config('MAIL_USE_TLS', default=True, cast=bool)
MAIL_USERNAME = config('MAIL_USERNAME', default='')
MAIL_PASSWORD = config('MAIL_PASSWORD', default='')
MAIL_DEFAULT_SENDER = config('MAIL_DEFAULT_SENDER', default='noreply@obraspro.com.br')

CATEGORIAS_DESPESA = [
    'Materiais de Construção',
    'Mão de Obra',
    'Equipamentos',
    'Serviços Profissionais',
    'Transporte',
    'Aluguel de Equipamentos',
    'Licenças e Permissões',
    'Seguros',
    'Energia Elétrica',
    'Água',
    'Combustível',
    'Alimentação',
    'Uniformes e EPIs',
    'Manutenção',
    'Outros',
]

CATEGORIAS_RECEITA = [
    'Receita de Vendas',
    'Financiamento',
    'Investimento',
    'Adiantamento de Cliente',
    'Outros',
]

STATUS_OBRA = ['Planejamento', 'Em Execução', 'Paralisada', 'Concluída', 'Entregue']

FORMAS_PAGAMENTO = ['Dinheiro', 'PIX', 'Transferência', 'Débito', 'Crédito', 'Boleto', 'Cheque']

STATUS_PAGAMENTO = ['Pago', 'Pendente', 'Atrasado', 'Cancelado']

# Configurações de Segurança
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=False, cast=bool)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
PERMANENT_SESSION_LIFETIME = config('SESSION_LIFETIME', default=86400, cast=int)
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
UPLOAD_ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx'}

# Rate Limiting
FLASK_ENV = config('FLASK_ENV', default='development')
CACHE_TYPE = config('CACHE_TYPE', default='simple')
REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')
RATELIMIT_STORAGE_URL = config('RATELIMIT_STORAGE_URL', default='memory://')
RATELIMIT_DEFAULT = config('RATELIMIT_DEFAULT', default='100 per hour')
RATELIMIT_LOGIN = config('RATELIMIT_LOGIN', default='10 per minute')

# CORS
ALLOWED_ORIGINS = config(
    'ALLOWED_ORIGINS', default='', cast=lambda s: [x.strip() for x in s.split(',') if x.strip()]
)

# Configurações de Pool de Conexões (para PostgreSQL apenas)
# SQLite não suporta estas opções
_db_url = DB_PATH
if _db_url and ('postgres://' in _db_url or 'postgresql://' in _db_url):
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'max_overflow': 20,
        'pool_timeout': 30,
        'pool_recycle': 1800,
    }
else:
    SQLALCHEMY_ENGINE_OPTIONS = {}


def validate_production_config():
    """Valida configurações obrigatórias em produção"""
    if config('FLASK_ENV', default='development') == 'production':
        errors = []
        if not config('SECRET_KEY', default=None):
            errors.append('SECRET_KEY é obrigatória em produção')
        if not config('RATELIMIT_STORAGE_URL', default=None):
            errors.append('Configure RATELIMIT_STORAGE_URL para produção')

        if errors:
            raise RuntimeError('Erros de configuração em produção:\n' + '\n'.join(errors))
