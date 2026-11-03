# Reparar descricoes e capas dos 5 Shorts ja publicados

Este procedimento corrige **os uploads existentes**, sem publicar videos novos,
sem substituir os MP4s e sem alterar privacidade ou titulos.

## Causa do texto corrompido

A versao anterior de `publicar-5-shorts.ps1` montava descricoes com palavras
acentuadas diretamente no fonte do PowerShell, lido sem UTF-8 BOM pelo
Windows PowerShell 5.1. O resultado foi `AnÃ¡lise`, `IlustraÃ§Ãµes`
e semelhantes. A geracao agora ocorre em Python 3, sempre em UTF-8,
usando `scripts/metadata_shorts.py`.

## Comandos no Windows

```powershell
cd "C:\Users\helio\Documents\arquivo-otaku-github"
git pull --ff-only origin main

# Etapa 1: preflight local: sem rede / sem alterar nada no YouTube
.\corrigir-5-shorts.ps1

# Etapa 2: atualizar descricoes e reenviar as capas 9:16 por API
.\corrigir-5-shorts.ps1 -Aplicar
```

A segunda etapa solicita uma **nova autorizacao OAuth**, porque editar
metadados requer `youtube.force-ssl` e o publicador antigo usava
apenas `youtube.upload`. O token do reparo fica em
`.secrets/youtube-repair-token.json`, separado do token de publicacao,
sem enviar credenciais ao GitHub.

## Funcionamento e garantias

- Antes de se conectar, confere os cinco arquivos MP4 e seus respectivos
  `estado-upload-<SHA12>.json` e `<ID>-master-capa.jpg`.
- Recusa registros sem correspondencia de hash ou dois IDs do YouTube iguais.
- Confere se os videos pertencem ao canal Google autenticado.
- Mantem o titulo, categoria, tags e idioma que ja estavam no YouTube.
- Atualiza apenas a descricao para o roteiro PT-BR em UTF-8.
- Tenta aplicar a imagem original `master-capa.jpg` **sem redesenhar**.
- Grava resultados em `assets/gerados/publicacao-youtube/reparo-5-shorts.json`.
- Nao realiza `videos.insert` e nao muda `privacyStatus`.

## Se o YouTube recusar uma miniatura de Short

A API `thumbnails.set` pode recusar uploads por permissao da conta,
configuracao do canal ou suporte do produto. O script informa HTTP 400,
403, 429 etc. e continua para corrigir a descricao. Uma resposta de
sucesso da API nao garante que a miniatura ja esteja visivel no feed.

O Help Center atual do YouTube informa que contas verificadas podem
adicionar capas personalizadas dos Shorts pelo **YouTube Studio no
computador**, inclusive depois do upload:

1. Entre em https://studio.youtube.com/ e abra Conteudo > Shorts.
2. Clique no Short, entre em Detalhes e na secao Miniatura escolha
   **Enviar arquivo**.
3. Escolha `assets/gerados/shorts-animados/<ID>/<ID>-master-capa.jpg`
   e salve. Aguarde a propagacao.

Documentacao oficial:
- https://support.google.com/youtube/answer/72431
- https://developers.google.com/youtube/data/reference/rest/v3/thumbnails/set
- https://developers.google.com/youtube/data/reference/rest/v3/videos/update

Nao rode `publicar-5-shorts.ps1` novamente para tentar corrigir os
videos ja publicados. Esse script e para **novos uploads**; o de reparo
atualiza os IDs ja registrados.
