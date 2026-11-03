# Otaku Reframe — Death Note EP01 (English, retention-first)

## Goal

Create an **original English-language short** about Death Note episode 1, using a different edit from the Brazilian Short. Hook in the first two seconds, at least one re-hook during 15–30 seconds, no locked/static shot above 4.8 seconds, captions with word emphasis, and 55–59s target. Absolute project limit: **60.000s**, verified by ffprobe.

**Manifest:** `conteudos/otaku-reframe-ep01-en.json` (`101-death-note-ep01`). The published Portuguese EP01 must never be replaced. English files go to `assets/gerados/shorts-animados/101-death-note-ep01/en-US/`.

## Commands (Windows PowerShell, at repository root)

```powershell
git pull
# Safe metadata plan: no image generation, speech, OAuth or publication
python scripts/renderizar_shorts_en.py --manifesto conteudos/otaku-reframe-ep01-en.json --acao planejar --id 101-death-note-ep01

# English neural narration + timed word boundaries. Independent of approved image cache.
python scripts/renderizar_shorts_en.py --manifesto conteudos/otaku-reframe-ep01-en.json --acao voz --id 101-death-note-ep01

# Audit existing PT image cache before spending quotas.
.\gerar-shorts-master.ps1 -Id 101-death-note-ep01 -DiagnosticarCache

# Visual planning is free; target shorter shots to prevent stagnant frames.
.\gerar-shorts-master.ps1 -Id 101-death-note-ep01 -SomentePlanejar -MaxSegundosPorPlano 4.5

# ONLY after source art and its layers have been approved:
python scripts/renderizar_shorts_en.py --manifesto conteudos/otaku-reframe-ep01-en.json --acao renderizar --id 101-death-note-ep01 --perfil vivo
```

If scene images are missing, use the master generator within available quota, review master/foreground/background, then retry rendering. The Python English renderer does **not** generate new images or publish anything. Do not claim success until MP4, word-timed captions and final duration are validated.

## Retention beat map

- **0–2s:** "One name. One death." Reveal the notebook immediately, tight zoom and high-contrast emphasis.
- **3–15s:** Light finds the book, writes a name, watches the live TV death.
- **15–30s:** Re-hook "Coincidence?" Confirm a second death, then raise the stakes: Light's new idea of justice.
- **30–42s:** Re-hook "It wasn't an accident." Reveal Ryuk and his boredom.
- **42–52s:** Light refuses to show fear; reveal his ambition and the birth of Kira.
- **52–59s:** Moral choice + direct channel follow CTA.

Change camera framing during longer scenes; **do not** hold an unchanged source image for 15 seconds. Kinetic emphasis on NAME, DEATH, COINCIDENCE, RYUK and KIRA. No uncontrolled flash intensity. Keep readable subtitles out of YouTube's UI safe zones.

## Editorial facts and risk controls

- The **L televised trap** is in episode 2; it does not belong in this episode 1 recap.
- English SEO metadata must say **Otaku Reframe**, not Otaku Archives.
- English OAuth tokens and English output directories must remain isolated from the Brazilian channel.
- Don't push generated videos, AI image cache, tokens or `.secrets` to GitHub.
- Don't upload without explicit permission, human image review, correct target channel verification and a duration test.

## Quality gate before release

1. Listen to every English sentence for pronunciation and natural pacing; a primitive TTS proof of concept is **not** the release voice.
2. Verify every visual change and caption sync, especially the first 2 seconds and both re-hooks.
3. Verify Ryuk / Light identities and that no L episode-2 plot point appears.
4. Run `ffprobe` on the final MP4 and block release if longer than 60 seconds.
5. Review title, description and cover with **Otaku Reframe** branding.
6. Save as an English draft and obtain final human approval before any YouTube upload.
