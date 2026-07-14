@echo off
REM ============================================
REM GlassFish Monitor - Script Admin (chamado pelo UAC)
REM ============================================

cd /d "%~dp0"

echo ===================================
echo    GlassFish Monitor v1.0.0
echo ===================================
echo [OK] Executando como Administrador
echo.

REM Verificar se o Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python não encontrado. Instale Python 3.10+
    pause
    exit /b 1
)

REM Criar/ativar ambiente virtual e instalar dependências
if not exist ".venv" (
    echo [INFO] Criando ambiente virtual...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

if not exist ".venv\.deps_installed" (
    echo [INFO] Instalando dependências...
    pip install -e . >nul 2>&1
    echo. > ".venv\.deps_installed"
)

echo [INFO] Iniciando GlassFish Monitor...
echo.

REM Executar a aplicação
python -m glassfish_monitor

echo.
pause
