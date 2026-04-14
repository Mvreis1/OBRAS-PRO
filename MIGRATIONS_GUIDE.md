# Guia de Migrations - OBRAS PRO

## O que é Flask-Migrate?

Flask-Migrate usa **Alembic** para gerenciar mudanças no banco de dados de forma versionada e segura. 
Em vez de usar `db.create_all()` (que não atualiza tabelas existentes), você cria **migrations** que são scripts de alteração do schema.

## Configuração Inicial (FAZER APENAS UMA VEZ)

### Opção 1: Usando o script helper (RECOMENDADO)

```bash
# 1. Inicializar migrations
python db_manager.py init

# 2. Gerar primeira migration (detecta modelos automaticamente)
python db_manager.py migrate "initial migration"

# 3. Aplicar migration no banco
python db_manager.py upgrade
```

### Opção 2: Usando Flask CLI diretamente

```bash
# Definir variável de ambiente para o app
set FLASK_APP=run.py

# 1. Inicializar
flask db init

# 2. Gerar migration
flask db migrate -m "initial migration"

# 3. Aplicar
flask db upgrade
```

## Uso Diárioario

### Quando alterar um modelo (adicionar/remover colunas, novas tabelas)

```bash
# 1. Fazer alteração no modelo (ex: app/models/modelos.py)
#    Exemplo: adicionar campo 'foto' em Usuario

# 2. Gerar migration automaticamente
python db_manager.py migrate "adicionar campo foto em usuario"

# 3. Verificar o arquivo gerado em migrations/versions/xxx_adicionar_foto.py
#    (Opcional: revisar para garantir que está correto)

# 4. Aplicar no banco de desenvolvimento
python db_manager.py upgrade

# 5. Commit do código + pasta migrations no git
git add migrations/
git commit -m "Adicionar campo foto em usuario"
```

### Comandos Úteis

```bash
# Ver histórico de migrations
python db_manager.py history

# Ver versão atual do banco
python db_manager.py current

# Reverter última migration (CUIDADO: pode perder dados)
python db_manager.py downgrade

# Reverter para uma versão específica
python db_manager.py downgrade <revision_id>

# Aplicar todas migrations pendentes
python db_manager.py upgrade

# Aplicar até uma versão específica
python db_manager.py upgrade <revision_id>
```

## Workflow de Produção

### Deploy em Produção

```bash
# 1. Pull do código no servidor de produção
git pull

# 2. Instalar dependências (se houver novas)
pip install -r requirements.txt

# 3. Aplicar migrations pendentes
python db_manager.py upgrade

# 4. Reiniciar aplicação
#    (Gunicorn, etc.)
```

### Por que isso é importante?

- ✅ **Zero downtime**: Aplica mudanças sem derrubar o app
- ✅ **Rollback seguro**: Pode reverter se algo der errado
- ✅ **Versionado**: Cada mudança está no git
- ✅ **Multi-ambiente**: Mesmo schema em dev/staging/prod

## Estrutura da Pasta `migrations/`

```
migrations/
├── versions/          # Arquivos de migration (scripts SQL)
│   ├── 001_initial.py
│   ├── 002_add_foto_usuario.py
│   └── ...
├── alembic.ini        # Configuração do Alembic
├── env.py             # Ambiente de execução
└── script.py.mako     # Template para novas migrations
```

## Problemas Comuns

### "Target database is not up to date"
Significa que há migrations pendentes. Execute:
```bash
python db_manager.py upgrade
```

### Migration gerada está vazia
- Certifique-se de que importou todos os modelos no `app/models/__init__.py`
- O Alembic detecta mudanças comparando o estado atual do banco com os modelos

### Erro ao aplicar migration
1. Verifique o arquivo em `migrations/versions/`
2. Corrija o script se necessário
3. Execute `python db_manager.py stamp <revision>` para marcar a versão
4. Tente `python db_manager.py upgrade` novamente

## Boas Práticas

1. ✅ **Sempre revisar** migrations geradas antes de aplicar
2. ✅ **Commit migrations** junto com as mudanças nos modelos
3. ✅ **Testar em dev** antes de aplicar em produção
4. ✅ **Backup do banco** antes de migrations em produção
5. ✅ **Mensagem descritiva** ao gerar migrations
6. ❌ **NUNCA editar** migrations já aplicadas
7. ❌ **NUNCA deletar** migrations do histórico

## Exemplo Prático

### Cenário: Adicionar tabela de Fornecedores

1. Crio o modelo em `app/models/fornecedores.py`:
```python
class Fornecedor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cnpj = db.Column(db.String(14))
    # ...
```

2. Exporto no `app/models/__init__.py`:
```python
from app.models.fornecedores import Fornecedor
__all__ = [..., 'Fornecedor']
```

3. Gero a migration:
```bash
python db_manager.py migrate "adicionar tabela fornecedor"
```

4. Aplicação:
```bash
python db_manager.py upgrade
```

---

**Para dúvidas**: Consulte a documentação oficial do Alembic: https://alembic.sqlalchemy.org/
