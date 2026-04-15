# Guia de Deploy no Render - OBRAS PRO

## Resumo das Correções Aplicadas

### 1. Código-Fonte

#### ✅ Problemas Corrigidos:
- **Imports quebrados**: Adicionado tratamento de exceção para `pyotp` em `app/routes/auth.py`
- **Variável PORT**: Todos os arquivos de configuração agora usam `$PORT` do ambiente
- **Health Check**: Registro do blueprint de monitoramento habilitado em produção

#### Arquivos Modificados:
- `app/__init__.py` - Monitoramento sempre registrado (necessário para health check)
- `app/routes/auth.py` - Import de pyotp com fallback seguro

### 2. Configuração

#### ✅ requirements.txt
Adicionada dependência faltante:
```
bcrypt==4.1.2
```

#### ✅ Procfile
```
web: gunicorn run:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120 --keep-alive 5 --max-requests 1000 --access-logfile - --error-logfile -
release: flask db upgrade
```

#### ✅ render.yaml
- Build command atualizado para executar migrations
- Start command otimizado com workers/threads balanceados
- Variáveis de ambiente adicionadas (RATELIMIT_STORAGE_URL, CACHE_TYPE)

#### ✅ Dockerfile
- CMD atualizado para usar `$PORT` do ambiente
- Health check apontando para `/healthz` (rota sem autenticação)

### 3. Banco de Dados

#### ✅ Migrations Automáticas
- `Procfile` com release phase: `flask db upgrade`
- `build.sh` executa migrations durante o build
- `render.yaml` com build command incluindo migrations

#### ✅ DATABASE_URL
- Já configurado corretamente em `app/__init__.py` com conversão de `postgres://` para `postgresql://`
- Configuração de pool de conexões otimizada para PostgreSQL

### 4. Segurança

#### ✅ SECRET_KEY
- Configurada via variável de ambiente no `render.yaml` com `generateValue: true`
- Validação em `app/config.py` exige SECRET_KEY em produção

#### ✅ Bibliotecas de Criptografia
- `pyotp==2.9.0` - Já presente para 2FA
- `bcrypt==4.1.2` - Adicionado ao requirements.txt
- `werkzeug` - Usado para hash de senhas

### 5. Compatibilidade com Render

#### ✅ Scripts de Deploy
- `build.sh` - Script de build executado durante o deploy
- `start.sh` - Script de inicialização com configurações otimizadas

#### ✅ Configurações Gunicorn Otimizadas:
```bash
--workers 2          # Balanceamento entre memória e performance
--threads 4          # Melhor para I/O bound (banco de dados)
--timeout 120        # Evita timeout em operações lentas
--keep-alive 5       # Conexões persistentes
--max-requests 1000  # Reciclagem de workers
```

#### ✅ Health Check
- Rota `/healthz` disponível sem autenticação
- Verifica conexão com banco de dados
- Usado pelo Render para verificar saúde da aplicação

## Instruções de Deploy

### 1. Criar conta no Render
- Acesse https://render.com
- Conecte sua conta GitHub

### 2. Criar Blueprint
- No dashboard, clique em "Blueprints"
- Selecione o repositório OBRAS_FINANCEIRO
- O Render detectará automaticamente o `render.yaml`

### 3. Configurar Variáveis de Ambiente (Opcional)
Se precisar adicionar variáveis extras:
```
OPENAI_API_KEY=sk-...
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
```

### 4. Deploy
- O deploy será automático ao fazer push para a branch main
- Acompanhe os logs no dashboard do Render

## URLs Úteis Após Deploy

- **Aplicação**: `https://obras-financeiro.onrender.com`
- **Health Check**: `https://obras-financeiro.onrender.com/healthz`
- **Setup Demo**: `https://obras-financeiro.onrender.com/setup-demo`
- **Test DB**: `https://obras-financeiro.onrender.com/test-db`

## Troubleshooting

### Erro 502 Bad Gateway
- Verificar logs no dashboard do Render
- Confirmar que `$PORT` está sendo usado corretamente
- Health check deve retornar 200 em `/healthz`

### Erro de Migrations
- Verificar se `flask db upgrade` foi executado
- Conferir se a tabela `alembic_version` existe no banco

### Timeout em Rotas
- Aumentar `--timeout` no gunicorn (já configurado para 120s)
- Otimizar queries no código

## Checklist Pré-Deploy

- [ ] Repositório está no GitHub
- [ ] Arquivo `render.yaml` está na raiz
- [ ] `requirements.txt` está completo
- [ ] Migrations estão commitadas
- [ ] `SECRET_KEY` será gerada automaticamente
- [ ] `DATABASE_URL` será configurada automaticamente

## Monitoramento

Após o deploy, monitore:
1. Logs do Render (stdout/stderr)
2. Health check status
3. Métricas de performance
4. Erros de banco de dados

---

**Data da Análise**: 2026-04-14
**Versão**: 1.0.0
