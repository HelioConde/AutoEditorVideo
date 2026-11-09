# Plano técnico — experimentos offline Otaku Multicena BR (2026-11-09)

**Estado:** planejamento, sem ativação de produção. Canal `UCXGYTuBYn-0Ziqin5ajKhOw`. Escopo somente BR. Não gerar imagens, renderizar/publicar vídeos, alterar metadados ou visibilidade, nem usar credenciais.

## Referências e invariantes
- Ler `AGENTS.md`, `config/otaku-character-identity-policy.json`, `config/otaku-growth-active-v1.json` e `docs/ACOMPANHAMENTO-METRICAS-REDES.md` antes de implementar.
- Preservar âncoras e SHA-256, referências reais de personagens nomeados, QA visual humano, direitos, IDs/reservas, privacidade, voz Edge TTS, WordBoundary real, legendas canônicas, capa original e proteção de uploads.
- Não modificar `.github/workflows/otaku-growth-autotune.yml` nem o perfil ativo nesta etapa. O workflow atual roda no main, recalcula o perfil e faz push; não usá-lo como executor dos experimentos. Uma eventual implementação deve ter comando `--offline --dry-run`, sem rede, secrets, escrita em perfil ativo ou caminhos de upload.
- Distinguir evidência de hipótese: snapshots históricos têm janelas diferentes; valores ausentes = null, não zero. Não inferir taxa de 'continuou assistindo' a partir de engagedViews/views.

## Desenho experimental
Unidade: Short futuro único; variações emparelhadas por franquia, subtema, complexidade, faixa de duração, dia e idade de publicação. O mesmo vídeo não pode ser publicado duas vezes como teste. Offline: gerar apenas propostas textuais e storyboards de referência usando ativos já licenciados/localmente disponíveis; nenhuma API de imagem/voz ou renderização obrigatória. Os testes offline verificam conformidade, **não** provam aumento de audiência.

1. **Ganchos de mistério**: A = declaração direta de conflito; B = pergunta específica verificável. Mesmo assunto, promessa factual, resolução e duração alvo; primeiros 3s e até 12 palavras sugeridas. Revisar ausência de clickbait e entrega do payoff. Registrar `hook_variant`, `topic_id`, `franchise`, `script_word_count`.
2. **Duração**: A = 25–40s; B = 60–90s, apenas como candidatos de roteiro. Medir duração real por áudio/ffprobe se houver mídia local; sem mudar limites, default ou participação máxima de testes longos do perfil ativo (atualmente 25% para estendidos). Testes de faixas diferentes exigem controle por tema e idade; não afirmar causalidade se assuntos diferirem.
3. **Movimento**: A = composição estática válida; B = articulação/malha sobre camadas independentes e âncoras existentes, quando disponíveis e autorizadas. Checagens offline de referência/identidade, hashes, deformação, bordas, flicker, oclusão, sincronia e continuidade; zoom isolado não conta como movimento de personagem. Se não houver material de referência adequado, marcar `blocked_missing_assets`, sem fabricar prova de QA.
4. **Título e SEO**: A = curiosidade específica; B = consequência concreta. Mesmo tópico e palavras-chave verificadas, sem tag técnica, spoiler enganoso ou mudança de título após publicação. Validar tamanho 12–70 caracteres sugerido, no máximo 2 palavras de ênfase em maiúsculas, tags via `scripts/youtube_public_tags.py:public_tags`; guardar `title_variant`, `keyword_basis`, `topic_id`.
5. **Conversão**: métrica `1000 * subscribersGained / engagedViews` quando `engagedViews > 0`; também registrar `subscribersLost` e `net_subscribers_per_1000_engaged_views = 1000*(gained-lost)/engagedViews`. Nulos se ausentes/denominador zero. Sem CTA genérico na narração; observar janelas idênticas e não atribuir causalidade a um único vídeo.

## Esquema proposto (arquivo experimental separado, nunca no perfil ativo)
```json
{
  "schema": "autoeditorvideo/offline-editorial-experiment/v1",
  "channel_id": "UCXGYTuBYn-0Ziqin5ajKhOw",
  "experiment_id": "string",
  "video_id": null,
  "topic_id": "string",
  "franchise": "string",
  "variant": "A",
  "hook_variant": null,
  "duration_band_seconds": [25, 40],
  "motion_variant": null,
  "title_variant": null,
  "publish_time": null,
  "measurement_age_hours": null,
  "measurement_window": null,
  "views": null,
  "engaged_views": null,
  "subscribers_gained": null,
  "subscribers_lost": null,
  "viewed_vs_swiped_percent": null,
  "average_view_percentage": null,
  "qa": {"canon_verified": false, "identity_reviewed": false, "captions_real": false, "rights_reviewed": false},
  "status": "offline_proposal"
}
```
Não incluir nomes pessoais, credenciais, imagens privadas, URLs assinadas ou identificadores de OAuth.

## Análise e critérios de promoção
- Pré-registro das hipóteses e variantes; comparação exploratória com pelo menos 5 vídeos **concluídos por variante**, idealmente mais antes de alterar regras globais.
- Coletas nas idades 1h, 6h, 24h, 72h e 168h quando disponíveis; tolerância de idade declarada, mesma definição de janela e mesma plataforma. Relatar cobertura de dados e tamanho da amostra.
- Primário: taxa de continuou assistindo **somente quando fornecida diretamente pelo Studio**. Secundários: engaged views, duração média, porcentagem média assistida, views por idade, conversão em inscritos. Distinguir percentuais de visualização de decisão de assistir.
- Reportar mediana, dispersão e diferença absoluta por variante; sem significância/ganho causal com amostra insuficiente. Bloquear promoção automática se dados ausentes, identidade visual não aprovada ou direitos/QA pendentes.
- Preferir análise por pares de tema e idade; controle de publicação/efeitos de calendário. Evitar comparação de contadores acumulados com métricas de período.

## Implementação futura proposta (não executada)
1. Criar `scripts/otaku_offline_experiments.py` com CLI `plan`, `validate`, `report`; entradas locais e saída somente em diretório temporário/artefatos ignorados pelo Git.
2. Criar fixtures sintéticas sem dados pessoais em `tests/fixtures/otaku_offline_experiments/` e testes `tests/test_otaku_offline_experiments.py`.
3. Casos obrigatórios: campos ausentes; denominador zero; idade/janela divergentes; franquia desbalanceada; menos de 5 por variante; vídeo duplicado; tags técnicas; ausência de âncoras; zoom como falsa animação; proibição de chamadas de rede e publicação.
4. Rodar `python -m pytest -q tests/test_otaku_offline_experiments.py` em ambiente isolado; depois, testes existentes de growth e QA. Qualquer falha bloqueia promoção.
5. Revisar resultados e proposta em PR separado, sem alterar `main` automaticamente. Só promover regra após aprovação e evidência comparável.

## Critério de conclusão desta etapa
Plano versionado; nenhuma mudança no pipeline, workflow, perfil ativo, imagens, vídeos, segredos ou publicações. Resultados de performance ainda são hipóteses.
