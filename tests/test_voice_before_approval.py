"""Narration must be creatable before any visual scene is approved."""
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import renderizar_master_remotion as render


def test_voice_only_does_not_validate_or_render_unapproved_images(tmp_path,monkeypatch):
    monkeypatch.setattr(render,"production_storyboard",lambda *args,**kwargs:tmp_path/"dummy.json")
    monkeypatch.setattr(render,"read_storyboard",lambda path:{"id":"ep-test","scenes":[{"id":"01"}]})
    monkeypatch.setattr(render,"select_episode",lambda name:{"script":"A historia comeca"})
    def bad_validate(*args,**kwargs):
        raise AssertionError("Image QA must not run while creating voice only")
    monkeypatch.setattr(render,"validate_scenes",bad_validate)
    monkeypatch.setattr(render,"OUT",tmp_path)
    calls=[]
    def mocked_voice(ep,folder,*,create):
        calls.append((ep["script"],folder,create))
        return folder/"voz-master.mp3",folder/"legendas.ass"
    monkeypatch.setattr(render,"ensure_voice",mocked_voice)
    # Mocked MP3 does not exist; isolate duration probe while retaining the 60s gate.
    monkeypatch.setattr(render,"audio_duration",lambda path: 42.0)
    assert render.main(["--id","ep-test","--somente-voz","--criar-voz"])==0
    assert calls==[("A historia comeca",tmp_path/"ep-test",True)]


def test_voice_only_cannot_also_render(tmp_path,monkeypatch):
    import pytest
    monkeypatch.setattr(render,"production_storyboard",lambda *args,**kwargs:tmp_path/"dummy.json")
    monkeypatch.setattr(render,"read_storyboard",lambda path:{"id":"ep-test","scenes":[{"id":"01"}]})
    monkeypatch.setattr(render,"OUT",tmp_path)
    with pytest.raises(ValueError,match="nao pode renderizar"):
        render.main(["--id","ep-test","--somente-voz","--renderizar"])
