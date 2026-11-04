# Narração Acolhedora Kids v1 — teste da estrelinha azul

## Objetivo

Trocar o ritmo excessivamente acelerado (cerca de 25 segundos) por uma história acolhedora, com tempo real para crianças de 4 a 7 anos observarem e responderem.

Neste piloto, somente kids-001-estrela-azul muda:
- Voz pt-BR-FranciscaNeural (-15%), com 13 frases individuais;
- 13,1 segundos de pausas solicitadas antes da geração, não apenas reticências;
- Pausas secundárias ajustadas automaticamente se a duração real das falas ultrapassar o limite; as perguntas preservam os 1,8 segundo de resposta;
- Esperas de 1,8 segundo após cada pergunta sobre casinhas;
- Final afetuoso: "Obrigada por ajudar a estrelinha azul a encontrar sua casinha!";
- Duração-alvo de 45–55 segundos, com bloqueio acima de 59,2 segundos;
- Cinco cenas visuais originais com 13 estados temporais. A casinha azul só aparece quando a narradora revela sua chegada.

Os demais Kids, Games, Otaku Multicena e Otaku Reframe não são modificados.

## Implementação

O manifesto conteudos/piloto-games-kids-3x2-v3.json tem o campo kids_pacing: texto, cena, cue, manchete e pausa pós-frase.

O módulo scripts/kids_narracao_acolhedora_v1.py:
1. Gera cada frase no Edge TTS e cacheia por hash de texto/voz/taxa.
2. Usa FFmpeg para decodificar os trechos de MP3 em PCM mono 48kHz.
3. Mede o tempo real da fala e calcula as pausas efetivas. Se a soma original ficar longa demais (ex.: **62,2 s = 49,1 s de fala + 13,1 s de pausas**), reduz somente pausas secundárias e mantém **1,8 s** nas perguntas. Para esse exemplo, a estimativa é cerca de **58,5 s**. Não acelera a voz nem elimina perguntas. Se nem as pausas mínimas couberem, bloqueia e informa quantos segundos de roteiro precisam ser cortados.
4. Adiciona silêncio PCM real e exporta narração.mp3, verificada com FFprobe.
5. Preserva marcações de tempo de cada palavra, 13 estados visuais, legendas sem texto durante pausas e divisão de cinco cenas. Registra `pause_adaptation` com pausas originais, efetivas e tempo economizado.
6. Guarda versões anteriores de narração e vídeo em historico-voz e historico-renders.
7. Interrompe se a voz não for gerada ou se ultrapassar 59,2s; nunca inventa áudio ou acelera a fala automaticamente.

A animação Remotion mantém movimentos leves durante as pausas e mostra as casinhas no momento certo. Não há animações piscantes, sustos, CTA de comentários/inscrições, nem upload embutido.

## Comando no Windows

    cd "C:\Users\helio\Documents\arquivo-otaku-github"
    git pull --ff-only origin main

    # Validar e preparar sem gastar TTS
    .\kids-narracao-acolhedora.ps1 -Acao Planejar

    # Gerar voz com pausas, renderizar e verificar o MP4 local
    .\kids-narracao-acolhedora.ps1 -Acao Testar

    # Abrir no player do Windows
    .\kids-narracao-acolhedora.ps1 -Acao Abrir

Também é possível executar fases separadas:

    .\kids-narracao-acolhedora.ps1 -Acao Voz -Refazer
    .\kids-narracao-acolhedora.ps1 -Acao Renderizar -Refazer
    .\kids-narracao-acolhedora.ps1 -Acao VerificarVideo

Requisitos reais: Python .venv e edge-tts, internet para TTS, FFmpeg e FFprobe no PATH, Node/npm e Remotion instalado em motion-remotion (npm.cmd install). O primeiro teste realiza várias chamadas Edge TTS; caches reduzem repetições.

Saída: assets/gerados/piloto-canais-v3/kids/kids-001-estrela-azul/final.mp4.
O arquivo anterior não é descartado: é arquivado antes de substituição. Se a biblioteca dos quatro canais existir, o render atualiza sua pasta Kids automaticamente.

## Revisão

- Alvo 45–55s; tempo final real depende da voz Edge. Não forçar duração preenchendo silêncio desnecessário.
- Regras técnicas de duração, integridade de áudio, formato 9:16 e cache continuam obrigatórias.
- Avaliação artística do vídeo completo ocorre depois, preferencialmente no YouTube Studio em upload privado, quando houver conta Kids real verificada.
- O script NÃO envia para YouTube, não conecta OAuth e não cria canal.
- O público infantil deve ser identificado corretamente como Made for Kids quando um publicador for criado.
- Os testes automáticos usam vozes simuladas: não provam a prosódia real ou o resultado final no Windows.

Testes em tests/test_kids_narracao_acolhedora_v1.py e tests/test_kids_narracao_acolhedora_launcher.ps1. Compilação TypeScript via npm run typecheck em motion-remotion.

Primeiro experimento controlado: comparar com o Short anterior de aproximadamente 25 segundos; alongar a história só vale se a compreensão e a experiência melhorarem.
