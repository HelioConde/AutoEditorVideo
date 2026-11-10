# Envia credenciais JA EXISTENTES do Windows para GitHub Actions Secrets.
# Nao gera token OAuth: rode scripts/autorizar_youtube_canais.py primeiro.
# Nunca mostra conteudos de .env, client.json ou token.json na tela.
[CmdletBinding()]
param(
    [ValidateSet('Proxy', 'YouTube')]
    [string]$Acao = 'Proxy',
    [ValidateSet('br', 'en', 'kids')]
    [string]$Canal = 'br'
)

$ErrorActionPreference = 'Stop'
$repo = 'HelioConde/AutoEditorVideo'
$root = $PSScriptRoot
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw 'GitHub CLI (gh) ausente. Instale com: winget install --id GitHub.cli -e'
}

function Enviar-Segredo([string]$Nome, [string]$Valor) {
    if ([string]::IsNullOrWhiteSpace($Valor)) {
        throw "Valor ausente para $Nome"
    }
    # The standard input is encrypted by gh before transmission.
    # Never use --body or echo the value in logs.
    $Valor | & gh secret set $Nome -R $repo --app actions
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao cadastrar $Nome. Confira gh auth login e permissao ao repo."
    }
    Write-Host "[OK] Secret $Nome cadastrado (valor oculto)." -ForegroundColor Green
}

function Ler-Json([string]$Arquivo) {
    if (-not (Test-Path -LiteralPath $Arquivo -PathType Leaf)) {
        throw "Arquivo nao encontrado: $Arquivo. Gere/autentique primeiro."
    }
    $valor = [System.IO.File]::ReadAllText($Arquivo, [System.Text.Encoding]::UTF8)
    $null = $valor | ConvertFrom-Json -ErrorAction Stop
    return $valor
}

if ($Acao -eq 'Proxy') {
    $arquivos = @(
        (Join-Path $root 'chatgpt-codex-proxy\.env'),
        (Join-Path $root '..\arquivo-otaku-kit\chatgpt-codex-proxy\.env')
    )
    $encontrado = $null
    foreach ($arquivo in $arquivos) {
        if (Test-Path -LiteralPath $arquivo -PathType Leaf) {
            $encontrado = $arquivo
            break
        }
    }
    if (-not $encontrado) {
        throw 'Chave do proxy ausente. Use .\testar-codex-proxy.ps1 -Acao instalar no Windows com Docker funcionando.'
    }
    $m = [regex]::Match(
        [System.IO.File]::ReadAllText($encontrado),
        '(?m)^PROXY_API_KEY\s*=\s*(.*?)\s*$'
    )
    if (-not $m.Success) { throw 'PROXY_API_KEY nao localizada no .env.' }
    $key = $m.Groups[1].Value.Trim().Trim('"').Trim("'")
    if ($key.Length -lt 15 -or $key.StartsWith('change-me')) {
        throw 'PROXY_API_KEY nao parece valida.'
    }
    Enviar-Segredo 'PROXY_API_KEY' $key
    Write-Host '[AVISO] A chave nao liga nem autentica uma conta no servidor proxy. Ela apenas protege as chamadas ao servico.'
    exit 0
}

$cliente = Join-Path $root '.secrets\youtube-oauth-client.json'
$tokenPorCanal = @{
    br = 'youtube-token.json'
    en = 'youtube-en-token.json'
    kids = 'youtube-kids-token.json'
}
$secretPorCanal = @{
    br = 'YOUTUBE_BR_TOKEN_JSON'
    en = 'YOUTUBE_EN_TOKEN_JSON'
    kids = 'YOUTUBE_KIDS_TOKEN_JSON'
}
$token = Join-Path $root ('.secrets\' + $tokenPorCanal[$Canal])
# Check both inputs before sending either, to avoid partial registration.
$clientJson = Ler-Json $cliente
$tokenJson = Ler-Json $token
$clientData = $clientJson | ConvertFrom-Json
$tokenData = $tokenJson | ConvertFrom-Json
if (-not $clientData.installed.client_id -or -not $clientData.installed.client_secret) {
    throw 'OAuth client invalido: baixe JSON de App para computador.'
}
if (-not $tokenData.client_id -or -not $tokenData.client_secret -or -not $tokenData.refresh_token) {
    throw 'OAuth token invalido: execute a autorizacao com navegador antes.'
}
if ($clientData.installed.client_id -ne $tokenData.client_id) {
    throw 'Token e cliente OAuth sao de projetos diferentes.'
}
Enviar-Segredo 'YOUTUBE_OAUTH_CLIENT_JSON' $clientJson
Enviar-Segredo $secretPorCanal[$Canal] $tokenJson
Write-Host "[OK] Canal $Canal configurado. Nenhum video foi enviado."
