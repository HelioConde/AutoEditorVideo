# Otaku Reframe - entrada segura para produzir Shorts EN no Windows.
# Requer os scripts Python do AutoEditorVideo desta branch.
# Nao publica nem altera o canal brasileiro.
[CmdletBinding()]
param(
  [ValidateSet('Preparar','Diagnosticar','GerarImagens','Revisar','Validar','Renderizar','Automatizar')]
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
  [ValidateSet('automatico','manual')]
  [string]$ModoQA='automatico',
  [ValidateSet('private','unlisted','public')]
  [string]$Visibilidade='private',
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
if($Acao -notin @('GerarImagens','Automatizar') -and $MaxChamadas -ne 0){
  throw 'MaxChamadas so pode ser usado em -Acao GerarImagens ou Automatizar.'
}
if($Acao -eq 'GerarImagens' -and $MaxChamadas -lt 1){
  throw 'GerarImagens exige -MaxChamadas com orcamento explicito maior que zero.'
}
if($Acao -ne 'Renderizar' -and $ConfirmarRevisaoVisual){
  throw 'ConfirmarRevisaoVisual so pode ser usado em -Acao Renderizar.'
}
if($Acao -eq 'Automatizar' -and $ModoQA -ne 'automatico'){
  throw 'Automatizar exige -ModoQA automatico. O modo manual fica em -Acao Revisar.'
}
if($Acao -ne 'Renderizar' -and $Refazer){
  throw 'Refazer so pode ser usado em -Acao Renderizar.'
}

function Invoke-English {
  param([Parameter(Mandatory=$true)][string]$Step)
  $argv=@($script:render,'--manifesto',$script:manifestPath,'--acao',$Step,
          '--id',$script:Id,'--modelo',$script:Modelo,'--perfil',$script:Perfil)
  if($script:Refazer -and $Step -eq 'renderizar'){$argv+='--refazer'}
  $argv+=@('--modo-qa',$script:ModoQA)
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
  } else {
    throw 'Storyboard exclusivo EN nao encontrado. Execute -Acao Preparar antes de gerar imagens ou render.'
  }
  & $script:master -Id $script:Id -Modelo $script:Modelo @Options
  # O script filho valida seus proprios exit codes e lanca erros.
  if(-not $?){
    throw "Falha no gerador de imagens para $($script:Id)."
  }
}

function Invoke-StrictEnglishQA {
  $validator=Join-Path $script:root 'scripts\validar_reframe_en.py'
  if(-not (Test-Path -LiteralPath $validator -PathType Leaf)){
    throw 'QA EN local ausente; atualize o AutoEditorVideo com git pull.'
  }
  $venv=Join-Path $script:root '.venv\Scripts\python.exe'
  $runner=if(Test-Path -LiteralPath $venv -PathType Leaf){$venv}else{$script:python}
  & $runner $validator '--manifesto' $script:manifestPath '--id' $script:Id '--modelo' $script:Modelo '--modo-qa' $script:ModoQA
  if($LASTEXITCODE -ne 0){
    throw 'Imagens, aprovacao manual, voz ou legendas EN ainda nao validas. Nao renderizar.'
  }
}

function Invoke-Preparation {
  $preflight=@((Join-Path $script:root 'scripts\otaku_reframe_direction.py'),
               '--manifesto',$script:manifestPath,'--id',$script:Id)
  & $script:python @preflight
  if($LASTEXITCODE -ne 0){throw 'Falha ao preparar storyboard EN (sem IA).'}
  # Instala dependencias, imprime cache, sem gerar imagens nem narracao PT.
  Invoke-Master @{DiagnosticarCache=$true;TodasCenas=$true;CriarVoz=$true;MaxChamadas=0;MaxSegundosPorPlano=4.5}
  Invoke-English 'planejar'
  Invoke-English 'voz'
}

