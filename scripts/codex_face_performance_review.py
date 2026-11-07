#!/usr/bin/env python3
"""A/B verification of Codex PR #81's *new* automatic face animation.

On an isolated review branch, reuse verified original V6 anime art and voice.
Run adaptive_performance.prepare_scene_art() on the genuine RGBA for Codex
face detection, then render two identical Remotion timelines (static control
and browser Canvas CharacterArt), with no provider calls or YouTube upload.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from adaptive_performance import prepare_scene_art
from otaku_multicena_duration_90 import PLAN,PAUSE,load
from legendas_precisas import captions_from_markers

WORKFLOW="Codex PR81 - real adaptive character animation A/B review (no upload)"
BRANCH="refs/heads/test/codex-face-performance-review-20261107"
EPISODE="5995-codex-face-animation-test"
OWNER="chatgpt_codex_adaptive_performance_review_20261107"
SOURCE_RUN="42332358380"
ORIGINAL=ROOT/"assets/gerados/otaku-v6-real-90s"
PUBLIC=ROOT/"motion-remotion/public"
DEST=PUBLIC/"generated/codex-pr81-face-review"
REVIEW=ROOT/"codex-pr81-animation-review"
VIDEO_FPS=30
SECONDS=8
SHA={
 "pose-05-1.png":"fcebfb9b195325d52ec79abc3d58d287ed8c456b8f39f888873cb6b8026709e8",
 "background-05.png":"038181a5ce82ffa061f9ce4bf5f56cb62445e130672a7eeb61a26d541f120db5",
 "voz-master.mp3":"d67cd58ff30c45d4aeede31484434360e96f9bd855a27fce96f2866646927398",
 "marcacoes-voz.json":"544f61af96fade7b23639725894b3336727a55bb6c95c97a3b402c049e19c530"
}

class ReviewBlocked(RuntimeError):
    pass

def digest(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def preflight(env:dict)->dict:
    needed={
     "GITHUB_REPOSITORY":"HelioConde/AutoEditorVideo",
     "GITHUB_REF":BRANCH,
     "GITHUB_EVENT_NAME":"push",
     "GITHUB_RUN_ATTEMPT":"1",
     "GITHUB_WORKFLOW":WORKFLOW,
     "CODEX_PR81_ONE_REVIEW":"1",
     "MAX_IMAGE_CALLS":"0",
    }
    if any(env.get(k)!=v for k,v in needed.items()):
        raise ReviewBlocked("UNAUTHORIZED_CI_OR_IMAGE_CALLS")
    if any(env.get(k) for k in ("PROXY_API_KEY","PROXY_ACCOUNTS_JSON",
                               "YOUTUBE_CLIENT_JSON","YOUTUBE_BR_TOKEN_JSON")):
        raise ReviewBlocked("IMAGE_PROVIDER_AND_YOUTUBE_SECRETS_FORBIDDEN")
    paused=load(PAUSE)
    if not (paused.get("pause_requested") is True and
            paused.get("authorized_public") is False and
            paused.get("resume_authorized_after_maintenance") is False):
        raise ReviewBlocked("PRODUCTION_QUEUE_MUST_STAY_PAUSED")
    ledger=json.loads((ROOT/"conteudos/otaku-production-reservations.json").read_text(encoding="utf-8"))
    rows=[x for x in ledger["entries"] if x.get("channel")=="br" and x.get("id")==EPISODE]
    if len(rows)!=1 or rows[0].get("status")!="reserved" or rows[0].get("reservation_owner")!=OWNER:
        raise ReviewBlocked("BR_REVIEW_NOT_RESERVED")
    return load(PLAN)["items"][0]

def verify_assets():
    for filename,sha256 in SHA.items():
        f=ORIGINAL/filename
        if not f.is_file() or digest(f)!=sha256:
            raise ReviewBlocked("V6_ORIGINAL_ARTIFACT_BAD_HASH_"+filename)
    with Image.open(ORIGINAL/"pose-05-1.png") as img:
        if img.size!=(1024,1536) or img.mode!="RGBA":
            raise ReviewBlocked("V6_CHAR_NOT_EXPECTED_RGBA")

def find_auto_performance():
    """Run Codex automatic detector on real original image; fail visibly if absent."""
    plan_attempts=[]
    for pose in ("pose-05-1.png","pose-05-2.png","pose-09-1.png",
                 "pose-07-1.png","pose-03-1.png","pose-01-1.png"):
        file=ORIGINAL/pose
        if not file.is_file():
            continue
        with Image.open(file) as im:
            if im.mode!="RGBA" or im.size!=(1024,1536):
                continue
        rel="generated/codex-pr81-face-review/"+pose
        shutil.copy2(file,DEST/pose)
        scene={
         "subject":"personagens","renderMode":"multilayer",
         "background":"generated/codex-pr81-face-review/background.png",
         "foreground":"generated/codex-pr81-face-review/background.png",
         "layers":[{"id":"single-original-foreground","role":"character",
                    "src":rel,"z":10,"alphaCoverage":.3,
                    "contactRisk":0,"heroRisk":0}]
        }
        try:
            prepare_scene_art([scene],PUBLIC)
            performance=scene["layers"][0].get("performance")
            faces=(performance or {}).get("faces",[])
            eyes=sum(len(f.get("eyes",[])) for f in faces)
            plan_attempts.append({"image":pose,"detected_faces":len(faces),
                                  "recognized_eyes":eyes,
                                  "automatic":bool(performance)})
        except Exception as exc:
            plan_attempts.append({"image":pose,"error":type(exc).__name__,
                                  "automatic":False})
            continue
        if performance and eyes>=2 and len(faces)==1:
            return scene,performance,pose,plan_attempts,True
    # Keep a meaningful real-engine test even if anime-style faces defeat
    # the detector. The fallback is fully explicit and never called automatic.
    pose="pose-05-1.png"
    plan={
       "width":1024,"height":1536,"seed":135827,
       "faces":[{
          "box":[355,290,300,330],
          "eyes":[[453,432,30,12],[546,429,30,12]],
       }],
       "motion":"cutout",
    }
    scene={
     "subject":"personagens","renderMode":"multilayer",
     "background":"generated/codex-pr81-face-review/background.png",
     "foreground":"generated/codex-pr81-face-review/background.png",
     "layers":[{"id":"single-original-foreground","role":"character",
                "src":"generated/codex-pr81-face-review/"+pose,
                "z":10,"alphaCoverage":.3,
                "contactRisk":0,"heroRisk":0,"performance":plan}]
    }
    return scene,plan,pose,plan_attempts,False

def make_props(row,scene,with_motion,source_pose):
    scene=json.loads(json.dumps(scene))
    if not with_motion:
        for l in scene["layers"]:
            l.pop("performance",None)
    captions=captions_from_markers(ORIGINAL/"voz-master.mp3",
                                  row["narration_script"],91.44,
                                  fps=VIDEO_FPS)
    captions=[{**c,"endFrame":min(c["endFrame"],SECONDS*VIDEO_FPS)}
              for c in captions if c["startFrame"]<SECONDS*VIDEO_FPS]
    if not captions:
        raise ReviewBlocked("NO_AUTHENTIC_CAPTIONS")
    return {
        "id":EPISODE+("-codex" if with_motion else "-static"),
        "durationFrames":SECONDS*VIDEO_FPS,
        "audio":"generated/codex-pr81-face-review/voice.mp3",
        "scenes":[{
           **scene,"id":"PR81-CODEX-AUTOMATIC-FACE",
           "startFrame":0,"endFrame":SECONDS*VIDEO_FPS,
           "shotType":"close","beatRole":"setup",
           "transitionStyle":"hard"
        }],
        "captions":captions,
        "hook":"CODEX • TESTE ANIMAÇÃO",
        "animationMode":"cinematica",
        "visualProfile":"otaku-v6-vertical",
        "editorialProfile":"PR81 control experiment - authentic Remotion Canvas character renderer"
    }

def render(name:str,props:Path):
    output=REVIEW/name
    run=subprocess.run([
        "npm","run","render:master","--",str(output.resolve()),
        "--props",str(props.resolve()),"--concurrency","1",
        "--codec","h264","--crf","19"
    ],cwd=ROOT/"motion-remotion",capture_output=True,text=True,timeout=3600)
    if run.returncode:
        print("[CODEX PR81] remotion stderr: "+run.stderr[-1800:],file=sys.stderr)
        raise ReviewBlocked("REMOTION_RENDER_FAILED_"+name)
    if not output.is_file() or output.stat().st_size<250000:
        raise ReviewBlocked("REMOTION_MP4_MISSING_"+name)
    return output

def frame_at(video:Path,second:float)->np.ndarray:
    proc=subprocess.run(["ffmpeg","-v","error","-ss",str(second),
        "-i",str(video),"-frames:v","1","-f","image2pipe","-vcodec","png","-"],
        capture_output=True,timeout=60,check=True)
    data=np.frombuffer(proc.stdout,np.uint8)
    frame=cv2.imdecode(data,cv2.IMREAD_COLOR)
    if frame is None or frame.shape[:2]!=(1920,1080):
        raise ReviewBlocked("DECODED_VIDEO_FRAME_INVALID")
    return frame

def compare_frames(static:Path,animated:Path,performance:dict)->dict:
    # Work in native output coordinates (source 1024x1536 -> 1080x1920).
    metrics=[]
    cols=[]
    for t in (.2,1.1,1.8,2.3,3.0,4.2,5.4,6.6,7.6):
        a=frame_at(static,t)
        b=frame_at(animated,t)
        # Pixel difference in person upper half, excluding captions/hook.
        # Animated facial canvas should alter appearance even with camera equal.
        roi=(slice(320,1000),slice(245,800))
        delta=cv2.absdiff(a[roi],b[roi])
        change=np.any(delta>18,axis=2)
        fraction=float(np.mean(change))
        mean_luma=float(np.mean(delta))
        metrics.append({"seconds":t,"changed_pixels_18":round(fraction,5),
                        "mean_abs_bgr_diff":round(mean_luma,3),
                        "animated_frame_gray_std":round(float(np.std(
                          cv2.cvtColor(b,cv2.COLOR_BGR2GRAY))),2)})
        if t in (1.8,3.0,5.4):
            pair=np.concatenate([a,b],axis=1)
            cv2.putText(pair,"STATIC ORIGINAL",(35,85),cv2.FONT_HERSHEY_SIMPLEX,1.4,(255,255,255),3)
            cv2.putText(pair,"CODEX PR81",(1125,85),cv2.FONT_HERSHEY_SIMPLEX,1.4,(255,255,255),3)
            pair=cv2.resize(pair,(810,720),interpolation=cv2.INTER_AREA)
            cv2.imwrite(str(REVIEW/("compare-%.1f.jpg"%t)),pair,
                        [cv2.IMWRITE_JPEG_QUALITY,86])
            cols.append(pair)
    if max(m["changed_pixels_18"] for m in metrics)<.001:
        raise ReviewBlocked("CODEX_RENDER_HAS_NO_VISIBLE_CHARACTER_CHANGE")
    cv2.imwrite(str(REVIEW/"AB-static-versus-Codex.jpg"),
                np.concatenate(cols,axis=1),
                [cv2.IMWRITE_JPEG_QUALITY,86])
    return {"face_region_temporal_ab_comparison":metrics,
            "max_changed_fraction":max(x["changed_pixels_18"] for x in metrics),
            "background_and_voice_identical":True,
            "same_initial_source_image":True}

def probe(video:Path)->dict:
    run=subprocess.run(["ffprobe","-v","error","-show_streams",
        "-show_format","-of","json",str(video)],
        capture_output=True,text=True,check=True)
    obj=json.loads(run.stdout)
    v=next((x for x in obj["streams"] if x["codec_type"]=="video"),None)
    audio=any(x["codec_type"]=="audio" for x in obj["streams"])
    duration=float(obj["format"]["duration"])
    if not v or v.get("width")!=1080 or v.get("height")!=1920 or not audio or abs(duration-SECONDS)>.25:
        raise ReviewBlocked("BAD_9_16_VIDEO_OR_AUDIO")
    return {"duration":duration,"resolution":"1080x1920","audio_stream":audio,
            "video_bytes":video.stat().st_size,"sha256":digest(video)}

def main():
    try:
        row=preflight(os.environ)
        if len(sys.argv)>1 and sys.argv[1]=="--preflight":
            print("[CODEX PR81] ONE_ISOLATED_NO_COST_REVIEW_AUTHORIZED")
            return 0
        verify_assets()
        if DEST.exists() or REVIEW.exists():
            raise ReviewBlocked("OUTPUT_EXISTS_NO_DUPLICATE_REVIEW")
        DEST.mkdir(parents=True)
        REVIEW.mkdir(parents=True)
        shutil.copy2(ORIGINAL/"background-05.png",DEST/"background.png")
        shutil.copy2(ORIGINAL/"voz-master.mp3",DEST/"voice.mp3")
        scene,perf,pose,attempts,auto=find_auto_performance()
        (REVIEW/"face-detection.json").write_text(json.dumps({
            "automatic_detection_used":auto,
            "selected_source":pose,
            "detector_attempts":attempts,
            "performance_plan":perf
        },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("[CODEX PR81] FACE_DETECTOR result="+str(auto)+
              " selected="+pose+" eyes="+str(sum(len(f["eyes"]) for f in perf["faces"])),
              flush=True)
        p0=REVIEW/"props-static.json"
        p1=REVIEW/"props-codex.json"
        p0.write_text(json.dumps(make_props(row,scene,False,pose),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        p1.write_text(json.dumps(make_props(row,scene,True,pose),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        baseline=render("A_original_estatico.mp4",p0)
        codex=render("B_Codex_PR81_animacao_nova.mp4",p1)
        comparison=compare_frames(baseline,codex,perf)
        report={
            "source_branch_commit":"f2b6f344b98fb077627a11a7fb9d1974eb3b0116",
            "codex_original_component":"motion-remotion/src/character-art.tsx",
            "detector":"scripts/adaptive_performance.py",
            "detector_auto_success":auto,
            "selected_original_rgba":pose,
            "source_run_id":SOURCE_RUN,
            "new_image_calls":0,
            "youtube_uploads":0,
            "preview_only":True,
            "human_qualitative_review_required":True,
            "limitation":"New Canvas character animation is limited to facial micro-expressions and small portrait motion; not full body rigging, independent limbs, or true motion-brush generative synthesis.",
            "static":probe(baseline),
            "codex":probe(codex),
            **comparison
        }
        (REVIEW/"qa-codex-pr81.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("[CODEX PR81] A_B_MP4_RENDERED_TESTED_NO_UPLOAD",flush=True)
        return 0
    except Exception as exc:
        import traceback
        last=traceback.extract_tb(exc.__traceback__)[-1:]
        at=(Path(last[0].filename).name+":"+str(last[0].lineno)) if last else "unknown"
        print("[CODEX PR81 BLOCKED] "+type(exc).__name__+" at "+at,file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
