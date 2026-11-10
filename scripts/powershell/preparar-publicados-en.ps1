# Prepara somente a fila EN de Shorts que estao publicos no canal BR.
# Nao gera IA, MP4, voz nem realiza upload. Preserva todos os caches.
[CmdletBinding()]
param(
  [ValidateSet('Resumo','Preparar','Verificar')][string]$Acao='Resumo',
  [string[]]$Id=@(),
  [string]$Saida='assets\gerados\otaku-br-publicados-en-v3.json'
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$py=Join-Path $root '.venv\Scripts\python.exe'
$program=Join-Path $root 'scripts\preparar_publicados_en_v3.py'
if(-not(Test-Path -LiteralPath $py -PathType Leaf)){
  throw 'Ambiente .venv ausente. Configure o Python local antes de preparar a fila EN.'
}
if(-not(Test-Path -LiteralPath $program -PathType Leaf)){
  throw 'Preparador Otaku Reframe V3 ausente. Atualize o projeto pelo GitHub.'
}
$destino=if([IO.Path]::IsPathRooted($Saida)){$Saida}else{Join-Path $root $Saida}
$action=$Acao.ToLowerInvariant()
$argsList=@($program,'--acao',$action,'--saida',$destino)
foreach($episode in $Id){
  if([string]::IsNullOrWhiteSpace($episode)){continue}
  $argsList+=@('--id',$episode)
}
& $py @argsList
if($LASTEXITCODE -ne 0){
  throw "Fila EN V3 bloqueada (codigo $LASTEXITCODE). Nenhum upload ou MP4 modificado."
}
Write-Host '[OTAKU EN V3] Preparacao offline concluida. Nenhum Short foi enviado.' -ForegroundColor Green
