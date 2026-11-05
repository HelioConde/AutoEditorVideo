"""No network, secrets, audio generation, image calls, YouTube upload or video render."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import production_reservations as reservations
import otaku_dual_5011_cloud as dual


def test_reservations_are_recorded_before_automation():
    rows=reservations.load()
    assert reservations.get_entry('br','5009-overgeared',rows)['status']=='in_production'
    assert reservations.get_entry('br','5010-aoashi',rows)['status']=='in_production'
    assert reservations.get_entry('br','5008-firefly-wedding',rows)['status']=='published'
    assert reservations.get_entry('br','5005-bleach-thousand-year-blood-war',rows)['status']=='existing_assets_unverified'
    for language in ('br','en'):
        assert reservations.assert_reserved(language,dual.ID,dual.OWNER,data=rows)['publication_target']=='private'
    assert reservations.next_available('br',rows)=='5012-solo-leveling'


@pytest.mark.parametrize('id',[
    '5001-black-clover','5002-apothecary-diaries','5003-cyberpunk-edgerunners',
    '5004-jojo-steel-ball-run','5005-bleach-thousand-year-blood-war',
    '5006-blue-box','5007-tokyo-revengers','5008-firefly-wedding',
    '5009-overgeared','5010-aoashi',
])
def test_produced_active_and_local_unverified_not_reselected(id):
    with pytest.raises(ValueError,match='ALREADY_PUBLISHED_OR_RESERVED'):
        reservations.assert_reserved('br',id,dual.OWNER)


def test_unauthorized_reservation_fails_closed():
    with pytest.raises(ValueError,match='ALREADY_PUBLISHED_OR_RESERVED'):
        reservations.assert_reserved('en','5011-gachiakuta','other_owner')
    with pytest.raises(ValueError,match='NOT_RESERVED'):
        reservations.assert_reserved('br','5012-solo-leveling',dual.OWNER)


def valid_env():
    return {
        'GITHUB_REPOSITORY':'HelioConde/AutoEditorVideo',
        'GITHUB_REF':'refs/heads/main','GITHUB_EVENT_NAME':'push',
        'GITHUB_RUN_ATTEMPT':'1','IMAGE_MODEL':'gpt-image-2',
        'PROXY_API_KEY':'synthetic-example-value',
    }


def test_dual_pilot_passes_strict_budget_and_channel_identity():
    dual.preflight(valid_env(),21)
    data=json.loads(dual.EN_MANIFEST.read_text(encoding='utf-8'))
    assert data['target_channel_id']==dual.EN_CHANNEL
    assert data['episodes'][0]['id']==dual.ID
    assert len(data['episodes'][0]['script'].split())>=50
    assert not data['episodes'][0].get('scenes')  # reuse the BR scene layers, avoid paid duplicate


@pytest.mark.parametrize('changes,calls,code',[
    ({'GITHUB_REF':'refs/heads/feature'},21,'MAIN_ONE_SHOT_ONLY'),
    ({'GITHUB_EVENT_NAME':'workflow_dispatch'},21,'MAIN_ONE_SHOT_ONLY'),
    ({'GITHUB_RUN_ATTEMPT':'2'},21,'NO_RERUN_ALLOWED'),
    ({'IMAGE_MODEL':'gpt-image-1.5'},21,'WRONG_IMAGE_MODEL'),
    ({'PROXY_API_KEY':''},21,'MISSING_PROTECTED_PROXY_KEY'),
    ({},0,'IMAGE_CALL_BUDGET_MUST_EQUAL_21'),
    ({},22,'IMAGE_CALL_BUDGET_MUST_EQUAL_21'),
])
def test_no_secrets_or_unauthorized_call_ever_starts(changes,calls,code):
    with pytest.raises(dual.CloudBlocked,match=code):
        dual.preflight(valid_env()|changes,calls)


def test_no_one_channel_artifact_on_partial_failure(tmp_path,monkeypatch):
    monkeypatch.setattr(dual,'ROOT',tmp_path)
    monkeypatch.setattr(dual,'DEST',tmp_path/'cloud-br-en-review-5011')
    with pytest.raises(dual.CloudBlocked,match='MISSING_COVER_OR_QA'):
        dual.package_both()
    assert not dual.DEST.exists()


def test_no_upload_flags_or_private_state_export():
    source=(ROOT/'scripts'/'otaku_dual_5011_cloud.py').read_text(encoding='utf-8')
    assert "fluxo_unico_short.py" in source
    assert "renderizar_shorts_en.py" in source
    assert "'--publicar'" not in source
    assert "youtube.videos().insert(" not in source
    assert "shutil.copytree" not in source
    assert "'--tentativas','1'" in source
