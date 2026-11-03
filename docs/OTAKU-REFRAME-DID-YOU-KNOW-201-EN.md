# Otaku Reframe — Did You Know? (Death Note name + face)

**Short ID:** `201-death-note-rosto-nome`

**Editorial order:** Death Note EP01 recap (101) → **Did You Know? / anime fact (201)** → Do You Remember? (301). Do not insert a second episode recap before curiosity.

**Manifesto EN:** `conteudos/otaku-reframe-did-you-know-201-en.json`
**Video output:** `assets/gerados/shorts-animados/201-death-note-rosto-nome/en-US/201-death-note-rosto-nome-en-US-retention-v2.mp4`

## Producao 100% automatizada pelo AutoEditorVideo

O video vetorial produzido externamente foi reprovado. O unico render final
valido usa: storyboard EN -> imagens originais Codex Proxy -> camadas
master/foreground/background -> voz Edge TTS com WordBoundary -> Remotion
-> MP4 9:16 <=60s -> upload ao canal Otaku Reframe verificado.

O usuario revisa a qualidade do **video completo no YouTube**, nao cada
imagem. A opcao `-Acao Revisar` continua disponivel apenas para diagnostico
manual voluntario; NAO e um requisito para novos videos EN.

```powershell
cd "$HOME\Documents\arquivo-otaku-github"
git switch main
git pull --ff-only origin main

.\gerar-otaku-reframe.ps1 -Acao Automatizar -Id 201-death-note-rosto-nome -Manifesto conteudos/otaku-reframe-did-you-know-201-en.json -MaxChamadas 60 -Visibilidade private
```

`-MaxChamadas 60` e orcamento maximo de imagens adicionais, nao numero
de imagens que serao feitas ou valor monetario. Imagens existentes sao
reaproveitadas. Para trabalhar somente com cache completo:
`-MaxChamadas 0`.

`-Visibilidade private` (padrao) envia para a aba Conteudo do YouTube
Studio ingles, onde o criador revisa o Short inteiro. `-Visibilidade
public` e opt-in para publicacao automatica. O programa nao faz
upload duplicado, nao toca no canal BR e falha se OAuth/Channel ID
nao forem do canal EN. O token OAuth e salvo apenas em `.secrets/` local.

O QA automatico verifica cenas completas, hash/cache, alfa e composicao
das camadas, voz e sincronizacao de legendas, MP4 e duracao via ffprobe.
Ele nao finge uma certificacao estetica nem escreve aprovacoes manuais.
Cenas que tenham sido reprovadas explicitamente continuam bloqueando o
render. Quando falhar, consulte os logs; nenhuma parte incompleta e
publicada.

## Editorial canon

The notebook requires a face in the writer's mind while writing the target's name; people who share the same name are not all affected. As documented in the manga rule "How To Use It: I", and adapted to the anime. Keep the fact accurate: a name by itself isn't enough; you cannot infer that no one wearing a mask could ever be targeted (the writer may already know what they look like).

## Retention direction

- First 2s: "Did you know? A name ALONE isn't enough..." and a moving notebook/character illustration, with bold legible headline.
- Around 13–25s: two distinct adults who share a name. Re-hook: "So which Alex is the target?"
- 25–33s: first answer/reveal, face in memory. Make the visual contrast obvious.
- ~34–43s: hidden identities and masked detective, with distinct backgrounds.
- 43–51s: big conceptual payoff "POWER HAS A LIMIT".
- Last seconds: direct question and explicit subscription CTA.

**Assets:** All 12 beats have distinct English art directions, no licensed footage, no Portuguese text. Motion is activated from the beginning and captions use up to 3 words and active-word highlight. The new scene cache uses automatic technical QA; manual image review is optional. Real length is validated from generated audio and with ffprobe after Remotion; hard maximum 60s.

## Revisao manual opcional

Se voce quiser inspecionar uma imagem defeituosa, pode usar `-Acao Revisar`
para consultar o cache, sem mudar o fluxo principal. Nenhum clique
individual e necessario para `-Acao Automatizar`.

## Metadata

**Title:** Did You Know? The Death Note Needs MORE Than Your Name 📓 #Shorts

**Description and focused tags:** Stored explicitly in the manifest. Film & Animation category ID 1. Avoid broad, unrelated tags like "free movie", "anime in Hindi" and "full movie".
