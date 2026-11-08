# AutoEditorVideo: conectar GitHub -> ADB Wi-Fi -> Samsung -> galeria do Kwai.
# Sistema de estagio, NAO realiza publicacao, login nem toque no aplicativo.
[CmdletBinding()]
param(
  [ValidateSet('Diagnosticar','Monitorar','InstalarAgendamento','RemoverAgendamento')]
  [string]$Acao='Diagnosticar',
  [switch]$ConfirmarAgendamento
)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$repo='HelioConde/AutoEditorVideo'
$taskName='AutoEditorVideo-Kwai-ADB-Stage'
$script=Join-Path $root 'scripts\kwai_github_pc_agent.py'
$bridge=Join-Path $root 'scripts\kwai_adb_local_bridge.py'
if(-not(Test-Path -LiteralPath $script -PathType Leaf)){throw 'Agente local Kwai nao encontrado. Execute git pull --ff-only origin main.'}
if(-not(Test-Path -LiteralPath $bridge -PathType Leaf)){throw 'Bridge ADB nao encontrado. Atualize o projeto.'}

$python = Get-Command python.exe -ErrorAction SilentlyContinue
if($null -eq $python) {
  $venv=Join-Path $root '.venv\Scripts\python.exe'
  if(-not(Test-Path -LiteralPath $venv -PathType Leaf)){throw 'Python 3 ausente. Instale Python ou configure .venv.'}
  $pythonPath=$venv
} else {
  $pythonPath=$python.Source
}
& $pythonPath --version
if($LASTEXITCODE -ne 0){throw 'Python nao esta funcionando.'}

if($Acao -eq 'RemoverAgendamento') {
  if(-not $ConfirmarAgendamento){throw 'Use -ConfirmarAgendamento para remover a tarefa.'}
  Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction Stop
  Write-Host '[KWAI] Agendamento local removido. Os videos no telefone foram preservados.'
  return
}
$gh=Get-Command gh.exe -ErrorAction SilentlyContinue
if($null -eq $gh){throw 'GitHub CLI ausente. Instale gh e autentique no seu PC via gh auth login.'}
$adb=Get-Command adb.exe -ErrorAction SilentlyContinue
if($null -eq $adb -and -not(Test-Path 'C:\platform-tools\adb.exe' -PathType Leaf)){
  throw 'ADB nao foi encontrado. Mantenha C:\platform-tools\adb.exe ou adicione ADB ao PATH.'
}
if($Acao -eq 'Diagnosticar') {
  & $pythonPath $script --action dry-run
  if($LASTEXITCODE -ne 0){throw 'Falha ao consultar a fila do GitHub.'}
  & $pythonPath $bridge --action diagnose
  if($LASTEXITCODE -ne 0){throw 'ADB Samsung nao conectado. Confira a Depuracao Wi-Fi.'}
  Write-Host '[OK] Github e telefone comunicam. Nenhum upload ao Kwai.'
  return
}
if($Acao -eq 'Monitorar') {
  & $pythonPath $script --action watch --interval-seconds 180
  exit $LASTEXITCODE
}
if(-not $ConfirmarAgendamento){
  throw 'A instalacao da tarefa exige -ConfirmarAgendamento. Nenhuma alteracao feita.'
}
# Executa sob o mesmo usuario interativo que pareou o celular no ADB.
# Nao armazena senhas, tokens ou permissao de administrador.
$who=[System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$action=New-ScheduledTaskAction -Execute $pythonPath -Argument ('"'+$script+'" --action once') -WorkingDirectory $root
$start=(Get-Date).AddMinutes(1)
$trigger=New-ScheduledTaskTrigger -Once -At $start -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration (New-TimeSpan -Days 365)
$principal=New-ScheduledTaskPrincipal -UserId $who -LogonType Interactive -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 20)
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Write-Host "[OK] Agente Kwai instalado: verifica fila do GitHub a cada 5 minutos sob sua sessao Windows."
Write-Host '[SEGURANCA] Apenas transfere MP4 aprovado pelo ADB; nao abre nem publica no Kwai.'
Write-Host "[CONTROLE] .\kwai-github-celular.ps1 -Acao RemoverAgendamento -ConfirmarAgendamento"
