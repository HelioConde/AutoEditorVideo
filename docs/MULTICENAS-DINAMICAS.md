# Arquivo Otaku — Storyboard dinâmico + imagem-mãe + Remotion (v1.4)

## O que já está no GitHub

O roteirista define acontecimentos narrativos, e a direção visual decide quantos enquadramentos ajudam a contar cada acontecimento. Não há número fixo de cenas. Um bloco de 16 segundos pode ter três planos com imagens próprias; um de quatro segundos pode manter só um. O parâmetro MaxSegundosPorPlano (padrão 6s) controla o limite recomendado de permanência de uma imagem, sem exigir um número fixo.

Cada enquadramento possui: master.png (cena integral) → foreground.png (sujeito com alpha) e background.png (cenário reconstruído com máscara) → composição alinhada no Remotion. Os planos são ligados a trechos reais do roteiro, não a uma tabela fixa de sete imagens.

**As imagens novas e a voz dependem do seu Windows, Codex Proxy e Edge TTS.** Testes CI não usam cota nem publicam vídeos.

## Primeiro: use o clone oficial

```powershell
cd "C:\Users\helio\Documents\arquivo-otaku-github"
git pull origin main
```

O projeto antigo continua intacto. É possível copiar apenas os outputs/cache, sem credenciais:

```powershell
$old="C:\Users\helio\Documents\arquivo-otaku-kit"
$new="C:\Users\helio\Documents\arquivo-otaku-github"
robocopy "$old\assets\gerados" "$new\assets\gerados" /E
```

Robocopy costuma retornar códigos 1–7 mesmo quando a cópia foi concluída; confira seu resumo.

Quando executado no clone, o wrapper busca automaticamente a configuração do proxy na pasta antiga arquivo-otaku-kit (somente leitura), se a configuração ainda não existir no clone. Não commit credenciais ou vídeos.

## Produção por etapas

```powershell
# 1. Planejar sem custo ou login
.\gerar-shorts-master.ps1 -Id 003-death-note-xadrez -SomentePlanejar

# 2. Gerar APENAS o primeiro enquadramento, até três chamadas de imagem
.\gerar-shorts-master.ps1 -Id 003-death-note-xadrez -Cena 1 -MaxChamadas 3

# 3. Verificar comparacao.jpg e qa.json no cache, antes de ampliar o lote.
# 4. Gerar os restantes com limite explícito de chamadas.
.\gerar-shorts-master.ps1 -Id 003-death-note-xadrez -TodasCenas -MaxChamadas 18

# 5. Quando todas as imagens estiverem completas, renderizar e gerar voz:
.\gerar-shorts-master.ps1 -Id 003-death-note-xadrez -TodasCenas -MaxChamadas 0 -Renderizar -CriarVoz

# Se já existir voz e legendas no cache, não precisa gerar voz de novo:
.\gerar-shorts-master.ps1 -Id 003-death-note-xadrez -TodasCenas -MaxChamadas 0 -Renderizar -Offline
```

Para aproveitar uma imagem-mãe já existente, forneça MasterExistente com o caminho do master.png 1024x1536. Isso economiza a primeira chamada naquele enquadramento. Os demais cortes sempre usam imagens-mãe diferentes quando os prompts diferem.

## Como reusar cache

Os nomes dos diretórios dos enquadramentos incluem um hash do modelo e do prompt. Se o storyboard mudar, os novos arquivos são produzidos em outra pasta e os antigos ficam preservados. O modo MaxChamadas 0 nunca pede novas imagens. Se a IA entregar PNG sem alpha, o processo interrompe e preserva os arquivos raw para inspeção; não cria fundo verde.

## Publicação e limite

Não existe upload automático. O MP4 final, a capa e o relatório de QA são produzidos em assets/gerados/shorts-animados/<ID> e precisam passar por revisão humana antes de publicar.

## Validação e limitações

- A cronologia dos enquadramentos é estimada por proporção de palavras e ajustada à duração real da narração; não é alinhamento semântico perfeito de cada fala.
- O Edge TTS fornece os tempos reais de início/fim das palavras para as legendas, quando a rede permite.
- A edição por imagens de entrada usa /v1/images/edits em JSON; o seu Codex Proxy pode não suportar esse recurso ou pode ignorar parâmetros. Ele será verificado no teste local.
- Remotion mantém o quadro integral com bordas de segurança. O movimento do primeiro plano é propositalmente pequeno para não expor imperfeições na reconstrução do fundo.
- A montagem produz uma prévia final com relatório, não uma aprovação visual automática.

Documentação de terceiros: https://developers.openai.com/api/reference/resources/images/methods/edit e https://www.remotion.dev/docs/cli/render


## Correcao de residuos de cabelo e maos no background

A mascara de personagens foi reforcada. O gerador pode reaproveitar uma imagem de fundo limpa de outro enquadramento somente quando a geometria da camera corresponder. Para reprocessar a composicao usando apenas cache:

```powershell
.\gerar-shorts-master.ps1 -Id 003-death-note-xadrez -Cena 6 -MaxChamadas 0 -Offline
```

Se ainda houver residuos no background, use reparo de fundo na cena escolhida:

```powershell
.\gerar-shorts-master.ps1 -Id 003-death-note-xadrez -Cena 6 -RepararFundo -MaxChamadas 1
```

O reparo consome no maximo uma nova chamada de edicao por cena, preserva a master e o foreground em cache e faz backup do background raw anterior. Agora o reparo recusa a execucao se master/foreground estiverem ausentes; nao os recria silenciosamente.

**Reutilizacao de fundo segura:** um `background.png` gerado de outra cena nao e considerado automaticamente um fundo limpo, pois pode conter cabelo/maos flutuantes. Depois de revisar visualmente e confirmar que o fundo esta correto, copie-o manualmente como `background-clean.png` na pasta da cena. Apenas os arquivos com esse nome entram na busca; o codigo ainda compara as partes visiveis do cenario para rejeitar outra posicao de camera. Nao copie uma cena com cortes ou fantasmas. Os fundos sem aprovacao visual nao sao promovidos automaticamente.

O `qa.json` passou a registrar `warnings` de mascara obsoleta ou sem historico (`background_sem_registro_de_mascara`). Isso e esperado no primeiro processamento de caches antigos. Novos reparos gravam a assinatura `background-raw-mask.sha256` e avisam caso a mascara mude. Esse aviso nao significa que houve nova cobranca. A imagem `diferencas.jpg` ajuda a localizar areas onde a composicao diverge da master; ela nao substitui a revisao humana.

Revise `comparacao.jpg` e `diferencas.jpg` antes de renderizar. Nao ha upload automatico.
