# Arquivo Otaku — orientações para agentes

## REGRA — CINCO CANAIS YOUTUBE SEPARADOS (05/11/2026)

- Registro oficial: config/youtube-channel-registry.json; validar com scripts/youtube_channel_registry.py. Sao **cinco canais**, sem reutilizar ID, OAuth, thumbnail, voz ou metadados de outro.
- Otaku Multicena BR: UCXGYTuBYn-0Ziqin5ajKhOw; Otaku Reframe EN: UCBoNbQjaMYdpJqPLRZAFkvQ (uploaders existentes preservados).
- Gamer: UCg77gYc1_wkHuL07XPtKcow; YouTube exibe **Hélio Conde**, **Conde Games** e proposta ainda nao aplicada na conta. Exigir gameplay real e/ou autorizado.
- Kids: UCxEzVW2Uy44OUVurTQSg_Eg; YouTube exibe **Emanuelly Kids**, a serie oficial e **Fofinhos**. Toda publicacao para criancas deve ter classificacao Made for Kids, sem CTA para comentarios/inscricoes de criancas. Nunca publicar fotos privadas nem musicas sem direitos.
- Alchemy Lab: UCCTYFE5Cmz2aYZ37cJQ-wcg; YouTube exibe **Alchemy Flames**; a identidade planejada e **Alchemy Lab** (IA pratica e automacoes). Nunca afirmar que o nome foi alterado na conta; nunca falsificar testes ou criar conteudo repetitivo de baixo valor.
- Os tres novos canais estao **somente registrados**, com OAuth e publicacao cloud DESATIVADOS; criar Environment e token proprios somente apos autorizacao especifica e verificacao do ID via channels.list(mine=true). Nunca usar segredos YouTube Otaku/CodeX Proxy como substitutos.
- Manter roteiros/miniaturas originais, categoria e idioma por canal, default privado, verificacao de direitos, QA e controle de duplicatas. Os pilotos antigos Checkpoint Pixel/MiniMundo Curioso permanecem isolados com upload_enabled=false e IDs nulos; sao drafts, NAO sao identidade do Emanuelly Kids.
- Reservar cada (canal, episodio) antes de gerar scripts, comandos PowerShell ou MP4s usando conteudos/otaku-production-reservations.json, agora compatível com cinco canais; nenhum upload e geracao sao autorizados apenas pelo registro.
- Guia: docs/CANAIS-5-YOUTUBE-GITHUB.md.


## REGRA PERMANENTE — RESERVAR NO GITHUB ANTES DE QUALQUER VIDEO/COMANDO

**Regra definida pelo criador em 05/11/2026:** toda vez que solicitar ao
ChatGPT/Codex um script, comando PowerShell, workflow, lote ou vídeo para gerar,
**registrar primeiro no GitHub** o episódio e o canal como `reserved` ou
`in_production` em `conteudos/otaku-production-reservations.json`.
O registro deve ser integrado à `main` antes de consumir chamadas de imagem.

- A reserva é por par `channel + id`: BR Otaku Multicena e EN Otaku
  Reframe têm estados e OAuth independentes.
- A geração cloud deve exigir a reserva correta com
  `scripts/production_reservations.py` e seu `reservation_owner`.
  Ausência de registro, reserva de outro job, `published`,
  `in_production`, `existing_assets_unverified` ou vídeo já gerado
  bloqueiam a seleção automática. Nunca assumir que falta de pasta significa
  vídeo inédito ou que uma pasta prova publicação.
- A fila atual: `5009-overgeared` e `5010-aoashi` em produção pelo
  criador (não usar de novo); `5008-firefly-wedding` já publicado;
  `5011-gachiakuta` reservado para **dois Shorts separados BR e EN**;
  depois disso, o próximo candidato BR é `5012-solo-leveling`, sujeito
  a nova verificação no canal e à reserva antes de qualquer script.
- Antes de escolher novo episódio, conferir o registro versionado e, quando
  disponível, o histórico do YouTube incluindo privado/agendado; registrar
  alterações observadas. Se houver conflito, bloquear em vez de gerar outro vídeo.
- Publicar privado por padrão, **apenas** com token OAuth do canal identificado
  e verificado. Não inferir autorização do YouTube a partir de sessão OAuth do
  proxy de imagens. Agendar somente se data e hora forem definidas.
- A regra vale também se o usuário pedir só um comando ou PowerShell para gerar
  vídeo, não apenas quando solicitar uma produção completa. O registro precisa
  preceder a entrega do comando; não depender de memória de conversa.


Projeto local de produção de Shorts em PT-BR: radar editorial, roteiro revisado,
imagens anime via Codex Proxy local, edição com MoneyPrinterTurbo/FFmpeg,
miniaturas e upload OAuth para YouTube.


