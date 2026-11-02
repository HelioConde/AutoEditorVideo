# Arquivo Otaku: storyboard variavel -> master -> fundo/foreground -> Remotion.
# Nunca publica; preserva os assets e MP4 anteriores.
[CmdletBinding()]
param(
  [string]$Id='003-death-note-xadrez',
  [ValidateRange(1,60)][int]$Cena=1,
  [switch]$TodasCenas,
  [string]$Plano='',
  [string]$MasterExistente='',
  [ValidateSet('gpt-image-1.5','gpt-image-2')][string]$Modelo='gpt-image-1.5',
  [ValidateRange(0,180)][int]$MaxChamadas=3,
  [ValidateRange(2.5,12.0)][double]$MaxSegundosPorPlano=6,
  [switch]$SomentePlanejar,
  [switch]$SomenteValidar,
  [switch]$Renderizar,
  [switch]$CriarVoz,
  [switch]$Offline
)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$py=Join-Path $root '.venv\Scripts\python.exe'
if($Renderizar -and -not $TodasCenas){ throw 'Para renderizar o Short inteiro, use -TodasCenas.' }
if($MasterExistente -and $TodasCenas){ throw '-MasterExistente somente com uma cena.' }
if($CriarVoz -and $Offline){ throw 'Nao e possivel gerar voz em modo offline.' }

if($SomentePlanejar){
  if(-not(Test-Path $py)){
    $systemPython=Get-Command python -ErrorAction SilentlyContinue
    if(-not $systemPython){ throw 'Instale Python 3.11, ou uv para criar .venv.' }
    $py=$systemPython.Source
  }
  $planner=Join-Path $root 'scripts\roteiro_para_storyboard.py'
  $argsList=@($planner,'--id',$Id,'--max-segundos-por-plano', $MaxSegundosPorPlano.ToString([cultureinfo]::InvariantCulture))
  & $py @argsList
  if($LASTEXITCODE -ne 0){ throw 'Erro ao planejar o storyboard.' }
  return
}

if(-not(Test-Path $py)){
  if(-not(Get-Command uv -ErrorAction SilentlyContinue)){throw 'Instale uv: winget install --id astral-sh.uv -e'}
  & uv venv (Join-Path $root '.venv') --python 3.11
  if($LASTEXITCODE -ne 0){throw 'Erro ao criar .venv'}
}
# Nao execute imports potencialmente falhos com 2>$null:
# PowerShell 5.1 pode promover traceback nativo a erro terminante.
$checker=Join-Path $root 'scripts\diagnosticar_dependencias_master.py'
if(-not(Test-Path $checker)){throw "Verificador de dependencias ausente: $checker. Atualize com git pull."}
$missingCore = & $py $checker
if($LASTEXITCODE -ne 0){throw 'Falhou o verificador Python de dependencias'}
if($missingCore -and $missingCore.Trim()){
  Write-Host "[DEPENDENCIAS] Faltando ou com falha de import: $missingCore. Instalando via uv..." -ForegroundColor Yellow
  if(-not(Get-Command uv -ErrorAction SilentlyContinue)){
    throw "Instale uv: winget install --id astral-sh.uv -e. Depois execute: uv pip install --python .\.venv\Scripts\python.exe -r .\requirements-master.txt"
  }
  & uv pip install --python $py -r (Join-Path $root 'requirements-master.txt')
  if($LASTEXITCODE -ne 0){throw 'Falha ao instalar dependencias com uv; verifique a mensagem acima'}
  $missingAfter = & $py $checker
  if($LASTEXITCODE -ne 0 -or ($missingAfter -and $missingAfter.Trim())){
    throw "Dependencias ainda indisponiveis apos instalacao: $missingAfter"
  }
  Write-Host '[OK] Dependencias do motor Python verificadas.' -ForegroundColor Green
}
if($Renderizar){
  if(-not(Get-Command ffprobe -ErrorAction SilentlyContinue)){throw 'FFprobe ausente no PATH'}
  if(-not(Get-Command ffmpeg -ErrorAction SilentlyContinue)){throw 'FFmpeg ausente no PATH'}
  if(-not(Get-Command npm.cmd -ErrorAction SilentlyContinue)){throw 'Node/npm nao encontrado'}
  $motion=Join-Path $root 'motion-remotion'
  if(-not(Test-Path (Join-Path $motion 'node_modules'))){
    Push-Location $motion
    try {
      & npm.cmd install --no-audit --no-fund
      if($LASTEXITCODE -ne 0){throw 'Falha ao instalar Remotion'}
    } finally {Pop-Location}
  }
  if($CriarVoz){
    $missingVoice = & $py $checker --voz
    if($LASTEXITCODE -ne 0){throw 'Falhou a verificacao da biblioteca de voz'}
    if($missingVoice -and $missingVoice.Trim()){
      Write-Host '[DEPENDENCIAS] Instalando edge-tts para narracao...' -ForegroundColor Yellow
      if(-not(Get-Command uv -ErrorAction SilentlyContinue)){throw 'Instale uv para adicionar edge-tts'}
      & uv pip install --python $py 'edge-tts>=7,<9'
      if($LASTEXITCODE -ne 0){throw 'Nao foi possivel instalar edge-tts'}
      $missingVoiceAfter = & $py $checker --voz
      if($LASTEXITCODE -ne 0 -or ($missingVoiceAfter -and $missingVoiceAfter.Trim())){
        throw 'edge-tts continua indisponivel apos a instalacao'
      }
    }
  }
}
# Mantem o arquivo de credenciais onde ja estava. Nada e enviado ao GitHub.
$oldEnv=Join-Path $root '..\arquivo-otaku-kit\chatgpt-codex-proxy\.env'
if((Test-Path $oldEnv) -and -not (Test-Path (Join-Path $root 'chatgpt-codex-proxy\.env'))){
  $env:ARQUIVO_OTAKU_PROXY_ENV=$oldEnv
}
$script=Join-Path $root 'scripts\master_scenes.py'
$argsList=@($script,'--id',$Id,'--cena',[string]$Cena,'--modelo',$Modelo,
 '--max-chamadas',[string]$MaxChamadas,'--max-segundos-por-plano',
 $MaxSegundosPorPlano.ToString([cultureinfo]::InvariantCulture))
if($Plano){$argsList+=@('--plano',$Plano)}
if($MasterExistente){$argsList+=@('--master-existente',$MasterExistente)}
if($TodasCenas){$argsList+='--todas-cenas'}
if($SomenteValidar){$argsList+='--validar'}
if($Offline){$argsList+='--offline'}
& $py @argsList
if($LASTEXITCODE -ne 0){throw 'Geracao interrompida. Cache e videos anteriores preservados.'}
if($Renderizar){
  $videoArgs=@((Join-Path $root 'scripts\renderizar_master_remotion.py'),
    '--id',$Id,'--modelo',$Modelo,'--max-segundos-por-plano',
    $MaxSegundosPorPlano.ToString([cultureinfo]::InvariantCulture),'--renderizar')
  if($Plano){$videoArgs+=@('--plano',$Plano)}
  if($CriarVoz){$videoArgs+='--criar-voz'}
  & $py @videoArgs
  if($LASTEXITCODE -ne 0){throw 'Falhou montagem Remotion. Imagens mantidas em cache.'}
}
Write-Host '[OK] Fluxo local concluido, sem upload ao YouTube.'
