#!/bin/bash
# Build script para OBRAS PRO no Render

echo "=========================================="
echo "Iniciando build do OBRAS PRO"
echo "=========================================="

# Instalar dependencias
echo "-> Instalando dependencias..."
pip install -r requirements.txt

# Executar migrations
echo "-> Executando migrations..."
flask db upgrade

# Verificar se migrations foram aplicadas
if [ $? -eq 0 ]; then
    echo "-> Migrations aplicadas com sucesso!"
else
    echo "-> AVISO: Falha ao aplicar migrations. O banco pode já estar atualizado."
fi

echo "=========================================="
echo "Build concluido!"
echo "=========================================="
