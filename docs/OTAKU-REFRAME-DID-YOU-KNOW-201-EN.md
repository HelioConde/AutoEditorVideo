# Otaku Reframe — Did You Know? (Death Note name + face)

**Short ID:** `201-death-note-rosto-nome`

**Editorial order:** Death Note EP01 recap (101) → **Did You Know? / anime fact (201)** → Do You Remember? (301). Do not insert a second episode recap before curiosity.

**Manifesto EN:** `conteudos/otaku-reframe-did-you-know-201-en.json`
**Video output:** `assets/gerados/shorts-animados/201-death-note-rosto-nome/en-US/201-death-note-rosto-nome-en-US-retention-v2.mp4`

## Editorial canon

The notebook requires a face in the writer's mind while writing the target's name; people who share the same name are not all affected. As documented in the manga rule "How To Use It: I", and adapted to the anime. Keep the fact accurate: a name by itself isn't enough; you cannot infer that no one wearing a mask could ever be targeted (the writer may already know what they look like).

## Retention direction

- First 2s: "Did you know? A name ALONE isn't enough..." and a moving notebook/character illustration, with bold legible headline.
- Around 13–25s: two distinct adults who share a name. Re-hook: "So which Alex is the target?"
- 25–33s: first answer/reveal, face in memory. Make the visual contrast obvious.
- ~34–43s: hidden identities and masked detective, with distinct backgrounds.
- 43–51s: big conceptual payoff "POWER HAS A LIMIT".
- Last seconds: direct question and explicit subscription CTA.

**Assets:** All 12 beats have distinct English art directions, no licensed footage, no Portuguese text. Motion is activated from the beginning and captions use up to 3 words and active-word highlight. The new scene master cache requires human approval on each original image. Real length is validated from generated audio and with ffprobe after Remotion; hard maximum 60s.

## Commands (PowerShell in repository root)

```powershell
cd "$HOME\Documents\arquivo-otaku-github"
git switch main
git pull --ff-only origin main

# 0 image credits: EN storyboard, voice (Edge TTS), cache diagnosis
.\gerar-otaku-reframe.ps1 -Acao Preparar -Id 201-death-note-rosto-nome -Manifesto conteudos/otaku-reframe-did-you-know-201-en.json

# Optional: review estimated image calls and missing source files
.\gerar-otaku-reframe.ps1 -Acao Diagnosticar -Id 201-death-note-rosto-nome -Manifesto conteudos/otaku-reframe-did-you-know-201-en.json

# Only if generation is budgeted and image proxy is configured. The cap is calls, not money:
.\gerar-otaku-reframe.ps1 -Acao GerarImagens -Id 201-death-note-rosto-nome -Manifesto conteudos/otaku-reframe-did-you-know-201-en.json -MaxChamadas 60

# Inspect each master + foreground + background; approve each scene individually:
# .\gerar-shorts-master.ps1 -Id 201-death-note-rosto-nome -Plano assets\gerados\shorts-animados\201-death-note-rosto-nome\en-US\storyboard-reframe-v2.json -Cena 1 -AprovarCena -Motivo "Manual QA verified" 

.\gerar-otaku-reframe.ps1 -Acao Validar -Id 201-death-note-rosto-nome -Manifesto conteudos/otaku-reframe-did-you-know-201-en.json

# Only after all assets/voice are manually reviewed:
.\gerar-otaku-reframe.ps1 -Acao Renderizar -Id 201-death-note-rosto-nome -Manifesto conteudos/otaku-reframe-did-you-know-201-en.json -ConfirmarRevisaoVisual
```

If the proxy has no available account, do NOT switch identity, bypass quotas, or publish partial renders. Keep cached approved assets and retry only when access is valid. No YouTube or TikTok upload is performed by these commands.

## Metadata

**Title:** Did You Know? The Death Note Needs MORE Than Your Name 📓 #Shorts

**Description and focused tags:** Stored explicitly in the manifest. Film & Animation category ID 1. Avoid broad, unrelated tags like "free movie", "anime in Hindi" and "full movie".
