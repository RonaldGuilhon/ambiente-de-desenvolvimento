# ============================================
# GlassFish Monitor - Script de Inicialização
# ============================================

Write-Host "===================================" -ForegroundColor Cyan
Write-Host "   GlassFish Monitor v1.0.0" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

# Verificar se já é administrador
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "[INFO] Solicitando permissões de administrador..." -ForegroundColor Yellow
    Write-Host "[INFO] O GlassFish em 'Program Files' requer permissões elevadas." -ForegroundColor Yellow
    Write-Host ""
    
    try {
        Start-Process powershell -ArgumentList @(
            "-ExecutionPolicy", "Bypass",
            "-File", "`"$PSCommandPath`""
        ) -Verb RunAs -Wait
    } catch {
        Write-Host "[ERRO] Não foi possível obter permissões de administrador." -ForegroundColor Red
        Write-Host "Tente executar o PowerShell como Administrador manualmente." -ForegroundColor Red
        Read-Host "Pressione Enter para sair"
    }
    exit
}

Write-Host "[OK] Executando como Administrador" -ForegroundColor Green
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
}

& ".venv\Scripts\Activate.ps1"

if (-not (Test-Path ".venv\.deps_installed")) {
    Write-Host "[INFO] Instalando dependências..." -ForegroundColor Yellow
    pip install -e . 2>$null | Out-Null
    New-Item -ItemType File -Path ".venv\.deps_installed" -Force | Out-Null
}

Write-Host "[INFO] Iniciando GlassFish Monitor..." -ForegroundColor Green
Write-Host ""

python -m glassfish_monitor

Read-Host "Pressione Enter para sair"
