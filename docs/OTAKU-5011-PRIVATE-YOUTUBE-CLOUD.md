# Enviar Gachiakuta 5011 BR e EN como PRIVADO pelo GitHub

**O YouTube ainda não recebeu estes vídeos por este workflow.** O upload só
acontece se os MP4s originais do GitHub tiverem passado no QA e se o criador
configurar e autorizar separadamente o OAuth das duas contas YouTube.

## Não confundir os três tipos de credenciais

- `PROXY_ACCOUNTS_JSON`: OAuth do Codex Proxy. Serve **somente para imagens**.
- `YOUTUBE_BR_TOKEN_JSON`: conta dona de **Otaku Multicena**,
  `UCXGYTuBYn-0Ziqin5ajKhOw`.
- `YOUTUBE_EN_TOKEN_JSON`: conta dona de **Otaku Reframe**,
  `UCBoNbQjaMYdpJqPLRZAFkvQ`.

A identidade é consultada via `channels.list(mine=true)` com acesso
`youtube.readonly`, **antes** de qualquer `videos.insert`. Também é
necessário `youtube.upload`. Se o token antigo não tiver ambos os escopos,
autorize uma sessão nova para o canal correto. A API poderá forçar uploads
privados para projetos OAuth não verificados.

## 1. Configuração única no GitHub, com consentimento explícito

1. Abra `https://github.com/HelioConde/AutoEditorVideo/settings/environments`.
2. Crie o Environment **`youtube-private-upload`**, distinto do Environment
   `image-generation`.
3. Em **Deployment branches and tags**, selecione **Selected branches and tags**
   e permita **exclusivamente** a branch `main`. Se a política não permitir
   somente a `main`, o workflow bloqueia o upload **antes** de ler os tokens.
4. Depois de revisar e aceitar o risco de armazenar refresh tokens OAuth no
   GitHub Environment, importe os valores pelo **seu PowerShell local** com
   `gh` autenticado. Não compartilhe JSON, OAuth, tokens ou captura das chaves
   nesta conversa.

```powershell
cd C:\Users\helio\Documents\arquivo-otaku-github
Get-Content -LiteralPath '.secrets\youtube-oauth-client.json' -Raw | gh secret set YOUTUBE_CLIENT_JSON -e youtube-private-upload -R HelioConde/AutoEditorVideo
Get-Content -LiteralPath '.secrets\youtube-token.json' -Raw | gh secret set YOUTUBE_BR_TOKEN_JSON -e youtube-private-upload -R HelioConde/AutoEditorVideo
Get-Content -LiteralPath '.secrets\youtube-en-token.json' -Raw | gh secret set YOUTUBE_EN_TOKEN_JSON -e youtube-private-upload -R HelioConde/AutoEditorVideo
```

Os três comandos acima **fazem a transferência dos tokens sensíveis** para
o GitHub. Só execute se concordar explicitamente com essa finalidade e
verificar se os tokens pertencem aos canais certos. Cada token tem ciclo de
validade/refresh próprio; renovações no runner não persistem automaticamente
no Environment.

## 2. Exigir renderização de ambos

Workflow original: `otaku-cloud-dual-5011.yml`.

A execução escolhida para esta produção é
`https://github.com/HelioConde/AutoEditorVideo/actions/runs/42013193406`.

O publicador pinou o SHA do commit e o ID desta execução. Ele recusa outro run
ou um MP4 diferente. O artifact deve ter nome
`otaku-5011-gachiakuta-BR-EN-autoeditorvideo`. O artifact do piloto tem
**retencao de 1 dia**; faça a configuração antes da expiração. Uma expiração
não autoriza repetição automática de 21 imagens.

## 3. Disparo explícito — ambos PRIVADOS, sem data de agendamento

```powershell
gh workflow run otaku-cloud-private-5011.yml -R HelioConde/AutoEditorVideo --ref main -f render_run_id=42013193406 -f channel=both -f confirm_private_upload=true
```

Isso apenas **solicita o upload no GitHub Actions**; nenhum MP4 é publicado
pelo computador. Nunca executar antes do QA dos dois vídeos e verificação dos
três Secrets e dos canais.

O workflow `otaku-cloud-private-5011.yml` faz a validação do Environment
em job sem Secrets; faz upload em **jobs independentes por canal**; verifica
hashes e títulos; checa o histórico do canal para evitar duplicidade; envia
sempre com `privacyStatus='private'`, sem `publishAt`, sem agendar ou tornar
público. Confirme os dois IDs de vídeo no próprio Actions/YouTube Studio.

Se um upload retornar resposta ambígua, o workflow bloqueia **sem retry**.
É preciso inspecionar o Studio antes de qualquer nova tentativa; não
assumir que HTTP inválido significa vídeo não enviado.

## 4. Próximos vídeos — regra de reserva

`conteudos/otaku-production-reservations.json` é obrigatório.
Toda solicitação de script, PowerShell ou geração recebe reserva
no GitHub **antes** de geração. `5009-overgeared` e `5010-aoashi`
já estão em produção; `5011-gachiakuta` está reservado para os dois canais.
Nenhum desses assuntos pode ser escolhido automaticamente de novo.

**Importante:** publicar privado continua sendo uma ação real na conta do
YouTube. A configuração por si só não executa upload; o usuário controla o
`workflow_dispatch` com aprovação explícita.
