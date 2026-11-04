<div align="center">
<h1>🎬 Arquivo Otaku</h1>
<p><strong>Produção de Shorts sobre anime: ideias → roteiro → imagens IA → vídeo → miniaturas → YouTube</strong></p>
<p>Projeto local e gratuito para instalar; as APIs podem ter cotas, indisponibilidade ou custos conforme a conta.</p>
</div>

> **Substitui o AutoEditor Studio** neste repositório a partir de v0.8. O editor
> anterior permanece integralmente na branch
> [`backup/autoeditor-studio-2026-11-01`](../../tree/backup/autoeditor-studio-2026-11-01).

## Kids — Narração Acolhedora com pausas reais (teste)

A história da **estrelinha azul** foi reescrita em 13 falas PT-BR
com perguntas, 11,8 segundos de pausas naturais e animação sincronizada.
A criança tem 1,8 segundo para responder a cada pergunta de cor, sem
o personagem antecipar a resposta.

    .\piloto-canais-v3.ps1 -Acao inspecionar -Canal kids -Id kids-001-estrela-azul
    .\piloto-canais-v3.ps1 -Acao voz -Canal kids -Id kids-001-estrela-azul -Refazer
    .\piloto-canais-v3.ps1 -Acao renderizar -Canal kids -Id kids-001-estrela-azul -Refazer

A narração é reconstruída com FFmpeg a partir de trechos Edge TTS.
A meta é 45–55s, e a duração real nunca pode ultrapassar 60s.
Esse teste não altera os outros Kids, Gamer ou os canais de anime,
e **não envia nem publica vídeos**.

[Guia do teste de Narração Acolhedora](docs/KIDS-NARRACAO-ACOLHEDORA-V1.md).

## Biblioteca de videos por canal + revisao do MP4 no YouTube

Novo organizador **nao destrutivo** de `assets/gerados`: ao executar,
cria `biblioteca-videos/Kids`, `Gamer`, `Otaku Multicena` e `Otaku Reframe`,
com videos separados por episodio e catalogo SHA-256. Os caminhos originais
permanecem intactos para todos os scripts e plataformas.

    .\organizar-videos.ps1 -Acao Prever
    .\organizar-videos.ps1 -Acao Organizar
    .\organizar-videos.ps1 -Acao Abrir -Canal "Otaku Reframe"

Depois da primeira organizacao, os renderizadores PT-BR, EN e piloto
Gamer/Kids atualizam a biblioteca automaticamente. O modo padrao copia
arquivos; `-Metodo Link` economiza espaco, mas usa os mesmos bytes do
original e nao substitui um backup.

**Aprovacao manual de imagens/cenas nao e mais um requisito para renderizar.**
O criador avalia o MP4 completo **depois de enviar PRIVADO ao YouTube Studio**.
Continuam as verificacoes tecnicas de camadas, QA, duracao, audio e identidade
de canal. Nenhum envio automatico e criado por essa mudanca.

Guia: [Biblioteca e revisao posterior](docs/BIBLIOTECA-VIDEOS-CANAIS-POST-UPLOAD.md).

## Otaku Reframe (EN): producao e envio automaticos

O AutoEditorVideo Windows e o UNICO motor de edicao aprovado: artes originais
pelo Codex Proxy, narracao Edge TTS, movimento Remotion, legendas e ffprobe.
Nao usar videos montados externamente. A revisao humana e do MP4 completo
no YouTube Studio, **nao de cada uma das 18 imagens**.

Com seu clone local atualizado, crie e envie automaticamente o Short
`Did You Know? Death Note — regra do nome e rosto`:

```powershell
cd "$HOME\Documents\arquivo-otaku-github"
git switch main
git pull --ff-only origin main
.\gerar-otaku-reframe.ps1 -Acao Automatizar -Id 201-death-note-rosto-nome -Manifesto conteudos/otaku-reframe-did-you-know-201-en.json -MaxChamadas 60 -Visibilidade private
```

