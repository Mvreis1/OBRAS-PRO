# OBRAS_FINANCEIRO - Refactoring Analysis Report

**Date:** 2026-04-15
**Scope:** `app/` directory (routes, services, utils, models)
**Methodology:** Static analysis of code patterns, duplication detection, complexity analysis

---

## Executive Summary

The OBRAS_FINANCEIRO codebase is a Flask-based financial management system for construction projects. While it has a reasonable service-layer foundation, significant refactoring opportunities exist across **code duplication**, **N+1 query patterns**, **missing abstractions**, **import organization**, and **performance bottlenecks**.

**Key Metrics:**
- ~103 occurrences of `session.get('empresa_id')` (should be a helper)
- ~35 occurrences of `datetime.strptime(..., '%Y-%m-%d')` (should use existing `parse_date`)
- ~33 occurrences of `sum(l.valor for l in ...)` pattern (could use SQL aggregation)
- ~45 occurrences of `.filter_by(id=X, empresa_id=empresa_id).first_or_404()` (repeated ownership check)
- At least 8 routes with functions >50 lines
- Multiple N+1 query patterns in loops
- Inconsistent import organization across files

---

## 1. CODE DUPLICATION

### 1.1 Multi-Tenant Ownership Check Pattern (CRITICAL)
**Occurrences:** ~45 across all route files

Every route that accesses a resource repeats the same ownership verification pattern:

```python
empresa_id = session.get('empresa_id')
obj = Model.query.filter_by(id=obj_id, empresa_id=empresa_id).first_or_404()
```

**Files affected:**
- `routes/main.py`: lines 131, 233, 266, 336, 363, 481, 508, 565, 599, 628
- `routes/orcamentos.py`: lines 179, 193, 236, 248, 293, 319, 348, 395
- `routes/contratos.py`: lines 112, 141, 186, 198, 247, 262, 276
- `routes/fornecedores.py`: lines 118, 167, 197, 212
- `routes/banco.py`: lines 69, 115, 137, 149
- `routes/api.py`: lines 55, 389, 425, 446, 460, 493
- `routes/rbac.py`: lines 95, 144, 180, 252
- `routes/extrato.py`: line 56

**Suggested Improvement:**
Create a base repository or query helper:

```python
# app/utils/query_helpers.py
def get_owned_or_404(model, obj_id, empresa_id):
    """Get object owned by empresa or 404"""
    return model.query.filter_by(id=obj_id, empresa_id=empresa_id).first_or_404()

def get_owned_query(model, empresa_id):
    """Get base query filtered by empresa_id"""
    return model.query.filter_by(empresa_id=empresa_id)
```

**Impact:** Would eliminate ~90 lines of duplicated code across routes.

---

### 1.2 `empresa_id` Session Access Pattern (HIGH)
**Occurrences:** 103 times across the codebase

Every single route function starts with:
```python
empresa_id = session.get('empresa_id')
```

**Suggested Improvement:**
Create a helper and/or context processor:

```python
# In app/utils/__init__.py (already exists at line 7)
def get_current_empresa_id():
    return session.get('empresa_id')
```

Or use a Flask `@before_request` hook to inject it into `g`:

```python
@app.before_request
def load_empresa_context():
    g.empresa_id = session.get('empresa_id')
```

Then routes can use `g.empresa_id` directly.

**Impact:** Cleaner route code, easier to test, centralized session access.

---

### 1.3 Date Parsing Duplication (HIGH)
**Occurrences:** 35+ times

Pattern repeated across routes and services:
```python
datetime.strptime(request.form.get('data_inicio'), '%Y-%m-%d').date()
datetime.strptime(data_inicio, '%Y-%m-%d').date()
```

The project already has `app/utils/dates.py` with `parse_date()` function, but it is **inconsistently used**:
- `routes/contratos.py` correctly uses `parse_date()` (lines 66-67, 157-158)
- `routes/api.py` correctly uses `parse_date()` (lines 247, 362-363)
- `routes/main.py` does NOT use it (lines 199, 241, 246, 397, 399, 455, 489, 773, 775)
- `services/relatorio_service.py` does NOT use it (lines 22, 26, 59, 63, 136, 140, 195, 199)
- `routes/excel.py` does NOT use it (lines 59, 61)
- `routes/banco.py` does NOT use it (lines 166, 275, 278)

