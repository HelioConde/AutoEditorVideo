# Acompanhamento de métricas — AutoEditorVideo

## Estado em 08/11/2026

Histórico manual iniciado com três capturas fornecidas pelo proprietário.
O snapshot bruto está em [dados/metricas-redes/2026-11-08-capturas-manuais.json](../dados/metricas-redes/2026-11-08-capturas-manuais.json).

| Origem da tela | Itens distintos visíveis | Visualizações somadas somente nesses itens | Curtidas visíveis |
| --- | ---: | ---: | ---: |
| Grade de Reels do Instagram | 12 | 1.541 | não mostradas |
| Painel de conteúdo da Meta (plataforma não confirmada) | 12 | 658 | 34 |

**Não somar os totais das duas linhas:** não há comprovação de que representam
contas, métricas ou publicações equivalentes. Os números são contagens que
apareceram na captura, **não total de views da conta**, nem views no dia.

### Destaques que aparecem no primeiro registro

- **Instagram:** "MUDAR O PASSADO" (318), "CORRIDA MORTAL" (187) e "SEM MAGIA?!" (173).
- **Painel Meta:** vídeo sobre Maomao (418 views, 24 curtidas) e vídeo sobre um caderno capaz de matar (237 views, 9 curtidas).
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
- Segunda e terceira imagens: tabela `Conteúdo` da Meta, com privacidade `Todos`, views, curtidas e comentários. O aplicativo/plataforma específica não é comprovado pela captura.
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
