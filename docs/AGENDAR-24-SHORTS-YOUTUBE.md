# Agendamento nativo YouTube — 24 Shorts Arquivo Otaku

## O que foi preparado

**24 roteiros inéditos**, com produção de imagens e narracao local, seguindo
8 vezes o ciclo:

1. 1 episodio da historia de Death Note (episodios 2 a 9).
2. 1 curiosidade independente sobre regras e detalhes da obra.
3. 1 "Voce lembra?" com nostalgia e chamada para comentario.

O episodio 1, ja publicado, ficou fora. O lote possui 8 recaps, 8
curiosidades e 8 nostálgicos. Cada roteiro começa pelo gancho e termina
com **"Inscreva-se..."**; imagens devem ser geradas por IA, sem
capturas/trechos originais de anime. O MP4 final deve passar pelo
verificador de **até 60,000 segundos** antes do envio; falha bloqueia
a publicação, mesmo que o roteiro tenha o tamanho planejado.

## A diferenca: o proprio YouTube agenda

O sistema passa no upload \`status.privacyStatus = "private"\` e
\`status.publishAt = <data/hora UTC futura>\`, usando a
**YouTube Data API** oficial. O YouTube mantem o video privado ate o
horario programado. Depois do upload e confirmacao, o computador
**nao precisa ficar ligado para o horario de liberacao**.
O computador precisa estar ligado durante geracao/render e uploads.

Documentacao:
https://developers.google.com/youtube/data/reference/rest/v3/videos
https://support.google.com/youtube/answer/1270709

## Comandos no CMD / PowerShell (Windows)

Abra o terminal dentro da pasta do projeto:

\`\`\`cmd
cd /d C:\Users\helio\Documents\arquivo-otaku-github
git pull --ff-only origin main
programar-24-shorts.cmd planejar 2026-11-05
programar-24-shorts.cmd agendar 2026-11-05
\`\`\`

O \`planejar\` **nunca produz, envia ou consome imagens**. So
mostra a tabela dos 24 horarios no fuso de Brasilia.
O \`agendar\` **autoriza** a geracao (custos/cotas), a renderizacao,
os uploads privados e a programacao no YouTube.

Se nao informar data no CMD, o agendador sugere o dia dois
dias apos a data em que o comando e executado, sempre com
primeiro horario as **09:00, America/Sao_Paulo (UTC-03 em nov/2026)**.
Data explicita e preferivel quando for interromper e retomar a fila.

O exemplo de **05/11/2026** distribui os 24 horarios a cada hora:
05/11 das 09:00 as 23:00, 06/11 das 00:00 as 08:00.
Isso é um experimento de alta frequencia — nao se sabe se aumenta alcance.
Para espacamento maior, use o PowerShell:

\`\`\`powershell
.\programar-24-shorts.ps1 -DataInicio 2026-11-05 -HoraInicio '09:00' -IntervaloMinutos 240 -Agendar
\`\`\`

(240 minutos = 4h.) Para espacamento entre dias, forneca
\`-IntervaloMinutos 1440\` (24h).

Para fazer apenas **3 uploads por execucao**, por exemplo para revisar custos
e resultados ou lidar com cotas de API:

\`\`\`powershell
.\programar-24-shorts.ps1 -DataInicio 2026-11-05 -Limite 3 -Agendar
\`\`\`

Use a **mesma data, intervalo, perfil e arquivo de plano** nas repeticoes.
O estado local fica em
\`assets/gerados/publicacao-youtube/lote-24-agendamento.json\`.
Ele fixa o planejamento antes do primeiro upload. Cada upload confirmado
salva um arquivo
\`assets/gerados/publicacao-youtube/estado-upload-<sha>.json\`
com o video_id, a privacidade solicitada e a hora agendada.

O script nao permite agendar um video com horario vencido ou
menos de 15 minutos no futuro: esse bloqueio evita a publicacao
imediata se a renderizacao passar do horario. Se a producao atrasar,
verifique o Studio e reformule os slots restantes com cuidado,
sem alterar silenciosamente videos ja agendados.

## Importante sobre cotas, seguranca e realismo

- Cada curta pode precisar de muitas chamadas de IA para planos diferentes.
  O comando de producao usa por padrao limite de **45 chamadas por video**
  (24 x 45 = **ate 1080** chamadas estimadas antes de caches, falhas e
  limites do provedor). **O gasto real nao e conhecido antecipadamente**.
  Use \`-MaxChamadas\` para controlar o limite por Short e \`-Limite\`
  para testar apenas poucos uploads na primeira execucao.
- O YouTube pode aplicar limites por canal, autenticacao, cota e politica;
  agendar 24 videos nao garante que todos os uploads serao aceitos.
- Nao basta cadastrar o roteiro. O MP4 precisa ter voz, imagens,
  legenda, capa e passar por duracao e QA real no computador.
- O agendamento e feito no **mesmo canal das credenciais OAuth locais**:
  \`.secrets/youtube-oauth-client.json\` e
  \`.secrets/youtube-token.json\`. Confirme o canal antes de autorizar.
- Se o EP02 ou outro video ja estiver publico, nao republicar. O
  sistema rejeita conflitos de agendamento nos registros existentes.
- Se houver falha com status de upload incerto, confira o YouTube Studio
  antes de reexecutar para nao duplicar.
- Miniaturas de Shorts podem exigir selecao no aplicativo YouTube; a
  API pode recusar JPG mesmo quando o upload do MP4 e bem-sucedido.
- Nao publique material de anime nao licenciado retirado da TV;
  todos os roteiros, imagens e narrações deste lote sao originais,
  sem prometer ausencia de reivindicacoes de direitos.


## Erro "Proxy nao encontrado" ao criar a Curiosidade 1

Se o EP02 foi agendado, mas o segundo Short falhou por faltar o Codex Proxy,
**nao exclua nem reenvie o primeiro**. O comprovante local preserva o ID do
episodio e o horario de 05/11/2026 09:00 (Brasilia).

A correção atual reconhece tanto
`chatgpt-codex-proxy/.env` quanto
`../arquivo-otaku-kit/chatgpt-codex-proxy/.env` (instalacao antiga), sem
copiar segredos para o GitHub e sem trocar conta automaticamente.

No **PowerShell** em `C:\Users\helio\Documents\arquivo-otaku-github`:

```powershell
git pull --ff-only origin main
.\testar-codex-proxy.ps1 -Acao iniciar
.\testar-codex-proxy.ps1 -Acao status
```

Se `iniciar` disser que o proxy ainda nao foi instalado, abra o Docker
Desktop e rode `.\testar-codex-proxy.ps1 -Acao instalar` somente se
necessario. Esse comando baixa/inicia um servico de terceiros; revise o
projeto antes de autorizar uma conta. Se o status indicar nenhuma conta,
o login requer sua autorizacao explicita e pode ser feito com
`.\testar-codex-proxy.ps1 -Acao login`. Nao compartilhe tokens no chat.
Se não há conta elegível por limite de uso, aguarde a disponibilidade
normal em vez de contornar a cota.

Quando o status confirmar uma conta elegivel, retome sem duplicar uploads:

```cmd
programar-24-shorts.cmd agendar 2026-11-05
```

O pipeline agora faz um teste read-only antes de tentar imagens pendentes;
se o proxy estiver indisponivel, para **uma vez**, sem repetir tentativas
identicas em todas as cenas. Se todas as imagens ja estiverem em cache,
nao e necessario ter o proxy ligado.

Se o YouTube retornar **HTTP 429 no envio da capa**, isso nao invalida o
agendamento do MP4. Nao reenvie o video: a miniatura pode precisar ser
ajustada no aplicativo YouTube quando o canal permitir.

## Arquivos implementados

- \`programar-24-shorts.cmd\`: atalho para planejar ou agendar.
- \`programar-24-shorts.ps1\`: opcoes de data, hora, intervalo e limite.
- \`scripts/agendar_24_shorts.py\`: calcula horario, valida roteiro
  e coordena agendamento nativo com retomada sem duplicata.
- \`conteudos/lote-24-shorts.json\`: slots/editoria.
- \`conteudos/death-note-recaps-60s.json\`: episodios 2 a 9.
- \`conteudos/death-note-formatos-60s.json\`: curiosidades/nostalgia.
- \`scripts/publicar_arquivo_otaku.py\`: campo \`status.publishAt\`
  e registro da confirmacao de agendamento.
- \`tests/test_agendar_24_shorts.py\`: regressao offline.
