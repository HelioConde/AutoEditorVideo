# Arquivo Otaku - Integracao oficial com TikTok (Windows)

O publicador utiliza TikTok Content Posting API para os cinco MP4s renderizados,
sem recomprimir, recriar imagens ou copiar cookies. Nao utiliza automacao de
navegador para clicar em publicar.

## Pre-requisitos e limites

1. Crie aplicativo em https://developers.tiktok.com/ e ative Login Kit.
2. Em Login Kit > Desktop, cadastre o redirect URI exato:
   http://127.0.0.1:8731/callback/
3. Adicione Content Posting API ao app. Para envio a caixa de entrada, solicite
   video.upload. Para publicacao direta, solicite video.publish, mais a
   aprovacao/auditoria TikTok correspondente.
4. Crie .secrets/tiktok-app.json SOMENTE no seu computador com o JSON abaixo:

    {
      "client_key": "CHAVE_DO_SEU_APP",
      "client_secret": "SEGREDO_DO_SEU_APP",
      "redirect_uri": "http://127.0.0.1:8731/callback/"
    }

Nunca envie chaves ou tokens ao GitHub ou ao chat. A pasta .secrets/ esta no
.gitignore. Nao salve fotos de codigos de autenticacao.

App ainda nao auditado nao consegue publicacao direta publica pela API;
posts diretos sao restritos a privado. O modo rascunho envia os MP4s mas exige
concluir a publicacao no app TikTok. Nao existe atalho legitimamente suportado
para essas exigencias.

## Comandos PowerShell

    cd "C:\Users\helio\Documents\arquivo-otaku-github"
    git pull --ff-only origin main

    # Diagnosticar sem enviar
    .\publicar-tiktok.ps1 -Acao diagnostico
    .\publicar-tiktok.ps1 -Acao preparar -Limite 5

    # Conectar sua conta pelo navegador oficial (somente primeira vez)
    .\publicar-tiktok.ps1 -Acao conectar -Modo rascunho

    # Enviar um unico Short como teste
    .\publicar-tiktok.ps1 -Acao enviar -Modo rascunho -Limite 1 -ConfirmarEnvio

    # Enviar um outro Short especifico
    .\publicar-tiktok.ps1 -Acao enviar -Modo rascunho -Id 004-death-note-segundo-kira -ConfirmarEnvio

    # Consultar upload anterior
    .\publicar-tiktok.ps1 -Acao status -Modo rascunho

Apos revisar todos os arquivos, titulos, direitos e autorizacoes, para enviar
os cinco MP4s com uma unica execucao:

    .\publicar-tiktok.ps1 -Acao enviar -Modo rascunho -Limite 5 -ConfirmarEnvio

Isso envia automaticamente arquivos para a conta autorizada, mas NAO publica:
abra a caixa de entrada TikTok e conclua a edicao e publicacao de cada um.

## Publicacao direta (somente se aprovada pelo TikTok)

    .\publicar-tiktok.ps1 -Acao conectar -Modo direto
    .\publicar-tiktok.ps1 -Acao preparar -Id 003-death-note-xadrez
    .\publicar-tiktok.ps1 -Acao enviar -Modo direto -Id 003-death-note-xadrez -Privacidade SELF_ONLY -ConfirmarEnvio
    .\publicar-tiktok.ps1 -Acao status -Modo direto

PUBLIC_TO_EVERYONE exige o app aprovado/auditado e a opcao devolvida em
creator_info/query para a conta. O comando nao supera tais limitacoes.

O codigo faz a verificacao de duracao, formato, audio, privacidade do criador,
permite autorizar o lote explicitamente e marca is_aigc como verdadeiro quando
publica diretamente videos com arte IA.

## Arquivos e estado

- MP4: assets/gerados/shorts-animados/<ID>/<ID>-master-multicenas-personagens-v3-equilibrado.mp4
- Credenciais do app: .secrets/tiktok-app.json
- OAuth/refresh token: .secrets/tiktok-token.json
- Historico: assets/gerados/publicacao-tiktok/envios.json

Duplicatas sao bloqueadas pelo SHA-256 do video, conta TikTok e modo.
Com publish_id ja registrado, o sistema nao cria um segundo envio.
Em caso de transferencia interrompida, rode -Acao status antes de tentar
de novo; nunca tente burlar limites da plataforma, inclusive HTTP 429.

Legenda TikTok e montada a partir do titulo do episodio com hashtags e UTF-8,
sem os problemas de acentuacao que ocorreram no YouTube. A capa JPG do YouTube
nao e enviada isoladamente: a API oficial de videos permite selecionar apenas
um frame como capa por timestamp.

## Referencias oficiais

- https://developers.tiktok.com/docs/en/login-kit-desktop
- https://developers.tiktok.com/docs/en/content-posting-api-get-started
- https://developers.tiktok.com/docs/en/content-posting-api-get-started-upload-content
- https://developers.tiktok.com/docs/en/content-posting-api-media-transfer-guide
- https://developers.tiktok.com/docs/en/content-posting-api-reference-get-video-status
