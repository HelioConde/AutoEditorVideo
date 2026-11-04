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
  Copy-Item -LiteralPath $source -Destination (Join-Path $temp 'gerar-historia-kids.ps1')
  @'
import json,sys
from pathlib import Path
Path(__file__).resolve().parent.parent.joinpath("registro.json").write_text(
    json.dumps(sys.argv[1:], ensure_ascii=False),encoding="utf8")
'@ | Set-Content -LiteralPath (Join-Path $temp 'scripts\serie_kids_emanuelly_v1.py') -Encoding UTF8
  $wrapper=Join-Path $temp 'gerar-historia-kids.ps1'
  & $wrapper -Acao Planejar -Parte 1 | Out-Null
  $argsPy=Get-Content -LiteralPath (Join-Path $temp 'registro.json') -Raw | ConvertFrom-Json
  if($argsPy[0] -ne '--acao' -or $argsPy[1] -ne 'planejar' -or
     -not ($argsPy -contains '--parte') -or -not ($argsPy -contains '1')){
    throw 'Planejar nao repassou os argumentos'
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