## MUSICA DE FUNDO DOS KIDS — DUAS FAIXAS DE ENTRADA

- Musicas originais adicionadas na raiz do repositorio em 04/11/2026:
  `Wondertrail _Main Theme_.mp3`, `Wondertrail _Main Theme_2.mp3`.
  Nao renomear, modificar ou mover estes fontes.
- Usar apenas nos renders Kids, nunca Gamer/Otaku.
  Alternar na serie Emanuelly (Partes 1/3 = faixa 1; Partes 2/4 =
  faixa 2). Pilot Kids usa padrao estavel.
- O volume padrao do Remotion e 7,5% (teto absoluto de 12%),
  com fade-in/out 1,5s; narracao TTS em primeiro plano e pausas
  de compreensao preservadas. Ouvir o resultado real antes de publicar.
- Modulo de preparo: `scripts/kids_musicas_fundo_v1.py`.
  Somente copia local para a pasta gerada do Remotion; hash SHA-256
  garante integridade. O cache de render Kids deve exigir a assinatura
  da faixa atual. Alterou trilha => gerar nova versao de MP4.
- Nao alegar que estas musicas sao liberadas para publicacao:
  **direitos/licenca nao verificados**. Manter
  `music_rights_review=pending_before_publication`
  ate o titular comprovar autorizacao de uso, especialmente no YouTube.
  Nada de upload automatico; evitar reclamações de copyright.
- Manter a musica baixa e sem abafamento de voz. Testar
  `tests/test_kids_musicas_fundo_v1.py` e compilacao Remotion.

## REGRA CRÍTICA — PERSONAGENS NASCEM ANTES DE APARECER (KIDS)

- Em 04/11/2026, o criador confirmou erro grave na Parte 1,
  especialmente quadro 08: Fofinho e Fofinha Arco-Íris foram
  mostrados ao lado de Emanuelly **antes de nascerem**.
  É proibido repetir isto em qualquer nova geração.
- **EP01 Parte 1, TODOS os nove quadros: Emanuelly (Manu) é
  a única personagem visível; ovo de dragão AZUL permanece fechado.
  Nenhum bichinho de pelúcia pode aparecer, nem ao fundo, como reflexo,
  silhueta, brinquedo decorativo ou figurante.**
- EP01 Parte 2 quadros 01–05: só Emanuelly e ovo ainda fechado/
  abrindo; Fofinho ainda não saiu. A partir do quadro 06, aparecem
  Emanuelly e Fofinho **azul**. Partes 3–4: apenas os dois.
- Fofinhas Arco-Íris e Rosa são gêmeas nascidas UM ANO depois;
  Raposo e Porco-espinho serão apresentados no futuro e NUNCA
  podem aparecer em EP01. Não antecipar fisicamente novos personagens.
- A prancha original do elenco é APENAS uma fonte para criar dois
  arquivos de referência **isolados e privados**: emanuelly-solo.png
  (1 pessoa) e emanuelly-fofinho.png (somente 2 personagens).
  Nunca enviar prancha do elenco inteiro como referência de quadros.
  Não assumir que texto negativo basta para conter vazamento.
- Preparar estas imagens via
  `gerar-historia-kids.ps1 -Acao PrepararReferencias -MaxChamadas 2`.
  São 2 chamadas GPT Image 2 e ficam fora do Git.
  O isolamento visual é um auxílio, não uma garantia de visão:
  avaliar o MP4 completo antes de publicar.
- O gerador Kids com referência DEVE usar exclusivamente
  **gpt-image-2**; `gpt-image-1.5` é rejeitado. Nunca fazer fallback
  de modelo quando tiver imagem de referência.
- Cada quadro usa apenas a referência permitida pela cronologia,
  com política versionada `emanuelly/character-continuity/v2`,
  SHA-256 do elenco e da imagem isolada, e QA de entrada/saída.
  Cache com a política antiga é INVÁLIDO e não pode entrar no render.
- Corrigir precisamente o quadro 03 (só Emanuelly e efeitos mágicos
  abstratos, sem pelúcias) e 08 (só Emanuelly e o mesmo ovo azul
  no mesmo quarto noturno). Preservar os arquivos anteriores em
  histórico; regenerar Parte 1 com `-Acao Imagens -Parte 1
  -MaxChamadas 9 -Refazer` depois de preparar as referências.
  NÃO alterar a história original e não publicar por esta ação.

## CORREÇÃO KIDS — ENQUADRAMENTO DE POSES E RESPOSTA PAGA

