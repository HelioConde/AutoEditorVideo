# Teste isolado Windows do launcher; nenhum modelo de imagem, TTS ou upload.
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$source=Join-Path (Split-Path -Parent $PSScriptRoot) 'gerar-historia-kids.ps1'
$tokens=$null; $errors=$null
[System.Management.Automation.Language.Parser]::ParseFile(
  $source,[ref]$tokens,[ref]$errors
) | Out-Null
if($errors.Count -gt 0){throw 'PowerShell serie Kids tem erros sintaticos'}

$temp=Join-Path ([IO.Path]::GetTempPath()) ('serie-kids-test-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path (Join-Path $temp 'scripts') -Force | Out-Null
try{
  # Novo motor separado: os testes usam stub e nao sintetizam voz real.
  Copy-Item -LiteralPath (Join-Path (Split-Path -Parent $PSScriptRoot) 'fofinhos-ep01.ps1') -Destination (Join-Path $temp 'fofinhos-ep01.ps1')
  @'
import sys,json
from pathlib import Path
Path(__file__).resolve().parents[1].joinpath("args-fofinhos.json").write_text(
  json.dumps(sys.argv[1:]),encoding="utf8")
'@ | Set-Content -LiteralPath (Join-Path $temp 'scripts\fofinhos_ep01_render.py') -Encoding UTF8
  # Stub do compositor por camadas da Parte 2, SEM imagens nem render.
  @'
[CmdletBinding()]
param([string]$Acao,[string]$Parte,[int]$MaxChamadas,[switch]$Refazer)
@{acao=$Acao;parte=$Parte;chamadas=$MaxChamadas;refazer=$Refazer.IsPresent} |
  ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'args-camadas.json') -Encoding UTF8
'@ | Set-Content -LiteralPath (Join-Path $temp 'animar-emanuelly.ps1') -Encoding UTF8
  Copy-Item -LiteralPath $source -Destination (Join-Path $temp 'gerar-historia-kids.ps1')
  @'
import json,sys
from pathlib import Path
Path(__file__).resolve().parent.parent.joinpath("registro.json").write_text(
    json.dumps(sys.argv[1:], ensure_ascii=False),encoding="utf8")
'@ | Set-Content -LiteralPath (Join-Path $temp 'scripts\serie_kids_emanuelly_v1.py') -Encoding UTF8
  $wrapper=Join-Path $temp 'gerar-historia-kids.ps1'
  & $wrapper -Acao Planejar -Parte 1 | Out-Null
  $argsNew=Get-Content -LiteralPath (Join-Path $temp 'args-fofinhos.json') -Raw | ConvertFrom-Json
  if(-not ($argsNew -contains 'planejar') -or ($argsNew -contains 'renderizar')){
    throw 'Planejar Parte 1 precisa usar o roteiro aprovado Fofinhos'
  }
  & $wrapper -Acao Voz -Parte 1 | Out-Null
  $argsNew=Get-Content -LiteralPath (Join-Path $temp 'args-fofinhos.json') -Raw | ConvertFrom-Json
  if(-not ($argsNew -contains 'voz')){
    throw 'Voz Parte 1 precisa usar a narracao canônica de 15 cenas'
  }
  & $wrapper -Acao Planejar -Parte 2 | Out-Null
  $camadas=Get-Content -LiteralPath (Join-Path $temp 'args-camadas.json') -Raw | ConvertFrom-Json
  if($camadas.acao -ne 'Planejar' -or $camadas.parte -ne '2'){
    throw 'Planejar Parte 2 deve usar storyboard sem limite fixo de cenas'
  }
  & $wrapper -Acao Renderizar -Parte 2 | Out-Null
  $camadas=Get-Content -LiteralPath (Join-Path $temp 'args-camadas.json') -Raw | ConvertFrom-Json
  if($camadas.acao -ne 'Renderizar' -or $camadas.parte -ne '2'){
    throw 'Renderizar Parte 2 deve usar camadas, nao 10 quadros antigos'
  }
  & $wrapper -Acao Voz -Parte 2 | Out-Null
  $argsPy=Get-Content -LiteralPath (Join-Path $temp 'registro.json') -Raw | ConvertFrom-Json
  if($argsPy[0] -ne '--acao' -or $argsPy[1] -ne 'voz' -or
     -not ($argsPy -contains '--parte') -or -not ($argsPy -contains '2')){
    throw 'Voz Parte 2 usa motor de narracao, sem gerar quadros antigos'
  }
  $blocked=$false
  try{& $wrapper -Acao Gerar -Parte 1 -MaxChamadas 9 | Out-Null}catch{$blocked=$true}
  if(-not $blocked){throw 'Foto ausente deveria bloquear a geracao Kids'}
  New-Item -ItemType Directory -Path (Join-Path $temp 'assets\referencias-privadas') -Force | Out-Null
  'fake_private_image_for_wrapper_only' |
    Set-Content -LiteralPath (Join-Path $temp 'assets\referencias-privadas\emanuelly-elenco.png')
  & $wrapper -Acao Gerar -Parte 1 -MaxChamadas 9 | Out-Null
  $argsPy=Get-Content -LiteralPath (Join-Path $temp 'registro.json') -Raw | ConvertFrom-Json
  if(-not ($argsPy -contains 'testar') -or -not ($argsPy -contains '--max-chamadas') -or
     -not ($argsPy -contains '9') -or -not ($argsPy -contains '1')){
    throw 'Gerar deve ser um unico Short com limite explicito de imagens'
  }
  & $wrapper -Acao PrepararReferencias -Parte Todas -MaxChamadas 2 | Out-Null
  $argsPy=Get-Content -LiteralPath (Join-Path $temp 'registro.json') -Raw | ConvertFrom-Json
  if(-not ($argsPy -contains 'preparar-referencias') -or
     -not ($argsPy -contains '--modelo') -or -not ($argsPy -contains 'gpt-image-2')){
    throw 'PrepararReferencias deve usar o gpt-image-2'
  }
  & $wrapper -Acao Imagens -Parte Todas -MaxChamadas 0 | Out-Null
  $argsPy=Get-Content -LiteralPath (Join-Path $temp 'registro.json') -Raw | ConvertFrom-Json
  if($argsPy -contains '--parte'){
    throw 'Parte Todas deve encaminhar o lote intencionalmente'
  }
  $blocked=$false
  try{
    & $wrapper -Acao Gerar -Parte 1 -Referencia 'C:\foto.png' -MaxChamadas 9 | Out-Null
  }catch{$blocked=$true}
  if(-not $blocked){throw 'Nao permitir misturar nova referencia sem instala-la primeiro'}
  Write-Host '[OK] PowerShell Emanuelly - 4 Shorts roteados, foto privada, limite IA e zero upload.' -ForegroundColor Green
}finally{
  Remove-Item -LiteralPath $temp -Force -Recurse -ErrorAction SilentlyContinue
}