**Files to update:**
- `routes/main.py`: 9 occurrences
- `services/relatorio_service.py`: 8 occurrences
- `routes/excel.py`: 2 occurrences
- `routes/banco.py`: 3 occurrences
- `routes/fornecedores.py`: 1 occurrence
- `services/lancamento_service.py`: 4 occurrences
- `services/obra_service.py`: 3 occurrences

**Impact:** Consistency, error handling, reduced code size.

---

### 1.4 Receita/Despesa Summation Pattern (MEDIUM)
**Occurrences:** 33 times

This pattern appears in nearly every route and service that deals with financial data:
```python
total_despesas = sum(l.valor for l in lancamentos if l.tipo == 'Despesa')
total_receitas = sum(l.valor for l in lancamentos if l.tipo == 'Receita')
```

**Locations:**
- `routes/main.py`: lines 138-139, 532-533, 568-569, 606-607, 635-636, 778-779
- `routes/excel.py`: lines 93-94, 135-136, 199-200, 261-262
- `services/relatorio_service.py`: lines 30-31, 67-68, 100-101
- `services/lancamento_service.py`: lines 125-126
- `services/obra_alerta_service.py`: line 30
- `utils/pdf_export.py`: lines 263-264

**Performance Issue:** This loads ALL lancamentos into Python memory and sums in Python, instead of using SQL aggregation.

**Suggested Improvement:**
Use SQL aggregation (already done correctly in some places):
```python
# Current (bad - Python iteration):
lancamentos = Lancamento.query.filter_by(obra_id=obra_id).all()
total_despesas = sum(l.valor for l in lancamentos if l.tipo == 'Despesa')

# Better (SQL aggregation):
from sqlalchemy import case, func
result = db.session.query(
    func.sum(case((Lancamento.tipo == 'Despesa', Lancamento.valor), else_=0)).label('despesas'),
    func.sum(case((Lancamento.tipo == 'Receita', Lancamento.valor), else_=0)).label('receitas'),
).filter(Lancamento.obra_id == obra_id).first()
total_despesas = result.despesas or 0
total_receitas = result.receitas or 0
```

The pattern is already correctly implemented in:
- `routes/main.py` lines 52-63 (dashboard)
- `routes/banco.py` lines 87-98 (banco_detalhe)
- `app/utils/financeiro.py` (calcular_totais_obra, calcular_totais_empresa)

**Impact:** Significant performance improvement for large datasets; reduced memory usage.

---

### 1.5 Pagination + Filter Args Pattern (LOW-MEDIUM)
**Occurrences:** ~10 list views

Every list view repeats the same pagination setup and filter args construction:

```python
# Example from routes/contratos.py:32-55
paginacao = Paginacao(query, page=page, per_page=per_page)
filter_args = {}
if status_filter:
    filter_args['status'] = status_filter
if busca:
    filter_args['busca'] = busca
```

**Files:**
- `routes/main.py` (lancamentos): lines 387-438
- `routes/orcamentos.py` (orcamentos): lines 62-85
- `routes/contratos.py` (contratos): lines 32-55
- `routes/fornecedores.py` (fornecedores): lines 39-77

**Suggested Improvement:**
Create a query builder helper:
```python
class QueryBuilder:
    def __init__(self, model, empresa_id):
        self.query = model.query.filter_by(empresa_id=empresa_id)
        self.filters = {}

    def filter_by_field(self, field, value):
        if value:
            self.query = self.query.filter_by(**{field: value})
            self.filters[field] = value
        return self

    def filter_by_date_range(self, data_inicio, data_fim):
        if data_inicio:
            self.query = self.query.filter(Model.data >= parse_date(data_inicio))
        if data_fim:
            self.query = self.query.filter(Model.data <= parse_date(data_fim))
        return self

    def paginate(self, page, per_page):
        return Paginacao(self.query, page=page, per_page=per_page), self.filters
```

---

### 1.6 Import/Export File Validation Pattern (LOW)
**Occurrences:** 3 import routes

The file upload validation pattern is repeated:
```python
if 'arquivo' not in request.files:
    flash('Nenhum arquivo enviado', 'danger')
    return redirect(...)
file = request.files['arquivo']
if file.filename == '':
    flash('Nenhum arquivo selecionado', 'danger')
    return redirect(...)
```

