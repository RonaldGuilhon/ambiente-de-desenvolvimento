@echo off
REM Script para executar o GlassFish Monitor

echo ===================================
echo    GlassFish Monitor v1.0.0
echo ===================================
echo.

REM Verificar se o Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python não encontrado. Instale Python 3.10+
    pause
    exit /b 1
)

REM Verificar se o ambiente virtual existe
if not exist ".venv" (
    echo [INFO] Criando ambiente virtual...
    python -m venv .venv
    call .venv\Scripts\activate
    echo [INFO] Instalando dependências...
    pip install -e .
) else (
    call .venv\Scripts\activate
)

echo [INFO] Iniciando GlassFish Monitor...
echo.

REM Executar a aplicação
python -m glassfish_monitor

if errorlevel 1 (
    echo.
    echo [ERRO] Aplicação encerrou com erro
    pause
)
