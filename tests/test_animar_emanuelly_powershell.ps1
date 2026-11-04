# No source photographs, no image calls, no MP4s in this test.
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$source=Join-Path (Split-Path -Parent $PSScriptRoot) 'animar-emanuelly.ps1'
$tokens=$null;$errors=$null
[System.Management.Automation.Language.Parser]::ParseFile(
  $source,[ref]$tokens,[ref]$errors
) | Out-Null
if($errors.Count -gt 0){throw 'Erro de sintaxe no compositor Kids'}
$temp=Join-Path ([IO.Path]::GetTempPath()) ('emanuelly-layers-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path (Join-Path $temp 'scripts') -Force | Out-Null
try{
  Copy-Item -LiteralPath $source -Destination (Join-Path $temp 'animar-emanuelly.ps1')
  @'
import sys,json
from pathlib import Path
Path(__file__).resolve().parents[1].joinpath("args.json").write_text(
  json.dumps(sys.argv[1:]),encoding="utf8")
'@ | Set-Content -LiteralPath (Join-Path $temp 'scripts\kids_emanuelly_todos_videos_v2.py') -Encoding UTF8
  $runner=Join-Path $temp 'animar-emanuelly.ps1'
  & $runner -Acao Catalogo -Parte Todas | Out-Null
  $argsPy=Get-Content -LiteralPath (Join-Path $temp 'args.json') -Raw | ConvertFrom-Json
  if(-not ($argsPy -contains 'catalogo') -or -not ($argsPy -contains 'Todas')){
    throw 'Catalogo das quatro partes nao chegou ao motor'
  }
  & $runner -Acao Planejar -Parte 3 | Out-Null
  $argsPy=Get-Content -LiteralPath (Join-Path $temp 'args.json') -Raw | ConvertFrom-Json
  if(-not ($argsPy -contains 'planejar') -or -not ($argsPy -contains '3')){
    throw 'Planejar Parte 3 nao foi encaminhado'
  }
  & $runner -Acao Planejar | Out-Null
  $argsPy=Get-Content -LiteralPath (Join-Path $temp 'args.json') -Raw | ConvertFrom-Json
  if(-not ($argsPy -contains 'planejar')){
    throw 'Planejamento nao encaminhado'
  }
  $src=Join-Path $temp 'fake-original.png'
  'fake image, mock launcher only' | Set-Content -LiteralPath $src
  & $runner -Acao Instalar -Tipo Jardim -Indice 4 -Arquivo $src | Out-Null
  $argsPy=Get-Content -LiteralPath (Join-Path $temp 'args.json') -Raw | ConvertFrom-Json
  if(-not ($argsPy -contains 'instalar') -or
     -not ($argsPy -contains 'Jardim') -or -not ($argsPy -contains '4') -or
     -not ($argsPy -contains '--arquivo')){
    throw 'Registro de imagem oficial incorreto'
  }
  & $runner -Acao InstalarLote -Pasta $temp | Out-Null
  $argsPy=Get-Content -LiteralPath (Join-Path $temp 'args.json') -Raw | ConvertFrom-Json
  if(-not ($argsPy -contains 'instalar-lote') -or -not ($argsPy -contains '--pasta')){
    throw 'InstalarLote nao recebeu pasta'
  }
  & $runner -Acao Preparar | Out-Null
  $argsPy=Get-Content -LiteralPath (Join-Path $temp 'args.json') -Raw | ConvertFrom-Json
  if(-not ($argsPy -contains 'props')){
    throw 'Compositor nao recebeu acao Preparar'
  }
  & $runner -Acao GerarImagens -Parte 2 -Recurso ovo-rachado -MaxChamadas 1 | Out-Null
  $argsPy=Get-Content -LiteralPath (Join-Path $temp 'args.json') -Raw | ConvertFrom-Json
  if(-not ($argsPy -contains 'gerar-imagens') -or
     -not ($argsPy -contains 'ovo-rachado') -or
     -not ($argsPy -contains '1')){
    throw 'GerarImagem obrigatoriamente seleciona recurso e limite'
  }
  & $runner -Acao Renderizar -Parte 4 -Refazer | Out-Null
  $argsPy=Get-Content -LiteralPath (Join-Path $temp 'args.json') -Raw | ConvertFrom-Json
  if(-not ($argsPy -contains '4') -or -not ($argsPy -contains 'renderizar') -or
     -not ($argsPy -contains '--refazer')){
    throw 'Renderizar nao encaminhou os argumentos'
  }
  $blocked=$false
  try{& $runner -Acao Planejar -Refazer | Out-Null}catch{$blocked=$true}
  if(-not $blocked){throw 'Planejar com Refazer deveria bloquear'}
  Write-Host '[OK] Kids camadas: Planejar/Instalar/InstalarLote/Preparar/Renderizar, zero IA e upload.' -ForegroundColor Green
}finally{
  Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
}
