# Arquivo Otaku — orientações para agentes

Projeto local de produção de Shorts em PT-BR: radar editorial, roteiro revisado,
imagens anime via Codex Proxy local, edição com MoneyPrinterTurbo/FFmpeg,
miniaturas e upload OAuth para YouTube.

## REGRA PERMANENTE: PRODUCAO DE VIDEOS PELO AUTOEDITORVIDEO NO GITHUB

- **TODOS os novos Shorts do Otaku Reframe (EN) e Otaku Multicena (PT-BR)** devem
  ser produzidos pelo pipeline deste repositorio: roteiro/manifesto local,
  storyboard, artes originais geradas pelo Codex Proxy configurado neste projeto,
  vozes sincronizadas pelo Edge TTS, composicao Remotion/FFmpeg, QA e export MP4.
- **NAO usar editores ou compositores externos** (vidIQ Compose, Cloudinary video
  transformations, geradores de video avulsos, montagens vetoriais externas,
  slideshows ou demos graficas) como substitutos do render final do AutoEditorVideo.
  Links de previas externas nunca sao considerados um video do projeto aprovado.
- Para novos Shorts originais EN, o manifesto deve trazer `production` com
  `engine=AutoEditorVideo`, `images=codex-proxy`, `narration=edge-tts`,
  `captions=WordBoundary`, `editor=remotion`, `qa=manual-per-scene`,
  `external_rendering=false` e `auto_publish=false`.
- **Bloqueio obrigatorio:** se faltar imagem, camada alfa, storyboard EN, voz,
  legenda, revisao visual de QUALQUER cena ou duracao <=60s, **nao renderizar
  como pronto, nao entregar como final e nao publicar**. Diagnosticar sem gastar
  chamadas de IA; preservar caches e arquivos ja publicados.
- O fluxo oficial do canal EN e `gerar-otaku-reframe.ps1` com
  `-Acao Preparar`, `-Acao GerarImagens` (orcamento explicito),
  `-Acao Validar` (aprovacoes obrigatorias) e
  `-Acao Renderizar -ConfirmarRevisaoVisual`.
- Os arquivos de producao locais, video, imagem e credenciais **nao** devem ser
  enviados para o GitHub. GitHub armazena codigo, roteiros, prompts e testes;
  execucao das artes e do render e feita no Windows local do usuario.
- **Nao efetuar upload ao YouTube/TikTok** sem pedido e aprovacao explicitos.
  O video EN existente de Death Note EP01 nao deve ser substituido.
- O usuario rejeitou o preview experimental em graficos vetoriais para o
  `201-death-note-rosto-nome`. Descarta-lo como saida, gerar imagens originais
  pelo Codex Proxy e revisar todas antes de considerar o Short concluido.

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
