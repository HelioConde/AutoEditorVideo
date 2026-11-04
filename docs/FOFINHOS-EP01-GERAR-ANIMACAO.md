# Fofinhos — gerar a nova animação do EP01 com a narração aprovada

Esta é a **Parte 1: O Ovo Azul**, a história de 15 cenas aprovada em
`conteudos/fofinhos-ep01-parte01-narracao-aprovada-v1.json`.
O antigo arquivo de 9 cenas NÃO É o roteiro aprovado.

## Por que os comandos antigos foram bloqueados?

- A voz anterior tinha 9 cenas, incompatíveis com as 15 cenas aprovadas.
- O Remotion anterior limitava o vídeo a 60 segundos.
- O ovo estava posicionado por coordenadas fixas que não conferiam com a
  localização das flores no cenário real.
- O argumento `-MaxChamadas X` era apenas um exemplo:
  o PowerShell exige **número inteiro**, não a letra X.

O novo fluxo reutiliza o modelo visual oficial, preserva o material antigo
e fornece uma **prévia vertical completa** (não necessariamente um Short).
Só a geração de áudio faz chamadas TTS; **zero novas chamadas GPT Image 2**.

## 1. Atualizar e conferir

No Windows, salve primeiro suas alterações locais no Git, se existirem;
não use reset --hard nem clean -fd.

    cd "C:\Users\helio\Documents\arquivo-otaku-github"
    git status
    git pull --ff-only origin main
    .\fofinhos-ep01.ps1 -Acao Planejar

A lista `visual_assets_missing` mostra cenários, poses e o objeto
`caminha-ovo` que ainda não estão válidos. **Não gaste chamadas de imagem
em poses já prontas**.

## 2. Gerar a narração aprovada

    .\fofinhos-ep01.ps1 -Acao Voz

Também funciona o comando histórico:

    .\gerar-historia-kids.ps1 -Acao Voz -Parte 1

O MP3 fica separado do antigo, em

    assets\gerados\fofinhos\ep01-parte01-canonico\narracao-canonica.mp3

O áudio contém **todas as 15 cenas** e as pausas explícitas 1,0, 0,8
e 1,8 segundos. Não acelera ou corta a narração para forçar 60 segundos.
Se passar de 59,2 s, a saída será **prévia de vídeo longo**, NÃO será
classificada automaticamente como YouTube Short. O TTS pode exigir internet.

## 3. Marcar onde estão as flores (obrigatório)

    .\fofinhos-ep01.ps1 -Acao GuiaFlores
    .\fofinhos-ep01.ps1 -Acao Abrir

O sistema abre a pasta de guias. Veja
`jardim-03-grade.png` e `jardim-04-grade.png`: cada um exibe uma grade
de coordenadas normalizadas de 0 a 1.

Abra o arquivo:

    assets\gerados\fofinhos\ep01-parte01-canonico\canteiro-flores.json

As coordenadas estão inicialmente nulas. Substitua por valores OBSERVADOS
nos PNGs da sua máquina, por exemplo:

    "angles": {
      "jardim-03": {
        "x": 0.30,
        "y": 0.70,
        "aprovado_visual": true,
        "background_sha256": "... MANTER O VALOR JA GERADO ..."
      },
      "jardim-04": {
        "x": 0.67,
        "y": 0.59,
        "aprovado_visual": true,
        "background_sha256": "... MANTER O VALOR JA GERADO ..."
      }
    }

**Os números acima são meramente ilustrativos e NÃO devem ser copiados sem
examinar o jardim real.** Mantenha o `background_sha256` que o programa
registrou automaticamente. Escolha X/Y em uma área de canteiro florido
**fora do caminho**, confira a prévia e marque aprovado_visual=true
somente quando o ponto estiver correto.

Rode `-Acao GuiaFlores` de novo para visualizar o ponto azul sobre
o canteiro no PNG. O render exige aprovação para jardim-03 e jardim-04,
e invalida a aprovação se a imagem-base mudar.

## 4. Gerar recursos ausentes somente se o planejamento pedir

Gerar **um recurso derivado** (usa gpt-image-2, até 1 chamada, pode haver
custo de imagem, usando a referência privada existente):

    .\animar-emanuelly.ps1 -Acao GerarImagens -Parte 1 -Recurso caminha-ovo -MaxChamadas 1

Se `visual_assets_missing` indicar uma pose, gere aquela pose separadamente:

    .\gerar-poses-emanuelly.ps1 -Acao Gerar -Pose encantada -MaxChamadas 1

Repita apenas para nomes efetivamente pendentes. A referência privada pode
ser enviada ao Codex Proxy/provedor ao autorizar geração de imagem.
O novo motor não gera imagens por conta própria.

## 5. Renderizar a prévia completa para inspeção

    .\fofinhos-ep01.ps1 -Acao Planejar
    .\fofinhos-ep01.ps1 -Acao Renderizar
    .\fofinhos-ep01.ps1 -Acao Abrir

Também funciona o comando histórico:

    .\animar-emanuelly.ps1 -Acao Renderizar -Parte 1

O vídeo é salvo em:

    assets\gerados\fofinhos\ep01-parte01-canonico\previa-canonica.mp4

O render usa os backgrounds fixos e camadas independentes para Emanuelly,
ovo e caminha. Há animações de **movimento de sprites** (caminhar,
aproximar, levantar o ovo, balanço e luzes), mas **não há rigging completo
de braços, pernas e expressões**. Validar o resultado e ajustar
composições se as interações ainda parecerem artificiais.

## Segurança e limites

- Zero publicação automática no YouTube; a marca e todo elenco permanecem
  protegidos por continuidade editorial.
- A prévia nova não substitui o arquivo antigo `final-camadas.mp4`.
- Voz e vídeo passam por cache com hash do conteúdo e preservam histórico
  quando `-Refazer` é usado.
- A posição do ovo deve ser revisada no vídeo final, não só no PNG com grade.
- A presença de coordenadas aprovadas não prova automaticamente que o ovo
  está nas flores: a aprovação final continua humana.
- A música de fundo, se presente, mantém revisão de direitos pendente.
- O novo episódio é uma prévia longa; qualquer divisão em Shorts deverá
  respeitar a fala completa, as pausas e a continuidade.
