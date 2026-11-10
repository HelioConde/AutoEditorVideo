# Interface local do Arquivo Otaku. Nao requer Node ou servico em nuvem.
[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$python=Join-Path $root '.venv\Scripts\python.exe'
if(-not (Test-Path $python)){
    $cmd=Get-Command python -ErrorAction SilentlyContinue
    if(-not $cmd){throw 'Python nao encontrado. Instale Python 3.11 ou uv.'}
    $python=$cmd.Source
}
Write-Host '[STUDIO] Abrindo interface local. Mantenha esta janela aberta.'
& $python (Join-Path $root 'scripts\shorts_studio.py')
if($LASTEXITCODE -ne 0){throw 'O Shorts Studio terminou com erro.'}
