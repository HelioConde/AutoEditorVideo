$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { throw 'Execute scripts\instalar-windows.ps1 primeiro.' }
Write-Host 'Abrindo ponte gratuita AI Horde na porta 7861 (nao feche esta janela durante a renderizacao)...'
Write-Host 'Fila gratuita pode demorar e nao garante disponibilidade ou qualidade.'
& $python (Join-Path $PSScriptRoot 'ponte_ai_horde.py') --port 7861
if ($LASTEXITCODE -ne 0) { throw "API gratuita falhou (codigo $LASTEXITCODE)" }
