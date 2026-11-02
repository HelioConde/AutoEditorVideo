# Instala g4f em um ambiente isolado, sem tocar no ambiente do MoneyPrinterTurbo.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    $uv = (Get-Command uv -ErrorAction SilentlyContinue)
    $uvExe = if ($uv) { $uv.Source } else { Join-Path $env:USERPROFILE '.local\bin\uv.exe' }
    if (-not (Test-Path $uvExe)) { throw 'uv nao encontrado. Execute: winget install --id=astral-sh.uv -e ; depois reabra o PowerShell.' }
    Write-Host '[1/3] Python 3.11 (automatico via uv)...'
    & $uvExe python install 3.11
    if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel instalar Python 3.11.' }
    Write-Host '[2/3] Criando ambiente GPT4Free isolado...'
    & $uvExe venv --python 3.11 '.g4f-venv'
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar ambiente GPT4Free.' }
    $python = Join-Path $root '.g4f-venv\Scripts\python.exe'
    Write-Host '[3/3] Instalando g4f 8.8.6 (dependencias slim)...'
    & $uvExe pip install --python $python 'g4f[slim]==8.8.6'
    if ($LASTEXITCODE -ne 0) { throw 'Falha na instalacao do GPT4Free. Reveja mensagens acima.' }
    # Evitar strings com aspas internas em -c: Windows PowerShell 5.1 pode remove-las.
    & $python -c 'import g4f, fastapi, PIL'
    if ($LASTEXITCODE -ne 0) { throw 'Erro ao importar os pacotes.' }
    Write-Host '[OK] GPT4Free, FastAPI e Pillow importados com sucesso.' -ForegroundColor Green
    Write-Host 'GPT4Free instalado isoladamente. Execute .\scripts\iniciar-gpt4free.ps1' -ForegroundColor Green
} finally { Pop-Location }
