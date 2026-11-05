# Política de títulos, descrições, hashtags e tags — cinco canais (05/11/2026)

**Escopo:** planejamento editorial para futuros Shorts e vídeos do AutoEditorVideo. **Nenhuma alteração automática em vídeos existentes, nenhum upload e nenhuma reserva de produção** decorrente deste arquivo.

Fonte estruturada: [config/seo-metadata-policy-v1.json](../config/seo-metadata-policy-v1.json). Preservar regras existentes de `AGENTS.md`, `config/youtube-channel-registry.json` e `config/youtube-upload-profiles.json`.

## O que o exemplo do vidIQ realmente mostra

O criador forneceu a captura textual de https://youtube.com/shorts/zwyLeTzeCn4, com título "A regra secreta do Death Note que você não sabia", nota sugerida 92 no título, 100 na descrição, **30 visualizações** e previsão do vidIQ de aproximadamente **35 até o 14º dia**. São dados da captura, não uma consulta atual de analytics.

Problemas observados na captura: descrição completa/roteiro e bloco de SEO repetidos, muitas tags genéricas, marca antiga `Arquivo Otaku`, e indicação visual de `Alchemy Lab` em conteúdo de anime. **Verificar canal de publicação por ID** antes de qualquer alteração; não presumir upload errado apenas pelo texto da interface.

Notas de otimização são diagnósticos, não garantias de views. Segundo o artigo atual do vidIQ, no *Optimize Score* título e miniatura recebem 48% cada, descrição 2,5%, tags 1% e horário 0,5%. Esses pesos **não descrevem o algoritmo do YouTube**. O YouTube considera tags auxiliares; título, thumbnail e descrição pesam mais para descoberta.

## Padrão de metadados

| Campo | Padrão de redação proposto | Bloqueios |
|---|---|---|
| Título | Preferir 35–65 caracteres, expressão principal clara, curiosidade honesta; sem obrigar hashtag | Não prometer fatos, lançamentos ou resultados não demonstrados |
| Primeiras linhas | 1–2 frases específicas com assunto/palavra-chave de forma natural | Nunca texto genérico idêntico em todos os vídeos |
| Descrição | Resumo único, contexto / explicação / benefício, um CTA apropriado e crédito real | Proibir roteiro repetido, parágrafos duplicados e keyword stuffing |
| Hashtags | 2–4, incluindo apenas jogo/obra/ferramenta/quadro/marca pertinentes | Nunca usar hashtags irrelevantes só porque pontuam bem |
| Tags internas | 8–15 termos específicos, variantes genuínas e marca correta; teto técnico 500 caracteres | Não preencher 500 por preencher; não usar "anime clip" sem clipe |
| Evidências | Testes e tutoriais mostram resultados reais, versões, limitações e fontes | Sem demos inventadas, preços desatualizados ou "testei" falso |
| Métricas | Avaliar 1h, 24h, 72h e 7 dias em idades comparáveis | Não confundir previsão do vidIQ com resultado real |

São metas de trabalho, **não limites oficiais de pontuação**. O YouTube permite até 5.000 caracteres na descrição, mas não exige descrição longa; o YouTube afirma que tags têm influência pequena e que hashtags irrelevantes ou excessivas prejudicam a experiência.

## Modelos por canal

| Canal | Direção da descrição e das tags | Atenção especial |
|---|---|---|
| **Otaku Multicena (BR)** | Obra, personagem, fato específico e análise; #OtakuMulticena | Não deixar #ArquivoOtaku, outras marcas ou spoilers não sinalizados |
| **Otaku Reframe (EN)** | English-language anime analysis with exact work and character | Tudo no idioma inglês; #OtakuReframe |
| **Hélio Conde (Gamer)** | Jogo, título, modo, desafio ou curiosidade e plataforma | Gameplay real; não trocar marca automaticamente para Conde Games |
| **Emanuelly Kids** | História do Fofinhos explicada aos responsáveis | Made for Kids; evitar CTA de comentário/inscrição direcionado às crianças |
| **Alchemy Lab (planejado)** | Ferramenta/modelo, experimento, resultado real, tutorial e limite da técnica | Canal ainda exibe Alchemy Flames até renomeação; testes exigem evidência |

Não reutilizar marca, thumbnail, OAuth, categoria ou dados de outro canal. Conferir `channel_id` exato contra `config/youtube-channel-registry.json` e preservar bloqueio de publicação para Games/Kids/Alchemy enquanto OAuth específico não estiver configurado.

## Exemplo revisado — Death Note

**Título sugerido:** Death Note: por que saber o nome NÃO é suficiente? 📓

**Descrição sugerida:**

> Você sabia que conhecer o nome de alguém não é suficiente para usar o Death Note? 📓
>
> Existe uma regra fundamental: quem escreve no caderno também precisa visualizar o rosto da pessoa. Isso impede que outras pessoas com o mesmo nome sejam atingidas por engano.
>
> Descubra por que essa regra torna o confronto entre Light Yagami e L ainda mais interessante.
>
> 💬 Você acha que essa é uma das regras mais inteligentes de Death Note? Conte sua opinião!
>
> 🎬 Análise, roteiro, narração e edição originais, com ilustrações geradas por IA. Conteúdo independente, não oficial.
>
> #DeathNote #CuriosidadesAnime #OtakuMulticena

**Tags do campo específico do Studio:** Death Note, Death Note Brasil, regras do Death Note, Death Note explicado, Light Yagami, L Lawliet, Kira, curiosidades Death Note, curiosidades anime, Death Note rules, anime Brasil, caderno da morte, Otaku Multicena

As tags são separadas de hashtags; não copiar esse campo para a descrição. Esse conjunto é proposta editorial; **não foi publicado no YouTube**.

## Pipeline recomendado para o editor (a implementar)

1. Identificar canal e verificar ID exato antes de elaborar metadados; recuperar marca atual e público.
2. Pesquisar a palavra-chave principal e seus sinônimos com vidIQ quando houver saldo; registrar data e valor retornado, sem inventar scores indisponíveis.
3. Conferir fatos/versões/datas, e assistir ao vídeo ou estudar evidência do teste antes do título final.
4. Gerar 3 alternativas **honestas** de título; escolher a de maior clareza e promessa fiel, usando Optimize Score como critério secundário.
5. Gerar **descrição única** (não transcrição repetida), 2–4 hashtags relevantes e 8–15 tags exatas; validar tamanho e duplicações.
6. QA bloqueia conflito de marca, tema incompatível, "testei" sem evidência, metadados irrelevantes, erros objetivos de formatação e conteúdo infantil inadequado.
7. Para vídeos novos seguir fluxo de reserva em `conteudos/otaku-production-reservations.json` **antes de roteiros/comandos/assets/produção**, como define `AGENTS.md`; publicação futura preserva política de OAuth e privacidade.
8. Após publicar, avaliar métricas reais (retenção, views intencionais, fontes de tráfego e inscritos) por idade equivalente. Não otimizar só pelo score.

## Referências

- YouTube — Tags: https://support.google.com/youtube/answer/146402?hl=pt-BR
- YouTube — Descrições: https://support.google.com/youtube/answer/12948449
- YouTube — Hashtags: https://support.google.com/youtube/answer/6390658
- vidIQ — Optimize Score: https://support.vidiq.com/en/articles/13892020-uploading-and-editing-on-youtube-with-vidiq

**Status:** planejamento e configuração editorial criados; nenhum uploader foi modificado, nenhum vídeo foi editado e nenhum recurso de geração de mídia foi executado.
