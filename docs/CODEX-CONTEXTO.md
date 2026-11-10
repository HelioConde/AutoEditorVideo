# Contexto, memória e delegação no AutoEditorVideo

O Astra High/Ultra dirige arquitetura, animação, diagnósticos difíceis, integração e avaliação final. O operador escolhe o modelo no Codex. O utilitário é opcional e funciona fora dos pipelines de vídeo. A ordem de leitura por tarefa está no [AGENTS.md](../AGENTS.md), as decisões reutilizáveis estão na [memória técnica](memoria/README.md) e os números da homologação estão na [medição de Fofinhos](medicoes/codex-fofinhos-2026-11-09.json).

## Trabalhar com o contexto necessário

Comece pelos nomes versionados. Por exemplo, `git ls-files "*fofinhos*" "*ambient*"` encontra os módulos sem percorrer dependências ou mídias. Use `rg -n "def ambient_profiles" scripts` para localizar o símbolo. Leia as linhas relevantes e consulte os documentos exigidos pela combinação de canal, operação e caminho. Para conferir uma mudança pequena, use `git diff -- caminho`. Em ambientes com RTK, aplique o prefixo local. Registre um erro extenso em arquivo local de acesso restrito e extraia o nome do teste e a primeira causa reproduzível. Revise qualquer trecho antes de compartilhá-lo.