**Files:**
- `routes/excel.py`: lines 340-347 (importar_lancamentos), lines 496-503 (importar_obras)
- `routes/extrato.py`: lines 59-63 (already uses validate_upload helper)

**Note:** `extrato.py` already has a `validate_upload()` helper (line 23). This should be moved to a shared utility and reused by `excel.py`.

---

## 2. FUNCTIONS TOO LONG OR COMPLEX

### 2.1 `routes/main.py` - `relatorios()` (60 lines)
**Location:** `main.py:692-750`

This function calls 6 different RelatorioService methods and passes 20+ template variables.

**Suggested Improvement:**
Create a `RelatorioViewData` class or dataclass to encapsulate all the report data:
```python
@dataclass
class RelatorioData:
    total_receitas: float
    total_despesas: float
    lucro_obras: list
    evolucao_mensal: list
    # ... etc
```

---

### 2.2 `routes/main.py` - `exportar_relatorio_financeiro_excel()` (148 lines)
**Location:** `excel.py:175-322`

This function generates a multi-sheet Excel report with 3 sheets. It should be delegated to a service.

**Suggested Improvement:**
Move to `services/excel_report_service.py`:
```python
class ExcelReportService:
    @staticmethod
    def generate_financial_report(empresa_id) -> BytesIO:
        # Build multi-sheet report
        pass
```

---

### 2.3 `routes/ia.py` - `chat_ia()` (55 lines)
**Location:** `ia.py:28-83`

Multiple conditional branches for different AI providers with repeated fallback patterns.

**Suggested Improvement:**
Use strategy pattern:
```python
class AIProvider(ABC):
    @abstractmethod
    def generate(self, mensagem, contexto): pass

class OpenAIProvider(AIProvider): ...
class GeminiProvider(AIProvider): ...
class ClaudeProvider(AIProvider): ...
class LocalProvider(AIProvider): ...

# Then:
provider = provider_factory(modelo, config)
resposta = provider.generate(mensagem, contexto)
```

---

### 2.4 `app/__init__.py` - `create_app()` (280+ lines)
**Location:** `__init__.py:30-582`

The application factory is extremely long. The debug/test routes (lines 231-581, ~350 lines) should be moved to a separate `routes/debug.py` blueprint.

**Suggested Improvement:**
```
app/routes/debug.py  - All /debug/*, /test*, /setup* routes
app/__init__.py      - Only app factory setup
```

---

### 2.5 `routes/excel.py` - `importar_lancamentos()` (108 lines)
**Location:** `excel.py:330-440`

Combines file validation, parsing, database operations, and flash messages.

**Suggested Improvement:**
Extract import logic to service layer (partially exists in `excel_import.py` but route still does too much).

---

### 2.6 `services/relatorio_service.py` - Multiple methods
Several methods load all records into memory then iterate in Python:
- `calcular_lucro_por_obra()` (line 47-83): N+1 pattern - iterates obras, queries lancamentos per obra
- `calcular_evolucao_mensal()` (line 86-113): Queries DB 12 times in a loop
- `calcular_orcamento_vs_realizado()` (line 116-180): N+1 pattern

These should use SQL GROUP BY and window functions.

---

## 3. MISSING SERVICE LAYER EXTRACTION

### 3.1 No `ObraService` for Core Operations
While `services/obra_service.py` exists, the routes in `main.py` still do all the work:
- `nova_obra()` (main.py:174-226): Creates Obra directly in route
- `editar_obra()` (main.py:231-259): Updates Obra directly in route
- `upload_imagem_obra()` (main.py:264-328): File handling in route
- `excluir_obra()` (main.py:361-367): Delete directly in route

Similarly for `Lancamento`, `Fornecedor`, `Contrato`, `Orcamento`.

**Suggested Services to Create/Expand:**
- `ObraService.create()`, `ObraService.update()`, `ObraService.delete()`, `ObraService.upload_image()`
- `LancamentoService.create()`, `LancamentoService.update()`, `LancamentoService.delete()`
- `FornecedorService.create()`, `FornecedorService.update()`, `FornecedorService.deactivate()`
- `ContratoService.create()`, `ContratoService.add_parcela()`, `ContratoService.pagar_parcela()`
- `OrcamentoService.create()`, `OrcamentoService.duplicate()`, `OrcamentoService.add_item()`

