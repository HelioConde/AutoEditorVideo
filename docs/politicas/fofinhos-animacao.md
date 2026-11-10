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
