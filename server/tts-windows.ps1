param(
  [Parameter(Mandatory=$true)][string]$TextFile,
  [Parameter(Mandatory=$true)][string]$OutputFile
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
  $voice = $synth.GetInstalledVoices() | Where-Object {
    $_.VoiceInfo.Culture.Name -match '^pt(-BR|-PT)?$'
  } | Select-Object -First 1
  if (-not $voice) { throw 'Nenhuma voz em português disponível. Instale uma voz pt-BR nas configurações de fala do Windows.' }
  $synth.SelectVoice($voice.VoiceInfo.Name)
  $synth.Rate = 0
  $synth.SetOutputToWaveFile($OutputFile)
  $content = [IO.File]::ReadAllText($TextFile, [Text.Encoding]::UTF8)
  $synth.Speak($content)
  $synth.SetOutputToNull()
} finally { $synth.Dispose() }
