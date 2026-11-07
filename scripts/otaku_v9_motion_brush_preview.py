#!/usr/bin/env python3
"""One 8s V9 mask-guided Motion Brush 2D review with original AutoEditorVideo.

No paid AI calls, no YouTube, no new artwork. Real anchored+moving pins drive
CPU bounded mask-guided displacement; Remotion combines RGBA and background.
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
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from otaku_multicena_duration_90 import PLAN,PAUSE,load
from legendas_precisas import captions_from_markers
from motion_brush_2d import MotionBrush2D,load_config,DURATION as SECONDS,WIDTH,HEIGHT

WORKFLOW="Otaku V9 - Motion Brush 2D 8s real AutoEditorVideo review (no upload)"
EPISODE="5997-otaku-v9-motion-brush-8s-review"
OWNER="chatgpt_v9_motion_brush_20261107"
SOURCE_RUN="42332358380"
SOURCE=ROOT/"assets/gerados/otaku-v6-real-90s"
MEDIA=ROOT/"motion-remotion/public/generated/otaku-v9-brush"
REVIEW=ROOT/"otaku-v9-motion-brush-review"
VIDEO_FPS=30
BRUSH_FPS=30
SHA={
 "pose-05-1.png":"fcebfb9b195325d52ec79abc3d58d287ed8c456b8f39f888873cb6b8026709e8",
 "background-05.png":"038181a5ce82ffa061f9ce4bf5f56cb62445e130672a7eeb61a26d541f120db5",
 "voz-master.mp3":"d67cd58ff30c45d4aeede31484434360e96f9bd855a27fce96f2866646927398",
 "marcacoes-voz.json":"544f61af96fade7b23639725894b3336727a55bb6c95c97a3b402c049e19c530",
}

class Blocked(RuntimeError):
    pass

def digest(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def preflight(env:dict[str,str])->dict:
    required={
      "GITHUB_REPOSITORY":"HelioConde/AutoEditorVideo",
      "GITHUB_REF":"refs/heads/main",
      "GITHUB_EVENT_NAME":"push",
      "GITHUB_RUN_ATTEMPT":"1",
      "GITHUB_WORKFLOW":WORKFLOW,
      "OTAKU_V9_BRUSH_REVIEW":"1",
      "MAX_IMAGE_CALLS":"0"
    }
    if any(env.get(k)!=v for k,v in required.items()):
        raise Blocked("ONLY_RESERVED_V9_FIRST_MAIN_PUSH_ZERO_IMAGE_CALLS")
    if any(env.get(x) for x in ("PROXY_API_KEY","PROXY_ACCOUNTS_JSON",
                               "YOUTUBE_BR_TOKEN_JSON","YOUTUBE_CLIENT_JSON")):
        raise Blocked("NO_GENERATION_OR_YOUTUBE_SECRETS_PERMITTED")
    gate=load(PAUSE)
    if not (gate.get("pause_requested") is True and
            gate.get("authorized_public") is False and
            gate.get("resume_authorized_after_maintenance") is False):
        raise Blocked("PRODUCTION_QUEUE_MUST_REMAIN_PAUSED")
    registry=json.loads((ROOT/"conteudos/otaku-production-reservations.json").read_text(encoding="utf-8"))
    matches=[e for e in registry["entries"] if e.get("channel")=="br" and e.get("id")==EPISODE]
    if len(matches)!=1 or matches[0].get("status")!="reserved" or matches[0].get("reservation_owner")!=OWNER:
        raise Blocked("V9_REVIEW_RESERVATION_INVALID")
    return load(PLAN)["items"][0]

def verify_original_artifacts():
    for name,expected in SHA.items():
        path=SOURCE/name
        if not path.is_file() or digest(path)!=expected:
            raise Blocked("ORIGINAL_ARTIFACT_HASH_MISMATCH_"+name)
    with Image.open(SOURCE/"pose-05-1.png") as original:
        if original.mode!="RGBA" or original.size!=(WIDTH,HEIGHT):
            raise Blocked("WRONG_CHARACTER_ALPHA_OR_SIZE")
    with Image.open(SOURCE/"background-05.png") as original:
        if original.size!=(WIDTH,HEIGHT):
            raise Blocked("WRONG_BACKGROUND_SIZE")

def build(row:dict)->dict:
    if MEDIA.exists() or REVIEW.exists():
        raise Blocked("V9_ALREADY_RENDERED_DO_NOT_DUPLICATE")
    verify_original_artifacts()
    config_path=ROOT/"config/otaku-v9-motion-brush.json"
    config=load_config(config_path)
    animator=MotionBrush2D(config)
    MEDIA.mkdir(parents=True)
    REVIEW.mkdir(parents=True)
    shutil.copy2(SOURCE/"background-05.png",MEDIA/"background.png")
    shutil.copy2(SOURCE/"voz-master.mp3",MEDIA/"voice.mp3")
    shutil.copy2(config_path,REVIEW/"brush-config.json")
    original=np.asarray(Image.open(SOURCE/"pose-05-1.png").convert("RGBA"))
    alpha=original[:,:,3]>32
    debug=animator.debug_masks(original)
    Image.fromarray(debug,"RGBA").save(REVIEW/"painted-motion-and-protection-regions.png")
    checks=[]
    paths=[]
    keyframes=(0,48,72,105,135,159,180,210,239)
    for n in range(BRUSH_FPS*SECONDS):
        second=n/BRUSH_FPS
        current=animator.warp(original,second)
        name=f"brush-{n:03d}.webp"
        Image.fromarray(current,"RGBA").save(MEDIA/name,"WEBP",quality=95,method=3)
        paths.append("generated/otaku-v9-brush/"+name)
        if n in keyframes:
            Image.fromarray(current,"RGBA").save(REVIEW/f"frame-{n:03d}.png")
            moved_mask=current[:,:,3]>32
            iou=float(np.logical_and(alpha,moved_mask).sum()/
                      max(1,int(np.logical_or(alpha,moved_mask).sum())))
            changed=np.any(np.abs(original[:,:,:3].astype(np.int16)-
                                 current[:,:,:3].astype(np.int16))>22,axis=2)
            fraction=float((changed&alpha).sum()/max(1,int(alpha.sum())))
            q=animator.quality(second)
            # Face is an explicit zero-motion protected zone. Pixel-perfect
            # preservation guards against the twisting seen in Puppet Pins.
            face=(slice(447,500),slice(477,537))
            static_face=bool(np.array_equal(current[face],original[face]))
            check={"frame":n,"second":round(second,3),
                  "alpha_iou":round(iou,4),
                  "visible_pixel_change":round(fraction,4),
                  "face_pixels_unchanged":static_face,**q}
            checks.append(check)
            if not static_face:
                raise Blocked("PROTECTED_FACE_WARPED")
            if not q["within_safe_bounds"]:
                raise Blocked("BRUSH_STRAIN_LIMIT_EXCEEDED")
            if iou<float(config["limits"]["min_alpha_iou"]):
                raise Blocked("BRUSH_ALPHA_SHAPE_UNSAFE")
    if checks[0]["visible_pixel_change"]!=0 or checks[0]["alpha_iou"]!=1:
        raise Blocked("V9_IDENTITY_FRAME_MODIFIED")
    if max(c["visible_pixel_change"] for c in checks)<.006:
        raise Blocked("BRUSH_MOTION_TOO_WEAK_TO_EVALUATE")
    captions=captions_from_markers(SOURCE/"voz-master.mp3",
                                   row["narration_script"],91.44,fps=VIDEO_FPS)
    if not captions:
        raise Blocked("ORIGINAL_CAPTIONS_MISSING")
    captions=[{**c,"endFrame":min(c["endFrame"],SECONDS*VIDEO_FPS)}
              for c in captions if c["startFrame"]<SECONDS*VIDEO_FPS]
    props={
      "id":EPISODE,"durationFrames":SECONDS*VIDEO_FPS,
      "audio":"generated/otaku-v9-brush/voice.mp3",
      "scenes":[{
        "id":"v9-brush","subject":"personagens",
        "startFrame":0,"endFrame":SECONDS*VIDEO_FPS,
        "background":"generated/otaku-v9-brush/background.png",
        "foreground":"generated/otaku-v9-brush/background.png",
        "renderMode":"mesh2d","shotType":"close",
        "beatRole":"setup","transitionStyle":"hard",
        "layers":[{
            "id":"original-character-motion-brush","role":"character","z":10,
            "src":paths[0],"meshFrames":{"fps":BRUSH_FPS,"frames":paths}
        }]
      }],
      "captions":captions,"hook":"V9 • MOTION BRUSH",
      "animationMode":"brush2d",
      "visualProfile":"otaku-v6-vertical",
      "editorialProfile":"Otaku Multicena V9 bounded motion-brush masks review only"
    }
    (REVIEW/"props-v9.json").write_text(json.dumps(props,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    report={
      "schema":"autoeditorvideo/motion-brush-v9-preview/v1",
      "method":"editable polygon masks and directional flow with feathered protect zones",
      "NOT_runway_motion_brush_or_generative_video":True,
      "source_run_id":SOURCE_RUN,
      "source_png_sha256":SHA["pose-05-1.png"],
      "brush_regions":[b["id"] for b in config["brushes"]],
      "protected_regions":[p["id"] for p in config["protections"]],
      "review_seconds":SECONDS,"motion_frames":len(paths),
      "motion_fps":BRUSH_FPS,"output_fps":VIDEO_FPS,
      "all_frames_from_same_png":True,
      "original_background_separate":True,
      "new_image_ai_calls":0,"youtube_uploads":0,
      "no_full_body_crossfade":True,
      "metrics":checks,"human_visual_review_required":True,
      "limitations":"Mask-guided pixel warping cannot reveal missing sleeve/skin, rotate 3D body, or perform full character motion without extra layers or generative image-to-video."
    }
    (REVIEW/"qa-v9-pre-render.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("[OTAKU V9] MOTION_BRUSH_MASK_FRAMES_240_READY",flush=True)
    return report

def render(report:dict):
    dest=REVIEW/"Otaku_Multicena_V9_Motion_Brush_8s_Teste.mp4"
    proc=subprocess.run(["npm","run","render:master","--",str(dest.resolve()),
       "--props",str((REVIEW/"props-v9.json").resolve()),
       "--concurrency","1","--codec","h264","--crf","19"],
       cwd=ROOT/"motion-remotion",text=True,capture_output=True,timeout=3600)
    if proc.returncode:
        print("[OTAKU V9] REMOTION_STDERR: "+proc.stderr[-1700:],file=sys.stderr)
        raise Blocked("V9_REMOTION_RENDER_FAILED")
    if not dest.is_file() or dest.stat().st_size<400_000:
        raise Blocked("V9_VIDEO_EMPTY")
    probed=subprocess.run(["ffprobe","-v","error","-show_streams",
         "-show_format","-of","json",str(dest)],capture_output=True,
         text=True,check=True)
    info=json.loads(probed.stdout)
    streams=info["streams"]
    video=next((x for x in streams if x["codec_type"]=="video"),None)
    if not video or video.get("width")!=1080 or video.get("height")!=1920 or (
        not any(x["codec_type"]=="audio" for x in streams)):
        raise Blocked("V9_AV_STREAM_INVALID")
    duration=float(info["format"]["duration"])
    if abs(duration-SECONDS)>.25:
        raise Blocked("V9_DURATION_NOT_8_SECONDS")
    report.update({"video_file":dest.name,"duration_seconds":duration,
                   "video_sha256":digest(dest),"video_bytes":dest.stat().st_size,
                   "render_verified":True,"ready_to_publish":False})
    (REVIEW/"qa-v9.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("[OTAKU V9] MOTION_BRUSH_MP4_READY_NO_YOUTUBE",flush=True)

def main()->int:
    try:
        row=preflight(os.environ)
        if len(sys.argv)>1 and sys.argv[1]=="--preflight":
            print("[OTAKU V9] RESERVED_PIN_PREVIEW_ONLY_ZERO_IMAGE_CALLS")
            return 0
        report=build(row)
        print("[OTAKU V9] 240 BRUSH-MASK FRAMES GENERATED",flush=True)
        render(report)
        return 0
    except Exception as exc:
        print("[OTAKU V9 BLOCKED] "+
              (str(exc) if isinstance(exc,Blocked) else type(exc).__name__),
              file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
