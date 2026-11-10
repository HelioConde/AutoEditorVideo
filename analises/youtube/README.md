# Central de análise do YouTube — AutoEditorVideo

Este diretório é exclusivo para **análises, relatórios e comparações de desempenho dos cinco canais**. Não contém tokens OAuth, credenciais, imagens privadas, vídeos renderizados ou ações de upload.

## Estrutura

- `README.md`: documentação e regras de interpretação.
- `config/canais.json`: registro de canais e metas de medição.
- `relatorios/`: relatórios versionados, escritos manualmente ou produzidos por ferramentas de análise (sem dados secretos).
- `scripts/`: scripts de análise **somente leitura**; não publicam, editam nem apagam vídeos.

## Canais

Otaku Multicena (BR), Otaku Reframe (EN), Gamer (Hélio Conde), Emanuelly Kids e Alchemy Lab.

## Fontes já existentes (preservadas)

- `dados/metricas-redes/`: capturas manuais e snapshots históricos, inclusive Instagram e Kwai.
- `dados/metricas-youtube.json`: arquivo legado; **não remover** até identificar leitores e migrar com testes.
- `docs/ACOMPANHAMENTO-METRICAS-REDES.md`: procedimento multirrede.

## Regras de análise

1. Distinguir dados públicos de métricas internas do YouTube Studio. Não inferir `shown_in_feed`, retenção ou `viewed_vs_swiped_away` de contagens públicas.
2. Registrar data, janela, fonte, canal e ID real do vídeo. Valores desconhecidos = `null`, nunca zero inventado.
3. Comparar janelas de 24h/72h/7d e separar Shorts antigos de novos; não dividir views de canal por uploads e chamar isso de média dos vídeos novos.
4. Para o Kids, avaliar separadamente Fofinhos e os testes de nichos secundários.
5. Não publicar informações pessoais, credenciais, dados de menores ou exportações privadas.
6. Mudanças na estrutura de produção exigem busca de referências, testes e validação de workflows antes de mover ou excluir arquivos.

## Plano de migração

**Fase 1 (esta branch):** central de análise, inventário e relatório inicial, sem quebrar caminhos.
**Fase 2:** mapear todas as dependências dos scripts e workflows e criar aliases/compatibilidade.
**Fase 3:** migrar caminhos gradualmente e rodar testes.
**Fase 4:** excluir apenas arquivos comprovadamente redundantes, com histórico recuperável no Git e revisão do diff.

A existência desta pasta **não** ativa agendamentos, automações, coleta de APIs ou uploads.
