# Otaku Multicena 3.0 — guia operacional

> Estado: **fase 1 implementada em branch de desenvolvimento**. Sem uploads, sem geracao de imagem, sem alteracao de horarios/privacidade e sem dados de plataformas consultados pelo auditor offline.

## Objetivo

Criar Shorts e Reels de anime capazes de interessar alguem que ainda nao conhece o canal, com historias originais, ganchos claros, QA audiovisual e aprendizado baseado em metricas.

**Nao existe garantia de viralizacao ou limite oficial de tres Shorts recomendados por dia.**
A hipotese observada em dois lotes (tres primeiros com alcance, quarto e quinto sem impulso) deve ser testada, nao transformada em regra.

## O que esta implementado na fase 1

- `scripts/otaku_growth_v3.py`: auditoria editorial independente de APIs, com relatorio estruturado em JSON.
- `grade-50-shorts.ps1 -Acao Validar`: agora executa auditoria informativa automaticamente.
- `grade-50-shorts.ps1 -AuditarEditorial`: exibe a auditoria ao preparar/produzir.
- `grade-50-shorts.ps1 -ExigirGatesEditoriais`: bloqueia **problemas objetivos** (ex.: gancho ausente, roteiro divergente, titulo invalido), sem alegar que revisou fatos ou qualidade artistica.
- Comparador de **idade equivalente de publicacao** em 1, 6, 24, 72 e 168 horas. Dado desconhecido e `null`, nao zero.
- Testes unitarios offline no arquivo `tests/test_otaku_growth_v3.py`.

A auditoria identifica introducoes genericas, ganchos longos, narracao divergente, metadados ausentes ou com marca antiga, roteiros/aberturas repetidos e descricoes com inicio copiado.

Ela **nao** garante fidelidade ao anime, qualidade da animacao, autorizacao de musica/arte, ausencia de alucinacao ou resultado no algoritmo.

## Executar no Windows — nenhuma publicacao

```powershell
cd "$HOME\Documents\arquivo-otaku-github"
git pull --ff-only origin main

# Auditoria da grade inteira, informativa, sem imagens/voz/MP4
.\grade-50-shorts.ps1 -Acao Validar -Quantidade 50

# Auditoria do primeiro video, com bloqueio apenas dos erros objetivos
.\grade-50-shorts.ps1 -Acao Validar -InicioNaLista 1 -Quantidade 1 -ExigirGatesEditoriais

# Relatorio JSON detalhado para toda a grade (offline)
.\.venv\Scripts\python.exe .\scripts\otaku_growth_v3.py --saida assets\gerados\otaku-growth-v3-editorial.json

# Testes sem upload
.\.venv\Scripts\python.exe -m pytest -q tests\test_otaku_growth_v3.py
```

> A branch precisa ser integrada em `main` antes de usar o comando de `git pull` acima. Enquanto estiver em revisao, execute o auditor diretamente pela branch de trabalho. `assets/gerados` e apenas para saidas locais; nao enviar dados de conta, caches, tokens, imagens ou MP4 ao Git.

## Dados comparaveis por idade de video

Criar um JSON **local** com snapshots coletados de fontes autorizadas. Nao fabricar views nem chamar zero quando um valor estiver indisponivel.

```json
[
  {
    "platform": "youtube",
    "video_id": "ID_REAL_DO_VIDEO",
    "published_at": "2026-11-04T03:00:00Z",
    "collected_at": "2026-11-04T09:00:00Z",
    "views": null,
    "engaged_views": null,
    "shown_in_feed": null,
    "average_view_percentage": null
  }
]
```

O exemplo usa datas apenas para demonstrar o formato, **nao** sao metricas observadas. O auditor tambem aceita `"age_hours": 6` quando a idade ja foi calculada a partir de horarios confiaveis.

```powershell
.\.venv\Scripts\python.exe .\scripts\otaku_growth_v3.py `
  --metricas .\dados\metricas-locais-privadas.json `
  --saida .\assets\gerados\otaku-growth-v3-relatorio.json
```

