#!/usr/bin/env python3
"""One genuine AutoEditorVideo 90s review render through Edge TTS + gpt-image-2 + Remotion.

User authorized ONE GitHub-only preview, not resumption of the 50-Short queue.
No YouTube OAuth/imports/upload. No fake artwork or synthetic offline surrogate.
All source art remains pending human rights, anatomy and character QA.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

from PIL import Image, ImageOps, ImageStat

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from otaku_multicena_editorial_score_v5 import audit as editorial_audit
from otaku_multicena_duration_90 import load,PLAN,PAUSE
from narracao_shorts import ensure_voice, _spoken_words
from legendas_precisas import captions_from_markers
from gerar_video_codex import proxy_key,check_proxy_accounts,request_image
from capa_cinematografica import render_cover
from otaku_multicena_video_qa import inspect as inspect_mp4

WORK=ROOT/"assets"/"gerados"/"otaku-v5-review-real-90s"
MOTION=ROOT/"motion-remotion"
PUBLIC=MOTION/"public"/"generated"/"otaku-v5-real-90s-review"
REVIEW=ROOT/"otaku-real-90s-review"
EPISODE="otaku-v5-death-note-review-only"
MODEL="gpt-image-2"
IMAGE_CALL_LIMIT=10
SCENE_COUNT=10
FPS=30

class PreviewBlocked(RuntimeError):
    pass

def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def validate_environment(env:dict[str,str])->dict:
    if any((env.get(k)!="1" for k in ("OTAKU_SINGLE_REVIEW_AUTHORIZED","GITHUB_RUN_ATTEMPT"))):
        raise PreviewBlocked("SINGLE_TEST_FIRST_ATTEMPT_ONLY")
    if env.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo":
        raise PreviewBlocked("WRONG_REPOSITORY")
    if env.get("GITHUB_REF")!="refs/heads/main" or env.get("GITHUB_EVENT_NAME")!="push":
        raise PreviewBlocked("REQUIRES_MAIN_PUSH")
    if env.get("IMAGE_MODEL")!=MODEL or env.get("MAX_IMAGE_CALLS")!="10":
        raise PreviewBlocked("IMAGE_PROVIDER_OR_BUDGET_NOT_EXACT")
    if env.get("GITHUB_WORKFLOW")!="Otaku V5 - REAL 90s MP4 review from AutoEditorVideo (no upload)":
        raise PreviewBlocked("WRONG_GITHUB_WORKFLOW")
    if env.get("YOUTUBE_BR_TOKEN_JSON") or env.get("YOUTUBE_CLIENT_JSON"):
        raise PreviewBlocked("YOUTUBE_CREDENTIALS_NOT_PERMITTED_IN_PREVIEW")
    flags=load(PAUSE)
    if not (flags.get("pause_requested") is True and
            flags.get("authorized_public") is False and
            flags.get("maintenance_complete") is False and
            flags.get("resume_authorized_after_maintenance") is False):
        raise PreviewBlocked("ORIGINAL_PUBLIC_QUEUE_MUST_REMAIN_PAUSED")
    report=editorial_audit()
    if report["score"]!=9:
        raise PreviewBlocked("EDITORIAL_QUALITY_SCORE_NOT_NINE")
    p=load(PLAN)
    row=p["items"][0]
    if (row["rank"]!=1 or row["anime"]!="Death Note" or
        row["ending_policy"]!="answer_only_no_cta" or
        row["ready_to_render"] is not False or
        row["story_quality_v5"]["approved_for_media"] is True):
        raise PreviewBlocked("UNEXPECTED_SCRIPT_OR_HUMAN_APPROVAL")
    if WORK.exists() or REVIEW.exists():
        raise PreviewBlocked("NO_DUPLICATE_REVIEW_GENERATION")
    return row

def probe_seconds(path:Path)->float:
    p=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                      "-of","default=nokey=1:noprint_wrappers=1",str(path)],
                     text=True,capture_output=True,timeout=30,check=True)
    return float(p.stdout.strip())

def make_voice(row:dict)->tuple[Path,float,list[dict]]:
    import narracao_shorts as ns
    script=row["narration_script"]
    rate=0
    best=None
    # First take, then at most 2 corrections using genuine Edge TTS pacing;
    # never time-stretch recorded audio or insert fake silence.
    for attempt in range(3):
        ns.RATE=("%+d"%rate)+"%"
        subdir=WORK/("voice-take-%d"%(attempt+1))
        mp3,_=ensure_voice({"script":script},subdir,create=True,engine="edge")
        duration=probe_seconds(mp3)
        if not 55 <= duration <= 130:
            raise PreviewBlocked("TTS_VOICE_DURATION_IMPLAUSIBLE")
        if best is None or abs(duration-90)<abs(best[1]-90):
            best=(mp3,duration)
        print("[PREVIEW REAL] TTS_TAKE_%d_SECONDS_%.2f"%(attempt+1,duration),flush=True)
        if 87<=duration<=93:
            captions=captions_from_markers(mp3,script,duration,fps=FPS)
            if not captions or len(captions)<40:
                raise PreviewBlocked("GENUINE_WORD_CAPTIONS_NOT_AVAILABLE")
            return mp3,duration,captions
        speed=max(.7,min(1.3,(1+rate/100)*duration/90))
        newrate=int(round((speed-1)*100))
        if newrate==rate:
            newrate=rate+(3 if duration>93 else -3)
        rate=max(-30,min(30,newrate))
    raise PreviewBlocked("REAL_TTS_COULD_NOT_REACH_87_TO_93S_NO_STRETCH_USED")

# Original illustration instructions, not prompts to recreate official animation frames.
# Avoid depicting books with readable franchise logos or screenshots.
SHOTS=(
 ("A thoughtful young adult student with chestnut brown hair and beige jacket "
  "sits across a pale enigmatic detective with messy black hair in a white shirt. "
  "Close-up on their wary eyes in a dark university reading room."),
 ("Wide university atrium at dusk; the same pale detective discreetly approaches "
  "the same brown-haired student to propose collaboration."),
 ("A case board with connected abstract photographs and colored pins; the "
  "same two men assess the clues, silent tense analytical expressions."),
 ("Interior of police investigation task force office, detective introduces "
  "the student to the task force; subtle gestures, different wide shot."),
 ("Close reaction of the brown-haired student pretending calm under the "
  "detective's suspicious gaze, warm light versus cool shadows."),
 ("An anonymous second imitator appears as a distant silhouette outside "
  "a rainy city building, the police investigation expands on the case board."),
 ("A private quiet scene, the student deliberately sets down a mysterious "
  "plain black unbranded notebook, conflicted expression, no magical effects."),
 ("The student with changed, sincere expression and detective stand together "
  "examining crime records in an office, no notebook shown."),
 ("Tight close-up of the detective's observant eyes reflecting a blurred "
  "task force board and the student, unresolved suspicion."),
 ("Final cinematic wide shot: student and detective at opposite ends of "
  "a single investigation table, strong contrast of warm lamp and cool "
  "window light; visual answer is the distance between trust and suspicion.")
)

def make_prompt(row:dict,index:int)->str:
    if index not in range(SCENE_COUNT):raise PreviewBlocked("INVALID_SHOT_INDEX")
    return (
      "Create ONE original, premium hand-painted 2D anime-inspired editorial "
      "illustration, 1024x1536 portrait, for a Brazilian analysis of Death Note. "
      "This is original illustrative analysis artwork, NOT a screenshot, "
      "not an imitation of a specific anime scene/frame or an official poster. "
      "Original cohesive cinematic character designs: same fictional adult "
      "student with chestnut hair, beige jacket and white collar; same pale "
      "slim adult detective with messy dark hair and loose white shirt. "
      "Keep their character features and clothing CONSISTENT across all shots. "
      "Narrative facts: a suspect is invited into investigation, both test "
      "one another, a second Kira appears, the suspect relinquishes memories "
      "and later sincerely helps investigate; detective still doubts him. "
      "Deep midnight blues, wine red accents, low-key cinematic amber practical "
      "lighting, layered background depth, crisp expressive face, believable "
      "hands, vivid narrative action. No injuries or violence. "
      "Never include writing, logos, signs, subtitles, watermarks, split screens, "
      "montage collage, brand or text. Reserve bottom 22 percent for later captions. "
      "All people and objects fully within the image; safe headroom. "
      "Unique storyboard frame %d of %d; precise visible action: %s" %
      (index+1,SCENE_COUNT,SHOTS[index])
    )

def generate_images(row:dict,key:str)->list[Path]:
    if len(SHOTS)!=SCENE_COUNT:raise PreviewBlocked("INVALID_IMAGE_COUNT")
    images=[]
    WORK.mkdir(parents=True,exist_ok=False) if not WORK.exists() else None
    for i in range(SCENE_COUNT):
        dest=WORK/("shot-%02d.png"%(i+1))
        if dest.exists():raise PreviewBlocked("SHOTS_CANNOT_BE_REGENERATED")
        print("[PREVIEW REAL] IMAGE_REQUEST_%02d_OF_10"%(i+1),flush=True)
        raw=request_image(make_prompt(row,i),MODEL,key,"1024x1536")
        with Image.open(io.BytesIO(raw)) as im:
            im.load()
            if im.width<512 or im.height<768:raise PreviewBlocked("MODEL_IMAGE_TOO_SMALL")
            full=ImageOps.pad(im.convert("RGB"),(1024,1536),
                              method=Image.Resampling.LANCZOS,color=(12,13,27))
            stats=ImageStat.Stat(full.resize((64,96))).stddev
            if max(stats)<15:raise PreviewBlocked("MODEL_IMAGE_BLANK")
            full.save(dest,"PNG",optimize=True)
        images.append(dest)
        print("[PREVIEW REAL] IMAGE_VERIFIED_%02d_OF_10"%(i+1),flush=True)
    if len({sha(p) for p in images})!=SCENE_COUNT:
        raise PreviewBlocked("DUPLICATE_IMAGES_CANNOT_RENDER")
    return images

def build_cuts(row:dict,voice:Path,frames:int)->list[int]:
    word_data=json.loads((voice.parent/"marcacoes-voz.json").read_text(encoding="utf-8"))
    real=word_data["words"]
    counts=[len(_spoken_words(seg["text"]).split()) for seg in row["story_segments"]]
    if len(real)<160 or sum(counts)<190 or len(counts)!=6:
        raise PreviewBlocked("REAL_NARRATION_WORD_MARKERS_INCOMPLETE")
    # Ten meaningful shots: hook, two from context/tension/twist/explanation,
    # and one conclusion; index each cut into ACTUAL Edge TTS word boundaries.
    indices=[0,counts[0]]
    running=counts[0]
    for count in counts[1:5]:
        indices.extend([running+round(count/2),running+count])
        running+=count
    # Ten scene starts, plus the measured audio end, for eleven boundaries.
    if len(indices)!=10:raise PreviewBlocked("INVALID_TEN_SHOT_SEGMENT_MAP")
    # TTS WordBoundary can tokenize numbers/names slightly differently.
    total=sum(counts)
    actual=len(real)
    starts=[]
    for index in indices:
        k=min(actual-1,max(0,round(index*actual/total)))
        starts.append(round(float(real[k]["start"])*FPS) if index else 0)
    cuts=starts+[frames]
    if any(b-a<40 or b-a>420 for a,b in zip(cuts,cuts[1:])):
        raise PreviewBlocked("REAL_SCENE_TIMINGS_NOT_USABLE")
    return cuts

def render(row:dict,audio:Path,duration:float,captions:list[dict],images:list[Path])->dict:
    frames=round(duration*FPS)
    cuts=build_cuts(row,audio,frames)
    PUBLIC.mkdir(parents=True,exist_ok=False)
    for i,file in enumerate(images,1):
        shutil.copy2(file,PUBLIC/("shot-%02d.png"%i))
    shutil.copy2(audio,PUBLIC/"voice.mp3")
    role=["hook","setup","detail","detail","rehook","twist","detail","answer","answer","answer"]
    shot_types=["close","wide","detail","medium","reaction","wide","detail","medium","close","final"]
    scenes=[]
    for i in range(SCENE_COUNT):
        path="generated/otaku-v5-real-90s-review/shot-%02d.png"%(i+1)
        scenes.append({"id":"%02d"%(i+1),"subject":"personagens",
          "startFrame":cuts[i],"endFrame":cuts[i+1],
          "background":path,"foreground":path,
          "renderMode":"master_static","shotType":shot_types[i],
          "beatRole":role[i],
          "transitionStyle":"hard" if i in (0,4,5,9) else "crossfade"})
    props={"id":EPISODE,"durationFrames":frames,
       "audio":"generated/otaku-v5-real-90s-review/voice.mp3",
       "scenes":scenes,"captions":captions,
       "hook":"POR QUE L CHAMOU LIGHT?",
       "animationMode":"cinematica","characterPreset":"equilibrado",
       "visualProfile":"original","editorialProfile":"otaku-v5-real-90s-review-only",
       "soundCues":[]}
    prop_file=WORK/"remotion-props.json"
    prop_file.write_text(json.dumps(props,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    mp4=WORK/"Otaku_Multicena_AutoEditorVideo_Death_Note_90s_PREVIEW.mp4"
    args=["npm","run","render:master","--",str(mp4.resolve()),
          "--props",str(prop_file.resolve()),"--concurrency","2",
          "--codec","h264","--crf","20"]
    print("[PREVIEW REAL] ORIGINAL_REMOTION_MASTER_RENDER_START",flush=True)
    # Keep untrusted media/provider output out of Action logs.
    result=subprocess.run(args,cwd=MOTION,capture_output=True,text=True,
                          check=False,timeout=3600)
    if result.returncode:
        print("[PREVIEW REAL] REMOTION_EXIT_CODE_%d"%result.returncode,flush=True)
        print((result.stderr or result.stdout)[-1300:],file=sys.stderr)
        raise PreviewBlocked("ACTUAL_REMOTION_RENDER_FAILED")
    if not mp4.is_file() or mp4.stat().st_size<400_000:
        raise PreviewBlocked("REMOTION_OUTPUT_MISSING")
    report=inspect_mp4(mp4,duration_profile="short_90s_test")
    summary={
      "schema":"autoeditorvideo/real-90s-preview/v1",
      "created_by":"scripts/otaku_multicena_90s_real_preview.py",
      "repository":"HelioConde/AutoEditorVideo",
      "render_engine":"motion-remotion/src/master-short.tsx",
      "voice_engine":"narracao_shorts.py Edge TTS genuine WordBoundary",
      "image_engine":"gerar_video_codex.py request_image via pinned native Go proxy",
      "image_model":MODEL,"image_requests":SCENE_COUNT,
      "narration_sha256":hashlib.sha256(row["narration_script"].encode()).hexdigest(),
      "voice_seconds":duration,"video_sha256":sha(mp4),
      "actual_video_qa":report,"cut_frames":cuts,
      "real_character_rig_motion":False,
      "actual_user_uploaded_content_used":False,
      "artwork_human_review":False,"canon_human_review":False,
      "rights_human_review":False,
      "approved_for_youtube":False,"youtube_uploads":0,
      "creator_queue_still_paused":True,
      "no_fake_art_or_voice_fallback":True,
      "note":"Real original engine preview, NOT external simulator. Ten independently generated still illustrations; camera motion only, no independently articulated character rigs."
    }
    REVIEW.mkdir(parents=True,exist_ok=False)
    shutil.copy2(mp4,REVIEW/mp4.name)
    with Image.open(images[0]) as im:
        render_cover(im,"L CONVIDOU LIGHT?",REVIEW/"cover.jpg",focus_x=.5,focus_y=.38)
    (REVIEW/"qa-report.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (REVIEW/"narration-script.txt").write_text(row["narration_script"]+"\n",encoding="utf-8")
    (REVIEW/"remotion-props.json").write_text(json.dumps(props,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("[PREVIEW REAL] MP4_READY_REAL_ENGINE_NO_YOUTUBE",flush=True)
    return summary

def run()->dict:
    row=validate_environment(os.environ)
    WORK.mkdir(parents=True,exist_ok=False)
    # Generate genuine voice and validate duration BEFORE spending image credits.
    audio,duration,captions=make_voice(row)
    print("[PREVIEW REAL] MEASURED_VOICE_%.2fs_PRE_IMAGE_BUDGET_OK"%duration,flush=True)
    key=proxy_key()
    check_proxy_accounts(key)
    images=generate_images(row,key)
    return render(row,audio,duration,captions,images)

def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--preflight",action="store_true")
    args=parser.parse_args()
    try:
        row=validate_environment(os.environ)
        if args.preflight:
            print(json.dumps({"status":"SAFE_ONE_PREVIEW_ONLY",
                "anime":row["anime"],"image_budget":IMAGE_CALL_LIMIT,
                "pause_unchanged":True,"youtube_upload":False},ensure_ascii=False))
            return 0
        run()
        return 0
    except Exception as error:
        # Do not print proxy account or third-party error payloads in public logs.
        if isinstance(error,PreviewBlocked):
            print("[PREVIEW REAL BLOCKED] "+str(error),file=sys.stderr)
        else:
            print("[PREVIEW REAL BLOCKED] STAGE_"+type(error).__name__,file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
