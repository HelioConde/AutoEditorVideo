# Serie Kids: Emanuelly e seus Amigos de Pelucia - EP 1 em quatro Shorts.
# Referencia ISOLADA por fase: apenas Emanuelly antes de Fofinho nascer.
# GPT Image 2 obrigatorio; nunca enviar a prancha inteira ao gerar quadros.
# Sem criar canal, sem OAuth, sem publicacao, sem imagens substitutas.
[CmdletBinding()]
param(
  [ValidateSet('Planejar','InstalarReferencia','PrepararReferencias','Imagens','Voz','Renderizar','Gerar','Verificar','Abrir')]
  [string]$Acao='Planejar',

  [ValidateSet('Todas','1','2','3','4')]
  [string]$Parte='1',

  [string]$Referencia='',

  [ValidateSet('gpt-image-2')]
  [string]$Modelo='gpt-image-2',

  [ValidateRange(0,100)][int]$MaxChamadas=0,

  [switch]$Refazer
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
# Parte 1 aprovada: delegar somente Voz/Planejar/Verificar/Renderizar/Abrir
# para o novo motor, sem reativar o roteiro antigo de 9 cenas.
if($Parte -eq '1' -and $Acao -in @('Voz','Planejar','Verificar','Renderizar','Abrir')){
  $new=Join-Path $root 'fofinhos-ep01.ps1'
  if(-not(Test-Path -LiteralPath $new -PathType Leaf)){
    throw 'Motor Fofinhos aprovado nao encontrado. Atualize a branch main.'
  }
  $names=@{
    'Voz'='Voz'; 'Planejar'='Planejar'; 'Verificar'='Planejar';
    'Renderizar'='Renderizar'; 'Abrir'='Abrir'
  }
  $name=$names[$Acao]
  if($Acao -eq 'Abrir'){
    & $new -Acao $name
  }else{
    & $new -Acao $name -Refazer:$Refazer
  }
  return
}
$program=Join-Path $root 'scripts\serie_kids_emanuelly_v1.py'
if(-not(Test-Path -LiteralPath $program -PathType Leaf)){
  throw 'Motor da serie ausente. Execute git pull --ff-only origin main.'
}
$python=Join-Path $root '.venv\Scripts\python.exe'
if(-not(Test-Path -LiteralPath $python -PathType Leaf)){
  $cmd=Get-Command python -ErrorAction SilentlyContinue
  if(-not $cmd){throw 'Python nao encontrado. Configure o ambiente .venv do projeto.'}
  $python=$cmd.Source
}
$privateImage=Join-Path $root 'assets\referencias-privadas\emanuelly-elenco.png'
if($Acao -eq 'Abrir'){
  if($Parte -eq 'Todas'){throw 'Para abrir um MP4, escolha -Parte 1, 2, 3 ou 4.'}
  $ids=@{
    '1'='kids-emanuelly-ep01-p01-ovo-azul'
    '2'='kids-emanuelly-ep01-p02-nascimento'
    '3'='kids-emanuelly-ep01-p03-poder-agua'
    '4'='kids-emanuelly-ep01-p04-abraco-magico'
  }
  $movie=Join-Path $root ("assets\gerados\kids-emanuelly\"+$ids[$Parte]+"\final.mp4")
  if(-not(Test-Path -LiteralPath $movie -PathType Leaf)){
    throw "MP4 ainda nao foi renderizado: $movie"
  }
  Start-Process -FilePath $movie
  return
}
if($Acao -eq 'InstalarReferencia' -and [string]::IsNullOrWhiteSpace($Referencia)){
  throw 'Informe -Referencia "C:\caminho\da\foto.png" para instalar localmente.'
}
if($Referencia -and $Acao -ne 'InstalarReferencia'){
  throw 'Para nao misturar fotos, use primeiro -Acao InstalarReferencia -Referencia "arquivo.png".'
}
if($Refazer -and $Acao -in @('Planejar','Verificar')){
  throw 'Refazer nao se aplica a Planejar ou Verificar.'
}
$mapped=@{
  Planejar='planejar';InstalarReferencia='instalar-referencia';
  PrepararReferencias='preparar-referencias';
  Imagens='imagens';Voz='voz';Renderizar='renderizar';
  Gerar='testar';Verificar='verificar'
}
$argsPy=@($program,'--acao',$mapped[$Acao],'--modelo',$Modelo,'--max-chamadas',"$MaxChamadas")
if($Acao -eq 'InstalarReferencia'){
  $resolved=(Resolve-Path -LiteralPath $Referencia -ErrorAction Stop).Path
  $argsPy+=@('--referencia',$resolved)
}else{
  if($Parte -ne 'Todas'){$argsPy+=@('--parte',$Parte)}
}
if($Refazer){$argsPy+='--refazer'}

if($Acao -in @('PrepararReferencias','Imagens','Gerar')){
  if(-not(Test-Path -LiteralPath $privateImage -PathType Leaf)){
    throw ('Referencia privada ausente em: '+$privateImage+
      '. Extraia o ZIP da foto na raiz do projeto ou use -Acao InstalarReferencia.')
  }
  if($MaxChamadas -le 0){
    Write-Warning 'Nenhuma chamada de IA autorizada (-MaxChamadas 0). So funcionara com referencias/imagens em cache.'
  }else{
    Write-Host "[IMAGENS] Limite explicito por execucao: $MaxChamadas novas chamadas; sem fallback." -ForegroundColor Yellow
  }
}

Write-Host ("[EMANUELLY KIDS PT-BR] "+$Acao+" | Parte "+$Parte+" | modelo "+$Modelo+" | Zero upload") -ForegroundColor Cyan
& $python @argsPy
if($LASTEXITCODE -ne 0){
  throw 'Geracao Kids interrompida com bloqueio. Caches e videos originais preservados. Nenhum upload.'
}
Write-Host '[EMANUELLY] Etapa concluida localmente. Nenhum envio ao YouTube.' -ForegroundColor Green
