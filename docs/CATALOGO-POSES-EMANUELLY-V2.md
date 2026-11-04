# Emanuelly — catálogo de poses v2 (Kids / animação por camadas)

Biblioteca de **54 poses independentes** para o episódio do ovo azul e histórias futuras.
Mantemos sem qualquer mudança **8 poses já existentes e seus hashes de cache**;
acrescentamos **46 ações** ao mesmo gerador PowerShell.

Cada pose deve conter somente Emanuelly, PNG transparente 1024×1536.
O ovo azul, Fofinho, flores, objetos, casa e jardim são camadas SEPARADAS.
Nunca renderizar personagens futuros dentro do PNG de Emanuelly. Em cenas,
o Fofinho só aparece após o nascimento no roteiro. A referência privada
fica em assets/referencias-privadas/emanuelly-personagem-oficial.png.

## Primeiro executar no PowerShell

    cd "C:\Users\helio\Documents\arquivo-otaku-github"
    git pull --ff-only origin main

    # Exibir TODAS as categorias e sequências, sem chamar o modelo
    .\gerar-poses-emanuelly.ps1 -Acao Catalogo

    # Conferir as oito poses já geradas (cache intacto)
    .\gerar-poses-emanuelly.ps1 -Acao Verificar -Grupo Essenciais

    # Planejar poses do primeiro episódio (16 no total, oito adicionais)
    .\gerar-poses-emanuelly.ps1 -Acao Planejar -Grupo Ep01

    # Gerar somente duas poses ainda ausentes, com teto de 2 chamadas
    .\gerar-poses-emanuelly.ps1 -Acao Gerar -Grupo Ep01 -Quantidade 2 -MaxChamadas 2

    # Uma pose específica para cenas com Fofinho futuramente
    .\gerar-poses-emanuelly.ps1 -Acao Gerar -Pose fazendo-carinho -MaxChamadas 1

    # Verificar quantas poses de carinho precisam ser geradas
    .\gerar-poses-emanuelly.ps1 -Acao Planejar -Grupo Carinho

    # Produzir um pequeno lote de carinho
    .\gerar-poses-emanuelly.ps1 -Acao Gerar -Grupo Carinho -Quantidade 3 -MaxChamadas 3

    # Somente inventariar a biblioteca completa
    .\gerar-poses-emanuelly.ps1 -Acao Planejar -Grupo Todas

    # Abrir a pasta dos PNGs no Windows
    .\gerar-poses-emanuelly.ps1 -Acao Abrir

O grupo padrão é Essenciais, preservando o significado do antigo
comando sem -Grupo. -Pose escolhe uma pose específica e prevalece
sobre -Grupo. -Quantidade N no modo Gerar seleciona as próximas N
poses **pendentes**, sem cobrar por imagens em cache; -MaxChamadas N
é um TETO de chamadas GPT Image 2, não uma meta de consumo.

Para refazer somente uma pose ruim:

    .\gerar-poses-emanuelly.ps1 -Acao Gerar -Pose fazendo-carinho -MaxChamadas 1 -Refazer

A versão anterior é arquivada no histórico.

## Categorias e quantidade

| Grupo | Total | Ações |
|---|---:|---|
| Essenciais | 8 | Em pé, caminhar, observar, ajoelhar, estender a mão, segurar ovo invisível, preparar caminha, surpresa |
| Ep01 | 16 | Essenciais + brincar no jardim, abaixar, pegar ovo, caminhar com ovo, colocar ovo, olhar ovo, escutar ovo, prometer cuidar |
| Carinho | 8 | Fazer carinho, acariciar cabeça, abraçar pelúcia invisível, abraço lateral, beijinho, consolar, ninar, sentar com carinho |
| Emocoes | 8 | Sorrir, rir, curiosidade, encanto, preocupação, alívio, tristeza leve, bocejar |
| Movimento | 8 | Correr, passo lateral, virar, agachar, levantar, pular, sentar, levantar do chão |
| Brincadeiras | 6 | Palmas, dançar, apontar, soprar bolha, esconde-esconde, comemorar |
| Cotidiano | 8 | Dormir, acordar, ler, regar planta, cuidar flores, abrir porta, oferecer, escutar |
| Futuras | 38 | Todos os cinco grupos futuros, sem repetir as essenciais |
| Todas | 54 | Biblioteca completa, com poses únicas |

## Continuidade e futura animação

O catálogo registra sugestões de sequências:
- encontrar-ovo: brincar, observar, se aproximar, ajoelhar, pegar e levar
- acolher-ovo: preparar cama, colocar ovo, cuidar e escutar
- carinho-fofinho: sentar, fazer carinho, abraçar, beijar e ninar
- brincadeira: andar, correr, pular, bater palmas e dançar

As poses são PERSONAGEM ISOLADA, não renders de cena. Uma pose
de acariciar coloca a mão na posição adequada para um amigo
INVISÍVEL; o compositor depois posicionará o Fofinho como camada
separada. Dessa forma não existe spoiler de personagens futuros
nem mudança involuntária de jardim/casa/ovo.

**Limitação:** metadados e PNGs de poses não equivalem a animação
articulada. Para movimentos fluidos entre imagens, será necessário
implementar keyframes/rigging e transições independentes de zoom
no renderizador. A identidade facial continua exigindo revisão visual.

## Privacidade, custos e qualidade

A IA de edição recebe a imagem privada somente na ação Gerar e
pode encaminhá-la ao provedor configurado no Codex Proxy.
O modelo permitido é exclusivamente gpt-image-2.
O sistema gera PNG com transparência real, salva o bruto da resposta
paga antes de validar, preserva histórico de versões antigas e
impede chamadas acima de MaxChamadas.

Se a imagem inicial foi produzida com membros cortados, o
reenquadramento local não recupera as partes ausentes.
Nenhuma ação desta biblioteca cria vídeo, publica ou faz
login no YouTube. Testes em CI usam respostas simuladas e não enviam
referências reais para serviços externos.
