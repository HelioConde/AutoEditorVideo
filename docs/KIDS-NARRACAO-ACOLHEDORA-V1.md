# Narração Acolhedora Kids V1 — teste com a estrelinha azul

## Por que este teste existe

A versão antiga tinha uma única fala contínua: a criança não tinha
tempo para observar a casinha nem responder antes da narradora.

O experimento **não altera Gamer, Otaku Multicena, Otaku Reframe
ou os dois outros Shorts Kids**. Afeta somente o ID:

    kids-001-estrela-azul

A história agora tem 13 blocos narrados em português brasileiro,
com frases calorosas, perguntas e agradecimento final. A narradora
segue com voz pt-BR-FranciscaNeural em velocidade -15%.

## Pausas verdadeiras

- Entre frases: 0,6–0,9 segundos na maioria dos blocos.
- Após "Será que é essa casinha vermelha?": 1,8 segundo.
- Após "E essa casinha amarela?": 1,8 segundo.
- Após "Será que é essa?": 1,8 segundo.
- Total planejado de silêncios inseridos entre trechos: 11,8 segundos.
- Meta editorial: aproximadamente 45–55 segundos, **não uma duração
  obrigatória**. O resultado real depende da síntese e deve ser medido.
- Bloqueio técnico: narração PCM acima de 59,15 segundos e MP4
  final que não atenda ao limite interno de 60 segundos.

O código gera **cada fala individualmente**, extrai PCM 48 kHz mono
com FFmpeg, acrescenta quadros exatos de silêncio e reexporta MP3.
WordBoundary de cada fala é deslocado para a posição correta do
áudio final. Legendas terminam antes das pausas, não respondem perguntas
antecipadamente, e as cenas são sincronizadas ao áudio real.

A animação original usa 13 intervalos independentes: a estrela olha
para a casa vermelha, espera a criança, responde; repete o processo
na amarela e, diante da azul, aguarda a criança antes de comemorar.
A câmera fica estável e o movimento do personagem é suave.

## Testar no Windows

    cd "C:\Users\helio\Documents\arquivo-otaku-github"
    git pull --ff-only origin main

    # Primeiro ver o plano, sem fazer TTS nem render
    .\piloto-canais-v3.ps1 -Acao inspecionar -Canal kids -Id kids-001-estrela-azul

    # IMPORTANTE: -Refazer substitui a voz antiga de ~25 segundos
    # por uma com pausas e marcas de palavras atualizadas.
    .\piloto-canais-v3.ps1 -Acao voz -Canal kids -Id kids-001-estrela-azul -Refazer

    # Se Remotion ainda nao estiver instalado:
    cd motion-remotion
    npm.cmd install
    cd ..

    # Produzir o video 9:16 com a nova timeline, sem publicar.
    .\piloto-canais-v3.ps1 -Acao renderizar -Canal kids -Id kids-001-estrela-azul -Refazer

    # Verificar tecnicamente (sem upload):
    .\piloto-canais-v3.ps1 -Acao verificar-video -Canal kids -Id kids-001-estrela-azul

A criação da narração requer acesso ao Edge TTS, ffmpeg e ffprobe.
A renderização exige Node, Remotion e FFmpeg/FFprobe.
O cache antigo é invalidado quando o roteiro ou as pausas mudarem.
Se exceder 60s, **o programa não remove pausas automaticamente nem
acelera a voz**: reduzir fala mantendo as respostas será uma nova
decisão editorial.

Arquivos locais gerados:

    assets/gerados/piloto-canais-v3/kids/kids-001-estrela-azul/
      narracao.mp3
      marcacoes-voz.json
      final.mp4
      qa-local.json

marcacoes-voz.json inclui segments (início da fala, fim da fala,
fim da pausa, cena, título e ID do bloco), words com tempo absoluto,
duration_pcm_s, total_pause_s, hash do roteiro e da timeline.
Todos os caminhos continuam no canal Kids; o MP4 final integra
a biblioteca de vídeos após a primeira organização.

## Critérios de avaliação no YouTube Studio

Primeiro, assistir ao arquivo renderizado e confirmar integridade
técnica. Se o canal Kids existir e o titular autorizar explicitamente
um envio, usar a conta e o token corretos, classificação Made for
Kids e visibilidade privada para revisar o vídeo completo no Studio.
**Este teste não conecta OAuth, não envia MP4 nem publica nada.**

Avaliar especialmente:
- A criança consegue olhar a casa durante os 1,8s?
- A resposta só aparece na voz e imagem **depois** da pausa?
- A narradora mantém um tom acolhedor, sem fala robótica ou corrida?
- Texto e movimentos estão sincronizados e sem excesso de estímulos?
- O final agradece, sem pedir like, inscrição ou comentários?

Se o teste funcionar, o mesmo padrão pode ser adaptado aos Shorts
dos passarinhos e das formas, cada um com suas próprias pausas.
