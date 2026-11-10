# Organização por canal — AutoEditorVideo

Este diretório centraliza **documentação editorial e índices de conteúdo de cada canal**.

| Pasta | Canal | Chave técnica |
| --- | --- | --- |
| `otaku-br/` | Otaku Multicena | `br` |
| `otaku-en/` | Otaku Reframe | `en` |
| `gamer/` | Gamer | `games` |
| `manu-kids/` | Emanuelly Kids / Manu Kids | `kids` |
| `alchemy-lab/` | Alchemy Lab | `alchemy` |

Cada pasta contém `README.md` e `conteudos/indice.json`. Os arquivos de execução originais continuam em `conteudos/` e `config/` por compatibilidade com scripts, GitHub Actions, reservas e uploads. **Os índices são referências, não novos manifestos executáveis.**

A identidade OAuth e as regras de upload permanecem centralizadas em `config/youtube-channel-registry.json` e `config/youtube-upload-profiles.json`. Nunca copiar tokens para pastas dos canais.

A central de análise fica separada em `analises/youtube/` e pode segmentar relatórios pela chave técnica. A criação destas pastas não aciona geração, publicação ou alteração de privacidade.

## Próxima migração

Para mover os manifestos e scripts de fato: mapear todas as referências, introduzir compatibilidade de caminhos, atualizar workflows, executar testes e só então retirar os arquivos legados. Não apagar histórico de uploads e reservas.
