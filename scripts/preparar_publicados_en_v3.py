#!/usr/bin/env python3
"""Prepare native-English versions ONLY for verified BR-published Shorts.

Offline, source-mapped, zero uploads and zero image-generation calls.
No placeholder dubbed video and no silent reuse of uncertain source material.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from metadata_shorts import load_episodes
from renderizar_shorts_en import load_english

SNAPSHOT = ROOT / "conteudos" / "otaku-br-publicados-snapshot-20261104.json"
CURATED = ROOT / "conteudos" / "otaku-br-publicados-en-curadoria-v3.json"
LEGACY_EN = ROOT / "conteudos" / "testes-animados-5-en.json"
DEFAULT_OUTPUT = ROOT / "assets" / "gerados" / "otaku-br-publicados-en-v3.json"
SOURCE_CHANNEL = "UCXGYTuBYn-0Ziqin5ajKhOw"
TARGET_CHANNEL = "UCBoNbQjaMYdpJqPLRZAFkvQ"
PRIORITY = (
    "003-death-note-xadrez", "005-death-note-sangue",
    "5002-apothecary-diaries", "5001-black-clover",
    "202-death-note-40-segundos", "004-death-note-segundo-kira",
    "5003-cyberpunk-edgerunners", "5004-jojo-steel-ball-run",
    "006-death-note-shinigami", "007-death-note-maca",
    "102-death-note-ep02", "103-death-note-ep03",
    "401-jujutsu-kaisen-ep01",
)
LEGACY_HOOKS = {
    "003-death-note-xadrez": [
        "Light and L never needed to throw a single punch to go to war.",
        "What if your opponent could read every mistake you made?",
        "Would you reveal one clue to challenge the world's best detective?",
        "How did Light and L turn conversations into a chess match?",
        "One wrong move in their mind game could cost a life.",
    ],
    "004-death-note-segundo-kira": [
        "L thought he was hunting one Kira.",
        "Why did a second Kira make Light's situation worse?",
        "Would you trust someone who shared your most dangerous secret?",
        "Who was sending messages as the second Kira?",
        "A new Kira meant more risks for Light and L.",
    ],
    "005-death-note-sangue": [
        "In Death Note, horror rarely needs to show blood.",
        "Light promised justice. But who gave him that power?",
        "Would you write someone's name to make the world safer?",
        "When did Light stop being a hero?",
        "Light's idea of justice came with a terrifying human cost.",
    ],
    "006-death-note-shinigami": [
        "Ryuk is a shinigami, a god of death.",
        "The chaos began because Ryuk was bored.",
        "Why would Ryuk drop a Death Note into the human world?",
        "What made Ryuk watch Light as entertainment?",
        "One bored shinigami changed Light's life forever.",
    ],
    "007-death-note-maca": [
        "A terrifying god of death who can't get enough of apples?",
        "Ryuk looks terrifying. His favorite snack doesn't.",
        "Would you give a shinigami an apple?",
        "Why is Ryuk so obsessed with apples?",
        "A simple apple became one of Ryuk's strangest traits.",
    ],
}
LEGACY_DESCRIPTIONS = {
    "003-death-note-xadrez": (
        "♟️ Light and L fight with logic, silence and impossible choices. "
        "Who would win the most dangerous mind game in Death Note?\n\n"
        "Original English analysis and narration, edited using AI-generated illustrations. "
        "Unofficial anime commentary.\n\n"
        "#DeathNote #LightYagami #L #AnimeMindGames #OtakuReframe #Shorts"
    ),
    "004-death-note-segundo-kira": (
        "😱 One Kira was difficult enough to find. Then Misa appeared as the second Kira "
        "and changed the investigation.\n\n"
        "Did Misa help Light or put him in danger?\n\n"
        "Original English commentary and narration with AI-generated illustrations. "
        "Independent, unofficial fan content.\n\n"
        "#DeathNote #MisaAmane #SecondKira #OtakuReframe #Shorts"
    ),
    "005-death-note-sangue": (
        "🩸 Light wanted to call himself justice. But when does that mission become absolute power?\n\n"
        "An original English character analysis with cinematic AI-generated illustrations. "
        "Independent fan work, not official anime footage.\n\n"
        "#DeathNote #Kira #LightYagami #AnimeAnalysis #OtakuReframe #Shorts"
    ),
    "006-death-note-shinigami": (
        "👁️ Ryuk changed everything by dropping a notebook into the human world. "
        "His reason wasn't justice. It was boredom.\n\n"
        "Original English storytelling, voice and editing using AI-generated illustrations. "
        "Independent fan commentary.\n\n"
        "#DeathNote #Ryuk #Shinigami #AnimeLore #OtakuReframe #Shorts"
    ),
    "007-death-note-maca": (
        "🍎 Why is Ryuk obsessed with apples from the human world? "
        "One strange craving makes Death Note's shinigami unforgettable.\n\n"
        "Original English narration and editing with AI-generated illustrations. "
        "Independent anime commentary.\n\n"
        "#DeathNote #Ryuk #Apples #AnimeTrivia #OtakuReframe #Shorts"
    ),
}
LEGACY_TAGS = {
    "003-death-note-xadrez": ["Death Note", "Light vs L", "Light Yagami", "L", "mind games", "anime analysis"],
    "004-death-note-segundo-kira": ["Death Note", "second Kira", "Misa Amane", "Light Yagami", "Death Note explained"],
    "005-death-note-sangue": ["Death Note", "Kira justice", "Light Yagami", "anime analysis"],
    "006-death-note-shinigami": ["Death Note", "Ryuk", "shinigami", "anime lore"],
    "007-death-note-maca": ["Death Note", "Ryuk apples", "shinigami", "anime facts"],
}


def _read(path: Path) -> dict:
    result = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(result, dict):
        raise ValueError(f"Arquivo JSON invalido: {path}")
    return result


def _sha(script: str) -> str:
    return hashlib.sha256(script.encode("utf-8")).hexdigest()


def validate_snapshot(source: dict) -> None:
    if source.get("schema") != "otaku-multicena/published-br-snapshot/v3":
        raise ValueError("Snapshot BR nao reconhecido")
    if source.get("source_channel_id") != SOURCE_CHANNEL or source.get("target_channel_id") != TARGET_CHANNEL:
        raise ValueError("IDs dos canais divergentes; nao preparar para a conta errada")
    rows = source.get("videos", [])
    if len(rows) != 18 or len({r["video_id"] for r in rows}) != len(rows):
        raise ValueError("Snapshot deve ter 18 IDs BR unicos verificados")
    allowed = {"ready", "source_unconfirmed", "already_on_english"}
    for row in rows:
        if row.get("status") not in allowed or row.get("privacy") != "public":
            raise ValueError("Estado BR invalido: " + str(row.get("video_id")))
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", str(row.get("video_id", ""))):
            raise ValueError("YouTube BR video ID invalido")
        if row["status"] == "ready" and not row.get("episode_id"):
            raise ValueError("Fonte BR confirmada sem episodio")
    if set(source.get("verified_en_preexisting", {})) != {
            "101-death-note-ep01", "201-death-note-rosto-nome"}:
        raise ValueError("Registro EN existente divergente; revisar duplicatas")


def _first_sentence(script: str) -> str:
    import re
    return re.split(r"(?<=[.!?])\s+", script, 1)[0].strip()


def build_manifest(
    *, snapshot: dict | None = None, curated: dict | None = None,
    pt_episodes: dict[str, dict] | None = None, legacy_english: list[dict] | None = None,
    only_ids: list[str] | None = None,
) -> tuple[dict, dict]:
    snapshot = snapshot or _read(SNAPSHOT)
    curated = curated or _read(CURATED)
    pt_episodes = pt_episodes or load_episodes(include_recaps=True)
    legacy_english = legacy_english or load_english(LEGACY_EN)
    validate_snapshot(snapshot)
    if curated.get("schema") != "otaku-multicena/english-editorial-v3":
        raise ValueError("Curadoria EN invalida")
    proposed = {e["id"]: e for e in curated["episodes"]}
    if len(proposed) != len(curated["episodes"]):
        raise ValueError("IDs EN repetidos na curadoria")
    legacy = {e["id"]: e for e in legacy_english}
    ready = {r["episode_id"]: r for r in snapshot["videos"] if r["status"] == "ready"}
    if set(ready) != set(PRIORITY):
        raise ValueError("Fila de fontes BR divergente; revisar correspondencias")
    if only_ids:
        missing = set(only_ids) - set(ready)
        if missing:
            raise ValueError("ID nao elegivel para EN: " + ", ".join(sorted(missing)))
    episodes = []
    for ep_id in PRIORITY:
        if only_ids and ep_id not in only_ids:
            continue
        source = pt_episodes.get(ep_id)
        row = ready[ep_id]
        if source is None or not source.get("script") or source.get("id") != ep_id:
            raise ValueError("Fonte PT nao existe no catalogo: " + ep_id)
        if ep_id in snapshot["verified_en_preexisting"]:
            raise ValueError("Upload EN ja detectado; bloqueado: " + ep_id)
        if ep_id in legacy:
            original = legacy[ep_id]
            chosen = _first_sentence(original["script"])
            option_set = LEGACY_HOOKS[ep_id]
            if chosen != option_set[0]:
                raise ValueError("Gancho legado alterado sem atualizar alternativas: " + ep_id)
            e = {**original, "description": LEGACY_DESCRIPTIONS[ep_id],
                 "tags": LEGACY_TAGS[ep_id] + ["Otaku Reframe", "anime shorts"],
                 "selected_hook": chosen, "hook_options": option_set}
        else:
            authored = proposed.get(ep_id)
            if authored is None:
                raise ValueError("Falta adaptacao editorial EN para " + ep_id)
            e = {k: authored[k] for k in ("id", "series", "title", "cover", "script",
                                           "description", "tags", "selected_hook", "hook_options")}
        if e["series"] != source["series"] or not e["script"].startswith(e["selected_hook"]):
            raise ValueError("Roteiro/gancho EN ou anime divergente da fonte: " + ep_id)
        if not 50 <= len(e["script"].split()) <= 145:
            raise ValueError("Roteiro EN fora da faixa de revisao: " + ep_id)
        hooks = e["hook_options"]
        if len(hooks) != 5 or len(set(hooks)) != 5:
            raise ValueError("Cinco propostas de gancho sao obrigatorias: " + ep_id)
        if e["selected_hook"] not in hooks:
            raise ValueError("Gancho aprovado ausente nas cinco alternativas: " + ep_id)
        if len(e["title"]) > 100 or not e["cover"].strip() or not e["description"]:
            raise ValueError("Metadados EN incompletos: " + ep_id)
        if "#OtakuReframe" not in e["description"] or "ArquivoOtaku" in e["description"]:
            raise ValueError("Marca EN incorreta: " + ep_id)
        episodes.append({
            **e,
            "channel": "Otaku Reframe",
            "source_br_video_id": row["video_id"],
            "source_pt_episode_id": ep_id,
            "source_pt_script_sha256": _sha(source["script"]),
            "source_snapshot_date": snapshot["observed_date"],
            "source_visual_check": "requires_full_english_video_review",
        })
    manifest = {
        "schema": "arquivo-otaku/shorts-english/v1",
        "channel": "Otaku Reframe",
        "language": "en-US",
        "voice": "en-US-GuyNeural",
        "target_channel_id": TARGET_CHANNEL,
        "source_br_channel_id": SOURCE_CHANNEL,
        "editorial_profile": "otaku-multicena/english-reuse/v3",
        "episodes": episodes,
    }
    pending = [r for r in snapshot["videos"] if r["status"] == "source_unconfirmed"]
    report = {
        "schema": "otaku-multicena/en-source-audit/v3",
        "observed_date": snapshot["observed_date"],
        "br_public_count": len(snapshot["videos"]),
        "ready_to_plan": len(episodes),
        "already_on_english": [
            r for r in snapshot["videos"] if r["status"] == "already_on_english"
        ],
        "unmatched_source": pending,
        "known_en_existing": snapshot["verified_en_preexisting"],
        "requires_qa": [
            "Original PT scene cache and scene hash must still be available",
            "English narration must be generated separately; no Portuguese dubbing",
            "Inspect rendered video for Portuguese baked into the art",
            "Verify character motion is more than camera zoom where required",
            "Review subtitles, pronunciation, licensed music, anime facts and rights",
            "Upload can only target authenticated Otaku Reframe, private by default",
        ],
        "uploads_executed": 0,
    }
    return manifest, report


def check_local_assets(manifest: dict, root: Path = ROOT) -> list[dict]:
    """Metadata only. Never call storyboard generators or mutate any cache."""
    rows = []
    for ep in manifest["episodes"]:
        folder = root / "assets" / "gerados" / "shorts-animados" / ep["id"]
        path = folder / "storyboard-producao.json"
        fallback = root / "assets" / "gerados" / "planos-visuais" / f"{ep['id']}-master-dinamico.json"
        selected = path if path.is_file() else fallback if fallback.is_file() else None
        rows.append({
            "id": ep["id"], "br_video_id": ep["source_br_video_id"],
            "pt_storyboard_present": bool(selected),
            "pt_storyboard_file": str(selected) if selected else None,
            "visual_quality_approved": False,
            "en_render_complete": False,
            "blocking_if_missing_cache": selected is None,
        })
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Otaku Reframe: preparar versoes inglesas de Shorts BR publicados")
    parser.add_argument("--acao", choices=("resumo", "preparar", "verificar"),
                        default="resumo")
    parser.add_argument("--id", action="append", help="IDs PT confirmados, opcionais")
    parser.add_argument("--saida", type=Path, default=DEFAULT_OUTPUT,
                        help="Manifesto local EN; nao enviar MP4 ou caches ao Git")
    args = parser.parse_args(argv)
    manifest, report = build_manifest(only_ids=args.id)
    if args.acao == "verificar":
        report["local_assets"] = check_local_assets(manifest)
    if args.acao == "preparar":
        args.saida.parent.mkdir(parents=True, exist_ok=True)
        args.saida.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")
        report["english_manifest_file"] = str(args.saida)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print("[EN BLOQUEADO] " + str(exc), file=sys.stderr)
        raise SystemExit(1)
