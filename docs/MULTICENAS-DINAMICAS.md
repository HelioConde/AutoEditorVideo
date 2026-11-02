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


## Composição 2.5D com fundo limpo e foreground alinhado

**Regra atualizada:** o `background.png` passa a usar diretamente o fundo
`background-normalized.png` (ou um `background-clean.png` aprovado e alinhado),
sem misturar pixels da master via `background-mask.png`. A mistura anterior
recolocava fragmentos de cabelo, braço e mão na sala já reconstruída pela IA.

A máscara continua existindo, mas serve **somente para solicitar a remoção dos
personagens pela IA**. A camada para reprodução `foreground.png` pode receber
um deslocamento independente, enquanto `foreground-normalized.png` e o
`foreground-raw.png` preservam o recorte sem ajuste.

Na cena 06 do episódio `003-death-note-xadrez`, foi aprovado o deslocamento
**x=0, y=-211 pixels** para o cache **06-594007f1c10bb8**, reproduzindo o
alinhamento feito no Photoshop. Os ajustes ficam em
`configs/foreground-placements.json` e exigem correspondência **exata**
entre episódio e diretório/hash da cena. Outros caches/modelos não herdam o
deslocamento por engano. Para outras cenas, ajuste os valores em pixels originais
de **1024×1536**, com `x` positivo para a direita e `y` positivo para baixo.

Para reprocessar e conferir a cena sem custo de IA:

```powershell
.\gerar-shorts-master.ps1 -Id 003-death-note-xadrez -Cena 6 -MaxChamadas 0 -Offline
```

O processo preserva os três arquivos `*-raw.png`, aplica o deslocamento,
gera `background.png`, `foreground.png`, `comparacao.jpg` e
`diferencas.jpg`, atualizando o QA com `background_compositing=clean-direct`
e `foreground_offset`. Se o hash atual for diferente de
`06-594007f1c10bb8`, use `-DiagnosticarCache` antes de mudar a configuração.
Confirme visualmente o resultado; um foreground redesenhado pela IA pode não
coincidir totalmente com a master, apesar do alinhamento.


## Regra permanente: diversidade visual de cenas (v1)

O gerador agora usa uma biblioteca determinística de **10 planos de câmera para
xadrez e 10 planos reutilizáveis para outros assuntos**. Cada enquadramento
novo recebe os metadados `shot_type`, `camera_angle`, `camera_distance`,
`focus_subject`, `action`, `emotion`,
`must_differ_from_previous` e `avoid_repeating`.

O prompt sempre começa com direção de fotografia, ângulo e ação narrativa,
seguido de uma proibição explícita de repetir o enquadramento anterior.
Duas cenas consecutivas não podem repetir o mesmo tipo de plano; a distribuição
padrão também impede usar o mesmo plano mais de duas vezes em Shorts curtos.

### Exemplo didático de xadrez

A sequência de direção inclui: duelo em plano geral; câmera por trás de Light
olhando L; **close de uma mão de Light movendo o rei preto**; close na reação
de L; **ângulo por trás de L com mão movimentando o rei branco**; plano final
dramático em diagonal. Os movimentos de peças são **metáforas visuais do
confronto intelectual**, não uma afirmação de que uma partida literal ocorreu
no anime. A distribuição real depende do número de cenas identificado pelo
roteiro e do momento do fechamento.

### Verificar sem gastar créditos ou mexer no Short já pronto

```powershell
.\\gerar-shorts-master.ps1 -Id 003-death-note-xadrez -SomentePlanejar
```

O comando escreve a **proposta** em
`assets/gerados/planos-visuais/003-death-note-xadrez-master-dinamico.json`.
Ele não modifica o `storyboard-producao.json` já fixado, não regenera
a master aprovada nem faz requisições de imagem.

Para começar uma produção nova com a diversidade visual, revise antes a
proposta e use `-Replanejar` **intencionalmente**, em um novo conjunto de
imagens e com um orçamento permitido. O sistema preserva o plano antigo em
backup e mantém pastas antigas identificadas por hash. **Atenção:** o
`configs/scene-cache-pins.json` contém uma escolha manual da antiga cena 06
do episódio do xadrez; remova/ajuste essa escolha somente quando for iniciar
uma versão realmente nova e após revisar o cache existente. Não misture o
foreground de um enquadramento novo com uma master antiga por engano.

