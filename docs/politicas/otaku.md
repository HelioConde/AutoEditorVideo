# REGRA PRIORITÁRIA E PERMANENTE — PERSONAGENS RECONHECÍVEIS NOS CANAIS OTAKU (08/11/2026)

**Autorização expressa do criador.** Esta política NÃO pode ser revertida, enfraquecida,
ignorada nem substituída por personagens genéricos sem nova instrução explícita
do criador. Prioridade sobre antigos prompts genéricos de vídeos de anime.
Contrato: `config/otaku-character-identity-policy.json`.

- Otaku Multicena BR e Otaku Reframe EN: se o roteiro nomear um personagem
  de anime, retratá-lo com aparência reconhecível do anime, preservando cabelo,
  rosto, olhos, roupas, acessórios, paleta, proporções e silhueta.
  A ação da cena deve corresponder à história narrada.
- Proibido usar generic athlete, generic student, fictional silhouette,
  fresh fictional character, avoid brand-specific costume, not copied exactly
  ou outras instruções que descaracterizem personagens nomeados de anime.
  Isso NÃO altera as regras dos canais Gamer, Kids e IA.
- Cada vídeo anime deve criar imagens âncora para os personagens e usar
  essas imagens como REFERÊNCIAS REAIS em images/edits em todas as cenas,
  evitando imagens independentes apenas a partir de texto.
- QA: registrar SHA-256 de cada âncora, referência de cada cena, fidelidade
  da história e avaliação real da continuidade visual. Hash e resolução
  NÃO são garantia de semelhança facial: não alegar revisão artística
  automática que não ocorreu. Bloquear publicação sem revisão visual.
- Versionar os vídeos corrigidos. Publicar publicamente somente após QA,
  confirmação exata do canal, status público, processamento e capa.
  Excluir SOMENTE IDs antigos expressamente autorizados, APÓS confirmação
  da substituição; sem exclusão ampla e sem reupload cego em erros de rede.
- Testes de regressão devem bloquear retorno de prompts genéricos;
  mudança da regra requer autorização explícita posterior do criador.

---

## GRADE DE 50 ANIMES — PUBLICAR IMEDIATAMENTE COMO PUBLICO

- Catalogos: `conteudos/otaku-multicena-grade-50-a.json` e
  `conteudos/otaku-multicena-grade-50-b.json`: 50 Shorts originais,
  do anime atual ao nostalgico, IDs 5001..5050.
