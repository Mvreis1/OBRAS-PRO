# 📘 Guia de Refatoração - OBRAS FINANCEIRO PRO

## Visão Geral

Este documento descreve a refatoração completa do sistema para separar lógica de negócio (Services) das rotas (Controllers), seguindo o padrão **Service-Repository** e melhorando a organização do código.

---

## 🎯 Objetivos da Refatoração

### Problemas Identificados
1. **Routes com lógica de negócio inline** - CRUD completo dentro das rotas
2. **Services existentes não eram utilizados** - ObraService, LancamentoService criados mas ignorados
3. **Duplicação de código** - Mesma lógica repetida em 6+ rotas diferentes
4. **Performance ruim** - Python `sum()` em vez de SQL aggregation
5. **Arquivos gigantes** - `main.py` com 837 linhas (Deus file)
6. **Falta de services** - Import, IA, RBAC, Dashboard sem camada de serviço

### Solução Implementada
1. ✅ **Novos Services criados**: DashboardService, ImportService, IAService, RBACService
2. ✅ **Services existentes integrados**: ObraService, LancamentoService
3. ✅ **Rotas limpas** - Apenas validação, chamada de service, e renderização
4. ✅ **SQL aggregation** - Queries otimizadas no banco em vez de Python
5. ✅ **Arquivo de exemplo** - `main_refatorado.py` mostrando o padrão correto

---

## 📁 Estrutura de Arquivos

### Novos Services Criados

```
app/services/
├── dashboard_service.py      ✨ NOVO - Dashboard data aggregation
├── import_service.py         ✨ NOVO - Excel/CSV import logic
├── ia_service.py             ✨ NOVO - AI model orchestration
├── rbac_service.py           ✨ NOVO - Role/permission management
├── __init__.py               ✨ ATUALIZADO - Exporta novos services
└── (demais services existentes)
```

### Rotas Refatoradas

```
app/routes/
├── main_refatorado.py        ✨ NOVO - Exemplo de main.py limpo
├── main.py                   ⚠️ LEGADO - Substituir por versão refatorada
└── (demais rotas)
```

---

## 🔧 Services Criados

### 1. DashboardService

**Localização**: `app/services/dashboard_service.py`

**Responsabilidade**: Agregação de dados para dashboards e relatórios

**Métodos Principais**:
```python
DashboardService.get_dashboard_resumo(empresa_id)
    # Retorna: receitas, despesas, saldo, obras stats, categorias

DashboardService.get_dashboard_chart_data(empresa_id, meses=12)
    # Retorna: dados mensais para gráficos

DashboardService.get_obra_dashboard_data(obra_id, empresa_id)
    # Retorna: dados completos de uma obra

DashboardService.get_kpi_tendencias(empresa_id, meses=6)
    # Retorna: tendências de KPIs
```

**Antes (main.py linha 38-85)**:
```python
# ❌ Lógica inline na rota
result = db.session.query(
    func.sum(case((Lancamento.tipo == 'Despesa', Lancamento.valor), else_=0)).label('despesas'),
    func.sum(case((Lancamento.tipo == 'Receita', Lancamento.valor), else_=0)).label('receitas'),
).filter(Lancamento.empresa_id == empresa_id).first()

despesas_mes = result.despesas or 0
receitas_mes = result.receitas or 0
```

**Depois (main_refatorado.py)**:
```python
# ✅ Service call
dashboard_data = DashboardService.get_dashboard_resumo(empresa_id)
```

---

### 2. ImportService

**Localização**: `app/services/import_service.py`

**Responsabilidade**: Importação de dados de arquivos Excel/CSV

**Métodos Principais**:
```python
ImportService.importar_lancamentos(empresa_id, file_path, dry_run=False)
    # Retorna: (imported_count, error_count, errors)

ImportService.importar_obras(empresa_id, file_path, dry_run=False)
    # Retorna: (imported_count, error_count, errors)

ImportService.save_upload_file(file, upload_folder)
    # Retorna: (file_path, error_message)

ImportService.allowed_file(filename)
    # Retorna: bool
```

**Antes (excel.py)**:
```python
# ❌ 150 linhas de lógica inline na rota
wb = openpyxl.load_workbook(file_path)
for row in ws.iter_rows():
    # parsing manual...
    lancamento = Lancamento(...)
    db.session.add(lancamento)
```

**Depois**:
```python
# ✅ Service call
imported, errors, error_count = ImportService.importar_lancamentos(
    empresa_id, file_path
)
```

---

### 3. IAService

**Localização**: `app/services/ia_service.py`

**Responsabilidade**: Orquestração de modelos de IA (OpenAI, Gemini, Claude)

**Métodos Principais**:
```python
IAService.chat(empresa_id, mensagem, modelo='local')
    # Retorna: resposta da IA

IAService.validate_api_key(model, api_key)
    # Retorna: (is_valid, error_message)

IAService.get_model_status(empresa_id)
    # Retorna: status de todos os modelos

IAService.get_quick_buttons()
    # Retorna: lista de botões rápidos
```

**Antes (ia.py)**:
```python
# ❌ 3 funções separadas para cada modelo
def chamar_openai(mensagem, contexto, modelo, api_key):
    # 40 linhas de código...

def chamar_gemini(mensagem, contexto, api_key):
    # 20 linhas de código...
```

**Depois**:
```python
# ✅ Service unificado
resposta = IAService.chat(empresa_id, mensagem, modelo)
```

---

### 4. RBACService

