# Arquivo Otaku v0.7 — Pesquisa e melhorias do pipeline

Data da pesquisa: 2026-11-01. Fontes externas trazem **dados públicos**, nao acesso a estatisticas privadas de retencao dos canais.

## 1. Canais estudados
- **Locomotiva Pop**: https://www.youtube.com/@Locomotivapop/shorts — 1,04 milhão de inscritos e 48 Shorts recentes com duracao mediana de 1:00; titulos sobre curiosidades, entretenimento e polemicas. Dados: https://vidiq.com/youtube-stats/channel/@locomotivapop/videos/ (referencia 2026-10-31).
- **Time Trends**: https://www.youtube.com/@TimeTrends/shorts — 1,43 milhão de inscritos e 48 Shorts recentes com duracao mediana de 1:02; anime, curiosidades, comparativos e informacoes de fandom. Dados: https://vidiq.com/youtube-stats/channel/@timetrends/videos/ (referencia 2026-10-31).

**Limite importante:** Titulos, videos listados, datas e visualizacoes sao comprovados pelas paginas publicas. Velocidade de cortes, entonacao, mixagem e legendas dos criadores nao foram medidos diretamente. Os ajustes abaixo sao estrategias propostas para o Arquivo Otaku, nao copias dos criadores.

## 2. Mudancas implementadas
- `scripts/planejador_editorial.py`: diagnostica a estrutura do roteiro, ganchos, encerramento e duracao estimada sem consultar IA ou inventar noticias.
- `scripts/editor_shorts.py`: gera dois recortes diferentes de cada cena 9:16 para aumentar ritmo sem perder formato vertical, com manifesto em JSON e cache. Sao **recortes da mesma imagem**, nao cenas novas.
- `scripts/gerar_video_codex.py`: utiliza 3 segundos por plano, 14 planos para as 7 cenas, fonte maior e contorno mais forte, 72% da tela e uma leve aceleracao de locucao.
- `scripts/finalizador_audio.py`: tenta normalizar áudio para -16 LUFS (TP -1,5 dB) usando FFmpeg; se falhar, preserva o MP4 sem alterações.
- `conteudos/001-death-note-direcao.json`: gancho mais direto, contraste Light vs L e resposta concreta no final.
- `planejar-episodio.ps1`: valida novo roteiro antes de gerar imagens.
- Preservado: cache de IA, qualidade de luz, reutilizacao sem acesso ao proxy, uso de MPT e upload separado para evitar duplicacoes.

## 3. O que avaliar ao assistir a v0.7
- Se o gancho apresenta a promessa ja no primeiro segundo.
- Se duas variacoes do mesmo desenho parecem repetitivas; se sim, futuras versoes devem gerar mais imagens originais.
- Se o tamanho das legendas cabe em uma linha e nao cobre rostos nem o titulo.
- Se a duracao final da narracao cabe no total de material (14 x 3 = 42s); se for maior, gere mais planos ou reduza o roteiro, **nao acelere excessivamente a voz**.
- Se pausa entre frases parece natural. O TTS nao foi modificado diretamente para corte de pausas.
- Checar dados do Studio: escolheu assistir, porcentagem media visualizada, duracao media e comentarios.
- Para videos de noticias reais, fontes confiaveis sao obrigatorias: ganchos nao devem afirmar vazamentos ou anuncios nao verificados.

## 4. Monetizacao e direitos
O YouTube aceita uso criativo de IA, mas exige contribuicao original e desencoraja series massificadas de slides quase identicos. Ver: https://support.google.com/youtube/blog/356734251/response-to-creator-questions-about-ypp-policies-july-2025

Nao pressupor que ilustracoes de personagens licenciados estejam automaticamente liberadas para uso comercial. Revisar direitos, e quando necessario usar design original do proprio canal.

## 5. Executar
```powershell
.\planejar-episodio.ps1
.\gerar-video-codex.ps1 -SomenteConfigurar
.\gerar-video-codex.ps1 -ReutilizarImagens
```

**A execucao nao publica automaticamente.** So publica mediante comando separado de upload.

## 6. Miniatura e título para esta nova versão
O `publicar-youtube.ps1` preserva os metadados anteriores, por segurança. Para preparar
uma nova miniatura e o novo título do plano **sem publicar**, execute:
```powershell
.\publicar-youtube.ps1 -Etapa preparar -Video ".\assets\gerados\arquivo-otaku-piloto-v07-reuso.mp4" -Episodio ".\conteudos\001-death-note-direcao.json" -Refazer
```
Verifique manualmente `assets\gerados\publicacao-youtube\metadata.json`.
A publicação continua uma etapa independente, e nao é executada por esse comando.
