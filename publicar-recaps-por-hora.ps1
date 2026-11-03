# Teste por intervalos: Death Note episodio 2 agora, episodio 3 1h depois.
# Um unico processo local, com comprovantes do YouTube, retomada e sem duplicar.
[CmdletBinding()]
param(
    [switch]$Publicar,
    [ValidateRange(60,1440)][int]$IntervaloMinutos=60,
    [ValidateSet('public','private','unlisted')][string]$Privacidade='public',
    [ValidateSet('gpt-image-1.5','gpt-image-2')][string]$Modelo='gpt-image-1.5',
    [ValidateSet('equilibrado','vivo','ultrassutil')][string]$Perfil='equilibrado',
    [ValidateRange(0,180)][int]$MaxChamadas=45
)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$env:PYTHONUNBUFFERED='1'
$script=Join-Path $root 'scripts\publicar_recap_hourly.py'
if(-not(Test-Path -LiteralPath $script)){
    throw 'Script ausente. Execute git pull --ff-only origin main.'
}
$py=Join-Path $root '.venv\Scripts\python.exe'
if(-not(Test-Path -LiteralPath $py)){
    $python=Get-Command python -ErrorAction SilentlyContinue
    if(-not $python){throw 'Python nao encontrado. Instale Python 3.11 ou rode o criador de Shorts primeiro.'}
    $py=$python.Source
}
$argsList=@(
    $script,
    '--intervalo-minutos',[string]$IntervaloMinutos,
    '--privacidade',$Privacidade,
    '--modelo',$Modelo,
    '--perfil',$Perfil,
    '--max-chamadas',[string]$MaxChamadas
)
if($Publicar){$argsList+='--publicar'}
if($Publicar){
    Write-Host '[TESTE] Publicacao explicita autorizada: episodio 2 e depois episodio 3.' -ForegroundColor Cyan
    Write-Host "[INTERVALO] Pelo menos $IntervaloMinutos minutos entre uploads confirmados." -ForegroundColor Cyan
    Write-Host '[IMPORTANTE] Mantenha este PowerShell aberto e o computador ligado.' -ForegroundColor Yellow
}else{
    Write-Host '[PREVIA] Somente planejamento; nenhum upload ou gasto de IA.' -ForegroundColor Yellow
}
& $py @argsList
if($LASTEXITCODE -ne 0){
    throw 'Teste interrompido. Verifique o YouTube Studio e os logs antes de repetir.'
}
