# Safe YouTube OAuth onboarding for the three new AutoEditorVideo channels.
# This NEVER generates images, uploads a video, or changes YouTube metadata.
[CmdletBinding()]
param(
  [ValidateSet('games','kids','alchemy')]
  [string]$Canal = 'games',
  [ValidateSet('Inspecionar','Conectar','EnviarSecret')]
  [string]$Acao = 'Inspecionar',
  [switch]$SubstituirToken,
  [switch]$ConfirmarArmazenamentoGitHub
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$repo = 'HelioConde/AutoEditorVideo'
$root = $PSScriptRoot
$py = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $py -PathType Leaf)) {
  throw 'Python .venv ausente. Instale a venv e requirements-publicacao.txt antes de continuar.'
}

$registry = Join-Path $root 'config\youtube-channel-registry.json'
if (-not (Test-Path -LiteralPath $registry)) {
  throw 'Registro de canais nao encontrado. Atualize o repositorio.'
}
$data = Get-Content -LiteralPath $registry -Raw -Encoding UTF8 | ConvertFrom-Json
$channel = $data.channels.$Canal
$expected = @{
  games = 'UCg77gYc1_wkHuL07XPtKcow'
  kids = 'UCxEzVW2Uy44OUVurTQSg_Eg'
  alchemy = 'UCCTYFE5Cmz2aYZ37cJQ-wcg'
}
if ($null -eq $channel -or $channel.youtube_channel_id -cne $expected[$Canal]) {
  throw 'O ID do canal nao corresponde ao registro verificado.'
}
$environment = [string]$channel.youtube_environment
if ($environment -cne 'youtube-private-upload') {
  throw 'O canal nao esta apontando para o Environment compartilhado aprovado.'
}
$tokenSecretName = [string]$channel.oauth_token_secret_name
$tokenPath = Join-Path $root (".secrets\youtube-$Canal-cloud-token.json")
$clientPath = Join-Path $root '.secrets\youtube-oauth-client.json'

if ($Acao -eq 'Inspecionar') {
  & $py (Join-Path $root 'scripts\youtube_new_channels_oauth.py') --action inspect --channel $Canal
  if ($LASTEXITCODE -ne 0) { throw 'Verificacao do registro falhou.' }
  Write-Host '[OK] Sem login, sem segredo, sem upload.'
  exit 0
}

if ($Acao -eq 'Conectar') {
  if (-not (Test-Path -LiteralPath $clientPath -PathType Leaf)) {
    throw 'Falta .secrets\youtube-oauth-client.json no computador.'
  }
  $argsScript = @((Join-Path $root 'scripts\youtube_new_channels_oauth.py'), '--action','connect','--channel',$Canal)
  if ($SubstituirToken) { $argsScript += '--replace-token' }
  & $py @argsScript
  if ($LASTEXITCODE -ne 0) { throw 'Conexao OAuth falhou. Nenhum token enviado ao GitHub.' }
  Write-Host '[OK] OAuth local verificado. Para importar no GitHub use -Acao EnviarSecret -ConfirmarArmazenamentoGitHub.'
  exit 0
}

if (-not $ConfirmarArmazenamentoGitHub) {
  throw 'O envio de refresh tokens ao GitHub exige -ConfirmarArmazenamentoGitHub.'
}
if (-not (Test-Path -LiteralPath $tokenPath -PathType Leaf) -or
    -not (Test-Path -LiteralPath $clientPath -PathType Leaf)) {
  throw 'Token/client OAuth local nao encontrado. Execute -Acao Conectar primeiro.'
}
$gh = Get-Command gh -ErrorAction SilentlyContinue
if (-not $gh) { throw 'GitHub CLI gh nao instalado/autenticado.' }

# Never put credentials into an Environment not explicitly restricted to main.
try {
  $envObj = & gh api "repos/$repo/environments/$environment" | ConvertFrom-Json
  if ($LASTEXITCODE -ne 0 -or $null -eq $envObj) { throw 'Environment ausente.' }
  $policies = & gh api "repos/$repo/environments/$environment/deployment-branch-policies?per_page=100" | ConvertFrom-Json
  if ($LASTEXITCODE -ne 0 -or $null -eq $policies) { throw 'Politica de branches indisponivel.' }
  if ($envObj.name -cne $environment -or
      $envObj.deployment_branch_policy.custom_branch_policies -ne $true -or
      $envObj.deployment_branch_policy.protected_branches -ne $false -or
      $policies.total_count -ne 1 -or
      $policies.branch_policies.Count -ne 1 -or
      $policies.branch_policies[0].name -cne 'main' -or
      $policies.branch_policies[0].type -cne 'branch') {
    throw 'Environment nao esta restrito EXCLUSIVAMENTE a main.'
  }
} catch {
  throw 'Politica de protecao do GitHub nao confirmada. NENHUM token enviado.'
}
# Preserve the OAuth CLIENT and BR/EN token Secrets already in this Environment.
# Only the individually selected new-channel token is allowed to be written.
try {
  $savedSecretsRaw = & gh secret list -e $environment -R $repo --json name
  if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel listar os nomes dos Secrets.' }
  $savedSecrets = @($savedSecretsRaw | ConvertFrom-Json)
  if (-not (@($savedSecrets | Where-Object { $_.name -ceq 'YOUTUBE_CLIENT_JSON' }).Count -eq 1)) {
    throw 'O Secret YOUTUBE_CLIENT_JSON existente nao foi confirmado. Preservar Otaku.'
  }
} catch {
  throw 'Nao foi possivel confirmar o OAuth CLIENT existente. NENHUM Secret alterado.'
}

# Ensure this locally authorized token uses the local client JSON, without
# printing secrets; Google Actions will also reject any mismatched cloud client.
try {
  $clientObject = Get-Content -LiteralPath $clientPath -Raw -Encoding UTF8 | ConvertFrom-Json
  $tokenObject = Get-Content -LiteralPath $tokenPath -Raw -Encoding UTF8 | ConvertFrom-Json
  $localClientId = if ($null -ne $clientObject.installed) {
    [string]$clientObject.installed.client_id
  } else { [string]$clientObject.web.client_id }
  if ([string]::IsNullOrWhiteSpace($localClientId) -or
      $tokenObject.client_id -cne $localClientId) {
    throw 'Identidade do OAuth client local incorreta.'
  }
} catch {
  throw 'Token OAuth local nao corresponde ao client local. NENHUM Secret alterado.'
}

Get-Content -LiteralPath $tokenPath -Raw -Encoding UTF8 |
  & gh secret set $tokenSecretName -e $environment -R $repo
if ($LASTEXITCODE -ne 0) { throw 'Falha ao registrar somente o token do canal selecionado.' }
Write-Host "[OK] ${Canal}: Token individual registrado no Environment compartilhado $environment."
Write-Host '[SEGURANCA] CLIENT e tokens BR/EN preservados. Nenhum upload nem token exibido.'
