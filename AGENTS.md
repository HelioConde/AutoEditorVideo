# AutoEditorVideo

## Contratos permanentes

- Antes de preparar qualquer vídeo, script, comando de geração ou lote, verificar canal e duplicatas e registrar a reserva no GitHub. A reserva na `main` precede chamadas de imagem. Registro, OAuth e render têm autorizações distintas.
- Cada um dos cinco canais tem identidade e OAuth próprios. Conferir ID exato, recibos, direitos e privacidade. A publicação depende da autorização para aquele fluxo. Reconciliar respostas ambíguas antes de qualquer ação. Exclusão exige IDs expressamente autorizados e as verificações do canal.
- Preservar contratos, assets oficiais, continuidade, articulação e referências privadas, em especial Emanuelly e Fofinho. Fotos privadas, credenciais, cache bruto, mídia e dados de conta ficam fora de logs, repositórios e artifacts, observadas as exceções expressas de cada política.
- **REGRA PRIORITÁRIA E PERMANENTE** de 08/11/2026 para Otaku BR/EN. Aplicar `config/otaku-character-identity-policy.json`, referências reais em todas as cenas e revisão visual antes da publicação. A mudança deste contrato requer autorização explícita do criador.
- QA, radar, testes e `-SomenteConfigurar` rodam sem gasto de cota e sem publicação. Respeitar limites do serviço. Medir cada Short com ffprobe e recusar duração acima de 60,000 s. Para mudanças funcionais, executar `python -m pytest -q tests` antes da entrega.

## Leitura obrigatória por tarefa

Somar as linhas aplicáveis ao canal, à operação e aos arquivos afetados. Abrir os documentos indicados antes de agir, inclusive ao iniciar o Codex na raiz. Caminhos em crases nas políticas são relativos à raiz do repositório.

| Quando | Instruções canônicas |
| --- | --- |
| Canal, conteúdo, dados privados, reserva, imagem, publicação, comando de vídeo, OAuth ou credenciais | [Segurança, canais e reservas](docs/politicas/seguranca-e-reservas.md) |
| Roteiro, fila de produção, processamento, render, automação do motor ou Actions de vídeo | [Produção e contratos de QA](docs/politicas/producao.md) |
| Upload, capa, metadados, SEO, Studio, visibilidade, agendamento ou exclusão | [Publicação e revisão](docs/politicas/publicacao.md) e regras do canal |
| Otaku Multicena BR ou Otaku Reframe EN, inclusive capa e lote Grade 50 | [Identidade, miniaturas, editorial, filas e EN](docs/politicas/otaku.md) |
| Emanuelly, Fofinho, série Kids, personagens, poses ou assets da série | [Referências oficiais e cânone](docs/politicas/fofinhos-referencias.md) e [animação, narração e QA Kids](docs/politicas/fofinhos-animacao.md) |
| Gamer, Alchemy Lab ou seus visuais e miniaturas | [Gamer e IA](docs/politicas/gamer-ia.md) |
| Launchers de canal ou pilotos 3×2 Gamer, Kids e EN | [PowerShell e pilotos legados](docs/politicas/lancadores-e-pilotos.md) e regras do canal |
| Animação, Remotion, câmera, voz, CTA ou legenda | [Direção e voz](docs/politicas/movimento-e-voz.md) e [instruções de animação](motion-remotion/AGENTS.md) |
| Python, PowerShell ou testes destes, mesmo em arquivos da raiz | [Scripts e testes](scripts/AGENTS.md) |
| GitHub Actions e código de seus jobs | [Workflows](.github/workflows/AGENTS.md) |

Em sobreposição de regras antigas e recentes, conferir [precedência documentada](docs/memoria/precedencia.md) e parar a ação específica se continuar ambígua.

## Contexto de trabalho

Pesquisar caminhos e símbolos primeiro. Abrir apenas trechos pertinentes, excluindo dependências, builds, mídia e caches da busca inicial. Reutilizar resultados verificados enquanto suas entradas não mudarem. Conferir diffs e limitar a saída do terminal, guardando detalhes de falha localmente quando necessário.

Começar pela entrada pertinente da [memória técnica](docs/memoria/README.md). Ao concluir trabalho relevante, atualizar ali evidência, testes, pendências e decisões reutilizáveis. Para delegação, cache e medição, consultar o [guia de contexto do Codex](docs/CODEX-CONTEXTO.md). Astra High/Ultra decide arquitetura, animação complexa e integração final.
