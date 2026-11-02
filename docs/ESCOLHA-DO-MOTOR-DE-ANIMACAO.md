# Auditoria dos motores do GitHub — 2026-11-01

**Escolha:** Remotion como renderizador **opcional**, sem remover a montagem
existente MoneyPrinterTurbo/FFmpeg.

| Projeto | Uso no Arquivo Otaku | Decisao |
| --- | --- | --- |
| [Remotion](https://github.com/remotion-dev/remotion) | Cena, camadas, zoom, movimento deterministico, voz, legenda, MP4 | Integracao experimental no repo |
| [Rigby2D](https://github.com/jaisurya-dev-art/rigby2d) | Ossos, IK, articulacao, piscadas | Fase 2: precisa PSD por partes |
| [Anime2.5DRig](https://github.com/852wa/Anime2.5DRig) | Puppet anime | Alternativa |
| [See-through](https://github.com/shitagaki-lab/see-through) | Separar imagem achatada em partes | GPU NVIDIA robusta; nao instalar na RX 580 |
| [DepthFlow](https://github.com/BrokenSource/DepthFlow) | Camera e parallax em fundos | Opcional; observar AGPL-3.0 |
| [ToonCrafter](https://github.com/Doubiiu/ToonCrafter) | Interpolar quadros de anime | VRAM demais para a RX 580 |

## Falhas observadas no teste 003-death-note-xadrez.mp4

O usuario enviou um MP4 de 31.37 segundos que tem verde residual proximo ao
pescoco e maos de Light, ao cabelo e maos de L. As pecas sao grandes e
sobrepostas ao tronco/mesa, deslocando-se de forma artificial.
Isso nao se resolve apenas trocando FFmpeg por Remotion: precisamos de
**PNG com alpha real** e ancoras de posicao.

## Por que alpha nativo vem antes do rig

O gerador antigo pedia fundo verde uniforme e tentava remove-lo com rembg.
O provedor oficial de imagens suporta \`background: transparent\` para modelos
compativeis; isso nao garante que o proxy de terceiros preserve o parametro.
A funcao \`request_image\` agora recebe os parametros opcionais e informa
quando o proxy os recusa. No motor Remotion, RGBs opacos e verde remanescente
sao bloqueados antes de renderizar.

Referencias:
- https://developers.openai.com/api/docs/guides/image-generation
- https://www.remotion.dev/docs/render
- https://rigby2d.com/docs/autorig.html

## Limites do MVP

Motor opcional: audio e legenda precisam existir no cache; nao gera novas
imagens nem roteiros, nao cria automaticamente rigs e nao faz upload.
A proxima fase sera integrar o gerador local de cinco Shorts ao novo motor
na mesma rotina, com QC audiovisual e selecao automatica do melhor render.
