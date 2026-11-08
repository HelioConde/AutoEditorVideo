# Acompanhamento de métricas — AutoEditorVideo

## Estado em 08/11/2026

Histórico manual iniciado em 08/11/2026 com quatro capturas fornecidas pelo proprietário.
Os snapshots brutos estão em [Instagram e painel Meta](../dados/metricas-redes/2026-11-08-capturas-manuais.json) e [Kwai](../dados/metricas-redes/2026-11-08-kwai-captura-manual.json).

| Origem da tela | Itens distintos visíveis | Visualizações somadas somente nesses itens | Curtidas visíveis |
| --- | ---: | ---: | ---: |
| Grade de Reels do Instagram | 12 | 1.541 | não mostradas |
| Painel de conteúdo da Meta (plataforma não confirmada) | 12 | 658 | 34 |
| Grade de vídeos do Kwai (plataforma informada pelo proprietário) | 8 | aproximadamente 5.467 | não mostradas |

**Não somar os totais das plataformas/linhas:** não há comprovação de que representam
contas, métricas ou publicações equivalentes. Os números são contagens que
apareceram na captura, **não total de views da conta**, nem views no dia.

### Destaques que aparecem no primeiro registro

- **Instagram:** "MUDAR O PASSADO" (318), "CORRIDA MORTAL" (187) e "SEM MAGIA?!" (173).
- **Painel Meta:** vídeo sobre Maomao (418 views, 24 curtidas) e vídeo sobre um caderno capaz de matar (237 views, 9 curtidas).
- **Kwai:** vídeo de personagem castanho acompanhado de criatura sombria (mostra `1,1 mil`, aproximadamente 1.100 reproduções) e vídeo de personagem castanho lendo um caderno preto (944 reproduções).
- O vídeo "Kira achava que ninguém poderia encontrá-lo..." tem 2 views e 1 curtida no painel Meta.
- Vários vídeos no painel exibem **0**; esses zeros são dados observados, não inferidos.

## Como registrar novas medições

1. Gerar **um novo arquivo datado** em `dados/metricas-redes/`, sem sobrescrever o anterior.
2. Identificar `plataforma`, `superficie`, `data_observacao`, origem e se a coleta foi manual ou via API.
3. Registrar views, curtidas, comentários e demais campos como números **somente se mostrados**; valores indisponíveis devem ser `null`, jamais 0.
4. Registrar IDs/permalinks reais quando puderem ser verificados, para permitir comparar a **mesma publicação** ao longo do tempo; não usar títulos/posições na grade como identificadores confiáveis.
5. Evitar contagem dupla quando uma publicação aparece em mais de uma captura na mesma coleta.
6. Comparar métricas por plataforma, publicação, janela de observação e idade do vídeo. Não confundir totais de itens visíveis com métricas agregadas da conta.
7. Para estudos de desempenho, priorizar medições com 1h, 6h, 24h, 72h e 7 dias de publicação, quando a informação estiver disponível.

## Limites desta coleta

- Primeira imagem: grade de Reels do Instagram. Exibe contagens de visualizações, mas não curtidas, comentários, data de publicação nem IDs.
- Segunda e terceira imagens: tabela `Conteúdo` da Meta, com privacidade `Todos`, views, curtidas e comentários.
- Quarta imagem: grade Kwai, com sete contagens exatas somando 4.367, mais um contador arredondado exibido como `1,1 mil`; o total dos oito é aproximadamente 5.467, não exato. O cartão `Memórias 10` foi excluído por não exibir contador de vídeo.
- A conta Kwai não está conectada à API; nenhum ID, data de postagem, título ou interação é verificável nesta imagem. O aplicativo/plataforma específica não é comprovado pela captura.
- Os vídeos de Kira e Ryuk reaparecem na segunda e na terceira imagens: foram registrados **uma única vez**.
- Os títulos da tabela são truncados na interface; sua transcrição não deve ser tratada como o título completo.
- A captura informa dados históricos em 03, 04 e 05/11/2026; o registro foi feito em 08/11/2026.
- Nenhuma API foi consultada. Os prints originais **não** foram publicados no repositório.
- O repositório é público. Nunca versionar tokens, credenciais, dados privados de contas ou informações pessoais.

