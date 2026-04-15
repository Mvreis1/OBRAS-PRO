# ruff: noqa
"""
Guia de nomenclatura do sistema OBRAS PRO

Este arquivo define as convenções de nomenclatura para o projeto.
Todo o código deve seguir estas regras para manter consistência.

================================================================================
REGRAS GERAIS
================================================================================

1. VARIÁVEIS E FUNÇÕES: camelCase (Python standard)
   - goods ✅
   - totalAmount ✅
   - nome_usuario ❌ (snake_case para vars)
   - nomeUsuario ✅ (camelCase)

2. CLASSES: PascalCase
   - class UsuarioService ✅
   - class LancamentoFinanceiro ✅

3. CONSTANTES: UPPER_SNAKE_CASE
   - MAX_RETRY = 3 ✅
   - DATABASE_URL = '...' ✅

4. Arquivos/folders: snake_case
   - user_service.py ✅
   - financial_report.py ✅

================================================================================
TERMINOLOGIA PADRÃO: INGLÊS
================================================================================

EVITAR misturar português/inglês. Preferir termos em inglês:

| Português       | Inglês (usar)      |
|-----------------|-------------------|
| obra            | project           |
| lançamento     | transaction       |
| despesa         | expense           |
| receita         | revenue           |
| saldo           | balance           |
| cliente         | client            |
| fornecedor      | vendor            |
| contrato        | contract          |
| orçamento       | budget            |
| pagamento       | payment           |
| situação        | status            |
| descrição       | description       |
| início          | start_date        |
| fim             | end_date          |

================================================================================
NOMENCLATURA DE VARIÁVEIS (INGLÊS)
================================================================================

# Financial
revenue        # receita
expense        # despesa
balance        # saldo (diferença)
amount         # valor
total          # total
budget         # orçamento
paid           # pago
pending        # pendente

# Project
project        # obra
task            # tarefa
milestone       # marco
progress        # progresso
status          # situação
startDate       # data início
endDate         # data fim

# User/Auth
userId         # ID usuário
username       # nome usuário
email          # email
password       # senha
role           # perfil/permissão
permission     # permissão
active         # ativo
lastLogin      # último login

# Time
createdAt      # criado em
updatedAt      # atualizado em
dueDate        # data vencimento
expiryDate     # data expiração

# Query/Filter
page           # página
perPage        # por página
limit          # limite
offset         # offset
sortBy         # ordenar por
filterBy       # filtrar por

================================================================================
ABREVIATURAS COMUNS
================================================================================

ID         - Identifier
URL        - Uniform Resource Locator
API        - Application Programming Interface
DTO        - Data Transfer Object
VO         - Value Object
DAO        - Data Access Object
DTO        - Data Transfer Object
CRUD       - Create, Read, Update, Delete
HTTP       - Hypertext Transfer Protocol
JSON       - JavaScript Object Notation
SQL        - Structured Query Language
ORM        - Object-Relational Mapping

================================================================================
EXEMPLOS DE NOMENCLATURA
================================================================================

# ❌ Errado (mix português/inglês)
total_despesas = sum(l.valor for l in lancamentos)
nome_projeto = obra.nome
data_inicio_obra = obra.data_inicio
valor_total_receita = total_revenue

# ✅ Correto (inglês consistente)
totalExpenses = sum(transaction.amount for transaction in transactions)
projectName = project.name
projectStartDate = project.startDate
totalRevenue = revenue.total

# Funções
# def calculateProjectBalance(projectId):
#     """Calculate revenue - expenses for a project"""
#     ...
#
# def getActiveVendors(companyId):
#     """Fetch all active vendors for a company"""
#     ...
#
# # Classes
# class FinancialReport:
#     """Generate financial reports"""
#     
#     def getMonthlyRevenue(self, year):
#         ...
#
# class ProjectService:
#     """Manage project lifecycle"""
#     
#     def createProject(self, data):
#         ...

================================================================================
"""

# Constantes do sistema (inglês para código)
class Constants:
    """System-wide constants in English"""
    
    # Status
    STATUS_ACTIVE = "active"
    STATUS_INACTIVE = "inactive"
    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"
    
    # Transaction types
    TYPE_REVENUE = "revenue"
    TYPE_EXPENSE = "expense"
    
    # Project status
    PROJECT_PLANNING = "Planning"
    PROJECT_IN_PROGRESS = "In Progress"
    PROJECT_COMPLETED = "Completed"
    PROJECT_ON_HOLD = "On Hold"
    PROJECT_CANCELLED = "Cancelled"
    
    # Payment status
    PAYMENT_PAID = "paid"
    PAYMENT_PENDING = "pending"
    PAYMENT_OVERDUE = "overdue"

# Alias em português para compatibilidade (deprecated - usar英文)
# Estes são mantidos apenas para compatibilidade temporária
# NÃO usar em código novo
import warnings

def __getattr__(name):
    # Deprecation warnings
    if name in ['total_despesas', 'total_receitas', 'nome_obra']:
        warnings.warn(
            f"'{name}' is deprecated. Use English naming (totalExpenses, totalRevenue, projectName)",
            DeprecationWarning,
            stacklevel=2
        )
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")