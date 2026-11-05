# Lote 2 Otaku Multicena (BR) + Otaku Reframe (EN): 3 Shorts por canal.
# Sem -Publicar: valida a fila, sem IA, render ou upload.
# Com -Publicar: publica PUBLICAMENTE assim que cada video for aprovado no QA.
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

foreach($name in @('grade-50-shorts.ps1','preparar-publicados-en.ps1',
                   'gerar-shorts-en.ps1','publicar-shorts-en.ps1')){
    if(-not(Test-Path (Join-Path $root $name) -PathType Leaf)){
        throw "Arquivo ausente: $name. Atualize o projeto com git pull."
    }
}

function Invoke-Etapa {
    param([string]$Nome,[hashtable]$Parametros)
    & (Join-Path $script:root $Nome) @Parametros
    if(-not $?){throw "Falhou a etapa: $Nome"}
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
        Write-Host '[OK] Para iniciar producao e upload PUBLICO, acrescente -Publicar.' -ForegroundColor Green
        return
    }

    Write-Host '[UPLOAD] Publico, imediato e sem agendamento.' -ForegroundColor Yellow
    Write-Host '[BLEACH] 0 chamadas de imagem; usa somente cache.' -ForegroundColor Yellow
    Write-Host "[TETO IA] Outros 2 BR: ate $($MaxChamadasNovos*2) chamadas adicionais." -ForegroundColor Yellow
    $concluidos=New-Object System.Collections.Generic.List[string]
    $pendentes=New-Object System.Collections.Generic.List[string]

    foreach($ep in $br){
        try {
            Write-Host "[BR] $($ep.Id) | ate $($ep.Chamadas) chamadas" -ForegroundColor Cyan
            $p=@{
                Acao='ProduzirPublicar'
                InicioNaLista=[int]$ep.Numero
                Quantidade=1
                Modelo=$Modelo
                Perfil=$Perfil
                MaxChamadasPorVideo=[int]$ep.Chamadas
                ConfirmarPublicacao=$true
            }
            if($ep.Chamadas -gt 0){$p.ConfirmarCotaImagem=$true}
            if($ExigirMovimentoPersonagem){$p.ExigirMovimentoPersonagem=$true}
            Invoke-Etapa 'grade-50-shorts.ps1' $p
            $concluidos.Add("BR $($ep.Id)")
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
                Privacidade='public';ConfirmarEnvio=$true
            }
            $concluidos.Add("EN $id")
        }catch{
            $pendentes.Add("EN $id")
            Write-Warning "[EN PENDENTE] ${id}: $_"
            Write-Warning 'Se houve inicio de upload, confira o Studio antes de repetir.'
        }
    }

    Write-Host "[RESUMO] Concluidos: $($concluidos.Count); pendentes: $($pendentes.Count)." -ForegroundColor Cyan
    foreach($x in $concluidos){Write-Host "OK: $x" -ForegroundColor Green}
    foreach($x in $pendentes){Write-Warning "PENDENTE: $x"}
    Write-Host 'Confira as publicacoes no YouTube Studio dos dois canais.' -ForegroundColor Yellow
    if($pendentes.Count -gt 0){
        throw 'Lote parcialmente concluido. Consulte os avisos; nao faca reupload cego.'
    }
}finally {
    Pop-Location
}
