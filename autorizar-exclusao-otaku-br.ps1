# One safe command on the owner's PC: authorize EXACT BR YouTube channel for
# deletion of ONE obsolete video, upload only the isolated deletion secret to
# the protected main-only GitHub environment, and trigger one-shot cleanup.
# NEVER modifies existing OAuth upload/read-only tokens.
[CmdletBinding()]
param(
    [switch]$ConfirmarExclusaoDoVideoAntigo,
    [switch]$RenovarTokenDeExclusao
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if (-not $ConfirmarExclusaoDoVideoAntigo) {
    throw 'A exclusao irreversivel requer -ConfirmarExclusaoDoVideoAntigo. Nenhuma acao realizada.'
}

$repo='HelioConde/AutoEditorVideo'
$expectedChannel='UCXGYTuBYn-0Ziqin5ajKhOw'
$environment='youtube-private-upload'
$onlyOldId='alHbSHUN0dA'
$root=$PSScriptRoot
$python=Join-Path $root '.venv\Scripts\python.exe'
$clientPath=Join-Path $root '.secrets\youtube-oauth-client.json'
$tokenPath=Join-Path $root '.secrets\youtube-br-delete-token.json'
$wf='.github/workflows/otaku-br-delete-only-original-20261108.yml'

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'Ambiente Python .venv ausente; crie-o e instale requirements-publicacao.txt.'
}
if (-not (Test-Path -LiteralPath $clientPath -PathType Leaf)) {
    throw 'OAuth client local .secrets\youtube-oauth-client.json ausente.'
}
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw 'Instale GitHub CLI (gh) e autentique usando gh auth login.'
}
if (-not (Test-Path -LiteralPath (Join-Path $root $wf) -PathType Leaf)) {
    throw 'Execute git pull e confira o workflow de exclusao no repositorio.'
}

# Keep all OAuth tokens private. Confirm protected shared environment main-only
# BEFORE user is asked to grant any new destructive permission.
try {
    $envObj=(& gh api "repos/$repo/environments/$environment" | ConvertFrom-Json)
    if ($LASTEXITCODE -ne 0 -or $null -eq $envObj) { throw 'Environment unavailable' }
    $policies=(& gh api "repos/$repo/environments/$environment/deployment-branch-policies?per_page=100" | ConvertFrom-Json)
    if ($LASTEXITCODE -ne 0 -or $null -eq $policies) { throw 'Policies unavailable' }
    if ($envObj.name -cne $environment -or
        $envObj.deployment_branch_policy.custom_branch_policies -ne $true -or
        $envObj.deployment_branch_policy.protected_branches -ne $false -or
        $policies.total_count -ne 1 -or
        $policies.branch_policies.Count -ne 1 -or
        $policies.branch_policies[0].name -cne 'main' -or
        $policies.branch_policies[0].type -cne 'branch') {
        throw 'Shared environment not exclusively main-only'
    }
} catch {
    throw '[BLOQUEADO] Nao foi possivel validar que o GitHub Environment esta restrito a main.'
}

# This token is new and separate. The Google browser must authorize the exact
# BR channel. Never grant this token access to other YouTube channels.
$argsAuthorize=@((Join-Path $root 'scripts\autorizar_exclusao_otaku_br.py'))
if ($RenovarTokenDeExclusao) { $argsAuthorize+= '--renovar' }
& $python @argsAuthorize
if ($LASTEXITCODE -ne 0) { throw '[BLOQUEADO] Nova autorizacao de exclusao falhou. Nenhum secret alterado.' }

# Offline verify client, scopes and exact channel intended. Do not print token.
$client=Get-Content -LiteralPath $clientPath -Raw -Encoding UTF8 | ConvertFrom-Json
$token=Get-Content -LiteralPath $tokenPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($token.client_id -cne [string]$client.installed.client_id -or
    -not $token.refresh_token -or
    -not ($token.scopes -contains 'https://www.googleapis.com/auth/youtube.force-ssl') -or
    -not ($token.scopes -contains 'https://www.googleapis.com/auth/youtube.readonly')) {
    throw '[BLOQUEADO] O token dedicado nao pertence ao cliente ou nao recebeu a permissao de exclusao.'
}
$clientSecretNames=(& gh secret list -e $environment -R $repo --json name | ConvertFrom-Json)
if ($LASTEXITCODE -ne 0 -or -not @($clientSecretNames | Where-Object { $_.name -ceq 'YOUTUBE_CLIENT_JSON' }).Count) {
    throw '[BLOQUEADO] O secret de cliente OAuth nao existe no environment. Nao enviar novo token.'
}

Get-Content -LiteralPath $tokenPath -Raw -Encoding UTF8 |
    & gh secret set YOUTUBE_BR_DELETE_TOKEN_JSON -e $environment -R $repo
if ($LASTEXITCODE -ne 0) { throw '[BLOQUEADO] Falha ao guardar o token de exclusao isolado.' }
Write-Host '[OK] Somente YOUTUBE_BR_DELETE_TOKEN_JSON atualizado. Tokens de upload preservados.'

# No deletion here; GitHub job verifies 3 new public Shorts and ID/metadata
# of the only old video before making EXACTLY ONE videos.delete request.
& gh workflow run $wf -R $repo --ref main
if ($LASTEXITCODE -ne 0) {
    throw '[ATENCAO] Token atualizado, mas disparo do workflow falhou; use a aba Actions.'
}
Write-Host "[INICIADO] Exclusao via API limitada a $onlyOldId apos checar canal $expectedChannel."
Write-Host "Acompanhe em https://github.com/$repo/actions/workflows/otaku-br-delete-only-original-20261108.yml"
