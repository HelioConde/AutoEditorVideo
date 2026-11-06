# AutoEditorVideo — Qualidade editorial V2 (Otaku Multicena)

**Status:** desenvolvimento e auditoria offline. **Geração e publicação suspensas por solicitação do criador.**

## Segurança da pausa

- Controle vivo: `conteudos/otaku-br-50-serial-launch-20261106.json`.
- Ações bloqueadas: geração serial, geração paralela do lote pausado e publicação pública.
- `scripts/otaku_br_50_maintenance_gate.py` lê a versão **atual** de `main` via API autenticada do GitHub antes de iniciar produção ou publicação; uma Action iniciada antes da pausa não pode ignorar o novo estado.
- Quatro confirmações independentes são exigidas para liberar o fluxo: `pause_requested=false`, `authorized_public=true`, `maintenance_complete=true` e `resume_authorized_after_maintenance=true`. O último campo deve depender de novo pedido explícito do criador.
- A pausa não exclui vídeos, thumbnails, cache, artefatos, registros nem comprovantes existentes. Se o upload já tiver iniciado antes da pausa, conferir o comprovante e o YouTube antes de agir; não reenviar cegamente.

## O que os dados realmente demonstram

Dados fornecidos pelo criador, consolidados em
`conteudos/otaku-multicena-insights-editor-v2.json`:

| Referência | Retenção informada | Tempo médio | Sinal |
| --- | ---: | ---: | --- |
| Light caçou Kira | 69,45% | 28s | Mistério e revelação |
| Light virou o mal | 58,43% | 17s | Dilema moral |
| Regra dos 40 segundos | 46,56% | 23s | Consequência de uma regra |
| Maomao | 41,54% | 17s | Inteligência, inscrição |
| Blue Box | 32,34% | 12s | Conversão em inscritos |
| Steel Ball Run | 37,05% | 14s | Alcance maior |

Não há evidência de que mudar só as tags reproduza esses números. Segundo o YouTube, título, miniatura, descrição, satisfação e retenção importam muito mais que tags. Compare cada vídeo na mesma janela de **48h** após a publicação.

## Problemas técnicos encontrados no editor atual

1. O renderizador BR em `scripts/otaku_br_50_render.py` divide cinco imagens em intervalos iguais (`cuts`) sem considerar a frase exata de cada revelação. O momento narrativo pode ficar fora de sincronia com a ação visual.
2. O compositor recebe `renderMode="master_static"` e um primeiro plano RGBA transparente de 1024x1536. Assim, a geração com cinco PNGs estáticos produz apenas movimento da câmera e luz ambiente — **não** animação articulada dos personagens.
3. O perfil aplica uma tela de gancho nos primeiros 2,2s, mas não audita automaticamente a correspondência entre pergunta inicial e recompensa final.
4. A geração de cenas pode receber HTTP 400; os prompts precisam ser mais claros, adequados e autorais, com alternativas revisadas editorialmente, sem repetir às cegas pedidos recusados.
5. Nem todas as sugestões externas de tags são úteis. Termos de futebol, livros, finanças, concorrentes ou temas aleatórios não devem ser copiados para um Short sobre Death Note.

## Melhorias implementadas nesta fase

- `scripts/otaku_multicena_editorial_audit.py` roda inteiramente offline.
- Ele examina 50 roteiros/episódios e sinaliza ganchos longos, títulos extensos, roteiros com tamanho atípico, cenas incompletas e tags que não correspondem ao tema.
- `review_candidates(row, candidates)` deduplica e filtra sugestões, usa termos da franquia e **somente personagens realmente abordados** no roteiro. Aplica limite conservador de 12 tags / 260 caracteres, e isola termos irrelevantes.
- O script **não** altera a lista original de tags, recibos, vídeos, channel tokens ou metadados de uploads existentes. Ele propõe tags para revisão humana em um relatório.
- Os seis nomes de concorrentes são guardados apenas para comparação editorial futura, nunca como tags automáticas.
- A Action `otaku-editorial-quality-offline.yml` produz relatório de QA sem acessar proxy de imagens ou YouTube.

## Diretrizes para a próxima versão de renderização (a implementar)

**Experimento A: Mistério e revelação (35–45s, somente se TTS real permitir).**
Gancho em 0–3s; contexto objetivo; uma reviravolta factual; entrega da resposta antes da conclusão. Usar `Light caçou Kira` apenas como **estrutura**, nunca como roteiro copiado.

**Experimento B: Escolhas emocionais (30–45s).**
Descrever um dilema específico e seu custo; explorar hipótese de maior conversão de inscritos, inspirada nos resultados de Maomao e Blue Box.

