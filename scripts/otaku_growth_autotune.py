#!/usr/bin/env python3
"""Autotune editorial offline: dados reais -> politica conservadora de futuros Shorts.

Sem rede, OAuth, geracao de imagem, TTS, render, upload ou alteracao de
videos existentes. Nao compara janelas diferentes como se fossem iguais.
"""
from __future__ import annotations

import argparse
from datetime import date
from hashlib import sha256
import json
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
CHANNEL_ID = "UCXGYTuBYn-0Ziqin5ajKhOw"
API_SOURCE = ROOT / "dados/metricas-redes/2026-11-08-youtube-api-vidiq.json"
RECAP_SOURCE = ROOT / "dados/metricas-redes/2026-11-08-youtube-recap-26out-01nov.json"
ACTIVE = ROOT / "config/otaku-growth-active-v1.json"

class EvidenceBlocked(ValueError):
    pass

def read(path: Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise EvidenceBlocked("SNAPSHOT_MUST_BE_OBJECT")
    return data

def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    return "".join(c for c in value if not unicodedata.combining(c))

def _whole_words(text: str) -> list[str]:
    return re.findall(r"[\wÀ-ÿ]+", str(text))

def latest_sources() -> tuple[Path, Path]:
    """Escolhe a ultima captura com mesmo schema verificavel, sem inferir data."""
    def select(pattern: str, baseline: Path, schema: str, date_key: str) -> Path:
        candidates = [baseline]
        candidates.extend(p for p in baseline.parent.glob(pattern)
                          if p.is_file() and p != baseline)
        valid = []
        for path in candidates:
            try:
                doc = read(path)
                if doc.get("esquema") != schema:
                    continue
                recorded = date.fromisoformat(str(doc[date_key]))
                if recorded > date.today():
                    # Data futura de uma captura nao pode ser usada para
                    # mudar politicas antes do evento real.
                    continue
                if schema.endswith("manual-recap/v1") and doc.get("canal_id") != CHANNEL_ID:
                    continue
                if schema.endswith("api-snapshot/v1") and not any(
                    c.get("channel_id") == CHANNEL_ID for c in doc.get("canais", [])
                ):
                    continue
                valid.append((recorded, path.name, path))
            except (OSError, ValueError, TypeError, KeyError):
                continue
        if not valid:
            raise EvidenceBlocked("NO_TRUSTED_EDITORIAL_SNAPSHOT_"+schema)
        return max(valid)[2]
    return (
        select("*youtube-api-vidiq*.json", API_SOURCE,
               "autoeditor/youtube-analytics-api-snapshot/v1", "coleta_em"),
        select("*youtube-recap*.json", RECAP_SOURCE,
               "autoeditor/youtube-studio-manual-recap/v1", "data_registro")
    )

def evidence(api: dict, recap: dict, *, api_source: Path = API_SOURCE,
             recap_source: Path = RECAP_SOURCE) -> dict:
    if api.get("esquema") != "autoeditor/youtube-analytics-api-snapshot/v1":
        raise EvidenceBlocked("UNKNOWN_ANALYTICS_SOURCE_SCHEMA")
    if recap.get("esquema") != "autoeditor/youtube-studio-manual-recap/v1":
        raise EvidenceBlocked("UNKNOWN_STUDIO_RECAP_SCHEMA")
    if recap.get("canal_id") != CHANNEL_ID:
        raise EvidenceBlocked("WRONG_RECAP_CHANNEL")
    channels = [c for c in api.get("canais", []) if c.get("channel_id") == CHANNEL_ID]
    if len(channels) != 1:
        raise EvidenceBlocked("MISSING_OR_DUPLICATE_BR_CHANNEL")
    br = channels[0]
    metrics = br.get("metricas_periodo", {})
    period = api.get("periodo_relatorio", {})
    week = recap.get("periodo_recap_semanal", {})
    rolling = recap.get("ultimos_28_dias", {})
    decision = rolling.get("decisao_assistir", {})
    viewed = decision.get("continuaram_assistindo_percentual")
    ignored = decision.get("ignoraram_percentual")
    if any(isinstance(n, bool) or not isinstance(n, (int, float)) or not 0 <= n <= 100
           for n in (viewed, ignored)) or abs(viewed + ignored - 100) > 0.11:
        raise EvidenceBlocked("VIEWED_VS_SWIPED_TOTAL_INVALID")
    for label, obj in (("API", period), ("RECAP", week)):
        try:
            first = date.fromisoformat(obj["inicio"])
            last = date.fromisoformat(obj["fim"])
        except (KeyError, ValueError, TypeError):
            raise EvidenceBlocked("INVALID_"+label+"_WINDOW") from None
        if first > last or (last-first).days > 90:
            raise EvidenceBlocked("IMPOSSIBLE_"+label+"_WINDOW")
    if not isinstance(metrics.get("views"), int) or metrics["views"] < 0:
        raise EvidenceBlocked("INVALID_ANALYTICS_VIEWS")
    top = rolling.get("top_5_shorts_por_visualizacoes", [])
    if len(top) != 5 or any(not isinstance(item.get("titulo_visivel"), str) for item in top):
        raise EvidenceBlocked("MISSING_TOP_FIVE_EDITORIAL_REFERENCES")
    titles = [x["titulo_visivel"] for x in top]
    return {
        "channel_id": CHANNEL_ID,
        "api_period": [period["inicio"], period["fim"]],
        "recap_week": [week["inicio"], week["fim"]],
        "rolling_28d_exact_dates": None,
        "views_analytics_api_period": metrics["views"],
        "engaged_views_api_period": metrics.get("engaged_views"),
        "views_vs_swiped_28d_percent": round(float(viewed), 2),
        "ignored_28d_percent": round(float(ignored), 2),
        "recap_week_likes": week.get("curtidas_recebidas"),
        "recap_week_subscribers_gained": week.get("inscritos_ganhos"),
        "top_five_from_separate_28d_window": titles,
        "source_files": [str(api_source.relative_to(ROOT)),
                         str(recap_source.relative_to(ROOT))],
    }

def build_policy(api: dict, recap: dict, *, api_source: Path = API_SOURCE,
                 recap_source: Path = RECAP_SOURCE) -> dict:
    data = evidence(api, recap, api_source=api_source, recap_source=recap_source)
    viewed = data["views_vs_swiped_28d_percent"]
    # Apenas uma medicao de viewed-vs-swiped -> piloto, nao auto-trocar a
    # duracao de todos os videos nem atribuir causalidade a um titulo.
    focus = "test_hook_first_3s" if viewed < 40 else "keep_testing_hooks"
    return {
        "schema": "autoeditorvideo/otaku-growth-active/v1",
        "channel": "br",
        "channel_id": CHANNEL_ID,
        "mode": "auto_adaptive_editorial_guards_not_video_mutation",
        "inputs": data,
        "hypothesis_not_proven": True,
        "priority": focus,
        "viewed_rate_aspirational_target_percent": 40,
        "production_rules": {
            "hook": {
                "first_seconds": 3,
                "suggested_max_words": 12,
                "styles_to_test": ["misterio_contradicao","escolha_consequencia",
                                   "curiosidade_de_habilidade"],
                "no_generic_intro": True,
                "promised_fact_must_be_grounded": True,
                "show_narrated_action_in_first_frame": True
            },
            "title": {
                "preferred_characters": [12, 70],
                "max_uppercase_emphasis_words": 2,
                "must_be_specific_to_story": True,
                "no_unverified_clickbait": True,
                "allow_title_variation_only_before_upload": True
            },
            "script": {
                "clear_question_or_conflict": True,
                "payoff_before_end": True,
                "no_filler": True,
                "no_spoken_channel_name": True,
                "default_ending": "deliver_story_result_without_generic_cta",
                "do_not_change_published_narration": True
            },
            "narration": {
                "engine": "edge-tts",
                "style": "natural_ptbr_with_story_specific_emphasis",
                "verify_character_names_and_pronunciation": True,
                "sync_from_actual_audio": True,
                "no_unverified_synthetic_word_timing": True
            },
            "captions": {
                "max_words_per_phrase": 3,
                "timestamps_source": "real_word_boundaries_or_verified_asr",
                "high_contrast": True,
                "avoid_faces_and_hands": True,
                "mobile_safe_zone_required": True
            },
            "thumbnail": {
                "aspect_ratio": "9:16",
                "format": "original_render_thumbnail",
                "preferred_words": [2, 5],
                "readable_mobile": True,
                "recognizable_story_subject": True,
                "verify_hash_before_upload": True,
                "do_not_replace_with_youtube_auto_frame": True
            },
            "visual": {
                "first_scene_narrative_action": True,
                "preserve_named_character_identity_anchors": True,
                "prefer_independent_layers_for_real_motion": True,
                "camera_zoom_is_not_character_animation": True,
                "avoid_jump_cut_flicker": True,
                "smooth_camera_zoom_max_percent": 4,
                "no_fake_gameplay": True
            },
            "duration": {
                "baseline_experiment_seconds": [30, 45],
                "extended_experiment_seconds": [87, 93],
                "extended_max_share_of_new_tests_percent": 25,
                "actual_duration_from_tts_and_ffprobe": True,
                "do_not_force_a_global_duration_from_one_snapshot": True
            },
            "content": {
                "experiments": [
                    {"key": "misterio_contradicao", "example": "Death Note",
                     "question": "Gancho contraditorio entrega a revelacao?"},
                    {"key": "escolha_consequencia", "example": "Steel Ball Run ou dilemas emocionais",
                     "question": "Conflito com custo claro incentiva continuar?"},
                    {"key": "curiosidade_de_habilidade",
                     "example": "Zenitsu, Kurapika ou Killua",
                     "question": "Habilidade com pergunta verificavel desperta curiosidade?"}
                ],
                "avoid_all_topics_same_franchise": True,
                "never_duplicate_existing_video": True,
                "no_unverified_news_or_canon": True
            }
        },
        "measurement_protocol": {
            "age_hours": [1,6,24,72,168],
            "primary": "viewed_vs_swiped_percent",
            "secondary": ["engaged_views","average_view_percentage",
                          "subscribers_per_1000_views","views_at_same_age"],
            "compare_same_channel_window_and_video_age": True,
            "minimum_completed_per_variant_before_promotion": 5,
            "automatic_promotion_without_comparable_evidence": False
        },
        "protected_guards": {
            "do_not_edit_existing_public_videos": True,
            "no_render_or_upload_by_autotune": True,
            "no_image_api_calls": True,
            "no_secrets_or_private_images": True,
            "keep_creator_pause_and_reservation_registry": True,
            "human_canon_rights_review_where_required": True,
            "private_review_or_explicit_public_upload_authorization": True
        }
    }

def load_policy(path: Path = ACTIVE) -> dict | None:
    if not Path(path).is_file():
        if Path(path) != ACTIVE or not API_SOURCE.is_file() or not RECAP_SOURCE.is_file():
            return None
        api_source, recap_source = latest_sources()
        return build_policy(read(api_source), read(recap_source),
                            api_source=api_source, recap_source=recap_source)
    value = read(path)
    if (value.get("schema") != "autoeditorvideo/otaku-growth-active/v1"
        or value.get("channel_id") != CHANNEL_ID
        or value.get("protected_guards",{}).get("no_render_or_upload_by_autotune") is not True):
        raise EvidenceBlocked("INVALID_PROTECTED_GROWTH_POLICY")
    return value

def editorial_advice(episode: dict, policy: dict | None = None) -> list[dict]:
    """Sinaliza problemas concretos de FUTUROS roteiros, sem reescrever canon."""
    if policy is None:
        policy = load_policy()
    if policy is None:
        return []
    rules = policy["production_rules"]
    hook = str(episode.get("hook") or "").strip()
    title = str(episode.get("title") or episode.get("titulo") or "").strip()
    script = str(episode.get("script") or episode.get("narration_script") or "").strip()
    cover = str(episode.get("cover") or episode.get("cover_text") or "").strip()
    scenes = episode.get("storyboard") or []
    warnings: list[dict] = []
    def warn(code: str, message: str):
        warnings.append({"code": code, "severity": "advisory", "message": message})
    if hook and len(_whole_words(hook)) > rules["hook"]["suggested_max_words"]:
        warn("growth_hook_long","Gancho extenso: testar promessa clara nos primeiros 1–3s sem falar mais rapido.")
    if hook and _normalize(hook).startswith((
        "hoje vamos falar","fala galera","no video de hoje","seja bem vindo",
        "bem vindos ao canal")):
        warn("growth_generic_intro","Comecar pelo conflito narrado, sem saudacao ou introducao genérica.")
    if title and not rules["title"]["preferred_characters"][0] <= len(title) <= rules["title"]["preferred_characters"][1]:
        warn("growth_title_length","Testar titulo mais claro com 12–70 caracteres; manter fatos verificaveis.")
    if title:
        loud = [w for w in title.split() if len(w)>2 and w.isupper()]
        if len(loud)>rules["title"]["max_uppercase_emphasis_words"]:
            warn("growth_title_caps","Evitar muitas palavras em caixa alta no titulo.")
    if script and "otaku multicena" in _normalize(script):
        warn("growth_spoken_brand","Nao narrar nome do canal, entregar a historia diretamente.")
    if cover and not rules["thumbnail"]["preferred_words"][0] <= len(cover.split()) <= rules["thumbnail"]["preferred_words"][1]:
        warn("growth_thumbnail_copy","Miniatura mobile: testar texto de 2 a 5 palavras e contraste forte.")
    if scenes and isinstance(scenes,list) and len(scenes)>0:
        first = scenes[0]
        if isinstance(first,dict):
            action = str(first.get("action") or first.get("visual_instruction") or "")
            if not action.strip():
                warn("growth_first_scene_no_action","Descrever acao visivel coerente com o gancho no primeiro quadro.")
    return warnings

def cli(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AutoEditorVideo crescimento, offline e sem upload")
    p.add_argument("--output", type=Path, default=ACTIVE)
    p.add_argument("--check", action="store_true",
                   help="Exigir politica atual consistente com fontes; nao salvar")
    args = p.parse_args(argv)
    api_source, recap_source = latest_sources()
    profile = build_policy(read(api_source), read(recap_source),
                           api_source=api_source, recap_source=recap_source)
    data = json.dumps(profile, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        current = args.output.read_text(encoding="utf-8") if args.output.is_file() else ""
        if current != data:
            print("[GROWTH] Politica precisa de atualizacao; nao mexemos em videos.")
            return 1
    else:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(data,encoding="utf-8")
        print("[GROWTH] Perfil de producao recalculado a partir de dados versionados.")
    return 0

if __name__=="__main__":
    try:
        raise SystemExit(cli())
    except (EvidenceBlocked,ValueError,KeyError,OSError) as exc:
        raise SystemExit("[GROWTH BLOCKED] "+str(exc)) from None