### QA de imagens repetidas

Além da auditoria dos metadados do storyboard, depois de compor cada cena o
motor compara a master com as **até seis masters anteriores do mesmo
storyboard/modelo**. A assinatura perceptual em tons de cinza e a diferença
média de luminância geram o aviso `composicao_repetitiva` quando as imagens
parecem quase idênticas. Esse aviso aparece no console e no
`qa.json.visual_diversity`, incluindo IDs das cenas parecidas e os resultados
da comparação.

**O detector é conservador e não substitui revisão humana**: o mesmo cenário
com personagens em poses diferentes pode escapar ao teste, e fundos muito
parecidos podem merecer avaliação manual. O gerador **não repete chamadas
pagas, não apaga arquivos e não altera imagens aprovadas** apenas porque
encontrou similaridade. O editor decide se vale gerar outra versão depois de
ver o custo estimado.

## Evitar personagens redesenhados sobre a mesa / tabuleiro

Quando a IA recebe uma imagem-mãe para **extrair** um foreground transparente,
ela pode, incorretamente, **redesenhar** o personagem, mudar o contorno do
corpo e até acrescentar partes da mesa dentro do recorte. O alpha pode ser
válido e as margens podem estar corretas, mas a composição final fica errada.
Isso aconteceu no exemplo enviado da cena 04 (L pensando diante do
tabuleiro): a master original é utilizável, enquanto o novo torso recortado
avança sobre a mesa.

### Novo QA: fidelidade da camada ao original

`scripts/qa_foreground_fidelity.py` mede a diferença entre pixels opacos do
`foreground-normalized.png` **antes de qualquer deslocamento/escala** e a
mesma posição da `master.png`. Inclui média global e da metade inferior.
Quando detecta redesenho grave, registra
`qa.json.foreground_source_consistency.redrawn=true` e o aviso
`foreground_redesenhado` e cria `preview-render-seguro.jpg`.

O QA de alinhamento antigo calculava apenas a diferença de composição média
sobre a tela inteira. Essa métrica sozinha pode esconder um torso redesenhado.

### O que acontece no render

Ao encontrar esse problema, o Remotion **não utiliza a camada defeituosa**.
Ele incorpora a **master original inteira** como quadro seguro e usa um
foreground transparente, sem movimento independente do corpo. A imagem
continua podendo receber movimento de câmera de cena, mas perde o efeito
parallax 2.5D, preferível a ter braços/mesa sobrepostos. A capa também usa
a master original se a extração está incorreta.

O renderizador recalcula a verificação mesmo para QA legado, de modo que um
`qa.json` antigo sem esse campo não permita o erro silenciosamente. O
manifesto de render registra `render_mode: master_static` para essas cenas.
Não são feitas chamadas de IA nem descartados arquivos raw/caches.

### Reprocessar a cena 04 do Death Note sem custo

```powershell
git pull origin main
.\gerar-shorts-master.ps1 -Id 003-death-note-xadrez -Cena 4 -Modelo gpt-image-1.5 -MaxChamadas 0 -Offline
```

Abra o `preview-render-seguro.jpg` no cache da cena 04, que mostra o quadro
que será utilizado no Short. Se desejar animação 2.5D do personagem
novamente, é necessário um recorte realmente fiel à master ou uma nova
edição aprovada, não uma transformação arbitrária da pose. A detecção é
heurística e **não dispensa conferência humana**.



### Bloquear uma master com anatomia fisicamente errada (pés/corpo na mesa)

A proteção acima preserva a **master** original quando o recorte alpha é ruim.
Se a master também tem pé, corpo ou objetos atravessando a mesa, **não é
possível corrigir isso apenas reorganizando camadas**. Marque a cena como
reprovada. A reprovação fica no cache local da cena (arquivo
`visual-review.json`), não é enviada ao repositório. O vídeo e a capa
passam a recusar cenas reprovadas.

