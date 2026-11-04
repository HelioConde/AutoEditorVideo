# Arquivo Otaku — orientações para agentes

Projeto local de produção de Shorts em PT-BR: radar editorial, roteiro revisado,
imagens anime via Codex Proxy local, edição com MoneyPrinterTurbo/FFmpeg,
miniaturas e upload OAuth para YouTube.

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
