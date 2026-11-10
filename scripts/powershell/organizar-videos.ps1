# Organizador de MP4s - Kids, Gamer, Otaku Multicena e Otaku Reframe.
# Modo padrao PREVER: nada altera. Organizar COPIA, nao move/apaga originais.
[CmdletBinding()]
param(
    [ValidateSet('Prever','Organizar','Abrir')][string]$Acao='Prever',
    [ValidateSet('Copiar','Link')][string]$Metodo='Copiar',
    [ValidateSet('Todos','Kids','Gamer','Otaku Multicena','Otaku Reframe')]
    [string]$Canal='Todos'
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$python=Join-Path $root '.venv\Scripts\python.exe'
if(-not(Test-Path -LiteralPath $python -PathType Leaf)){
    $cmd=Get-Command python -ErrorAction SilentlyContinue
    if(-not $cmd){throw 'Python nao instalado. Configure .venv ou o comando python.'}
    $python=$cmd.Source
}
$organizador=Join-Path $root 'scripts\organizar_videos_por_canal.py'
if(-not(Test-Path -LiteralPath $organizador -PathType Leaf)){
    throw 'Organizador ausente. Execute git pull --ff-only origin main.'
}
$library=Join-Path $root 'assets\gerados\biblioteca-videos'
if($Acao -eq 'Abrir'){
    if($Canal -eq 'Todos'){$pasta=$library}else{$pasta=Join-Path $library $Canal}
    if(-not(Test-Path -LiteralPath $pasta -PathType Container)){
        throw 'Biblioteca ainda nao foi criada. Execute .\organizar-videos.ps1 -Acao Organizar.'
    }
    Start-Process explorer.exe -ArgumentList ('"'+$pasta+'"')
    return
}
if($Canal -ne 'Todos'){
    throw '-Canal serve apenas com -Acao Abrir. Para organizar, catalogar os quatro canais juntos.'
}
$acaoPython=if($Acao -eq 'Organizar'){'organizar'}else{'prever'}
$metodoPython=if($Metodo -eq 'Link'){'link'}else{'copiar'}
if($metodoPython -eq 'link'){
    Write-Warning 'Link fisico usa os mesmos bytes do original. Editar o MP4 na biblioteca tambem alterara o original. Nao e backup independente.'
}
Write-Host "[BIBLIOTECA] $Acao | metodo=$Metodo | nenhum upload" -ForegroundColor Cyan
& $python $organizador --acao $acaoPython --raiz $root --metodo $metodoPython
if($LASTEXITCODE -ne 0){throw 'Organizacao interrompida. Arquivos originais preservados.'}
if($Acao -eq 'Organizar'){
    Write-Host "[OK] Abra no Explorador: $library" -ForegroundColor Green
    Write-Host 'Os caminhos antigos dos motores, caches e publicadores continuam intactos.' -ForegroundColor Cyan
}else{
    Write-Host '[PREVIA] Nada foi copiado ou movido. Para aplicar: .\organizar-videos.ps1 -Acao Organizar' -ForegroundColor Yellow
}
