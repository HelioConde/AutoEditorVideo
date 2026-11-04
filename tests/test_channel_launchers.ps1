# Teste hermetico das rotas PowerShell. NENHUMA chamada real a Python/OAuth/YouTube.
# Executar em Windows PowerShell: powershell -NoProfile -File tests\test_channel_launchers.ps1
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$repo=Split-Path -Parent $PSScriptRoot

function Assert-True {
  param([bool]$Condicao,[string]$Mensagem)
  if(-not $Condicao){throw "[TESTE FALHOU] $Mensagem"}
}
function Assert-Bloqueado {
  param([scriptblock]$Bloco,[string]$Mensagem)
  $bloqueou=$false
  try { & $Bloco | Out-Null } catch { $bloqueou=$true }
  Assert-True $bloqueou $Mensagem
}
function Ler-Registro {
  $arq=Join-Path $script:temp 'registro.json'
  if(-not(Test-Path -LiteralPath $arq)){throw "Registro fake ausente: $arq"}
  return (Get-Content -LiteralPath $arq -Raw | ConvertFrom-Json)
}

foreach($nome in @('canal-gamer.ps1','canal-ingles.ps1')){
  $arquivo=Join-Path $repo $nome
  $tokens=$null;$errors=$null
  [System.Management.Automation.Language.Parser]::ParseFile(
    $arquivo,[ref]$tokens,[ref]$errors
  ) | Out-Null
  Assert-True ($errors.Count -eq 0) "Erro de sintaxe no $nome"
}