- `grade-50-shorts.ps1`: Validar/Preparar/Produzir/**ProduzirPublicar**.
  **Nao agendar, nao usar publishAt** nesta fila: o usuario pediu
  publicar como `public` imediatamente quando terminar cada MP4.
- `ProduzirPublicar` executa producao, QA, depois publica aquele episodio
  como `public` usando `-MaxChamadas 0` apenas no passo do upload.
  Avanca ao proximo somente apos confirmar video_id e status PUBLIC.
  O processo e sequencial, nao faz upload concorrente.
- `ConfirmarPublicacao` e indispensavel para qualquer envio remoto.
  `ConfirmarCotaImagem` e exigido quando `MaxChamadasPorVideo>0`.
  O limite e POR VIDEO, nao custo total garantido. Nao iniciar lote
  grande sem explicitar o pior caso (50x30 = 1500 chamadas).
- Antes de enviar: MP4 <=60s, capa vertical valida, QA vinculada ao
  arquivo `mp4`, som Edge TTS e legendas sincronizadas.
  `camera_only_scenes` e informativo por padrao: o pipeline gera
  principalmente camadas 2.5D ou masters inteiras, e rejeitar
  automaticamente 100% camera-only bloqueava toda a fila.
  Usar `-ExigirMovimentoPersonagem` se o usuario quiser um modo
  estrito e aceitar o bloqueio; caso contrario publico com zoom suave.
  Nao chamar zoom de animacao facial ou gesto corporal.
- **REGRA INVIOLAVEL — MINIATURAS GERADAS (05/11/2026):** para todo
  upload BR e EN, usar SEMPRE o JPG original que foi gerado pelo
  AutoEditorVideo, personalizado para aquele episodio e idioma, nunca frame
  capturado, screenshot, thumbnail sugerida pelo YouTube, capa de outro
  idioma ou imagem refeita durante upload. O pacote do render DEVE trazer
  `cover_sha256`, `cover`, `render_origin` e `channel`; o uploader
  valida todos ANTES de `videos.insert`. A excecao de assinatura vale
  somente para o artifact antigo do 5011 Gachiakuta que precede a regra.
  Se a miniatura falhar apos o upload, manter video privado e registrar
  pendencia, sem recriar video ou substituir a capa. Configuracoes de upload
  do BR/EN sao mantidas em `config/youtube-upload-profiles.json` e
  documentadas em `docs/PERFIS-YOUTUBE-BR-EN-MINIATURAS-ORIGINAIS.md`.
- **REGRA OBRIGATORIA CLOUD BR/EN (05/11/2026):** a capa JPG 9:16 do
  AutoEditorVideo NAO pode apenas existir no artifact. Apos confirmar o upload,
  o workflow deve consultar `videos.list(part=processingDetails,status)`,
  verificar `processingStatus=succeeded` e `privacyStatus=private`,
  executar `thumbnails.set` com a capa aprovada do canal e validar a resposta.
  Se a capa falhar por 403/429/permissao, marcar thumbnail pendente com codigo
  seguro e **NUNCA reenviar MP4**. Guardar recibo do video_id ANTES da
  tentativa de thumbnail. Usar credenciais OAuth diferentes BR e EN.
  Upload de thumbnail e acao propria, sem alterar privacidade/agendamento,
  sem produzir nova imagem/voz/video e sem usar outro canal.
- Reparos em Shorts ja enviados sao **somente thumbnails.set**, condicionados
  a verificar ID correto, OAuth do canal e SHA/asset da capa. Nunca recriar ou
  reenviar video so para corrigir capa; respeitar elegibilidade de thumbnail
  para Shorts no YouTube e registrar falhas sem mascarar sucesso.
- **Thumbnail:** enviar JPG vertical do editor por `thumbnails.set`
  apenas quando `processingDetails.processingStatus=succeeded`.
  Pode falhar por elegibilidade da conta; registrar pendencia, NUNCA
  reenviar MP4 para corrigir capa.
- Em falha ambigua de API, guardar estado local e exigir inspecao no
  Studio; nao duplicar uploads. Mantem `grade-50-estado.json` fora
  do Git. Publicacao real depende do Windows com OAuth/caches locais.
- Erros `images/edits` do Codex Proxy (como 5005 Bleach cenas 01/06/07):
  **nao inventar arte** para cobrir falhas. `master_scenes.py` persiste
  `scene-failure.json` por cena, sem corpo bruto de resposta/token.
  HTTP 400/401/403/404/415/422/429 nao deve consumir retries imediatos;
  408/5xx podem usar as tentativas limitadas. Sempre preservar raw/cache.
- `-ContinuarAposFalha` e opcional em `grade-50-shorts.ps1`: pula apenas
  producao falha, nunca video parcial nem falha de upload. Para apos tres
  falhas de producao consecutivas; a grade parcial retorna codigo 2.
  Falhas pendentes podem ser retomadas depois sem reenviar os Shorts
  que ja tem recibo de upload publico.
- Ver `docs/OTAKU-GRADE-50.md` e o guia anterior de vidIQ.

## OTAKU MULTICENA 3.0 — DIRETRIZ EDITORIAL E CRESCIMENTO

- Para pautas novas, aplicar as regras do [guia 3.0](../OTAKU-MULTICENA-3-0.md):
  audiencia brasileira de anime, especialmente nao seguidores; gancho compreensivel
  nos primeiros segundos, conflito concreto, roteiro original e conclusao satisfatoria.
- Antes de gerar imagens, revisar cinco enfoques do gancho (curiosidade,
  contradicao, decisao, misterio, consequencia) sem prometer fatos inexistentes.
  A geracao desses enfoques NAO equivale a verificacao factual automatica.
- `scripts/otaku_growth_v3.py` realiza auditoria offline; a validacao da grade
  agora imprime informacoes editoriais. O modo `-ExigirGatesEditoriais` bloqueia
  apenas defeitos objetivos e nao aprova animacao, direitos ou fidelidade ao anime.
- Reaproveitar o QA de MP4/cenas e os modos estritos ja existentes; zoom suave
  NAO e animacao articulada. Nunca relatar movimento facial/corporal sem provas.
- Aprendizado: comparar visualizacoes, feed, retencao e engajamento nas mesmas
  idades (1, 6, 24, 72 horas e 7 dias), preservando `null` para dados ausentes.
  Nao supor um teto de tres Shorts recomendados por dia.
- Publicar ou alterar videos, contas, visibilidade e horarios continua exigindo
  autorizacao explicita; nenhum comando de auditoria pode gerar imagens,
  consumir cota, alterar MP4 ou usar credenciais.
- As regras e caches preexistentes dos fluxos PT/EN continuam validos.
  O guia 3.0 e incremental: nao presumir que todas as fases estao implementadas.


## OTAKU MULTICENA 3.0 — CRESCIMENTO DE REDES COM POUCA TRACAO

- Priorizar adaptacoes para TikTok e Kwai, preservando os sinais ja observados no
  YouTube e Instagram. Nao prometer a mesma audiencia em outras plataformas.
- Nova ferramenta offline: scripts/plano_multiplataforma_v3.py; gera propostas de
  legenda/QA para YouTube, Instagram, TikTok e Kwai, sem publicacao, IA ou alteracoes
  remotas. Consulte docs/CRESCIMENTO-MULTIPLATAFORMA-3-0.md.
- TikTok: o criador relatou som removido em videos anteriores; conferir o motivo
  real e o resultado do recurso no aplicativo antes de novos envios.
  Nao presumir que uma unica palavra tenha causado a remocao. Nao tentar burlar
  moderacao mudando termos, voz ou reenviando material recusado.
- Kwai: na ausencia de autorizacao/integracao confirmada, somente propostas
  para publicacao manual. Nunca afirmar que conta, API ou monetizacao estao ativos.
- Metas devem usar intervalos comparaveis de idade do video (1, 6, 24, 72, 168h)
  e levar em conta retencao, distribuicao, compartilhamentos e seguidores.
  Ausencia de dados nao e zero; nao atribuir causalidade a amostras pequenas.
- Direitos de trilha, voz, imagens e regras atuais sao revisao obrigatoria;
  ffprobe apenas checa duracao, formato e presenca de audio.
- Nao editar videos publicados, enviar rascunhos, fazer uploads ou alterar
  privacidade/horarios sem aprovacao explicita. Caches e IDs locais preservados.

## OTAKU REFRAME EN V3 — ADAPTACAO DE SHORTS BR JA PUBLICADOS

- Escopo: somente videos publicos BR com episodio-fonte mapeado no snapshot de 2026-11-04. O levantamento tem 18 Shorts BR: 13 fontes para preparar EN, 1 episodio ja em ingles e 4 sem fonte confirmada.
- Canal BR: UCXGYTuBYn-0Ziqin5ajKhOw. Canal EN ja existente Otaku Reframe: UCBoNbQjaMYdpJqPLRZAFkvQ. Nunca misturar OAuth/tokens, IDs ou estados.
- Episodios 101 e 201 ja possuem publicacoes em ingles. Nao duplicar; itens com status source_unconfirmed ficam fora da fila.
- O preparador scripts/preparar_publicados_en_v3.py nao executa audio, proxy de imagem, video ou upload; valida a correspondencia dos roteiros BR e EN e cinco abordagens de gancho.
- Usar ingles natural, narracao e legendas EN, metadados proprios, imagem inicial compreensivel e historia com recompensa real, sem conteudo enganoso.
- Reusar imagens PT somente se preservam continuidade e nao trazem texto PT gravado na arte. QA de video inteiro deve verificar pronuncia, movimento de personagens alem de zoom, direitos e MP4 completo.
- O publicador EN exige manifestos de origem coerentes, QA assinado e destino Otaku Reframe; upload privado por padrao e apenas com confirmacao explicita. Nunca publicar automaticamente durante o preparo.
- Consultar docs/OTAKU-REFRAME-PUBLICADOS-BR-EN-V3.md. Action verde nao comprova caches ou videos renderizados no Windows.
