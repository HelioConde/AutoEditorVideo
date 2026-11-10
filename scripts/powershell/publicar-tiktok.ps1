# Arquivo Otaku / TikTok API oficial. Nenhum upload por padrao.
[CmdletBinding()]
param(
    [ValidateSet('diagnostico','conectar','preparar','enviar','status')][string]$Acao='diagnostico',
    [ValidateSet('rascunho','direto')][string]$Modo='rascunho',
    [ValidateSet('SELF_ONLY','PUBLIC_TO_EVERYONE','MUTUAL_FOLLOW_FRIENDS','FOLLOWER_OF_CREATOR')]
    [string]$Privacidade='SELF_ONLY',
    [ValidateSet('equilibrado','vivo','ultrassutil')][string]$Perfil='equilibrado',
    [ValidateRange(1,5)][int]$Limite=1,
    [string]$Id='',
    [switch]$ConfirmarEnvio
)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$py=Join-Path $root '.venv\Scripts\python.exe'
$program=Join-Path $root 'scripts\publicar_tiktok.py'
if(-not(Test-Path $program)){throw 'Publicador TikTok ausente. Execute git pull --ff-only origin main.'}
if(-not(Test-Path $py)){throw 'Ambiente Python ausente. Execute scripts\instalar-windows.ps1.'}
& $py -c "import requests"
if($LASTEXITCODE -ne 0){
    throw 'Biblioteca requests ausente. Execute: uv pip install --python .\.venv\Scripts\python.exe -r .\requirements-master.txt'
}
$argsList=@($program,'--acao',$Acao,'--modo',$Modo,'--privacidade',$Privacidade,
    '--perfil',$Perfil,'--limite',[string]$Limite)
if($Id){$argsList+=@('--id',$Id)}
if($ConfirmarEnvio){$argsList+='--confirmar'}
& $py @argsList
if($LASTEXITCODE -ne 0){throw "Operacao TikTok interrompida (codigo $LASTEXITCODE). Nenhum upload adicional sera tentado."}
