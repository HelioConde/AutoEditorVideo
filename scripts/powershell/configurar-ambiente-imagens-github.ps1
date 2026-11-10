# Configura Environment separado para imagens e, somente por opt-in,
# envia o estado OAuth EXISTENTE do proxy para um Environment Secret.
# NUNCA imprime tokens, usa secrets em PR ou publica video.
[CmdletBinding()]
param(
    [ValidateSet('Preparar', 'Status', 'ImportarSessao')]
    [string]$Acao = 'Status',
    [string]$Arquivo = ''
)

$ErrorActionPreference = 'Stop'
$repo = 'HelioConde/AutoEditorVideo'
$nomeAmbiente = 'image-generation'
$endpoint = "repos/$repo/environments/$nomeAmbiente"
$politicasEndpoint = "$endpoint/deployment-branch-policies"

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw 'Instale GitHub CLI: winget install --id GitHub.cli -e'
}
& gh auth status 1>$null 2>$null
if ($LASTEXITCODE -ne 0) { throw 'Execute gh auth login com permissoes administrativas no repositorio.' }

function Ler-GitHub-Json([string]$Rota) {
    $resposta = & gh api $Rota 2>$null
    if ($LASTEXITCODE -ne 0) { throw "Falha na consulta GitHub API ($Rota)" }
    return (($resposta | Out-String) | ConvertFrom-Json -ErrorAction Stop)
}

function Confirmar-Protecao {
    $ambiente = Ler-GitHub-Json $endpoint
    if (-not $ambiente -or $ambiente.name -ne $nomeAmbiente) {
        throw 'Environment image-generation nao existe.'
    }
    if (-not $ambiente.deployment_branch_policy.custom_branch_policies -or
        $ambiente.deployment_branch_policy.protected_branches) {
        throw 'Protecao ausente: configure custom deployment branch policies.'
    }
    $lista = Ler-GitHub-Json ($politicasEndpoint + '?per_page=100')
    $regras = @($lista.branch_policies | Where-Object { $null -ne $_ })
    if ($lista.total_count -ne 1 -or $regras.Count -ne 1 -or
        $regras[0].name -ne 'main' -or
        ($regras[0].type -and $regras[0].type -ne 'branch')) {
        throw 'Politica insegura: apenas a branch main deve ser autorizada.'
    }
    Write-Host '[OK] Environment image-generation: somente main.' -ForegroundColor Green
}

if ($Acao -eq 'Preparar') {
    $jaExiste = $false
    try {
        $null = Ler-GitHub-Json $endpoint
        $jaExiste = $true
    } catch {
        # Se houver erro de permissao, o PUT tambem falhara, sem permitir acesso inseguro.
    }
    if (-not $jaExiste) {
        $json = @{
            deployment_branch_policy = @{
                protected_branches = $false
                custom_branch_policies = $true
            }
            wait_timer = 0
        } | ConvertTo-Json -Compress -Depth 6
        $json | & gh api --method PUT $endpoint --input - --silent
        if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel criar o Environment protegido.' }
        '{"name":"main","type":"branch"}' |
            & gh api --method POST $politicasEndpoint --input - --silent
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao restringir o Environment a main.' }
    }
    Confirmar-Protecao
    & gh variable set IMAGE_MODEL -R $repo -e $nomeAmbiente -b 'gpt-image-2'
    if ($LASTEXITCODE -ne 0) { throw 'Erro ao cadastrar IMAGE_MODEL.' }
    & gh variable set MAX_IMAGE_CALLS -R $repo -e $nomeAmbiente -b '0'
    if ($LASTEXITCODE -ne 0) { throw 'Erro ao cadastrar MAX_IMAGE_CALLS.' }
    & gh variable set PROXY_PORT -R $repo -e $nomeAmbiente -b '8080'
    if ($LASTEXITCODE -ne 0) { throw 'Erro ao cadastrar PROXY_PORT.' }
    Write-Host '[OK] Variables: IMAGE_MODEL, MAX_IMAGE_CALLS=0, PROXY_PORT.' -ForegroundColor Green
    Write-Host '[PENDENTE] Nenhuma sessao OAuth foi enviada.'
    exit 0
}

