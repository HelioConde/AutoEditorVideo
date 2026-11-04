# Canal Gamer (PT-BR) - entrada exclusiva e segura no AutoEditorVideo.
# Reutiliza o motor Games/Kids, mas NUNCA seleciona o canal Kids.
# Roteiros, voz e render sao locais. Este arquivo NAO publica videos.
[CmdletBinding()]
param(
  [ValidateSet('Validar','Preparar','Inspecionar','VerificarVideo','Voz','Renderizar')]
  [string]$Acao='Validar',

  [ValidatePattern('^game-[0-9]{3}-[a-z0-9-]+$')]
  [string]$Id='',

  [switch]$Refazer
)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

$root=$PSScriptRoot
$entrada=Join-Path $root 'piloto-canais-v3.ps1'
if(-not (Test-Path -LiteralPath $entrada -PathType Leaf)){
  throw 'Motor do canal Gamer ausente. Atualize com git pull --ff-only origin main.'
}

$mapa=@{
  Validar='validar'
  Preparar='preparar'
  Inspecionar='inspecionar'
  VerificarVideo='verificar-video'
  Voz='voz'
  Renderizar='renderizar'
}
$acaoMotor=$mapa[$Acao]

if($Acao -in @('Voz','Renderizar') -and [string]::IsNullOrWhiteSpace($Id)){
  throw 'Informe -Id game-001-minecraft-um-coracao (ou outro ID game-) para voz/render.'
}
if($Refazer -and $Acao -notin @('Voz','Renderizar')){
  throw '-Refazer somente e permitido em -Acao Voz ou Renderizar.'
}

$argumentos=@{Acao=$acaoMotor;Canal='games'}
if($Id){$argumentos.Id=$Id}
if($Refazer){$argumentos.Refazer=$true}

Write-Host "[GAMER PT-BR] $Acao | canal=games | $Id" -ForegroundColor Cyan
& $entrada @argumentos
if(-not $?){
  throw 'Etapa gamer falhou: confira o erro do motor. Nenhum upload foi solicitado.'
}
Write-Host '[GAMER] Etapa concluida localmente. Publicacao e criacao de canal permanecem desativadas.' -ForegroundColor Green
