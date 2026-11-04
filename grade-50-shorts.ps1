# Grade Otaku Multicena: 50 Shorts. Never uploads unless -Acao Agendar
# AND -ConfirmarPublicacao; production uses an explicit AI call budget.
[CmdletBinding()]
param(
    [ValidateSet('Validar','Preparar','Produzir','Agendar')]
    [string]$Acao='Validar',
    [ValidateRange(1,50)][int]$InicioNaLista=1,
    [ValidateRange(1,50)][int]$Quantidade=50,
    [ValidateSet('gpt-image-1.5','gpt-image-2')]
    [string]$Modelo='gpt-image-2',
    [ValidateSet('ultrassutil','equilibrado','vivo')]
    [string]$Perfil='equilibrado',
    [ValidateRange(0,180)][int]$MaxChamadasPorVideo=0,
    [switch]$ConfirmarCotaImagem,
    [string]$InicioAgendamento='',
    [ValidateRange(1,168)][int]$IntervaloHoras=24,
    [switch]$ConfirmarPublicacao,
    [switch]$Refazer
)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$py=Join-Path $root '.venv\Scripts\python.exe'
$program=Join-Path $root 'scripts\grade_50_shorts.py'
if(-not(Test-Path $program)){
    throw 'Fila de 50 Shorts ausente. Rode git pull --ff-only origin main.'
}
if(-not(Test-Path $py)){
    if($Acao -eq 'Validar' -or $Acao -eq 'Preparar'){
        $python=Get-Command python.exe -ErrorAction SilentlyContinue
        if(-not $python){throw 'Python indisponivel. Prepare .venv primeiro.'}
        $py=$python.Source
    }else{
        throw 'Ambiente .venv ausente. Execute primeiro .\criar-publicar-short.ps1.'
    }
}
$argsList=@(
    $program,
    '--acao',$Acao.ToLowerInvariant(),
    '--inicio-na-lista',[string]$InicioNaLista,
    '--quantidade',[string]$Quantidade,
    '--modelo',$Modelo,
    '--perfil',$Perfil,
    '--max-chamadas-por-video',[string]$MaxChamadasPorVideo,
    '--intervalo-horas',[string]$IntervaloHoras
)
if($ConfirmarCotaImagem){$argsList+='--confirmar-cota-imagem'}
if($ConfirmarPublicacao){$argsList+='--confirmar-publicacao'}
if($InicioAgendamento){$argsList+=@('--inicio-agendamento',$InicioAgendamento)}
if($Refazer){$argsList+='--refazer'}
& $py @argsList
if($LASTEXITCODE -ne 0){
    throw "Grade de 50 Shorts interrompida (codigo $LASTEXITCODE). '
          + 'NENHUM reenvio automatico; verifique os logs e a pasta local."
}
