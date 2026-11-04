# Publica apenas no segundo canal YouTube, depois de conferir o Channel ID.
[CmdletBinding()]
param(
    [ValidateSet('verificar','conectar','enviar')][string]$Acao='verificar',
    [string]$Id='',
    [string]$Manifesto='',
    [ValidateSet('equilibrado','vivo','ultrassutil')][string]$Perfil='equilibrado',
    [ValidateSet('private','unlisted','public')][string]$Privacidade='private',
    [ValidateRange(1,5)][int]$Limite=1,
    [switch]$ConfirmarEnvio
)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$py=Join-Path $root '.venv\Scripts\python.exe'
$program=Join-Path $root 'scripts\publicar_shorts_en.py'
if(-not(Test-Path $py)){throw 'Python .venv ausente: execute scripts\instalar-windows.ps1'}
if(-not(Test-Path $program)){throw 'Script de publicacao EN ausente: git pull --ff-only origin main'}
$argsList=@($program,'--acao',$Acao,'--perfil',$Perfil,'--privacidade',$Privacidade,
           '--limite',[string]$Limite)
if($Id){$argsList+=@('--id',$Id)}
if($Manifesto){$manifestPath=if([IO.Path]::IsPathRooted($Manifesto)){$Manifesto}else{Join-Path $root $Manifesto};$argsList+=@('--manifesto',$manifestPath)}
if($ConfirmarEnvio){$argsList+='--confirmar'}
& $py @argsList
if($LASTEXITCODE -ne 0){throw "Publicacao EN interrompida (codigo $LASTEXITCODE); nenhuma nova tentativa automatica."}