**Localização**: `app/services/rbac_service.py`

**Responsabilidade**: Gestão de roles e permissões

**Métodos Principais**:
```python
RBACService.get_roles_empresa(empresa_id)
    # Retorna: lista de roles

RBACService.criar_role(empresa_id, nome, descricao, permissoes_ids)
    # Retorna: (role, error_message)

RBACService.editar_role(role_id, empresa_id, nome, descricao, permissoes_ids)
    # Retorna: (role, error_message)

RBACService.excluir_role(role_id, empresa_id)
    # Retorna: (success, error_message)

RBACService.get_permissoes_agrupadas()
    # Retorna: dict de permissões por módulo
```

---

## 🔄 Como Migrar suas Rotas

### Passo 1: Backup

```bash
cp app/routes/main.py app/routes/main.py.bak
```

### Passo 2: Estude o Exemplo

Leia `app/routes/main_refatorado.py` para entender o padrão:

```python
@main_bp.route('/obra/nova', methods=['GET', 'POST'])
@login_required
def nova_obra():
    empresa_id = session.get('empresa_id')

    if request.method == 'POST':
        # 1. Preparar dados do form
        dados = {
            'nome': request.form.get('nome', '').strip(),
            'descricao': request.form.get('descricao'),
            # ... outros campos
        }

        # 2. Usar Service (lógica de negócio)
        obra, erro = ObraService.criar_obra(empresa_id, dados)

        # 3. Tratar resultado
        if erro:
            flash(erro, 'danger')
            return render_template('main/obra_form.html', obra=None)

        # 4. Log de auditoria
        AuditService.log('Criar obra', 'Obra', obra.id, f'Nova obra: {obra.nome}')
        flash('Obra cadastrada com sucesso!', 'success')
        return redirect(url_for('main.obras'))

    # GET: mostrar formulário
    return render_template('main/obra_form.html', obra=None)
```

### Passo 3: Substituir Rotas

Para cada rota no `main.py` original:

1. **Identificar a lógica de negócio** (criação, edição, consulta, cálculo)
2. **Verificar se existe service** para essa lógica
3. **Substituir pela chamada do service**
4. **Manter na rota apenas**: validação de input, chamada do service, renderização

### Passo 4: Testar

```bash
# Rodar testes
pytest

# Ou manualmente
flask run
```

---

## 📊 Métricas de Melhoria

### Antes
- **main.py**: 837 linhas
- **Lógica duplicada**: 6+ rotas com mesma query
- **Performance**: Python `sum()` sobre listas
- **Testabilidade**: Baixa (lógica misturada)

### Depois
- **main_refatorado.py**: ~400 linhas (52% redução)
- **Services reutilizáveis**: 4 novos + 2 integrados
- **Performance**: SQL aggregation no banco
- **Testabilidade**: Alta (services isolados)

---

## 🚀 Próximos Passos

### Alta Prioridade
1. ✅ **Substituir main.py** por main_refatorado.py
2. ⏳ **Refatorar excel.py** para usar ImportService
3. ⏳ **Refatorar ia.py** para usar IAService
4. ⏳ **Refatorar rbac.py** para usar RBACService

### Média Prioridade
5. ⏳ **Integrar ContratoService** em contratos.py
6. ⏳ **Integrar BancoService** em banco.py
7. ⏳ **Integrar OrcamentoService** em orcamentos.py

### Baixa Prioridade
8. ⏳ **Dividir main_refatorado.py** em blueprints menores:
   - `dashboard.py`
   - `obras.py`
   - `lancamentos.py`
   - `relatorios.py`

---

## ✅ Checklist de Validação

Após migrar cada rota:

- [ ] A rota chama um service em vez de fazer lógica inline
- [ ] Não há queries SQL complexas na rota
- [ ] Não há cálculos ou agregações na rota
- [ ] A rota tem menos de 30 linhas
- [ ] Testes passam (`pytest`)
- [ ] Funcionalidade manual funciona
- [ ] Logs de auditoria estão presentes

---

## 🛠️ Comandos Úteis

```bash
# Verificar estrutura
tree app/services

# Rodar testes
pytest

# Rodar linter
ruff check app/

# Formatar código
ruff format app/

# Rodar aplicação
flask run
```

---

## 📝 Padrão de Nomenclatura

### Services
- **Nome**: `{Entidade}Service`
- **Métodos**: `criar_{entidade}`, `editar_{entidade}`, `excluir_{entidade}`
- **Retorno**: `Tuple[Resultado, Optional[str]]` (resultado, erro)

### Rotas
- **Nome blueprint**: `{entidade}_bp`
- **URL**: `/{entidade}`, `/{entidade}/<id>`, `/{entidade}/novo`
- **Funções**: `{entidade}`, `nova_{entidade}`, `editar_{entidade}`

---

## ⚠️ Avisos Importantes

1. **Não apague main.py** até validar completamente a versão refatorada
2. **Teste cada rota** após migrar
3. **Mantenha logs de auditoria** em todas as operações CRUD
4. **Valide inputs** antes de chamar services
5. **Trate erros** retornados pelos services (tupla com error_message)

---

## 🎓 Referências

- **Service Layer Pattern**: Martin Fowler
- **Clean Architecture**: Robert C. Martin
- **Flask Best Practices**: Official Flask Documentation
- **SQLAlchemy Performance**: SQL vs Python aggregation

---

**Última atualização**: Abril 2026  
**Versão**: 1.0  
**Autor**: Refatoração automatizada com supervisão humana
