# Arquivo Otaku v0.7 — gera novo MP4 sem substituir o video ja enviado.
[CmdletBinding()]
param(
  [ValidateSet('gpt-image-1.5','gpt-image-2')][string]$Modelo='gpt-image-1.5',
  [switch]$SomenteConfigurar,
  [switch]$ApenasQA,
  [switch]$ReutilizarImagens,
  [string]$PastaImagens = ''
)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$py=Join-Path $root '.venv\Scripts\python.exe'
$script=Join-Path $root 'scripts\gerar_video_codex.py'
if (-not (Test-Path $py)) { throw 'Ambiente .venv ausente. Execute scripts\instalar-windows.ps1' }
if (-not (Test-Path $script)) { throw 'Extraia o pacote v0.6 completo, incluindo scripts\.' }
$env:MPT_HOME=Join-Path $root '.mpt-runtime'
$arguments=@($script,'--modelo',$Modelo)
if($SomenteConfigurar){$arguments+='--somente-configurar'}
if($ApenasQA){$arguments+='--apenas-qa'}
if($ReutilizarImagens){$arguments+='--reutilizar-imagens'}
if($PastaImagens){$arguments+=@('--pasta-imagens',$PastaImagens)}
Push-Location $root
try {
  & $py @arguments
  if($LASTEXITCODE -ne 0){throw "Gerador retornou erro $LASTEXITCODE. Verifique as mensagens acima."}
  if(-not $SomenteConfigurar -and -not $ApenasQA){
    $nome=if($ReutilizarImagens){'arquivo-otaku-piloto-v07-reuso.mp4'}else{'arquivo-otaku-piloto-codex-v07.mp4'}
    $target=Join-Path $root ('assets\gerados\'+$nome)
    if(Test-Path $target){Start-Process -FilePath $target}
  }
} finally { Pop-Location }
