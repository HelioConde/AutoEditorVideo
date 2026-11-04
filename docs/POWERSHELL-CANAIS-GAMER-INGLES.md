# PowerShell por canal — Gamer (PT-BR) e Otaku Reframe (EN)

## Objetivo

Dois arquivos dedicados na raiz do AutoEditorVideo, sem misturar idioma,
Shorts, logins ou diretorios de saida:

- canal-gamer.ps1 -> Gamer, jogos em portugues brasileiro (3 roteiros iniciais).
- canal-ingles.ps1 -> Otaku Reframe, anime em ingles americano (en-US).

O canal Kids continua com o motor piloto-canais-v3.ps1 -Canal kids.
Os canais Games e Kids ainda nao estao criados/vinculados no YouTube.
O Otaku Reframe **ja existe**, com Channel ID
UCBoNbQjaMYdpJqPLRZAFkvQ.

Ambos os PowerShells foram desenhados para **nao publicar por padrao**.

## 1. Gamer em PT-BR

No PowerShell Windows:

    cd "C:\Users\helio\Documents\arquivo-otaku-github"
    git pull --ff-only origin main

    # Nenhum TTS ou upload: apenas validar e gerar pacotes
    .\canal-gamer.ps1 -Acao Validar
    .\canal-gamer.ps1 -Acao Preparar
    .\canal-gamer.ps1 -Acao Inspecionar

    # Criar narracao PT-BR de UM Short (usa Edge TTS)
    .\canal-gamer.ps1 -Acao Voz -Id game-001-minecraft-um-coracao

    # Renderizar UM Short com gameplay verdadeiro ja gravado
    .\canal-gamer.ps1 -Acao Renderizar -Id game-001-minecraft-um-coracao

    # Checar MP4 via ffprobe
    .\canal-gamer.ps1 -Acao VerificarVideo -Id game-001-minecraft-um-coracao

Outros IDs disponíveis:
- game-002-roblox-obby
- game-003-tillfolk-colonia

O Gamer **nao solicita tokens nem publica**. Para renderizar, coloque
cinco gravacoes reais de jogo (suficientes para a duracao da cena) nas
pastas existentes em assets/gerados/piloto-canais-v3/capturas/<ID>/,
como cena-01.mp4 ate cena-05.mp4.

A renderizacao usa Remotion, ffprobe e a narracao de
pt-BR-AntonioNeural. A verificacao nao assegura fidelidade artistica,
permissoes de uso, ausencia de bugs ou bom desempenho no algoritmo.

## 2. Canal Ingles: Otaku Reframe

O script canal-ingles.ps1 tem dois catalogos:
- PublicadosBR (padrao): Shorts JA publicados no canal brasileiro e
  com correspondencia editorial aprovada. Gera manifestos EN independentes.
- Legado: o lote historico de cinco roteiros EN, sem alterar esse lote.

Etapas locais sem upload:

    # Conferir fontes
    .\canal-ingles.ps1 -Acao Resumo
    .\canal-ingles.ps1 -Acao VerificarFontes

    # Preparar manifesto ingles dos Shorts BR confirmados
    .\canal-ingles.ps1 -Acao Preparar

    # Gerar audio EN so de um episodio
    .\canal-ingles.ps1 -Acao Planejar -Id 003-death-note-xadrez
    .\canal-ingles.ps1 -Acao Voz -Id 003-death-note-xadrez

    # Exportar o MP4; opcionalmente exigir camada movel do personagem
    .\canal-ingles.ps1 -Acao Renderizar -Id 003-death-note-xadrez -ExigirMovimentoPersonagem

    # Conferir arquivo, metadados e QA do MP4 sem enviar
    .\canal-ingles.ps1 -Acao VerificarUpload -Id 003-death-note-xadrez

Para um roteiro legado ja existente:

    .\canal-ingles.ps1 -Catalogo Legado -Acao Planejar -Id 004-death-note-segundo-kira

A opcao -ExigirMovimentoPersonagem bloqueia cenas apenas com movimento
de camera onde personagens exigem camadas moveis verificadas. Camadas
rigidas nao equivalem a articulacao de membros; sempre revisar o MP4.

O canal ingles usa a voz en-US-GuyNeural, OAuth e diretorios exclusivos.
Jamais usar IDs, tokens ou metadados dos canais brasileiro, Gamer ou Kids.

### Conectar e envio OPCIONAL (com confirmacao)

**Estes comandos NAO foram executados.** Sao para usar somente apos
revisar video, narração, legendas, direitos e autorizacao.

    # Configure ID real em .secrets/youtube-en-channel-id.txt
    # O script exige exatamente UCBoNbQjaMYdpJqPLRZAFkvQ

    .\canal-ingles.ps1 -Acao Conectar

    # O envio nao ocorre sem ID individual e ConfirmarEnvio
    .\canal-ingles.ps1 -Acao Enviar -Id 003-death-note-xadrez -ConfirmarEnvio

O comando acima, se executado com conta certa e assets aprovados,
envia como **private** por padrao. Para publicar diretamente em public:

    .\canal-ingles.ps1 -Acao Enviar -Id 003-death-note-xadrez -Privacidade public -ConfirmarEnvio -ConfirmarPublico

Ha protecao de duplicidade e falha ambigua no publicador EN existente.
Nao disparar novo envio se a API der retorno incerto: conferir o Studio.

## Requisitos e limitacoes

- Windows com PowerShell, Python .venv e dependencias do repositorio.
- Para renderizacao: Node/Remotion, ffmpeg/ffprobe, narracao Edge TTS,
  artes aprovadas (EN) ou gameplay real (Games).
- Os roteiros e metadados sao drafts; nenhum canal Gamer foi criado nem
  sao fornecidas credenciais em arquivos de codigo.
- Nenhum comando de producao envia video sem acao especifica de envio.
- Testes isolados em tests/test_channel_launchers.ps1 verificam
  roteamento, idioma por motor, confirmacao, privacidade e identidade.
