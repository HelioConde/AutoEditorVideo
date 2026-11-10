## KIDS FOFINHO — ASSETS OFICIAIS DOS QUATRO SHORTS

- Fonte editorial: conteudos/kids-emanuelly-ep01-shortserie-v1.json.
- Fonte única de imagens e storyboard (4 partes):
  scripts/kids_fofinho_storyboards_v2.py. Cada quadro tem
  cenário, pose Manu, estado do ovo, pose Fofinho e gotas.
- Biblioteca persistente: scripts/kids_emanuelly_series_assets_v2.py.
  Imagens oficiais são registradas uma única vez com SHA-256.
  Não redesenhar jardim, quarto, ovo ou rosto do Fofinho a cada beat.
- PowerShell animar-emanuelly.ps1 suporta Parte 1,2,3,4,Todas;
  Catalogo lista cada recurso, Planejar mostra os pendentes,
  GerarImagens pode gerar faltantes com limite explícito de IA.
- Ordem do ovo: Parte 1 sempre fechado; Parte 2 quadros
  1/2 fechado, 3/4 rachado, 5 aberto, quadros 6+ Fofinho
  fora do ovo. Partes 3/4: não mostrar ovo original.
  Fofinho só aparece em Parte 2 beat 6, nunca antes.
- Gotas d'água são um único asset transparente repetido,
  com animação independente. Mesmo Fofinho azul, miando,
  patinhas e aconchegado referenciados ao sprite oficial.
- Imagens de Fofinha Arco-Íris, Fofinha Rosa, Raposo e
  Porco-espinho NÃO são requeridas nem renderizadas no EP01.
  As irmãs gêmeas só nascem UM ANO depois de Fofinho.
  Na Parte 4 beat 9 mostrar apenas brilhos abstratos.
- GerarImagens exige gpt-image-2 e edição com fonte oficial,
  sem fallback. Salvar resposta paga antes de QA e não
  gastar créditos regenerando assets válidos. Regeneração
  explícita -Refazer mantém versão anterior em histórico.
- Não alterar TTS/música aprovada nem substituir final.mp4.
  Renderiza final-camadas.mp4 em cada pasta de Parte.
- Nenhum upload, sem controle de canais; revisar o vídeo
  inteiro e só depois avaliar publicação em privado.
- Guia: docs/KIDS-FOFINHO-TODOS-VIDEOS-REFERENCIAS-V2.md.
- Testar tests/test_kids_fofinho_todos_videos_v2.py,
  testes Windows PowerShell e TypeScript Remotion.

## KIDS — REUTILIZAR CENARIOS E OBJETOS NA ANIMACAO

- A partir da Parte 1 de Emanuelly, USAR preferencialmente cenários
  e objetos oficiais fixos com camadas independentes em Remotion.
  Nunca redesenhar o jardim, o quarto ou o ovo para cada frase.
- Um único ovo-azul.png com gotinhas em todas as cenas; a cena 01
  mostra apenas ovo e jardim, sem Emanuelly. Manu aparece no
  jardim nas seguintes, e vai ao quarto a partir da cena 06.
  Nenhum Fofinho/irmãs/Raposo/Porco-espinho antes da apresentação.
- Quatro vistas jardins e quatro quartos oficiais. Todas
  instaladas localmente com animar-emanuelly.ps1 -Acao InstalarLote.
  A pasta assets/gerados/kids-emanuelly/cenarios-oficiais/ fica
  fora do Git; os SHA e históricos preservam cada referência.
- Mover personagem e ovo com transformações 2D independentes
  do cenário, usando poses PNG transparentes já aprovadas.
  Isso é animação por camadas, não rigging ou lip-sync completo.
  Priorizar ação visível em vez de zoom de câmera genérico.
- Preservar MP4 original final.mp4. Prévia em final-camadas.mp4,
  QA separado. A voz e a música existentes devem ser reutilizadas
  sem alterar volumes ou pedir novo TTS desnecessariamente.
- Compositor só para EP01 Parte 1 nesta versão; não
  aplicar automaticamente cenas desse episódio às outras partes.
- Sem geração de IA de imagem, sem upload, somente revisão local
  do vídeo completo depois de renderizar. Não alegar aprovação
  visual automática apenas pelo SHA dos recursos.
- Guia docs/KIDS-EMANUELLY-CENARIOS-CAMADAS-V1.md.
  Testes tests/test_kids_emanuelly_cenarios_camadas_v1.py
  e tests/test_animar_emanuelly_powershell.ps1.

