# Emanuelly EP 01 — animação por camadas sobre cenários fixos

Este compositor é uma segunda opção para produzir a **Parte 1** da série.
Em vez de pedir ao GPT Image 2 nove imagens completas e diferentes,
ele reúne elementos que já foram gerados e avaliados pelo criador:

- quatro vistas do MESMO jardim (sem personagens, ovo, textos ou objetos novos);
- quatro vistas do MESMO quarto (decoração e arquitetura consistentes);
- UM ovo azul mágico em PNG verdadeiramente transparente;
- poses oficiais de Emanuelly, em PNG transparente;
- locução Kids PT-BR e música Kids já existentes no AutoEditorVideo.

**A primeira cena mostra somente o jardim e o ovo. Emanuelly não aparece.**
O jardim mantém sua identidade nas cenas 1–5; a mudança para o quarto
acontece na cena 6. O ovo é sempre o mesmo PNG: não nasce
outro personagem, não muda o desenho das gotinhas e não é
regenerado a cada cena. Nas cenas 8/9 ele balança e brilha
no quarto à noite. Fofinho, as gêmeas, Raposo e Porco-espinho
não aparecem nesta Parte 1.

## 1. Atualizar o projeto

    cd "C:\Users\helio\Documents\arquivo-otaku-github"
    git pull --ff-only origin main

Se a atualização ficar bloqueada por configurações locais do Git,
preserve e concilie as mudanças antes de executar o pull.
Não use git reset --hard nem git clean.

## 2. Criar pasta com as NOVE imagens oficiais

Salve as imagens que já geramos no computador, sem legendas nem personagens
embutidos nos cenários, com estes nomes EXATOS na pasta escolhida:

    C:\Users\helio\Pictures\Emanuelly\Referencias\
      jardim-01.png
      jardim-02.png
      jardim-03.png
      jardim-04.png
      quarto-01.png
      quarto-02.png
      quarto-03.png
      quarto-04.png
      ovo-azul.png

Os quatro jardins são ângulos diferentes de um mesmo local.
Os quatro quartos representam o mesmo quarto. Não use uma imagem
do ovo junto com cenário/personagem; o PNG do ovo precisa ter
transparência real. Não utilize uma imagem que contenha os
personagens futuros da história.

Instale as imagens numa operação:

    .\animar-emanuelly.ps1 -Acao InstalarLote -Pasta "$env:USERPROFILE\Pictures\Emanuelly\Referencias"

Ou instale os arquivos individualmente:

    .\animar-emanuelly.ps1 -Acao Instalar -Tipo Jardim -Indice 1 -Arquivo "C:\Imagens\jardim01.png"
    .\animar-emanuelly.ps1 -Acao Instalar -Tipo Quarto -Indice 1 -Arquivo "C:\Imagens\quarto01.png"
    .\animar-emanuelly.ps1 -Acao Instalar -Tipo Ovo -Arquivo "C:\Imagens\ovo-transparente.png"

Os nove recursos serão copiados para:

    assets\gerados\kids-emanuelly\cenarios-oficiais\

Cada um tem SHA-256 e metadados locais para impedir trocas silenciosas.
As imagens anteriores só podem ser substituídas com -Refazer, que
guarda o arquivo e metadados antigos em histórico.
Não são enviadas ao GitHub público.

## 3. Validar as poses e a narração

    .\animar-emanuelly.ps1 -Acao Planejar

O relatório deve exibir "ready": true. Se houver poses ausentes,
gere-as com o comando de poses já conhecido, por exemplo:

    .\gerar-poses-emanuelly.ps1 -Acao Gerar -Pose estendendo-mao -MaxChamadas 1

O compositor desta primeira parte requer somente as poses
caminhando, observando, estendendo-mao, segurando-ovo,
preparando-caminha e surpresa. Não exige as 54 poses de
histórias futuras.

A narração e música são reaproveitadas do gerador Kids anterior.
Se o relatório mostrar "narracao_original" ausente, execute:

    .\gerar-historia-kids.ps1 -Acao Voz -Parte 1

A voz não deve ser regenerada se já estiver aprovada.
Se faltar a música original, verifique o arquivo
Wondertrail _Main Theme_.mp3 na raiz do projeto.

## 4. Montar a prévia com animação

    .\animar-emanuelly.ps1 -Acao Preparar

    .\animar-emanuelly.ps1 -Acao Renderizar

    .\animar-emanuelly.ps1 -Acao Abrir

A saída será:

    assets\gerados\kids-emanuelly\
      kids-emanuelly-ep01-p01-ovo-azul\
        final-camadas.mp4
        qa-camadas.json

Não sobrescreve o MP4 anterior final.mp4, nem a voz ou a música.
Se modificar manualmente um cenário ou uma pose, o compositor detecta
o novo SHA e exige -Acao Renderizar -Refazer para guardar a prévia
antiga em histórico.

## 5. Como funcionam as animações

1. Jardim e quarto são camadas de fundo FIXAS.
2. Emanuelly entra caminhando com deslocamento lateral e movimento
   vertical discreto; cada beat usa uma pose adequada à ação.
3. O ovo é uma camada única que pode mudar posição, girar e balançar,
   sem mudar sua aparência.
4. Brilhos e purpurina são camadas vetoriais à parte.
5. A câmera não precisa dar zoom na imagem inteira para simular vida.
6. A locução e as pausas vêm dos tempos originais; a música Kids
   permanece baixa. O sistema verifica formato e limite de 60 segundos.

**Limitação de qualidade:** mover o PNG de Emanuelly não é a mesma coisa
que animar individualmente braços, boca, mãos ou cabelo com rigging.
As poses oferecem posturas diferentes e deslocamento independente,
mas movimentos plenamente articulados exigirão
keyframes adicionais/rigging. Verifique a sincronização do ovo
nas mãos, escala da Manu e continuidade das vistas no MP4.

## 6. Direitos e publicação

Este modo não solicita novas imagens de IA nem envia nada ao YouTube.
A publicação não é automática. As músicas Wondertrail ainda precisam
ter a licença de uso comercial/YouTube conferida antes da publicação.
Os arquivos de referência que contenham imagem de criança permanecem
somente no computador do criador.

Os testes Python e PowerShell usam imagens fictícias e não publicam nada.
A presença de PNGs e hashes não substitui a revisão visual completa.
