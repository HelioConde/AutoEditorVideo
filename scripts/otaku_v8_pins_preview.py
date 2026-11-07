#!/usr/bin/env python3
"""One 8s V8 Pin/Puppet Warp review made with the original AutoEditorVideo.

No paid AI calls, no YouTube, no new artwork. Real anchored+moving pins drive
CPU inverse-TPS deformable mesh; Remotion composes independent RGBA/background.
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
from puppet_pin_warp import PINS,pin_positions,warp_rgba,SECONDS,WIDTH,HEIGHT

WORKFLOW="Otaku V8 - Puppet Pin 2D 8s real AutoEditorVideo review (no upload)"
EPISODE="5998-otaku-v8-pins-8s-review"
OWNER="chatgpt_otaku_v8_pin_warp_20261107"
SOURCE_RUN="42332358380"
SOURCE=ROOT/"assets/gerados/otaku-v6-real-90s"
MEDIA=ROOT/"motion-remotion/public/generated/otaku-v8-pins"
REVIEW=ROOT/"otaku-v8-pins-review"
VIDEO_FPS=30
PIN_FPS=15
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
      "OTAKU_V8_PIN_REVIEW":"1",
      "MAX_IMAGE_CALLS":"0"
    }
    if any(env.get(k)!=v for k,v in required.items()):
        raise Blocked("ONLY_RESERVED_V8_FIRST_MAIN_PUSH_ZERO_IMAGE_CALLS")
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
        raise Blocked("V8_REVIEW_RESERVATION_INVALID")
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

def draw_pin_debug(original:Image.Image,second:float,filename:Path):
    img=Image.new("RGBA",(WIDTH,HEIGHT),(12,16,28,255))
    img.alpha_composite(original)
    draw=ImageDraw.Draw(img)
    points=pin_positions(second)
    for name,(x,y) in points.items():
        ox,oy=PINS[name]
        fixed=abs(x-ox)+abs(y-oy)<.01
        if name.startswith("fixed_border_"):continue
        color=(55,226,164,255) if fixed else (255,109,103,255)
        draw.ellipse((x-8,y-8,x+8,y+8),fill=color,outline=(0,0,0,255),width=2)
        if not fixed:
            draw.line((ox,oy,x,y),fill=(255,205,92,255),width=3)
            draw.ellipse((ox-3,oy-3,ox+3,oy+3),fill=(255,205,92,255))
    img.thumbnail((600,900),Image.Resampling.LANCZOS)
    img.save(filename)

def build(row:dict)->dict:
    if MEDIA.exists() or REVIEW.exists():
        raise Blocked("V8_ALREADY_RENDERED_DO_NOT_DUPLICATE")
    verify_original_artifacts()
    MEDIA.mkdir(parents=True)
    REVIEW.mkdir(parents=True)
    shutil.copy2(SOURCE/"background-05.png",MEDIA/"background.png")
    shutil.copy2(SOURCE/"voz-master.mp3",MEDIA/"voice.mp3")
    source_img=Image.open(SOURCE/"pose-05-1.png").convert("RGBA")
    original=np.asarray(source_img)
    mask=original[:,:,3]>32
    snapshots=[]
    paths=[]
    checks=[]
    for n in range(PIN_FPS*SECONDS):
        seconds=n/PIN_FPS
        warped=warp_rgba(original,seconds)
        filename=f"pin-{n:03d}.webp"
        Image.fromarray(warped,"RGBA").save(MEDIA/filename,"WEBP",lossless=True,method=3)
        paths.append("generated/otaku-v8-pins/"+filename)
        if n in (0,30,60,75,90,119):
            Image.fromarray(warped,"RGBA").save(REVIEW/f"frame-{n:03d}.png")
            warped_mask=warped[:,:,3]>32
            alpha_iou=float(np.logical_and(mask,warped_mask).sum()/
                      max(1,int(np.logical_or(mask,warped_mask).sum())))
            changed=np.any(np.abs(original[:,:,:3].astype(np.int16)-
                                 warped[:,:,:3].astype(np.int16))>25,axis=2)
            fraction=float((changed&mask).sum()/max(1,int(mask.sum())))
            checks.append({"frame":n,"second":round(seconds,3),
                           "alpha_iou":round(alpha_iou,4),
                           "visible_pixel_change":round(fraction,4)})
        if n in (0,60,90):
            draw_pin_debug(Image.fromarray(warped,"RGBA"),seconds,
                           REVIEW/f"pin-controls-{n:03d}.png")
    if checks[0]["visible_pixel_change"]!=0 or checks[0]["alpha_iou"]!=1:
        raise Blocked("PIN_START_FRAME_CHANGED")
    if min(x["alpha_iou"] for x in checks)<.90:
        raise Blocked("PIN_DEFORMATION_TEAR_OR_SCALE")
    if max(x["visible_pixel_change"] for x in checks)<.10:
        raise Blocked("PIN_MOTION_NOT_VISIBLE")
    # Hard gate: the anchors are mathematically fixed at all sampled times.
    for t in (0,2,4,5,7,8):
        current=pin_positions(t)
        for name,source in PINS.items():
            if name.startswith("fixed_border_") or name in (
                "hip_left","hip_right","belt","foot_left","foot_right"):
                if abs(current[name][0]-source[0])+abs(current[name][1]-source[1])>1e-8:
                    raise Blocked("PIN_FIXED_ANCHOR_MOVED")
    captions=captions_from_markers(SOURCE/"voz-master.mp3",
                                  row["narration_script"],91.44,fps=VIDEO_FPS)
    if not captions:
        raise Blocked("CACHED_VOICE_CAPTIONS_MISSING")
    captions=[{**entry,"endFrame":min(entry["endFrame"],SECONDS*VIDEO_FPS)}
              for entry in captions if entry["startFrame"]<SECONDS*VIDEO_FPS]
    props={
       "id":EPISODE,"durationFrames":SECONDS*VIDEO_FPS,
       "audio":"generated/otaku-v8-pins/voice.mp3",
       "scenes":[{
           "id":"v8-puppet-pin","subject":"personagens",
           "startFrame":0,"endFrame":SECONDS*VIDEO_FPS,
           "background":"generated/otaku-v8-pins/background.png",
           "foreground":"generated/otaku-v8-pins/background.png",
           "renderMode":"mesh2d","shotType":"close","beatRole":"setup",
           "transitionStyle":"hard",
           "layers":[{"id":"single-identity-pin-deform","role":"character","z":10,
                      "src":paths[0],"meshFrames":{"fps":PIN_FPS,"frames":paths}}]
       }],
       "captions":captions,"hook":"V8 • PUPPET PINS",
       "animationMode":"pins2d","visualProfile":"otaku-v6-vertical",
       "editorialProfile":"Otaku Multicena V8 pinned deformable mesh review only"
    }
    (REVIEW/"props-v8.json").write_text(
        json.dumps(props,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    report={
      "method":"anchored movable artist pins + inverse TPS 2D warp",
      "source_run_id":SOURCE_RUN,"source_png_sha256":SHA["pose-05-1.png"],
      "pin_count":len(PINS),
      "fixed_anchor_names":[k for k in PINS if k.startswith("fixed_border_") or k in (
          "hip_left","hip_right","belt","foot_left","foot_right")],
      "deformation_preview_seconds":SECONDS,"mesh_frame_rate":PIN_FPS,
      "output_frame_rate":VIDEO_FPS,"all_frames_from_one_png":True,
      "two_full_body_crossfading":False,"original_background_separate":True,
      "new_paid_image_calls":0,"youtube_uploads":0,
      "sample_metrics":checks,
      "reviewed_by_human":False,
      "limit":"Puppet pins deform existing visible pixels; do not reveal hidden parts, cannot produce true mouth shapes or independently repainted hand anatomy."
    }
    return report

def render(report:dict):
    dest=REVIEW/"Otaku_Multicena_V8_Puppet_Pins_8s_Teste.mp4"
    proc=subprocess.run(["npm","run","render:master","--",str(dest.resolve()),
       "--props",str((REVIEW/"props-v8.json").resolve()),
       "--concurrency","1","--codec","h264","--crf","19"],
       cwd=ROOT/"motion-remotion",text=True,capture_output=True,timeout=3600)
    if proc.returncode:
        print("[OTAKU V8] REMOTION_STDERR: "+proc.stderr[-1700:],file=sys.stderr)
        raise Blocked("V8_REMOTION_RENDER_FAILED")
    if not dest.is_file() or dest.stat().st_size<400_000:
        raise Blocked("V8_VIDEO_EMPTY")
    probed=subprocess.run(["ffprobe","-v","error","-show_streams",
         "-show_format","-of","json",str(dest)],capture_output=True,
         text=True,check=True)
    info=json.loads(probed.stdout)
    streams=info["streams"]
    video=next((x for x in streams if x["codec_type"]=="video"),None)
    if not video or video.get("width")!=1080 or video.get("height")!=1920 or (
        not any(x["codec_type"]=="audio" for x in streams)):
        raise Blocked("V8_AV_STREAM_INVALID")
    duration=float(info["format"]["duration"])
    if abs(duration-SECONDS)>.25:
        raise Blocked("V8_DURATION_NOT_8_SECONDS")
    report.update({"video_file":dest.name,"duration_seconds":duration,
                   "video_sha256":digest(dest),"video_bytes":dest.stat().st_size,
                   "render_verified":True,"ready_to_publish":False})
    (REVIEW/"qa-v8.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("[OTAKU V8] PIN_CONTROLLED_MP4_READY_NO_YOUTUBE",flush=True)

def main()->int:
    try:
        row=preflight(os.environ)
        if len(sys.argv)>1 and sys.argv[1]=="--preflight":
            print("[OTAKU V8] RESERVED_PIN_PREVIEW_ONLY_ZERO_IMAGE_CALLS")
            return 0
        report=build(row)
        print("[OTAKU V8] PIN_FRAMES_120_READY",flush=True)
        render(report)
        return 0
    except Exception as exc:
        print("[OTAKU V8 BLOCKED] "+
              (str(exc) if isinstance(exc,Blocked) else type(exc).__name__),
              file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
