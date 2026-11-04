# Arquivo Otaku — orientações para agentes

Projeto local de produção de Shorts em PT-BR: radar editorial, roteiro revisado,
imagens anime via Codex Proxy local, edição com MoneyPrinterTurbo/FFmpeg,
miniaturas e upload OAuth para YouTube.

## KIDS — NARRACAO ACOLHEDORA V1 (TESTE ESTRELINHA AZUL)

- Somente `kids-001-estrela-azul` usa por enquanto `narration_style=kids-acolhedora-v1`.
  Manter a proposta inclusiva, simples, acolhedora e nao apressada, com
  "Obrigada por me ajudar..." no final; outros Kids aguardam avaliacao.
- 13 blocos de fala em `narration_timeline` do manifesto;
  pausas reais de 0,6–0,9s entre falas e **1,8s apos cada pergunta**
  sobre a casinha vermelha, amarela e azul. Total de 11,8s.
- Gerar TTS independente por fala (Francisca pt-BR -15%), decodificar PCM
  mono/48kHz com FFmpeg, inserir silêncios por amostra e reencodar um MP3.
  Recalcular WordBoundary, legendas, cenas, personagens e abertura;
  nunca narrar marcadores de pausa nem adiantar a resposta visual.
- Objetivo editorial 45–55s, medida real obrigatoria, teto tecnicamente
  validado de 60s. Se longo, nao remover pausas e nao acelerar a voz
  silenciosamente; revisar roteiro. Nao substituir MP3/cache antigo sem
  `-Refazer`. Fingerprint inclui texto E duracao das pausas.
- Animar estrela olhando para as casas durante o silencio, corpo/expressao
  suave, câmera fixa, sem flashes ou pedidos de comentarios/inscricoes.
- A revisao narrativa continua no MP4 completo depois de upload privado
  com autorizacao expressa; o piloto nao possui OAuth nem upload.
  Ver `docs/KIDS-NARRACAO-ACOLHEDORA-V1.md`.

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

## PADRAO VISUAL ATUAL: ZOOM CONTINUO SEM FLIQUES (2026-11-03)

- O criador rejeitou os **jump cuts virtuais** em 1,25s / 2,45s e as
  trocas de posicao a cada 2,7s; causavam desconforto e atrapalhavam
  a percepcao do movimento do personagem. **Nunca reintroduzir**.
- Abertura: zoom in / zoom out suave de ate 4% com curva continua;
  long holds: respiracao de camera de ate 2,2% sem saltos. Pan global
  quase zero; camera centrada em cada cena. Nunca alterar o ponto focal
  abruptamente em uma mesma imagem.
- Personagens com RGBA semantico seguro: movimento rigido de corpo inteiro,
  sem alongar rostos, maos, pernas ou tecidos. Preset equilibrado permite
  deslocamento mais perceptivel, mas bloqueia personagens encostados em
  objeto/manga/maos com risco de descolamento.
- **Arte plana nao pode ter membros articulados de verdade** apenas com
  transformacao global. Informar `camera_only_scenes` no QA; se o
  movimento de corpo for indispensavel, produzir camadas/frames realmente
  aprovados em vez de prometer gestos inexistentes.
- Texto/legendas: blocos de ate 3 palavras, fundo escuro, tempos reais
  da voz Edge TTS/ASR. Nao pronunciar o nome do canal no CTA.
- Evitar reenquadramento excessivo, flicker, jitter, transicoes rapidas
  e fontes cobrindo o rosto. Validar quadros e o video final no celular.
- Alteracoes no motor de render invalidam MP4 local (renderer_sha256).
  Nao reenviar videos antigos automaticamente.

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

## REGRA EDITORIAL: CTA SEM MARCA NA NARRACAO

- Em novos roteiros PT-BR, manter um CTA curto e natural, como
  `Inscreva-se para acompanhar o proximo episodio!`.
- **Nao narrar o nome "Otaku Multicena"** no CTA final. A marca continua
  no titulo, descricao, hashtags, capa e elementos visuais quando apropriado.
- Aplicar em roteiros novos ou em edicoes explicitamente solicitadas; nao
  reescrever audios de Shorts ja publicados sem pedido.
