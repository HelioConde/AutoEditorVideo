# Otaku Multicena BR — produção integral no GitHub Actions

Este é o fluxo correto: **o AutoEditorVideo original executa inteiramente no GitHub**.
Não é necessário abrir o editor no Windows, Docker, Codex local nem renderizar com
programas externos. Um runner Linux com Go, Python/Edge TTS, FFmpeg e Remotion
usa o storyboard real do canal BR e o Codex Proxy original fixado em commit.

## Primeiro piloto

- ID: `5008-firefly-wedding` (o primeiro sem pasta no `dir` local fornecido).
- Motor: `scripts/fluxo_unico_short.py` do repositório (chamado pelo script
  `scripts/otaku_br_cloud_short.py`), que utiliza `master_scenes.py` e
  `renderizar_master_remotion.py` com os assets gerados em tempo de execução.
- Storyboard: **sete** planos. No cache vazio, **21 requisições de imagem**
  previstas: master, foreground RGBA e background para cada plano.
- Modelo: `gpt-image-2`; voz `edge` PT-BR; composição `ArquivoOtakuMaster`
  original do Remotion; 1080×1920/30 FPS, duração limitada pelo QA original.
- Nenhum upload ao YouTube. Revisão editorial e visual obrigatória após o teste.

## Segurança e custo

- O proxy Go depende de endpoints não documentados; o funcionamento anterior de
  `/v1/images/generations` **não** garante que `/v1/images/edits` funcionará.
- O Environment `image-generation` deve continuar autorizado **somente à `main`**.
  Um job sem Secrets valida a política antes de agendar o runner com OAuth.
- A permissão de **21 chamadas** vale somente para a execução especial de piloto;
  **não** muda o default `MAX_IMAGE_CALLS=0` do Environment.
- O workflow bloqueia PRs, branches diferentes da main e reexecuções (`attempt > 1`)
  antes do acesso aos Secrets. Não usa reenvio automático de imagens: uma tentativa.
- Não colocar `accounts.json`, fotos infantis, PNG raw, máscaras, credenciais
  ou logs privados em artifact. O proxy escreve log temporário que é apagado.
- Para permitir a revisão do Short BR, há exceção **apenas neste piloto sem fotos
  pessoais**: o MP4 final, uma capa, metadados e um QA técnico são enviados como
  artifact de execução com retenção de **1 dia**. Por ser repositório público,
  considere esses arquivos **acessíveis a quem pode ler o repositório**.
- O estado OAuth poderá ser renovado pelo proxy mas **não** atualiza o Secret
  automaticamente. Para produção recorrente, será preciso persistência segura
  de tokens, cache de geração e gerenciamento de custos.

## Execução pelo GitHub (sem execução local)

A integração do PR do piloto com o título especial
`feat(cloud-br): run 5008 full video from AutoEditorVideo`
dispara uma execução **única**, que verifica o limite antes de chamar IA.

Em execuções futuras, use o Actions UI ou apenas o **gatilho remoto**:

```powershell
gh workflow run otaku-br-cloud-full-short.yml -R HelioConde/AutoEditorVideo --ref main -f episode_id=5008-firefly-wedding -f max_calls=21
```

Esse comando **não renderiza no computador**: só solicita execução ao GitHub.
Para inspecionar, visite o workflow em GitHub Actions e, caso os três jobs
passem, baixe o artifact `otaku-multicena-BR-5008-autoeditorvideo-review`.
Se a geração falhar, nenhum MP4 fictício será usado. As imagens e respostas
do provedor não são expostas por fallback externo. O cache do runner é
efêmero e não estará disponível na próxima execução, exigindo estratégia
de persistência privada antes de produção em escala.

## Limites da prova

Um Actions verde demonstra geração, narração, render e QA técnico realizados
pelo motor original. Não comprova que os personagens têm gestos articulados
nem que a obra está pronta para publicação; o QA de movimento informa
quantas cenas usaram camadas de personagem e quantas ficaram só na câmera.
