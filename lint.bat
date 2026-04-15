@echo off
REM Script para executar o linter Ruff
REM Uso: lint.bat [opcoes]
REM Exemplos:
REM   lint.bat              - Verifica erros
REM   lint.bat --fix        - Corrige erros automaticos
REM   lint.bat --statistics - Mostra resumo

cd /d "%~dp0"

if "%1"=="" (
    echo Executando verificacao de lint...
    venv\Scripts\ruff.exe check app/ --statistics
) else (
    echo Executando Ruff com opcoes: %*
    venv\Scripts\ruff.exe check app/ %*
)

echo.
echo Para mais informacoes: relatorio_linter_resumo.txt
pause
