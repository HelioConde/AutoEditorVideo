# 8 ciclos de EP -> Curiosidade -> Voce lembra, agendamento nativo YouTube.
# Somente -Agendar envia arquivos e consome chamadas de imagem.
[CmdletBinding()]
param(
  [switch]$Agendar,
  [string]$DataInicio='',
  [ValidatePattern('^([01]\d|2[0-3]):[0-5]\d$')][string]$HoraInicio='09:00',
  [ValidateRange(60,10080)][int]$IntervaloMinutos=60,
  [ValidateRange(1,24)][int]$Limite=24,
  [ValidateSet('gpt-image-1.5','gpt-image-2')][string]$Modelo='gpt-image-1.5',
  [ValidateSet('equilibrado','vivo','ultrassutil')][string]$Perfil='equilibrado',
  [ValidateRange(0,180)][int]$MaxChamadas=45
)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$env:PYTHONUNBUFFERED='1'
$program=Join-Path $root 'scripts\agendar_24_shorts.py'
if(-not(Test-Path -LiteralPath $program)){
  throw 'Arquivo de agendamento ausente. Execute git pull --ff-only origin main.'
}
$py=Join-Path $root '.venv\Scripts\python.exe'
if(-not(Test-Path -LiteralPath $py)){
  $python=Get-Command python -ErrorAction SilentlyContinue
  if(-not $python){throw 'Instale Python ou execute criar-publicar-short.ps1 primeiro.'}
  $py=$python.Source
}
$argsPython=@($program,'--hora-inicio',$HoraInicio,
  '--intervalo-minutos',[string]$IntervaloMinutos,
  '--limite',[string]$Limite,'--modelo',$Modelo,'--perfil',$Perfil,
  '--max-chamadas',[string]$MaxChamadas)
if($DataInicio){$argsPython+=@('--data-inicio',$DataInicio)}
if($Agendar){
  $argsPython+='--agendar'
  Write-Host '[AGENDAR YOUTUBE] Voce autorizou geracao de IA, uploads privados e 24 horarios futuros.' -ForegroundColor Cyan
  Write-Host "[COTA] Ate $MaxChamadas chamadas de imagens por video; reusa cache quando disponivel." -ForegroundColor Yellow
  Write-Host '[ATENCAO] Nao feche este PowerShell enquanto estiver produzindo e enviando os MP4s.' -ForegroundColor Yellow
  Write-Host '[DEPOIS] Ao confirmar cada agendamento, o YouTube publica sozinho no horario.' -ForegroundColor Green
}else{
  Write-Host '[PLANEJAMENTO] Nenhum upload, agendamento ou gasto de imagens.' -ForegroundColor Green
}
& $py @argsPython
if($LASTEXITCODE -ne 0){throw 'Lote interrompido. Confira logs e YouTube Studio antes de retomar.'}
