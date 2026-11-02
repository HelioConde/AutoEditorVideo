$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { throw 'Execute scripts\instalar-windows.ps1 primeiro.' }
& $python (Join-Path $PSScriptRoot 'configurar_gratis.py')
if ($LASTEXITCODE -ne 0) { throw "Configuracao falhou (codigo $LASTEXITCODE)" }