## Próximas atualizações

Quando novas capturas ou relatórios autorizados estiverem disponíveis,
acrescentar um snapshot datado e usar os IDs dos vídeos para conferir crescimento,
engajamento e resultados por tema. Uma integração de métricas da Meta só poderá
ser ativada após conectar e autorizar a conta correta; a preparação de publicação
do Instagram **não** representa conexão ativa de métricas.

As métricas do YouTube ficam em seus próprios registros; este snapshot
não modifica `dados/metricas-youtube.json` ou qualquer fluxo de publicação.


## YouTube via API — 08/11/2026

Fonte: integração vidIQ autorizada para os canais próprios, consultando relatórios
do YouTube Analytics, com janela **09/10 a 07/11/2026**. Dados brutos:
[dados/metricas-redes/2026-11-08-youtube-api-vidiq.json](../dados/metricas-redes/2026-11-08-youtube-api-vidiq.json).

| Canal conectado | Inscritos atuais | Views no período | Engaged views | Minutos assistidos | Curtidas | Inscritos ganhos/perdidos |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Otaku Multicena (BR) | 36 | 7.535 | 2.728 | 895 | 272 | +30 / -5 |
| Otaku Reframe (EN) | 4 | 517 | 228 | 57 | 11 | +2 / 0 |

- As estatísticas atuais dos canais são diferentes de estatísticas de período.
- **BR:** 7.220 das 7.535 visualizações vieram do feed de Shorts (~95,8%);
  233 vieram da pesquisa (~3,1%). Os vídeos "Light caçou Kira" (1.193)
  e "Steel Ball Run" (1.141) lideraram a janela.
- **EN:** 457 das 517 visualizações vieram do feed de Shorts (~88,4%);
  56 vieram da pesquisa (~10,8%). "Who played the better game? L or Light?"
  teve 505 visualizações da janela (~97,7%).
- Engaged views e views **não** permitem inferir taxa de conclusão,
  retenção média ou percentual de espectadores que deslizaram.
- O relatório diário retornou apenas as datas 01 a 05/11 no BR e 03 a
  05/11 no EN; os dias ausentes **não foram preenchidos com zero**.
- O agrupamento por tipo de conteúdo apresentou 7.560 views em Shorts
  para BR, divergindo do total geral de 7.535; preservar essa discrepância
  entre consultas, sem alterar silenciosamente os totais.
- O agrupamento de fontes BR soma 7.547, levemente acima das 7.535 do
  total geral. O agrupamento de fontes EN soma 517.
- Os canais Gamer, Kids e Alchemy **não estavam conectados ao vidIQ nesta
  consulta**, portanto não há relatório Analytics deles neste snapshot.
- Os créditos da integração acabaram antes de obter o agrupamento por tipo
  do EN; os dados anteriores já haviam sido recebidos com sucesso.
- Consulta somente leitura; não houve upload, alteração de metadados,
  troca de privacidade ou publicação. Nenhuma credencial foi salva no GitHub.

### Leituras iniciais para decisões editoriais

1. Comparar ganchos e retenção por vídeo em próximas medições, usando a
   mesma idade de publicação e `engagedViews` separadamente de `views`.
2. Avaliar novos ângulos de Death Note no EN, sem inferir tendência
   estatística a partir de um único vídeo vencedor.
3. No BR, testar variações narrativas sobre Death Note, Steel Ball Run,
   Blue Box e Maomao, buscando consistência além de poucos destaques.
4. Antes de incluir Gamer/Kids/Alchemy, conectar e autorizar a identidade
   correta de cada canal no provedor de análise; não reutilizar OAuth
   de um canal para outro.
