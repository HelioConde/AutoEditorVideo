# Teste hermetico do launcher Kids, sem TTS, sem Remotion e sem uploads.
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$source=Join-Path $root 'kids-narracao-acolhedora.ps1'
$tokens=$null
$errors=$null
[System.Management.Automation.Language.Parser]::ParseFile(
  $source,[ref]$tokens,[ref]$errors
) | Out-Null
if($errors.Count -gt 0){
  $errors | ForEach-Object {Write-Error $_.ToString()}
  throw 'Sintaxe do PowerShell Kids invalida'
}
$temp=Join-Path ([IO.Path]::GetTempPath()) ('kids-acolhedora-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temp -Force | Out-Null
try{
  Copy-Item $source $temp
  New-Item -ItemType Directory -Path (Join-Path $temp 'conteudos') -Force | Out-Null
  '{}' | Set-Content -LiteralPath (Join-Path $temp 'conteudos\piloto-games-kids-3x2-v3.json')
  @'
[CmdletBinding()]
param(
 [string]$Acao,[string]$Canal,[string]$Id,[switch]$Refazer
)
@{acao=$Acao;canal=$Canal;id=$Id;refazer=[bool]$Refazer} |
 ConvertTo-Json -Compress |
 Add-Content -LiteralPath (Join-Path $PSScriptRoot 'registro.ndjson')
'@ | Set-Content -LiteralPath (Join-Path $temp 'piloto-canais-v3.ps1') -Encoding UTF8

  & (Join-Path $temp 'kids-narracao-acolhedora.ps1') -Acao Planejar | Out-Null
  $rows=Get-Content -LiteralPath (Join-Path $temp 'registro.ndjson') | ForEach-Object {$_|ConvertFrom-Json}
  if($rows.Count -ne 2 -or $rows[0].acao -ne 'validar' -or
     $rows[1].acao -ne 'preparar'){
    throw 'Planejar deveria executar validacao + pacotes offline'
  }
  Remove-Item -LiteralPath (Join-Path $temp 'registro.ndjson')
  & (Join-Path $temp 'kids-narracao-acolhedora.ps1') -Acao Testar | Out-Null
  $rows=Get-Content -LiteralPath (Join-Path $temp 'registro.ndjson') | ForEach-Object {$_|ConvertFrom-Json}
  if($rows.Count -ne 4){throw 'Teste deveria validar, criar voz, renderizar e verificar MP4'}
  if(($rows|ForEach-Object {$_.acao}) -join ',' -ne 'validar,voz,renderizar,verificar-video'){
    throw 'Ordem do teste Kids incorreta'
  }
  if($rows[1].refazer -ne $true -or $rows[2].refazer -ne $true){
    throw 'Voz e render antigo devem ser substituidos com backup'
  }
  foreach($row in $rows){
    if($row.canal -ne 'kids' -or $row.id -ne 'kids-001-estrela-azul'){
      throw 'Nao e permitido enviar pedido para outro canal/episodio'
    }
  }
  Write-Host '[OK] PowerShell Kids - ordens seguras e sem upload real.' -ForegroundColor Green
}finally{
  Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
}
