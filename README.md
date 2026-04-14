# OBRAS PRO 🏗️

Sistema completo de gestao financeira para construtoras e empresas de engenharia com automação IA.

## ✨ Funcionalidades

- **Dashboard Inteligente** - Visao geral de receitas, despesas e alertas em tempo real
- **Gestao de Obras** - Controle orcamentario, progresso e status de multiplas obras
- **Lancamentos Financeiros** - Registro de receitas e despesas com parcelamento automatico
- **Contratos** - Gestao completa com parcelas e controle de vencimentos
- **Orcamentos** - Criacao de orcamentos profissionais para clientes
- **Fornecedores** - Cadastro e historico de compras por fornecedor
- **Gestao Bancaria** - Contas bancarias, lancamentos e importacao de extratos (OFX, CSV, CNAB)
- **Assistente IA** - Consultas inteligentes com IA sobre dados financeiros
- **Exportacao Excel** - Relatorios profissionais em formato .xlsx real
- **2FA** - Autenticacao em dois fatores para seguranca adicional
- **RBAC** - Controle granular de permissoes por perfil de usuario
- **Multi-tenant** - Isolamento completo de dados por empresa

## 🚀 Inicio Rapido

### Pre-requisitos

- Python 3.11+
- pip

### Instalacao

```bash
# Clone o repositorio
git clone https://github.com/seu-usuario/obras-pro.git
cd obras-pro

# Crie o ambiente virtual
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Instale as dependencias
pip install -r requirements.txt

# Copie o arquivo de ambiente
cp .env.example .env  # Linux/Mac
# copy .env.example .env  # Windows

# Configure as variaveis no .env (SECRET_KEY e obrigatorio)
```

### Executando

```bash
python run.py
```

Acesse: ** **

### Primeiros Passos

1. Acesse a pagina de login
2. Clique em **"Criar nova conta"**
3. Preencha os dados da sua empresa
4. Use a senha minima: 8 caracteres + 1 letra + 1 numero
5. Apos o cadastro, voce entra como **Administrador** com acesso total

## 📁 Estrutura do Projeto

```
OBRAS_FINANCEIRO/
├── app/
│   ├── __init__.py          # Factory pattern + configuracoes
│   ├── config.py            # Configuracoes centralizadas
│   ├── models/              # Modelos SQLAlchemy
│   │   ├── models.py        # Empresa, Usuario, Obra, Lancamento, etc.
│   │   ├── banco.py         # Contas bancarias
│   │   ├── contratos.py     # Contratos e parcelas
│   │   ├── orcamentos.py    # Orcamentos e itens
│   │   ├── fornecedores.py  # Fornecedores e compras
│   │   ├── notificacoes.py  # Notificacoes e config email
│   │   └── acesso.py        # RBAC: Permissao, Role, PermissaoUsuario
│   ├── routes/              # Blueprints Flask
│   │   ├── auth.py          # Login, cadastro, 2FA
│   │   ├── main.py          # Dashboard, obras, lancamentos
│   │   ├── banco.py         # Gestao bancaria
│   │   ├── contratos.py     # CRUD contratos
│   │   ├── orcamentos.py    # CRUD orcamentos
│   │   ├── fornecedores.py  # CRUD fornecedores
│   │   ├── excel.py         # Exportacao Excel
│   │   ├── rbac.py          # Rotas de gestao de acesso
│   │   └── ...
│   ├── utils/               # Utilitarios
│   │   ├── paginacao.py     # Classe de paginacao
│   │   ├── rbac.py          # Decoradores de permissao
│   │   ├── two_factor.py    # Helper 2FA
│   │   └── excel_export.py  # Gerador de Excel profissional
│   └── templates/           # Templates Jinja2
├── migrations/              # Migrations Alembic
├── tests/                   # Testes pytest
├── requirements.txt         # Dependencias Python
├── run.py                   # Ponto de entrada
├── Procfile                 # Configuracao de deploy
└── .env.example             # Exemplo de variaveis de ambiente
```

## 🗄️ Banco de Dados

### Migrations

```bash
# Criar nova migration (apos alterar modelos)
flask db migrate -m "descricao da mudanca"

# Aplicar migrations pendentes
flask db upgrade

# Reverter ultima migration
flask db downgrade
```

### Seed de Dados

O sistema ja cria as tabelas automaticamente na primeira execucao. Para dados de demonstracao:

```bash
python criar_dados.py
```

## 🧪 Testes

```bash
# Executar todos os testes
pytest tests/ -v

# Com coverage
pytest tests/ --cov=app --cov-report=html

# Testes especificos
pytest tests/test_auth.py -v
```

## 🔐 Seguranca

- **CSRF Protection** em todos os formularios
- **Autenticacao 2FA** com TOTP (Google Authenticator, Authy)
- **RBAC** com 5 perfis pre-configurados: Administrador, Engenheiro, Financeiro, Almoxarifado, Visitante
- **Permissoes individuais** por usuario (allow/deny)
- **Senhas** com hash bcrypt via Werkzeug
- **Sessao** com regeneracao anti session fixation

## 📊 Exportacoes

| Formato       | Rota                                     |
|---------------|------------------------------------------|
| Excel (.xlsx) | Lancamentos, Obras, Relatorio Financeiro |
| PDF           | Obra individual, Relatorio completo      |
| CSV           | Lancamentos, Obras                       |

## 🌐 Deploy

### Producao com Gunicorn

```bash
# Instale dependencias de producao
pip install -r requirements.txt

# Configure DATABASE_URL para PostgreSQL no .env
# Configure SECRET_KEY forte

# Rode com gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 4 run:app
```

### Railway / Render / Fly.io

O projeto inclui `Procfile` e suporte a variaveis de ambiente. Basta conectar o repositorio e configurar:

```
DATABASE_URL=postgresql://...
SECRET_KEY=sua-chave-secreta
```

## 📝 Licenca

MIT License

## 👤 Autor MARCELO REIS

Desenvolvido com ❤️ para construtoras que precisam de controle financeiro profissional.

---

**Dúvidas?** Abra uma [issue](https://github.com/seu-usuario/obras-pro/issues) ou entre em contato. E-MAIL - MARCELOG1946@HOTMAIL.COM
