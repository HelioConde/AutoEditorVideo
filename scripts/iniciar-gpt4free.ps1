# Executa a API g4f em 127.0.0.1:1337. Mantenha esta janela aberta durante o teste.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.g4f-venv\Scripts\python.exe'
if (-not (Test-Path $python)) { throw 'Instale GPT4Free com .\scripts\instalar-gpt4free.ps1 primeiro.' }
Write-Host 'Iniciando GPT4Free em http://127.0.0.1:1337/docs (somente neste computador).'
Write-Host 'Ctrl+C interrompe o servidor. Nao compartilhe cookies ou credenciais no chat.'
Push-Location $root
try {
    & $python -m g4f api --bind 127.0.0.1:1337 --port 1337 --no-gui --disable-pa-auto-download
    if ($LASTEXITCODE -ne 0) { throw "GPT4Free saiu com codigo $LASTEXITCODE" }
} finally { Pop-Location }