- O criador reportou em 04/11/2026 o erro
  `Personagem encostou na borda e pode ficar cortada: caminhando`
  durante `gerar-poses-emanuelly.ps1 -Acao Gerar -Pose Todas -MaxChamadas 7`.
- A pose paga NÃO pode ser perdida por um teste de margem. Salvar
  imediatamente o PNG original em `poses/brutos/` com hash,
  modelo e identidade de referência ANTES de QA.
- Reenquadrar APENAS pixels existentes, com Pillow e transparência
  real em `scripts/kids_poses_enquadramento_v1.py`: ajustar o alpha
  bbox para margem segura e preservar proporção. Zero nova IA.
- Não afirmar que isso recupera partes do corpo ausentes. Se o PNG
  original toca a borda, marcar `source_may_already_be_cropped`
  e exigir revisão visual. Nunca fabricar dedos ou mãos.
- A execução seguinte deve reconhecer PNG bruto válido e fazer
  QA novamente com `-MaxChamadas 0`, sem reenvio ao proxy.
  `Planejar` indica custo real: respostas brutas recuperáveis
  não contam como novas chamadas.
- `em-pe` já aceita no cache anterior DEVE continuar válida mesmo
  após reforço do prompt de enquadramento, para que o lote restante
  continue com até 7 chamadas e não se perca a pose aprovada.
- Não alterar a referência privada, áudio, música, renderizador
  ou outros canais. Nenhum upload ou publicação automática.
- Testar regressão em `tests/test_gerar_poses_emanuelly_gpt_image_2.py`.


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

## KIDS — NARRACAO ACOLHEDORA V1, TESTE ISOLADO

- O usuário deseja histórias infantis com fala calorosa, perguntas simples
  e pausas reais para a criança entender e responder. NAO apenas reduzir
  a velocidade global nem narrar literalmente "pausa".
- Somente kids-001-estrela-azul recebeu kids_pacing (13 frases,
  13,1s de pausas **solicitadas**, podendo diminuir automaticamente apenas pausas
  secundárias após medir o TTS, e **1,8s intocáveis** após perguntas).
  Exemplo de 62,2s é ajustado para cerca de 58,5s; não acelerar a voz.
  Meta 45–55s e
  limite técnico de áudio 59,2s, vídeo final <=60s.
- Gerar TTS em blocos com Edge pt-BR-FranciscaNeural, PCM 48kHz e
  silêncio real; preservar WordBoundary, hash do roteiro/pausas, áudio
  anterior e MP4 anterior. Falhas de voz não podem criar silêncio falso.
- Storyboard de 5 cenas tem 13 marcadores de ação; vermelho e amarelo
  são apresentados antes de azul. NÃO revelar a casa azul antecipadamente.
- Em pauses as legendas desaparecem; estrelas continuam movimento suave,
  sem flashes, cortes agressivos ou chamadas a comentar/inscrever.
- Command local: kids-narracao-acolhedora.ps1 -Acao Testar.
  NUNCA chamar upload; a avaliação visual ocorre no vídeo completo,
  e o canal infantil ainda precisa ser criado e marcado Made for Kids.
- Não alterar o ritmo dos Games, Otaku Multicena ou Otaku Reframe.
- Ver docs/KIDS-NARRACAO-ACOLHEDORA-V1.md e testes dedicados.

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
- **REGRA ATUALIZADA 05/11/2026 — CLOUD-FIRST:** o objetivo principal para
  Otaku Multicena BR e, futuramente, EN/Kids e gerar o roteiro, imagens, voz,
  animacoes, MP4 e QA integralmente no **GitHub Actions**, usando o motor
  AutoEditorVideo original (Codex Proxy Go nativo, Edge TTS, Remotion/FFmpeg).
  Nunca substituir por renderizacao externa/vidIQ, previews vetoriais ou
  pedir render local no Windows como passo obrigatorio. O cache do Windows
  nao aparece automaticamente no runner; planejar armazenamento seguro.
- Nunca enviar tokens, `.secrets`, cache bruto de IA, fotos privadas de
  criancas ou logs de credenciais ao repositorio nem a Actions artifacts.
  **Excecao explicita somente para pilotos BR nao pessoais autorizados:**
  um artifact temporario (retencao 1 dia) pode conter apenas MP4 final,
  capa, metadados e QA, com aviso de que leitores do repositorio publico
  podem acessa-lo. Rever armazenamento privado antes de rotina em escala.
- O upload para YouTube depende de OAuth do canal correto e privacidade
  adequada; neste momento, o job cloud BR gera apenas video para revisao,
  sem upload. Nao exigir Windows para *geracao*. Antes de mover o upload
  para Actions, implementar OAuth segregado, verificacao do canal,
  controle de duplicatas e escopos/credenciais apropriados.
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