function Invoke-YoutubeEnglish {
  $upload=Join-Path $script:root 'scripts\publicar_shorts_en.py'
  if(-not (Test-Path -LiteralPath $upload -PathType Leaf)){
    throw 'Uploader EN nao encontrado; atualize com git pull.'
  }
  $venv=Join-Path $script:root '.venv\Scripts\python.exe'
  $runner=if(Test-Path -LiteralPath $venv -PathType Leaf){$venv}else{$script:python}
  & $runner $upload '--acao' 'enviar' '--manifesto' $script:manifestPath '--id' $script:Id `
      '--perfil' $script:Perfil '--privacidade' $script:Visibilidade '--confirmar'
  if($LASTEXITCODE -ne 0){throw 'Upload EN nao confirmado; confira estado.json e Studio antes de repetir.'}
}

Write-Host "[OTAKU REFRAME] $Id | $Acao | en-US" -ForegroundColor Cyan
switch($Acao){
  'Preparar' {
    Invoke-Preparation
    Write-Host '[OK] Storyboard, voz EN e diagnostico preparados. Sem upload.' -ForegroundColor Green
  }
  'Diagnosticar' {
    Invoke-English 'planejar'
    Invoke-Master @{DiagnosticarCache=$true;TodasCenas=$true;MaxChamadas=0;MaxSegundosPorPlano=4.5}
  }
  'GerarImagens' {
    Invoke-Master @{TodasCenas=$true;MaxChamadas=$MaxChamadas;MaxSegundosPorPlano=4.5}
    Write-Host '[REVISAO] Para conferir e aprovar cada cena, execute -Acao Revisar.' -ForegroundColor Yellow
  }
  'Revisar' {
    if(-not (Test-Path -LiteralPath $enPlan -PathType Leaf)){
      throw 'Storyboard EN nao encontrado. Execute -Acao Preparar primeiro.'
    }
    $reviewer=Join-Path $root 'scripts\revisar_reframe_en.py'
    if(-not (Test-Path -LiteralPath $reviewer -PathType Leaf)){
      throw 'Assistente de revisao ausente. Atualize com git pull.'
    }
    $venv=Join-Path $root '.venv\Scripts\python.exe'
    $runner=if(Test-Path -LiteralPath $venv -PathType Leaf){$venv}else{$python}
    & $runner $reviewer '--plano' $enPlan '--id' $Id '--modelo' $Modelo '--acao' 'revisar'
    if($LASTEXITCODE -ne 0){throw 'Revisao interrompida. Nenhuma imagem foi aprovada automaticamente.'}
    Write-Host '[REVISAO] A aprovacao registrada pertence apenas ao cache exato da cena.' -ForegroundColor Cyan
  }
  'Validar' {
    Invoke-Master @{SomenteValidar=$true;TodasCenas=$true;MaxChamadas=0}
    Invoke-StrictEnglishQA
    Write-Host '[OK] Todas as cenas aprovadas, voz/legendas EN e camadas verificadas. Nao publicado.' -ForegroundColor Green
  }
  'Renderizar' {
    if($ModoQA -eq 'manual' -and -not $ConfirmarRevisaoVisual){
      throw 'QA manual exige -ConfirmarRevisaoVisual; para automatizar use -ModoQA automatico.'
    }
    Invoke-Master @{SomenteValidar=$true;TodasCenas=$true;MaxChamadas=0}
    Invoke-StrictEnglishQA
    # Somente o compositor local Remotion do AutoEditorVideo gera o MP4.
    Invoke-English 'renderizar'
    $folder=Join-Path $root ("assets\gerados\shorts-animados\{0}\en-US" -f $Id)
    Write-Host "[MP4 EN] Procure o arquivo final em: $folder" -ForegroundColor Green
    Write-Host '[SEGURANCA] Arquivo local; nenhum upload ao YouTube/TikTok.' -ForegroundColor Cyan
  }
  'Automatizar' {
    Write-Host '[AUTO EN] Iniciando pipeline do AutoEditorVideo. Destino: YouTube EN.' -ForegroundColor Cyan
    Write-Host "[UPLOAD] Privacidade: $Visibilidade. QA tecnico nao garante qualidade artistica." -ForegroundColor Yellow
    Invoke-Preparation
    Invoke-Master @{TodasCenas=$true;MaxChamadas=$MaxChamadas;MaxSegundosPorPlano=4.5}
    Invoke-Master @{SomenteValidar=$true;TodasCenas=$true;MaxChamadas=0}
    Invoke-StrictEnglishQA
    Invoke-English 'renderizar'
    # Upload ocorre somente apos Remotion gerar e validar um MP4 assinado.
    # Conta OAuth precisa corresponder ao canal EN, nunca ao BR.
    Invoke-YoutubeEnglish
    Write-Host '[AUTO EN OK] Confira o Short completo no YouTube Studio do canal EN.' -ForegroundColor Green
  }
}
