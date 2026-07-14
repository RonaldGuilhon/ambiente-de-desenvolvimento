# GlassFish Monitor - Script de Inicialização

Write-Host "===================================" -ForegroundColor Cyan
Write-Host "   GlassFish Monitor v1.0.0" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

# Verificar se o Python está instalado
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERRO] Python não encontrado. Instale Python 3.10+" -ForegroundColor Red
    Read-Host "Pressione Enter para sair"
    exit 1
}

# Verificar se o ambiente virtual existe
if (-not (Test-Path ".venv")) {
    Write-Host "[INFO] Criando ambiente virtual..." -ForegroundColor Yellow
    python -m venv .venv
    
    Write-Host "[INFO] Ativando ambiente virtual..." -ForegroundColor Yellow
    & ".venv\Scripts\Activate.ps1"
    
    Write-Host "[INFO] Instalando dependências..." -ForegroundColor Yellow
    pip install -e .
} else {
    Write-Host "[INFO] Ativando ambiente virtual..." -ForegroundColor Yellow
    & ".venv\Scripts\Activate.ps1"
}

Write-Host "[INFO] Iniciando GlassFish Monitor..." -ForegroundColor Green
Write-Host ""

# Executar a aplicação
python -m glassfish_monitor

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ERRO] Aplicação encerrou com erro" -ForegroundColor Red
    Read-Host "Pressione Enter para sair"
}
