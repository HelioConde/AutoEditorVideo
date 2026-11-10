# Entrada única do AutoEditorVideo. Compatível com Windows PowerShell 5.1 e PowerShell 7.
# Os motores legados permanecem internos até migração e testes.
[CmdletBinding()]
param(
  [ValidateSet('ajuda','br','en','gamer','kids','fofinhos','alchemy','diagnostico')]
  [string]$Canal='ajuda',
  [string]$Acao='',
  [string]$Id='',
  [string]$Manifesto='',
  [ValidateSet('private','unlisted','public')][string]$Privacidade='private',
  [switch]$Refazer,
  [switch]$ConfirmarEnvio,
  [switch]$ConfirmarPublico
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$root=$PSScriptRoot

function Show-Help {
  Write-Host 'AutoEditorVideo - comando unico' -ForegroundColor Cyan
  Write-Host '.\autoeditor.ps1 -Canal br -Acao validar -Id 101-death-note-ep01'
  Write-Host '.\autoeditor.ps1 -Canal br -Acao produzir -Id 101-death-note-ep01'
  Write-Host '.\autoeditor.ps1 -Canal en -Acao resumo'
  Write-Host '.\autoeditor.ps1 -Canal en -Acao renderizar -Id 202-death-note-40-segundos'
  Write-Host '.\autoeditor.ps1 -Canal gamer -Acao validar'
  Write-Host '.\autoeditor.ps1 -Canal gamer -Acao renderizar -Id game-101-minecraft-agua-v2'
  Write-Host '.\autoeditor.ps1 -Canal fofinhos -Acao planejar'
  Write-Host '.\autoeditor.ps1 -Canal kids -Acao planejar -Id 1'
  Write-Host '.\autoeditor.ps1 -Canal diagnostico'
  Write-Host 'EN enviar exige -Id -ConfirmarEnvio; publico tambem exige -ConfirmarPublico.'
  Write-Host 'BR produzir nao publica; BR enviar exige -ConfirmarEnvio e usa private por padrao.'
  Write-Host 'Alchemy: apenas indice editorial por enquanto; sem motor local canonico confirmado.'
}

function Invoke-Internal([string]$File, [hashtable]$Params) {
  $path=Join-Path $root $File
  if(-not (Test-Path -LiteralPath $path -PathType Leaf)){throw "Motor ausente: $File"}
  Write-Host "[AUTOEDITOR] $File" -ForegroundColor Cyan
  & $path @Params
  if(-not $?){throw "Falha no motor $File"}
}
$action=$Acao.ToLowerInvariant()
switch($Canal) {
  'ajuda' {Show-Help; break}
  'diagnostico' {
    Write-Host 'Verificando entradas principais:'
    foreach($file in @('criar-publicar-short.ps1','canal-ingles.ps1','canal-gamer.ps1','gerar-historia-kids.ps1','fofinhos-ep01.ps1')) {
      Write-Host ("{0}: {1}" -f $file, $(if(Test-Path (Join-Path $root $file)){'OK'}else{'AUSENTE'}))
    }
    break
  }
  'br' {
    if($action -notin @('validar','produzir','enviar')){throw 'BR aceita validar, produzir ou enviar.'}
    if(-not $Id){throw 'Informe -Id para BR.'}
    if($action -eq 'enviar' -and -not $ConfirmarEnvio){throw 'Upload bloqueado: informe -ConfirmarEnvio.'}
    if($action -eq 'enviar' -and $Privacidade -eq 'public' -and -not $ConfirmarPublico){throw 'Publicacao publica bloqueada: informe -ConfirmarPublico.'}
    $args=@{Id=$Id;Privacidade=$Privacidade}
    if($Refazer){$args.Refazer=$true}
    if($action -eq 'validar'){$args.SomenteValidar=$true}
    if($action -eq 'enviar'){$args.Publicar=$true}
    Invoke-Internal 'criar-publicar-short.ps1' $args
    break
  }
  'en' {
    $allowed=@('resumo','verificarfontes','preparar','planejar','voz','capa','renderizar','verificarupload','conectar','enviar')
    if(-not $action){$action='resumo'}
    if($action -notin $allowed){throw "EN aceita: $($allowed -join ', ')"}
    if($action -eq 'enviar' -and (-not $Id -or -not $ConfirmarEnvio)){throw 'EN upload exige -Id e -ConfirmarEnvio.'}
    if($action -eq 'enviar' -and $Privacidade -eq 'public' -and -not $ConfirmarPublico){throw 'EN publico exige -ConfirmarPublico.'}
    $map=@{resumo='Resumo';verificarfontes='VerificarFontes';preparar='Preparar';planejar='Planejar';voz='Voz';capa='Capa';renderizar='Renderizar';verificarupload='VerificarUpload';conectar='Conectar';enviar='Enviar'}
    $args=@{Acao=$map[$action];Privacidade=$Privacidade}
    if($Id){$args.Id=$Id}
    if($Manifesto){$args.Manifesto=$Manifesto}
    if($Refazer){$args.Refazer=$true}
    if($ConfirmarEnvio){$args.ConfirmarEnvio=$true}
    if($ConfirmarPublico){$args.ConfirmarPublico=$true}
    Invoke-Internal 'canal-ingles.ps1' $args
    break
  }
  'gamer' {
    if(-not $action){$action='validar'}
    $map=@{validar='Validar';preparar='Preparar';inspecionar='Inspecionar';verificarvideo='VerificarVideo';voz='Voz';renderizar='Renderizar'}
    if(-not $map.ContainsKey($action)){throw 'Gamer aceita validar, preparar, inspecionar, verificarvideo, voz, renderizar.'}
    $args=@{Acao=$map[$action]}
    if($Id){$args.Id=$Id}
    if($Refazer){$args.Refazer=$true}
    Invoke-Internal 'canal-gamer.ps1' $args
    break
  }
  'kids' {
    if(-not $action){$action='planejar'}
    $map=@{planejar='Planejar';voz='Voz';renderizar='Renderizar';verificar='Verificar';abrir='Abrir'}
    if(-not $map.ContainsKey($action)){throw 'Kids aceita planejar, voz, renderizar, verificar, abrir.'}
    $args=@{Acao=$map[$action];Parte=$(if($Id){$Id}else{'1'})}
    if($Refazer){$args.Refazer=$true}
    Invoke-Internal 'gerar-historia-kids.ps1' $args
    break
  }
  'fofinhos' {
    if(-not $action){$action='planejar'}
    $map=@{planejar='Planejar';voz='Voz';guiaflores='GuiaFlores';renderizar='Renderizar';abrir='Abrir'}
    if(-not $map.ContainsKey($action)){throw 'Fofinhos aceita planejar, voz, guiaflores, renderizar, abrir.'}
    $args=@{Acao=$map[$action]}
    if($Refazer){$args.Refazer=$true}
    Invoke-Internal 'fofinhos-ep01.ps1' $args
    break
  }
  'alchemy' {
    if($action -and $action -ne 'planejar'){throw 'Alchemy ainda nao possui entrada canonica validada neste comando. Use -Acao planejar.'}
    $index=Join-Path $root 'canais\alchemy-lab\conteudos\indice.json'
    if(-not(Test-Path -LiteralPath $index)){throw 'Indice Alchemy ausente.'}
    Get-Content -LiteralPath $index -Raw -Encoding UTF8 | Write-Output
    break
  }
}
