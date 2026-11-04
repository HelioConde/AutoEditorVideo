# Teste dedicado da Narracao Acolhedora Kids.
# Gera audio pt-BR com pausas REAIS + MP4 local; NAO faz login/upload.
[CmdletBinding()]
param(
  [ValidateSet('Planejar','Voz','Renderizar','Testar','VerificarVideo','Abrir')]
  [string]$Acao='Planejar',
  [switch]$Refazer
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

$root=$PSScriptRoot
$episode='kids-001-estrela-azul'
$motor=Join-Path $root 'piloto-canais-v3.ps1'
$video=Join-Path $root 'assets\gerados\piloto-canais-v3\kids\kids-001-estrela-azul\final.mp4'
$manifest=Join-Path $root 'conteudos\piloto-games-kids-3x2-v3.json'

if(-not(Test-Path -LiteralPath $motor -PathType Leaf)){
  throw 'Motor Kids ausente. Execute git pull --ff-only origin main.'
}
if(-not(Test-Path -LiteralPath $manifest -PathType Leaf)){
  throw 'Manifesto Kids ausente. Execute git pull --ff-only origin main.'
}
if($Refazer -and $Acao -notin @('Voz','Renderizar','Testar')){
  throw '-Refazer somente em Voz, Renderizar ou Testar.'
}

function Executar-Etapa([string]$Etapa,[bool]$Forcar) {
  $argumentos=@{Acao=$Etapa;Canal='kids';Id=$episode}
  if($Forcar){$argumentos.Refazer=$true}
  & $motor @argumentos
  if(-not $?){
    throw "Falhou a etapa $Etapa. Nenhum video foi publicado."
  }
}
Write-Host "[KIDS ACOLHEDOR PT-BR] $Acao | $episode | ZERO upload" -ForegroundColor Cyan

switch($Acao){
  'Planejar' {
    Executar-Etapa 'validar' $false
    Executar-Etapa 'preparar' $false
    Write-Host '[KIDS] 13 falas planejadas; perguntas com pausa >=1,5s.' -ForegroundColor Green
  }
  'Voz' {
    Executar-Etapa 'voz' ([bool]$Refazer)
  }
  'Renderizar' {
    Executar-Etapa 'renderizar' ([bool]$Refazer)
  }
  'VerificarVideo' {
    Executar-Etapa 'verificar-video' $false
  }
  'Testar' {
    # A voz antiga de 25s nao pode ser reutilizada: roteiro e pausas mudaram.
    # O motor guarda backup antes de substituir voz/MP4, e reaproveita
    # segmentos TTS cacheados quando correspondem ao texto e voz.
    Executar-Etapa 'validar' $false
    Executar-Etapa 'voz' $true
    Executar-Etapa 'renderizar' $true
    Executar-Etapa 'verificar-video' $false
    Write-Host '[KIDS] MP4 de teste gerado; revise o ritmo no video completo.' -ForegroundColor Green
  }
  'Abrir' {
    if(-not(Test-Path -LiteralPath $video -PathType Leaf)){
      throw 'MP4 ausente. Execute .\kids-narracao-acolhedora.ps1 -Acao Testar.'
    }
    Start-Process -FilePath $video
  }
}
if($Acao -in @('Testar','Renderizar','VerificarVideo')){
  Write-Host "[KIDS] Arquivo esperado: $video" -ForegroundColor Cyan
  Write-Host 'Os resultados da narracao sao locais. Nenhum upload, criacao de canal ou publicacao.' -ForegroundColor Yellow
}
