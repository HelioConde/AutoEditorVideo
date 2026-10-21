# Testes com mídia real — AutoEditor Studio

Três arquivos MP4 foram adicionados ao repositório em 21/10/2026:

- 15979800_1080_1920_30fps.mp4
- public/6767176-uhd_2560_1440_25fps.mp4
- public/VID-20250216-WA0003.mp4

O comando `npm run qa:media` verifica codecs, duração, proporções e presença de áudio com FFprobe; executa o analisador audiovisual real do projeto nos primeiros 12 segundos; converte uma amostra para Short vertical 360×640 e produz uma captura JPG.

O relatório `test-results/real-media/report.json`, as capturas e os MP4 curtos são publicados no artefato `real-media-qa` do GitHub Actions.

**Limites:** reconhecer cortes de cena e energia de áudio não equivale a entender acontecimentos marcantes. Se não houver fala, o ranking semântico existente não gera candidatos automaticamente e precisamos adicionar um detector visual independente. Não inventar legendas para os testes.

Observação: um arquivo dentro de `public/` pode ser copiado para o build web, aumentando o artefato de publicação mesmo quando nenhum componente o utiliza.

## Resultados iniciais dos dois primeiros vídeos

- O arquivo `15979800_1080_1920_30fps.mp4` foi lido como vídeo vertical H.264, 1080×1920, 28,23 s, **sem faixa de áudio**, sem mudança de cena nos primeiros 12 s.
- O arquivo `public/6767176-uhd_2560_1440_25fps.mp4` foi lido como vídeo horizontal H.264, 2560×1440, 13,57 s, com uma faixa AAC cujo áudio é praticamente silencioso (volume médio medido em aproximadamente −91 dB), sem mudanças de cena nos primeiros 12 s.
- O terceiro vídeo será caracterizado automaticamente no próximo job do GitHub Actions, sem presumir falas, conteúdo ou presença de eventos.

Uma cena contínua pode conter ação relevante mesmo com zero mudanças de cena; esse conjunto motiva um módulo de detecção de movimento/acontecimentos independente da transcrição.
