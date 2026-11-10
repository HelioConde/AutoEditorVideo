# Limpeza de duplicatas — 10/11/2026

## Exclusões nesta branch (ainda não incorporadas à main)

Os quatro arquivos abaixo tinham **o mesmo blob SHA** que um manifesto canônico preservado. Removemos somente as cópias da branch de revisão; os objetos e históricos continuam recuperáveis via Git.

| Cópia removida | Canônico preservado | SHA do conteúdo |
| --- | --- | --- |
| `conteudos/kids-elefantinho-existing-id-reconcile-retry-20261108.json` | `conteudos/kids-elefantinho-existing-id-reconcile-20261108.json` | `1f6bd5564880e750303353589731d3578cb7d3cb` |
| `conteudos/gamer-v2-http400-fix-retry-launch-20261108.json` | `conteudos/gamer-v2-http400-fix-launch-20261108.json` | `10b8f3b9f5ff4892614c25dee969db3926d1f3ab` |
| `conteudos/otaku-br-characters-v2-final-launch-20261108.json` | `conteudos/otaku-br-characters-v2-launch-20261108.json` | `3f21c763be91ef597cbe342ebab19ce00092350b` |
| `conteudos/otaku-br-characters-v2-retry-launch-20261108.json` | `conteudos/otaku-br-characters-v2-launch-20261108.json` | `3f21c763be91ef597cbe342ebab19ce00092350b` |

**Atenção:** equivalência de conteúdo não garante equivalência de caminho. Antes de mesclar o PR, verificar scripts, workflows, comandos externos e execuções agendadas que possam referenciar os caminhos removidos. Se houver referência ativa, atualizar o consumidor ou restaurar o arquivo. Nenhuma execução de testes foi feita nesta etapa.

## Não excluídos

- Manifests de lote, reservas, recibos de upload e IDs de vídeo: histórico de idempotência.
- Músicas e recursos Kids: dependências de renderização e licenciamento a verificar.
- `dados/metricas-youtube.json`: arquivo vazio, mas leitores ainda não auditados.
- `tests/`, `config/`, `configs/`, `.github/`: preservar até mapear dependências.