- Quando editar o campo `script`, atualizar o campo `cta` correspondente e
  invalidar voz/legendas/MP4 em cache se as palavras faladas mudarem.
- Edge TTS segue o motor padrao. Nenhum upload automatico decorrente de revisao
  textual; exigir o sinalizador de publicacao explicito.

## MOTOR DE VOZ OPCIONAL: VOICESTUDIO

- Edge TTS e a opcao **padrao** e nunca deve ser removida nem substituida silenciosamente.
- `-VozMotor voicestudio` seleciona o VoiceStudio apenas explicitamente no pipeline PT-BR.
- Primeiro teste: `testar-voz-studio.ps1`; nenhuma imagem, render ou upload.
- No VoiceStudio, legendar **somente** com tempos reais de ASR; falha de servidor,
  modelo, transcricao ou tempos bloqueia a geracao. Nao fabricar word boundaries,
  nao misturar cache de Edge e VoiceStudio e nao reutilizar MP4 com voz incorreta.
- Restrito a API local 127.0.0.1 / localhost, sem credenciais publicadas no repo.
- Licencas dos modelos de voz precisam ser verificadas antes de uso monetizado;
  pesos OmniVoice padrao podem ter restricao NC. Conservar audio em cache local.

## REGRA PERMANENTE: PRODUCAO AUTOMATICA PELO AUTOEDITORVIDEO

- Todos os Shorts EN e PT-BR continuam usando o motor deste repositorio, com
  Codex Proxy, Edge TTS/vozes do projeto, Remotion/FFmpeg e ffprobe. Nunca
  substituir o render final por video externo, slide vetorial ou vidIQ Compose.
- O usuario escolheu **nao revisar/aprovar imagens uma a uma**. Para os Shorts EN
  originais, o padrao e `QA automatico tecnico`: validar o storyboard/caches
  corretos, master/foreground/background, alfa, mascaras, hashes, composicao,
  voz EN, marcacoes de legenda, render vertical e MP4 final <=60,000s.
  Isto NAO garante avaliacao artistica humana. Cenas explicitamente reprovadas,
  QA/caches invalidos ou incompletos e erros de duracao continuam bloqueando.
- **Nao forjar registros `visual-review.json` nem fingir aprovacao humana**.
  A revisao por cena (`-Acao Revisar` / `-ModoQA manual`) e opcional.
- `gerar-otaku-reframe.ps1 -Acao Automatizar -MaxChamadas <limite>` e o fluxo
  de ponta a ponta para EN: prepara roteiro/voz, gera apenas arte faltante
  dentro do orcamento, valida, renderiza com Remotion e envia ao **canal
  ingles OAuth verificado**. A propria invocacao e a autorizacao de upload.
- **Privacidade padrao: private**, para que o criador assista ao video pronto
  no YouTube Studio. `-Visibilidade public` e opt-in explicito. Confirmacao
  de Channel ID EN, token separado do PT, registro de SHA/ID e bloqueio de
  upload duplicado sao obrigatorios. Nenhum upload parcial ou em canal errado.
- O criador faz a revisao de qualidade do VIDEO COMPLETO depois do envio ao
  YouTube; nao adicionar bloqueios com `APROVAR 01` / `APROVAR 02` como
  requisito normal para Shorts EN. Se um problema visual real for encontrado,
  corrigir/regenere o cache mantendo o restante.
- Para novos originais EN, `production.qa=automatic-technical`,
  `post_upload_review=true`, `external_rendering=false` e
  `auto_publish=false` (sem publicacao PUBLICA automatica por padrao).
- Nunca enviar tokens, `.secrets`, cache IA, imagens e videos finais ao GitHub.
  Este repositorio armazena apenas codigo, manifests, roteiros, testes e docs.
- O upload YouTube e somente no computador local Windows com OAuth da conta.
  ChatGPT/GitHub Actions nao possuem acesso ao cache local do PC.
- A previa vetorial externa do Short `201-death-note-rosto-nome` foi rejeitada;
  nao reutilizar suas artes/voz/trilha no MP4 gerado pelo AutoEditorVideo.