As imagens ja em cache sao reutilizadas; o numero 60 e apenas o **maximo
de chamadas adicionais de imagem**, nao estimativa de preco. Se o cache
estiver completo, use `-MaxChamadas 0`. O comando prepara o storyboard/voz,
faz QA tecnico automatico, renderiza MP4 pelo Remotion e envia via OAuth
ao **canal ingles confirmado**. O arquivo vai ao YouTube como **privado**
por padrao para voce revisar a versao pronta. Use `-Visibilidade public`
somente quando quiser que o Short seja publicado publicamente sem nova revisao.
O comando nao consegue trabalhar se o PC local estiver desligado.

Erros reais (cota indisponivel, cache inexistente/corrompido, cena explicitamente
reprovada, voz/legenda incompleta, duracao acima de 60 segundos, OAuth errado)
interrompem o fluxo. O QA tecnico nao garante ausencia de defeitos artisticos.
O upload nao e refeito cegamente se o resultado estiver ambiguo ou ja constar
no registro local. Consulte o [guia do Short EN](docs/OTAKU-REFRAME-DID-YOU-KNOW-201-EN.md).

## Otaku Multicena 3.0 — auditoria editorial e crescimento (fase 1)

O projeto agora inclui auditoria editorial **offline**, com checagens de gancho,
roteiro, marca, metadados e repeticao de aberturas; e comparacao de metricas
coletadas nas mesmas idades do video. Nada disso usa imagem IA, publica ou altera
os videos existentes.

```powershell
.\grade-50-shorts.ps1 -Acao Validar -Quantidade 50
.\grade-50-shorts.ps1 -Acao Validar -Quantidade 1 -ExigirGatesEditoriais
.\.venv\Scripts\python.exe .\scripts\otaku_growth_v3.py --saida assets\gerados\growth-v3-audit.json
```

Os gates automaticos nao substituem verificacao factual, audiovisual, de
movimento de personagens e direitos. Para exigir camadas de movimento de personagem
na producao, a grade ja possui `-ExigirMovimentoPersonagem`. Nao afirmar que
zoom de camera e animacao real. Nenhuma nova publicacao e executada apenas
por atualizar o GitHub.

Detalhes: [Otaku Multicena 3.0](docs/OTAKU-MULTICENA-3-0.md).

## Entradas PowerShell separadas: Gamer PT-BR e Otaku Reframe EN

Agora existem dois launchers dedicados, sem alterar o canal Kids:

    .\canal-gamer.ps1 -Acao Validar
    .\canal-gamer.ps1 -Acao Preparar
    .\canal-gamer.ps1 -Acao Voz -Id game-001-minecraft-um-coracao
    .\canal-ingles.ps1 -Acao Resumo
    .\canal-ingles.ps1 -Acao Preparar
    .\canal-ingles.ps1 -Acao Planejar -Id 003-death-note-xadrez

O Gamer usa **pt-BR**, exige cinco clips de gameplay real por Short e nao
possui publicacao. O Otaku Reframe usa **en-US**, manifesto/voz/QA exclusivos
e **nao envia** sem `-Acao Enviar -Id ... -ConfirmarEnvio`.
O envio EN privado e o padrao; publico exige confirmacao adicional.
Nenhum canal ou MP4 foi criado so por adicionar os scripts.

Veja [PowerShell por canal](docs/POWERSHELL-CANAIS-GAMER-INGLES.md).

## Dois novos canais PT-BR — Games + Kids (piloto 3x2)

Novo projeto independente com **3 Shorts Games** e **3 Shorts Kids**,
todos em português brasileiro: roteiro, títulos, voz e legendas.
Nomes provisórios: Checkpoint Pixel (games) e MiniMundo Curioso (kids).

    .\piloto-canais-v3.ps1 -Acao validar
    .\piloto-canais-v3.ps1 -Acao preparar
    .\piloto-canais-v3.ps1 -Acao inspecionar

Kids tem animações vetoriais originais em Remotion, voz pt-BR-FranciscaNeural
e classificação Made for Kids planejada. Games precisa de **gameplay real**
(Minecraft, Roblox e TILLFOLK) e narração pt-BR-AntonioNeural.

Nomes ainda precisam de aprovação, canais YouTube ainda não foram criados e
nenhum MP4 ou upload foi executado. O motor Otaku permanece inalterado.
O piloto não possui opção de publicar nem usa tokens OAuth de outros canais.