## KIDS — CATALOGO DE POSES V2 ATUAIS E FUTURAS

- Usar scripts/kids_emanuelly_catalogo_poses_v2.py como fonte de
  46 novas poses e grupos. As 8 poses legadas EM POSE devem manter
  strings e SHA dos prompts originais: NÃO invalidar cache pago.
- Um total de 54 poses, divididas por Essenciais, Ep01, Carinho,
  Emocoes, Movimento, Brincadeiras, Cotidiano, Futuras e Todas.
- O PowerShell gerar-poses-emanuelly.ps1 recebe -Grupo, -Pose,
  -Quantidade, -MaxChamadas e ações Catalogo/Planejar/Gerar.
  O padrão continua Essenciais. A ação Catalogo não faz chamadas.
- Exemplo recomendado: -Acao Gerar -Pose fazendo-carinho
  -MaxChamadas 1, ou -Grupo Carinho -Quantidade 2 -MaxChamadas 2.
  Preferir lotes pequenos para inspecionar a fidelidade facial.
- Em poses de carinho, NÃO desenhar Fofinho ou qualquer outro
  personagem dentro do PNG: braços e mãos interagem com amigos ou
  objetos invisíveis que serão sobrepostos como camadas independentes.
  Respeitar a cronologia da série, incluindo as gêmeas e Raposo.
- Categorias de movimento e sequências são planejamento editorial,
  NÃO alegar rigging automático ou movimento de membros no Remotion.
- Continuar obrigatório GPT Image 2, PNG RGBA, referência privada
  em cada chamada, validação de alpha, cache de PNG bruto e histórico.
  A geração nunca publica vídeos, não toca trilha, narração ou outros canais.
- Documentação: docs/CATALOGO-POSES-EMANUELLY-V2.md.
  Testes: tests/test_kids_emanuelly_catalogo_poses_v2.py e
  suite Python/PowerShell legada de poses.

## EMANUELLY — ASSETS PARA ANIMACAO POR CAMADAS

- A personagem NÃO pode ser redesenhada com rosto, cabelo, roupa
  ou detalhes inventados. Cada pose deve ser gerada com a MESMA imagem
  de referência visual que o criador forneceu. Esta fonte fica
  localmente em assets/referencias-privadas/emanuelly-personagem-oficial.png,
  NUNCA em GitHub público.
- Comando gerar-poses-emanuelly.ps1 e
  scripts/gerar_poses_emanuelly_gpt_image_2.py.
  A ação Gerar usa exclusivamente gpt-image-2 com images/edits,
  referência em CADA pedido e background=transparent.
- Gerar 8 poses individuais: em-pe, caminhando, observando,
  ajoelhada, estendendo-mao, segurando-ovo (sem objeto),
  preparando-caminha (sem objetos), surpresa.
  Evitar repetição de poses e folha de personagens no mesmo quadro.
- Os PNGs devem ter alfa REAL, corpo inteiro, espaço nas bordas,
  sem cenário, ovo, jardim, quarto, pelúcias ou futuros personagens.
  O ovo, os cenários e os efeitos serão camadas reutilizáveis separadas.
- Orçamento de chamadas sempre explícito; -MaxChamadas 0 só consulta
  cache. Falhas e referências alteradas não sobrescrevem arquivos sem
  -Refazer, que guarda histórico. SHA do conteúdo e do prompt
  invalida caches anteriores.
- A semelhança de Emanuelly continua aguardando revisão HUMANA.
  Hash válido e alfa transparente não provam identidade facial.
- Esta biblioteca cria assets, NÃO renderiza animação articulada,
  NÃO muda narração/música e NÃO envia Shorts para YouTube.
- Documentação: docs/POSES-EMANUELLY-GPT-IMAGE-2.md.
  Testes: tests/test_gerar_poses_emanuelly_gpt_image_2.py
  e tests/test_gerar_poses_emanuelly_powershell.ps1.

## GERAÇÃO DA SÉRIE KIDS COM FOTO DE REFERÊNCIA

- Comando: gerar-historia-kids.ps1 (Planejar, InstalarReferencia,
  Imagens, Voz, Renderizar, Gerar, Verificar, Abrir).
- Script scripts/serie_kids_emanuelly_v1.py; 4 partes e 37
  quadros visuais no total, orçamento de chamadas de IA EXPLÍCITO.
