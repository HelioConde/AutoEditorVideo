# Fofinhos — Parte 1: contrato de narrativa e continuidade (04/11/2026)

**Nome oficial:** Fofinhos. **Episódio:** 01, Parte 1 — O Ovo Azul.
**Fonte de verdade:** conteudos/fofinhos-ep01-parte01-narracao-aprovada-v1.json.
**Status:** narração integral aprovada pelo criador; adaptação e renderização ainda pendentes.

## Por que o vídeo anterior estava incoerente

A versão anterior do projeto produzia **9 trechos** e mostrava o ovo sobre
um **caminho de jardim**. O roteiro revisado do criador contém **15 cenas**
e afirma explicitamente que o ovo está **entre flores coloridas**.
Nunca trocar a localização narrada por outra apenas por estética.

Os quatro shorts anteriores permanecem como histórico; a Parte 1 antiga
foi marcada como **obsoleta**, e a geração de novas vozes/frames ou
renderização desse rascunho é bloqueada. Não reusar narracao.mp3 antiga
como se fosse a voz aprovada.

## Mapa narrativo aprovado (15 cenas)

| Cena | Trecho/ação | Local e visual exigido |
| --- | --- | --- |
| 01 | Apresentação de Emanuelly | Jardim; apresentar Emanuelly, ainda sem mostrar ovo |
| 02 | Emanuelly brinca perto das flores | Jardim; flores coloridas realmente visíveis |
| 03 | Percebe algo diferente | Jardim; brilho vem do canteiro, não do caminho |
| 04 | Revelação do ovo azul e pergunta | Mesmo ovo azul, gotinhas na casca, entre flores; pausa de 1,0 s após pergunta |
| 05 | Curiosidade e decisão de descobrir | Olhar da menina orientado para ovo no canteiro |
| 06 | Aproximação gradual | Jardim; aproximar sem teletransportar o ovo; pausa de 0,8 s |
| 07 | Ovo azul brilhando entre as flores | Close comprovando que ovo está entre as flores, **fora da rua/caminho** |
| 08 | Ajoelha e estende a mão devagar | Mão e olhar apontam para o mesmo ovo |
| 09 | Ovo brilha mais | Brilho suave; mesmas flores e desenhos de gotinhas |
| 10 | Pega o ovo e leva para casa | O objeto sai do canteiro e fica apoiado nas mãos; sem levitação |
| 11 | Prepara caminha com manta e almofada | Interior do quarto oficial; caminha claramente macia |
| 12 | Promete cuidar | Emanuelly sorri olhando para ovo na caminha |
| 13 | Naquela noite, observa o ovo | Mesmo quarto em iluminação noturna; ovo intacto |
| 14 | Toc... toc... e ovo balança | Ovo balança na caminha sem rachar; pausa de 1,8 s |
| 15 | Quem será que estava lá dentro? | Close no mesmo ovo fechado; nenhum spoiler de Fofinho; continua na Parte 2 |

## Obrigações do editor/renderizador

1. **Narração:** preservar frases originais e pausas do JSON; usar sincronização
   com voz real. Não usar TTS antigo armazenado com outra assinatura.
2. **Cenário:** jardim-01 a 04 representam o MESMO jardim; quarto-01 a 04,
   o MESMO quarto. Um outro ângulo não pode mudar móveis, canteiros ou objetos.
3. **Posicionamento:** o compositor deve tratar o ovo como camada independente
   sobre o canteiro de flores. **Posição X/Y predefinida sem inspecionar o PNG
   não comprova onde estão as flores.** Antes de aprovar, olhar o frame renderizado.
4. **Olhar/gesto:** Emanuelly olha, se agacha e estende a mão na direção
   correta, sem mãos duplicadas, membros cortados ou objetos flutuando.
5. **Cronologia:** parte 1 sempre ovo inteiro; Fofinho nasce somente na
   Parte 2, cena 6. Não revelar Fofinha Arco-Íris, Fofinha Rosa ou outros.
6. **Tempo de vídeo:** a narrativa integral pode exceder o limite
   técnico atual de 60s, mas **isso precisa ser medido com TTS real**. Não
   cortar falas, acelerar voz ou eliminar pausas para caber. Se necessário,
   adaptar editorialmente para mais Shorts ou outro formato, preservando
   a pergunta e a resposta na cronologia correta.
7. **Aprovação:** cada cena deve ter conferência audiovisual humana,
   separada dos testes automatizados de alfa, geometria, hashes e validade.

## Comandos de auditoria após atualizar o GitHub

    cd "C:\Users\helio\Documents\arquivo-otaku-github"
    git pull --ff-only origin main
    python scripts\fofinhos_ep01_canon.py --acao revisar

O relatório demonstra por que a Parte 1 antiga não está pronta. Nenhum
comando desse documento gera imagens, consome créditos ou faz upload.

**Ainda falta implementar a nova adaptação e renderização das 15 cenas.**
Este commit registra a voz aprovada, o storyboard correto e impede
regressão para uma narração antiga. Não afirma que a localização das flores
já foi verificada em seus arquivos PNG locais.
