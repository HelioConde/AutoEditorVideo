# Laboratório de Audiência — comparação com métricas reais (v1)

## Segurança e escopo
Este componente **não consulta YouTube, vidIQ ou rede**, não usa OAuth, não
publica nem altera vídeos, imagens, roteiros ou o manifesto da produção.
A análise usa somente CSVs selecionados e fornecidos explicitamente.

A pasta dados-privados/audiencia/ é ignorada pelo Git. Não envie exportações
de Analytics, tokens ou relatórios privados em PRs, issues, commits ou
artefatos públicos. GitHub Actions testa apenas arquivos sintéticos e a
ausência segura de dados reais.

## Regra de comparação
1. Gere o relatório editorial JSON dos roteiros com audiencia_simulada.py.
2. Relacione explicitamente episode_id a video_id e channel_id com dados
   confirmados no YouTube Studio; nunca deduza IDs por títulos parecidos.
3. Exporte totais por vídeo para os **sete primeiros dias de calendário**,
   contando a data local de publicação como o primeiro dia.
4. Use o mesmo recorte e tipo de métricas para todos os vídeos.
5. Só compare após completar toda a janela de sete dias.

O piloto aceita exclusivamente o canal Otaku Multicena BR, ID
UCXGYTuBYn-0Ziqin5ajKhOw.

## Dois CSVs privados

Arquivo 1: dados-privados/audiencia/mapa.csv

    episode_id,video_id,channel_id,published_on
    5015-jujutsu-kaisen-dominio,AAAAAAAAAAA,UCXGYTuBYn-0Ziqin5ajKhOw,2026-11-01

Arquivo 2: dados-privados/audiencia/metricas.csv

    video_id,window_start,window_end,captured_on,views,engaged_views,average_view_percentage
    AAAAAAAAAAA,2026-11-01,2026-11-07,2026-11-09,200,130,68.5

**Todos os números e IDs dos exemplos são fictícios.** Datas usam
YYYY-MM-DD. A captura deve ocorrer depois do último dia da janela.

- views: visualizações totais dentro da janela.
- engaged_views: visualizações engajadas medidas na mesma janela.
- average_view_percentage: porcentagem média assistida, que pode passar de
  100% em Shorts assistidos mais de uma vez.

Não misture métricas de últimos 28 dias ou de toda a vida do vídeo com
dados da janela especificada. O programa verifica duplicidades, canal,
IDs, datas, percentuais e contagens incoerentes.

## Executar no PowerShell

Para obter o relatório editorial:

    python scripts/audiencia_simulada.py --output reports/audiencia-simulada-br-piloto.json

Para comparar os arquivos locais:

    python scripts/audiencia_metricas_reais.py --editorial-report reports/audiencia-simulada-br-piloto.json --mapping dados-privados/audiencia/mapa.csv --metrics dados-privados/audiencia/metricas.csv --output dados-privados/audiencia/comparacao.json --markdown-output dados-privados/audiencia/comparacao.md --as-of 2026-11-09

A data de referência acima é ilustrativa; substitua pela data da
captura ao executar. Sem os dois CSVs, o programa retorna apenas estado
de dados indisponíveis, sem criar valores artificiais.

## Resultados
- sem_mapeamento: nenhum ID foi confirmado para aquele roteiro.
- aguardando_metrica: episódio mapeado, mas sem dados daquele vídeo.
- janela_ainda_nao_completa: dados ainda não cobrem o período completo.
- apto_comparacao: episódio com métricas de uma janela completa.

O programa só calcula Spearman descritivo para **pelo menos oito vídeos
maduros**, com diversidade suficiente de índices e de visualizações
engajadas. Três vídeos não bastam. A associação de ranking não significa
causalidade, previsão de views nem recomendação automática de publicação.

## Testes

    python -m unittest discover -s tests -p "test_audiencia*.py" -v

Os testes são totalmente sintéticos. No workflow do PR o processo de
comparação é executado sem entrada de métricas de usuários, apenas
para garantir que não fabrica dados e não aciona publicação.

Mais adiante, uma integração autenticada ao YouTube precisará de aprovação
específica, permissões de leitura e controle cuidadoso dos relatórios.
