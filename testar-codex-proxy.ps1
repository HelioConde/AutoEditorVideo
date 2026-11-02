# Arquivo Otaku - teste isolado do projeto comunitario 10/chatgpt-codex-proxy.
# PowerShell 5.1+; comandos: -Acao instalar, iniciar, login, status, imagem, parar
# O login e um ato explicito do usuario; NUNCA cole tokens em chats.
[CmdletBinding()]
param(
    [ValidateSet('instalar', 'iniciar', 'login', 'status', 'imagem', 'parar')]
    [string]$Acao = 'status',
    [ValidateSet('gpt-image-2', 'gpt-image-1.5')]
    [string]$Modelo = 'gpt-image-2',
    [string]$Prompt = 'Light Yagami from Death Note, faithful hand-drawn 2D Japanese TV anime character portrait, mid 2000s cel animation, crisp ink contours, flat colors, sharp brown eyes, layered brown hair, white shirt and red tie, serious analytical expression, portrait vertical framing, no text, no watermark'
)
$ErrorActionPreference = 'Stop'
$baseUrl = 'http://127.0.0.1:8080'
$repoDir = Join-Path $PSScriptRoot 'chatgpt-codex-proxy'
$envPath = Join-Path $repoDir '.env'
$composePath = Join-Path $repoDir 'compose.yaml'
$loginIdPath = Join-Path $PSScriptRoot '.codex-proxy-login-id.txt'

function Verificar-Comando([string]$Nome) {
    if (-not (Get-Command $Nome -ErrorAction SilentlyContinue)) {
        throw "Comando '$Nome' nao encontrado. Instale-o antes de continuar."
    }
}

# Em Windows PowerShell 5.1, a saida stderr de executaveis nativos pode
# virar NativeCommandError quando $ErrorActionPreference = Stop.
# Capture stderr com Continue e cheque $LASTEXITCODE explicitamente.
function Testar-DockerEngine {
    $anterior = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $resultado = @(& docker info --format '{{.ServerVersion}}' 2>&1)
        return ($LASTEXITCODE -eq 0 -and $resultado.Count -gt 0)
    } catch {
        return $false
    } finally {
        $ErrorActionPreference = $anterior
    }
}

function Executar-Nativo {
    param([string]$Comando, [string[]]$Argumentos)
    $anterior = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $Comando @Argumentos 2>&1 | ForEach-Object {
            if ($_ -is [System.Management.Automation.ErrorRecord]) {
                Write-Host ($_.ToString())
            } else {
                Write-Host $_
            }
        }
        $codigo = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $anterior
    }
    return [int]$codigo
}

function Confirmar-DockerEngine {
    if (Testar-DockerEngine) { return }

    $desktop = Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
    if (Test-Path $desktop) {
        Write-Host '[Docker] Motor Linux indisponivel. Tentando abrir o Docker Desktop...'
        try {
            Start-Process -FilePath $desktop -ErrorAction Stop
        } catch {
            Write-Warning "Nao consegui abrir Docker Desktop automaticamente: $($_.Exception.Message)"
        }
        for ($tentativa = 1; $tentativa -le 30; $tentativa++) {
            if (Testar-DockerEngine) {
                Write-Host '[OK] Docker Desktop conectado ao motor Linux.' -ForegroundColor Green
                return
            }
            Start-Sleep -Seconds 3
        }
    }
    throw @'
Docker Desktop esta instalado, mas o motor Linux (dockerDesktopLinuxEngine) nao responde.
Abra o Docker Desktop, confirme que esta em Linux containers e que o motor foi iniciado.
Diagnostico em outra janela:
  docker version
  docker info --format '{{.ServerVersion}}'
  wsl --list --verbose
Se necessario, reinicie o Docker Desktop e repita -Acao instalar.
Nao e necessario reinstalar o GPT4Free ou MoneyPrinterTurbo.
'@
}

function Ler-Chave {
    if (-not (Test-Path $envPath)) {
        throw 'Arquivo .env nao encontrado. Execute -Acao instalar primeiro.'
    }
    $line = @(Get-Content $envPath | Where-Object { $_ -match '^PROXY_API_KEY=' } | Select-Object -First 1)
    if ($line.Count -eq 0) { throw 'PROXY_API_KEY ausente em .env.' }
    $key = ($line[0] -replace '^PROXY_API_KEY=', '').Trim().Trim('"').Trim("'")
    if (-not $key -or $key.StartsWith('change-me')) { throw 'PROXY_API_KEY invalida em .env.' }
    return $key
}

function Headers-Autenticados {
    $k = Ler-Chave
    return @{ Authorization = "Bearer $k" }
}

