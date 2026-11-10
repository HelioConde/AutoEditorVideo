# Authorize public publishing of EXISTING AutoEditorVideo Shorts safely.
# Local Google consent is required; secrets are NEVER printed or committed.
[CmdletBinding()]
param(
  [ValidateSet('games','kids','alchemy','br','en')]
  [string]$Canal = 'games',
  [ValidateSet('Verificar','Conectar','EnviarSecret')]
  [string]$Acao = 'Verificar',
  [switch]$ConfirmarArmazenamentoGitHub
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$repo = 'HelioConde/AutoEditorVideo'
$environment = 'youtube-private-upload'
$root = $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
$oauthScript = Join-Path $root 'scripts\youtube_public_edit_oauth_local.py'
$tokenFile = Join-Path $root ('.secrets\youtube-' + $Canal + '-public-edit-token.json')
$clientFile = Join-Path $root '.secrets\youtube-oauth-client.json'
$secretName = @{
  br='YOUTUBE_BR_TOKEN_JSON'
  en='YOUTUBE_EN_TOKEN_JSON'
  games='YOUTUBE_GAMES_TOKEN_JSON'
  kids='YOUTUBE_KIDS_TOKEN_JSON'
  alchemy='YOUTUBE_ALCHEMY_TOKEN_JSON'
}[$Canal]

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
  throw 'Falta Python .venv. Instale os requisitos locais do AutoEditorVideo.'
}
if (-not (Test-Path -LiteralPath $oauthScript -PathType Leaf)) {
  throw 'Atualize o repositorio: arquivo OAuth de publicacao nao encontrado.'
}
if ($Acao -eq 'Conectar') {
  if (-not (Test-Path -LiteralPath $clientFile -PathType Leaf)) {
    throw 'Credenciais OAuth locais nao encontradas em .secrets\youtube-oauth-client.json.'
  }
  Write-Host '[YOUTUBE] O Google abrira a autorizacao para gerenciar videos do canal selecionado.'
  & $python $oauthScript --channel $Canal --action connect
  if ($LASTEXITCODE -ne 0) { throw 'Autorizacao do Google falhou. NENHUM token alterado no GitHub.' }
  Write-Host "[OK] Agora execute: .\autorizar-publicacao-youtube.ps1 -Canal $Canal -Acao EnviarSecret -ConfirmarArmazenamentoGitHub"
  exit 0
}
& $python $oauthScript --channel $Canal --action verify
if ($LASTEXITCODE -ne 0) {
  throw 'O token nao esta validado para o canal e escopos de edicao. NENHUM Secret alterado.'
}
if ($Acao -eq 'Verificar') {
  Write-Host '[OK] A conta, o canal e a permissao de edicao foram confirmados; nenhum token enviado.'
  exit 0
}
if (-not $ConfirmarArmazenamentoGitHub) {
  throw 'Use -ConfirmarArmazenamentoGitHub para confirmar o armazenamento do novo token no Secret protegido.'
}
$gh = Get-Command gh -ErrorAction SilentlyContinue
if (-not $gh) { throw 'GitHub CLI nao instalado ou nao autenticado.' }
if (-not (Test-Path -LiteralPath $tokenFile -PathType Leaf)) {
  throw 'O token local de publicacao nao existe; execute -Acao Conectar.'
}

# Fail closed unless GitHub confirms THIS Environment is restricted to main.
$envInfoRaw = & gh api "repos/$repo/environments/$environment" 2>$null
if ($LASTEXITCODE -ne 0) { throw 'Falha ao confirmar a politica do Environment. Nenhum token enviado.' }
$envInfo = $envInfoRaw | ConvertFrom-Json
$policiesRaw = & gh api "repos/$repo/environments/$environment/deployment-branch-policies?per_page=100" 2>$null
if ($LASTEXITCODE -ne 0) { throw 'Falha ao consultar as politicas de branch do Environment.' }
$policies = $policiesRaw | ConvertFrom-Json
if ($envInfo.name -cne $environment -or
    $envInfo.deployment_branch_policy.custom_branch_policies -ne $true -or
    $envInfo.deployment_branch_policy.protected_branches -ne $false -or
    $policies.total_count -ne 1 -or
    $policies.branch_policies.Count -ne 1 -or
    $policies.branch_policies[0].name -cne 'main' -or
    $policies.branch_policies[0].type -cne 'branch') {
  throw 'Politica main-only do Environment nao confirmada; NENHUM Secret enviado.'
}
$existingRaw = & gh secret list -e $environment -R $repo --json name 2>$null
if ($LASTEXITCODE -ne 0) { throw 'Falha ao listar Secrets existentes.' }
$existing = @($existingRaw | ConvertFrom-Json)
if (@($existing | Where-Object { $_.name -ceq 'YOUTUBE_CLIENT_JSON' }).Count -ne 1 -or
    @($existing | Where-Object { $_.name -ceq $secretName }).Count -ne 1) {
  throw 'Secrets Google OAuth existentes nao confirmados; NENHUM Secret enviado.'
}

# A pipe avoids command-line arguments, process listings, transcripts or logs
# containing refresh tokens. Only the SELECTED channel secret is replaced.
Get-Content -LiteralPath $tokenFile -Raw -Encoding UTF8 |
  & gh secret set $secretName -e $environment -R $repo
if ($LASTEXITCODE -ne 0) { throw 'Falha ao atualizar o Secret. Nao houve alteracao dos videos.' }
Write-Host "[OK] OAuth de edicao do canal $Canal atualizado no Environment protegido $environment."
Write-Host '[SEGURANCA] Nenhuma publicacao, troca de privacidade ou upload duplicado foi realizado nesta etapa.'
