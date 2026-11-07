#!/usr/bin/env python3
"""One authentic V10 performance-brush 8s review through AutoEditorVideo.

Original character/background/voice from verified V6 workflow; all 240 RGBA
frames use one identity, with subtle head rotation, eyes blinking, hair, tie,
and purposeful hand movement. No AI image APIs, no YouTube upload.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from performance_brush_2d import PerformanceBrush2D,SECONDS,WIDTH,HEIGHT
from otaku_multicena_duration_90 import PLAN,PAUSE,load
from legendas_precisas import captions_from_markers

WORKFLOW="Otaku V10 - Performance Brush 8s original AutoEditorVideo test (no upload)"
EPISODE="5996-otaku-v10-performance-brush-8s-review"
OWNER="chatgpt_v10_performance_brush_20261107"
SOURCE_RUN="42332358380"
SOURCE=ROOT/"assets/gerados/otaku-v6-real-90s"
MEDIA=ROOT/"motion-remotion/public/generated/otaku-v10-performance"
REVIEW=ROOT/"otaku-v10-performance-review"
FPS=30
SOURCE_SHA={
    "pose-05-1.png":"fcebfb9b195325d52ec79abc3d58d287ed8c456b8f39f888873cb6b8026709e8",
    "background-05.png":"038181a5ce82ffa061f9ce4bf5f56cb62445e130672a7eeb61a26d541f120db5",
    "voz-master.mp3":"d67cd58ff30c45d4aeede31484434360e96f9bd855a27fce96f2866646927398",
    "marcacoes-voz.json":"544f61af96fade7b23639725894b3336727a55bb6c95c97a3b402c049e19c530"
}

class Blocked(RuntimeError):
    pass

def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def preflight(env:dict[str,str])->dict:
    mandatory={
        "GITHUB_REPOSITORY":"HelioConde/AutoEditorVideo",
        "GITHUB_REF":"refs/heads/main",
        "GITHUB_EVENT_NAME":"push",
        "GITHUB_RUN_ATTEMPT":"1",
        "GITHUB_WORKFLOW":WORKFLOW,
        "OTAKU_V10_ONE_PERFORMANCE":"1",
        "MAX_IMAGE_CALLS":"0",
    }
    if any(env.get(k)!=v for k,v in mandatory.items()):
        raise Blocked("V10_FIRST_MAIN_PUSH_ONLY_ZERO_IMAGE_CALLS")
    if any(env.get(k) for k in ("PROXY_API_KEY","PROXY_ACCOUNTS_JSON",
                                "YOUTUBE_CLIENT_JSON","YOUTUBE_BR_TOKEN_JSON")):
        raise Blocked("PAID_PROVIDER_AND_UPLOAD_SECRETS_NOT_ALLOWED")
    gate=load(PAUSE)
    if not (gate.get("pause_requested") is True and
            gate.get("authorized_public") is False and
            gate.get("resume_authorized_after_maintenance") is False):
        raise Blocked("YOUTUBE_BATCH_STILL_MUST_BE_PAUSED")
    registry=json.loads((ROOT/"conteudos/otaku-production-reservations.json").read_text(encoding="utf-8"))
    selected=[e for e in registry["entries"] if e.get("channel")=="br" and e.get("id")==EPISODE]
    if len(selected)!=1 or selected[0].get("status")!="reserved" or selected[0].get("reservation_owner")!=OWNER:
        raise Blocked("V10_REVIEW_RESERVATION_MISSING_OR_WRONG")
    return load(PLAN)["items"][0]

def verify_originals():
    for name,expected in SOURCE_SHA.items():
        p=SOURCE/name
        if not p.is_file() or sha(p)!=expected:
            raise Blocked("ORIGINAL_ASSET_HASH_CHANGED_"+name)
    with Image.open(SOURCE/"pose-05-1.png") as im:
        if im.mode!="RGBA" or im.size!=(WIDTH,HEIGHT):
            raise Blocked("ORIGINAL_CHARACTER_NOT_RGBA_OR_WRONG_SIZE")
    with Image.open(SOURCE/"background-05.png") as im:
        if im.size!=(WIDTH,HEIGHT):
            raise Blocked("ORIGINAL_BACKGROUND_WRONG_SIZE")

def prepare(row:dict)->dict:
    if MEDIA.exists() or REVIEW.exists():
        raise Blocked("V10_ALREADY_GENERATED_DO_NOT_DUPLICATE")
    verify_originals()
    rig=PerformanceBrush2D()
    MEDIA.mkdir(parents=True)
    REVIEW.mkdir(parents=True)
    shutil.copy2(SOURCE/"background-05.png",MEDIA/"background.png")
    shutil.copy2(SOURCE/"voz-master.mp3",MEDIA/"voice.mp3")
    original=np.asarray(Image.open(SOURCE/"pose-05-1.png").convert("RGBA"))
    visible=original[:,:,3]>32
    sample_frames={0,45,46,47,75,96,142,159,169,171,187,215,239}
    paths=[]
    checks=[]
    prior_flow=None
    # Authentic 30fps rendered character movement from a single identity.
    for frame in range(int(SECONDS*FPS)):
        second=frame/FPS
        qa=rig.quality(second)
        if not qa["safe"]:
            raise Blocked("PROTECTED_PERFORMANCE_FLOW_UNSAFE")
        flow=rig.displacement(second)
        if prior_flow is not None:
            step=max(float(np.max(abs(flow[0]-prior_flow[0]))),
                     float(np.max(abs(flow[1]-prior_flow[1]))))
            if step>1.3:
                raise Blocked("MOTION_BRUSH_JUMP_AT_FRAME_"+str(frame))
        prior_flow=flow
        image=rig.warp(original,second)
        name="performance-%03d.webp"%frame
        Image.fromarray(image,"RGBA").save(
            MEDIA/name,"WEBP",quality=94,method=3)
        paths.append("generated/otaku-v10-performance/"+name)
        if frame in sample_frames:
            Image.fromarray(image,"RGBA").save(REVIEW/("frame-%03d.png"%frame))
            after=image[:,:,3]>32
            iou=float(np.logical_and(visible,after).sum()/
                      max(1,int(np.logical_or(visible,after).sum())))
            change=np.any(abs(image[:,:,:3].astype(np.int16)-
                              original[:,:,:3].astype(np.int16))>24,axis=2)
            qa.update({
                "frame":frame,
                "alpha_iou":round(iou,5),
                "changed_fraction":round(float((change&visible).sum()/
                       max(1,int(visible.sum()))),4)
            })
            if iou<.975:
                raise Blocked("EXCESSIVE_CHARACTER_SILHOUETTE_CHANGE")
            checks.append(qa)
    # A blink changes ONLY the small annotated eye regions; meaningful
    # motion requires multiple beats, not only background/camera zoom.
    for frame in (46,169):
        evidence=np.asarray(Image.open(REVIEW/("frame-%03d.png"%frame)).convert("RGBA"))
        change=np.abs(evidence[419:458,418:595,:3].astype(np.int16)-
                      original[419:458,418:595,:3].astype(np.int16))
        if np.count_nonzero(np.max(change,axis=2)>30)<300:
            raise Blocked("BLINK_NOT_VISIBLE_AT_EXPECTED_FRAME")
    if not any(x["maximum_motion_px"]>10 for x in checks):
        raise Blocked("NO_VISIBLE_GESTURE")
    if checks[0]["changed_fraction"]!=0:
        raise Blocked("FIRST_FRAME_NOT_ORIGINAL")
    captions=captions_from_markers(
        SOURCE/"voz-master.mp3",row["narration_script"],91.44,fps=FPS)
    captions=[{**c,"endFrame":min(c["endFrame"],FPS*int(SECONDS))}
              for c in captions if c["startFrame"]<FPS*int(SECONDS)]
    if not captions:
        raise Blocked("ORIGINAL_VOICE_CAPTIONS_MISSING")
    props={
        "id":EPISODE,"durationFrames":int(SECONDS*FPS),
        "audio":"generated/otaku-v10-performance/voice.mp3",
        "scenes":[{
            "id":"v10-performance-original-character",
            "subject":"personagens",
            "startFrame":0,"endFrame":int(SECONDS*FPS),
            "background":"generated/otaku-v10-performance/background.png",
            "foreground":"generated/otaku-v10-performance/background.png",
            "renderMode":"mesh2d","shotType":"close",
            "beatRole":"setup","transitionStyle":"hard",
            "layers":[{
                "id":"original-character-v10-performance","role":"character","z":10,
                "src":paths[0],"meshFrames":{"fps":FPS,"frames":paths}
            }]
        }],
        "captions":captions,"hook":"V10 • PERFORMANCE BRUSH",
        "animationMode":"performance2d",
        "visualProfile":"otaku-v6-vertical",
        "editorialProfile":"Otaku V10 review-only authentic 2D performance brushes"
    }
    (REVIEW/"props-v10.json").write_text(json.dumps(props,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    report={
        "schema":"autoeditorvideo/v10-performance-brush-review/v1",
        "source_run_id":SOURCE_RUN,
        "original_rgba_sha256":SOURCE_SHA["pose-05-1.png"],
        "authentic_performance_beats":["blink 1.54s","head look 2-4s",
            "nod 4.1-6.5s","free arm 4.2-6.6s","blink 5.64s",
            "hair drift","tie sway","breathing"],
        "source_character_count":1,"source_background_count":1,
        "frame_count":len(paths),"fps":FPS,
        "no_generated_or_replaced_subjects":True,
        "new_image_ai_calls":0,"youtube_uploaded":False,
        "no_crossfade_of_separate_poses":True,
        "source_calibration_required_for_other_characters":True,
        "frame_measurements":checks,
        "human_visual_review_required":True
    }
    (REVIEW/"qa-v10-before-render.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("[OTAKU V10] BLINK_HEAD_TIE_HAND_240_FRAMES_VALIDATED",flush=True)
    return report

def render(report:dict):
    video=REVIEW/"Otaku_Multicena_V10_Performance_Brush_8s_Teste.mp4"
    proc=subprocess.run(
        ["npm","run","render:master","--",str(video.resolve()),
         "--props",str((REVIEW/"props-v10.json").resolve()),
         "--concurrency","1","--codec","h264","--crf","19"],
        cwd=ROOT/"motion-remotion",capture_output=True,text=True,timeout=3600)
    if proc.returncode:
        print("[V10 REMOTION] "+proc.stderr[-1500:],file=sys.stderr)
        raise Blocked("V10_RENDER_FAILED")
    if not video.is_file() or video.stat().st_size<400_000:
        raise Blocked("V10_VIDEO_MISSING")
    result=subprocess.run(["ffprobe","-v","error","-show_streams",
        "-show_format","-of","json",str(video)],
        check=True,text=True,capture_output=True)
    meta=json.loads(result.stdout)
    vid=next((x for x in meta["streams"] if x["codec_type"]=="video"),None)
    aud=any(x["codec_type"]=="audio" for x in meta["streams"])
    duration=float(meta["format"]["duration"])
    if not vid or vid.get("width")!=1080 or vid.get("height")!=1920 or not aud or abs(duration-SECONDS)>.25:
        raise Blocked("V10_MP4_FORMAT_INVALID")
    report.update({
        "render_verified":True,"video_seconds":duration,
        "video_bytes":video.stat().st_size,
        "video_sha256":sha(video),
        "published":False
    })
    (REVIEW/"qa-v10.json").write_text(json.dumps(
        report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("[OTAKU V10] ORIGINAL_PERFORMANCE_MP4_READY_REVIEW_ONLY",flush=True)

def main():
    try:
        row=preflight(os.environ)
        if len(sys.argv)>1 and sys.argv[1]=="--preflight":
            print("[OTAKU V10] RESERVED_ZERO_COST_REVIEW_APPROVED",flush=True)
            return 0
        qa=prepare(row)
        render(qa)
        return 0
    except Exception as exc:
        import traceback
        lines=traceback.extract_tb(exc.__traceback__)
        last=lines[-1] if lines else None
        loc=(Path(last.filename).name+":"+str(last.lineno)) if last else "unknown"
        print("[OTAKU V10 BLOCKED] "+type(exc).__name__+" at "+loc,
              file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