function Verificar-Servidor {
    try {
        $health = Invoke-RestMethod -Uri "$baseUrl/health/live" -Method Get -TimeoutSec 10
        Write-Host "[OK] Proxy acessivel em $baseUrl"
    } catch {
        throw "Proxy nao acessivel em $baseUrl. Execute -Acao instalar, confirme que o Docker Desktop esta rodando e consulte 'docker compose logs --tail 60' na pasta do proxy. Detalhe: $($_.Exception.Message)"
    }
}

function Consultar-Contas {
    $headers = Headers-Autenticados
    return Invoke-RestMethod -Uri "$baseUrl/admin/accounts" -Method Get -Headers $headers -TimeoutSec 30
}

switch ($Acao) {
    'iniciar' {
        Verificar-Comando 'docker'
        if (-not(Test-Path $composePath) -or -not(Test-Path $envPath)) {
            throw 'Proxy nao configurado. Use -Acao instalar uma unica vez antes de iniciar.'
        }
        $compose = [System.IO.File]::ReadAllText($composePath)
        $localPort = '- "127.0.0.1:${PORT:-8080}:${PORT:-8080}"'
        if (-not $compose.Contains($localPort)) {
            throw 'Porta local do proxy nao validada. Execute -Acao instalar para restringir a 127.0.0.1.'
        }
        Confirmar-DockerEngine
        Push-Location $repoDir
        try {
            $codigo = Executar-Nativo -Comando 'docker' -Argumentos @('compose', 'up', '-d')
            if ($codigo -ne 0) { throw 'Nao foi possivel iniciar o container existente.' }
        } finally { Pop-Location }
        Verificar-Servidor
        Write-Host '[OK] Proxy iniciado. Sessao pode exigir login manual se expirou.'
        break
    }
    'instalar' {
        Verificar-Comando 'git'
        Verificar-Comando 'docker'
        Confirmar-DockerEngine

        if (-not (Test-Path $repoDir)) {
            Write-Host '[1/4] Clonando o repositorio oficial do autor comunitario...'
            $codigo = Executar-Nativo -Comando 'git' -Argumentos @('clone', '--depth', '1', 'https://github.com/10/chatgpt-codex-proxy.git', $repoDir)
            if ($codigo -ne 0) { throw 'Falha ao clonar repositorio.' }
        } elseif (-not (Test-Path $composePath)) {
            throw "A pasta $repoDir existe mas nao contem compose.yaml; verifique-a manualmente."
        } else {
            Write-Host '[1/4] Repositorio ja existe, preservando seus arquivos.'
        }

        if (-not (Test-Path $envPath)) {
            Write-Host '[2/4] Criando chave forte para API local (sem imprimir segredo)...'
            $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
            $bytes = New-Object byte[] 32
            try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
            $key = [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
            [System.IO.File]::WriteAllText($envPath, "PROXY_API_KEY=$key`nPORT=8080`nDEBUG_LOG_PAYLOADS=false`n", (New-Object System.Text.UTF8Encoding($false)))
        } else {
            Write-Host '[2/4] .env existente preservado.'
        }
        $null = Ler-Chave

        Write-Host '[3/4] Restringindo a porta ao proprio PC (127.0.0.1)...'
        $compose = [System.IO.File]::ReadAllText($composePath)
        $originalPort = '- "${PORT:-8080}:${PORT:-8080}"'
        $localPort = '- "127.0.0.1:${PORT:-8080}:${PORT:-8080}"'
        if ($compose.Contains($originalPort)) {
            $compose = $compose.Replace($originalPort, $localPort)
            [System.IO.File]::WriteAllText($composePath, $compose, (New-Object System.Text.UTF8Encoding($false)))
        } elseif (-not $compose.Contains($localPort)) {
            throw 'Nao encontrei a porta esperada em compose.yaml. Nao iniciarei um proxy potencialmente exposto na rede.'
        }

        Write-Host '[4/4] Construindo/iniciando o container Docker...'
        Push-Location $repoDir
        try {
            $codigo = Executar-Nativo -Comando 'docker' -Argumentos @('compose', 'up', '-d', '--build')
            if ($codigo -ne 0) { throw 'Docker Compose falhou. Consulte docker compose logs --tail 80.' }
            $null = Executar-Nativo -Comando 'docker' -Argumentos @('compose', 'ps')
        } finally {
            Pop-Location
        }
        Verificar-Servidor
        Write-Host '[OK] Instalacao inicial concluida. Proximo: .\testar-codex-proxy.ps1 -Acao login'
        break
    }
    'login' {
        Verificar-Servidor
        $headers = Headers-Autenticados
        Write-Host 'ATENCAO: repositorio de terceiro; autentique somente se confiar no codigo e aceitar o risco de tokens armazenados no Docker.' -ForegroundColor Yellow
        $record = Invoke-RestMethod -Uri "$baseUrl/admin/accounts/device-login/start" -Method Post -Headers $headers -TimeoutSec 60
        if (-not $record.login_id -or -not $record.auth_url -or -not $record.user_code) {
            throw 'Resposta de login incompleta. Nao insira codigos em sites desconhecidos.'
        }
        [System.IO.File]::WriteAllText($loginIdPath, [string]$record.login_id)
        Write-Host "URL oficial de autorizacao informada pelo proxy: $($record.auth_url)"
        Write-Host "Codigo de dispositivo: $($record.user_code)"
        Write-Host 'Confira o dominio do site antes de entrar com sua conta. Conclua a autorizacao no navegador.'
        Write-Host 'Depois execute: .\testar-codex-proxy.ps1 -Acao status'
        break
    }
    'status' {
        Verificar-Servidor
        if (Test-Path $loginIdPath) {
            $id = [System.IO.File]::ReadAllText($loginIdPath).Trim()
            if ($id -match '^login_[A-Za-z0-9.]+$') {
                try {
                    $progress = Invoke-RestMethod -Uri "$baseUrl/admin/accounts/device-login/$id" -Method Get -Headers (Headers-Autenticados) -TimeoutSec 30
                    Write-Host "Login: $($progress.status)"
                    if ($progress.error) { Write-Warning $progress.error }
                } catch {
                    Write-Host 'Registro de login expirado ou indisponivel; consultando contas existentes.'
                }
            }
        }
        $accounts = Consultar-Contas
        if (-not $accounts.accounts -or @($accounts.accounts).Count -eq 0) {
            Write-Host 'Nenhuma conta conectada. Execute -Acao login.'
        } else {
            $accounts.accounts | Select-Object @{N='Status';E={$_.status}}, @{N='Elegivel';E={$_.eligible_now}}, @{N='Plano';E={$_.plan_type}} | Format-Table -AutoSize
            Write-Host 'Se a conta esta ativa, proximo: .\testar-codex-proxy.ps1 -Acao imagem'
        }
        break
    }
    'imagem' {
        Verificar-Servidor
        $accounts = Consultar-Contas
        if (-not @($accounts.accounts | Where-Object { $_.eligible_now }).Count) {
            throw 'Nenhuma conta elegivel. Execute -Acao login e depois -Acao status.'
        }
        $headers = Headers-Autenticados
        $body = @{
            model = $Modelo
            prompt = $Prompt
            n = 1
            size = '1024x1536'
            output_format = 'png'
        } | ConvertTo-Json -Depth 5
        Write-Host "Solicitando UMA imagem, modelo $Modelo. Isso pode consumir cota da conta ChatGPT."
        try {
            $response = Invoke-RestMethod -Uri "$baseUrl/v1/images/generations" -Method Post -Headers $headers -Body $body -ContentType 'application/json' -TimeoutSec 360
        } catch {
            throw "Falha na geracao: $($_.Exception.Message). Talvez a conta nao tenha acesso ao modelo de imagens ou o endpoint privado tenha mudado."
        }
        if (-not $response.data -or -not $response.data[0]) {
            throw 'Resposta sem data[0]; cheque logs do proxy.'
        }
        $image = $response.data[0]
        $folder = Join-Path $PSScriptRoot 'assets\gerados'
        New-Item -ItemType Directory -Path $folder -Force | Out-Null
        $path = Join-Path $folder 'teste-codex-proxy.png'
        if ($image.b64_json) {
            $bytes = [Convert]::FromBase64String([string]$image.b64_json)
            [System.IO.File]::WriteAllBytes($path, $bytes)
        } elseif ($image.url -and [string]$image.url -match '^data:image/[^;]+;base64,(.*)$') {
            $bytes = [Convert]::FromBase64String([string]$Matches[1])
            [System.IO.File]::WriteAllBytes($path, $bytes)
        } elseif ($image.url -and [string]$image.url -match '^https://') {
            Invoke-WebRequest -Uri $image.url -OutFile $path -TimeoutSec 120
        } else {
            throw 'Formato de imagem nao reconhecido. Esperado b64_json ou URL https.'
        }
        $size = (Get-Item $path).Length
        if ($size -lt 1000) { throw "Arquivo gerado tem apenas $size bytes; revise a resposta da API." }
        Write-Host "[OK] Imagem salva: $path ($size bytes)" -ForegroundColor Green
        Start-Process $path
        break
    }
    'parar' {
        Verificar-Comando 'docker'
        if (-not (Test-Path $composePath)) { throw 'Proxy ainda nao foi instalado nesta pasta.' }
        Push-Location $repoDir
        try {
            $codigo = Executar-Nativo -Comando 'docker' -Argumentos @('compose', 'down')
            if ($codigo -ne 0) { throw 'Falha ao parar o Docker Compose.' }
        } finally { Pop-Location }
        Write-Host 'Container parado. Volume de contas preservado. Para remover dados, sera preciso excluir o volume deliberadamente.'
        break
    }
}
