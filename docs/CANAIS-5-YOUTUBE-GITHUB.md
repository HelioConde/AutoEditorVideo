# Cinco canais YouTube no AutoEditorVideo — 05/11/2026

Fonte de verdade: config/youtube-channel-registry.json. Este cadastro NÃO cria
nem renomeia canais no YouTube, não conecta OAuth e NÃO publica vídeos.

## Identidades

| Chave | YouTube Channel ID | Nome atual verificado | Marca planejada | Idioma |
|---|---|---|---|---|
| br | UCXGYTuBYn-0Ziqin5ajKhOw | Otaku Multicena | Otaku Multicena | pt-BR |
| en | UCBoNbQjaMYdpJqPLRZAFkvQ | Otaku Reframe | Otaku Reframe | en-US |
| games | UCg77gYc1_wkHuL07XPtKcow | Hélio Conde | Conde Games (proposta, não renomeado) | pt-BR |
| kids | UCxEzVW2Uy44OUVurTQSg_Eg | Emanuelly Kids | Emanuelly Kids / série Fofinhos | pt-BR |
| alchemy | UCCTYFE5Cmz2aYZ37cJQ-wcg | Alchemy Flames | Alchemy Lab (renomeação pendente) | pt-BR |

Os nomes atuais foram consultados por Channel ID no YouTube em 05/11/2026.
A aprovação de um nome de marca NÃO significa que o nome do canal foi alterado.

## O que já existe

- BR e EN Otaku: uploaders existentes com OAuth protegido e rotas separadas.
- Games: entrada canal-gamer.ps1, sem função de publicação, gameplay real.
- Kids: série oficial Fofinhos no catálogo Emanuelly; música, fotos e
  classificação infantil exigem salvaguardas próprias.
- Alchemy Lab: identidade editorial planejada para tutoriais IA e automação;
  não existe ainda um uploader cloud desse canal.
- Scripts youtube_channel_registry.py e production_reservations.py passam a
  validar os cinco destinos e exigem reserva de vídeo no GitHub antes de gerar.

## Separação do YouTube OAuth

| Canal novo | GitHub Environment planejado | Secret planejado | Estado |
|---|---|---|---|
| games | youtube-games-private-upload | YOUTUBE_GAMES_TOKEN_JSON | upload bloqueado |
| kids | youtube-kids-private-upload | YOUTUBE_KIDS_TOKEN_JSON | upload bloqueado |
| alchemy | youtube-alchemy-private-upload | YOUTUBE_ALCHEMY_TOKEN_JSON | upload bloqueado |

Esses Secrets são NOMES de futuras configurações. Nenhum token foi inserido,
nenhum OAuth foi conectado e nenhuma alteração foi feita nas contas.
Nunca reutilizar tokens do Otaku BR/EN ou do Codex Proxy para enviar vídeos.
O uploader futuro deve verificar channels.list(mine=true) contra o ID
registrado, proteger a privacidade e impedir duplicações.

## Políticas obrigatórias

Games: categoria Gaming (20), público gamer geral; só gameplay próprio
ou autorizado, nunca inventar conquistas. Conde Games ainda é proposta.

Kids: série Fofinhos, Made for Kids = true, categoria Filme e animação (1);
sem chamadas para crianças comentarem, curtirem ou se inscreverem; respeitar
restrições do YouTube e direitos de imagem e música. O piloto antigo
MiniMundo Curioso continua sandbox com youtube_channel_id=null e
upload_enabled=false: NÃO vincular seus Shorts ao Emanuelly Kids sem revisar
marca, conteúdo e direitos.

Alchemy Lab: categoria Ciência e tecnologia (28); IA e automação com
experimentos verificáveis; não gerar conteúdo repetitivo de baixo valor;
declarar mídia sintética realista quando exigido. O canal continua exibido
como Alchemy Flames até o criador alterar o nome.

Todos: privacidade inicial privada, miniatura original gerada no projeto e
pertencente ao vídeo/canal, sem códigos AUTOEDITORVIDEO-... em descrição,
reserva do vídeo no GitHub antes de scripts, sem publicação pública
ou agendamento não autorizado.

## Validar sem acessar contas ou gerar imagens

No diretório do projeto, depois de atualizar a branch main:

- python scripts/youtube_channel_registry.py --action list
- python scripts/youtube_channel_registry.py --action verify --channel kids
- python scripts/production_reservations.py --acao status --canal games --id game-001-minecraft-um-coracao
- python -m pytest -q tests/test_youtube_channel_registry.py

A tentativa de checar autorização de upload para games/kids/alchemy deve
FALHAR enquanto a implantação de OAuth separado não existir.
O GitHub Actions verifica as regras, sem Secrets e sem qualquer upload.
