# Política de comandos PowerShell na raiz

A raiz deve conter somente **entradas principais e essenciais** para operação recorrente: produção, canais, publicação, configuração inicial e diagnósticos necessários. Scripts de correção pontual, testes experimentais e comandos de um vídeo específico não devem permanecer na raiz.

## Remoções propostas nesta branch (10/11/2026)

- `segundo-short-death-note.ps1`: launcher de um episódio específico, não é entrada geral.
- `testar-voz-studio.ps1`: teste pontual de motor de voz, não é entrada geral.
- `testar-short-br-real.ps1`: teste de homologação de um Short específico, não é entrada geral.

Os códigos ainda podem ser recuperados no histórico do Git. A remoção não apaga os scripts Python invocados nem os conteúdos do episódio.

## Manter até confirmar dependências

- `gerar-shorts-en.ps1`: **manter**; `canal-ingles.ps1` chama esse arquivo e `lote2-otaku-3br-3en.ps1` também exige sua existência. Apagar diretamente quebraria o canal EN.
- `preparar-publicados-en.ps1`, `publicar-shorts-en.ps1`: manter pelo mesmo motivo.
- `gerar-shorts-master.ps1`, `criar-publicar-short.ps1`, `publicar-youtube.ps1`: entradas de produção/publicação.
- `animar-emanuelly.ps1`, `gerar-historia-kids.ps1`, `gerar-poses-emanuelly.ps1`: produção Kids.
- `autorizar-exclusao-otaku-br.ps1`: comando destrutivo de escopo específico; manter até conferir se existe autorização ou execução pendente, então remover em mudança separada.
- `corrigir-5-shorts.ps1`, `lote2-otaku-3br-3en.ps1`: candidatos à retirada, mas exigem busca de referências e revisão de agendamentos.

## Antes de mesclar

Executar busca de referências de cada arquivo excluído em `.github/workflows`, `scripts`, `tests`, documentação e automações externas; se houver consumidor ativo, restaurar ou adaptar. Executar testes. **Ainda não realizado.**

A meta é centralizar tarefas recorrentes em entradas estáveis e evitar dezenas de atalhos históricos.
