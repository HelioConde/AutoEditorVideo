# Fofinhos - nove recursos canonicos com GPT Image 2 e continuidade de cenario.
# Duas etapas: tres bases aprovadas visualmente, depois seis novos angulos.
# Imagens e referencias privadas ficam apenas no Windows; zero upload.
[CmdletBinding()]
param(
  [ValidateSet('Planejar','Verificar','GerarBases','GerarAngulos','Abrir')]
  [string]$Acao='Planejar',
  [ValidateRange(0,100)][int]$MaxChamadas=0,
  [switch]$BasesAprovadas,
  [switch]$Refazer
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$script = Join-Path $root 'scripts\gerar_cenarios_fofinhos_gpt_image_2.py'
if (-not (Test-Path -LiteralPath $script -PathType Leaf)) {
  throw 'Motor de cenarios ausente. Atualize seu repositorio.'
}
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
  $cmd = Get-Command python -ErrorAction SilentlyContinue
  if (-not $cmd) { throw 'Python nao encontrado (.venv ou PATH).' }
  $python = $cmd.Source
}
$pasta = Join-Path $root 'assets\gerados\kids-emanuelly\cenarios-oficiais'
if ($Acao -eq 'Abrir') {
  if (-not (Test-Path -LiteralPath $pasta -PathType Container)) {
    throw 'Nenhum cenario gerado. Use GerarBases primeiro.'
  }
  Start-Process -FilePath $pasta
  return
}
if ($Refazer -and $Acao -notin @('GerarBases','GerarAngulos')) {
  throw '-Refazer somente com GerarBases ou GerarAngulos.'
}
if ($MaxChamadas -gt 0 -and $Acao -notin @('GerarBases','GerarAngulos')) {
  throw '-MaxChamadas somente com GerarBases ou GerarAngulos.'
}
if ($BasesAprovadas -and $Acao -ne 'GerarAngulos') {
  throw '-BasesAprovadas somente com GerarAngulos.'
}
$map = @{
  Planejar='planejar'; Verificar='verificar';
  GerarBases='bases'; GerarAngulos='angulos'
}
$argsPy = @($script,'--acao',$map[$Acao],'--max-chamadas',"$MaxChamadas")
if ($BasesAprovadas) { $argsPy += '--bases-aprovadas' }
if ($Refazer) { $argsPy += '--refazer' }
if ($Acao -in @('GerarBases','GerarAngulos')) {
  if ($Acao -eq 'GerarBases') {
    $source = Join-Path $root 'assets\referencias-privadas\emanuelly-solo.png'
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
      throw "Referencia oficial de estilo ausente: $source"
    }
    Write-Warning 'A referencia privada Emanuelly solo pode ser enviada ao Codex Proxy e ao provedor de imagem. O resultado sera um cenario SEM personagens.'
  }
  Write-Host "[GASTOS] Ate $MaxChamadas edicoes de imagem com gpt-image-2; nenhuma publicacao." -ForegroundColor Yellow
  if ($Acao -eq 'GerarAngulos') {
    Write-Host '[CENARIOS] Confirmacao: as tres bases foram revisadas e aprovadas por voce.' -ForegroundColor Yellow
  }
}
Write-Host "[FOFINHOS CENARIOS] $Acao | gpt-image-2 | Zero upload" -ForegroundColor Cyan
& $python @argsPy
if ($LASTEXITCODE -ne 0) {
  throw 'Geracao de cenarios interrompida. Cache pago preservado e nenhum upload feito.'
}
Write-Host '[FOFINHOS] Operacao local concluida, sem publicar.' -ForegroundColor Green