- A foto privada NÃO PODE SER VERSIONADA NO GITHUB. Somente
  assets/referencias-privadas/emanuelly-elenco.png local, protegida
  no .gitignore. Nunca subir imagens do elenco infantil ou a foto
  original como anexos públicos a issues.
- Ao gerar quadro, utilizar OBRIGATORIAMENTE o Codex Proxy
  /v1/images/edits com a referência PNG em cada chamada.
  Se não suportado, bloquear e informar; NUNCA usar text-to-image
  sem referência como fallback, nem reciclar imagens de outro personagem.
- Usar SHA256 de foto, prompt, modelo e beat para cache de quadros;
  rejeitar materiais stale e preservar históricos quando -Refazer.
- Voz pt-BR-FranciscaNeural com pausas PCM e WordBoundary real
  (Kids Narração Acolhedora); manter <=60s MP4, <=59,2s áudio,
  perguntas com ~1,8s e narracao de 45-55s quando possível.
  Se não couber, ajustar roteiro sem acelerar ou truncar falas.
- Composição Remotion EmanuellySerieV1: 9/10/9/9 cenas ilustradas
  de referência e efeitos vetoriais independentes. NÃO alegar
  movimento articulado de personagens; avaliar a coerência dos quadros
  no vídeo completo depois de renderizar.
- Salvar em assets/gerados/kids-emanuelly/<id>/final.mp4, QA local,
  atualizar biblioteca Kids quando inicializada, não tocar Games,
  Otaku Multicena, Otaku Reframe ou a estrelinha azul.
- Sem OAuth, nenhum upload e nenhuma publicação automática.
  Canais infantis exigem Made for Kids e revisão de direitos.
- Documentação: docs/GERAR-SERIE-KIDS-EMANUELLY.md;
  testes: tests/test_serie_kids_emanuelly_v1.py e
  tests/test_gerar_historia_kids_powershell.ps1.

## SERIE KIDS — EMANUELLY E SEUS AMIGOS DE PELUCIA (CANONE)

- História-base integral e fatos confirmados dos personagens em
  `docs/KIDS-EMANUELLY-SERIE-BIBLIA-V1.md`.
  Nunca sobrescrever o conto-base ao adaptar para novos formatos.
- Episodio 01 `O Ovo Azul e o Nascimento de Fofinho` tem quatro
  Shorts narrativos planejados em
  `conteudos/kids-emanuelly-ep01-shortserie-v1.json`.
  Cada parte com abertura envolvente, descoberta real e final de curiosidade
  leve que se resolve no começo da proxima parte.
- Máximo absoluto de 60 segundos no MP4. Alvo de 45-55 segundos com TTS
  acolhedor PT-BR e pausas reais. A duracao so e confirmada depois de
  sintetizar e medir; nao truncar, nao acelerar demais, nem cortar
  os intervalos de resposta das criancas.
- Fofinho e um gato de pelucia azul, nasceu de ovo de dragao encontrado
  por Emanuelly e controla agua. Arco-Iris e Rosa sao gatinhas gemeas,
  irmas mais novas; nascem UM ANO apos Fofinho. Nao antecipar seu
  nascimento no EP01 e nao inventar quantos ovos originam as gemeas.
- Raposo e uma ONCA de pelucia apelidada por sua criacao entre
  raposas/canideos; pega brinquedos porque deseja companhia, nao porque
  seja mau. Porco-espinho de pelucia adora abracos. Emanuelly e
  a protagonista afetuosa. Aparencia visual deve usar arte aprovada,
  nao inventar caracteristicas fisicas do retrato.
- Suspense infantil = descoberta e curiosidade, nunca perigo assustador,
  punicao, urgencia ou manipulacao de engajamento. Evitar pedidos
  de inscricoes/comentarios e manter Made for Kids.
- Manter figurinos, paleta, poderes, personalidade, quarto, ovo e efeitos
  consistentes entre partes. Cada parte deve entregar mini-recompensa
  (ovo acolhido / nascimento / agua magica / amizade).
- O manifesto e apenas PLANEJAMENTO EDITORIAL: sem mp4, TTS, uploads nem
  integracao automatica ao motor Kids ainda. Nao afirmar que ja esta pronto
  para renderizacao ate implementar e testar.
- Testar `tests/test_kids_emanuelly_serie.py` quando alterar roteiro.
  Manter `kids-001-estrela-azul` e demais projetos isolados.