Regras obrigatórias:
- **LOTE DE 24 SHORTS**: 8 ciclos completos de episodio -> curiosidade ->
  voce lembra, usando conteudos/lote-24-shorts.json; EP01 publicado fica de fora.
  Todos os roteiros devem iniciar com o campo `hook` e terminar com `cta`
  explicitamente pedindo inscricao; o validador final deve recusar MP4 >60,000s.
- **AGENDAMENTO YOUTUBE**: video enviado como `private` com `status.publishAt`
  futuro em UTC e confirmacao retornada pela API; jamais publicar em horario
  passado, jamais assumir sucesso sem id/hora confirmados. Sem `-Agendar`, nao
  gerar materiais nem consumir cota; nao duplicar uploads agendados.
- **REGRA DE DISTRIBUICAO EDITORIAL**: alternar `Um episodio em 60s` -> `Curiosidade` ->
  `Voce lembra?` -> proximo episodio, e repetir o ciclo quando houver
  roteiros novos aprovados. Nao publicar episodios consecutivos na fila
  automatica. Respeitar intervalo minimo de 60 minutos entre uploads
  confirmados, sem inferir que isso seja uma regra oficial do YouTube.
  No experimento atual: 102-death-note-ep02 -> 201-death-note-rosto-nome ->
  301-death-note-voce-lembra-justica -> 103-death-note-ep03.
  Nunca reutilizar videos antigos apenas para preencher o ciclo.
- **REGRA MESTRA INEGOCIAVEL: TODO Short deve ter duracao FINAL menor ou igual a 60,000 segundos**.
  Inclui gancho, historia, suspense, CTA de inscricao, pausas, transicoes e qualquer margem de render.
  Planejar entre 55 e 59 segundos; medir o MP4 com ffprobe, nao estimar apenas pelo roteiro.
  Validar antes da renderizacao (voz + margem final), depois de renderizar e ANTES de
  qualquer upload (YouTube PT-BR/EN e TikTok). Rejeitar duracoes >60s, sem excecoes.
  Se ultrapassar, editar/reduzir o roteiro, gerar a voz novamente e renderizar.
  Nao acelerar artificialmente a voz, nao cortar o CTA nem ocultar erros de duracao.
  Guard de codigo: scripts/shorts_duration.py. Testes: tests/test_shorts_duration.py.
- Nunca enviar `.env`, `.secrets`, tokens OAuth, credenciais de terceiros, vídeos,
  imagens geradas, caches nem dados de conta ao repositório.
- Toda geração de imagens deve considerar cotas e respeitar `no available accounts`.
  Não contornar cotas, não trocar conta automaticamente para burlar limites.
- `-SomenteConfigurar`, QA, radar e testes não podem gastar cota nem publicar.
- Evitar upload duplicado; publicar apenas quando o usuário solicita. Confirmar
  o modo de privacidade e registrar o ID retornado.
- Não inventar métricas, fontes de notícias nem prometer monetização.
- Interface do GitHub Pages é informativa, não executa o backend Windows.
- Usar `python -m pytest -q tests` antes de entregar mudanças funcionais.
- Para conteúdos de anime, revisar direitos de imagem, música e fontes originais.

## OTAKU MULTICENA 3.0 — DIRETRIZ EDITORIAL E CRESCIMENTO

- Para pautas novas, aplicar as regras do [guia 3.0](docs/OTAKU-MULTICENA-3-0.md):
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

## POWERHELL DEDICADO — GAMES PT-BR / OTAKU REFRAME EN

- `canal-gamer.ps1` encaminha EXCLUSIVAMENTE `-Canal games` ao motor
  `piloto-canais-v3.ps1`. Recusar IDs Kids, forcar IDs individuais para
  `Voz` e `Renderizar`, nunca publicar ou usar OAuth.
- `canal-ingles.ps1` encaminha `PublicadosBR` ao preparador EN V3
  e ao renderizador EN; aceita `Legado` isoladamente. Voz `en-US-GuyNeural`
  e canal-alvo Otaku Reframe `UCBoNbQjaMYdpJqPLRZAFkvQ`.
