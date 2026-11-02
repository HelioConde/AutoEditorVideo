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
  [switch]$RepararFundo,
  [switch]$DiagnosticarCache,
  [switch]$StatusCodex,
  [switch]$Replanejar,
  [switch]$SomenteCapa,
  [switch]$ReprovarCena,
  [switch]$AprovarCena,
  [switch]$PrepararReprovadas,
  [ValidateSet('classico','multicamadas')][string]$ModoComposicao='classico',
  [switch]$AprovarMulticamadas,
  [string]$Motivo='Defeito anatomico ou objeto atravessando a mesa',
  [switch]$Renderizar,
  [switch]$CriarVoz,
  [switch]$SemAnimacao,
  [switch]$Esqueleto2D,
  [switch]$PrepararRig2D,
  [string]$ImportarQuadrosRig2D='',
  [switch]$AprovarRig2D,
  [ValidateSet('l','light')][string]$PersonagemRig='l',
  [ValidateRange(8,60)][int]$RigFps=30,
  [ValidateSet('ultrassutil','equilibrado','vivo')][string]$PerfilPersonagens='equilibrado',
  [switch]$Offline
)
$ErrorActionPreference='Stop'
$env:PYTHONUNBUFFERED='1' # Enviar log ao Studio em tempo real.
$root=$PSScriptRoot
$py=Join-Path $root '.venv\Scripts\python.exe'
if(($ReprovarCena -or $AprovarCena) -and ($Renderizar -or $CriarVoz -or $SomenteCapa -or $TodasCenas)){
  throw 'Revise uma cena de cada vez, sem -Renderizar, -CriarVoz, -SomenteCapa nem -TodasCenas.'
}
if($ReprovarCena -and $AprovarCena){throw 'Escolha -ReprovarCena ou -AprovarCena.'}
if($Esqueleto2D -and $SemAnimacao){throw 'Escolha -Esqueleto2D ou -SemAnimacao.'}
if($AprovarRig2D -and (-not $PSBoundParameters.ContainsKey('Motivo') -or
                         -not $Motivo.Trim())){
  throw '-AprovarRig2D precisa de -Motivo explicito depois da revisao manual dos frames.'
}
$rigOperations=@([int]$PrepararRig2D,[int][bool]$ImportarQuadrosRig2D,[int]$AprovarRig2D)
if(($rigOperations | Measure-Object -Sum).Sum -gt 1){throw 'Escolha apenas uma operacao Rig2D por vez.'}
if((($rigOperations | Measure-Object -Sum).Sum -gt 0) -and ($Renderizar -or $CriarVoz -or $TodasCenas -or $SomenteCapa -or $PrepararReprovadas)){
  throw 'Preparar/importar/aprovar Rig2D exige uma cena e nao renderiza no mesmo comando.'
}
if($AprovarMulticamadas -and ($ReprovarCena -or $AprovarCena -or $PrepararReprovadas -or $Renderizar -or $SomenteCapa -or $TodasCenas)){
  throw '-AprovarMulticamadas exige uma unica cena para revisao, sem -Renderizar nem outras operacoes.'
}
if($ModoComposicao -eq 'multicamadas' -and ($RepararFundo -or $Replanejar -or $MasterExistente -or $SomentePlanejar)){
  throw 'Modo multicamadas usa a master ja criada e o storyboard fixado. Nao combina com -RepararFundo, -Replanejar, -MasterExistente ou -SomentePlanejar.'
}
if($PrepararReprovadas -and ($ReprovarCena -or $AprovarCena -or $SomentePlanejar -or $SomenteValidar -or $DiagnosticarCache -or $Renderizar -or $CriarVoz -or $Replanejar -or $TodasCenas -or $SomenteCapa -or $RepararFundo -or $MasterExistente -or $Plano)){
  throw '-PrepararReprovadas e um passo de preparo local: execute sozinho com -Id e -Modelo.'
}
if($SomenteCapa -and ($Renderizar -or $CriarVoz)){
  throw '-SomenteCapa nao pode ser combinado com -Renderizar ou -CriarVoz.'
}
if($Renderizar -and -not $TodasCenas){ throw 'Para renderizar o Short inteiro, use -TodasCenas.' }
if($MasterExistente -and $TodasCenas){ throw '-MasterExistente somente com uma cena.' }
if($CriarVoz -and $Offline){ throw 'Nao e possivel gerar voz em modo offline.' }
if($StatusCodex){
  if(-not(Test-Path $py)){
    $systemPython=Get-Command python -ErrorAction SilentlyContinue
    if(-not $systemPython){ throw 'Python nao encontrado para diagnostico do proxy.' }
    $py=$systemPython.Source
  }
  & $py (Join-Path $root 'scripts\estado_codex_proxy.py')
  if($LASTEXITCODE -ne 0){throw 'Falhou o diagnostico local do Codex Proxy.'}
  return
}

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
# Mantem o arquivo de credenciais onde ja estava. Nada e enviado ao GitHub.
$oldEnv=Join-Path $root '..\arquivo-otaku-kit\chatgpt-codex-proxy\.env'
if((Test-Path $oldEnv) -and -not (Test-Path (Join-Path $root 'chatgpt-codex-proxy\.env'))){
  $env:ARQUIVO_OTAKU_PROXY_ENV=$oldEnv
}
if($PrepararRig2D -or $ImportarQuadrosRig2D -or $AprovarRig2D){
  $rigArgs=@((Join-Path $root 'scripts\rigby2d_bridge.py'),
    '--id',$Id,'--modelo',$Modelo,'--cena',[string]$Cena,
    '--personagem',$PersonagemRig,'--fps',[string]$RigFps)
  if($PrepararRig2D){$rigArgs+='--preparar'}
  if($ImportarQuadrosRig2D){$rigArgs+=@('--importar-quadros',$ImportarQuadrosRig2D)}
  if($AprovarRig2D){$rigArgs+=@('--aprovar','--motivo',$Motivo)}
  & $py @rigArgs
  if($LASTEXITCODE -ne 0){throw 'Falha na preparacao/revisao Rigby2D. Caches originais preservados.'}
  return
}
if($PrepararReprovadas){
  & $py (Join-Path $root 'scripts\preparar_cenas_reprovadas.py') '--id' $Id '--modelo' $Modelo
  if($LASTEXITCODE -ne 0){throw 'Falhou preparo das cenas reprovadas; nenhum pedido pago enviado.'}
  return
}
if($ReprovarCena -or $AprovarCena){
  $reviewArgs=@((Join-Path $root 'scripts\revisao_visual_cenas.py'),
    '--id',$Id,'--modelo',$Modelo,'--cena',[string]$Cena,
    '--status',$(if($ReprovarCena){'reprovado'}else{'aprovado'}),
    '--motivo',$Motivo)
  if($Plano){$reviewArgs+=@('--plano',$Plano)}
  & $py @reviewArgs
  if($LASTEXITCODE -ne 0){throw 'Falhou o registro de revisao visual. Imagens mantidas.'}
  return
}
if($SomenteCapa){
  $capaArgs=@((Join-Path $root 'scripts\renderizar_master_remotion.py'),
    '--id',$Id,'--modelo',$Modelo,'--somente-capa',
    '--max-segundos-por-plano',$MaxSegundosPorPlano.ToString([cultureinfo]::InvariantCulture))
  if($Plano){$capaArgs+=@('--plano',$Plano)}
  & $py @capaArgs
  if($LASTEXITCODE -ne 0){throw 'Falhou ao criar capa local. Imagens originais preservadas.'}
  Write-Host '[OK] Capa premium gerada com cache local, sem IA ou upload.'
  return
}
if($ModoComposicao -eq 'multicamadas' -or $AprovarMulticamadas){
  $multArgs=@((Join-Path $root 'scripts\extract_scene_layers.py'),
    '--id',$Id,'--cena',[string]$Cena,'--modelo',$Modelo,
    '--max-chamadas',[string]$MaxChamadas,
    '--max-segundos-por-plano',$MaxSegundosPorPlano.ToString([cultureinfo]::InvariantCulture))
  if($Plano){$multArgs+=@('--plano',$Plano)}
  if($AprovarMulticamadas){$multArgs+=@('--aprovar','--motivo',$Motivo)}
  if($DiagnosticarCache -or $SomenteValidar){$multArgs+='--diagnosticar-cache'}
  if($Offline){$multArgs+='--offline'}
  if($TodasCenas){$multArgs+='--todas-cenas'}
  # Rendering with a zero-call budget uses existing approved multi layers
  # and falls back to legacy layers for scenes that were not converted.
  if($Renderizar -and $MaxChamadas -eq 0){
    Write-Host '[MULTICAMADAS] Render apenas, sem chamadas de imagem.' -ForegroundColor Cyan
  } else {
    & $py @multArgs
    if($LASTEXITCODE -ne 0){throw 'Extracao multicamadas interrompida. Cache e raws preservados.'}
  }
  # TTS nao depende da aprovacao da arte: preparar voz/legendas agora,
  # mesmo que o Short precise aguardar a revisao das novas camadas.
  if($CriarVoz){
    $voiceArgs=@((Join-Path $root 'scripts\renderizar_master_remotion.py'),
      '--id',$Id,'--modelo',$Modelo,'--somente-voz','--criar-voz',
      '--max-segundos-por-plano',$MaxSegundosPorPlano.ToString([cultureinfo]::InvariantCulture))
    if($Plano){$voiceArgs+=@('--plano',$Plano)}
    & $py @voiceArgs
    if($LASTEXITCODE -ne 0){throw 'Nao foi possivel gerar voz/legendas. Imagens preservadas.'}
  }
  if($Renderizar){
    $checkArgs=@((Join-Path $root 'scripts\extract_scene_layers.py'),
      '--id',$Id,'--modelo',$Modelo,'--verificar-aprovacoes',
      '--todas-cenas','--max-chamadas','0',
      '--max-segundos-por-plano',$MaxSegundosPorPlano.ToString([cultureinfo]::InvariantCulture))
    if($Plano){$checkArgs+=@('--plano',$Plano)}
    & $py @checkArgs
    if($LASTEXITCODE -ne 0){
      Write-Warning 'Imagens e voz geradas/em cache, mas o MP4 aguarda aprovacao visual. Nenhuma cena reprovada sera renderizada.'
      Write-Host 'Confira os previews, aprove cada cena e execute novamente com -MaxChamadas 0 -Renderizar.' -ForegroundColor Yellow
      return
    }
    $videoArgs=@((Join-Path $root 'scripts\renderizar_master_remotion.py'),
      '--id',$Id,'--modelo',$Modelo,'--max-segundos-por-plano',
      $MaxSegundosPorPlano.ToString([cultureinfo]::InvariantCulture),'--renderizar')
    if($Plano){$videoArgs+=@('--plano',$Plano)}
    $videoArgs+=@('--animacao',$(if($Esqueleto2D){'esqueleto2d'}elseif($SemAnimacao){'desligada'}else{'cinematica'}))
    $videoArgs+=@('--perfil-personagens',$PerfilPersonagens)
    & $py @videoArgs
    if($LASTEXITCODE -ne 0){throw 'Remotion bloqueou render ou falta aprovacao visual.'}
  }
  Write-Host '[OK] Modo multicamadas concluido; nenhum upload ao YouTube.' -ForegroundColor Green
  return
}
$script=Join-Path $root 'scripts\master_scenes.py'
$argsList=@($script,'--id',$Id,'--cena',[string]$Cena,'--modelo',$Modelo,
 '--max-chamadas',[string]$MaxChamadas,'--max-segundos-por-plano',
 $MaxSegundosPorPlano.ToString([cultureinfo]::InvariantCulture))
