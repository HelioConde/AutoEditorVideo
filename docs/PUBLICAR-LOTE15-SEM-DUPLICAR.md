# Publicar os 9 Shorts existentes sem duplicar arquivos

**Estado confirmado pela API autenticada do YouTube em 08/11/2026.**
Auditoria de somente leitura: [GitHub Actions 42496802090](https://github.com/HelioConde/AutoEditorVideo/actions/runs/42496802090).

| Canal | Episódio | ID do YouTube | Privacidade observada | Processamento observado |
| --- | --- | --- | --- | --- |
| Conde Games | Terraria | HW6fvYkYKlc | private | processing |
| Conde Games | Stardew Valley | mHW5MiWY71A | private | succeeded |
| Conde Games | Celeste | 8yrTR6qQVg4 | private | processing |
| Emanuelly Kids | Abelhinha | qJXNIUjkVrI | private | succeeded |
| Emanuelly Kids | Tartaruguinha | bHpcB2z6nUc | private | succeeded |
| Emanuelly Kids | Estrelinhas | 42Woqr9-ONw | private | succeeded |
| Alchemy Lab | Gatilhos | Nn8sOSw-_V8 | private | succeeded |
| Alchemy Lab | Agentes | Wu7RBUWDOb8 | private | succeeded |
| Alchemy Lab | Checar fontes | HHoIpKGTb-0 | private | succeeded |
| Alchemy Lab | Vídeo duplicado (novo piloto) | i-lzZrX_15w | **public** | succeeded |

O piloto Alchemy Lab foi **publicado com sucesso**, embora o workflow original tenha
registrado uma falha de verificação antes da estabilização dos metadados.
O código da verificação foi corrigido e **nenhum novo upload deve ser iniciado**
para o ID `i-lzZrX_15w`.

## Por que o lote anterior permanece privado?

Os 5 tokens de canais guardados no GitHub tinham apenas escopos
`youtube.upload` e `youtube.readonly`. Isso autoriza inserir um **novo**
vídeo diretamente como público, mas não autoriza `videos.update` para
alterar a privacidade de vídeos **existentes**. A API requer permissão
adicional, como `https://www.googleapis.com/auth/youtube.force-ssl`.

Um token já emitido **não pode receber o escopo automaticamente**
pelo GitHub. O dono do canal precisa consentir no Google.

## Autorizar cada um dos três canais no computador

No PowerShell, dentro da cópia atualizada do repositório:

```powershell
cd C:\Users\helio\Documents\arquivo-otaku-github
git pull
.\autorizar-publicacao-youtube.ps1 -Canal games -Acao Conectar
.\autorizar-publicacao-youtube.ps1 -Canal games -Acao EnviarSecret -ConfirmarArmazenamentoGitHub

.\autorizar-publicacao-youtube.ps1 -Canal kids -Acao Conectar
.\autorizar-publicacao-youtube.ps1 -Canal kids -Acao EnviarSecret -ConfirmarArmazenamentoGitHub

.\autorizar-publicacao-youtube.ps1 -Canal alchemy -Acao Conectar
.\autorizar-publicacao-youtube.ps1 -Canal alchemy -Acao EnviarSecret -ConfirmarArmazenamentoGitHub
```

Cada `-Acao Conectar` abre consentimento na conta Google do **canal
selecionado**; confira cuidadosamente o canal indicado. O script valida
`channels.list(mine=true)`, client OAuth, refresh token e escopos antes
de guardar novo arquivo local `.secrets/`. `EnviarSecret` envia
somente o token selecionado, usando `gh secret set` no Environment
`youtube-private-upload` **restrito a main**. Nunca cole tokens no chat.

Para revogar um consentimento, acesse sua Conta Google > Segurança >
Apps e serviços de terceiros.

## Publicar os mesmos IDs, sem reupload

**Somente depois** que os 3 canais tiverem autorizado o escopo
adicional e substituído seus Secrets:

```powershell
gh workflow run batch15-public-existing-after-oauth-20261108.yml -R HelioConde/AutoEditorVideo --ref main -f confirmar=PUBLICAR-9-SEM-DUPLICAR
```

[Workflow de publicação somente de IDs existentes](https://github.com/HelioConde/AutoEditorVideo/actions/workflows/batch15-public-existing-after-oauth-20261108.yml)

Este workflow **não** gera imagens, MP4s, miniaturas novas ou chamadas
`videos.insert`. Ele usa os recibos originais da execução 42481839933,
verifica owner/channel ID, título, descrição, classificação Kids e
processamento; aplica `videos.update(part=status)` apenas em vídeos
existentes privados e confirma `public` por leitura da API. Se um
vídeo continuar processando, ele fica pendente sem alteração, enquanto
os demais podem prosseguir. O fluxo não altera Otaku Multicena ou
Otaku Reframe, pois esses seis MP4s não foram finalizados no lote.

## Alternativa sem renovar OAuth

Abra [YouTube Studio](https://studio.youtube.com/) com a conta de cada
canal. Em **Conteúdo**, localize cada ID acima, altere
**Visibilidade > Público**, salve e confira o resultado. Nos vídeos
infantis, mantenha a classificação **conteúdo para crianças**. Não
reenvie os arquivos: eles já existem nos canais.

Atualize o registro [dados/metricas-redes/2026-11-08-lote15-publicacao-status.json](../dados/metricas-redes/2026-11-08-lote15-publicacao-status.json)
somente após uma nova verificação autenticada confirmar a visibilidade.
