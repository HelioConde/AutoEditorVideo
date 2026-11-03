# Primeiro teste local de narracao VoiceStudio. Edge TTS continua como motor padrao.
[CmdletBinding()]
param(
    [string]$Id='401-jujutsu-kaisen-ep01',
    [string]$ModeloVoiceStudio='tts-1',
    [string]$PerfilVoiceStudio='default',
    [switch]$CompararEdge,
    [switch]$AmostraCurta
)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$py=Join-Path $root '.venv\Scripts\python.exe'
if(-not(Test-Path $py)){throw 'Ambiente .venv ausente. Configure o AutoEditorVideo primeiro.'}
$priorModel=$env:OTAKU_VOICESTUDIO_MODEL
$priorVoice=$env:OTAKU_VOICESTUDIO_VOICE
try {
    $env:OTAKU_VOICESTUDIO_MODEL=$ModeloVoiceStudio
    $env:OTAKU_VOICESTUDIO_VOICE=$PerfilVoiceStudio
    $params=@((Join-Path $root 'scripts\testar_vozes.py'),'--id',$Id)
    if($CompararEdge){$params+='--comparar-edge'}
    if($AmostraCurta){$params+='--amostra-curta'}
    & $py @params
    if($LASTEXITCODE -ne 0){throw 'Teste de voz nao passou; nenhum video foi enviado.'}
} finally {
    $env:OTAKU_VOICESTUDIO_MODEL=$priorModel
    $env:OTAKU_VOICESTUDIO_VOICE=$priorVoice
}