- EN `Enviar` exige `-Id`, `-ConfirmarEnvio`, canal ID local identico,
  e `-ConfirmarPublico` adicional para privacidade `public`. Privacidade
  default `private`. Nunca enviar lotes acidentalmente.
- O canal Kids usa o `piloto-canais-v3.ps1 -Canal kids` existente.
- Teste `tests/test_channel_launchers.ps1` em Windows com motores fake,
  sem acessar YouTube, TTS ou imagens. Leia
  `docs/POWERSHELL-CANAIS-GAMER-INGLES.md`.
- Nenhuma mudanca nos scripts do canal anime BR sem pedido explicito.

## GAMES + KIDS — PILOTO 3x2 PT-BR

- Os dois novos canais sao totalmente PT-BR; NAO usar Otaku Reframe/ingles.
- Games (nome provisório Checkpoint Pixel): 3 Shorts com Minecraft, Roblox
  e TILLFOLK; requires first-party or licensed gameplay from local captures;
  jamais simular jogadas, vitória ou mecânicas não implementadas.
- Kids (nome provisório MiniMundo Curioso): 3 Shorts educativos originais
  sobre cores, contagem 1-5 e formas, para crianças de aproximadamente 4-7.
  Conteúdo dirigido a crianças: marcar Made for Kids true; nao pedir comentarios,
  inscricoes, compras ou engajamento; materiais suaves e apropriados à idade.
- As vozes são pt-BR-AntonioNeural para Games e pt-BR-FranciscaNeural para Kids.
- Conteudos/piloto-games-kids-3x2-v3.json é a fonte dos seis storyboards e
  metadados. O Remotion possui composicao original PilotoCanaisV3, com SVG Kids
  e videos capturados reais para Games. Nao inventar assets faltantes.
- Nomes e IDs dos canais ainda nao existem no projeto: youtube_channel_id=null.
  Nunca utilizar tokens, channel IDs ou uploads Otaku para novos canais.
- O piloto-canais-v3.ps1 so prepara/inspeciona/gera voz/renderiza localmente,
  sem autenticar/publicar. Cada render depende de TTS PT-BR e QA tecnico.
  Publicar só após criação, verificação OAuth independente e autorização explícita.
- Contar resultados por 1/6/24/72/168 horas e não presumir 3 impulsos diários.
- Docs: docs/PILOTO-GAMES-KIDS-3X2-V3.md.

## OTAKU REFRAME EN V3 — ADAPTACAO DE SHORTS BR JA PUBLICADOS

- Escopo: somente videos publicos BR com episodio-fonte mapeado no snapshot de 2026-11-04. O levantamento tem 18 Shorts BR: 13 fontes para preparar EN, 1 episodio ja em ingles e 4 sem fonte confirmada.
- Canal BR: UCXGYTuBYn-0Ziqin5ajKhOw. Canal EN ja existente Otaku Reframe: UCBoNbQjaMYdpJqPLRZAFkvQ. Nunca misturar OAuth/tokens, IDs ou estados.
- Episodios 101 e 201 ja possuem publicacoes em ingles. Nao duplicar; itens com status source_unconfirmed ficam fora da fila.
- O preparador scripts/preparar_publicados_en_v3.py nao executa audio, proxy de imagem, video ou upload; valida a correspondencia dos roteiros BR e EN e cinco abordagens de gancho.
- Usar ingles natural, narracao e legendas EN, metadados proprios, imagem inicial compreensivel e historia com recompensa real, sem conteudo enganoso.
- Reusar imagens PT somente se preservam continuidade e nao trazem texto PT gravado na arte. QA de video inteiro deve verificar pronuncia, movimento de personagens alem de zoom, direitos e MP4 completo.
- O publicador EN exige manifestos de origem coerentes, QA assinado e destino Otaku Reframe; upload privado por padrao e apenas com confirmacao explicita. Nunca publicar automaticamente durante o preparo.
- Consultar docs/OTAKU-REFRAME-PUBLICADOS-BR-EN-V3.md. Action verde nao comprova caches ou videos renderizados no Windows.
