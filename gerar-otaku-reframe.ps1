# Otaku Reframe - entrada segura para produzir Shorts EN no Windows.
# Requer os scripts Python do AutoEditorVideo desta branch.
# Nao publica nem altera o canal brasileiro.
[CmdletBinding()]
param(
  [ValidateSet('Preparar','Diagnosticar','GerarImagens','Validar','Renderizar')]
  [string]$Acao='Preparar',
  [string]$Id='101-death-note-ep01',
  [string]$Manifesto='conteudos/otaku-reframe-ep01-en.json',
  [ValidateSet('gpt-image-1.5','gpt-image-2')]
  [string]$Modelo='gpt-image-1.5',
  [ValidateSet('equilibrado','vivo','ultrassutil')]
  [string]$Perfil='vivo',
  [ValidateRange(0,180)]
  [int]$MaxChamadas=0,
  [switch]$ConfirmarRevisaoVisual,
  [switch]$Refazer
)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$python=Join-Path $root '.venv\Scripts\python.exe'
if(-not (Test-Path -LiteralPath $python -PathType Leaf)){
  $found=Get-Command python -ErrorAction SilentlyContinue
  if(-not $found){throw 'Python nao encontrado. Instale Python 3.11 e configure a .venv.'}
  $python=$found.Source
}

$render=Join-Path $root 'scripts\renderizar_shorts_en.py'
$master=Join-Path $root 'gerar-shorts-master.ps1'
$manifestPath=if([IO.Path]::IsPathRooted($Manifesto)){$Manifesto}else{Join-Path $root $Manifesto}
$enPlan=Join-Path $root ("assets\gerados\shorts-animados\{0}\en-US\storyboard-reframe-v2.json" -f $Id)
foreach($path in @($render,$master,$manifestPath)){
  if(-not (Test-Path -LiteralPath $path -PathType Leaf)){
    throw "Arquivo necessario nao encontrado: $path. Confira a branch do GitHub."
  }
}
if($Id -notmatch '^[a-z0-9]+(?:-[a-z0-9]+)*$'){
  throw 'ID invalido: use apenas letras minusculas, numeros e hifens.'
}
if($Acao -ne 'GerarImagens' -and $MaxChamadas -ne 0){
  throw 'MaxChamadas so pode ser usado em -Acao GerarImagens. Nenhuma IA foi chamada.'
}
if($Acao -eq 'GerarImagens' -and $MaxChamadas -lt 1){
  throw 'GerarImagens exige -MaxChamadas com orcamento explicito maior que zero.'
}
if($Acao -ne 'Renderizar' -and $ConfirmarRevisaoVisual){
  throw 'ConfirmarRevisaoVisual so pode ser usado em -Acao Renderizar.'
}
if($Acao -ne 'Renderizar' -and $Refazer){
  throw 'Refazer so pode ser usado em -Acao Renderizar.'
}

function Invoke-English {
  param([Parameter(Mandatory=$true)][string]$Step)
  $argv=@($script:render,'--manifesto',$script:manifestPath,'--acao',$Step,
          '--id',$script:Id,'--modelo',$script:Modelo,'--perfil',$script:Perfil)
  if($script:Refazer -and $Step -eq 'renderizar'){$argv+='--refazer'}
  # O gerador master pode criar a .venv na etapa anterior.
  $venv=Join-Path $script:root '.venv\Scripts\python.exe'
  $runner=if(Test-Path -LiteralPath $venv -PathType Leaf){$venv}else{$script:python}
  & $runner @argv
  if($LASTEXITCODE -ne 0){throw "Falha na etapa EN: $Step (codigo $LASTEXITCODE)."}
}

function Invoke-Master {
  param([Parameter(Mandatory=$true)][hashtable]$Options)
  if(Test-Path -LiteralPath $script:enPlan -PathType Leaf){
    $Options['Plano']=$script:enPlan
  } elseif($script:Id -eq '101-death-note-ep01'){
    throw 'Storyboard EN nao encontrado. Execute -Acao Preparar antes de usar imagens ou render.'
  }
  & $script:master -Id $script:Id -Modelo $script:Modelo @Options
  # O script filho valida seus proprios exit codes e lanca erros.
  if(-not $?){
    throw "Falha no gerador de imagens para $($script:Id)."
  }
}

Write-Host "[OTAKU REFRAME] $Id | $Acao | en-US" -ForegroundColor Cyan
switch($Acao){
  'Preparar' {
    # Primeiro cria o storyboard EN separado. Jamais usa o plano PT antigo.
    Invoke-English 'planejar'
    # Diagnostico sem chamadas de imagem; prepara dependencias do TTS.
    Invoke-Master @{DiagnosticarCache=$true;TodasCenas=$true;CriarVoz=$true;MaxChamadas=0;MaxSegundosPorPlano=4.5}
    Invoke-English 'voz'
    Write-Host '[OK] Plano, voz EN e diagnostico preparados. Revise o cache antes de gerar imagens.' -ForegroundColor Green
  }
  'Diagnosticar' {
    Invoke-English 'planejar'
    Invoke-Master @{DiagnosticarCache=$true;TodasCenas=$true;MaxChamadas=0;MaxSegundosPorPlano=4.5}
  }
  'GerarImagens' {
    Invoke-Master @{TodasCenas=$true;MaxChamadas=$MaxChamadas;MaxSegundosPorPlano=4.5}
    Write-Host '[REVISAO] Confira todas as imagens e camadas. Nenhum MP4 foi publicado.' -ForegroundColor Yellow
  }
  'Validar' {
    Invoke-Master @{SomenteValidar=$true;TodasCenas=$true;MaxChamadas=0}
    Write-Host '[OK] Camadas locais verificadas. Ouça tambem a voz e revise as cenas.' -ForegroundColor Green
  }
  'Renderizar' {
    if(-not $ConfirmarRevisaoVisual){
      throw 'Reveja as cenas e informe -ConfirmarRevisaoVisual para liberar o MP4. Nenhum upload sera feito.'
    }
    Invoke-Master @{SomenteValidar=$true;TodasCenas=$true;MaxChamadas=0}
    Invoke-English 'renderizar'
    $folder=Join-Path $root ("assets\gerados\shorts-animados\{0}\en-US" -f $Id)
    Write-Host "[MP4 EN] Procure o arquivo final em: $folder" -ForegroundColor Green
    Write-Host '[SEGURANCA] Arquivo local; nenhum upload ao YouTube/TikTok.' -ForegroundColor Cyan
  }
}
