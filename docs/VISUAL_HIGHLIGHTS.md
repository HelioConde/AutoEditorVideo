# AutoEditor — Shorts por movimento visual (fase experimental)

Esta fase resolve a impossibilidade de sugerir Shorts de material sem narração, como alguns gameplays, cenas externas e vídeos silenciosos.

### Pipeline local

1. FFmpeg inspeciona os quadros a **2 FPS / 160 pixels de largura**, utilizando `signalstats` para obter diferenças de luminosidade entre quadros sucessivos (`YDIF`).
2. O motor `rankVisualShorts` cria janelas de 12s (gameplay), 16s (tutorial) ou 18s (podcast); aceita origem de 8 segundos a 10 minutos.
3. Descarta janelas com menos de 8 quadros medidos, cobertura insuficiente, média de movimento inferior a 1,5 ou menos de 30% de quadros acima do limiar de diferença 2.
4. Classifica as janelas restantes, remove sobreposições e apresenta até 3 candidatos com justificativa, prévia e seleção explícita.
5. A exportação gera MP4 independentes em 9:16; se a origem não tiver SRT, não grava nenhuma legenda.

Quando há transcrição, o ranking continua usando falas e combina sinais adicionais de movimento, RMS e cortes de cena. O vídeo nunca é enviado a uma API externa.

### Limitações

Movimento pode vir de uma câmera tremida, água, transições ou ruído. Portanto, o algoritmo **não entende o valor narrativo** da cena e não garante que o trecho será atrativo. Vídeos estáticos permanecem sem sugestões. Modelos de ação, face tracking, detecção de eventos de jogo, VAD e legendas por palavra ainda não foram incorporados.

### Qualidade

- `npm test`: parsers, janelas de movimento, rejeição de cenas estáticas e testes FFmpeg reais.
- `npm run test:e2e`: cria vídeo silencioso animado, analisa, apresenta candidato, exporta MP4 720×1280 e confere ausência de faixas de legendas.
- `npm run qa:media`: mede atividade visual nos vídeos reais já anexados ao repositório, sem presumir que todos têm destaques.
