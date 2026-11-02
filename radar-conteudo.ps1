# Arquivo Otaku 0.8 — radar offline, SEM API e SEM upload.
[CmdletBinding()]
param([int]$Quantidade=8,[string]$Id='', [string]$Pautas='',[string]$Metricas='')
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$py=Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $py)){ throw 'Python .venv nao encontrado. Instale a versao principal do kit.' }
$cmd=@((Join-Path $root 'scripts\radar_editorial.py'),'--quantidade',[string]$Quantidade)
if ($Id){$cmd+=@('--id',$Id)}
if ($Pautas){$cmd+=@('--pautas',$Pautas)}
if ($Metricas){$cmd+=@('--metricas',$Metricas)}
& $py @cmd
if($LASTEXITCODE -ne 0){throw 'Falha no radar editorial; confira a mensagem acima.'}