---

### 3.2 No `FileUploadService`
Image upload logic in `main.py:upload_imagem_obra()` (lines 264-328) and `remover_imagem_obra()` (lines 333-356) should be extracted:

```python
class FileUploadService:
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    @staticmethod
    def save_file(file, directory, prefix=''):
        # Validate extension
        # Generate unique filename
        # Save and return path
        pass

    @staticmethod
    def delete_file(file_path):
        # Delete physical file
        pass
```

---

### 3.3 No `MultiTenantService`
The empresa ownership check pattern should be centralized:

```python
class MultiTenantService:
    @staticmethod
    def get_obra_or_404(obra_id, empresa_id):
        return Obra.query.filter_by(id=obra_id, empresa_id=empresa_id).first_or_404()

    @staticmethod
    def get_lancamento_or_404(lancamento_id, empresa_id):
        return Lancamento.query.filter_by(id=lancamento_id, empresa_id=empresa_id).first_or_404()
    # etc.
```

---

## 4. PERFORMANCE IMPROVEMENTS

### 4.1 N+1 Query Problems (CRITICAL)

**Location:** `routes/excel.py:134-155` (`exportar_obras_excel`)
```python
for obra in obras:
    total_gasto = sum(l.valor for l in obra.lancamentos if l.tipo == 'Despesa')  # N+1!
    total_receita = sum(l.valor for l in obra.lancamentos if l.tipo == 'Receita')  # N+1!
```

**Location:** `routes/excel.py:198-217` (`exportar_relatorio_financeiro_excel`)
Same pattern - iterates obras and queries lancamentos for each.

**Location:** `services/relatorio_service.py:49-83` (`calcular_lucro_por_obra`)
Iterates obras, then for each obra queries lancamentos separately.

**Location:** `services/relatorio_service.py:86-113` (`calcular_evolucao_mensal`)
Executes 12 separate queries (one per month).

**Fix:** Use JOINs and GROUP BY:
```python
# For obras with totals in a single query:
result = db.session.query(
    Obra,
    func.sum(case((Lancamento.tipo == 'Despesa', Lancamento.valor), else_=0)).label('despesas'),
    func.sum(case((Lancamento.tipo == 'Receita', Lancamento.valor), else_=0)).label('receitas'),
).outerjoin(Lancamento).filter(Obra.empresa_id == empresa_id).group_by(Obra.id).all()
```

---

### 4.2 Redundant `Obra.query` Calls (MEDIUM)

In `routes/main.py`, `Obra.query.filter_by(empresa_id=empresa_id).all()` is called in:
- `lancamentos()` (line 410)
- `novo_lancamento()` (line 473)
- `editar_lancamento()` (line 500)
- `api_dashboard()` (line 520)
- `relatorios()` (line 700)
- `exportar_relatorio_pdf()` (line 782)

These should be cached or consolidated where possible.

---

### 4.3 `categorias_count` Inefficient Query (LOW)
**Location:** `services/relatorio_service.py:227-237`
```python
categorias_count = (
    len(
        set(
            Lancamento.query.filter_by(empresa_id=empresa_id)
            .with_entities(Lancamento.categoria)
            .all()
        )
    )
    if lancamentos_count > 0
    else 0
)
```

This fetches ALL categories into Python, then uses `set()` to count distinct values.

**Fix:**
```python
categorias_count = (
    db.session.query(Lancamento.categoria)
    .filter_by(empresa_id=empresa_id)
    .distinct()
    .count()
)
```

---

### 4.4 Loading All Lancamentos in `relatorios` (MEDIUM)
**Location:** `services/relatorio_service.py:29`
```python
lancamentos = query.all()  # Could be thousands of rows
total_receitas = sum(l.valor for l in lancamentos if l.tipo == 'Receita')
```

Should use SQL aggregation instead.

---

## 5. CODE SMELLS

### 5.1 Imports Inside Functions (MEDIUM)

