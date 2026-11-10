# Canal Ingles: Otaku Reframe (en-US), separado do Otaku Multicena e do Gamer/Kids.
# Entrada unica para adaptar Shorts brasileiros ja publicados e o lote legado EN.
# Nao altera o canal BR. NENHUM upload sem -Acao Enviar -Id -ConfirmarEnvio.
[CmdletBinding()]
param(
  [ValidateSet('Resumo','VerificarFontes','Preparar','Planejar','Voz','Capa','Renderizar','VerificarUpload','Conectar','Enviar')]
  [string]$Acao='Resumo',

  [ValidateSet('PublicadosBR','Legado')]
  [string]$Catalogo='PublicadosBR',

  [ValidatePattern('^[a-z0-9]+(?:-[a-z0-9]+)*$')]
  [string]$Id='',

  [string]$Manifesto='',

  [ValidateSet('gpt-image-1.5','gpt-image-2')]
  [string]$Modelo='gpt-image-1.5',

  [ValidateSet('equilibrado','vivo','ultrassutil')]
  [string]$Perfil='equilibrado',

  [ValidateSet('private','unlisted','public')]
  [string]$Privacidade='private',

  [switch]$ExigirMovimentoPersonagem,
  [switch]$Refazer,
  [switch]$ConfirmarEnvio,
  [switch]$ConfirmarPublico
)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

$root=$PSScriptRoot
$canalIdEsperado='UCBoNbQjaMYdpJqPLRZAFkvQ'
$arquivoId=Join-Path $root '.secrets\youtube-en-channel-id.txt'
$preparador=Join-Path $root 'preparar-publicados-en.ps1'
$gerador=Join-Path $root 'gerar-shorts-en.ps1'
$publicador=Join-Path $root 'publicar-shorts-en.ps1'

if($Catalogo -eq 'Legado'){
  $padrao='conteudos\testes-animados-5-en.json'
}else{
  $padrao='assets\gerados\otaku-br-publicados-en-v3.json'
}
$caminhoInformado=if($Manifesto){$Manifesto}else{$padrao}
$caminhoManifesto=if([IO.Path]::IsPathRooted($caminhoInformado)){
  $caminhoInformado
}else{
  Join-Path $root $caminhoInformado
}

$acoesFontes=@('Resumo','VerificarFontes','Preparar')
$acoesGeracao=@('Planejar','Voz','Capa','Renderizar')
$acoesUpload=@('VerificarUpload','Conectar','Enviar')
$acaoSomenteArquivo=$Acao -in ($acoesGeracao + @('VerificarUpload','Enviar'))

if($Acao -in $acoesFontes -and $Catalogo -ne 'PublicadosBR'){
  throw 'Resumo, VerificarFontes e Preparar sao exclusivos do catalogo PublicadosBR.'
}
if($acaoSomenteArquivo -and -not (Test-Path -LiteralPath $caminhoManifesto -PathType Leaf)){
  throw "Manifesto EN ausente: $caminhoManifesto. Execute -Acao Preparar primeiro."
}
if($Acao -in ($acoesGeracao + @('VerificarUpload','Enviar')) -and [string]::IsNullOrWhiteSpace($Id)){
  throw 'Informe -Id de apenas um Short em ingles para evitar processar lotes por acidente.'
}
if($Refazer -and $Acao -ne 'Renderizar'){
  throw '-Refazer so pode ser usado em -Acao Renderizar.'
}
if($ExigirMovimentoPersonagem -and $Acao -ne 'Renderizar'){
  throw '-ExigirMovimentoPersonagem so pode ser usado em -Acao Renderizar.'
}
if($ConfirmarEnvio -and $Acao -ne 'Enviar'){
  throw '-ConfirmarEnvio so pode ser usado em -Acao Enviar.'
}
if($ConfirmarPublico -and $Acao -ne 'Enviar'){
  throw '-ConfirmarPublico so pode ser usado em -Acao Enviar.'
}
if($Acao -eq 'Enviar'){
  if(-not $ConfirmarEnvio){
    throw 'Upload bloqueado. Use -Acao Enviar -Id ... -ConfirmarEnvio.'
  }
  if($Privacidade -eq 'public' -and -not $ConfirmarPublico){
    throw 'Publicacao publica exige -ConfirmarPublico adicional.'
  }
}

