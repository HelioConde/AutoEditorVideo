# Teste REAL do Short PT-BR com os scripts oficiais AutoEditorVideo.
# Nunca usa vidIQ Compose, FFmpeg isolado, imagens vetoriais substitutas ou upload.
# A pasta assets/gerados/shorts-animados e privada/local.
[CmdletBinding()]
param(
  [ValidateSet('Planejar', 'Produzir', 'Validar')]
  [string]$Acao = 'Planejar',
  [ValidatePattern('^[0-9]{4}-[a-z0-9-]+$')]
  [string]$Id = '5008-firefly-wedding',
  [ValidateSet('gpt-image-1.5', 'gpt-image-2')]
  [string]$Modelo = 'gpt-image-2',
  [ValidateRange(0, 60)]
  [int]$MaxChamadas = 0,
  [switch]$ConfirmarCotaImagem
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$main = Join-Path $root 'criar-publicar-short.ps1'
$plan = Join-Path $root 'scripts\master_scenes.py'
$py = Join-Path $root '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $main -PathType Leaf)) {
  throw 'Script oficial criar-publicar-short.ps1 ausente. Atualize o projeto.'
}
if (-not (Test-Path -LiteralPath $plan -PathType Leaf)) {
  throw 'Motor master_scenes.py ausente. Atualize o projeto.'
}
if (-not (Test-Path -LiteralPath $py -PathType Leaf)) {
  throw 'Python do projeto ausente. Configure a .venv primeiro; nao use voz/arte de outro programa.'
}

$folder = Join-Path $root ('assets\gerados\shorts-animados\' + $Id)
$video = Join-Path $folder ($Id + '-master-multicenas-personagens-v3-equilibrado.mp4')
$cover = Join-Path $folder ($Id + '-master-capa.jpg')

if ($Acao -eq 'Planejar') {
  Write-Host '[BR REAL] Consulta do cache/roteiro oficial, SEM pedidos de IA nem upload.'
  & $py $plan --id $Id --todas-cenas --modelo $Modelo --max-chamadas 0 --diagnosticar-cache
  if ($LASTEXITCODE -ne 0) { throw 'Planejamento oficial falhou; nao executar geracao.' }
  Write-Host '[BR REAL] Planejamento concluido. Use -Acao Produzir com orcamento autorizado.'
  exit 0
}

if ($Acao -eq 'Validar') {
  if (-not (Test-Path -LiteralPath $video -PathType Leaf)) {
    throw ('MP4 produzido pelo AutoEditorVideo nao encontrado: ' + $video)
  }
  & $main -Id $Id -Modelo $Modelo -Perfil equilibrado -MaxChamadas 0 -SomenteValidar
  if ($LASTEXITCODE -ne 0) { throw 'QA do AutoEditorVideo falhou; nao publicar.' }
  Write-Host ('[BR REAL] MP4 existente e validado: ' + $video)
  exit 0
}

if ($MaxChamadas -gt 0 -and -not $ConfirmarCotaImagem.IsPresent) {
  throw 'Antes de produzir com chamadas IA, repita com -ConfirmarCotaImagem. O limite indica chamadas, nao preco garantido.'
}
if ($ConfirmarCotaImagem.IsPresent -and $MaxChamadas -eq 0) {
  Write-Host '[BR REAL] Modo cache: orcamento 0, nenhuma geracao paga autorizada.'
}
if (Test-Path -LiteralPath $video -PathType Leaf) {
  Write-Host '[BR REAL] MP4 ja existe. O motor oficial pode reutilizar cache e NAO recebe -Refazer.'
}
Write-Host ('[BR REAL] Produzindo ' + $Id + ' | modelo ' + $Modelo + ' | orcamento maximo ' + $MaxChamadas)
Write-Host '[BR REAL] Motor oficial: criar-publicar-short.ps1 -> fluxo_unico_short.py -> master_scenes.py -> renderizar_master_remotion.py'
Write-Host '[BR REAL] Sem -Publicar: NENHUM upload do YouTube sera realizado.'
& $main -Id $Id -Modelo $Modelo -VozMotor edge -Perfil equilibrado -MaxChamadas $MaxChamadas -Tentativas 1 -Privacidade private
if ($LASTEXITCODE -ne 0) {
  throw 'Pipeline oficial bloqueou a producao. Cache e arquivos locais preservados; nao usar outro motor como fallback.'
}
if (-not (Test-Path -LiteralPath $video -PathType Leaf) -or
    -not (Test-Path -LiteralPath $cover -PathType Leaf)) {
  throw 'O motor nao criou MP4 e capa completos; nao alegar sucesso.'
}
Write-Host ('[BR REAL] MP4 gerado pelo AutoEditorVideo: ' + $video)
Write-Host ('[BR REAL] Capa: ' + $cover)
Write-Host '[BR REAL] Nenhum upload foi realizado. Assista e revise o video antes de publicar.'
