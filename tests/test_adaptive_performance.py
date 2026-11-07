"""Exercise the offline detector on drawings with known eyes and scene cuts."""

from pathlib import Path
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from adaptive_performance import analyze_art, prepare_scene_art


def draw_face():
    image = Image.new("RGB", (200, 240), "#aabbd0")
    pen = ImageDraw.Draw(image)
    pen.ellipse((40, 16, 160, 202), fill="#da9879", outline="#6a4338", width=3)
    for x in (73, 128):
        pen.arc((x - 14, 83, x + 14, 102), 190, 340, fill="#402726", width=3)
        pen.ellipse((x - 12, 99, x + 12, 111), fill="white", outline="#704638", width=2)
        pen.ellipse((x - 4, 99, x + 4, 110), fill="#3f2d23")
    pen.line([(99, 112), (92, 139), (105, 141)], fill="#9e6951", width=2)
    pen.arc((82, 143, 118, 162), 0, 180, fill="#762e32", width=3)
    return image


def test_separate_controls_for_each_visible_face_at_different_scales(tmp_path):
    face = draw_face()
    canvas = Image.new("RGB", (650, 300), "#eee")
    canvas.paste(face.resize((176, 211)), (40, 40))
    canvas.paste(face, (366, 27))
    path = tmp_path / "group.png"
    canvas.save(path)
    scene = {
        "subject": "personagens",
        "renderMode": "master_static",
        "foreground": path.name,
        "background": path.name,
    }
    prepare_scene_art([scene], tmp_path)
    plan = scene["foregroundPerformance"]
    assert (plan["width"], plan["height"]) == canvas.size
    first, second = sorted(plan["faces"], key=lambda f: f["box"][0])
    for detected, xs in [(first, (104, 153)), (second, (439, 494))]:
        assert len(detected["eyes"]) == 2
        for (x, y, rx, ry), target in zip(detected["eyes"], xs):
            assert abs(x - target) < 4 and abs(y - 132) < 4
            assert rx > ry > 1


def test_invisible_portrait_and_object_shot_get_no_controls(tmp_path):
    art = draw_face().convert("RGBA")
    art.putalpha(0)
    path = tmp_path / "hidden.png"
    art.save(path)
    assert analyze_art(path) is None
    scene = {"subject": "objeto", "renderMode": "master_static"}
    prepare_scene_art([scene], tmp_path)
    assert "backgroundPerformance" not in scene
