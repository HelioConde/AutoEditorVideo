# Testa precisamente o bloco de validacao do script principal no Windows PowerShell 5.1.
# Nao faz chamadas de IA e nao precisa de Python, FFmpeg ou dependencias.
$ErrorActionPreference='Stop'
$scriptPath=Join-Path $PSScriptRoot '..\gerar-shorts-master.ps1'
$source=[System.IO.File]::ReadAllText($scriptPath)
$start=$source.IndexOf('$rigOperationCount=0')
$stop=$source.IndexOf('if($AprovarMulticamadas',$start)
if($start -lt 0 -or $stop -le $start){
  throw 'Bloco de validacao das operacoes Rig2D nao localizado.'
}
$block=[ScriptBlock]::Create($source.Substring($start,$stop-$start))

$cases=@(
  @{Name='sem operacao';Prepare=$false;Import='';Approve=$false;Count=0;Error=$false;Render=$false},
  @{Name='preparar sozinho';Prepare=$true;Import='';Approve=$false;Count=1;Error=$false;Render=$false},
  @{Name='importar sozinho';Prepare=$false;Import='C:\export\l';Approve=$false;Count=1;Error=$false;Render=$false},
  @{Name='aprovar sozinho';Prepare=$false;Import='';Approve=$true;Count=1;Error=$false;Render=$false},
  @{Name='importar vazio ou espacos';Prepare=$false;Import='   ';Approve=$false;Count=0;Error=$false;Render=$false},
  @{Name='preparar+aprovar';Prepare=$true;Import='';Approve=$true;Count=2;Error=$true;Render=$false},
  @{Name='preparar+importar';Prepare=$true;Import='C:\export\l';Approve=$false;Count=2;Error=$true;Render=$false},
  @{Name='importar+aprovar';Prepare=$false;Import='C:\export\l';Approve=$true;Count=2;Error=$true;Render=$false},
  @{Name='preparar+renderizar';Prepare=$true;Import='';Approve=$false;Count=1;Error=$true;Render=$true}
)
foreach($case in $cases){
  [switch]$PrepararRig2D=$case.Prepare
  [switch]$AprovarRig2D=$case.Approve
  $ImportarQuadrosRig2D=[string]$case.Import
  $Renderizar=[bool]$case.Render
  $CriarVoz=$false
  $TodasCenas=$false
  $SomenteCapa=$false
  $PrepararReprovadas=$false
  $rigOperationCount=-1
  $caught=$null
  try {
    . $block
  } catch {
    $caught=$_
  }
  if([bool]$caught -ne [bool]$case.Error){
    throw "Falha no caso '$($case.Name)': erro=$caught esperado=$($case.Error)"
  }
  if($rigOperationCount -ne $case.Count){
    throw "Falha no caso '$($case.Name)': contagem=$rigOperationCount esperada=$($case.Count)"
  }
  if($caught -and $caught.Exception.Message -match 'System.Int32|converter o valor'){
    throw "Falha original de conversao de switch no caso '$($case.Name)'"
  }
  Write-Host "[OK] $($case.Name) contagem=$rigOperationCount"
}
Write-Host '[PASSOU] Validacao Rig2D compativel com Windows PowerShell 5.1.'
