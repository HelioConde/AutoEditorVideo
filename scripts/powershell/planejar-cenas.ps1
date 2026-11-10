# Planejador de cenas por acontecimentos do roteiro. Nao gera imagens nem faz upload.
[CmdletBinding()]
param(
    [string]$Id = '003-death-note-xadrez',
    [string]$Manifesto = '',
    [double]$Duracao = 0,
    [string]$Saida = ''
)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { throw 'Python .venv nao encontrado. Rode scripts\instalar-windows.ps1.' }
$params = @((Join-Path $root 'scripts\planejar_cenas_dinamicas.py'), '--episodio', $Id)
if ($Manifesto) { $params += @('--manifesto', $Manifesto) }
if ($Duracao -gt 0) { $params += @('--duracao', $Duracao.ToString([cultureinfo]::InvariantCulture)) }
if ($Saida) { $params += @('--saida', $Saida) }
& $python @params
if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel planejar as cenas.' }
