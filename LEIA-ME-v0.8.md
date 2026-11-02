# Arquivo Otaku v0.8 — Radar de pautas, ideias e benchmarking

Esta versao **atualiza a v0.7**. Use o mesmo diretório `arquivo-otaku-kit`, substituindo os arquivos sem apagar `.venv`, `.secrets`, `.mpt-runtime`, `assets/gerados` ou `chatgpt-codex-proxy`.

## Novo comando — sem consumir tokens ou créditos

```powershell
.\radar-conteudo.ps1
.\radar-conteudo.ps1 -Quantidade 10
.\radar-conteudo.ps1 -Id hxh-killua
```

O comando gera:
- `assets/gerados/radar-editorial/fila-editorial.json`
- `assets/gerados/radar-editorial/fila-editorial.csv` (Excel PT-BR, separador ;)
- `assets/gerados/radar-editorial/fila-editorial.md`
- `assets/gerados/radar-editorial/brief-hxh-killua.md` (ao passar -Id)

## Trabalhar com dados reais do canal
Edite `dados/metricas-youtube.json` e acrescente **somente métricas reais** exportadas do seu YouTube Studio. Exemplo de esquema:

```json
{"videos":[{"formato":"personagem","escolheram_assistir_pct":63.0,"percentual_medio_assistido":88.0}]}
```

Os números acima são **apenas exemplo de formato**, não dados do Arquivo Otaku.
O radar mostra médias observadas por formato, sem prometer previsão de viralidade.

## O que melhorou
- 14 pautas originais de anime organizadas por tema (personagem, dilema, mistério)
- Fila diversificada entre franquias e temas, para evitar vídeos quase idênticos
- Notas heurísticas de curiosidade, identidade visual, originalidade e atemporalidade
- Alertas para fatos sem confirmação, spoilers e notícias que exigem fontes
- Brief de roteiro com estrutura de gancho, demonstração, interpretação e conclusão
- Auditoria editorial anterior agora inclui verificação de tese e variedade visual

## Limitações e segurança editorial
O programa **não pesquisa notícias em tempo real**, não lê os dados privados dos canais concorrentes e não garante mais visualizações. As pautas são hipóteses de produção, não notícias comprovadas. O conteúdo precisa ser pesquisado na obra antes da gravação. O script não publica nada e não altera OAuth ou vídeos existentes.

Para criar o vídeo de Death Note com o sistema já existente:
```powershell
.\planejar-episodio.ps1
.\gerar-video-codex.ps1 -SomenteConfigurar
.\gerar-video-codex.ps1 -ReutilizarImagens
```

Para outras pautas, use o brief como base e prepare um novo JSON de episódio revisado em `conteudos/`. Não reutilize imagens de Death Note para outros animes.

As regras de monetização do YouTube desaconselham slideshows repetitivos sem análise original: priorize roteiro com tese e evidência, e revise direitos autorais dos elementos visuais.

Pesquisa e fontes em `docs/BENCHMARK-V08.md`.
