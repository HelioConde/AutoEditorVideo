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
- Games: entrada canal-gamer.ps1, sem função de publicação; novos Shorts utilizam somente ilustrações IA, sem gameplay.
- Kids: série oficial Fofinhos no catálogo Emanuelly; música, fotos e
  classificação infantil exigem salvaguardas próprias.
- Alchemy Lab: identidade editorial planejada para tutoriais IA e automação;
  não existe ainda um uploader cloud desse canal.
- Scripts youtube_channel_registry.py e production_reservations.py passam a
  validar os cinco destinos e exigem reserva de vídeo no GitHub antes de gerar.

## OAuth individual dos cinco canais no mesmo Environment

**youtube-private-upload** é o Environment único existente. Ele deve
permanecer restrito à branch main. A centralização dos nomes de Secrets
reduz o isolamento entre jobs, não permite compartilhar tokens de conta.

| Canal | Environment único | Secret exclusivo | Situação |
|---|---|---|---|
| br | youtube-private-upload | YOUTUBE_BR_TOKEN_JSON | preservar |
| en | youtube-private-upload | YOUTUBE_EN_TOKEN_JSON | preservar |
| games | youtube-private-upload | YOUTUBE_GAMES_TOKEN_JSON | adicionar com consentimento |
| kids | youtube-private-upload | YOUTUBE_KIDS_TOKEN_JSON | adicionar com consentimento |
| alchemy | youtube-private-upload | YOUTUBE_ALCHEMY_TOKEN_JSON | adicionar com consentimento |

O sexto Secret, YOUTUBE_CLIENT_JSON, é o cliente OAuth já existente e
**não deve ser substituído** por este procedimento. Nenhum token é
transferido pela simples alteração do código ou pelo merge do PR.
Cada verificação exige channels.list(mine=true) e o ID exato.
Os uploaders dos canais novos continuam BLOQUEADOS; OAuth autorizado
não é autorização para publicação. Guia:
docs/CONECTAR-3-CANAIS-OAUTH-GITHUB.md.

## Políticas obrigatórias

Games: categoria Gaming (20), público gamer geral; NÃO gravar nem exigir gameplay.
Usar apenas artes e cenas geradas por IA, declaradas como ilustrativas;
não inventar testes/conquistas. Conde Games ainda é proposta.

Kids: série Fofinhos, Made for Kids = true, categoria Filme e animação (1);
sem chamadas para crianças comentarem, curtirem ou se inscreverem; respeitar
restrições do YouTube e direitos de imagem e música. O piloto antigo
MiniMundo Curioso continua sandbox com youtube_channel_id=null e
upload_enabled=false: NÃO vincular seus Shorts ao Emanuelly Kids sem revisar
marca, conteúdo e direitos.

Alchemy Lab: categoria Ciência e tecnologia (28); IA e automação com
ilustrações originais geradas por IA. Explicações factuais e tutoriais conceituais;
se não houve teste, não insinuar experimento real. Evitar conteúdo repetitivo;
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

## Regra editorial visual confirmada em 05/11/2026

- Gamer: **zero gameplay gravado**; vídeos de curiosidade, nostalgia e jogos em alta usam imagens e animações geradas por IA com aviso de que não são capturas de jogo.
- IA: explicações e comparações conceituais ilustradas por imagens geradas por IA; sem alegações falsas de testes, resultados ou interface do produto.
- Os lotes e metadados ativos estão em `conteudos/helio-conde-games-grade-50-seo-v1.json`, `conteudos/alchemy-lab-grade-50-v1.json` e `conteudos/lote-6-games-alchemy-producao-v1.json`.
