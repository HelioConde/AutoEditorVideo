"""Offline checks of genuine single-source V7 2D mesh deformation; no media API."""
import os
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import otaku_v7_mesh_preview as mesh

ENV={
    "GITHUB_REPOSITORY":"HelioConde/AutoEditorVideo",
    "GITHUB_REF":"refs/heads/main",
    "GITHUB_EVENT_NAME":"push",
    "GITHUB_RUN_ATTEMPT":"1",
    "GITHUB_WORKFLOW":mesh.NAME,
    "OTAKU_V7_MESH_ONE_REVIEW":"1",
    "MAX_IMAGE_CALLS":"0",
}

def test_one_reserved_preview_only_never_unpauses_youtube():
    row=mesh.preflight(ENV)
    assert row["anime"]=="Death Note"
    for field,value in [
        ("MAX_IMAGE_CALLS","1"),
        ("GITHUB_RUN_ATTEMPT","2"),
        ("GITHUB_EVENT_NAME","workflow_dispatch"),
        ("GITHUB_REF","refs/heads/unsafe"),
        ("OTAKU_V7_MESH_ONE_REVIEW","0"),
    ]:
        with pytest.raises(mesh.MeshBlocked):
            mesh.preflight({**ENV,field:value})
    with pytest.raises(mesh.MeshBlocked):
        mesh.preflight({**ENV,"YOUTUBE_BR_TOKEN_JSON":"secret"})

def test_mesh_preserves_original_characters_and_has_visible_motion():
    original=Image.new("RGBA",(mesh.WIDTH,mesh.HEIGHT),(0,0,0,0))
    d=ImageDraw.Draw(original)
    d.ellipse((300,220,750,830),fill=(225,162,110,255))
    d.rectangle((300,700,800,1470),fill=(110,65,200,255))
    rgb=np.asarray(original)
    zero=mesh.deform_same_rgba(rgb,0)
    final=mesh.deform_same_rgba(rgb,mesh.SECONDS)
    move=mesh.deform_same_rgba(rgb,5)
    assert np.array_equal(zero,rgb)
    assert np.array_equal(final,rgb)
    assert not np.array_equal(move,rgb)
    a=rgb[:,:,3]>32
    b=move[:,:,3]>32
    assert (a&b).sum()/(a|b).sum()>.90
    # New pixels come from the exact original image, not independently
    # generated costumes, limbs or characters.
    assert np.any(np.abs(move.astype(np.int16)-rgb.astype(np.int16))>25)

def test_mesh_vertices_remain_small_and_temporally_consistent():
    x,y=mesh.mesh_displacement(5)
    assert x.shape==(mesh.GRID[1]+1,mesh.GRID[0]+1)
    assert y.shape==x.shape
    assert float(np.max(np.abs(x)))<30
    assert float(np.max(np.abs(y)))<30
    near=mesh.mesh_displacement(5+1/mesh.MESH_FPS)
    assert float(np.max(np.abs(x-near[0])))<4
    assert float(np.max(np.abs(y-near[1])))<4

def test_remotion_uses_frame_mesh_not_ghost_crossfade():
    motion=(ROOT/"motion-remotion/src/master-short.tsx").read_text(encoding="utf-8")
    source=(ROOT/"scripts/otaku_v7_mesh_preview.py").read_text(encoding="utf-8")
    assert "meshFrameIndex({" in motion
    assert "scene.renderMode==='mesh2d'" in motion
    assert "mode==='malha2d'?layer.meshFrames" in motion
    assert "remap(image, source_x, source_y" in source
    assert "meshFrames" in source
    assert "request_image(" not in source
    assert "youtube.videos().insert" not in source
    assert '"MAX_IMAGE_CALLS": "0"' in source
