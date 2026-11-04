# Emanuelly — 8 poses transparentes com GPT Image 2

O objetivo é usar a mesma Emanuelly das referências aprovadas em diferentes ações de animação por camadas, sem inventar uma menina diferente a cada quadro.

Este script gera oito PNGs independentes e transparentes, sem fundo, jardim, quarto, ovo ou outros personagens. Cada pose recebe o mesmo PNG de referência real por uma chamada à API de edição de imagens gpt-image-2. Não faz upload para o YouTube, não altera MP4s, música, narração ou cenários já produzidos.

## Instalar a referência privada

A referência enviada na conversa deve ser copiada ou extraída para:

    assets\referencias-privadas\emanuelly-personagem-oficial.png

Essa pasta é ignorada pelo Git. A imagem não deve ser enviada ao GitHub público.

O ZIP privado disponibilizado na conversa possui a estrutura correta. Após baixar para Downloads:

    cd "C:\Users\helio\Documents\arquivo-otaku-github"
    git pull --ff-only origin main
    Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\referencia_emanuelly_poses_privada.zip" -DestinationPath (Get-Location)

Alternativa para instalar uma imagem diretamente:

    .\gerar-poses-emanuelly.ps1 -Acao InstalarReferencia -Referencia "C:\Users\helio\Downloads\referencia.png"

Se já existir uma referência diferente, o instalador protege a anterior. Use -Refazer na instalação para substituí-la com backup.

A referência é enviada à API de imagens SOMENTE na ação Gerar; o Codex Proxy local pode encaminhá-la a um serviço externo, conforme sua configuração. Execute apenas se autorizar esse envio.

## Comandos de produção

    # Ver o plano; zero chamadas de IA
    .\gerar-poses-emanuelly.ps1 -Acao Planejar

    # Gerar a primeira pose de teste com uma chamada GPT Image 2
    .\gerar-poses-emanuelly.ps1 -Acao Gerar -Pose em-pe -MaxChamadas 1

    # Se a primeira pose tiver a aparência correta, gerar as outras sete
    .\gerar-poses-emanuelly.ps1 -Acao Gerar -Pose Todas -MaxChamadas 7

    # Ou gerar todas as oito do zero com orçamento explícito
    .\gerar-poses-emanuelly.ps1 -Acao Gerar -Pose Todas -MaxChamadas 8

    # Conferir os arquivos e abrir a pasta
    .\gerar-poses-emanuelly.ps1 -Acao Verificar
    .\gerar-poses-emanuelly.ps1 -Acao Abrir

Para refazer apenas a pose ajoelhada sem destruir o arquivo anterior:

    .\gerar-poses-emanuelly.ps1 -Acao Gerar -Pose ajoelhada -MaxChamadas 1 -Refazer

As oito poses são: em-pe, caminhando, observando, ajoelhada, estendendo-mao, segurando-ovo (mãos em concha mas sem ovo desenhado), preparando-caminha (sem objetos) e surpresa.

## Correção — personagem perto da borda (pose caminhando)

Se o GPT Image 2 desenhar Emanuelly perto demais de uma borda,
o sistema tenta **reenquadrar o mesmo PNG localmente**, ajustando
escala e margens sem criar outra imagem ou consumir outra chamada.
As cores, roupa, cabelo e rosto da fonte permanecem inalterados.
O prompt também reserva espaço à esquerda, direita, em cima e embaixo.

**Importante:** redimensionar uma imagem não reconstrói
um braço, mão ou pé que o modelo já tenha desenhado cortado.
Quando a silhueta do PNG original tocar a borda, o arquivo será marcado
`source_may_already_be_cropped=true` para revisão visual, mesmo quando
o reenquadramento técnico funcionar. Não publicar nem incorporar
automaticamente uma pose visualmente incompleta.

Para impedir perda de respostas pagas, cada PNG bruto retornado pelo
modelo agora é salvo **antes da validação** em `poses/brutos/`
com SHA-256 e assinatura da referência. Se uma etapa local falhar,
o mesmo arquivo poderá ser recuperado na execução seguinte
sem outra chamada de IA. O comando Planejar mostra
`bruto_recuperavel_sem_ia` quando for possível.

A versão anterior NÃO salvou a saída reprovada de `caminhando`.
Portanto, para essa falha específica do programa antigo será
necessária uma chamada nova; futuras reprovações conservarão
a resposta bruta.

Após atualizar o GitHub, execute:

    .\gerar-poses-emanuelly.ps1 -Acao Planejar

Caso somente `em-pe` esteja aprovada, o plano deve indicar
**sete chamadas** para terminar as oito poses:

    .\gerar-poses-emanuelly.ps1 -Acao Gerar -Pose Todas -MaxChamadas 7

A pose `em-pe` já gerada é preservada com sua assinatura antiga.
Não use `-Refazer` para essa retomada normal: refazer
significa pedir novas gerações, e pode consumir as oito chamadas.

## Arquivos gerados

    assets\gerados\kids-emanuelly\biblioteca-personagens\emanuelly\poses\
      emanuelly-em-pe.png
      emanuelly-em-pe.json
      emanuelly-caminhando.png
      emanuelly-caminhando.json
      ...
      historico\

São PNGs 1024x1536 RGBA de transparência real. O ovo, jardim e quarto ficam separados e podem ser sobrepostos em outras cenas. A pose não é uma colagem com oito personagens.

O sistema exige a referência real, modelo gpt-image-2 e limite máximo de chamadas definido pelo usuário. Não aceita imagem sem alfa, fundo opaco ou corpo cortado perto das bordas. Cada resultado recebe SHA-256, registro da referência, modelo, pose e marcação pending_visual_review. Se a identidade visual ficar diferente, refazer somente a pose reprovada. IA de imagem não garante que o rosto fique idêntico.

A montagem automática dessas poses com o jardim/quarto oficiais e a animação independente das partes do corpo são etapas posteriores; este comando prepara a biblioteca de assets e não produz um vídeo novo por conta própria.

## Dependências e segurança

O Windows deve possuir Python com Pillow, NumPy e requests e um Codex Proxy funcionando com /v1/images/edits em gpt-image-2, incluindo background=transparent. Se o proxy não aceitar transparência, o processo é bloqueado sem criar figura falsa. Os pedidos podem consumir cotas/créditos.

Não se usa gpt-image-1.5, nem text-to-image sem referência e nem upload automático. Os testes do projeto usam um editor de imagens simulado: nenhuma foto pessoal é enviada durante a CI.
