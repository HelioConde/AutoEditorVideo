## REGRA PERMANENTE — TAGS DE SEO NÃO SÃO IDENTIFICADORES TÉCNICOS (05/11/2026)

- As tags visíveis no YouTube Studio e vidIQ devem conter **somente palavras-chave
  editoriais relevantes** ao tema do vídeo. É PROIBIDO enviar em `snippet.tags`
  qualquer código `autoeditorvideo-*`, `autoeditorvideo_*`, nome de reserva,
  hash, identificador de episódio, slug técnico ou marcador de idempotência.
- A função obrigatória de saída é `scripts/youtube_public_tags.py:public_tags`.
  Aplicá-la imediatamente antes de chamar `videos.insert` ou `videos.update`,
  mesmo quando o arquivo de metadados vier aprovado ou de uma automação antiga.
  Exemplos de tags boas: `Minecraft`, `Minecraft nostalgia`, `creeper`,
  `IA generativa`; nunca permitir um código do programa com nota 0 no vidIQ.
- **Controle de duplicação** deve usar reservas e recibos privados do GitHub,
  IDs retornados pela API e verificação do canal. O rastreio não pode depender
  de publicar identificadores internos na descrição, título ou tags.
  Se um upload for ambíguo, parar e reconciliar pelo manifesto/ID antes de
  qualquer reenvio; nunca reenviar cegamente.
- Ao corrigir tags de vídeo existente, consultar os metadados atuais e
  substituir apenas a lista de tags, preservando título, descrição,
  categoria, idioma e visibilidade (sem enviar `status` no update);
  não excluir o vídeo nem alterar sua miniatura.

## REGRA ATUAL — REVISAR NO YOUTUBE STUDIO, NAO APROVAR CENA A CENA

- Preferencia explicita do criador em 04/11/2026: toda avaliacao
  **artistica/narrativa do video completo** ocorre no YouTube Studio
  depois de upload **privado**. Nao adicionar gates por ausencia de
  `visual-review.json`, `multilayer/review.json`, `requires_manual_approval`,
  `-AprovarCena`, `-AprovarMulticamadas` em rotas reais de render e capa.
- Renders continuam exigindo QA automatico objetivo: arquivos presentes,
  hashes de cache, composicao sem bloqueios, 9:16, audio, <=60s,
  proveniencia e conta correta. Cache explicitamente REPROVADO continua
  bloqueado ate ser corrigido; nao forjar `status=aprovado` ou alterar arquivos
  de revisao. Alertas artisticos nao devem virar status falso de sucesso.
- Upload para revisao EN exige confirmacao explicita, OAuth valido e
  canal `UCBoNbQjaMYdpJqPLRZAFkvQ`, privacidade `private` por padrao.
  Nao alterar videos publicos ou executar upload durante preparacao/render.
  Direitos de imagens/musicas e seguranca de conteudo Kids continuam
  requisitos, e upload privado nao libera automaticamente publicar.
- `-ExigirMovimentoPersonagem` continua modo ESTRITO opcional; se bloquear
  cenas camera-only, renderizar sem esse switch para inspecao privada em
  video completo, sem chamar zoom de animacao de personagem.
- Biblioteca nova: `assets/gerados/biblioteca-videos/{Kids,Gamer,Otaku Multicena,Otaku Reframe}`;
  usar `organizar-videos.ps1 -Acao Prever` e depois `-Acao Organizar`.
  NUNCA mover/remover originais de `assets/gerados` (os publicadores ainda
  dependem dos caminhos antigos). Sem classificar fontes incertas como prontas.
  Varios renderizadores atualizam a biblioteca APOS a primeira organizacao.
  Consultar `docs/BIBLIOTECA-VIDEOS-CANAIS-POST-UPLOAD.md`.

## REGRA PERMANENTE — IDS INTERNOS FORA DA DESCRICAO YOUTUBE (05/11/2026)

- **Nunca publicar** strings de controle como
  `AUTOEDITORVIDEO-5011-en-fdc3d3a734833529`, hashes, IDs de pipeline,
  nomes de cache ou recibos no titulo, descricao, hashtags, tags, legendas ou
  texto exibido aos espectadores, em **nenhum** canal BR/EN.
- Antigos identificadores `AUTOEDITORVIDEO-<episodio>-<br|en>-<hash>`
  podem ser **lidos** somente para localizar uploads anteriores e evitar
  duplicatas; sao proibidos como texto de novos uploads. Persistir chave de
  idempotencia no recibo interno/registro de producao e YouTube video_id.
- Aplicar `sanitize_youtube_description` no caminho cloud
  `scripts/cloud_youtube_private_5011.py` e nos publicadores locais
  `scripts/publicar_arquivo_otaku.py` / `scripts/publicar_shorts_en.py`.
  Uma chave malformada deve **bloquear** em vez de vazar na descricao.
- Para um video ja enviado, limpar SOMENTE o identificador antigo
  com revisao do texto completo. Preservar titulo, tags, publico,
  privacidade, horario/agendamento, capa e outros metadados.
  **Nunca reenviar MP4 nem repetir geracao** para corrigir descricao.
- Novas historias precisam de reserva no GitHub antes de scripts/PowerShell
  conforme `conteudos/otaku-production-reservations.json`.
