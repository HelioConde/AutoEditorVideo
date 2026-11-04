# Piloto Games + Kids 3.0 — seis Shorts PT-BR

## Escopo confirmado

Ambos os canais serao **portugues brasileiro integral**: roteiro, voz, legendas, titulo, descricao e SEO.

**Games: Checkpoint Pixel** (nome provisório). Audiencia gamer geral, não infantil por padrão. Tres Shorts: Minecraft com um coracao; desafio Obby de Roblox; teste de autonomia dos colonos em TILLFOLK. Capturar **gameplay real ou autorizado**. Nada de simular conquistas ou fabricar cenas. Voz PT-BR AntonioNeural (+2%), sujeita a revisao auditiva.

**Kids: MiniMundo Curioso** (nome provisório). Publico-alvo: criancas entre 4 e 7 anos, com seus responsaveis. Tres Shorts originais: estrela azul encontra sua casa (cores), cinco passarinhos (contagem), casinha de formas geometricas. Animacao 2D vetorial original, movimentos lentos e independentes, sem flashes ou sustos. Voz PT-BR FranciscaNeural (-15%), sujeita a revisao. Sem pedidos para comentar, curtir, inscrever-se ou comprar. Classificar como Made for Kids no YouTube.

Nomes e IDs de canais ainda NAO foram confirmados ou criados. Nenhuma conta nova, OAuth, MP4 ou upload foi realizado pelo GitHub.

## Fontes oficiais

- Made for Kids: https://support.google.com/youtube/answer/9527654?hl=pt-BR
- Conteudo infantil de qualidade: https://support.google.com/youtube/answer/10774223?hl=pt-BR
- Uso de gameplay Minecraft: https://www.minecraft.net/en-us/usage-guidelines

Classificacao infantil impede comentarios e restringe varias outras funcoes. Nao usar metas de comentarios para Kids. Conteudo infantil precisa ser util, educativo, claro e adequado a idade. Gameplay Minecraft com narração criativa segue as condicoes oficiais de uso e nao autoriza copiar videos de terceiros.

## Implementacao

- conteudos/piloto-games-kids-3x2-v3.json: 3 historias/canal, 5 ganchos por tema, 5 cenas com movimento, roteiro, SEO e Made for Kids.
- scripts/piloto_canais_3x2_v3.py: validacao offline, seis pacotes de producao e inspecao, sem API ou upload.
- scripts/produzir_piloto_canais_v3.py: TTS com limites reais das palavras em portugues e render Remotion opcional, acionado por video.
- motion-remotion/src/pilot-short.tsx: vetores originais animados para Kids; Games exige arquivos de capturas reais.
- piloto-canais-v3.ps1: launcher seguro; nenhuma opcao de upload.
- tests/test_piloto_canais_3x2_v3.py: checks por canal, voz, Made for Kids, metadados e seguranca.

## Windows — primeiro validar, sem custo nem publicacao

    cd "C:\Users\helio\Documents\arquivo-otaku-github"
    git pull --ff-only origin main
    .\piloto-canais-v3.ps1 -Acao validar
    .\piloto-canais-v3.ps1 -Acao preparar
    .\piloto-canais-v3.ps1 -Acao inspecionar

Gerar apenas a narração em portugues de um Short (TTS Edge precisa internet):

    .\piloto-canais-v3.ps1 -Acao voz -Canal kids -Id kids-001-estrela-azul

Render local após a narração (não gera voz sozinho nem faz upload):

    cd motion-remotion
    npm.cmd install
    cd ..
    .\piloto-canais-v3.ps1 -Acao renderizar -Canal kids -Id kids-001-estrela-azul

Para Games, gravar cinco trechos por Short na pasta abaixo, com nomes cena-01.mp4 a cena-05.mp4, antes de renderizar:

    assets\gerados\piloto-canais-v3\capturas\<ID>\

IDs Games: game-001-minecraft-um-coracao, game-002-roblox-obby, game-003-tillfolk-colonia.

IDs Kids: kids-001-estrela-azul, kids-002-cinco-passarinhos, kids-003-formas-casinha.

O roteiro e storyboard preveem aproximadamente 38s Games e 28s Kids; o tempo real precisa seguir a voz e permanecer dentro de 60s. A saída, se renderizada e aprovada tecnicamente, fica em:

    assets\gerados\piloto-canais-v3\<canal>\<id>\final.mp4

O render exige FFprobe e Remotion no Windows e escreve QA local com SHA256, marcado como aguardando revisao humana de audio, imagem, legenda, direitos e adequacao infantil.

## Publicacao e aprendizado

Os Channel IDs continuam null e nenhuma API de publicacao foi adicionada. Criar e confirmar as duas contas do YouTube com identidades OAuth separadas e diferentes de Otaku antes de qualquer futuro envio. Privacidade inicial planejada: private.

Metadados: Games categoria Gaming (20), Kids Education (27) e Made for Kids true. Reavaliar classificacao caso algum video de games seja direcionado a criancas.

Analisar os Shorts apos 1, 6, 24, 72 e 168 horas, sem equiparar ausencia de dados a zero e sem assumir limite oficial de tres impulsos diários. Crescimento sustentavel depende de retencao, interesse e originalidade, e nao publicacao em massa.

Status: scripts e roteiros preparados. Os videos finais **ainda precisam ser renderizados no Windows** e os canais ainda precisam ser criados.
