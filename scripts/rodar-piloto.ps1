param(
    [ValidateSet('validar','renderizar')]
    [string]$Modo = 'validar',
    [string]$Episodio = '001-death-note',
    [ValidateSet('cartelas','ia-gratis','gpt4free')]
    [string]$Imagens = 'cartelas'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    $python = Join-Path $root '.venv\Scripts\python.exe'
    if (-not (Test-Path $python)) {
        throw 'Ambiente Python nao instalado. Execute: powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\instalar-windows.ps1'
    }
    $argsList = @('scripts\piloto.py', '--episodio', $Episodio, '--imagens', $Imagens)
    if ($Modo -eq 'renderizar') { $argsList += '--renderizar' }
    & $python @argsList
    if ($LASTEXITCODE -ne 0) {
        throw "O piloto falhou (codigo $LASTEXITCODE). Consulte a mensagem de erro acima."
    }
} finally {
    Pop-Location
}
