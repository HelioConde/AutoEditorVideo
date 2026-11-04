# Fofinho EP01 / 4 Shorts Kids PT-BR — biblioteca visual reutilizavel.
# Modo Catalogo e Planejar nao geram imagens; GerarImagens e opcional e
# exige orçamento explicito. Todos os demais modos: zero IA e zero upload.
[CmdletBinding()]
param(
  [ValidateSet('Catalogo','Planejar','Instalar','InstalarLote',
               'GerarImagens','Preparar','Renderizar','Verificar','Abrir')]
  [string]$Acao='Planejar',

  [ValidateSet('1','2','3','4','Todas')]
  [string]$Parte='1',

  [ValidateSet('Jardim','Quarto','Ovo')]
  [string]$Tipo='Jardim',

  [ValidateRange(1,4)]
  [int]$Indice=1,

  # Ex: -Recurso fofinho-azul; -Recurso ovo-rachado
  [string]$Recurso='',

  [string]$Arquivo='',
  [string]$Pasta='',
  [ValidateRange(0,100)]
  [int]$MaxChamadas=0,
  [switch]$Refazer
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$program=Join-Path $root 'scripts\kids_emanuelly_todos_videos_v2.py'
if(-not(Test-Path -LiteralPath $program -PathType Leaf)){
  throw 'Compositor de todos os videos Fofinho nao encontrado. Execute git pull.'
}
$python=Join-Path $root '.venv\Scripts\python.exe'
if(-not(Test-Path -LiteralPath $python -PathType Leaf)){
  $cmd=Get-Command python -ErrorAction SilentlyContinue
  if(-not $cmd){throw 'Python ausente. Instale/configure .venv do projeto.'}
  $python=$cmd.Source
}
$ids=@{
  '1'='kids-emanuelly-ep01-p01-ovo-azul'
  '2'='kids-emanuelly-ep01-p02-nascimento'
  '3'='kids-emanuelly-ep01-p03-poder-agua'
  '4'='kids-emanuelly-ep01-p04-abraco-magico'
}
if($Acao -eq 'Abrir'){
  if($Parte -eq 'Todas'){
    $folder=Join-Path $root 'assets\gerados\kids-emanuelly'
    if(-not(Test-Path -LiteralPath $folder -PathType Container)){
      throw 'Nenhum video Kids gerado na biblioteca.'
    }
    Start-Process -FilePath $folder
    return
  }
  $movie=Join-Path $root ("assets\gerados\kids-emanuelly\"+$ids[$Parte]+"\final-camadas.mp4")
  if(-not(Test-Path -LiteralPath $movie -PathType Leaf)){
    throw "Video de camadas ainda nao existe: $movie"
  }
  Start-Process -FilePath $movie
  return
}
if($Refazer -and $Acao -notin @('Instalar','InstalarLote',
                               'GerarImagens','Renderizar')){
  throw 'Refazer so e permitido ao instalar, gerar uma imagem ou renderizar.'
}
$map=@{
  Catalogo='catalogo';Planejar='planejar';Instalar='instalar';
  InstalarLote='instalar-lote';GerarImagens='gerar-imagens';
  Preparar='preparar';Renderizar='renderizar';Verificar='verificar'
}
$argsPython=@($program,'--acao',$map[$Acao],'--parte',$Parte,
             '--max-chamadas',"$MaxChamadas")
if($Acao -eq 'Instalar'){
  if([string]::IsNullOrWhiteSpace($Arquivo)){
    throw 'Instalar exige -Arquivo "C:\Imagens\recurso.png".'
  }
  $resolved=(Resolve-Path -LiteralPath $Arquivo -ErrorAction Stop).Path
  $argsPython+=@('--tipo',$Tipo,'--indice',"$Indice",'--arquivo',$resolved)
}
if($Acao -eq 'InstalarLote'){
  if([string]::IsNullOrWhiteSpace($Pasta)){
    throw 'InstalarLote exige -Pasta "C:\Imagens\BibliotecaFofinho".'
  }
  $resolved=(Resolve-Path -LiteralPath $Pasta -ErrorAction Stop).Path
  $argsPython+=@('--pasta',$resolved)
}
if(-not [string]::IsNullOrWhiteSpace($Recurso)){
  $argsPython+=@('--recurso',$Recurso)
}
if($Refazer){$argsPython+='--refazer'}
if($Acao -eq 'GerarImagens'){
  Write-Host '[CONSENTIMENTO] Referencias oficiais e de personagens podem ser enviadas ao Codex Proxy e ao provedor configurado.' -ForegroundColor Yellow
  Write-Host "[LIMITE] gpt-image-2 somente; ate $MaxChamadas novas chamadas. Nenhum upload de video." -ForegroundColor Yellow
}
Write-Host "[FOFINHO KIDS] $Acao | Parte $Parte | 0 uploads automaticos" -ForegroundColor Cyan
& $python @argsPython
if($LASTEXITCODE -ne 0){
  throw 'Fofinho: etapa bloqueada. Referencias, narracao, musicas e videos anteriores preservados.'
}
Write-Host '[FOFINHO KIDS] Etapa concluida localmente, sem publicar videos.' -ForegroundColor Green
