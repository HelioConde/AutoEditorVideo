# Otaku Multicena 3.0 — crescimento multiplataforma

## Missao

Levar a tracao inicial do YouTube/Instagram para TikTok e Kwai, onde o alcance ainda nao foi comprovado. Crescimento baseado em conteudo original, qualidade audiovisual e experimentacao, nao volume artificial de uploads.

## Contexto comprovado e pendencias

- YouTube: houve respostas positivas a historias de Death Note, Black Clover e Maomao.
- Instagram: Reels de Death Note e Black Clover receberam visualizacoes e crescimento gradual.
- TikTok: o criador informou a remocao de som em varios videos e ja enviou recursos; nao assumir que a palavra "Death" isoladamente causou a remocao.
- Kwai: nao temos metricas verificadas nem publicador automatico configurado. Confirmar a existencia e a identidade da conta antes de publicar.

## Fontes oficiais e precaucoes

- TikTok: https://support.tiktok.com/pt_BR/log-in-troubleshoot/troubleshooting/a-sound-i-added-to-tiktok-was-removed
  A plataforma cita direitos autorais e Diretrizes da Comunidade. Conforme a causa, pode permitir recurso ou troca de audio. Nao reencaminhar videos silenciados como tentativa de contornar a decisao.
- Meta: https://about.fb.com/news/2024/12/trial-reels-try-content-non-followers-first-see-what-perfoms-best/
  Trial Reels permitem testar conteudos com nao seguidores em contas elegiveis, mas nao garantem alcance.
- Kwai: https://www.kwai.com/pt-BR/creators/earn
  Incentiva producoes originais de qualidade. Validar politica atual, elegibilidade e direitos diretamente na plataforma.

## Nova ferramenta offline

Arquivo: scripts/plano_multiplataforma_v3.py

O comando utiliza episodios existentes, inclusive os historicos, e prepara propostas por rede:

- YouTube: conserva titulo/descricao como referencia; nenhuma atualizacao remota.
- Instagram: proposta de legenda de Reel, com gancho e contexto.
- TikTok: proposta de legenda e diagnostico de audio por video. Se o som foi removido, a proposta marca o canal como bloqueado para aquele ID.
- Kwai: proposta de legenda, apenas para publicacao manual apos verificar conta e politicas.

O plano nunca envia videos, troca trilhas, chama o proxy de imagem ou altera status em redes. Toda proposta requer revisao humana, tecnica e juridica.

### Exemplos PowerShell (nenhuma publicacao)

    cd "C:\Users\helio\Documents\arquivo-otaku-github"
    git pull --ff-only origin main

    # Propor metadados e controles para Black Clover
    .\.venv\Scripts\python.exe .\scripts\plano_multiplataforma_v3.py --id 5001-black-clover --saida .\assets\gerados\plano-black-clover-canais.json

    # Checar duracao, presenca de faixa de audio e formato 9:16 com FFprobe
    .\.venv\Scripts\python.exe .\scripts\plano_multiplataforma_v3.py --id 5001-black-clover --verificar-mp4 --saida .\assets\gerados\plano-black-clover-qa.json

    # APENAS se aquele video especifico tiver audio removido no TikTok
    .\.venv\Scripts\python.exe .\scripts\plano_multiplataforma_v3.py --id 5001-black-clover --tiktok-som-removido --saida .\assets\gerados\plano-black-clover-audio-pendente.json

    # Testes offline
    .\.venv\Scripts\python.exe -m pytest -q tests\test_plano_multiplataforma_v3.py

O argumento --tiktok-som-removido so aceita um ID por execucao para nao aplicar o status incorretamente a outros videos. O FFprobe nao pode confirmar a licenca do audio, apenas sua presenca.

## Piloto de 14 dias

### Dias 1 e 2: diagnostico e recuperacao

- Preservar uploads existentes e recursos em andamento.
- Verificar a justificativa e o resultado de cada recurso no TikTok.
- Confirmar a situacao do perfil Kwai.
- Escolher tres historias fortes e variadas, como Death Note, Black Clover e Maomao.
- Revisar uso de musica, narração e imagens e produzir apenas materiais autorizados.
- Concluir QA de video completo, sem aceitar zoom como prova de animacao de personagem.

### Dias 3 a 7: experimentos pequenos

- Publicar apenas apos autorizacao; testar um ou dois videos por dia conforme capacidade de QA, sem presumir limite oficial de distribuicao.
- Adaptar a legenda, o primeiro frame e a area segura de cada plataforma.
- Medir resultados apos 1, 6, 24 e 72 horas de cada publicacao.
- Registrar exposicoes, retencao, compartilhamentos, comentarios, conversao e qualquer aviso.
- Dado indisponivel = null, nunca zero.

### Dias 8 a 14: aprender e melhorar

- Diferenciar problemas de distribuicao de problemas de abertura ou retencao.
- Comparar os videos na mesma idade; nao apenas visualizacoes acumuladas.
- Repetir ideias e formatos que funcionaram, nao copiar videos quase identicos.
- Melhorar os primeiros tres segundos, narracao, legibilidade e animacao.
- Testar novos animes a partir de hipoteses documentadas.

## Metricas por plataforma

- YouTube: exibicoes no feed, escolheram assistir, visualizacoes intencionais, retencao e inscritos.
- Instagram: alcance nao seguidores, compartilhamentos, salvamentos, tempo assistido e seguidores.
- TikTok: views, tempo assistido, conclusao, compartilhamentos, seguidores e conformidade de audio.
- Kwai: alcance, retencao, comentarios e seguidores, quando esses dados estiverem disponiveis.

Meta da primeira rodada: tres publicacoes revisadas e tecnicamente conformes por rede-alvo, sem silenciamento e com dados de 72h, antes de definir uma meta numerica realista de visualizacoes.

## Bloqueios permanentes

- Nao publicar MP4 parcial ou sem QA.
- Nao tentar contornar remocao de audio, direitos autorais ou limites de API.
- Nao usar conta ou ferramenta de publicacao sem permissao.
- Nao presumir que existe publicador Kwai.
- Nao alterar videos publicados, horarios ou miniaturas sem aprovacao.
- Nao colocar MP4, tokens, segredos e caches em GitHub.

## Proximas evolucoes

1. Coleta de metricas reais do TikTok e Kwai, mediante ferramentas autorizadas.
2. Export audiovisual ajustado a safe-zones e verificador de animacao real.
3. Diagnostico melhor de direitos e conformidade de trilhas.
4. Calendario revisado e aprovado com protecao contra duplicatas.

Integrar este plano ao guia OTAKU-MULTICENA-3-0.md e manter a documentacao AGENTS.md como fonte das restricoes de publicacao. Esta fase prepara distribuicao: nao realiza uploads.