$temp=Join-Path ([IO.Path]::GetTempPath()) ('teste-launchers-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $temp | Out-Null
try {
  Copy-Item (Join-Path $repo 'canal-gamer.ps1') $temp
  Copy-Item (Join-Path $repo 'canal-ingles.ps1') $temp

  @'
[CmdletBinding()]
param([string]$Acao,[string]$Canal,[string]$Id,[switch]$Refazer)
@{motor='piloto';acao=$Acao;canal=$Canal;id=$Id;refazer=[bool]$Refazer} |
  ConvertTo-Json -Compress | Set-Content (Join-Path $PSScriptRoot 'registro.json')
'@ | Set-Content (Join-Path $temp 'piloto-canais-v3.ps1') -Encoding UTF8

  @'
[CmdletBinding()]
param([string]$Acao,[string[]]$Id=@(),[string]$Saida)
@{motor='preparar';acao=$Acao;id=$Id;saida=$Saida} |
  ConvertTo-Json -Compress | Set-Content (Join-Path $PSScriptRoot 'registro.json')
if($Acao -eq 'Preparar'){
  $folder=Split-Path -Parent $Saida
  New-Item -ItemType Directory -Force -Path $folder | Out-Null
  '{}' | Set-Content -LiteralPath $Saida -Encoding UTF8
}
'@ | Set-Content (Join-Path $temp 'preparar-publicados-en.ps1') -Encoding UTF8

  @'
[CmdletBinding()]
param([string]$Acao,[string]$Id,[string]$Manifesto,[string]$Modelo,
      [string]$Perfil,[switch]$Refazer,[switch]$ExigirMovimentoPersonagem)
@{motor='gerar';acao=$Acao;id=$Id;manifesto=$Manifesto;modelo=$Modelo;
  perfil=$Perfil;refazer=[bool]$Refazer;movimento=[bool]$ExigirMovimentoPersonagem} |
  ConvertTo-Json -Compress | Set-Content (Join-Path $PSScriptRoot 'registro.json')
'@ | Set-Content (Join-Path $temp 'gerar-shorts-en.ps1') -Encoding UTF8

  @'
[CmdletBinding()]
param([string]$Acao,[string]$Id,[string]$Manifesto,[string]$Perfil,
      [string]$Privacidade,[int]$Limite,[switch]$ConfirmarEnvio)
@{motor='publicar';acao=$Acao;id=$Id;manifesto=$Manifesto;perfil=$Perfil;
  privacidade=$Privacidade;limite=$Limite;confirma=[bool]$ConfirmarEnvio} |
  ConvertTo-Json -Compress | Set-Content (Join-Path $PSScriptRoot 'registro.json')
'@ | Set-Content (Join-Path $temp 'publicar-shorts-en.ps1') -Encoding UTF8

  $g=Join-Path $temp 'canal-gamer.ps1'
  $en=Join-Path $temp 'canal-ingles.ps1'

  & $g -Acao Validar | Out-Null
  $registro=Ler-Registro
  Assert-True ($registro.motor -eq 'piloto' -and $registro.canal -eq 'games') 'Gamer nao deve acessar Kids'
  Assert-True ($registro.acao -eq 'validar') 'Gamer deve validar por padrao'
  Assert-Bloqueado {& $g -Acao Voz} 'Gamer precisa de ID ao gerar voz'
  Assert-Bloqueado {& $g -Acao Voz -Id 'kids-001-estrela-azul'} 'Gamer precisa rejeitar ID Kids'
  Assert-Bloqueado {& $g -Acao Preparar -Refazer} 'Gamer nao deve refazer validacao'
  & $g -Acao Renderizar -Id 'game-001-minecraft-um-coracao' -Refazer | Out-Null
  $registro=Ler-Registro
  Assert-True ($registro.acao -eq 'renderizar' -and $registro.refazer -and
               $registro.id -eq 'game-001-minecraft-um-coracao') 'Gamer deve passar Refazer somente ao proprio episodio'

  & $en -Acao Resumo | Out-Null
  $registro=Ler-Registro
  Assert-True ($registro.motor -eq 'preparar' -and $registro.acao -eq 'Resumo') 'EN padrao somente resume, sem upload'
  & $en -Acao Preparar | Out-Null
  $manifesto=Join-Path $temp 'assets\gerados\otaku-br-publicados-en-v3.json'
  Assert-True (Test-Path -LiteralPath $manifesto -PathType Leaf) 'Preparar deve gerar manifesto EN'
  & $en -Acao Voz -Id '003-death-note-xadrez' | Out-Null
  $registro=Ler-Registro
  Assert-True ($registro.motor -eq 'gerar' -and $registro.acao -eq 'voz' -and
               $registro.id -eq '003-death-note-xadrez') 'EN deve gerar voz apenas do ID indicado'
  Assert-True ($registro.manifesto -eq $manifesto) 'EN deve usar manifesto proprio'
  Assert-Bloqueado {& $en -Acao Renderizar} 'EN nao deve renderizar lote silenciosamente'
  Assert-Bloqueado {& $en -Acao Enviar -Id '003-death-note-xadrez'} 'EN exige ConfirmarEnvio'
  Assert-Bloqueado {& $en -Acao Enviar -Id '003-death-note-xadrez' -ConfirmarEnvio} 'EN bloqueia conta sem ID conferido'

  $seg=Join-Path $temp '.secrets'
  New-Item -ItemType Directory -Force -Path $seg | Out-Null
  'UCXGYTuBYn-0Ziqin5ajKhOw' | Set-Content (Join-Path $seg 'youtube-en-channel-id.txt') -Encoding UTF8
  Assert-Bloqueado {& $en -Acao Enviar -Id '003-death-note-xadrez' -ConfirmarEnvio} 'EN rejeita ID do canal brasileiro'
  'UCBoNbQjaMYdpJqPLRZAFkvQ' | Set-Content (Join-Path $seg 'youtube-en-channel-id.txt') -Encoding UTF8
  Assert-Bloqueado {
    & $en -Acao Enviar -Id '003-death-note-xadrez' -Privacidade public -ConfirmarEnvio
  } 'EN publico exige uma segunda confirmacao'
  & $en -Acao VerificarUpload -Id '003-death-note-xadrez' | Out-Null
  $registro=Ler-Registro
  Assert-True ($registro.acao -eq 'verificar' -and -not $registro.confirma) 'Verificacao nao deve enviar'
  & $en -Acao Enviar -Id '003-death-note-xadrez' -ConfirmarEnvio | Out-Null
  $registro=Ler-Registro
  Assert-True ($registro.motor -eq 'publicar' -and $registro.acao -eq 'enviar' -and
               $registro.confirma -and $registro.privacidade -eq 'private' -and
               $registro.limite -eq 1) 'EN deve enviar somente um MP4, privado por padrao e com confirmacao'

  $legacy=Join-Path $temp 'conteudos\testes-animados-5-en.json'
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $legacy) | Out-Null
  '{}' | Set-Content -LiteralPath $legacy -Encoding UTF8
  & $en -Acao Planejar -Catalogo Legado -Id '003-death-note-xadrez' | Out-Null
  $registro=Ler-Registro
  Assert-True ($registro.acao -eq 'planejar' -and $registro.manifesto -eq $legacy) 'EN legado deve permanecer isolado'
  Assert-Bloqueado {& $en -Acao Preparar -Catalogo Legado} 'Fila BR->EN nao pode se misturar com legado'
  Assert-Bloqueado {& $en -Acao Voz -Id '003-death-note-xadrez' -ExigirMovimentoPersonagem} 'Movimento estrito apenas no render'

  Write-Host '[TESTES OK] Gamer PT-BR e Otaku Reframe EN: roteamento, protecoes e defaults.' -ForegroundColor Green
}finally{
  Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
}
