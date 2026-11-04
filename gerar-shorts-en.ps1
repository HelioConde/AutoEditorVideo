# Arquivo Otaku EN: reaproveita imagens e animacoes, troca narracao e legendas.
[CmdletBinding()]
param(
    [ValidateSet('planejar','voz','capa','renderizar')][string]$Acao='planejar',
    [string]$Id='',
    [string]$Manifesto='',
    [ValidateSet('gpt-image-1.5','gpt-image-2')][string]$Modelo='gpt-image-1.5',
    [ValidateSet('equilibrado','vivo','ultrassutil')][string]$Perfil='equilibrado',
    [switch]$Refazer
)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$py=Join-Path $root '.venv\Scripts\python.exe'
$program=Join-Path $root 'scripts\renderizar_shorts_en.py'
if(-not(Test-Path $py)){throw 'Python .venv ausente. Execute scripts\instalar-windows.ps1'}
if(-not(Test-Path $program)){throw 'Atualize o repositorio: git pull --ff-only origin main'}
$argsForPython=@($program,'--acao',$Acao,'--modelo',$Modelo,'--perfil',$Perfil)
if($Id){$argsForPython+=@('--id',$Id)}
if($Manifesto){$argsForPython+=@('--manifesto',(if([IO.Path]::IsPathRooted($Manifesto)){$Manifesto}else{Join-Path $root $Manifesto}))}
if($Refazer){$argsForPython+='--refazer'}
& $py @argsForPython
if($LASTEXITCODE -ne 0){throw "Processo EN falhou (codigo $LASTEXITCODE). O material PT foi preservado."}
