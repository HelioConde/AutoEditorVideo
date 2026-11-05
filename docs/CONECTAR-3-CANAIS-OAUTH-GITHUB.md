# Conectar Gamer, Kids e Alchemy Lab no GitHub — OAuth protegido

Etapa 05/11/2026. **Cloud-first.** O Windows faz somente o consentimento
inicial no Google; o GitHub Actions verifica a identidade e, em outra etapa
futura, renderiza e publica. **Nenhum vídeo é gerado ou enviado aqui.**

| Canal | ID real | Environment GitHub |
|---|---|---|
| Gamer (nome atual Hélio Conde) | UCg77gYc1_wkHuL07XPtKcow | youtube-games-private-upload |
| Emanuelly Kids (série Fofinhos) | UCxEzVW2Uy44OUVurTQSg_Eg | youtube-kids-private-upload |
| Alchemy Lab (nome atual Alchemy Flames) | UCCTYFE5Cmz2aYZ37cJQ-wcg | youtube-alchemy-private-upload |

## Etapa 1 — criar ambientes protegidos

Abra https://github.com/HelioConde/AutoEditorVideo/settings/environments
e crie exatamente os três Environments acima. Em cada um: Deployment
branches and tags > Selected branches and tags > autorizar somente a branch
main (tipo branch; não usar coringa). Opcionalmente, adicionar revisão
obrigatória no Kids. Não liberar bypass desnecessário.

O workflow confere as regras de cada Environment em job SEM Secrets.
Se algo estiver permissivo, ele bloqueia antes de carregar tokens.

## Etapa 2 — autorizar uma conta de cada vez no PC

No PowerShell:

    cd C:\Users\helio\Documents\arquivo-otaku-github
    git pull --ff-only origin main
    .\.venv\Scripts\python.exe -m pip install -r requirements-publicacao.txt

O OAuth client desktop já utilizado pelo AutoEditorVideo precisa existir
na pasta local .secrets\youtube-oauth-client.json. Nenhum segredo deve ser
enviado no chat ou adicionado ao Git.

    .\conectar-novos-canais.ps1 -Canal games -Acao Inspecionar
    .\conectar-novos-canais.ps1 -Canal games -Acao Conectar
    .\conectar-novos-canais.ps1 -Canal kids -Acao Conectar
    .\conectar-novos-canais.ps1 -Canal alchemy -Acao Conectar

Cada conexão abre o navegador e exige consentimento no Google. Se você
selecionar uma conta que não administra o Channel ID registrado,
o script BLOQUEIA e NÃO salva o token. É necessário conceder os escopos
youtube.upload + youtube.readonly e receber refresh token offline.

Tokens privados resultantes ficam em .secrets (ignorado no Git):
- youtube-games-cloud-token.json
- youtube-kids-cloud-token.json
- youtube-alchemy-cloud-token.json

Um token existente só é substituído com -SubstituirToken explicitamente.

## Etapa 3 — transferir tokens para os Environments com consentimento

Estas ações transferem tokens de longa duração para o GitHub Environment.
Execute SOMENTE se concordar com esse armazenamento. O PowerShell
verifica a política exclusiva de main antes de transferir algo.

    .\conectar-novos-canais.ps1 -Canal games -Acao EnviarSecret -ConfirmarArmazenamentoGitHub
    .\conectar-novos-canais.ps1 -Canal kids -Acao EnviarSecret -ConfirmarArmazenamentoGitHub
    .\conectar-novos-canais.ps1 -Canal alchemy -Acao EnviarSecret -ConfirmarArmazenamentoGitHub

Cada Environment terá YOUTUBE_CLIENT_JSON mais um token diferente:
- games: YOUTUBE_GAMES_TOKEN_JSON
- kids: YOUTUBE_KIDS_TOKEN_JSON
- alchemy: YOUTUBE_ALCHEMY_TOKEN_JSON

Confirme apenas os nomes, sem expor valores:

    gh secret list -e youtube-games-private-upload -R HelioConde/AutoEditorVideo
    gh secret list -e youtube-kids-private-upload -R HelioConde/AutoEditorVideo
    gh secret list -e youtube-alchemy-private-upload -R HelioConde/AutoEditorVideo

Os dois canais Otaku e seus Secrets ficam intactos.

## Etapa 4 — confirmar OAuth dentro do GitHub Actions SEM upload

Abra Actions > New Channels - Verify YouTube OAuth (Games Kids Alchemy)
READ ONLY > Run workflow, branch main. Execute três vezes: games,
kids, alchemy. Alternativamente:

    gh workflow run youtube-new-channels-oauth.yml -R HelioConde/AutoEditorVideo --ref main -f channel=games
    gh workflow run youtube-new-channels-oauth.yml -R HelioConde/AutoEditorVideo --ref main -f channel=kids
    gh workflow run youtube-new-channels-oauth.yml -R HelioConde/AutoEditorVideo --ref main -f channel=alchemy

O workflow valida o Environment antes dos Secrets, renova o token se
necessário e consulta apenas channels.list(mine=true), comparando o ID
EXATO com o registro. Não executa videos.insert, thumbnails.set,
produção de MP4, imagens IA, agendamentos nem alterações no canal.

Saída esperada: VERIFIED_[CANAL] e ZERO_VIDEOS_UPLOADED.

## Etapa seguinte — cloud production por canal (não liberada ainda)

Gamer: exigir gameplay gravado/permitido e reservar o episódio no
GitHub antes do script. Render original Remotion, QA e capa gerada,
depois upload privado e sem IDs internos nas descrições.

Kids Fofinhos: imagens pessoais de referência ficam privadas,
nunca em repo/artifact público; direitos das músicas ainda precisam
ser confirmados; marcação Made for Kids obrigatória para conteúdo
dirigido a crianças. Nenhum CTA de comentários/inscrições infantil.

Alchemy Lab: roteiros e demonstrações IA reais e verificáveis,
originalidade e declaração apropriada de conteúdo sintético.
O canal ainda aparece como Alchemy Flames até renomeação no YouTube.

O cadastro ou OAuth não concede autorização automática para publicar.
Antes de cada produção: reservar (canal, episódio), verificar material
fonte/direitos, QA, miniatura original com SHA e privacidade privada.

## Arquivos

- scripts/youtube_new_channels_oauth.py — conectividade e teste read-only
- scripts/youtube_new_channels_env_guard.py — regra main-only
- conectar-novos-canais.ps1 — consentimento local e Secrets protegidos
- .github/workflows/youtube-new-channels-oauth.yml — execução por canal
- tests/test_youtube_new_channels_oauth.py — testes offline

Nenhum Environment, token ou OAuth foi criado automaticamente por esta
mudança. Você controla cada autorização e cada possível futuro upload.
