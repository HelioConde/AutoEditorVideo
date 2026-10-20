# AutoEditor Studio — Shorts automáticos (primeiro MVP)

## Visão do produto

O objetivo central passa a ser **importar um vídeo, transcrever as falas, sugerir os melhores momentos e gerar Shorts verticais legendados**. O modo de edição manual permanece disponível para revisão.

### Fluxo inicial funcional no desktop

1. Importe uma gravação (limite atual de 512 MB, transcrição de até 10 min).
2. Use **Transcrever áudio** com Whisper.cpp local, ou importe um SRT correspondente ao vídeo.
3. Clique em **Encontrar melhores momentos**. O sistema organiza até três trechos não sobrepostos, com duração de 8 a 45 segundos.
4. Reveja título, trecho e motivo da seleção; escute o momento e, se desejar, use-o na timeline.
5. Clique em **Gerar Shorts legendados**. O backend cria arquivos **MP4 independentes em 9:16**, com SRT incorporado via FFmpeg/libass. Os resultados aparecem em Exportações, para download individual.

A detecção inicial é **heurística e transparente**, usando sinais no texto: perguntas, contraste, descobertas/resultados, frases de destaque, continuidade da fala e comprimento do trecho. A pontuação **não é probabilidade de viralização**. O sistema não entende emoções, imagens, humor nem reação do público.

## Módulos

- \`src/shorts-ranking.js\`: sugeridor determinístico, sem serviços pagos nem chamadas de rede.
- \`src/components/ShortsStudio.jsx\`: interface de descoberta, revisão e geração em lote.
- \`POST /api/projects/:id/shorts\`: geração local assíncrona de 1–3 MP4 verticais separados com legendas usando o renderizador já existente.

## Limitações e próximas fases

- O ranqueamento depende de transcrição SRT/Whisper e pode escolher momentos pouco interessantes. Rever antes de postar.
- 9:16 usa atualmente **corte central**; não há acompanhamento do rosto nem enquadramento inteligente.
- Legendas incorporadas são estáticas; animação palavra por palavra exige timestamps por palavra (o SRT atual não os contém).
- Para vídeos longos acima de 10 min, ampliar ingestão e transcrição em blocos com filas persistentes, recuperação e controle de CPU/disco.
- Evolução 2: diarização, detecção de mudanças de assunto, intensidade vocal, pausas, sinais visuais e modelo semântico local para ranking multimodal real, além de detecção de frases de gancho e finais completos.
- A versão web continua com limites de 30 MB/2 min e 20 s de saída, sem backend de transcrição; nesta rodada o modo automático está disponível **somente no desktop local**.

## Validação

- Testes unitários de pontuação e limites.
- Testes Playwright para criação do projeto, SRT e geração de Shorts.
- CI de build e QA desktop/web permanece obrigatório antes de integração.
