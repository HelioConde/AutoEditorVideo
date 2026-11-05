# Otaku lote 2 — controle de producao e retomada (2026-11-05)

Este registro documenta os IDs ja reservados no lote 2 para evitar
escolher os mesmos videos como "novos" em outro lote.

**Origem:** saida de log local fornecida pelo operador em 2026-11-05.
Este arquivo NAO e uma consulta ao YouTube Studio nem substitui os
recibos de upload e hashes mantidos em `assets/gerados/`.

| Canal | ID | Situacao reportada pelo log |
|---|---|---|
| BR / Otaku Multicena | 5005-bleach-thousand-year-blood-war | Pendente: cache de imagem incompleto (diagnostico anterior: 6 chamadas) |
| BR / Otaku Multicena | 5009-overgeared | Enviado como privado (recibo local relatado) |
| BR / Otaku Multicena | 5010-aoashi | Enviado como privado (recibo local relatado) |
| EN / Otaku Reframe | 5004-jojo-steel-ball-run | Ja enviado (log local; conferir visibilidade no Studio) |
| EN / Otaku Reframe | 202-death-note-40-segundos | Ja enviado (log local; conferir visibilidade no Studio) |
| EN / Otaku Reframe | 401-jujutsu-kaisen-ep01 | Pendente: cenas PT incompletas; master.png de 01 ausente, 09/background pendente |

## Retomada e limites

O script `lote2-otaku-3br-3en.ps1` envia **somente como privado**.
Nunca usar a acao `ProduzirPublicar` da grade 50, porque ela publica
imediatamente em modo publico.

A opcao `-SomenteJujutsu` seleciona apenas o episodio EN 401, sem tocar
nos outros cinco. A opcao `-MaxChamadasJujutsu N` autoriza NO MAXIMO N
chamadas de imagem por execucao no cache PT com modelo escolhido; com
N=0, nao ha geracao paga. `scripts/retomar_cache_por_cena.py` avanca por
cena sob esse teto e interrompe antes de render EN se ainda faltar arte.

Quando a resposta do provedor e recebida, os raws do cache permanecem
salvos. Se uma chamada falhar, conferir scene-failure.json antes de
repetir. Nao misturar imagens com hash, prompt, storyboard ou modelo
diferentes para "resolver" faltas.

Antes de tentar qualquer upload, consultar os recibos locais e o Studio
caso um upload tenha resultado ambiguo. Evitar reenviar videos ja aceitos.
Agendamento de privacidade pode ser feito no YouTube Studio apos revisar
os videos privados sem reenviar.
