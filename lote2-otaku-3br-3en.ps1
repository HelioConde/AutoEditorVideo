# Lote 2 Otaku Multicena (BR) + Otaku Reframe (EN): 3 Shorts por canal.
# Sem -Publicar: valida a fila, sem IA, render ou upload.
# Com -Publicar: produz, verifica QA e ENVIA COMO PRIVADO; agende depois no YouTube Studio.
# Bleach: somente cache local, sem novas chamadas de IA.
[CmdletBinding()]
param(
    [switch]$Publicar,
    [ValidateSet('gpt-image-1.5','gpt-image-2')]
    [string]$Modelo='gpt-image-2',
    [ValidateSet('equilibrado','vivo','ultrassutil')]
    [string]$Perfil='equilibrado',
    [ValidateRange(0,180)]
    [int]$MaxChamadasNovos=30,
    [switch]$ExigirMovimentoPersonagem
)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$root=$PSScriptRoot

$enIds=@(
    '5004-jojo-steel-ball-run',
    '202-death-note-40-segundos',
    '401-jujutsu-kaisen-ep01'
)
$br=@(
    [pscustomobject]@{Numero=5;Id='5005-bleach-thousand-year-blood-war';Chamadas=0},
    [pscustomobject]@{Numero=9;Id='5009-overgeared';Chamadas=$MaxChamadasNovos},
    [pscustomobject]@{Numero=10;Id='5010-aoashi';Chamadas=$MaxChamadasNovos}
)
$manifesto='assets\gerados\otaku-en-lote2-3-shorts.json'

foreach($name in @('grade-50-shorts.ps1','criar-publicar-short.ps1',
                   'preparar-publicados-en.ps1','gerar-shorts-en.ps1',
                   'publicar-shorts-en.ps1')){
    if(-not(Test-Path (Join-Path $root $name) -PathType Leaf)){
        throw "Arquivo ausente: $name. Atualize o projeto com git pull."
    }
}

function Invoke-Etapa {
    param([string]$Nome,[hashtable]$Parametros)
    & (Join-Path $script:root $Nome) @Parametros
    if(-not $?){throw "Falhou a etapa: $Nome"}
}

function Get-EstadoBR {
    param([string]$Id)
    $video=Join-Path $script:root ("assets\gerados\shorts-animados\{0}\{0}-master-multicenas-personagens-v3-{1}.mp4" -f $Id,$script:Perfil)
    if(-not(Test-Path -LiteralPath $video -PathType Leaf)){return 'pendente'}
    $hash=(Get-FileHash -LiteralPath $video -Algorithm SHA256).Hash.ToLowerInvariant()
    $receipt=Join-Path $script:root ("assets\gerados\publicacao-youtube\estado-upload-{0}.json" -f $hash.Substring(0,12))
    if(-not(Test-Path -LiteralPath $receipt -PathType Leaf)){return 'pendente'}
    $status=Get-Content -LiteralPath $receipt -Raw -Encoding UTF8 | ConvertFrom-Json
    if(-not $status.video_id){return 'incerto'}
    if($status.privacidade_solicitada -eq 'private'){return 'privado'}
    return 'outro'
}

function Assert-Grade50QA {
    param([string]$Id)
    $python=Join-Path $script:root '.venv\Scripts\python.exe'
    if(-not(Test-Path -LiteralPath $python -PathType Leaf)){
        throw 'Ambiente Python .venv ausente; QA BR nao pode ser verificado.'
    }
    $codigo=@'
import sys
from pathlib import Path
sys.path.insert(0, str(Path("scripts").resolve()))
from grade_50_shorts import load_queue, ensure_ready
items = [ep for ep in load_queue() if ep["id"] == sys.argv[1]]
if len(items) != 1:
    raise RuntimeError("Episodio BR nao encontrado na grade")
ensure_ready(items[0], sys.argv[2], require_character_motion=(sys.argv[3] == "1"))
'@
    $strict='0'
    if($script:ExigirMovimentoPersonagem){$strict='1'}
    & $python -c $codigo $Id $script:Perfil $strict
    if($LASTEXITCODE -ne 0){throw "QA BR reprovado: $Id. Nenhum upload."}
}

function Get-EstadoEN {
    param([string]$Id)
    $path=Join-Path $script:root 'assets\gerados\publicacao-youtube-en\estado.json'
    if(-not(Test-Path $path -PathType Leaf)){return 'pendente'}
    $state=Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
    if(-not $state.items){return 'pendente'}
    $enviado=$false
    $incerto=$false
    foreach($p in $state.items.PSObject.Properties){
        if($p.Value.id -ne $Id){continue}
        if($p.Value.video_id){$enviado=$true}else{$incerto=$true}
    }
    if($incerto){return 'incerto'}
    if($enviado){return 'enviado'}
    return 'pendente'
}

