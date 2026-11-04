# Gera poses CONSISTENTES de Emanuelly usando exclusivamente gpt-image-2.
# A imagem de referencia fica somente no Windows, fora do GitHub publico.
# O proxy de imagens pode encaminhar a imagem ao provedor de IA.
# Nao gera videos e NAO faz upload no YouTube.
[CmdletBinding()]
param(
  [ValidateSet('Planejar','Catalogo','InstalarReferencia','Gerar','Verificar','Abrir')]
  [string]$Acao='Planejar',

  # -Pose recebe qualquer slug oficial do catalogo; validacao rigorosa no Python.
  [string]$Pose='Todas',

  [ValidateSet('Essenciais','Ep01','Carinho','Emocoes','Movimento',
               'Brincadeiras','Cotidiano','Futuras','Todas')]
  [string]$Grupo='Essenciais',

  # Produzir poucas poses por vez, priorizando as que faltam no cache.
  [ValidateRange(0,100)]
  [int]$Quantidade=0,

  [string]$Referencia='',

  [ValidateRange(0,100)]
  [int]$MaxChamadas=0,

  [switch]$Refazer
)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$script=Join-Path $root 'scripts\gerar_poses_emanuelly_gpt_image_2.py'
if(-not (Test-Path -LiteralPath $script -PathType Leaf)){
  throw 'Motor de poses ausente. Atualize o repositorio AutoEditorVideo.'
}
$python=Join-Path $root '.venv\Scripts\python.exe'
if(-not(Test-Path -LiteralPath $python -PathType Leaf)){
  $found=Get-Command python -ErrorAction SilentlyContinue
  if(-not $found){throw 'Python nao encontrado (.venv ou PATH).'}
  $python=$found.Source
}
$installed=Join-Path $root 'assets\referencias-privadas\emanuelly-personagem-oficial.png'
if($Acao -eq 'InstalarReferencia'){
  if([string]::IsNullOrWhiteSpace($Referencia)){
    throw 'Informe -Referencia "C:\caminho\foto-aprovada.png".'
  }
}else{
  if(-not [string]::IsNullOrWhiteSpace($Referencia)){
    throw '-Referencia so pode ser usado com -Acao InstalarReferencia.'
  }
}
if($Acao -in @('Planejar','Catalogo','Verificar','Abrir') -and $Refazer){
  throw '-Refazer permitido apenas para InstalarReferencia ou Gerar.'
}
if($Acao -ne 'Gerar' -and $Quantidade -gt 0){
  throw '-Quantidade e permitido somente com -Acao Gerar.'
}
if($Acao -eq 'Gerar'){
  if(-not (Test-Path -LiteralPath $installed -PathType Leaf)){
    throw "Foto privada nao instalada: $installed. Use InstalarReferencia antes de Gerar."
  }
  if($MaxChamadas -eq 0){
    Write-Warning 'Orcamento zero: so funcionara com poses validas no cache.'
  }
  Write-Host "[CONSENTIMENTO] A foto privada sera enviada ao Codex Proxy local, que pode encaminha-la ao provedor configurado." -ForegroundColor Yellow
  Write-Host "[LIMITE] Ate $MaxChamadas chamadas de edicao de imagem, somente no modelo gpt-image-2." -ForegroundColor Yellow
}
$map=@{
  Planejar='planejar'
  Catalogo='catalogo'
  InstalarReferencia='instalar-referencia'
  Gerar='gerar'
  Verificar='verificar'
  Abrir='abrir'
}
$arguments=@($script,'--acao',$map[$Acao],'--pose',$Pose,
             '--grupo',$Grupo,'--quantidade',"$Quantidade",
             '--max-chamadas',"$MaxChamadas")
if($Acao -eq 'InstalarReferencia'){
  $resolved=(Resolve-Path -LiteralPath $Referencia -ErrorAction Stop).Path
  $arguments+=@('--referencia',$resolved)
}
if($Refazer){$arguments+='--refazer'}
Write-Host "[EMANUELLY POSES] $Acao | Grupo $Grupo | Pose $Pose | gpt-image-2 | ZERO upload" -ForegroundColor Cyan
& $python @arguments
if($LASTEXITCODE -ne 0){
  throw 'A geracao das poses foi interrompida. Imagens antigas preservadas, nenhum upload.'
}
Write-Host '[EMANUELLY POSES] Etapa local concluida.' -ForegroundColor Green