O auditor compara valores apenas quando a coleta ocorreu perto das janelas-alvo. Quando nao existe coleta adequada, retorna `null`. Nao misturar idade distinta com desempenho final.

## Gates editoriais obrigatorios no fluxo humano

1. **Assunto:** contexto correto, interesse e conflito compreensivel para nao seguidores.
2. **Gancho:** explicar rapidamente por que vale continuar.
3. **Roteiro:** cada frase avanca a historia e cumpre a promessa do gancho.
4. **Audiovisual:** personagem consistente, movimento real quando necessario, voz correta, legendas e MP4.
5. **Originalidade:** comentario, interpretacao ou narrativa propria, sem clonagem de outros criadores.
6. **Publicacao:** direitos, metadados, thumbnail, duracao e configuracoes aprovadas.
7. **Aprendizado:** registrar identificador e metricas no tempo certo, com valores desconhecidos explicitados.

**Ferramenta automatica nao deve marcar os gates de verificacao humana como aprovados.** O QA atual permite cenas com camera-only salvo no modo estrito; para exigir personagem animavel use `-ExigirMovimentoPersonagem` em conjunto com o QA tecnico. Isso so testa disponibilidade de camadas RGBA seguras, nao certifica gestos faciais ou rigging completo.

## Cinco variacoes de gancho por pauta

Ao selecionar uma ideia, escrever e revisar cinco abordagens: curiosidade, contradicao, decisao, misterio e consequencia. Para cada uma, identificar:

- promessa verdadeira, compreensivel sem familiaridade com o anime;
- primeira imagem, movimento independente e frase falada;
- informacao revelada na conclusao;
- riscos de exagero, spoiler e afirmacao nao verificada.

Nao trocar palavras para "burlar" moderacao de plataformas.

## Experimento: frequencia de publicacao

Usar video de qualidade semelhante, duas ou mais semanas e horarios comparaveis, alternando cadencias que possam ser sustentadas sem desgaste. Comecar com 1 ou 2 Shorts por dia; comparar com amostras de lotes anteriores sem afirmar causalidade.

**Indicadores fundamentais:** exibicoes no feed, proporcao que escolheu assistir, retencao inicial, visualizacoes intencionais, curtidas, compartilhamentos e inscritos por video. Classificar:

- pouca exibicao = distribuicao ainda nao observada;
- muita exibicao + pouca escolha de assistir = melhorar abertura;
- boa escolha + abandono precoce = melhorar progressao;
- boa retencao + baixa conversao = melhorar valor recorrente e identidade.

Nao apagar ou republicar videos de pouco alcance para fabricar um novo "teste inicial".

## Proximas fases a implementar

1. **QA audiovisual mais forte:** revisar quadros reais, a pronuncia de nomes, audio, sincronizacao de legendas e movimento de personagem (nao so zoom).
2. **Ciclo editorial:** gerar cinco ganchos factuais por pauta, selecionar um roteiro e planejar cada cena com acao independente.
3. **Conectores autorizados:** coletar metricas de YouTube Studio, Instagram, TikTok/Kwai apenas quando houver permissoes e dados disponiveis.
4. **Experimentacao:** cohort por idade, dashboards, relatorio de hipoteses e limites da evidencia.
5. **Publicacao segura:** preservar confirmacoes de custo e upload, recibos para evitar duplicatas, cache de cenas e bloqueio de MP4 parcial.

A grade de 50 foi criada com um fluxo historico de publicacao publica imediata. **Esta fase 1 nao o executa nem o converte silenciosamente em agendamento**, e a revisao de uma nova cadencia exige revisao propria da politica de publicacao.

## Critérios para liberar fase 2

- Testes automatizados passam.
- Auditoria offline gera relatorio sem rede.
- Nenhum MP4, token, conta ou status de publicacao e alterado.
- Nenhum gate humano e marcado como aprovado por um algoritmo.
- Falhas atuais de proxy podem continuar bloqueando cenas, sem tentativa de preencher com artes falsas.

Filosofia: *Otaku Multicena nao e uma fabrica de Shorts: historias boas primeiro, alcance como resultado a medir.*
