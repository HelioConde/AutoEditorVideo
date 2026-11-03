# Publica os cinco Shorts aprovados, com metadados por episodio.
# Nao gera imagens/voz e nao modifica arquivos MP4.
[CmdletBinding()]
param(
  [ValidateSet('private','unlisted','public')][string]$Privacidade='private',
  [ValidateSet('ultrassutil','equilibrado','vivo')][string]$PerfilPersonagens='equilibrado'
)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$ids=@(
  '003-death-note-xadrez',
  '004-death-note-segundo-kira',
  '005-death-note-sangue',
  '006-death-note-shinigami',
  '007-death-note-maca'
)
$manifestPath=Join-Path $root 'conteudos\testes-animados-5.json'
$oauth=Join-Path $root '.secrets\youtube-oauth-client.json'
$publisher=Join-Path $root 'publicar-youtube.ps1'
$py=Join-Path $root '.venv\Scripts\python.exe'
if(-not(Test-Path $py)){throw 'Python .venv ausente; execute scripts\instalar-windows.ps1'}
$published=Join-Path $root 'assets\gerados\publicacao-youtube'
$metadataDir=Join-Path $published 'episodios'

if(-not(Test-Path $manifestPath)){throw "Manifesto nao encontrado: $manifestPath"}
if(-not(Test-Path $oauth)){throw "OAuth ausente: $oauth. Configure o acesso ao canal YouTube primeiro."}
if(-not(Test-Path $publisher)){throw "Publicador nao encontrado: $publisher"}
if(-not(Get-Command ffprobe -ErrorAction SilentlyContinue)){
  throw 'FFprobe ausente no PATH. Instale FFmpeg e abra um novo PowerShell.'
}
$manifest=Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$items=@()
$hashes=@{}

# Preflight de TODO o lote antes do primeiro upload.
foreach($id in $ids){
  $episode=@($manifest.episodes | Where-Object { $_.id -eq $id })
  if($episode.Count -ne 1){throw "Episodio nao encontrado ou duplicado: $id"}
  $video=Join-Path $root ("assets\gerados\shorts-animados\$id\$id-master-multicenas-personagens-v3-$PerfilPersonagens.mp4")
  if(-not(Test-Path -LiteralPath $video -PathType Leaf)){
    throw "MP4 ausente: $video. Renderize esse Short antes da publicacao."
  }
  if((Get-Item -LiteralPath $video).Length -lt 100000){
    throw "MP4 pequeno/incompleto: $video"
  }
  $probeOutput=(& ffprobe -v error -show_entries 'stream=codec_type,width,height:format=duration' -of json $video) -join "`n"
  if($LASTEXITCODE -ne 0){throw "FFprobe falhou para $id"}
  $probe=$probeOutput | ConvertFrom-Json
  $v=@($probe.streams | Where-Object { $_.codec_type -eq 'video' })
  $a=@($probe.streams | Where-Object { $_.codec_type -eq 'audio' })
  if($v.Count -lt 1 -or $a.Count -lt 1){throw "Short sem video ou audio: $id"}
  if(-not $probe.format -or -not $probe.format.duration){throw "Duracao nao identificada pelo ffprobe: $id"}
  $duration=[double]::Parse([string]$probe.format.duration,[System.Globalization.CultureInfo]::InvariantCulture)
  if([double]::IsNaN($duration) -or [double]::IsInfinity($duration) -or $duration -le 0 -or $duration -gt 60.0){
    throw "[60S BLOQUEADO] $id possui $duration segundos. Reduza o roteiro e renderize novamente; nenhum video do lote sera enviado."
  }
  if([int]$v[0].width -lt 480 -or [int]$v[0].height -lt 800 -or
      [Math]::Abs(([double]$v[0].width / [double]$v[0].height) - (9.0 / 16.0)) -gt .02){
    throw "Short sem formato vertical 9:16: $id"
  }
  $hash=(Get-FileHash -LiteralPath $video -Algorithm SHA256).Hash.ToLowerInvariant()
  if($hashes.ContainsKey($hash)){
    throw "Videos $($hashes[$hash]) e $id sao identicos. Upload em lote cancelado."
  }
  $hashes[$hash]=$id
  $record=Join-Path $published ('estado-upload-'+$hash.Substring(0,12)+'.json')
  if(Test-Path $record){
    $state=Get-Content -LiteralPath $record -Raw -Encoding UTF8 | ConvertFrom-Json
    if($state.video_id -and $state.privacidade_solicitada -ne $Privacidade){
      throw "Video $id ja enviado com privacidade $($state.privacidade_solicitada). O publicador nao altera privacidade de uploads anteriores. Confira no YouTube Studio."
    }
  }
  $items+= [pscustomobject]@{
    id=$id; episode=$episode[0]; video=$video
  }
}

New-Item -ItemType Directory -Path $metadataDir -Force | Out-Null
Push-Location $root
try {
  foreach($item in $items){
    $id=$item.id
    $episodeFile=Join-Path $metadataDir ($id+'.json')
    # Gerar a descricao via Python UTF-8, nunca como literal PowerShell 5.1.
    & $py (Join-Path $root 'scripts\metadata_shorts.py') --id $id --destino $episodeFile
    if($LASTEXITCODE -ne 0){throw "Falha ao gerar metadados UTF-8 para $id"}
    $cover=Join-Path $root ("assets\gerados\shorts-animados\$id\$id-master-capa.jpg")
    if(-not(Test-Path $cover)){
      throw "Capa final de $id ausente: $cover. Gere com -SomenteCapa antes de publicar."
    }
    Write-Host "`n=== PUBLICANDO $id ($Privacidade) ===" -ForegroundColor Cyan
    & $publisher -Etapa tudo -Privacidade $Privacidade -Video $item.video -Episodio $episodeFile -ImagemFonte $cover -CapaFinalShorts $cover -Refazer
    if($LASTEXITCODE -ne 0){throw "Publicacao falhou em $id; confira YouTube Studio antes de repetir."}
    Write-Host "[OK] Publicador concluiu: $id" -ForegroundColor Green
  }
  Write-Host "`n[CONCLUIDO] Cinco envios processados. Confirme a visibilidade no YouTube Studio." -ForegroundColor Green
} finally {
  Pop-Location
}
