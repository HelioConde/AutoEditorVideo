# Segundo Short do Arquivo Otaku. Nada e publicado sem -Etapa publicar.
[CmdletBinding()]
param(
    [ValidateSet('plano','criar','preparar','publicar')][string]$Etapa = 'plano',
    [ValidateSet('gpt-image-1.5','gpt-image-2')][string]$Modelo = 'gpt-image-1.5',
    [ValidateSet('private','unlisted','public')][string]$Privacidade = 'private',
    [switch]$ConfirmarPublico,
    [switch]$ReutilizarImagens
)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$plano=Join-Path $root 'conteudos\002-death-note-memoria-direcao.json'
$video=Join-Path $root ('assets\gerados\arquivo-otaku-002-death-note-memoria-'+$(if($ReutilizarImagens){'reuso'}else{'codex'})+'.mp4')
$python=Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $plano)) { throw 'Plano do novo episodio ausente. Atualize o projeto antes de continuar.' }
if (-not (Test-Path $python)) { throw 'Ambiente Python .venv ausente. Rode scripts\instalar-windows.ps1.' }

function ExecutarOuFalhar([string]$Script, [string[]]$Argumentos) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Script @Argumentos
    if ($LASTEXITCODE -ne 0) { throw "Comando falhou: $Script (codigo $LASTEXITCODE)." }
}

if ($Etapa -eq 'plano') {
    & $python (Join-Path $root 'scripts\gerar_video_codex.py') --plano $plano --somente-configurar
    if($LASTEXITCODE -ne 0){throw 'Plano editorial invalido.'}
    Write-Host '[OK] Este comando nao gera imagem nem envia video.' -ForegroundColor Green
    exit 0
}

if ($Etapa -eq 'criar') {
    $params=@('-Modelo',$Modelo,'-Plano',$plano)
    if ($ReutilizarImagens) { $params += '-ReutilizarImagens' }
    ExecutarOuFalhar (Join-Path $root 'gerar-video-codex.ps1') $params
}

if ($Etapa -eq 'criar' -or $Etapa -eq 'preparar') {
    if (-not (Test-Path $video)) { throw "MP4 ainda nao encontrado: $video. Use -Etapa criar." }
    ExecutarOuFalhar (Join-Path $root 'publicar-youtube.ps1') @('-Etapa','preparar','-Video',$video,'-Episodio',$plano,'-Refazer')
    Write-Host "[OK] Novo video e capas preparados em $video. NADA foi publicado." -ForegroundColor Green
    exit 0
}

if ($Etapa -eq 'publicar') {
    if (-not (Test-Path $video)) { throw 'MP4 do episodio 002 nao encontrado. Rode -Etapa criar.' }
    if ($Privacidade -eq 'public' -and -not $ConfirmarPublico) {
        throw 'Para publicar como PUBLICO, adicione -ConfirmarPublico. Revise o MP4 e os direitos antes.'
    }
    $manifesto=Join-Path $root 'assets\gerados\publicacao-youtube\manifesto.json'
    if (-not (Test-Path $manifesto)) { throw 'Capas e metadados ainda nao preparados. Rode -Etapa preparar.' }
    $meta=Get-Content -LiteralPath $manifesto -Raw -Encoding UTF8 | ConvertFrom-Json
    if ([IO.Path]::GetFullPath([string]$meta.video) -ne [IO.Path]::GetFullPath($video)) {
        throw 'O manifesto de publicacao pertence a OUTRO video. Rode -Etapa preparar para o episodio 002.'
    }
    ExecutarOuFalhar (Join-Path $root 'publicar-youtube.ps1') @('-Etapa','enviar','-Video',$video,'-Episodio',$plano,'-Privacidade',$Privacidade)
}