**Locations:**
- `routes/main.py:50` - `from sqlalchemy import case, func` inside `dashboard()`
- `routes/main.py:109` - `from app.utils.paginacao import Paginacao` inside `obras()`
- `routes/main.py:219` - `import traceback` inside exception handler
- `routes/main.py:279` - `import os` and `from werkzeug.utils import secure_filename` inside `upload_imagem_obra()`
- `routes/main.py:340` - `import os` inside `remover_imagem_obra()`
- `routes/main.py:407` - `from app.utils.paginacao import Paginacao` inside `lancamentos()`
- `routes/main.py:596` - `from app.utils.pdf_export import exportar_obra_pdf` inside `exportar_obra_pdf()`
- `routes/main.py:625` - `from datetime import datetime` inside `exportar_obra()`
- `routes/main.py:757` - `from datetime import datetime` and `from app.utils.pdf_export import exportar_relatorio_pdf` inside `exportar_relatorio_pdf()`
- `routes/main.py:801` - `from flask import render_template` inside `ver_logs()` (already imported at top!)
- `routes/orcamentos.py:30-31` - `from flask import request` and `from app.models import LogAtividade` inside `log_atividade()`
- `routes/orcamentos.py:60` - `from app.utils.paginacao import Paginacao` inside `orcamentos()`
- `routes/orcamentos.py:141` - `import json` inside `novo_orcamento()`
- `routes/orcamentos.py:165` - `import traceback` inside exception handler
- `routes/orcamentos.py:316` - `from app.models.contratos import Contrato` inside `gerar_contrato()`
- `routes/api.py:58` - `from app.utils.financeiro import calcular_totais_obra` inside `api_obra_detalhe()`
- `routes/api.py:118` - `from app.utils.paginacao import Paginacao` inside `api_obras()`
- `routes/api.py:180-184` - `from datetime import datetime` inside `api_lancamentos()` (imported twice!)
- `routes/api.py:240-241` - `from app.utils.dates import parse_date` and `from app.utils.sanitize import sanitize_float, sanitize_string` inside `api_lancamento_criar()`
- `routes/api.py:287` - `from app.utils.financeiro import calcular_totais_empresa` inside `api_financeiro_resumo()`
- `routes/api.py:292` - `from app.utils.financeiro import get_obras_por_status` inside `api_financeiro_resumo()`
- `routes/api.py:349-351` - Multiple imports inside `api_obra_criar()`
- `routes/api.py:384-386` - Multiple imports inside `api_obra_editar()`
- `routes/api.py:422` - `from app.models import Obra` inside `api_obra_excluir()`
- `routes/api.py:463-464` - Multiple imports inside `api_lancamento_editar()`
- `routes/api.py:513` - `from app.utils.financeiro import get_obras_por_status` inside `api_relatorio_obras()`
- `routes/api.py:556` - `from app.utils.financeiro import calcular_despesas_por_categoria` inside `api_relatorio_categorias()`
- `routes/api.py:582` - `import os` inside `list_backups()`
- `routes/contratos.py:30` - `from app.utils.paginacao import Paginacao` inside `contratos()`
- `routes/contratos.py:201` - `from sqlalchemy.exc import IntegrityError` inside `nova_parcela()`
- `routes/contratos.py:237` - `import time` inside exception handler
- `routes/fornecedores.py:37` - `from app.utils.paginacao import Paginacao` inside `fornecedores()`
- `routes/fornecedores.py:123` - `from app.utils.paginacao import Paginacao` inside `fornecedor_detalhe()`
- `routes/fornecedores.py:244` - `import traceback` inside exception handler
- `routes/banco.py:24` - `from app.utils.paginacao import Paginacao` inside `bancos()`
- `routes/banco.py:74` - `from app.utils.paginacao import Paginacao` inside `banco_detalhe()`
- `routes/banco.py:85` - `from sqlalchemy import case, func` inside `banco_detalhe()`
- `routes/banco.py:215` - `from app.models.banco import LancamentoConta` inside `transferencia()`
- `routes/banco.py:252` - `from flask import jsonify` inside `api_bancos()` (already imported at top!)
- `routes/banco.py:263-264` - `from datetime import datetime` and `from flask import jsonify` inside `api_extrato()`
- `routes/extrato.py:92` - `from app.utils.extrato import processar_cnab, processar_csv, processar_ofx` inside `importar_extrato()`
- `routes/extrato.py:122-124` - `import csv` and `from flask import make_response` inside `modelo_csv()`
- `routes/auth.py:36` - `from functools import wraps` inside `login_required()`
- `routes/auth.py:87` - `from app.routes.notificacoes import gerar_alertas` inside `login()`
- `routes/auth.py:156-157` - `import secrets` and `from datetime import datetime` inside `recuperar_senha()`
- `routes/auth.py:303` - `from app.routes.notificacoes import gerar_alertas` inside `verificar_2fa()`
- `routes/auth.py:349-350` - `import base64`, `import io`, `import qrcode` inside `configurar_2fa()`

