# Fofinhos EP01 / Parte 1: historia aprovada em 15 cenas.
# Este fluxo e independente dos 4 Shorts antigos e NAO gera imagens.
[CmdletBinding()]
param(
  [ValidateSet('Planejar','Voz','GuiaFlores','Renderizar','Abrir')]
  [string]$Acao='Planejar',
  [switch]$Refazer
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$program=Join-Path $root 'scripts\fofinhos_ep01_render.py'
if(-not(Test-Path -LiteralPath $program -PathType Leaf)){
  throw 'Motor Fofinhos canonico ausente: atualize o GitHub.'
}
$python=Join-Path $root '.venv\Scripts\python.exe'
if(-not(Test-Path -LiteralPath $python -PathType Leaf)){
  $cmd=Get-Command python -ErrorAction SilentlyContinue
  if(-not $cmd){throw 'Python nao encontrado.'}
  $python=$cmd.Source
}
$folder=Join-Path $root 'assets\gerados\fofinhos\ep01-parte01-canonico'
if($Acao -eq 'Abrir'){
  $video=Join-Path $folder 'previa-canonica.mp4'
  if(Test-Path -LiteralPath $video -PathType Leaf){
    Start-Process -FilePath $video
    return
  }
  $guide=Join-Path $folder 'guias-flores'
  if(Test-Path -LiteralPath $guide -PathType Container){
    Start-Process -FilePath $guide
    return
  }
  throw 'Nenhuma previa ou guia gerado ainda.'
}
if($Refazer -and $Acao -notin @('Voz','Renderizar')){
  throw 'Refazer valido somente para Voz/Renderizar.'
}
$argsPy=@($program,'--acao',@{
  'Planejar'='planejar'; 'Voz'='voz';
  'GuiaFlores'='guia-flores'; 'Renderizar'='renderizar'
}[$Acao])
if($Refazer){$argsPy+='--refazer'}
Write-Host "[FOFINHOS EP01] $Acao | 15 cenas aprovadas | ZERO chamadas de imagem | ZERO uploads" -ForegroundColor Cyan
& $python @argsPy
if($LASTEXITCODE -ne 0){
  throw 'Producao canonica interrompida. Nenhuma imagem privada/publicacao alterada.'
}
Write-Host '[FOFINHOS] Operacao concluida localmente.' -ForegroundColor Green
