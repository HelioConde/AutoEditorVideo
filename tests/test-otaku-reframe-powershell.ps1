# Smoke test offline: sintaxe + bloqueios de cota/revisao do launcher.
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$launcher=Join-Path $root 'gerar-otaku-reframe.ps1'
$tokens=$null
$errors=$null
[System.Management.Automation.Language.Parser]::ParseFile(
  $launcher,[ref]$tokens,[ref]$errors) | Out-Null
if($errors.Count -gt 0){
  throw ('PowerShell: erro de sintaxe: ' + ($errors | ForEach-Object {$_.Message} | Out-String))
}

function Expect-Blocked {
  param([object[]]$Options,[string]$ExpectedMessage)
  $blocked=$false
  try {
    & $launcher @Options | Out-Null
  } catch {
    if($_.Exception.Message -notmatch $ExpectedMessage){throw}
    $blocked=$true
  }
  if(-not $blocked){throw "Comando perigoso nao foi bloqueado: $($Options -join ' ')"}
}
Expect-Blocked @('-Acao','GerarImagens','-MaxChamadas','0') 'orcamento explicito'
Expect-Blocked @('-Acao','Renderizar') 'ConfirmarRevisaoVisual'
Expect-Blocked @('-Acao','Preparar','-MaxChamadas','1') 'MaxChamadas so pode'
Expect-Blocked @('-Acao','Preparar','-ConfirmarRevisaoVisual') 'so pode ser usado'
Write-Host '[OK] Launcher PowerShell: sintaxe e bloqueios basicos.'
