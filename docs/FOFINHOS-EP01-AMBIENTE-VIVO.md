# Fofinhos EP01 — Ambiente Vivo: borboletas, nuvens e magia discreta

**Objetivo:** deixar o jardim e o quarto vivos sem redesenhar os
cenários oficiais nem contradizer a narração aprovada de 15 cenas.

## O que este recurso faz

Esta implementação desenha formas **SVG animadas e leves** no Remotion:

- **Borboletas delicadas** com asas batendo nas laterais dos canteiros.
- **Nuvens translúcidas** se deslocando lentamente no alto do jardim.
- **Pétalas e pólen** em quantidades pequenas, acompanhando uma brisa suave.
- **Poeira de luz acolhedora** nas cenas diurnas do quarto.
- **Brilhos concentrados no ovo** em cenas mágicas ou de suspense.

As formas são renderizadas pelo código: **0 imagens GPT Image 2,
0 chamadas externas, 0 novas referências privadas e 0 uploads**.
Se o visual 2D não combinar com as imagens 3D aprovadas, preferir
gerar **apenas 1 atlas transparente de borboletas** numa evolução futura,
e não recriar os quatro ângulos do jardim.

## Onde cada efeito aparece

| Cenas | Local / objetivo | Animações |
| --- | --- | --- |
| 01–02 | Apresentação e brincadeira | 2 borboletas, nuvens lentas, poucas pétalas e pólen |
| 03 | Emanuelly percebe algo | 1 borboleta, ambiente desacelera |
| 04–08 | Encontrar e aproximar do ovo | Somente 1–3 brilhinhos próximos ao ovo |
| 09 | Ovo fica mais luminoso | 5 brilhinhos muito pequenos em volta do ovo |
| 10 | Emanuelly leva o ovo | 1 pétala e 2 grãos de pólen, sem competir com as mãos |
| 11–12 | Quarto e promessa | Poeira luminosa suave, sem borboletas |
| 13 | Começa a noite | Apenas 2 partículas noturnas e brilho discreto |
| 14 | Ovo balança | 4 brilhos próximos do ovo, clima de descoberta |
| 15 | Suspense | 3 brilhos, nenhum animal, sem mostrar o Fofinho |

**Os efeitos não alteram o cenário, a posição X/Y do ovo, as falas,
as poses ou a duração.** A regra do ovo *entre as flores e fora do
caminho* continua obrigatória e deve ser conferida no frame final.

## Arquitetura e proteções

- Código visual: motion-remotion/src/fofinhos-ambient-effects.tsx
- Integração: motion-remotion/src/emanuelly-short.tsx
- Plano por cena: scripts/fofinhos_ep01_render.py, AMBIENT_SCENES
- Testes: tests/test_fofinhos_ep01_render.py

O componente **só funciona no episódio canônico de Fofinhos**.
Os quatro Shorts antigos e o projeto Otaku não recebem esses efeitos.
A densidade tem limites por camada, as posições são deterministas
(sem Math.random ou temporizadores) e os elementos não interceptam cliques.

Os novos frames são gerados **em SVG**, sem PNGs adicionais.
Não existe rigging completo, oscilação real de cortinas nem vento 3D.
O fundo continua uma imagem fixa, com movimento ambiental por sobreposição.

Mudanças no perfil de ambiente alteram a assinatura do vídeo,
evitando reaproveitar um MP4 antigo como se já tivesse borboletas.
O relatório QA também indica que a **revisão visual humana** está pendente.

## Validar e renderizar no Windows

Antes de atualizar, preservar alterações locais (há arquivos modificados
no editor que não devem ser perdidos):

    git status --short
    git stash push -m "Backup local antes da ambientacao Fofinhos"
    git pull --ff-only origin main

Não usar reset --hard. Quando o projeto estiver atualizado:

    .\fofinhos-ep01.ps1 -Acao Planejar

Se faltarem cenas/poses ou o arquivo `canteiro-flores.json` não estiver
aprovado, **não forçar o render**. Para visualizar os canteiros:

    .\fofinhos-ep01.ps1 -Acao GuiaFlores
    .\fofinhos-ep01.ps1 -Acao Abrir

Quando o preflight estiver liberado:

    .\fofinhos-ep01.ps1 -Acao Renderizar -Refazer
    .\fofinhos-ep01.ps1 -Acao Abrir

A prévia local resultante será
`assets/gerados/fofinhos/ep01-parte01-canonico/previa-canonica.mp4`.
Ela **não será publicada automaticamente**. O vídeo anterior é arquivado
ao refazer, se já existir.

## Checklist de aprovação (olhar o MP4)

1. O ovo está **entre flores**, nunca no caminho/rua.
2. O olho e a mão da Emanuelly apontam ao ovo correto.
3. A borboleta não tapa rosto, mão, ovo ou legendas.
4. As nuvens não parecem manchas atravessando árvores e móveis.
5. A densidade do pólen não se assemelha a chuva ou sujeira.
6. A noite é calma e agradável; o ovo balança sem rachar.
7. Brilhos mágicos ficam perto do ovo e **não revelam o Fofinho**.
8. O vídeo não depende apenas de zoom — gestos e poses precisam de
   avaliação separada; o ambiente vivo não resolve rigging.

**Quando justificar novas imagens:** apenas se houver erro estrutural de
perspectiva, falta de floreiras úteis, pose incompatível com a mão,
ou incompatibilidade visual notável entre borboletas SVG e o estilo 3D.
Comece pelo menor recurso possível; não substitua jardim e quarto inteiros
sem necessidade.