Guia: [Piloto Games e Kids — 3x2 PT-BR](docs/PILOTO-GAMES-KIDS-3X2-V3.md).

## Otaku Reframe EN V3 — Shorts brasileiros ja publicados

O canal ingles Otaku Reframe ja existe. O projeto agora permite preparar
versoes inglesas dos Shorts publicados no canal BR, com correspondencia
conservadora: 13 episodios mapeados, 1 ja em ingles e 4 sem fonte local confirmada.

Comandos Windows, sem upload nem gasto com IA:

    .\preparar-publicados-en.ps1 -Acao Resumo
    .\preparar-publicados-en.ps1 -Acao Verificar
    .\preparar-publicados-en.ps1 -Acao Preparar

O manifesto resultante fica em assets/gerados/otaku-br-publicados-en-v3.json.
Os scripts gerar-shorts-en.ps1 e publicar-shorts-en.ps1 aceitam -Manifesto
para nao afetar o lote historico de cinco videos EN. O upload exige a
identidade OAuth do Otaku Reframe, MP4 EN assinado, roteiro original ingles
e aprovacao especifica de envio. Privacidade padrao: private.

Leia: [Otaku Reframe BR->EN V3](docs/OTAKU-REFRAME-PUBLICADOS-BR-EN-V3.md).

## Otaku Multicena 3.0 — expansao TikTok e Kwai

A nova fase prioriza transferencia **responsavel** dos aprendizados de YouTube e Instagram
para plataformas onde o alcance ainda nao foi comprovado. A ferramenta
scripts/plano_multiplataforma_v3.py prepara legendas adaptadas e verifica o MP4
local opcionalmente, **sem uploads e sem consumir cota de IA**. Ela tambem registra
o status de som removido no TikTok por video (nao tenta alterar o audio ou reenviar).

Leia [o piloto multiplataforma de 14 dias](docs/CRESCIMENTO-MULTIPLATAFORMA-3-0.md)
antes de tentar qualquer publicacao. A integracao oficial TikTok existente
permanece separada, e Kwai nao possui publicador automatico configurado.

## Otaku Multicena — 50 Shorts com publicação imediata

50 roteiros e metadados estão cadastrados para novos e nostálgicos
animes. O motor Remotion usa **zoom suave**, sem flicker dos antigos
jump cuts; personagens só se movimentam de forma independente quando
há camadas RGBA seguras. Cenas padrão 2.5D sem RGBA individual passam
no QA e podem ser publicadas com zoom suave, com aviso explícito de
"somente câmera". Para exigir animação real de personagem e bloquear
essas cenas, use a opção `-ExigirMovimentoPersonagem`.

**Novo fluxo pedido:** gera um vídeo, valida QA, publica **público
imediatamente**, tenta enviar a thumbnail vertical depois que o YouTube
processar o Short, e avança para o próximo. **Sem agendamento.**

```powershell
cd "$HOME\Documents\arquivo-otaku-github"
git pull --ff-only origin main

# Preflight offline, sem publicar
.\grade-50-shorts.ps1 -Acao Validar -Quantidade 50

# Publica o primeiro Short como publico assim que pronto
.\grade-50-shorts.ps1 -Acao ProduzirPublicar -InicioNaLista 1 -Quantidade 1 `
  -Modelo gpt-image-2 -Perfil equilibrado `
  -MaxChamadasPorVideo 30 -ConfirmarCotaImagem -ConfirmarPublicacao
```

Para toda a grade, use `-Quantidade 50`, ciente de que 30 chamadas
por vídeo autorizam um teto de **1.500 chamadas de imagem**. Sem
`-ConfirmarPublicacao` não há upload. A função só roda no Windows local
com imagens, credenciais e proxy configurados.

Guia: [produção e publicação imediata de 50 Shorts](docs/OTAKU-GRADE-50.md).
O GitHub contém o código e os roteiros, não os 50 MP4s publicados.

## Melhorias Shorts a partir de 8 auditorias do vidIQ