**Experimento C: Curiosidade surpreendente (25–40s).**
Começar pela anomalia, explicar sua causa e dar uma resposta útil. Conferir em 48h o sinal de VPH do Zenitsu; um único pico não é padrão definitivo.

Para aumentar a qualidade visual: usar tomadas originais adicionais onde houver mudança real de ação; máscaras RGBA aprovadas ou sequências de poses para movimentos independentes; evitar simular movimento de personagem apenas por `scale` ou `translate` na imagem toda. Requer análise de custo, sincronização e QA humano — a auditoria offline **não** implementa rigging.

## Uso seguro, sem uploads

```powershell
python scripts/otaku_multicena_editorial_audit.py --output reports/otaku-editorial-v2.json
python -m pytest -q tests/test_otaku_multicena_editorial_audit.py tests/test_otaku_br_50_maintenance.py
```

O resultado deve permanecer um relatório de **revisão**, sem autorizar geração/publicação. Critérios de conclusão da fase: testes verdes, roteiro com promessa e recompensa claras, plano visual com ações verificáveis, legendas corretas, narração sincronizada e revisão do vídeo final pelo criador.

## Benchmark dos concorrentes

Nomes informados pelo criador, ainda sem verificação de métricas: Shin Animes 心; Animakai KAI; D+ANIMES; Mavua Animes; Anime Voz BR; Sabia Geek. A pesquisa futura deve comparar **tipo de gancho, ritmo, clareza de áudio, originalidade e narrativa** por amostra de vídeos. Não copiar imagens, falas ou títulos; não adicionar nomes de concorrentes como tags.

## Liberação da manutenção

Somente com novo consentimento explícito do criador e com testes/revisão aprovados. **Não retomar a fila dos 5 pendentes automaticamente.**


## Auditoria adicional fornecida pelo criador: 7.753 visualizações

Snapshot adicionado a `conteudos/otaku-multicena-insights-editor-v2.json`:

- 31 inscritos; 69 vídeos (todos Shorts); 7.753 views acumuladas
- Retenção média de 55,09% nos últimos 28 dias; 16 inscritos ganhos e 2 perdidos (saldo +14)
- Maior vídeo: `Light caçou Kira SEM SABER que era ele mesmo`, agora com 1.193 views
- Top 5: Light (1.193), Steel Ball Run (1.142), Zenitsu (651), Blue Box (645), Light vs L (610)
- **Correções de leitura:** 2 dos 5 líderes são de Death Note, não 3. 7.753 / 69 = 112,36 views por vídeo; a média informada de 130 views/Short provavelmente utiliza filtro ou janela diferente. Não misturar métricas.
- A hipótese de "cannibalização" ao publicar 10–15 Shorts/dia **não está demonstrada**. Usar teste com controle de janela de 48h, sem prometer efeito do algoritmo.

## Nova fase: editor antes de YouTube

O planejamento offline e sem qualquer upload está em
`scripts/otaku_multicena_strategy_plan.py`, com testes em
`tests/test_otaku_multicena_strategy_plan.py`.

- Avaliação de títulos por especificidade, pergunta/contradição e tamanho. Alertas são **heurísticas de revisão**, não nota preditiva de visualizações.
- **15 novas ideias para teste:** 5 de mistério/revelação, 5 de escolhas emocionais, 5 de curiosidades/poderes. O roteiro final deve ser factual e original.
- Duas cadências **somente propostas**: 2 Shorts/dia versus 3 Shorts/dia. Usar métricas nas primeiras 48h de cada Short e observar também permanência/visualização intencional.
- Estrutura de títulos "personagem + contradição" é uma opção forte a testar, não requisito universal. Steel Ball Run já performou sem essa construção.
- Não fixar 2/3 de Death Note: dois líderes do top 5 são desse anime e a amostra não sustenta a predominância como regra. Testar distribuição de franquias.
- Long-form 8–12 minutos: apenas hipótese de piloto **depois da fase de Shorts e de revisão editorial**. Não juntar Shorts automaticamente, não reutilizar mídia sem análise de direitos.

## Ritmo visual da geração futura

O renderizador futuro já possui um planejador de cortes por limites reais da narração:
`scripts/otaku_multicena_scene_pacing.py`. O renderizador BR usa esta função em vez de 5 cortes em partes iguais. Isso **não** afirma rigging: cenas ainda são PNGs estáticos com câmera/luz. Animação articulada, novas poses e expressão facial dependem de outra implementação, direitos de uso e QA de vídeo.

A Action `otaku-editorial-quality-offline.yml` executa testes e entrega relatórios das 50 pautas e das hipóteses de novos experimentos. Não usa API de YouTube nem provedores de imagem e não libera a pausa.
