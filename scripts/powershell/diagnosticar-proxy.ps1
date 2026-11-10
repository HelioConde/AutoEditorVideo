# Diagnostico somente leitura. Nao faz login nem chama o gerador de imagens.
[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
$envPath=Join-Path $PSScriptRoot 'chatgpt-codex-proxy\.env'
if(-not (Test-Path $envPath)){throw 'Arquivo do proxy nao encontrado: chatgpt-codex-proxy\.env'}
$raw=[IO.File]::ReadAllText($envPath)
$m=[regex]::Match($raw,'(?m)^PROXY_API_KEY\s*=\s*(.*?)\s*$')
if(-not $m.Success){throw 'PROXY_API_KEY nao foi localizada no .env'}
$apiKey=$m.Groups[1].Value.Trim().Trim('"').Trim("'")
if(-not $apiKey){throw 'Chave local vazia'}
try {
  $r=Invoke-RestMethod -Uri 'http://127.0.0.1:8080/admin/accounts' -Method Get -Headers @{Authorization="Bearer $apiKey"} -TimeoutSec 20
} catch {throw "O proxy nao respondeu. Confira o Docker Desktop e a porta 8080. Erro: $($_.Exception.Message)"}
$records=@($r.accounts | Where-Object { $null -ne $_ })
Write-Host ("Contas conectadas: {0}" -f $records.Count)
foreach($a in $records){
  Write-Host ("- Status: {0}; elegivel: {1}; plano: {2}" -f $a.status,$a.eligible_now,$a.plan_type)
  if($a.cooldown_until){Write-Host ("  Em espera ate: {0}" -f $a.cooldown_until)}
  if($a.status -ne 'active') {Write-Host '  Conta inativa/expirada. Confira o login por dispositivo.'}
  elseif($a.eligible_now -ne $true){Write-Host '  Conta ativa sem disponibilidade agora. Pode ser limite de uso, cooldown ou token; consulte cotas no proprio servico.'}
}
if($records.Count -eq 0){Write-Host 'Nao existe conta autorizada. Rode testar-codex-proxy.ps1 -Acao login'}
elseif(@($records|Where-Object {$_.eligible_now -eq $true}).Count -eq 0){Write-Host 'Nao faca novas requisicoes de imagem agora. Use o modo -ReutilizarImagens ou aguarde a disponibilidade.'}
Write-Host 'Apenas leitura: nenhuma imagem gerada, nenhum video enviado.'
