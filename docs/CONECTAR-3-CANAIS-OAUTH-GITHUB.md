# Conectar Gamer, Kids e Alchemy Lab ao Environment único do GitHub

Atualização 05/11/2026 — decisão do criador: CENTRALIZAR os cinco canais
no Environment existente youtube-private-upload. Nenhum token real é
transferido automaticamente por este PR e nenhum vídeo é publicado.

## Configuração final

Um único Environment: https://github.com/HelioConde/AutoEditorVideo/settings/environments
Selecione youtube-private-upload. Ele já existia com a proteção para main
e três Secrets utilizados pelos dois canais Otaku.

Secrets esperados:

| Secret no Environment único | Canal |
|---|---|
| YOUTUBE_CLIENT_JSON | OAuth Client Google existente, NÃO sobrescrever |
| YOUTUBE_BR_TOKEN_JSON | Otaku Multicena, preservar |
| YOUTUBE_EN_TOKEN_JSON | Otaku Reframe, preservar |
| YOUTUBE_GAMES_TOKEN_JSON | Gamer (Hélio Conde / Conde Games) |
| YOUTUBE_KIDS_TOKEN_JSON | Emanuelly Kids — série Fofinhos |
| YOUTUBE_ALCHEMY_TOKEN_JSON | Alchemy Flames / Alchemy Lab |

Todos os tokens de canal são independentes. Compartilhar o Environment
simplifica a administração, mas reduz o isolamento dos Secrets entre jobs
que utilizem esse Environment. Somente workflows estritamente controlados
na branch main devem acessá-lo. Cada ação que use um token deve receber
SOMENTE o Secret específico no passo e sempre verificar o Channel ID
com channels.list(mine=true) antes de qualquer escrita na conta.
Nenhum dos novos canais possui uploader automaticamente habilitado.

## 1 — Confirmar proteção da branch main

No Environment youtube-private-upload, configure Deployment branches and
tags > Selected branches and tags > somente a branch main.
Não crie outros Environments. O script local e a action bloqueiam o uso
dos Secrets quando não conseguem verificar que main é a única branch.

## 2 — Garantir que os tokens locais já existem (sem renová-los)

No PC, pasta C:\Users\helio\Documents\arquivo-otaku-github:

    Test-Path .secrets\youtube-games-cloud-token.json
    Test-Path .secrets\youtube-kids-cloud-token.json
    Test-Path .secrets\youtube-alchemy-cloud-token.json

Quando for necessário obter ou renovar o token de UM canal, execute,
no projeto com Python e os scripts atualizados:

    .\conectar-novos-canais.ps1 -Canal games -Acao Conectar
    .\conectar-novos-canais.ps1 -Canal kids -Acao Conectar
    .\conectar-novos-canais.ps1 -Canal alchemy -Acao Conectar

O login é local e usa o navegador Google. É preciso selecionar
exatamente o canal registrado e conceder youtube.upload e
youtube.readonly, com refresh token. Sem Channel ID confirmado,
nenhum token é salvo. Se token já existir, não renovar sem necessidade.

## 3 — Enviar APENAS os três novos tokens ao GitHub

O usuário optou por armazenar os três novos tokens no mesmo Environment.
Os comandos abaixo exigem confirmação explícita e validam a regra main-only
antes de escrever cada Secret. Eles NÃO sobrescrevem YOUTUBE_CLIENT_JSON,
YOUTUBE_BR_TOKEN_JSON ou YOUTUBE_EN_TOKEN_JSON.

    .\conectar-novos-canais.ps1 -Canal games -Acao EnviarSecret -ConfirmarArmazenamentoGitHub
    .\conectar-novos-canais.ps1 -Canal kids -Acao EnviarSecret -ConfirmarArmazenamentoGitHub
    .\conectar-novos-canais.ps1 -Canal alchemy -Acao EnviarSecret -ConfirmarArmazenamentoGitHub

O PowerShell confirma que YOUTUBE_CLIENT_JSON JÁ existe no Environment.
Se ele estiver ausente ou incompatível com a conta autorizada, NÃO
substitua o Secret sem antes conferir o impacto nos dois canais Otaku.

Verifique a existência dos seis nomes sem revelar os valores:

    gh secret list -e youtube-private-upload -R HelioConde/AutoEditorVideo

Os três Secrets antigos devem continuar existindo e com os mesmos
valores. Os três novos devem aparecer com suas chaves individuais.
Nunca poste tokens ou arquivos OAuth na conversa ou no Git.

## 4 — Conferir identidade pelo GitHub Actions SEM publicar vídeos

Workflow:
https://github.com/HelioConde/AutoEditorVideo/actions/workflows/youtube-new-channels-oauth.yml

    gh workflow run youtube-new-channels-oauth.yml -R HelioConde/AutoEditorVideo --ref main -f channel=games
    gh workflow run youtube-new-channels-oauth.yml -R HelioConde/AutoEditorVideo --ref main -f channel=kids
    gh workflow run youtube-new-channels-oauth.yml -R HelioConde/AutoEditorVideo --ref main -f channel=alchemy

Cada execução valida a proteção do mesmo Environment em um job sem
Secrets. Depois escolhe apenas o token do canal especificado,
renova-o se necessário e compara o Channel ID real com o registro.
A API utilizada é somente channels.list(mine=true). Nenhum vídeo
é gerado, atualizado, enviado, agendado ou publicado neste fluxo.
A verificação de acesso não implica autorização de publicação.

## 5 — Atualizar os scripts no Windows com branch Fofinhos modificada

Se a pasta local continua em audit/fofinhos-otaku-ciclo-1 e possui
arquivos Fofinhos modificados, não execute git switch main, reset --hard,
clean -fd ou git pull --ff-only origin main na branch divergente.
Depois da integração deste PR:

    git fetch origin main
    git restore --source=origin/main --worktree -- conectar-novos-canais.ps1 scripts/youtube_channel_registry.py scripts/youtube_new_channels_env_guard.py scripts/youtube_new_channels_oauth.py config/youtube-channel-registry.json

O restore atualiza somente os scripts escolhidos e não altera os
trabalhos locais do Fofinhos. Revise git status antes de fazer commit.

## Segurança editorial que continua obrigatória

- Gamer: gameplay real e permitido; reservar o episódio no GitHub.
- Kids Fofinhos: conteúdo Made for Kids, referências privadas e
  comprovação de direitos de música; nenhum pedido de comentários
  direcionado a crianças.
- Alchemy Lab: tutoriais com demonstrações reais, originalidade e
  declaração adequada de conteúdo sintético realista.
- Todos: publicar inicialmente como privado com confirmação, capa
  ORIGINAL gerada pelo AutoEditorVideo e hash; nada de marcadores internos
  AUTOEDITORVIDEO nas descrições; nenhuma regeneração ou reupload para
  corrigir somente miniatura ou metadados.
