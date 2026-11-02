"""The number of scenes must reflect story changes, not a fixed quota."""
import json
from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from planejar_cenas_dinamicas import scene_plan


def test_single_visual_idea_remains_one_scene():
    ep={"id":"curto","script":"Light permanece diante do tabuleiro. Ele observa a mesma posição com atenção."}
    plan=scene_plan(ep)
    assert plan["total_cenas"]==1
    assert plan["cenas"][0]["papel"]=="gancho"


def test_important_changes_create_more_scenes():
    ep={"id":"mudancas","script":(
       "Light entra na sala de investigação e encontra o tabuleiro. "
       "Ele tenta prever o próximo lance do adversário. "
       "Mas L percebe uma contradição na explicação de Light. "
       "Essa pista muda tudo para a equipe de investigação. "
       "Então um novo Kira aparece diante das câmeras. "
       "A investigação ganha outra direção inesperada. "
       "E você, acreditaria no plano de Light?")}
    plan=scene_plan(ep)
    assert 3 <= plan["total_cenas"] <= 5
    assert plan["total_cenas"]!=7
    assert [s["id"] for s in plan["cenas"]]==[f"{i:02}" for i in range(1,plan["total_cenas"]+1)]
    assert "Mas L" in " ".join(s["trecho_roteiro"] for s in plan["cenas"])


def test_manual_blocks_preserve_director_intent():
    blocks=["O tabuleiro está vazio.", "Mas Light revela uma pista importante.",
            "Então L muda a estratégia. E você, quem venceria?"]
    ep={"id":"editor","script":" ".join(blocks),"blocos_visuais":blocks}
    plan=scene_plan(ep,duration=27)
    assert plan["total_cenas"]==3
    assert plan["metodo"]=="roteirista"
    assert plan["cenas"][-1]["fim_estimado_s"]==27


def test_manual_blocks_must_not_change_narration():
    with pytest.raises(ValueError,match="preservar"):
        scene_plan({"script":"Um começo. Um final.","blocos_visuais":["Um começo."]})


def test_paragraphs_provide_intentional_boundary():
    plan=scene_plan({"script":"Uma cena com foco no tabuleiro.\n\nOutra cena mostrando o corredor."})
    assert plan["total_cenas"]==2


def test_all_five_episode_scripts_generate_variable_plans():
    manifest=json.loads((ROOT/'conteudos'/'testes-animados-5.json').read_text(encoding='utf-8'))
    plans=[scene_plan(e) for e in manifest['episodes']]
    assert len(plans)==5
    assert all(p['total_cenas']>=1 for p in plans)
    for e,p in zip(manifest['episodes'],plans):
        restored=" ".join(c['trecho_roteiro'] for c in p['cenas'])
        assert restored==e['script']
        assert not p['publicacao_automatica']
        assert all(c['revisao_visual_pendente'] for c in p['cenas'])


def test_no_network_or_upload():
    source=(ROOT/'scripts'/'planejar_cenas_dinamicas.py').read_text()
    assert "requests.post" not in source and "videos().insert" not in source
