# Auditoria de organização — AutoEditorVideo

## Inventário inicial

Árvore `main` observada no commit `587a9dee4f56d785effc80baf679f16e56e23bff`: **797 entradas** (arquivos e diretórios), `truncated=false`.

| Área | Entradas na árvore | Ação proposta |
| --- | ---: | --- |
| `.github/` | 102 | Preservar; revisar gatilhos e caminhos antes de alterações |
| `scripts/` | 199 | Catalogar produção, uploads, QA e análise; não mover sem testes |
| `tests/` | 146 | Preservar; identificar testes redundantes após executar suíte |
| `conteudos/` | 103 | Manter roteiros, reservas e lotes; não remover histórico de produção |
| `docs/` | 70 | Consolidar índice e marcar documentos legados, sem deletar de imediato |
| `dados/` | 63 | Preservar snapshots históricos; análise do YouTube terá central separada |
| `config/` e `configs/` | 20 | Mapear referências antes de unificar |
| `motion-remotion/` | 26 | Preservar renderer e testes |

## Riscos confirmados

- Duas faixas `Wondertrail _Main Theme_.mp3` e `Wondertrail _Main Theme_2.mp3` na raiz são referenciadas pelo README como usadas no Kids. **Não excluir nem mover sem migração de caminhos**. Direitos de uso devem ser verificados antes de publicar.
- `dados/metricas-youtube.json` existe, embora contenha atualmente `{"videos":[]}`. **Não excluir** até confirmar ausência de consumidores.
- Scripts PowerShell na raiz podem ser invocados por documentação, workflows e automações locais; movimentação direta pode quebrar execuções.
- `.gitignore` já ignora caches, vídeos e mídia gerada. Arquivos previamente rastreados não deixam de ser rastreados por isso.
- Repositório público: evitar salvar exports privados do Studio e credenciais.

## Critério de exclusão

Não excluir pelo nome (`old`, `teste`, `v0.6`, etc.). Para cada candidato: (1) confirmar se está rastreado; (2) buscar referências no código e workflows; (3) verificar duplicidade funcional; (4) executar testes; (5) registrar motivo; (6) excluir em PR separado, reversível.

## Entrega desta fase

Nova central `analises/youtube/`, cadastro de cinco canais e diagnóstico de referência. Nenhum arquivo de produção foi movido ou apagado. Próxima etapa: auditoria de referências e testes para uma limpeza segura.
