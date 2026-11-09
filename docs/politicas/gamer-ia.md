## REGRA PERMANENTE — FIM DE SHORTS E MINIATURAS GAMER + IA (05/11/2026)

### Identidade visual validável — modelo de referência do criador
- Thumbnail Gamer/IA: usar `scripts/capa_cinematografica.py` com
  `template='gamer-alchemy-reference'`, arte IA original, título branco
  serifado curto no topo, contraste e duas linhas vermelhas discretas;
  nunca usar outra rotina de montagem ou faixa inferior.
- Vídeo Gamer/IA: `motion-remotion/src/master-short.tsx` com
  `visualProfile='gamer-alchemy-reference'`, título legível fixo no
  topo da amostra; caixa escura compacta dentro da cena para 2–3 palavras,
  com a palavra falada em amarelo `#ffd166`. Tempos devem vir de
  `scripts/legendas_precisas.py` a partir de WordBoundary reais.
- O padrão anterior `visualProfile='original'` continua sendo o padrão
  para os outros canais. Não reutilizar o estilo do teste em Kids ou Otaku.
- Teste de homologação: `game-901-estilo-referencia-5s`, código
  `scripts/gamer_reference_style_5s.py` e workflow
  `.github/workflows/gamer-reference-style-5s.yml`. Usar somente
  frames IA já gerados; o teste não justifica geração paga de imagens.
- Verificação obrigatória: vídeo exatamente 5s em 1080×1920, capa
  1080×1920, palavras sincronizadas no Remotion, destino YouTube Gamer
  exato e upload inicial PRIVADO; não alterar os seis V3 existentes.


- **O AutoEditorVideo é o único gerador das capas.** Não criar miniaturas
  paralelas por PIL ad hoc, screenshots aleatórias, ferramentas externas ou
  montagens enviadas ao vídeo. Reutilizar `scripts/capa_cinematografica.py`
  (`render_cover`) a partir das artes originais geradas pelo pipeline.
  Usar layout da referência com título branco serifado no topo.
- **As legendas seguem obrigatoriamente o padrão do programa existente:**
  `scripts/narracao_shorts.py` para voz/WordBoundary,
  `scripts/legendas_precisas.py` para grupos de 2–3 palavras e
  `motion-remotion/src/master-short.tsx` (`ArquivoOtakuMaster`) para
  renderizar com palavra pronunciada em amarelo (`#ffd166`), texto
  branco grosso, fundo escuro e margens originais. Não substituir
  pelo ASS simples do piloto Gamer/Alchemy V1/V2.
- Para estes 6 Shorts, a revisão que usa esses componentes canônicos
  é `scripts/games_alchemy_native_v3.py`. V1/V2 são rascunhos privados,
  não a versão final aprovada. Antes de qualquer upload público,
  inspecionar o MP4 completo, as capas e as palavras destacadas.

- A **narração** deve terminar com um CTA relevante ao tema, por exemplo uma
  pergunta concreta e um convite para se inscrever/acompanhar o próximo Short.
  Proibido terminar narrando metadados de produção: "este vídeo foi criado por
  IA", "não é gameplay", "não é captura de tela", "não testamos o modelo", etc.
- **Não ocultar/falsificar** a natureza dos visuais: avisar na **descrição**
  que as imagens são ilustrações geradas por IA, classificar conteúdo sintético
  conforme regras da plataforma e nunca afirmar gameplay ou teste realizado.
- Estilo obrigatório de thumbnails nos canais Gamer e IA: referência
  `image(20261105-151450).png`; formato **9:16**, arte ilustrativa
  cinematográfica de corpo inteiro, título resumido em **BRANCO, CAIXA ALTA,
  FONTE SERIFADA** no **TOPO**, contorno preto e contraste adequado. Sem
  faixas de texto na parte inferior, logos que tapem a arte, títulos longos,
  recortes de personagens ou grafismos publicitários espalhafatosos.
- Em refações, gerar MP4 novo sem legendas anteriores queimadas e revisar
  as legendas novas com margem horizontal, evitando cortar palavras.
- Para versões já enviadas ao YouTube, nunca afirmar substituição in-place:
  fazer novo upload privado após reserva/versionamento, conferência de ID e QA,
  preservar o vídeo privado anterior até autorização explícita para exclusão.
- Referência de seis roteiros corrigidos e títulos de capas:
  `conteudos/lote-6-games-alchemy-recut-v2.json`.

## REGRA OFICIAL — GAMER E IA USAM SOMENTE IMAGENS GERADAS POR IA (05/11/2026)

- **Gamer (Hélio Conde): é proibido capturar, solicitar, baixar ou exigir gameplay real.**
  Ilustrar notícias, nostalgia, curiosidades e conceitos de jogos com artes
  e cenas originais geradas por IA; não apresentar essas artes como captura real
  de jogo, conquistas, resultados testados ou produto oficial.
- O terceiro quadro Gamer chama-se **Jogos em Alta**, substituindo
  "Jogos do Momento" nos próximos catálogos; não há "testei", "joguei",
  "consegui", "venci" ou desafios fingidos.
- Em descrições Gamer, acrescentar transparência:
  "🎨 Visuais ilustrativos gerados por IA; não são capturas de gameplay."
- **Canal IA:** usar imagens/cenas geradas por IA para explicar novidades,
  recursos e tutoriais conceituais. Nunca simular screenshots de produtos,
  resultados de testes ou tutoriais executados. Comparativos sem experimento
  devem ser análises das funcionalidades confirmadas, não um "Testei por Você!".
- Quadro equivalente para estudos sem testes: **IA Sob a Lupa**.
  Para alegar um experimento, registrar prova do resultado real e revisão
  factual antes de publicar; não inventar comparações.
- O motor pode animar ilustrações por camadas com efeitos de câmera suaves,
  evitando deformar personagens, saltos bruscos e falso movimento real.
- Prioridade de fontes: 50 pautas Gamer em
  `conteudos/helio-conde-games-grade-50-seo-v1.json`; 50 pautas IA em
  `conteudos/alchemy-lab-grade-50-v1.json`. Lote piloto reservado em
  `conteudos/lote-6-games-alchemy-producao-v1.json`.
- Respeitar registro de reservas, OAuth exclusivo por canal, verificação exata
  de Channel ID, privacidade inicial `private`, QA audiovisual e material
  produzido. A existência de secrets no GitHub NÃO comprova o upload nem
  substitui a verificação no momento da publicação.
- Esta regra editorial do criador prevalece sobre instruções antigas de
  "capturar gameplay real" relativas aos canais Gamer/IA; **não altera
  o canal Kids nem os dois canais Otaku**.
