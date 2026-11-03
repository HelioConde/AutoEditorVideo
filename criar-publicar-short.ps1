# Um comando: voz + imagens IA + render <60s + metadados + capa + YouTube.
# Falhas transitorias tentadas novamente, mas nunca publica material incompleto.
[CmdletBinding()]
param(
    [string]$Id='101-death-note-ep01',
    [ValidateSet('gpt-image-1.5','gpt-image-2')][string]$Modelo='gpt-image-1.5',
    [ValidateSet('ultrassutil','equilibrado','vivo')][string]$Perfil='equilibrado',
    [ValidateRange(0,180)][int]$MaxChamadas=45,
    [ValidateRange(1,3)][int]$Tentativas=2,
    [ValidateSet('private','unlisted','public')][string]$Privacidade='private',
    [string]$AgendarEm='',
    [switch]$Publicar,
    [switch]$Refazer,
    [switch]$SomenteValidar
)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$env:PYTHONUNBUFFERED='1'
$py=Join-Path $root '.venv\Scripts\python.exe'
$program=Join-Path $root 'scripts\fluxo_unico_short.py'
if(-not(Test-Path $program)){throw 'Pipeline ausente: execute git pull --ff-only origin main.'}
if(-not(Test-Path $py)){
    if(-not(Get-Command uv -ErrorAction SilentlyContinue)){
        throw 'Instale uv: winget install --id astral-sh.uv -e'
    }
    & uv venv (Join-Path $root '.venv') --python 3.11
    if($LASTEXITCODE -ne 0){throw 'Nao foi possivel criar o ambiente Python .venv.'}
}
if(-not(Get-Command ffprobe -ErrorAction SilentlyContinue)){
    throw 'FFprobe ausente no PATH. Instale FFmpeg antes de usar o editor.'
}
if(-not $SomenteValidar){
    if(-not(Get-Command npm.cmd -ErrorAction SilentlyContinue)){
        throw 'Node.js/npm ausente. Instale Node.js e tente novamente.'
    }
    $checker=Join-Path $root 'scripts\diagnosticar_dependencias_master.py'
    if(-not(Test-Path $checker)){throw 'Verificador de dependencias master ausente.'}
    $missing=& $py $checker
    if($LASTEXITCODE -ne 0){throw 'Falha ao verificar dependencias Python.'}
    if($missing -and ($missing -join '').Trim()){
        if(-not(Get-Command uv -ErrorAction SilentlyContinue)){
            throw "Dependencias faltando: $missing. Instale uv para corrigir automaticamente."
        }
        & uv pip install --python $py -r (Join-Path $root 'requirements-master.txt')
        if($LASTEXITCODE -ne 0){throw 'Falhou a instalacao das dependencias master.'}
    }
    $voiceMissing=& $py $checker --voz
    if($LASTEXITCODE -ne 0){throw 'Falhou o diagnostico de voz.'}
    if($voiceMissing -and ($voiceMissing -join '').Trim()){
        if(-not(Get-Command uv -ErrorAction SilentlyContinue)){
            throw 'edge-tts ausente. Instale uv para corrigir.'
        }
        & uv pip install --python $py 'edge-tts>=7,<9'
        if($LASTEXITCODE -ne 0){throw 'Falha na instalacao edge-tts.'}
    }
    if(-not(Test-Path (Join-Path $root 'motion-remotion\node_modules'))){
        Push-Location (Join-Path $root 'motion-remotion')
        try {
            & npm.cmd install --no-audit --no-fund
            if($LASTEXITCODE -ne 0){throw 'Falhou a instalacao do motor Remotion.'}
        } finally {
            Pop-Location
        }
    }
}
if($Publicar){
    $oauth=Join-Path $root '.secrets\youtube-oauth-client.json'
    if(-not(Test-Path $oauth)){throw "OAuth YouTube nao configurado: $oauth"}
    $marker=Join-Path $root '.venv\arquivo-otaku-publicacao-deps-ok'
    if(-not(Test-Path $marker)){
        $requirements=Join-Path $root 'requirements-publicacao.txt'
        if(Get-Command uv -ErrorAction SilentlyContinue){
            & uv pip install --python $py -r $requirements
        } else {
            & $py -m pip install -r $requirements
        }
        if($LASTEXITCODE -ne 0){throw 'Falha ao instalar dependencias oficiais do YouTube.'}
        New-Item -ItemType File -Path $marker -Force | Out-Null
    }
}
$params=@($program,'--id',$Id,'--modelo',$Modelo,'--perfil',$Perfil,
          '--max-chamadas',[string]$MaxChamadas,
          '--tentativas',[string]$Tentativas,
          '--privacidade',$Privacidade)
if($Publicar){$params+='--publicar'}
if($AgendarEm){$params+=@('--agendar-em',$AgendarEm)}
if($Refazer){$params+='--refazer'}
if($SomenteValidar){$params+='--somente-validar'}
& $py @params
if($LASTEXITCODE -ne 0){
    throw "Pipeline interrompido (codigo $LASTEXITCODE). Imagens e voz em cache preservadas; nenhum upload de MP4 parcial permitido."
}
