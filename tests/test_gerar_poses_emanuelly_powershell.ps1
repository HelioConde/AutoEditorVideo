# Mock Windows launcher test; no proxy request, no generated media and no OAuth.
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$source=Join-Path (Split-Path -Parent $PSScriptRoot) 'gerar-poses-emanuelly.ps1'
$tokens=$null
$parseErrors=$null
[System.Management.Automation.Language.Parser]::ParseFile(
  $source,[ref]$tokens,[ref]$parseErrors
) | Out-Null
if($parseErrors.Count -gt 0){throw 'Sintaxe de gerar-poses-emanuelly.ps1 invalida.'}
$temp=Join-Path ([IO.Path]::GetTempPath()) ('emanuelly-poses-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path (Join-Path $temp 'scripts') -Force | Out-Null
try{
  Copy-Item -LiteralPath $source -Destination (Join-Path $temp 'gerar-poses-emanuelly.ps1')
  @'
from pathlib import Path
import json,sys
Path(__file__).resolve().parents[1].joinpath("registro.json").write_text(
    json.dumps(sys.argv[1:],ensure_ascii=False),encoding="utf8")
'@ | Set-Content -LiteralPath (Join-Path $temp 'scripts\gerar_poses_emanuelly_gpt_image_2.py') -Encoding UTF8
  $runner=Join-Path $temp 'gerar-poses-emanuelly.ps1'
  & $runner -Acao Planejar -Pose Todas | Out-Null
  $argsPy=Get-Content -LiteralPath (Join-Path $temp 'registro.json') -Raw | ConvertFrom-Json
  if(-not ($argsPy -contains 'planejar') -or -not ($argsPy -contains 'Todas')){
    throw 'Planejamento nao chegou ao motor.'
  }
  $blocked=$false
  try{& $runner -Acao Gerar -Pose ajoelhada -MaxChamadas 1 | Out-Null}catch{$blocked=$true}
  if(-not $blocked){throw 'Geracao com imagem privada ausente devia bloquear.'}
  $folder=Join-Path $temp 'assets\referencias-privadas'
  New-Item -ItemType Directory -Path $folder -Force | Out-Null
  'fake reference (the mock engine does not open it)' |
    Set-Content -LiteralPath (Join-Path $folder 'emanuelly-personagem-oficial.png')
  & $runner -Acao Gerar -Pose ajoelhada -MaxChamadas 1 | Out-Null
  $argsPy=Get-Content -LiteralPath (Join-Path $temp 'registro.json') -Raw | ConvertFrom-Json
  if(-not ($argsPy -contains 'gerar') -or -not ($argsPy -contains 'ajoelhada') -or
     -not ($argsPy -contains '--max-chamadas') -or -not ($argsPy -contains '1')){
    throw 'Gerar nao repassou pose e limite.'
  }
  $blocked=$false
  try{& $runner -Acao Planejar -Refazer | Out-Null}catch{$blocked=$true}
  if(-not $blocked){throw 'Planejar com Refazer devia falhar.'}
  $another=Join-Path $temp 'source.png'
  'fake input' | Set-Content -LiteralPath $another
  & $runner -Acao InstalarReferencia -Referencia $another -Refazer | Out-Null
  $argsPy=Get-Content -LiteralPath (Join-Path $temp 'registro.json') -Raw | ConvertFrom-Json
  if(-not ($argsPy -contains 'instalar-referencia') -or -not ($argsPy -contains '--refazer') -or
     -not ($argsPy -contains '--referencia')){
    throw 'InstalarReferencia nao repassou o caminho privado.'
  }
  Write-Host '[OK] Gerador de poses: comandos corretos, foto privada obrigatoria e sem upload.' -ForegroundColor Green
}finally{
  Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
}
