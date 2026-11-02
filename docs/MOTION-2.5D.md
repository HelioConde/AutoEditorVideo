# Primeira prova do compositor 2.5D

Esta etapa usa um fundo estatico e **um personagem PNG com transparencia real**
(e opcionalmente um objeto PNG com transparencia). A animacao por FFmpeg realiza
movimentos independentes por camada. Nenhuma chamada de IA ou upload e feita.

## Executar no Windows

Instale Pillow e FFmpeg; depois rode a partir da raiz do repositorio:

```powershell
.\.venv\Scripts\python.exe .\scripts\motion_layers.py --fundo ".\assets\gerados\quarto.jpg" --personagem ".\assets\gerados\light.png" --objeto ".\assets\gerados\caderno.png" --segundos 5 --saida ".\assets\gerados\teste-camadas.mp4"
```

Sem arquivo de voz, o resultado e um **clipe mudo** para usar na montagem.
Se informar `--audio`, o clipe inclui trilha de audio. O resultado
ainda nao tem legendas e nao e uma montagem automatica de 25 videos.
O programa recusa PNG opaco ou com alpha todo zerado para evitar ilusao de transparencia.

## Cenas futuras

Separar cada cena em `background`, `personagem`,
`objeto`, `duracao` e `efeito`, sincronizando
depois com legendas SRT. O passo seguinte sera conectar o gerador de assets
ao renderizador atual e reaproveitar a biblioteca de personagens.

**Observacao:** um PNG que parece transparente mas tem pixels pretos ou brancos
no fundo nao tem alpha real. Solicitar saida PNG transparente do provedor e, se
nao houver suporte, fazer recorte local e revisar as bordas.