Os oito relatórios apontaram enquadramento estático e legendas difíceis.
**Correção final após feedback visual do criador:** câmera com zoom suave
no lugar de jump cuts internos; legendas contrastadas e palavras alinhadas
aos timestamps reais do TTS. O pipeline invalida MP4s antigos quando
código visual muda. Não reenvia vídeos antigos automaticamente.

Relatório: [diagnóstico dos oito Shorts](docs/VIDIQ-OTAKU-MULTICENA-QA.md).

## Voz opcional — VoiceStudio + Edge TTS

O **Edge TTS continua sendo o motor padrao**. Para testar uma segunda narração
com o VoiceStudio local (sem produzir video e sem publicar):

```powershell
cd "$HOME\Documents\arquivo-otaku-github"
git pull --ff-only origin main
.\testar-voz-studio.ps1 -Id 401-jujutsu-kaisen-ep01 -CompararEdge
```

Para produzir um Short com VoiceStudio apos configurar o modelo de fala e o
Whisper ASR de timestamps por palavra, use
`./criar-publicar-short.ps1 -Id 401-jujutsu-kaisen-ep01 -VozMotor voicestudio`.
Sem `-Publicar`, o comando nao faz upload. Os arquivos de cada motor ficam
separados e o video e rerenderizado quando a voz de origem mudar.
Instalacao, cautelas de licenca e erros: [Guia VoiceStudio](docs/VOICE-STUDIO.md).

## Painel Shorts Studio (Windows)

Para controlar o gerador de cenas por botões, acompanhar logs e verificar o
Codex Proxy sem gerar imagens:

```powershell
.\abrir-shorts-studio.ps1
```

O painel roda apenas em `127.0.0.1` no seu computador. Ele identifica quando
o storyboard mudou de hash e lista caches antigos sem confundir isso com
créditos ou desconexão. Consulte [o guia Shorts Studio](docs/SHORTS-STUDIO.md).

## O que este projeto faz

- **Radar de pautas**: 14 temas de anime e fila editorial diversa, com ganchos revisáveis;
- **Roteiro / QA editorial**: checa tese, promessas e variedade visual;
- **Imagens 2D**: gera cenas pelo `chatgpt-codex-proxy` local, se a conta estiver elegível;
- **Alternativa sem IA**: reutiliza imagens existentes, ajusta iluminação e enquadramentos;
- **Edição vertical**: MoneyPrinterTurbo e FFmpeg, legendas e voz em PT-BR;
- **Miniaturas**: YouTube 16:9 e Shorts/TikTok 9:16;
- **YouTube**: título e descrição, OAuth oficial, registro para evitar upload duplicado;
- **Testes**: Python com pytest; não acessam contas pessoais nem geram vídeos.

**Importante:** isto é um programa de **Windows/PowerShell**, não um serviço de
geração em GitHub Pages. A página do repositório apenas apresenta as instruções.
O projeto não envia vídeos ao TikTok automaticamente.

## Primeiros passos (Windows)

```powershell
git clone https://github.com/HelioConde/AutoEditorVideo.git
cd AutoEditorVideo

# Python 3.11 + MoneyPrinterTurbo via uv
winget install --id=astral-sh.uv -e
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\instalar-windows.ps1

# Radar e planejamento, sem IA e sem upload
.\radar-conteudo.ps1
.\radar-conteudo.ps1 -Id hxh-killua
.\planejar-episodio.ps1

# Testes do plano
.\gerar-video-codex.ps1 -SomenteConfigurar
```

Para novas imagens com o Codex Proxy, inicie o Docker e siga
[`GUIA-CODEX-PROXY.md`](GUIA-CODEX-PROXY.md). Ele é um serviço de terceiros
que usa interfaces não oficiais, sujeito a mudanças, permissões e cotas.

```powershell
# Com conta elegível, gerar um Short com novas imagens
.\gerar-video-codex.ps1 -Modelo gpt-image-1.5

# Sem conta elegível, reciclar imagens locais
.\gerar-video-codex.ps1 -ReutilizarImagens
```

**Atenção:** o script de vídeo atual é um piloto do episódio Death Note; o radar
não aciona automaticamente toda a produção de um novo anime. Para criar um
episódio novo, é preciso preparar e revisar o JSON em `conteudos/`.

## YouTube — publicar somente após revisão

