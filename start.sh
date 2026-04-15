#!/bin/bash
# Start script para OBRAS PRO no Render

echo "=========================================="
echo "Iniciando OBRAS PRO"
echo "=========================================="

# Verificar variaveis de ambiente obrigatorias
if [ -z "$PORT" ]; then
    echo "AVISO: PORT nao definida, usando 5000"
    export PORT=5000
fi

if [ -z "$SECRET_KEY" ]; then
    echo "ERRO: SECRET_KEY deve ser definida!"
    exit 1
fi

echo "-> PORT: $PORT"
echo "-> FLASK_ENV: ${FLASK_ENV:-production}"
echo "-> DATABASE_URL: ${DATABASE_URL:+configurado}"

# Iniciar Gunicorn com configurações otimizadas para Render
echo "-> Iniciando servidor..."
exec gunicorn run:app \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --threads 4 \
    --timeout 120 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    --enable-stdio-inheritance
