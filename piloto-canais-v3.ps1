# Criar 3 Shorts iniciais PT-BR para cada canal (Games / Kids).
# NAO conecta OAuth, NAO cria canais e NAO publica videos.
[CmdletBinding()]
param(
  [ValidateSet('validar','preparar','inspecionar','verificar-video','voz','renderizar')]
  [string]$Acao='validar',
  [ValidateSet('ambos','games','kids')][string]$Canal='ambos',
  [string]$Id='',
  [switch]$Refazer
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$python=Join-Path $root '.venv\Scripts\python.exe'
if(-not(Test-Path -LiteralPath $python -PathType Leaf)){
  throw 'Ambiente Python .venv nao encontrado; configure o projeto antes de produzir.'
}
if($Acao -in @('voz','renderizar')){
  if($Canal -eq 'ambos' -or [string]::IsNullOrWhiteSpace($Id)){
    throw 'Voz/renderizacao exigem -Canal games|kids e -Id especifico. Nunca produzir lote sem selecao.'
  }
  $program=Join-Path $root 'scripts\produzir_piloto_canais_v3.py'
  $arguments=@($program,'--acao',$Acao,'--canal',$Canal,'--id',$Id)
  if($Refazer){$arguments+='--refazer'}
}else{
  $program=Join-Path $root 'scripts\piloto_canais_3x2_v3.py'
  $arguments=@($program,'--acao',$Acao,'--canal',$Canal)
  if($Id){$arguments+=@('--id',$Id)}
  if($Refazer){throw '-Refazer e aceito apenas para voz ou renderizar'}
}
if(-not(Test-Path -LiteralPath $program -PathType Leaf)){
  throw "Script nao encontrado: $program"
}
& $python @arguments
if($LASTEXITCODE -ne 0){
  throw "Piloto 3x2 interrompido (codigo $LASTEXITCODE). Nenhum upload foi realizado."
}
Write-Host '[PILOTO 3x2] Etapa local concluida. Zero publicacoes automaticas.' -ForegroundColor Green
