"""Regressões offline para o crescimento adaptativo do Otaku Multicena.

Nao usa API, provider de imagem, token, video, upload ou dados inventados.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import otaku_growth_autotune as tune
import otaku_growth_v3 as growth
import roteiro_para_storyboard as storyboard
import planejador_editorial as planner


def test_real_snapshots_keep_time_windows_distinct():
    api = tune.read(tune.API_SOURCE)
    recap = tune.read(tune.RECAP_SOURCE)
    metrics = tune.evidence(api, recap)
    assert metrics["channel_id"] == tune.CHANNEL_ID
    assert metrics["views_analytics_api_period"] == 7535
    assert metrics["api_period"] == ["2026-10-09", "2026-11-07"]
    assert metrics["recap_week"] == ["2026-10-26", "2026-11-01"]
    assert metrics["rolling_28d_exact_dates"] is None
    assert metrics["recap_week_likes"] == 58
    assert metrics["views_vs_swiped_28d_percent"] == 34.8
    assert metrics["ignored_28d_percent"] == 65.2
    assert len(metrics["top_five_from_separate_28d_window"]) == 5


def test_fresh_policy_protects_existing_media_and_only_proposes_pilots():
    p = tune.build_policy(tune.read(tune.API_SOURCE),
                          tune.read(tune.RECAP_SOURCE))
    assert p["priority"] == "test_hook_first_3s"
    assert p["hypothesis_not_proven"] is True
    assert p["production_rules"]["captions"]["max_words_per_phrase"] == 3
    assert p["production_rules"]["narration"]["engine"] == "edge-tts"
    assert p["production_rules"]["visual"]["preserve_named_character_identity_anchors"] is True
    assert p["production_rules"]["visual"]["avoid_jump_cut_flicker"] is True
    assert p["production_rules"]["duration"]["do_not_force_a_global_duration_from_one_snapshot"]
    assert p["measurement_protocol"]["minimum_completed_per_variant_before_promotion"] >= 5
    assert not p["measurement_protocol"]["automatic_promotion_without_comparable_evidence"]
    assert all(p["protected_guards"][x] is True for x in (
        "no_render_or_upload_by_autotune", "do_not_edit_existing_public_videos",
        "no_image_api_calls", "keep_creator_pause_and_reservation_registry",
    ))


def test_fails_closed_on_mismatched_channels_or_unsupported_viewed_pct():
    api = tune.read(tune.API_SOURCE)
    recap = tune.read(tune.RECAP_SOURCE)
    recap["canal_id"] = "WRONG"
    with pytest.raises(tune.EvidenceBlocked, match="WRONG_RECAP_CHANNEL"):
        tune.evidence(api, recap)
    recap = tune.read(tune.RECAP_SOURCE)
    recap["ultimos_28_dias"]["decisao_assistir"]["ignoraram_percentual"] = 0
    with pytest.raises(tune.EvidenceBlocked, match="VIEWED_VS_SWIPED"):
        tune.evidence(api, recap)


def test_growth_advice_on_new_titles_hooks_and_original_thumbnail():
    p = tune.build_policy(tune.read(tune.API_SOURCE),
                          tune.read(tune.RECAP_SOURCE))
    episode = {
        "id": "teste-canon",
        "series": "Anime",
        "title": "LIGHT SURPRESA INACREDITAVEL IMPOSSIVEL EXCLUSIVO !!!!",
        "hook": "Hoje vamos falar sobre um monte de acontecimentos que aparecem em um anime e deveriam deixar todos muito curiosos e surpresos",
        "script": "Otaku Multicena, hoje vamos falar da historia deste anime.",
        "cover": "UMA FRASE DE CAPA MUITO LONGA QUE NINGUEM VAI LER",
        "storyboard": [{"action": ""}]
    }
    advice = tune.editorial_advice(episode, p)
    codes = {a["code"] for a in advice}
    assert {"growth_hook_long", "growth_generic_intro", "growth_spoken_brand",
            "growth_title_caps", "growth_thumbnail_copy",
            "growth_first_scene_no_action"} <= codes
    assert all(a["severity"] == "advisory" for a in advice)


def test_growth_advice_is_available_in_real_editorial_audit_without_blocking():
    ep = {
        "id": "test-1", "series": "Death Note",
        "hook": "Hoje vamos falar de um grande segredo narrativo que muda tudo nesta aventura longa demais",
        "script": ("Hoje vamos falar de um grande segredo narrativo que muda tudo nesta aventura longa demais. "
                   "Personagens fazem escolhas e o roteiro explica as consequencias."),
        "title": "Segredo de Death Note", "cover": "O SEGREDO DO CADERNO",
        "description_youtube": "Análise e história. #OtakuMulticena",
    }
    report = growth.audit_episode(ep)
    assert any(x["code"] == "growth_generic_intro" for x in report["issues"])
    assert all(x["severity"] == "advisory"
               for x in report["issues"] if x["code"].startswith("growth_"))


def test_first_storyboard_visual_directs_real_narrative_action_not_fake_animation():
    episode = {"series": "Death Note", "character": "Light Yagami",
               "background": "quarto do personagem", "object": "caderno"}
    subject, shot, prompt = storyboard.framing(episode, "gancho", 0, 0, 2)
    assert subject == "personagens"
    assert "EXPLICITAMENTE NARRADA" in shot
    assert "Light Yagami" in prompt
    assert "quarto" in prompt
    assert "NÃO desenhar texto" in prompt


def test_planner_receives_active_policy_without_upload_or_false_duration():
    result = planner.audit_plan({
        "serie": "Death Note",
        "titulo": "O segredo que Light não percebeu",
        "gancho_primeiros_segundos": "Qual era a pista?",
        "roteiro_melhorado": ("Qual era a pista? "
                              "L percebeu a reação, mas a história mostra outro detalhe."),
        "cenas": [{"tipo": "acao", "action": "L mostra um objeto"}]
    })
    assert result["growth_priority"] == "test_hook_first_3s"
    assert result["production_experiment_settings"]["max_caption_words"] == 3
    assert result["production_experiment_settings"]["narration_engine"] == "edge-tts"


def test_latest_known_sources_reject_unrecognized_schema_and_future_date(tmp_path, monkeypatch):
    snap = tmp_path / "dados/metricas-redes"
    snap.mkdir(parents=True)
    api = tune.read(tune.API_SOURCE)
    recap = tune.read(tune.RECAP_SOURCE)
    default_api = snap / "2026-11-08-youtube-api-vidiq.json"
    default_recap = snap / "2026-11-08-youtube-recap-26out-01nov.json"
    default_api.write_text(json.dumps(api), encoding="utf-8")
    default_recap.write_text(json.dumps(recap), encoding="utf-8")
    monkeypatch.setattr(tune, "API_SOURCE", default_api)
    monkeypatch.setattr(tune, "RECAP_SOURCE", default_recap)
    fake = snap / "2026-11-09-youtube-api-vidiq.json"
    fake.write_text(json.dumps({"esquema": "other","coleta_em":"2026-11-09"}),
                    encoding="utf-8")
    assert tune.latest_sources() == (default_api, default_recap)


def test_script_never_publishes_or_reads_credentials():
    source = (ROOT / "scripts/otaku_growth_autotune.py").read_text(encoding="utf-8")
    for forbidden in ("videos().insert", "videos().update",
                      "PROXY_API_KEY", "YOUTUBE_CLIENT_JSON",
                      "subprocess.run(", "requests.get("):
        assert forbidden not in source