**Issues:**
- Redundant imports (flask.render_template in main.py:801, flask.jsonify in banco.py:252)
- `datetime` imported at module level AND inside functions
- Should be at top of file for consistency and PEP 8 compliance

**Exceptions:** Lazy imports for optional dependencies or to avoid circular imports are acceptable.

---

### 5.2 Bare `except:` Clause (HIGH)
**Location:** `routes/orcamentos.py:46-47`
```python
def log_atividade(...):
    try:
        ...
    except:
        pass  # Silent failure - audit logs are lost!
```

**Fix:** At minimum, log the error:
```python
except Exception as e:
    current_app.logger.error(f'Erro ao registrar log de atividade: {e}')
```

---

### 5.3 `import io` at Bottom of File (HIGH)
**Location:** `routes/extrato.py:141`

The `import io` statement is at the **bottom of the file** after all functions, because it's needed by `modelo_csv()` at line 126. This is a code smell - imports should be at the top.

**Fix:** Move `import io` to the top of the file.

---

### 5.4 Unused `from flask import render_template` Re-import
**Location:** `routes/main.py:801`

```python
def ver_logs():
    from flask import render_template  # Already imported at line 14!
```

---

### 5.5 Duplicate `from flask import jsonify` Import
**Location:** `routes/banco.py:252-253`

```python
def api_bancos():
    from flask import jsonify  # Already imported at top of file? Actually NOT - but inconsistent
```

Actually, checking the file: `jsonify` is NOT imported at the top of `banco.py`, so it's needed. But the pattern is inconsistent across files.

---

### 5.6 `datetime` Imported Twice in Same Function
**Location:** `routes/api.py:180-184`
```python
if data_inicio:
    from datetime import datetime
    query = query.filter(...)
if data_fim:
    from datetime import datetime  # Duplicate import!
    query = query.filter(...)
```

---

### 5.7 Dead Code / Custom `login_required` vs Flask-Login
**Location:** `routes/auth.py:34-44`

The project uses Flask-Login (configured in `__init__.py:111-119`) but also defines a custom `login_required` decorator. Flask-Login provides `from flask_login import login_required`.

**Issue:** The custom decorator doesn't integrate with Flask-Login's `current_user`, `login_user`, etc.

**Recommendation:** Standardize on Flask-Login's `login_required` and remove the custom one, OR document why the custom one is needed.

---

### 5.8 `log_atividade` Function Duplicates `AuditService`
**Location:** `routes/orcamentos.py:27-47`

This function manually creates `LogAtividade` records, but `AuditService` already exists and is used in other routes (`main.py:214`, `contratos.py:101`).

**Fix:** Replace `log_atividade()` with `AuditService.log()` calls.

---

### 5.9 Mixed Query Styles
Some routes use `query.all()` then Python filtering; others use SQL filtering:
```python
# Bad (Python filtering):
lancamentos = Lancamento.query.filter_by(empresa_id=empresa_id).all()
despesas = sum(l.valor for l in lancamentos if l.tipo == 'Despesa')

# Good (SQL filtering):
result = db.session.query(func.sum(...)).filter(...).first()
```

---

### 5.10 No Input Validation on `sanitize_int` for `parcelas`
**Location:** `routes/main.py:458`
```python
parcelas=sanitize_int(request.form.get('parcelas'), min_val=1),
```

If `request.form.get('parcelas')` is None, `sanitize_int` returns `0` (default), which violates `min_val=1`. The `sanitize_int` function should return `min_val` when input is None/invalid, but currently it returns `default=0`.

---

