# Teste verdadeiro para Otaku Multicena BR (AutoEditorVideo)

Este procedimento usa SOMENTE o motor deste repositório:
`criar-publicar-short.ps1` → `fluxo_unico_short.py` → `master_scenes.py` (master/foreground/background) → `renderizar_master_remotion.py` (Remotion/FFmpeg).

**Não** usa vídeos externos, vidIQ Compose ou slides vetoriais. É executado localmente no Windows, porque o cache de imagens, voz e credenciais está no computador. O GitHub hospeda código e testes; não recebe MP4, PNG ou tokens privados.

## Primeiro episódio da fila não listado no `dir`

O diretório informado pelo autor contém `5001` até `5007`, mas não contém `5008-firefly-wedding`. Isso **não comprova** que nenhum dos anteriores foi publicado, apenas que existem pastas; `5008` é candidato ao teste, não requer alterar os anteriores.

## 1. Baixe o código novo

```powershell
cd C:\Users\helio\Documents\arquivo-otaku-github
git fetch origin main
git restore --source=origin/main -- testar-short-br-real.ps1
```

## 2. Planeje sem gerar ou gastar chamadas

```powershell
.\testar-short-br-real.ps1 -Acao Planejar -Id 5008-firefly-wedding
```

Este comando consulta o storyboard e o cache real para apresentar a quantidade de imagens pendentes, sem iniciar o proxy nem criar MP4. Não gera vídeo falso.

## 3. Confira limite de chamadas antes da produção

Cada cena precisa, normalmente, de **master + foreground + background**, três requisições por cena. Multiplique por quantidade de enquadramentos. O planejamento imprime o total; **não** pressuponha que o modelo seja gratuito nem use um teto menor que o total se não houver cache.

Com o proxy local funcionando e depois de revisar o orçamento:

```powershell
.\testar-short-br-real.ps1 -Acao Produzir -Id 5008-firefly-wedding -Modelo gpt-image-2 -MaxChamadas 21 -ConfirmarCotaImagem
```

No planejamento offline do GitHub, **7 enquadramentos × 3 camadas = 21 chamadas pendentes**. Por isso `21` é o teto deste exemplo, não previsão de custo nem garantia de sucesso. No seu Windows, a quantidade pode mudar conforme o cache fixado; utilize o total indicado por `Planejar` e o limite que deseja autorizar. O fluxo usa `Tentativas 1`, não recebe `-Publicar` e não marca o vídeo como público, privado ou agendado no YouTube: **não há upload algum**.

O projeto salva os resultados em `assets\gerados\shorts-animados\5008-firefly-wedding\`. Na conclusão, o motor produzirá um MP4 com nome `5008-firefly-wedding-master-multicenas-personagens-v3-equilibrado.mp4`, a capa e o QA. Se alguma etapa falhar, não substitua por vídeo externo; examine erros e retome preservando o cache.

## 4. Valide o MP4 com o programa

```powershell
.\testar-short-br-real.ps1 -Acao Validar -Id 5008-firefly-wedding
```

O modo `Validar` chama o verificador oficial (sem geração) e só confirma se há MP4 e capa válidos. **Concluído** significa válido tecnicamente, mas animação independente dos personagens, coerência artística e direitos devem ser revisados assistindo ao vídeo. Não confundir movimentação de câmera com rigging.

**Aviso:** nenhuma etapa cria/upload de MP4 dentro do GitHub Actions. A saída só existe após rodar o motor local ou uma futura solução segura de armazenamento privado explicitamente autorizada.
