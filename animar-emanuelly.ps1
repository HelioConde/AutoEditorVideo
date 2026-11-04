# Prepara/rende EP 1 Parte 1 por CAMADAS (jardim, quarto, Emanuelly, ovo).
# Nenhuma IA de imagens, sem upload e sem alterar videos/narracao originais.
[CmdletBinding()]
param(
  [ValidateSet('Planejar','Instalar','InstalarLote','Preparar','Renderizar','Verificar','Abrir')]
  [string]$Acao='Planejar',

  [ValidateSet('Jardim','Quarto','Ovo')]
  [string]$Tipo='Jardim',

  [ValidateRange(1,4)]
  [int]$Indice=1,

  [string]$Arquivo='',
  [string]$Pasta='',
  [switch]$Refazer
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$script=Join-Path $root 'scripts\kids_emanuelly_cenarios_camadas_v1.py'
if(-not (Test-Path -LiteralPath $script -PathType Leaf)){
  throw 'Compositor Kids ausente. Atualize o repositorio com git pull.'
}
$python=Join-Path $root '.venv\Scripts\python.exe'
if(-not (Test-Path -LiteralPath $python -PathType Leaf)){
  $cmd=Get-Command python -ErrorAction SilentlyContinue
  if(-not $cmd){throw 'Python indisponivel. Configure .venv do projeto.'}
  $python=$cmd.Source
}
$movie=Join-Path $root 'assets\gerados\kids-emanuelly\kids-emanuelly-ep01-p01-ovo-azul\final-camadas.mp4'
if($Acao -eq 'Abrir'){
  if(-not (Test-Path -LiteralPath $movie -PathType Leaf)){
    throw "Previa nao encontrada: $movie"
  }
  Start-Process -FilePath $movie
  return
}
if($Refazer -and $Acao -notin @('Instalar','InstalarLote','Renderizar')){
  throw '-Refazer permitido apenas com Instalar, InstalarLote ou Renderizar.'
}
$map=@{
  Planejar='planejar';Instalar='instalar';InstalarLote='instalar-lote';
  Preparar='props';Renderizar='renderizar';Verificar='verificar'
}
$argsPython=@($script,'--acao',$map[$Acao])
if($Acao -eq 'Instalar'){
  if([string]::IsNullOrWhiteSpace($Arquivo)){
    throw 'Instalar exige -Arquivo "C:\imagens\jardim.png".'
  }
  $file=(Resolve-Path -LiteralPath $Arquivo -ErrorAction Stop).Path
  $argsPython+=@('--tipo',$Tipo,'--indice',"$Indice",'--arquivo',$file)
}
if($Acao -eq 'InstalarLote'){
  if([string]::IsNullOrWhiteSpace($Pasta)){
    throw 'InstalarLote exige -Pasta "C:\pasta\referencias".'
  }
  $dir=(Resolve-Path -LiteralPath $Pasta -ErrorAction Stop).Path
  $argsPython+=@('--pasta',$dir)
}
if($Refazer){$argsPython+='--refazer'}
Write-Host "[KIDS CAMADAS PT-BR] $Acao | EP 1 Parte 1 | 0 chamadas IA | 0 uploads" -ForegroundColor Cyan
& $python @argsPython
if($LASTEXITCODE -ne 0){
  throw 'Composicao Kids interrompida. Fontes, audio, musica e videos anteriores preservados.'
}
Write-Host '[KIDS CAMADAS] Etapa local concluida. Nenhum upload.' -ForegroundColor Green
