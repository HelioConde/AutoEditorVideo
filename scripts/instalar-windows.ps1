# ARQUIVO OTAKU v0.2 - instalacao reproduzivel no Windows.
# Usa o gerenciador uv para obter Python 3.11 mesmo sem 'py -3.11'.
# Cria apenas a pasta .venv deste kit e instala os pacotes oficiais mpt e pillow.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    $uvCommand = Get-Command uv -ErrorAction SilentlyContinue
    $uvExecutable = $null
    if ($uvCommand) {
        $uvExecutable = $uvCommand.Source
    } elseif (Test-Path (Join-Path $env:USERPROFILE '.local\bin\uv.exe')) {
        $uvExecutable = Join-Path $env:USERPROFILE '.local\bin\uv.exe'
    }

    if (-not $uvExecutable) {
        throw "uv nao encontrado. Instale com: winget install --id=astral-sh.uv -e ; depois feche e reabra o PowerShell, e execute este script novamente."
    }

    Write-Host '[1/4] Preparando Python 3.11 com uv...'
    & $uvExecutable python install 3.11
    if ($LASTEXITCODE -ne 0) { throw 'uv nao conseguiu instalar Python 3.11. Verifique conexao e acesso ao GitHub.' }

    Write-Host '[2/4] Criando ambiente isolado .venv...'
    & $uvExecutable venv --python 3.11 --clear .venv
    if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel criar o ambiente .venv com Python 3.11.' }

    $python = Join-Path $root '.venv\Scripts\python.exe'
    if (-not (Test-Path $python)) { throw "Python nao encontrado apos criar o ambiente: $python" }

    Write-Host '[3/4] Instalando MoneyPrinterTurbo oficial (mpt) e Pillow...'
    & $uvExecutable pip install --python $python mpt pillow
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar mpt/pillow. Verifique o erro acima.' }

    Write-Host '[4/4] Verificando versao Python e dependencias...'
    # Verificacao sem aspas internas (compatibilidade com Windows PowerShell 5.1).
    & $python -c 'import sys, PIL; assert sys.version_info[:2] == (3, 11), sys.version'
    if ($LASTEXITCODE -ne 0) { throw 'Falha na verificacao do Python/Pillow.' }
    & $python --version
    Write-Host '[OK] Python 3.11 e Pillow importados com sucesso.' -ForegroundColor Green
    if (-not (Test-Path (Join-Path $root '.venv\Scripts\mpt.exe'))) {
        throw 'O executavel mpt.exe nao foi criado na .venv. Veja as mensagens da instalacao acima.'
    }

    Write-Host ''
    Write-Host 'INSTALACAO CONCLUIDA.' -ForegroundColor Green
    Write-Host 'Agora execute: powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\rodar-piloto.ps1 -Modo validar'
    Write-Host 'Depois:         powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\rodar-piloto.ps1 -Modo renderizar'
} finally {
    Pop-Location
}
