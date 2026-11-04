# Otaku Reframe V3 — adaptar Shorts BR ja publicados para ingles

## Resultado da auditoria (4 de novembro de 2026)

Canal brasileiro: [Otaku Multicena](https://www.youtube.com/@otakumulticena)
ID BR: UCXGYTuBYn-0Ziqin5ajKhOw

Canal ingles: [Otaku Reframe](https://www.youtube.com/@otakureframe)
ID EN: UCBoNbQjaMYdpJqPLRZAFkvQ

A consulta do vidIQ ao canal BR confirmou **18 Shorts publicos**. No canal EN,
foram encontrados **2 Shorts publicos**:
- EP01 (ID EN tPurNjxbnx0); a adaptacao do 101-death-note-ep01 NAO sera reenviada.
- Curiosidade sobre nome e rosto (ID EN gZt7V7L5L9c, episodio 201-death-note-rosto-nome).
  Nao inferir qual outro Short BR corresponde ao 201 sem verificar origem.

Os 18 Shorts BR foram divididos em:
- **13 com episodio-fonte do repositorio identificado por assunto e titulo**:
  003, 004, 005, 006, 007, 102, 103, 202, 401 e 5001..5004.
- **1 cuja adaptacao EN ja existe**: 101.
- **4 que exigem identificar qual storyboard local foi realmente usado**:
  m28-KzLSh1k, zwyLeTzeCn4, mP34eFfMIRI e VfliGg3N4rU.

Este mapeamento compara titulos publicos e catalogos. A validacao final das
*mesmas imagens efetivamente enviadas* exige os caches e registros do computador
local. Nenhum dos 13 e marcado automaticamente como MP4 pronto.

Arquivo da auditoria: conteudos/otaku-br-publicados-snapshot-20261104.json
Arquivo editorial EN: conteudos/otaku-br-publicados-en-curadoria-v3.json

## O que muda no Otaku Reframe

Nao e apenas trocar o audio PT por voz inglesa. Para cada Short:
1. Redigir um roteiro ingles original, preservando a historia e os fatos.
2. Preparar cinco opcoes de gancho; o roteiro final comeca no gancho escolhido.
3. Criar titulo/descricao/tags adequados ao publico internacional.
4. Reutilizar as imagens PT APENAS quando elas combinam com a nova narracao e
   nao exibem texto em portugues gravado no proprio desenho.
5. Narração EN en-US-GuyNeural e legendas EN com tempos da voz.
6. Renderizacao Remotion local 9:16, ate 60 segundos, com QA por checksum.
7. Conferir pronuncia, movimentos, legibilidade, direitos e originalidade.
8. Preparar upload para o canal EN, **private por padrao**, somente mediante
   autorizacao explicita. Verificar o video completo no Studio antes de tornar publico.

**Cenas que so dao zoom nao devem ser apresentadas como animacao real do personagem.**
O projeto ainda nao garante rigging de membros ou animacao facial sofisticada;
as melhorias cinematograficas seguem como prioridade separada.

## Atualizar o projeto local

No PowerShell:

    cd "C:\Users\helio\Documents\arquivo-otaku-github"
    git pull --ff-only origin main

## 1. Preparar a fila SEM IA, MP4 ou upload

    .\preparar-publicados-en.ps1 -Acao Resumo
    .\preparar-publicados-en.ps1 -Acao Verificar
    .\preparar-publicados-en.ps1 -Acao Preparar

O manifesto preparado fica fora do Git:

    assets\gerados\otaku-br-publicados-en-v3.json

Para preparar so Black Clover:

    .\preparar-publicados-en.ps1 -Acao Preparar -Id 5001-black-clover -Saida assets\gerados\black-clover-en-v3.json

O comando nao sobrescreve imagens PT, nao usa proxy de IA e nao mexe em OAuth.
A opcao Verificar informa se existe storyboard PT pinado ou plano de origem,
mas nao declara que cenas e MP4 ja foram aprovados.

## 2. Produzir ingles SEM enviar para YouTube

Usar o manifesto completo ou um manifesto de um episodio gerado pelo passo 1.

    $manifesto="assets\gerados\otaku-br-publicados-en-v3.json"

    # Planejamento e metadados EN sem gerar IA
    .\gerar-shorts-en.ps1 -Acao planejar -Manifesto $manifesto -Id 5001-black-clover

    # Gerar voz inglesa e novas legendas, preservando a voz PT
    .\gerar-shorts-en.ps1 -Acao voz -Manifesto $manifesto -Id 5001-black-clover

    # Renderizar APENAS se os assets PT aprovados existirem
    .\gerar-shorts-en.ps1 -Acao renderizar -Manifesto $manifesto -Id 5001-black-clover

    # Modo estrito: reprovar cenas com personagem cuja unica atividade e o zoom
    .\gerar-shorts-en.ps1 -Acao renderizar -Manifesto $manifesto -Id 5001-black-clover -ExigirMovimentoPersonagem

O QA EN passou a registrar quantas cenas possuem capacidade de movimento de
camadas de personagem, quantas sao camera-only e seus IDs. O sinalizador
-ExigirMovimentoPersonagem so aprova cenas de personagem com camada movel,
mas nao substitui avaliacao de gestos/rigging; se os assets PT nao tiverem
camadas adequadas, o render sera bloqueado com explicacao clara.
A verificacao estrita tambem considera o QA de um MP4 em cache.

O cache EN fica em assets/gerados/shorts-animados/<ID>/en-US/ com arquivo
MP4, narracao, legendas, metadata-en.json e qa-en-US.json.

No modo de reaproveitamento, nao gerar imagens novas apenas para cumprir um
numero de cenas. Se faltar cache PT, retornar erro e diagnosticar localmente.
Capa com texto em ingles nao remove texto portugues ja incorporado a outras
imagens; conferi-lo no video final.

Se um roteiro PT for alterado apos a curadoria EN, o sistema bloqueia o
manifesto gerado ate que o par PT/EN seja revalidado. O cache EN assinado
deve corresponder a origem BR real e ao roteiro ingles atual.

## 3. Verificar upload sem executar envio

    .\publicar-shorts-en.ps1 -Acao verificar -Manifesto $manifesto -Id 5001-black-clover

O publicador recusa MP4 incompleto, assinatura QA divergente, idioma incorreto
e fonte BR diferente da fonte inscrita no manifesto. O canal EN e fixado no ID
UCBoNbQjaMYdpJqPLRZAFkvQ; a conta OAuth precisa corresponder exatamente.
O token PT nao e utilizado.

O modo Verificar nao pede OAuth nem faz upload.

## 4. Envio privado — somente sob nova autorizacao

**Os comandos a seguir documentam o fluxo; NAO foram executados nesta tarefa.**

Primeiro, configure o ID real no computador local, se ainda nao estiver pronto:

    New-Item -ItemType Directory -Force .secrets | Out-Null
    Set-Content -Path .secrets\youtube-en-channel-id.txt -Encoding ASCII -Value "UCBoNbQjaMYdpJqPLRZAFkvQ"

Depois da revisao completa do MP4 e autorizacao de envio:

    .\publicar-shorts-en.ps1 -Acao conectar -Manifesto $manifesto
    .\publicar-shorts-en.ps1 -Acao enviar -Manifesto $manifesto -Id 5001-black-clover -Privacidade private -ConfirmarEnvio

O uploader usa estado e token separados da conta PT, SHA-256 e protecao contra
segundo envio do mesmo episodio. Para tornar publico depois da aprovacao
artistica, utilizar o YouTube Studio; nao reenviar o MP4 para mudar privacidade.

**Nao use** -Privacidade public antes da revisao. O aplicativo atual permite
publico apenas por opt-in explicito; esta fase nao aciona esse modo.

## 5. Calendario internacional de teste

Piloto inicial (proposta, sem agendamento automatico):
- Dia 1: adaptar e inspecionar 003 (xadrez Light vs L), um tema ja conhecido.
- Dia 2: adaptar e inspecionar 005 (justica de Kira).
- Dia 3: testar Maomao, que se destacou no BR.
- Dia 4: testar Black Clover.
- Dias seguintes: avaliar 40 segundos, Cyberpunk e Steel Ball Run.

Esse cronograma NAO pressupoe um limite de 3 Shorts recomendados/dia. Fazer
experimentos com cadencia pequena e medir exibicoes de feed, escolheram
assistir, views intencionais, retencao, compartilhamentos e inscritos em
janelas 1/6/24/72/168h. Dado ausente permanece nulo.

Nao reutilizar automaticamente o horario brasileiro: considerar o publico
internacional e dados do canal EN. Nao alterar videos ou agendamentos existentes.

## 6. Testes e limitacoes

    .\.venv\Scripts\python.exe -m pytest -q tests\test_preparar_publicados_en_v3.py tests\test_shorts_en.py tests\test_uploader_retention_en.py

O GitHub Actions testa mapeamentos, manifests e bloqueios de QA; NAO acessa
os seus arquivos de imagem e audio no Windows. Um check verde nao prova
que as 13 versoes inglesas foram efetivamente renderizadas ou publicadas.

Ver tambem:
- docs/OTAKU-MULTICENA-3-0.md
- docs/CANAL-INGLES.md
- docs/DIREITOS-E-REVISAO.md
