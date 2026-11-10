# Repara descricoes e tenta aplicar as capas ja aprovadas aos Shorts publicados.
# Nao faz upload de MP4 nem altera privacidade.
[CmdletBinding()]
param(
  [switch]$Aplicar,
  [switch]$SemCapas,
  [ValidateSet('equilibrado','vivo','ultrassutil')][string]$PerfilPersonagens='equilibrado'
)
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$py=Join-Path $root '.venv\Scripts\python.exe'
$script=Join-Path $root 'scripts\reparar_shorts_publicados.py'
if(-not(Test-Path $py)){throw 'Ambiente Python ausente; execute scripts\instalar-windows.ps1'}
if(-not(Test-Path $script)){throw 'Script de reparo ausente; execute git pull origin main'}
$argsList=@($script,'--perfil-personagens',$PerfilPersonagens)
if($SemCapas){$argsList+='--sem-capas'}
if($Aplicar){
  $oauth=Join-Path $root '.secrets\youtube-oauth-client.json'
  if(-not(Test-Path $oauth)){throw 'OAuth do YouTube ausente em .secrets\youtube-oauth-client.json'}
  $argsList+='--aplicar'
}
& $py @argsList
if($LASTEXITCODE -ne 0){throw "Reparo terminou com pendencias (codigo $LASTEXITCODE). Veja o relatorio local."}
