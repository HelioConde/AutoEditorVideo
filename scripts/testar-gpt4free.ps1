$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.g4f-venv\Scripts\python.exe'
if (-not (Test-Path $python)) { throw 'Execute primeiro .\scripts\instalar-gpt4free.ps1' }
Push-Location $root
try {
    & $python 'scripts\testar_gpt4free.py'
    if ($LASTEXITCODE -ne 0) { throw "Falha no teste de uma imagem (codigo $LASTEXITCODE)." }
} finally { Pop-Location }