Crie as credenciais OAuth oficiais do tipo **Aplicativo para computador**,
salvando-as somente na pasta local `.secrets/`. Instruções em
[`GUIA-PUBLICAR-YOUTUBE.md`](GUIA-PUBLICAR-YOUTUBE.md).

```powershell
# Checagem sem upload
.\publicar-youtube.ps1 -Etapa diagnostico
# Criar capas e metadados, sem upload
.\publicar-youtube.ps1 -Etapa preparar
# Publicar um vídeo preparado (privado, para revisão)
.\publicar-youtube.ps1 -Etapa enviar -Privacidade private
```

O código atual aceita `-Privacidade public` explicitamente. Antes de publicar,
verifique copyright, narração, erros no roteiro, legendas e miniatura.

**Privacidade:** não execute `-Etapa tudo` sem conferir a opção `-Privacidade`;
alguns scripts herdados podem sugerir publicação pública como padrão.

## Garantia de segurança

Não publique `.secrets/`, `.env`, `youtube-token.json`, imagens de personagem
ou vídeos em GitHub. Há regras em `.gitignore` para barrar esses arquivos,
mas revise também `git status` antes de qualquer push.

## Documentação

- [Evolução v0.8](LEIA-ME-v0.8.md)
- [Referências analisadas](docs/BENCHMARK-V08.md)
- [Instalação do Codex Proxy](GUIA-CODEX-PROXY.md)
- [YouTube OAuth](GUIA-PUBLICAR-YOUTUBE.md)
- [Direitos e revisão](docs/DIREITOS-E-REVISAO.md)

## Testar

```powershell
.\.venv\Scripts\python.exe -m pip install pytest
.\.venv\Scripts\python.exe -m pytest -q tests
```

> A execução local de imagens IA depende do proxy e de acesso válido.
> O GitHub Actions valida apenas lógica local, sem credenciais e sem cobranças.