# A conta inglesa ja existe, e o canal ID REAL foi verificado anteriormente.
# Quando usuario conectar ou enviar, bloquear ID local ausente/divergente.
if($Acao -in @('Conectar','Enviar')){
  if(-not (Test-Path -LiteralPath $arquivoId -PathType Leaf)){
    throw 'Configure .secrets\youtube-en-channel-id.txt com o ID real do Otaku Reframe.'
  }
  $valor=(Get-Content -LiteralPath $arquivoId -Raw -Encoding UTF8).Trim()
  if($valor -ne $canalIdEsperado){
    throw 'BLOQUEADO: ID local nao corresponde ao Otaku Reframe. Nenhum OAuth ou upload executado.'
  }
}

Write-Host "[OTAKU REFRAME EN] $Acao | catalogo=$Catalogo | $Id" -ForegroundColor Cyan

if($Acao -in $acoesFontes){
  if(-not (Test-Path -LiteralPath $preparador -PathType Leaf)){
    throw 'Preparador EN V3 nao encontrado. Atualize o projeto.'
  }
  $acaoFila=switch($Acao){
    'Resumo' {'Resumo'}
    'VerificarFontes' {'Verificar'}
    'Preparar' {'Preparar'}
  }
  $parametros=@{Acao=$acaoFila;Saida=$caminhoManifesto}
  if($Id){$parametros.Id=@($Id)}
  & $preparador @parametros
  if(-not $?){throw 'Preparacao EN falhou. Nenhum upload realizado.'}
  Write-Host '[EN] Preparacao offline concluida; arquivos brasileiros preservados.' -ForegroundColor Green
  return
}

if($Acao -in $acoesGeracao){
  if(-not (Test-Path -LiteralPath $gerador -PathType Leaf)){
    throw 'Gerador EN nao encontrado. Atualize o projeto.'
  }
  $parametros=@{
    Acao=$Acao.ToLowerInvariant()
    Id=$Id
    Manifesto=$caminhoManifesto
    Modelo=$Modelo
    Perfil=$Perfil
  }
  if($Refazer){$parametros.Refazer=$true}
  if($ExigirMovimentoPersonagem){$parametros.ExigirMovimentoPersonagem=$true}
  & $gerador @parametros
  if(-not $?){throw 'Etapa de criacao EN falhou. Nenhum upload realizado.'}
  Write-Host '[EN] Etapa local concluida. Nenhum video enviado.' -ForegroundColor Green
  return
}

if(-not (Test-Path -LiteralPath $publicador -PathType Leaf)){
  throw 'Publicador EN nao encontrado. Atualize o projeto.'
}
$acaoPublicador=switch($Acao){
  'VerificarUpload' {'verificar'}
  'Conectar' {'conectar'}
  'Enviar' {'enviar'}
}
$parametros=@{
  Acao=$acaoPublicador
  Perfil=$Perfil
  Privacidade=$Privacidade
  Limite=1
}
if($Acao -ne 'Conectar'){
  $parametros.Id=$Id
  $parametros.Manifesto=$caminhoManifesto
}
if($Acao -eq 'Enviar'){$parametros.ConfirmarEnvio=$true}
& $publicador @parametros
if(-not $?){
  throw 'Etapa YouTube EN falhou. Nunca reenvie automaticamente apos erro ambiguo.'
}
Write-Host '[EN] Etapa concluida. Verifique o canal Otaku Reframe no Studio quando aplicavel.' -ForegroundColor Green
