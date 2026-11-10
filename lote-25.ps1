# Gerencia fila de ate 25 videos. Nunca publica videos automaticamente.
[CmdletBinding()]
param(
    [ValidateSet('status','renderizar')][string]$Acao = 'status',
    [ValidateRange(1,25)][int]$Limite=25,
    [switch]$ConfirmarRender,
    [switch]$ReutilizarImagens,
    [switch]$ContinuarEmErro
)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$python=Join-Path $root '.venv\Scripts\python.exe'
if(-not(Test-Path $python)){throw 'Ambiente .venv nao encontrado; execute scripts\instalar-windows.ps1'}
$args=@((Join-Path $root 'scripts\lote_25.py'),'--acao',$Acao,'--limite',"$Limite")
if($ConfirmarRender){$args+='--confirmar-render'}
if($ReutilizarImagens){$args+='--reutilizar-imagens'}
if($ContinuarEmErro){$args+='--continuar-em-erro'}
& $python @args
if($LASTEXITCODE -ne 0){throw "Lote terminou com codigo $LASTEXITCODE. Veja os avisos."}