```powershell
# Exemplo: reprovar a cena 04 porque o corpo atravessa o tabuleiro
.\gerar-shorts-master.ps1 -Id 003-death-note-xadrez -Cena 4 -Modelo gpt-image-1.5 -ReprovarCena -Motivo "Corpo ou pe atravessa a mesa"

# Após corrigir e confirmar VISUALMENTE a imagem da MESMA pasta/cache:
.\gerar-shorts-master.ps1 -Id 003-death-note-xadrez -Cena 4 -Modelo gpt-image-1.5 -AprovarCena -Motivo "Revisada manualmente"
```

Não aprove imagens defeituosas apenas para permitir o render. Ao gerar
um **novo enquadramento/hash**, a reprovação da versão anterior continua na
pasta antiga sem bloquear uma imagem nova. A nova master precisa passar por
revisão própria. O parâmetro `-ReprovarCena` não chama IA.

Os prompts de novas cenas de xadrez agora exigem que pés, pernas, quadris e
troncos **não ocupem a superfície da mesa/tabuleiro**. Apenas mãos e
antebraços podem tocar a mesa. Esses prompts só alteram uma produção nova
depois de replanejamento explícito; cenas antigas e os caches pagos não
são sobrescritos.


### Preparar novamente só as cenas reprovadas, preservando as boas

Se marcou cenas no cache com `-ReprovarCena`, **não** basta executar
`-Cena 2 -MaxChamadas 3` outra vez: a pasta atual já contém imagens
pagas. Também **não** execute `-Replanejar` para corrigir apenas uma
pequena parte do Short, pois isso muda o planejamento de todas as cenas.

O modo `-PrepararReprovadas` cria novos hashes **somente para cenas cujo
cache atual está marcado como reprovado**, acrescenta regras de geometria
física aos prompts e preserva backup do storyboard antigo. Não chama IA,
não envia imagens ao GitHub, não mexe nas pastas raw anteriores e
não remove nenhuma reprovação. O comando é seguro para ser executado uma
única vez; rodar novamente sem novas reprovações não altera nada.

```powershell
cd C:\Users\helio\Documents\arquivo-otaku-github
git pull origin main

# 1. Criar novas versões 02/03/04 sem custo
.\gerar-shorts-master.ps1 -Id 003-death-note-xadrez -Modelo gpt-image-1.5 -PrepararReprovadas

# 2. Conferir plano e hashes, ainda sem custo
.\gerar-shorts-master.ps1 -Id 003-death-note-xadrez -TodasCenas -Modelo gpt-image-1.5 -DiagnosticarCache -MaxChamadas 0

# 3. Gerar SOMENTE as novas cenas (cada chamada = imagem cobrada)
.\gerar-shorts-master.ps1 -Id 003-death-note-xadrez -Cena 2 -Modelo gpt-image-1.5 -MaxChamadas 3
.\gerar-shorts-master.ps1 -Id 003-death-note-xadrez -Cena 3 -Modelo gpt-image-1.5 -MaxChamadas 3
.\gerar-shorts-master.ps1 -Id 003-death-note-xadrez -Cena 4 -Modelo gpt-image-1.5 -MaxChamadas 3
```

Verifique as três novas imagens e suas máscaras. **Não marque como
aprovada uma imagem que ainda apresenta pés, pernas ou roupas atravessando
a mesa.** Uma reprovada nova ficará na pasta nova, sem sobrescrever
a versão anterior. O orçamento sugerido de três chamadas por cena é um
**limite**, não garantia de custo ou de qualidade.

Somente depois de revisar todas as cenas, renderize usando o cache:

```powershell
.\gerar-shorts-master.ps1 -Id 003-death-note-xadrez -TodasCenas -Modelo gpt-image-1.5 -MaxChamadas 0 -Offline -Renderizar
```

Se o comando de diagnóstico encontrar outro cache incompleto, não autorize
a chamada por impulso: verifique primeiro cada pasta. Cenas antigas com
pins manuais também continuam vinculadas ao cache explicitamente escolhido.