Desenvolvido por [Hélio Conde](https://github.com/HelioConde).

## Planejador editorial sincronizado v0.9

O modulo arquivo_otaku.pipeline aceita episodios independentes e legendas SRT. E apenas um planejador: a exportacao final pelo MoneyPrinterTurbo ainda precisa seguir o fluxo local.

```powershell
python -m arquivo_otaku.pipeline --episodio arquivo_otaku/episodios/death-note.json --srt caminho/legendas.srt
```

## Segundo Short — Light investigando Kira (v0.9.2)

O episodio 002 esta pronto para gerar no Windows, mas exige Codex Proxy com conta elegivel. Primeiro valide sem gastar cota:

```powershell
.\segundo-short-death-note.ps1 -Etapa plano
```

Para gerar as sete imagens novas, o video e as capas correspondentes:

```powershell
.\segundo-short-death-note.ps1 -Etapa criar -Modelo gpt-image-1.5
```

Para preparar capas/metadados novamente, sem gerar novas imagens:

```powershell
.\segundo-short-death-note.ps1 -Etapa preparar
```

Depois de assistir e revisar, enviar como privado:

```powershell
.\segundo-short-death-note.ps1 -Etapa publicar
```

Para publicar como publico, apenas apos revisao:

```powershell
.\segundo-short-death-note.ps1 -Etapa publicar -Privacidade public -ConfirmarPublico
```

A nova saida e `assets/gerados/arquivo-otaku-002-death-note-memoria-codex.mp4`. O video 001 permanece intacto. Consulte [30 pautas de Death Note](docs/DEATH-NOTE-PAUTAS-v1.md).

## Hotfix v0.9.3 — PermissionError ao salvar recortes

Se o segundo Short gerou as 7 imagens e falhou no caminho `otaku-v07-*.partial.jpg`, os arquivos de IA **ja estao em cache**. Atualize o codigo, depois execute novamente:

```powershell
.\segundo-short-death-note.ps1 -Etapa criar -Modelo gpt-image-1.5
```

A proxima execucao devera exibir `0 cenas exigem IA` e `[CACHE]` nas 7 cenas. O editor agora usa temporarios aleatorios e salva recortes em pastas proprias de cada episodio. Se houver novo `PermissionError`, confira as permissoes de escrita/Windows Defender na pasta `.mpt-runtime\storage\local_videos`. Nao apague imagens originais nem o cache.

## Lote de 25 Shorts — planejamento e renderizacao local (v0.9.3)

Foi adicionado um **gerenciador de fila** com 25 pautas diferentes de Death Note.
Os roteiros ainda precisam ser preparados e revisados antes da renderizacao;
o sistema recusa roteiros nao aprovados e **nao publica em massa**.

```powershell
.\lote-25.ps1 -Acao status
.\lote-25.ps1 -Acao renderizar
# Somente depois de aprovar episodios em dados/lote-25-pautas.json:
.\lote-25.ps1 -Acao renderizar -ConfirmarRender
```

Leia [o guia do lote](docs/LOTE-25.md).

## Motor de animação Remotion (experimental)

Foi integrado um segundo renderizador que anima personagem, objetos e câmera com movimentos por tipo de cena, reutilizando voz e legendas em cache. Ele **não faz upload**, não altera vídeos anteriores e bloqueia PNG opaco ou com verde residual.

Documentação e instalação: [motion-remotion/README.md](motion-remotion/README.md). Análise dos motores GitHub: [docs/ESCOLHA-DO-MOTOR-DE-ANIMACAO.md](docs/ESCOLHA-DO-MOTOR-DE-ANIMACAO.md).

## Cenas por acontecimentos do roteiro (sem quantidade fixa)

O número de imagens é decidido pelas mudanças narrativas, não por um valor padrão. O planejador local propõe cortes e permite `blocos_visuais` escritos pelo roteirista. Para planejar o xadrez sem gastar IA:

```powershell
.\planejar-cenas.ps1 -Id 003-death-note-xadrez
```

O JSON gerado é uma **proposta visual para revisão**; ainda não constitui um vídeo final nem aciona automaticamente o gerador de imagens-mãe. Veja [docs/CENAS-DINAMICAS.md](docs/CENAS-DINAMICAS.md).

## Fluxo integrado: imagens-mãe multicenas por roteiro (v1.4)

O clone inclui geração de storyboards com quantidade variável de enquadramentos, extração com alpha nativo via image edits, cenário reconstruído da mesma imagem, narração, legendas e render Remotion. Nenhuma publicação automática.

```powershell
.\gerar-shorts-master.ps1 -Id 003-death-note-xadrez -SomentePlanejar
```

Guia completo: [docs/MULTICENAS-DINAMICAS.md](docs/MULTICENAS-DINAMICAS.md).


## TikTok — upload oficial dos cinco Shorts (Content Posting API)

O projeto agora oferece publicação no TikTok por meio da **API oficial**, reutilizando os MP4s já renderizados. O modo padrão envia **rascunhos** para finalizar pelo aplicativo TikTok; a publicação direta só funciona com o escopo `video.publish` aprovado e está sujeita à auditoria e às opções de privacidade da conta.

```powershell
# Primeiro leia docs/PUBLICAR-TIKTOK.md e configure seu aplicativo em developers.tiktok.com
.\publicar-tiktok.ps1 -Acao diagnostico
.\publicar-tiktok.ps1 -Acao preparar -Limite 5
.\publicar-tiktok.ps1 -Acao conectar -Modo rascunho
.\publicar-tiktok.ps1 -Acao enviar -Modo rascunho -Limite 1 -ConfirmarEnvio
.\publicar-tiktok.ps1 -Acao status -Modo rascunho
```

Guia: [Publicar no TikTok](docs/PUBLICAR-TIKTOK.md). Tokens locais ficam em `.secrets/` e não vão ao GitHub. Os envios possuem histórico por hash para evitar duplicatas; não há publicação automática sem consentimento explícito.

## Canal internacional — Otaku Archives (EN)

O pipeline pode adaptar os cinco Shorts existentes para inglês sem gerar novas imagens.
Produz nova voz `en-US`, legendas sincronizadas, capa inglesa e MP4 separado em
`assets/gerados/shorts-animados/<ID>/en-US/`. Nenhum upload ocorre durante a geração.

```powershell
.\gerar-shorts-en.ps1 -Acao planejar
.\gerar-shorts-en.ps1 -Acao voz
.\gerar-shorts-en.ps1 -Acao renderizar
```

O novo canal YouTube precisa ser criado pelo usuário no YouTube. O publicador
`publicar-shorts-en.ps1` exige autenticação OAuth **separada**, com conferência
do Channel ID antes de qualquer upload para não misturar os dois canais.

Guia completo: [Criar e publicar no segundo canal em inglês](docs/CANAL-INGLES.md).


## REGRA MESTRA — Shorts de no máximo 60 segundos

**Todos os Shorts do Arquivo Otaku e Otaku Archives (YouTube PT/EN e TikTok) precisam durar 60,000 segundos ou menos no arquivo MP4 final.** Inclui abertura, narrativa, final de suspense, CTA de inscrição e a margem de renderização. A faixa recomendada para escrever e editar é **55–59 segundos**.

O editor bloqueia automaticamente a montagem quando a narração mais a margem ultrapassa 60 segundos e recusa publicar qualquer MP4 cuja duração real exceda esse teto (checagem via FFprobe). Não acelere a voz nem corte o gancho/CTA para contornar a regra. **Reescreva o roteiro, regrave e renderize novamente**.

Implementação: [scripts/shorts_duration.py](scripts/shorts_duration.py) · Testes: [tests/test_shorts_duration.py](tests/test_shorts_duration.py) · Política para agentes: [AGENTS.md](AGENTS.md).


## Produzir e publicar um Short completo em um comando

Use o novo modo de geração, narração, cenas com IA, animação, capa, descrição e upload YouTube. O processo retoma cenas em cache após falhas recuperáveis, respeita limite total de **60 segundos** e nunca publica um vídeo incompleto.

```powershell
cd "C:\Users\helio\Documents\arquivo-otaku-github"
git pull --ff-only origin main
.\criar-publicar-short.ps1 -Id 101-death-note-ep01 -Publicar -Privacidade public
```

Outros episódios: `102-death-note-ep02` e `103-death-note-ep03`.
Para gerar sem publicar, basta omitir `-Publicar`. Publicação direta exige credenciais YouTube OAuth já configuradas; o upload registra hash/ID e a capa correta é preservada localmente mesmo se a API do YouTube bloquear a miniatura do Short.

Guia: [Comando único para Shorts](docs/COMANDO-UNICO-SHORTS.md).



## Experimento: episodio -> curiosidade -> voce lembra? -> proximo episodio

O novo fluxo local alterna **quatro publicacoes ineditas**: EP02 (historia),
curiosidade sobre nome e rosto, video nostalgico "Voce lembra?" e EP03.
Cada upload ocorre pelo menos 60 minutos depois da confirmacao do anterior.

```powershell
cd "C:\Users\helio\Documents\arquivo-otaku-github"
git pull --ff-only origin main
.\publicar-recaps-por-hora.ps1 -Publicar -Privacidade public
```

Sem `-Publicar`, o comando apenas planeja e nao gasta cota de imagem.
O computador deve permanecer ligado. Os dois videos intermediarios
sao novos e usam imagens geradas por IA. O EP01 nao sera reenviado.
Guia: [Rodizio de Shorts com intervalo de uma hora](docs/TESTE-INTERVALO-YOUTUBE.md).


## Agendar 24 Shorts pelo proprio YouTube

O lote contem 8 episodios (EP02-EP09), 8 curiosidades e 8 videos "Voce lembra?".
O primeiro horario e 09:00 (America/Sao_Paulo), com intervalo padrao de 1 hora.

```cmd
cd /d C:\Users\helio\Documents\arquivo-otaku-github
git pull --ff-only origin main
programar-24-shorts.cmd planejar 2026-11-05
programar-24-shorts.cmd agendar 2026-11-05
```

O modo `agendar` gera e envia os 24 videos (quando aprovados), todos privados,
com `status.publishAt` futuro para publicacao pelo YouTube. O computador nao
precisa permanecer ligado nos horarios de liberacao, apenas durante producao/upload.
**Nenhum video e agendado no YouTube pelo simples ato de atualizar o GitHub.**
Guia: [Agendar 24 Shorts](docs/AGENDAR-24-SHORTS-YOUTUBE.md).