O Codex lê instruções globais e a cadeia de arquivos entre a raiz Git e o diretório de início. O índice da raiz também referencia os escopos, pois iniciar na raiz e editar um arquivo em `scripts/` não carrega automaticamente o AGENTS dessa pasta. Em 09/11/2026, a CLI 0.166.0 mostrou a regra final antes omitida e os arquivos de escopo completos em quatro diretórios, usando `codex debug prompt-input` sem inferência. Essa saída pode incluir instruções locais privadas. Examine-a localmente. [OpenAI Docs](https://learn.chatgpt.com/docs/agent-configuration/agents-md)

## Executar o utilitário

Requisitos básicos são Git e Python 3.11+. O transporte de rede usa uma dependência opcional instalada com `python -m pip install -r tools/codex_aux/requirements.txt`. Execute a partir da raiz do repositório. Esses comandos também servem em outro repositório que adote o pacote e o resolvedor de chave local em `scripts/estado_codex_proxy.py`.

```sh
python -m tools.codex_aux --help
python -m tools.codex_aux probe
python -m tools.codex_aux run tools/codex_aux/ambient_plan.json
python -m tools.codex_aux report RUN_ID
python -m tools.codex_aux assess RUN_ID TASK_ID --quality pass --tests 6 --rework 0
```

O `probe` usa apenas GET. Registra os IDs anunciados depois de verificar disponibilidade, autenticação e elegibilidade. O plano de exemplo sem modelo devolve as duas investigações ao Astra. Saída 0 indica conclusão de todas as tarefas, 2 indica trabalho a assumir pelo Astra, 1 indica falha do utilitário e 130 indica interrupção pelo operador. Em um lote misto, leia os relatórios concluídos antes de executar qualquer handoff. O comando `assess` exige a avaliação realizada pelo responsável.

Um inventário determinístico pode ser executado sem proxy. Salve um plano JSON como o seguinte e informe o caminho a `run`.

```json
{"tasks": [{"id": "inventario", "kind": "inventory",
  "files": [{"path": "scripts/fofinhos_ep01_render.py", "start": 48, "end": 91}]}]}
```

O plano descreve trechos com linhas inclusivas, perguntas e dependências explícitas em `after`. O agendador valida o grafo inteiro, lê cada fonte uma vez por lote e libera tarefas assim que suas dependências terminam.

| Tipo ou condição | Execução |
| --- | --- |
| `inventory` | Inventário local de declarações e linhas. |
| `architecture`, `animation`, `integration`, `diagnosis` | Handoff com a pergunta, trechos e dependências para o Astra. |
| `review` com benefício medido | Requer `public: true`, nome exato de modelo anunciado e orçamento `{"direct": 1000, "delegated": 800, "quality_ok": true}`. Os números do exemplo devem ser substituídos por medições comparáveis que incluam a síntese do principal. |
| `review` experimental | `--pilot --model ID_ANUNCIADO` habilita uma amostra controlada com material revisado. O resultado é evidência para a decisão posterior. |
| Ausência de modelo, qualidade insuficiente, dependência pendente ou custo delegado maior | Handoff para execução direta. |

Marque `public` somente depois de revisar a pergunta e os trechos para envio. A integração admite fontes textuais versionadas e idênticas ao commit, com linhas e tamanho limitados. Aplica restrições de caminho e verificações de credenciais também aos relatórios. Arquivos de mídia, referências privadas, dados de conta e dados operacionais não são insumos do auxiliar. O auxiliar recebe texto, sem ferramentas para abrir arquivos, fazer commits, publicar, excluir ou gerar imagens.

## Proxy, cache e recuperação

A integração usa HTTP em loopback. O cliente faz GET em `/health/live`, `/admin/accounts` e `/v1/models`, e no máximo um POST em `/v1/chat/completions` por análise. Envia `response_format=json_schema` e exige resposta terminada. A fonte instalada oferece também Responses, streaming e ferramentas. O cliente usa Chat sem streaming e sem ferramentas. O backend instalado implementa troca interna de conta. Antes de cada POST, o cliente exige uma única conta cadastrada e elegível. O resultado pode mudar entre a consulta e o POST se um operador reconfigurar o serviço durante a execução. [Fonte auditada do proxy](https://github.com/10/chatgpt-codex-proxy/tree/1da5476e46ef62830d7016de2a931b0b8270a6c4)

O limite por lote é `--concurrency 1` ou `2`, com prazo de até 600 segundos por operação. Em 429, erro do servidor ou falha de autenticação, o agendador suspende os próximos envios e preserva resultados já concluídos. Interromper com Ctrl+C fecha as conexões do cliente. O backend pode ter recebido o pedido. Uma resposta incerta gera um recibo que impede nova submissão idêntica. Use a saída de handoff para continuar no Astra. Respeite o período de espera do serviço.

O SQLite fica no diretório Git privado da worktree, no arquivo `codex-aux.sqlite3`. Guarde o identificador de execução emitido no início. `report RUN_ID` recupera resultados já concluídos e métricas mesmo após interrupção de outras tarefas. A aplicação grava a conclusão e seu relatório em uma transação. Resultados aprovados de animação e pins de cenas continuam nos catálogos próprios do projeto.

O cache de inventário considera a revisão Git, a implementação, o hash do arquivo inteiro, os intervalos e o contexto. O cache de análise do modelo considera também o modelo, a pergunta e os relatórios das dependências. Reutilização entre execuções requer `--revision` com uma versão conhecida do backend e do modelo. Sem versão verificável, use a deduplicação dentro do lote. Declare todos os arquivos que sustentam a conclusão. O cache só cobre o conjunto declarado. Testes de regressão e homologação continuam exigindo execução nova.

As métricas distinguem chamadas de inferência, tokens de entrada/saída, entrada já em cache, erros, repetições, tempo e pico de tarefas auxiliares concorrentes. Campo `null` indica quantidade desconhecida. A entrada em cache já faz parte da entrada total. Custos monetários e franquia da assinatura dependem do serviço e não são calculados a partir destes contadores.

## Reproduzir e reverter

```sh
python -m pytest -q tests/test_codex_aux_engine.py tests/test_codex_aux_proxy.py tests/test_codex_aux_benchmark.py tests/test_codex_policy_integrity.py
python -m pytest -q tests arquivo_otaku/tests
npm ci --prefix motion-remotion
npm run test:qa --prefix motion-remotion
node tools/codex_aux/render_ambient_probe.cjs CAMINHO_NOVO_OU_VAZIO
```

Para repetir a medição com a assinatura ChatGPT já autenticada e o Astra Ultra disponível, rode `python -m tools.codex_aux.benchmark A` e depois `python -m tools.codex_aux.benchmark B`. Os contadores vêm da CLI em uma única rodada por braço. A grade fixa verifica seis respostas contra o código e o plano originais de Fofinhos. O braço C exige catálogo e conta elegível no proxy. Use `python -m tools.codex_aux.benchmark C --aux-model ID_ANUNCIADO` em um piloto autorizado. C valida as fontes, o plano, as duas respostas e o uso informado antes de somar auxiliares e síntese. Registre o tempo fim a fim e o nível de cache ao comparar rodadas futuras.

As regras permanentes originais podem ser recuperadas com `git show 48533df:AGENTS.md`. O teste de integridade usa o conteúdo das 32 seções e também funciona em checkout raso. A reversão integral pode ser feita revertendo o commit de implementação. Configurações globais, credenciais e pipelines de produção estão fora desse commit.
