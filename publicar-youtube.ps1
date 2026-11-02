# Uso: .\publicar-youtube.ps1 -Etapa preparar|-Etapa tudo|-Etapa enviar
[CmdletBinding()]
param(
    [ValidateSet('preparar','enviar','tudo','diagnostico')][string]$Etapa='preparar',
    [ValidateSet('private','unlisted','public')][string]$Privacidade='public',
    [ValidateSet('gpt-image-1.5','gpt-image-2')][string]$Modelo='gpt-image-1.5',
    [switch]$ArteIA,
    [switch]$TextoIA,
    [switch]$GerarVideo,
    [string]$Video='',
    [string]$Episodio='',
    [switch]$Refazer
)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$py=Join-Path $root '.venv\Scripts\python.exe'
$program=Join-Path $root 'scripts\publicar_arquivo_otaku.py'
if (-not (Test-Path $py)) { throw 'Ambiente Python ausente. Primeiro execute scripts\instalar-windows.ps1' }
if (-not (Test-Path $program)) { throw 'Extraia o ZIP de publicacao inteiro no arquivo-otaku-kit' }
if ($GerarVideo -and $Etapa -in @('enviar','tudo')) {
    $oauth=Join-Path $root '.secrets\youtube-oauth-client.json'
    if (-not (Test-Path $oauth)) {
        throw 'Credenciais OAuth ausentes. Configure o JSON OAuth em .secrets\youtube-oauth-client.json antes de gerar outro video para publicacao.'
    }
}
if ($GerarVideo) {
    $gerar=Join-Path $root 'gerar-video-codex.ps1'
    if (-not (Test-Path $gerar)) { throw 'gerar-video-codex.ps1 ausente; extraia o kit v0.4' }
    Write-Host '[ETAPA 1] Gerando o video via MoneyPrinterTurbo e Codex Proxy'
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $gerar -Modelo $Modelo
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao gerar video' }
    if (-not $Video) { $Video = Join-Path $root 'assets\gerados\arquivo-otaku-piloto-codex-v06.mp4' }
}
$marker=Join-Path $root '.venv\arquivo-otaku-publicacao-deps-ok'
if (-not (Test-Path $marker)) {
    Write-Host '[INFO] Conferindo dependencias para miniaturas e YouTube OAuth.'
    $req=Join-Path $root 'requirements-publicacao.txt'
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        & uv pip install --python $py -r $req
    } else {
        & $py -m pip install -r $req
    }
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar dependencias. Consulte GUIA-PUBLICAR-YOUTUBE.md' }
    New-Item -ItemType File -Path $marker -Force | Out-Null
}
$argsForPython=@($program,'--etapa',$Etapa,'--privacidade',$Privacidade,'--modelo-imagem',$Modelo)
if ($ArteIA) {$argsForPython+='--arte-ia'}
if ($TextoIA) {$argsForPython+='--texto-ia'}
if ($Refazer) {$argsForPython+='--refazer'}
if ($Video) {$argsForPython+=@('--video',$Video)}
if ($Episodio) {$argsForPython+=@('--episodio',$Episodio)}
Write-Host "[INFO] Etapa: $Etapa; privacidade solicitada: $Privacidade; IA de arte: $ArteIA; IA texto: $TextoIA"
& $py @argsForPython
if ($LASTEXITCODE -ne 0) { throw 'Pipeline interrompido. Confira a mensagem de erro acima.' }