### 5.11 Hardcoded Values
- `routes/main.py:78` - `despesas_mes * 0.8` and `receitas_mes * 0.9` - magic numbers for mock chart data
- `routes/ia.py:38` - `len(mensagem) > 500` - should be a config constant
- `routes/ia.py:48` - `modelos_openai = ['gpt-3.5-turbo', ...]` - should be a config constant
- `routes/extrato.py:84` - `10 * 1024 * 1024` - should be a config constant
- `routes/api.py:188` - `.limit(100)` - should be configurable

---

### 5.12 Debug Routes Exposed in Production (SECURITY)
**Location:** `app/__init__.py:231-566`

Routes like `/debug/db`, `/debug/user/<email>`, `/debug/config`, `/test-login`, `/setup-demo`, `/setup-dados-teste`, `/setup-demo-completo` are always registered regardless of environment.

While they don't have explicit auth checks, some expose sensitive data (user emails, password hash prefixes, database configuration).

**Recommendation:**
- Only register debug routes when `FLASK_ENV != 'production'`
- Add authentication/authorization checks

---

## 6. ARCHITECTURE RECOMMENDATIONS

### 6.1 Consolidate `utils/financeiro.py` with `services/relatorio_service.py`
Both contain overlapping financial calculation logic. Consider merging or having the service use the utils.

### 6.2 Standardize Import Order
Apply isort/flake8-import-order across all files for consistency.

### 6.3 Add Type Hints
None of the route handlers or service methods have type hints. Adding them would improve IDE support and catch bugs.

### 6.4 Consider Repository Pattern
Instead of direct `Model.query` calls in routes, use repository classes:
```python
class ObraRepository:
    def __init__(self, db_session):
        self.db = db_session

    def get_by_id_and_empresa(self, obra_id, empresa_id):
        return Obra.query.filter_by(id=obra_id, empresa_id=empresa_id).first_or_404()

    def get_all_by_empresa(self, empresa_id):
        return Obra.query.filter_by(empresa_id=empresa_id).all()
```

---

## PRIORITY MATRIX

| Priority | Category | Impact | Effort | Quick Win? |
|----------|----------|--------|--------|------------|
| P0 | N+1 Queries in Excel exports | High | Medium | No |
| P0 | SQL aggregation vs Python sum | High | Low | **Yes** |
| P1 | Centralize `get_owned_or_404` helper | Medium | Low | **Yes** |
| P1 | Standardize `parse_date` usage | Medium | Low | **Yes** |
| P1 | Bare except clause in orcamentos | High | Low | **Yes** |
| P1 | Debug routes in production | High | Low | **Yes** |
| P2 | Move debug routes to separate blueprint | Medium | Medium | No |
| P2 | Extract FileUploadService | Medium | Medium | No |
| P2 | Remove custom login_required | Medium | Medium | No |
| P2 | Move import io to top of file | Low | Low | **Yes** |
| P2 | Replace log_atividade with AuditService | Low | Low | **Yes** |
| P3 | Strategy pattern for IA providers | Low | High | No |
| P3 | Add type hints | Low | High | No |
| P3 | Repository pattern | Medium | High | No |
| P3 | QueryBuilder for pagination | Low | Medium | No |

---

## FILES SUMMARY

| File | Lines | Issues Found | Priority |
|------|-------|-------------|----------|
| `routes/main.py` | 837 | 15+ | P0-P2 |
| `routes/api.py` | 596 | 12+ | P1-P2 |
| `routes/excel.py` | 569 | 8+ | P0-P1 |
| `routes/orcamentos.py` | 400 | 7+ | P1-P2 |
| `routes/contratos.py` | 281 | 5+ | P1-P2 |
| `routes/fornecedores.py` | 292 | 4+ | P2 |
| `routes/banco.py` | 290 | 6+ | P2 |
| `routes/ia.py` | 191 | 3+ | P2-P3 |
| `routes/auth.py` | 411 | 4+ | P1-P2 |
| `routes/rbac.py` | 255 | 3+ | P2 |
| `routes/extrato.py` | 142 | 3+ | P1-P2 |
| `__init__.py` | 588 | 5+ | P1-P2 |
| `services/relatorio_service.py` | 260 | 5+ | P0-P1 |
| `utils/financeiro.py` | 127 | 2+ | P2 |

**Total estimated issues: ~85+**
