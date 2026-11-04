"""Testes offline do sistema Otaku Multicena 3.0."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import otaku_growth_v3 as growth


def episode(**updates):
    base = {
        "id": "teste-anime-01",
        "series": "Anime de teste",
        "hook": "Como uma escolha transformou a jornada desse personagem?",
        "script": (
            "Como uma escolha transformou a jornada desse personagem? "
            "O protagonista tenta resolver um problema inesperado. "
            "Seus amigos discordam da decisao e apresentam um desafio. "
            "Ele compara alternativas, descobre uma pista e decide agir. "
            "O resultado muda sua compreensao sobre o problema. "
            "Agora sera necessario lidar com as consequencias. "
            "Qual escolha voce teria feito nessa situacao? "
            "Inscreva-se para mais historias de anime!"
        ),
        "cta": "Inscreva-se para mais historias de anime!",
        "title": "Uma escolha que mudou tudo #Shorts",
        "description_youtube": "Uma decisao inesperada. #OtakuMulticena #Shorts",
    }
    base.update(updates)
    return base


def codes(result):
    return {item["code"] for item in result["issues"]}


def test_default_catalogs_are_audited_without_network_or_mutations():
    episodes = growth.read_catalogs(list(growth.DEFAULT_CATALOGS))
    report = growth.audit_batch(episodes)
    assert report["summary"]["episodes"] == 50
    assert report["summary"]["blocking_issues"] == 0
    assert len(report["episodes"]) == 50
    assert all(item["manual_review_required"] for item in report["episodes"])


def test_hook_missing_and_mismatched_block():
    missing = growth.audit_episode(episode(hook=""))
    assert "hook_missing" in codes(missing)
    other = growth.audit_episode(episode(hook="O segredo que mudou tudo"))
    assert "hook_mismatch" in codes(other)
    assert other["blocking"] > 0


def test_generic_and_lengthy_hook_are_advisories_not_guarantees():
    hook = "Hoje vamos falar sobre tudo o que mudou nessa historia de anime e seus personagens que voce precisa conhecer"
    result = growth.audit_episode(episode(hook=hook, script=hook + " " + episode()["script"]))
    assert "generic_hook" in codes(result)
    assert "hook_long" in codes(result)


def test_old_brand_and_missing_metadata_block():
    result = growth.audit_episode(episode(title="Arquivo Otaku", description_youtube=""))
    assert {"old_brand", "description_missing"} <= codes(result)


def test_detects_duplicate_hooks_and_repeated_description_templates():
    a = episode()
    b = episode(id="segundo", series="Outro anime")
    c = episode(id="terceiro", series="Mais outro anime")
    report = growth.audit_batch([a, b, c])
    assert "hook_duplicate" in codes(report["episodes"][1])
    assert "template_description" in codes(report["episodes"][2])


def test_metric_windows_compare_equal_age_only_and_preserve_null():
    report = growth.compare_metrics([
        {"platform": "YouTube", "video_id": "A", "age_hours": 1.1,
         "views": 0, "shown_in_feed": None},
        {"platform": "YouTube", "video_id": "A", "age_hours": 5.9,
         "views": 120, "engaged_views": 28},
        {"platform": "YouTube", "video_id": "B", "age_hours": 24.0,
         "views": None},
    ])
    a, b = report["videos"]
    assert a["windows"]["1"]["views"] == 0
    assert a["windows"]["1"]["shown_in_feed"] is None
    assert a["windows"]["6"]["engaged_views"] == 28
    assert a["windows"]["24"] is None
    assert b["windows"]["24"]["views"] is None
    assert b["windows"]["1"] is None


def test_rejects_invalid_metric_values_and_naive_timestamps():
    with pytest.raises(ValueError):
        growth.compare_metrics([{"platform": "yt", "video_id": "A", "age_hours": 1,
                                 "views": -1}])
    with pytest.raises(ValueError, match="fuso"):
        growth.compare_metrics([{"platform": "yt", "video_id": "A",
                                 "published_at": "2026-11-04T01:00:00",
                                 "collected_at": "2026-11-04T02:00:00",
                                 "views": 1}])


def test_cli_creates_offline_report_without_touching_video(tmp_path, capsys):
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps({"episodes": [episode()]}), encoding="utf-8")
    target = tmp_path / "audit.json"
    assert growth.main(["--catalog", str(catalog), "--saida", str(target)]) == 0
    output = json.loads(target.read_text(encoding="utf-8"))
    assert output["summary"]["episodes"] == 1
    assert output["summary"]["blocking_issues"] == 0
    assert "Relatorio" in capsys.readouterr().out
    assert growth.main(["--catalog", str(catalog), "--saida", str(target),
                        "--estrito"]) == 0


def test_cli_strict_blocks_broken_roster(tmp_path):
    catalog = tmp_path / "invalid.json"
    catalog.write_text(json.dumps({"episodes": [episode(hook="")]}), encoding="utf-8")
    assert growth.main(["--catalog", str(catalog), "--estrito"]) == 2


def test_grade_parser_supports_v3_without_turning_on_publication():
    import grade_50_shorts as grade
    args = grade.parser().parse_args([
        "--acao", "validar", "--auditar-editorial", "--exigir-gates-editoriais"
    ])
    assert args.acao == "validar"
    assert args.auditar_editorial and args.exigir_gates_editoriais
    assert not args.confirmar_publicacao
