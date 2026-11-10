# Arquivo Otaku v0.7 — plano de roteiro local sem consumo de APIs.
[CmdletBinding()]
param([string]$Plano='')
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$py=Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { throw 'Python do projeto nao encontrado (.venv). Instale o kit primeiro.' }
$argsForPython=@((Join-Path $root 'scripts\planejador_editorial.py'))
if($Plano){$argsForPython+=@('--plano',$Plano)}
& $py @argsForPython
if($LASTEXITCODE -ne 0){throw 'Falha ao preparar plano editorial'}