if($Plano){$argsList+=@('--plano',$Plano)}
if($MasterExistente){$argsList+=@('--master-existente',$MasterExistente)}
if($TodasCenas){$argsList+='--todas-cenas'}
if($SomenteValidar){$argsList+='--validar'}
if($RepararFundo){$argsList+='--reparar-fundo'}
if($DiagnosticarCache){$argsList+='--diagnosticar-cache'}
if($Replanejar){$argsList+='--replanejar'}
if($Offline){$argsList+='--offline'}
& $py @argsList
if($LASTEXITCODE -ne 0){throw 'Geracao interrompida. Cache e videos anteriores preservados.'}
if($Renderizar){
  $videoArgs=@((Join-Path $root 'scripts\renderizar_master_remotion.py'),
    '--id',$Id,'--modelo',$Modelo,'--max-segundos-por-plano',
    $MaxSegundosPorPlano.ToString([cultureinfo]::InvariantCulture),'--renderizar')
  if($Plano){$videoArgs+=@('--plano',$Plano)}
  if($CriarVoz){$videoArgs+='--criar-voz'}
  $videoArgs+=@('--animacao',$(if($Esqueleto2D){'esqueleto2d'}elseif($SemAnimacao){'desligada'}else{'cinematica'}))
    $videoArgs+=@('--perfil-personagens',$PerfilPersonagens)
  & $py @videoArgs
  if($LASTEXITCODE -ne 0){throw 'Falhou montagem Remotion. Imagens mantidas em cache.'}
}
Write-Host '[OK] Fluxo local concluido, sem upload ao YouTube.'
