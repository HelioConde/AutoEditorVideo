$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { throw 'Instale primeiro o kit principal com .\scripts\instalar-windows.ps1' }
Push-Location $root
try {
    & $python scripts\configurar_gpt4free.py
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao configurar o MoneyPrinterTurbo' }
} finally { Pop-Location }
