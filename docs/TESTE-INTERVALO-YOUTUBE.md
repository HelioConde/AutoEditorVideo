# Experimento de Shorts — episodio, curiosidade, nostalgia, proximo episodio

## Padrao de producao e distribuicao

A nova sequencia alterna 3 formatos: **Episodio em 60s -> Curiosidade -> Voce lembra? -> episodio seguinte**.
Cada publicacao deve ter pelo menos 60 minutos desde o envio confirmado da anterior.

Fila inicial para Death Note:
1. `102-death-note-ep02` — a armadilha de L (historia).
2. `201-death-note-rosto-nome` — por que conhecer so o nome nao basta? (curiosidade).
3. `301-death-note-voce-lembra-justica` — voce lembra de escolher Light ou L? (nostalgia).
4. `103-death-note-ep03` — a investigacao e a proposta dos olhos de shinigami (historia).

O EP01 ja foi enviado no experimento anterior. A fila inicial nao o republica.
Os dois formatos intermediarios sao videos NOVOS, nao repeticoes de 003 a 007.
Para continuar apos EP03, criar e revisar roteiros novos e repetir o mesmo padrao.

## Comando unico (PowerShell no Windows)

```powershell
cd "C:\Users\helio\Documents\arquivo-otaku-github"
git pull --ff-only origin main

# So exibe a sequencia, sem IA ou upload:
.\publicar-recaps-por-hora.ps1

# Gera voz, imagens IA, MP4, capa, descricao e publica cada video
# separando os uploads confirmados por pelo menos 60 minutos:
.\publicar-recaps-por-hora.ps1 -Publicar -Privacidade public
```

O processo roda **localmente**, em primeiro plano. Para publicar, mantenha o
computador ligado e a janela PowerShell aberta. O tempo conta desde o upload
anterior CONFIRMADO, nao desde o inicio da geracao. Gerar imagens e renderizar
pode prolongar o intervalo real.

Se EP02 ja tiver sido publicado pelo comando individual, a fila reconhece o
SHA-256 e o video_id local, nao reenvia EP02 e aguarda seu intervalo antes
da curiosidade. Se a fila antiga EP02 -> EP03 ja tiver sido executada e o
EP03 estiver publicado sem os dois formatos intermediarios, a nova fila
**interrompe e exige revisao**, em vez de inventar uma sequencia retroativa.

## Testar somente EP02

```powershell
.\criar-publicar-short.ps1 -Id 102-death-note-ep02 -Publicar -Privacidade public
```

Depois execute o comando da fila; ele reconhece o registro local se o MP4
e o ID de upload estiverem intactos.

## Seguranca de publicacao

- Sem `-Publicar`: somente planejamento, sem imagens IA, voz, OAuth ou upload.
- Somente videos cadastrados no repositorio entram na fila.
- Reutiliza caches e evita uploads duplicados usando SHA-256 + ID YouTube.
- Cada MP4 deve durar no maximo 60 segundos; erro interrompe a fila.
- Se voz, cenas IA, QA visual, render ou upload falhar, nenhum video posterior
  e publicado automaticamente.
- Nao repete upload cujo resultado remoto seja incerto; verificar YouTube Studio.
- Mantem a mesma privacidade ao retomar; nao altera publicacoes antigas.
- Credenciais e videos continuam no computador, nao no GitHub.
- Scripts locais nao contornam cotas de provedores nem garantem alcances no feed.

Comprovantes de envio:
`assets/gerados/publicacao-youtube/estado-upload-<sha256-12>.json`.

## Medicao

Registrar, apos **1h, 6h, 24h e 48h de cada upload**, visualizacoes,
visualizacoes intencionais, Mostrados no feed, espectadores que continuaram,
tempo medio, inscritos e comentarios. Comparar o mesmo tempo de vida,
diferenciando formato e horario; o teste nao prova um limite de publicacoes
na plataforma.

Arquivos: `scripts/publicar_recap_hourly.py`,
`publicar-recaps-por-hora.ps1` e `tests/test_publicar_recap_hourly.py`.