Confirmar-Protecao
if ($Acao -eq 'Status') {
    Write-Host '[INFO] Nomes dos secrets do Environment (valores ocultos):'
    & gh secret list -R $repo -e $nomeAmbiente
    if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel verificar a lista de secrets.' }
    exit 0
}

# A importacao exige confirmacao explicita e arquivo presente no Windows.
Write-Host '[ATENCAO] Voce enviara tokens OAuth da conta do proxy ao GitHub Environment image-generation.'
Write-Host '[ATENCAO] Apenas administradores e workflows autorizados devem poder acessa-los.'
Write-Host '[ATENCAO] O token atualizado no runner NAO atualizara automaticamente o Secret.'
$consentimento = Read-Host 'Digite AUTORIZO para continuar'
if ($consentimento -cne 'AUTORIZO') { throw 'Importacao cancelada pelo usuario.' }

$temporario = $null
try {
    if ([string]::IsNullOrWhiteSpace($Arquivo)) {
        if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
            throw 'Docker nao disponivel: informe -Arquivo com accounts.json privado ja exportado.'
        }
        $temporario = Join-Path ([System.IO.Path]::GetTempPath()) (
            'fofinhos-proxy-state-' + [guid]::NewGuid().ToString('N') + '.json'
        )
        & docker cp "chatgpt-codex-proxy:/app/data/accounts.json" $temporario 1>$null
        if ($LASTEXITCODE -ne 0) {
            throw 'Nao foi possivel obter accounts.json do container. Informe -Arquivo explicitamente.'
        }
        $alvo = $temporario
    } else {
        $alvo = (Resolve-Path -LiteralPath $Arquivo -ErrorAction Stop).Path
    }
    if (-not (Test-Path -LiteralPath $alvo -PathType Leaf)) {
        throw 'Arquivo accounts.json nao encontrado.'
    }
    $bytes = [System.IO.File]::ReadAllBytes($alvo)
    if ($bytes.Length -eq 0 -or $bytes.Length -gt 46080) {
        throw 'Arquivo vazio ou acima de 45 KiB. Nao enviar sem estrategia alternativa.'
    }
    $conteudo = [System.Text.Encoding]::UTF8.GetString($bytes)
    $estado = $conteudo | ConvertFrom-Json -ErrorAction Stop
    $contas = @($estado.records | Where-Object { $null -ne $_ })
    if ($contas.Count -lt 1 -or $contas.Count -gt 20) {
        throw 'Estado OAuth ausente ou fora do limite validado.'
    }
    foreach ($conta in $contas) {
        if (-not $conta.token -or
            [string]::IsNullOrWhiteSpace($conta.token.access_token) -or
            [string]::IsNullOrWhiteSpace($conta.token.refresh_token)) {
            throw 'Estado OAuth incompleto: dados de token ausentes.'
        }
    }
    # gh CLI cifra localmente antes de enviar; nunca use -b ou logs com tokens.
    $antigaCodificacao = $OutputEncoding
    try {
        $OutputEncoding = New-Object System.Text.UTF8Encoding($false)
        $conteudo | & gh secret set PROXY_ACCOUNTS_JSON -R $repo -e $nomeAmbiente --app actions
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao cadastrar PROXY_ACCOUNTS_JSON.' }
    } finally {
        $OutputEncoding = $antigaCodificacao
    }
    Write-Host '[OK] PROXY_ACCOUNTS_JSON cadastrado no Environment. Valores ocultos.' -ForegroundColor Green
    Write-Host '[AVISO] Nao execute geracao real ate revisar riscos, cota e persistencia de refresh token.'
} finally {
    if ($temporario -and (Test-Path -LiteralPath $temporario)) {
        Remove-Item -LiteralPath $temporario -Force -ErrorAction SilentlyContinue
    }
}
