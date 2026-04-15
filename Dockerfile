# ============================================
# Dockerfile para OBRAS FINANCEIRO PRO
# Multi-stage build para otimização
# ============================================

# ==========================================
# Stage 1: Builder - Instalação de dependências
# ==========================================
FROM python:3.11-slim AS builder

# Variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instalação de dependências do sistema necessárias para compilação
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar apenas requirements primeiro (para caching de camadas)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --prefix=/install -r requirements.txt

# Copiar código fonte para instalar dependências opcionais
COPY . .

# ==========================================
# Stage 2: Production - Imagem final otimizada
# ==========================================
FROM python:3.11-slim AS production

# Variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    PATH="/app/.local/bin:$PATH"

WORKDIR /app

# Instalação de dependências mínimas de runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* /var/tmp/*

# Copiar dependências Python do builder
COPY --from=builder /install /usr/local

# Copiar código da aplicação do builder
COPY --from=builder /app /app

# Criar diretórios necessários
RUN mkdir -p /app/logs /app/uploads /app/instance/backups && \
    chmod -R 755 /app/logs /app/uploads

# Usuário não-root para segurança
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Porta padrão
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/healthz || exit 1

# Executar aplicação com Gunicorn
CMD ["gunicorn", "-c", "gunicorn.conf.py", "--bind", "0.0.0.0:5000", "run:app"]