Push-Location $root
try {
    Write-Host '[BR] Bleach (#5), Overgeared (#9), Aoashi (#10)' -ForegroundColor Cyan
    Write-Host '[EN] Steel Ball Run, Death Note 40s, Jujutsu Kaisen' -ForegroundColor Cyan
    if(-not $Publicar){
        Write-Host '[PREVIA] Nenhum video sera enviado ou gerado.' -ForegroundColor Yellow
        foreach($ep in $br){
            Invoke-Etapa 'grade-50-shorts.ps1' @{
                Acao='Validar';InicioNaLista=$ep.Numero;Quantidade=1
            }
        }
        Invoke-Etapa 'preparar-publicados-en.ps1' @{
            Acao='Verificar';Id=$enIds
        }
        Write-Host '[OK] Para produzir e enviar COMO PRIVADO, acrescente -Publicar.' -ForegroundColor Green
        return
    }

    Write-Host '[UPLOAD PRIVADO] Nenhum Short sera tornado publico automaticamente.' -ForegroundColor Yellow
    Write-Host '[AGENDAMENTO] Depois, defina os horarios no YouTube Studio, sem reenviar.' -ForegroundColor Yellow
    Write-Host '[BLEACH] 0 chamadas de imagem; usa somente cache.' -ForegroundColor Yellow
    Write-Host "[TETO IA] Outros 2 BR: ate $($MaxChamadasNovos*2) chamadas adicionais." -ForegroundColor Yellow
    $concluidos=New-Object System.Collections.Generic.List[string]
    $pendentes=New-Object System.Collections.Generic.List[string]

    foreach($ep in $br){
        try {
            Write-Host "[BR] $($ep.Id) | ate $($ep.Chamadas) chamadas" -ForegroundColor Cyan
            $estado=Get-EstadoBR -Id $ep.Id
            if($estado -eq 'privado'){
                Write-Host "[BR JA PRIVADO] $($ep.Id) - nao reenviar." -ForegroundColor Green
                $concluidos.Add("BR $($ep.Id) (ja privado)")
                continue
            }
            if($estado -ne 'pendente'){
                throw "Upload anterior encontrado ($estado). Confira o YouTube Studio antes de tentar novamente."
            }
            # A grade 50 tem publicacao exclusivamente PUBLICA; use apenas o modo Produzir.
            $p=@{
                Acao='Produzir'
                InicioNaLista=[int]$ep.Numero
                Quantidade=1
                Modelo=$Modelo
                Perfil=$Perfil
                MaxChamadasPorVideo=[int]$ep.Chamadas
            }
            if($ep.Chamadas -gt 0){$p.ConfirmarCotaImagem=$true}
            Invoke-Etapa 'grade-50-shorts.ps1' $p

            # Mesmo QA visual, de duracao, capa e cenas do fluxo da grade antes do upload.
            Assert-Grade50QA -Id $ep.Id
            # Reusa cache e publica como private; NAO usa ProduzirPublicar, que envia publico.
            Invoke-Etapa 'criar-publicar-short.ps1' @{
                Id=$ep.Id;Modelo=$Modelo;Perfil=$Perfil;VozMotor='edge'
                MaxChamadas=0;Privacidade='private';Publicar=$true
            }
            $estadoDepois=Get-EstadoBR -Id $ep.Id
            if($estadoDepois -ne 'privado'){
                throw "Envio privado sem recibo confirmado para $($ep.Id). Verifique Studio; nao reenvie."
            }
            $concluidos.Add("BR $($ep.Id) (privado)")
        }catch{
            $pendentes.Add("BR $($ep.Id)")
            Write-Warning "[BR PENDENTE] $($ep.Id): $_"
            Write-Warning 'Confirme o estado no Studio antes de tentar reenviar.'
        }
    }

    try {
        Invoke-Etapa 'preparar-publicados-en.ps1' @{
            Acao='Preparar';Id=$enIds;Saida=$manifesto
        }
    }catch{
        throw "[EN BLOQUEADO] Nao foi possivel preparar o manifesto. Motivo: $_"
    }

    foreach($id in $enIds){
        try {
            $status=Get-EstadoEN -Id $id
            if($status -eq 'enviado'){
                Write-Host "[EN JA ENVIADO] $id" -ForegroundColor Green
                $concluidos.Add("EN $id (ja enviado)")
                continue
            }
            if($status -eq 'incerto'){
                throw 'Upload EN anterior incerto. Confira o Studio e o estado local.'
            }
            Write-Host "[EN] Preparando voz, legendas e MP4: $id" -ForegroundColor Cyan
            foreach($acao in @('planejar','voz','renderizar')){
                $p=@{
                    Acao=$acao;Manifesto=$manifesto;Id=$id
                    Modelo=$Modelo;Perfil=$Perfil
                }
                if($ExigirMovimentoPersonagem -and $acao -eq 'renderizar'){
                    $p.ExigirMovimentoPersonagem=$true
                }
                Invoke-Etapa 'gerar-shorts-en.ps1' $p
            }
            Invoke-Etapa 'publicar-shorts-en.ps1' @{
                Acao='verificar';Manifesto=$manifesto;Id=$id;Perfil=$Perfil
            }
            Invoke-Etapa 'publicar-shorts-en.ps1' @{
                Acao='enviar';Manifesto=$manifesto;Id=$id;Perfil=$Perfil
                Privacidade='private';ConfirmarEnvio=$true
            }
            $concluidos.Add("EN $id (privado)")
        }catch{
            $pendentes.Add("EN $id")
            Write-Warning "[EN PENDENTE] ${id}: $_"
            Write-Warning 'Se houve inicio de upload, confira o Studio antes de repetir.'
        }
    }

    Write-Host "[RESUMO] Concluidos: $($concluidos.Count); pendentes: $($pendentes.Count)." -ForegroundColor Cyan
    foreach($x in $concluidos){Write-Host "OK: $x" -ForegroundColor Green}
    foreach($x in $pendentes){Write-Warning "PENDENTE: $x"}
    Write-Host 'Confira os videos PRIVADOS no YouTube Studio e agende por la.' -ForegroundColor Yellow
    if($pendentes.Count -gt 0){
        throw 'Lote parcialmente concluido. Consulte os avisos; nao faca reupload cego.'
    }
}finally {
    Pop-Location
}
