#!/usr/bin/env python3
"""Genuine AutoEditorVideo V6 one-shot 90s preview with separate animated RGBA poses.

Uses the same original repo components: Edge Neural TTS, pinned Codex Proxy /
gpt-image-2, Remotion MasterShort, real word captions and FFmpeg AV QA.
Creates one REVIEW artifact only. Never imports or executes YouTube publishing.
"""
from __future__ import annotations
import asyncio
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageOps, ImageStat

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import otaku_multicena_90s_real_preview as previous
from otaku_multicena_duration_90 import PLAN,PAUSE,load
from otaku_multicena_editorial_score_v5 import audit as score_editorial
from otaku_multicena_pose_qa import inspect_poses
from gerar_video_codex import proxy_key,check_proxy_accounts,request_image
from narracao_shorts import VOICE,_spoken_words
from legendas_precisas import captions_from_markers
from capa_cinematografica import render_cover
from otaku_multicena_video_qa import inspect as inspect_video

WORK=ROOT/"assets"/"gerados"/"otaku-v6-real-90s"
MOTION=ROOT/"motion-remotion"
MEDIA=MOTION/"public"/"generated"/"otaku-v6-real-90s"
REVIEW=ROOT/"otaku-real-v6-review"
WORKFLOW="Otaku V6 - Animated 90s Death Note real AutoEditorVideo review (no upload)"
EPISODE="death-note-90s-v6-real-preview-no-youtube"
MODEL="gpt-image-2"
FPS=30
SCENES=10
ANIMATED_SHOTS=(0,2,4,6,8)
ART_REQUESTS=20
SIZE=(1024,1536)
VOICE_RATES=(5,8,8,6,6,4)
VOICE_PITCHES=(4,-2,3,0,-2,-4)
PAUSES=(.12,.16,.19,.12,.17,0.)

class V6Blocked(RuntimeError):
    pass

def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def check_env(env:dict[str,str])->dict:
    if not all((env.get(k)==v for k,v in {
        "OTAKU_V6_ONE_PREVIEW":"1","GITHUB_REPOSITORY":"HelioConde/AutoEditorVideo",
        "GITHUB_REF":"refs/heads/main","GITHUB_RUN_ATTEMPT":"1",
        "GITHUB_EVENT_NAME":"push","GITHUB_WORKFLOW":WORKFLOW,
        "IMAGE_MODEL":MODEL,"MAX_IMAGE_CALLS":"20"}.items())):
        raise V6Blocked("ONLY_EXPLICIT_FIRST_MAIN_PREVIEW_ACCEPTED")
    if env.get("YOUTUBE_BR_TOKEN_JSON") or env.get("YOUTUBE_CLIENT_JSON"):
        raise V6Blocked("YOUTUBE_CREDENTIALS_ARE_FORBIDDEN")
    gate=load(PAUSE)
    if not (gate.get("pause_requested") is True
            and gate.get("authorized_public") is False
            and gate.get("maintenance_complete") is False
            and gate.get("resume_authorized_after_maintenance") is False):
        raise V6Blocked("PUBLIC_FIFTY_QUEUE_MUST_STAY_PAUSED")
    if score_editorial()["score"]!=9:
        raise V6Blocked("EDITORIAL_PLAN_NOT_VALIDATED")
    row=load(PLAN)["items"][0]
    if (row.get("rank")!=1 or row.get("anime")!="Death Note" or
        row.get("ending_policy")!="answer_only_no_cta" or
        row.get("ready_to_render") is not False or
        row.get("story_segments",[])[-1]["role"]!="resultado"):
        raise V6Blocked("DEATH_NOTE_SCRIPT_CONTRACT_WRONG")
    if WORK.exists() or MEDIA.exists() or REVIEW.exists():
        raise V6Blocked("V6_ARTIFACT_EXISTS_DO_NOT_DUPLICATE")
    return row

# Every generated still must be an original editorial illustration, not an
# official anime frame. Animatable shots have EMPTY, character-free backgrounds.
DIRECTIONS=(
    "No characters. An atmospheric university library at dusk with two empty chairs on opposite sides of a warm desk lamp, tense cinematic composition, middle of canvas clear for later character overlays.",
    "The dark-haired detective meets a thoughtful young brown-haired university student in an outdoor college courtyard at night; clear active gestures, one approaches and extends an invitation.",
    "No people. Police evidence room with a corkboard filled with ABSTRACT shapes, anonymous photos without text, taut red string and an open blank investigation folder.",
    "Police task force members sit around a map while a pale young dark-haired detective introduces a young brown-haired student standing beside him, multiple reactions and hand gestures, a wide room view.",
    "No people. Detective office with moody window light, a single chair facing a cluttered investigation table, raindrops on a dark blue window.",
    "A separate shadowy adult imitator watches distant city lights under rain from a rooftop; the investigator's case board visible as a secondary editorial inset motif, strong silhouette, original character.",
    "No people. Unmarked matte-black notebook rests on a warm wooden table. A distant clock and blurred evidence folders suggest time passing. Keep open space for separately animated young man.",
    "The student and detective cooperate over a stack of case files, clearly DIFFERENT from earlier confrontation: open posture, earnest concern and a bright morning office, visible teamwork.",
    "No people. Investigation wall with glass reflection, single chair, cool fluorescent ceiling light and window, empty center for separately animated detective close-up.",
    "Cinematic wide overhead angle of student and detective standing at opposite sides of an investigation table, sharp shadows divide them, notebook and papers visible, no title lettering."
)
# Two separately illustrated poses per foreground shot. A real character's
# silhouette changes; NOT a zoom or still-frame movement.
POSES={
  0:("Two original young adult investigators on a shared 1024x1536 transparent canvas. One brown-haired student in tan jacket standing LEFT with hand resting on chin; one pale black-haired detective in loose white top standing RIGHT with arms folded. Curious suspicious expressions.",
     "SAME two original investigators, SAME scale and arrangement, same costumes. LEFT student lowers his hand and turns slightly toward RIGHT detective. RIGHT detective raises one hand in a questioning gesture. Visibly changed arms and expressions."),
  2:("Two investigators on a transparent canvas in front of imaginary evidence: LEFT brown-haired student in tan jacket points calmly to his LEFT, RIGHT pale detective in loose white top watches carefully, arm down.",
     "SAME two investigators, identical costumes and placement. Brown-haired student withdraws pointing hand and looks at detective. Detective points up with right hand as though highlighting an evidence clue."),
  4:("One brown-haired student in tan jacket centered on fully transparent portrait canvas, upright tense expression, right hand touching his chin, frontal medium shot.",
     "SAME student same haircut and jacket, frontal medium shot, he lowers his right hand and glances sharply to camera LEFT, anxious expression visibly changes."),
  6:("One brown-haired young adult student in tan jacket on transparent canvas, mid-shot, RIGHT hand held close to chest, hesitant as if considering an invisible notebook on a table, face serious.",
     "SAME student and outfit at the SAME scale and canvas position, he stretches RIGHT hand toward the imaginary tabletop and looks down thoughtfully, other arm stays steady."),
  8:("One pale young adult detective with messy black hair in loose white shirt on transparent canvas, close upper-body shot, thoughtful expression, head upright, left hand under chin.",
     "SAME detective at same size, pose and canvas location; he tilts head slightly toward the left, eyebrows narrow in suspicion and raises his left hand to gesture, clearly different face and hand.")
}

def original_prompt(index:int,*,pose:int|None=None)->str:
    base=(
      "ORIGINAL premium hand-painted 2D anime-inspired cinematic editorial "
      "art, no anime screenshot or copied existing illustration. Consistent "
      "original fictional young adult student with brown hair, tan jacket "
      "and ivory shirt, and original pale detective with messy black hair "
      "and plain loose white top. Depth, detailed believable anatomy, hands "
      "with five fingers, controlled amber practical lights and deep blue "
      "shadows, wine-red details. Precise storytelling; no violence. "
      "NO logos, text, letters, numbers, speech bubbles, borders, collage "
      "panels, watermarks or anime titles. Center essential content within "
      "middle 72 percent horizontal width, leave safe headroom and lower "
      "22 percent clear for captions. Correct realistic perspective. "
    )
    if pose is None:
        return (base+"This is a 1024x1536 VERTICAL BACKGROUND SCENE, "
                "cinematic original illustration. Unique shot %d/10. %s"%
                (index+1,DIRECTIONS[index]))
    if index not in POSES or pose not in (0,1):
        raise V6Blocked("UNAUTHORIZED_CHARACTER_POSE")
    return (base+
      "FULLY TRANSPARENT PNG alpha background, NO furniture, scenery, "
      "environment, color wash, ground, canvas border, background shade, "
      "text or drop shadow. ONLY clearly isolated fictional characters "
      "as authored 2D animation CEL layers, completely inside image. "
      "The isolated people must be placed in the CENTER of canvas, "
      "fully visible, consistent face, hairstyle, scale, outfit and "
      "lighting with the OTHER pose variant for this scene. "
      "This is independently animated foreground pose %d of 2 in shot %d: %s"%
      (pose+1,index+1,POSES[index][pose]))

def image_original(key:str,prompt:str,*,alpha:bool)->Image.Image:
    raw=request_image(prompt,MODEL,key,"1024x1536",
                     background="transparent" if alpha else None,
                     output_format="png")
    with Image.open(io.BytesIO(raw)) as img:
        img.load()
        if img.width<512 or img.height<768:
            raise V6Blocked("MODEL_IMAGE_RESOLUTION_TOO_SMALL")
        if alpha:
            rgba=img.convert("RGBA")
            real_alpha=rgba.getchannel("A")
            bbox=real_alpha.point(lambda x:255 if x>32 else 0).getbbox()
            if bbox is None:
                raise V6Blocked("EMPTY_TRANSPARENT_CHARACTER_LAYER")
            nopaque=sum(real_alpha.histogram()[240:])
            if nopaque/(rgba.width*rgba.height)>.78:
                raise V6Blocked("CHARACTER_IMAGE_HAS_OPAQUE_BACKGROUND")
            return rgba
        rgb=ImageOps.pad(img.convert("RGB"),SIZE,method=Image.Resampling.LANCZOS,
                         color=(9,12,23))
        if max(ImageStat.Stat(rgb.resize((64,96))).stddev)<15:
            raise V6Blocked("BLANK_BACKGROUND_IMAGE")
        return rgb

def standardize_pose(image:Image.Image)->Image.Image:
    """Scale/crop only transparent artwork into a consistent character region."""
    mask=image.getchannel("A")
    bbox=mask.point(lambda x:255 if x>28 else 0).getbbox()
    if not bbox:raise V6Blocked("EMPTY_CHARACTER")
    cut=image.crop(bbox)
    scale=min(740/max(1,cut.width),1210/max(1,cut.height))
    newsize=(max(1,round(cut.width*scale)),max(1,round(cut.height*scale)))
    cut=cut.resize(newsize,Image.Resampling.LANCZOS)
    out=Image.new("RGBA",SIZE,(0,0,0,0))
    # Align the visual center instead of bottom-aligning every separately
    # illustrated pose. With different aspect ratios, bottom alignment shifts
    # the head/torso by hundreds of pixels and creates a fake teleport.
    x=round((SIZE[0]-cut.width)/2)
    y=round(840-cut.height/2)
    if x<12 or y<12 or x+cut.width>SIZE[0]-12 or y+cut.height>SIZE[1]-12:
        raise V6Blocked("CHARACTER_POSE_CROPS_AT_EDGE")
    out.alpha_composite(cut,(x,y))
    return out

def produce_art(row:dict,key:str)->tuple[list[Path],dict[int,list[Path]],dict]:
    if len(DIRECTIONS)!=SCENES or set(POSES)!=set(ANIMATED_SHOTS):
        raise V6Blocked("STORYBOARD_IMAGE_PLAN_INVALID")
    WORK.mkdir(parents=True,exist_ok=True)
    # Alpha-capability FIRST, so unsupported transparency cannot waste all
    # ten scene generations. Never use an opaque/green-screen fallback.
    first=image_original(key,original_prompt(0,pose=0),alpha=True)
    firstfile=WORK/"pose-01-1.png"
    standardize_pose(first).save(firstfile)
    count=1
    frames={0:[firstfile]}
    backgrounds=[]
    for i in range(SCENES):
        print("[OTAKU V6] BACKGROUND_REQUEST_%02d_OF_10"%(i+1),flush=True)
        pic=image_original(key,original_prompt(i),alpha=False)
        dest=WORK/("background-%02d.png"%(i+1))
        pic.save(dest,"PNG",optimize=True)
        backgrounds.append(dest)
        count+=1
        print("[OTAKU V6] BACKGROUND_VERIFIED_%02d_OF_10"%(i+1),flush=True)
        if i in ANIMATED_SHOTS:
            frames.setdefault(i,[])
            for pose in (0,1):
                if i==0 and pose==0:continue
                print("[OTAKU V6] RGBA_POSE_REQUEST_SHOT_%02d_POSE_%d"%
                    (i+1,pose+1),flush=True)
                fg=image_original(key,original_prompt(i,pose=pose),alpha=True)
                target=WORK/("pose-%02d-%d.png"%(i+1,pose+1))
                standardize_pose(fg).save(target,"PNG",optimize=True)
                frames[i].append(target)
                count+=1
            if len(frames[i])!=2:raise V6Blocked("TWO_REAL_POSES_REQUIRED")
    if count!=ART_REQUESTS:raise V6Blocked("WRONG_PAID_IMAGE_CALL_COUNT")
    digests=[sha(x) for x in backgrounds]+[sha(y) for item in frames.values() for y in item]
    if len(set(digests))!=ART_REQUESTS:
        raise V6Blocked("DUPLICATE_OR_REPEATED_ART")
    validated={}
    reports={}
    rejected={}
    for scene,files in frames.items():
        try:
            report=inspect_poses(files)
            validated[scene]=files
            reports[str(scene+1)]=report
            print("[OTAKU V6] POSE_VALIDATED_SHOT_%02d"%(scene+1),flush=True)
        except ValueError as error:
            # Generated frames remain available as unreviewed originals for
            # human inspection, but may NEVER animate in an approved scene.
            reason=str(error)
            rejected[str(scene+1)]=reason
            print("[OTAKU V6] POSE_REJECTED_SHOT_%02d_REASON_%s"%
                  (scene+1,reason),flush=True)
    reports["rejected_scene_reasons"]=rejected
    reports["validated_scene_count"]=len(validated)
    reports["generated_pose_scene_count"]=len(frames)
    (WORK/"pose-validation-v6.json").write_text(json.dumps(
        reports,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if len(validated)<3:
        raise V6Blocked("FEWER_THAN_THREE_REAL_POSE_ANIMATIONS_PASSED")
    return backgrounds,validated,reports

async def edge_part(text:str,rate:int,pitch:int)->tuple[bytes,list[dict]]:
    import edge_tts
    speaker=edge_tts.Communicate(text,VOICE,
        rate="%+d%%"%rate,pitch="%+dHz"%pitch,boundary="WordBoundary")
    data=bytearray()
    words=[]
    async for event in speaker.stream():
        if event["type"]=="audio":
            data.extend(event.get("data",b""))
        elif event["type"]=="WordBoundary":
            start=event.get("offset",0)/10_000_000
            dur=event.get("duration",0)/10_000_000
            if dur>0: words.append({"start":start,"end":start+dur,
                                    "text":event.get("text","")})
    if len(data)<3000 or len(words)<3:
        raise V6Blocked("EDGE_SEGMENT_VOICE_OR_MARKERS_EMPTY")
    return bytes(data),words

def decoded_samples(mp3:Path)->np.ndarray:
    result=subprocess.run(["ffmpeg","-v","error","-i",str(mp3),
        "-ar","48000","-ac","1","-f","s16le","-"],
        check=True,capture_output=True,timeout=70)
    return np.frombuffer(result.stdout,dtype="<i2").copy()

def compose_voice(row:dict)->tuple[Path,float,list[dict],dict]:
    script=row["narration_script"]
    sections=row["story_segments"]
    if len(sections)!=6 or "?" in sections[-1]["text"]:
        raise V6Blocked("NARRATION_STRUCTURE_OR_ENDING_INVALID")
    # Each segment gets a deliberately different pace and small pitch shift.
    # No time-stretch, clip reuse or artificial long silence.
    direction=0
    for attempt in range(2):
        waveparts=[]
        marker=[]
        offset=0.
        global_delta=direction
        for i,section in enumerate(sections):
            rate=VOICE_RATES[i]+global_delta
            audio,words=asyncio.run(edge_part(section["text"],rate,VOICE_PITCHES[i]))
            part=WORK/("segment-%d-take%d.mp3"%(i+1,attempt+1))
            part.parent.mkdir(parents=True,exist_ok=True)
            part.write_bytes(audio)
            samples=decoded_samples(part)
            if samples.size<24000:raise V6Blocked("SPEECH_SEGMENT_TOO_SHORT")
            waveparts.append(samples)
            for item in words:
                marker.append({"start":round(offset+float(item["start"]),5),
                               "end":round(offset+float(item["end"]),5),
                               "text":item["text"]})
            offset+=len(samples)/48000
            pause=PAUSES[i]
            if pause:
                waveparts.append(np.zeros(round(pause*48000),dtype=np.int16))
                offset+=pause
        total=offset
        print("[OTAKU V6] TTS_EXPRESSIVE_TAKE_%d_%.3fs"%(attempt+1,total),flush=True)
        if not 87<=total<=93:
            direction=-4 if total<87 else 4
            if attempt==1:raise V6Blocked("EXPRESSIVE_TTS_NOT_WITHIN_87_TO_93_SECONDS")
            continue
        combined=np.concatenate(waveparts)
        raw_wav=WORK/"narration-master.wav"
        with wave.open(str(raw_wav),"wb") as out:
            out.setnchannels(1);out.setsampwidth(2);out.setframerate(48000)
            out.writeframes(combined.astype("<i2").tobytes())
        mp3=WORK/"voz-master.mp3"
        subprocess.run(["ffmpeg","-y","-v","error","-i",str(raw_wav),
             "-ac","1","-ar","48000","-codec:a","libmp3lame","-b:a","160k",
             str(mp3)],check=True,timeout=80)
        actual=previous.probe_seconds(mp3)
        if not 87<=actual<=93:raise V6Blocked("FINAL_MEASURED_VOICE_OUTSIDE_90S")
        # The actual Edge timestamps are preserved, not estimated from the
        # script. Small pause and each segment's boundary remain aligned.
        (WORK/"marcacoes-voz.json").write_text(json.dumps({
          "voice":VOICE,"rate":"per-segment-real-neural",
          "source":"edge-tts WordBoundary segmented original narration",
          "script_sha256":hashlib.sha256(script.strip().encode()).hexdigest(),
          "words":marker},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        captions=captions_from_markers(mp3,script,actual,fps=FPS)
        if len(captions)<45:raise V6Blocked("REAL_TTS_CAPTION_TIMING_INCOMPLETE")
        return mp3,actual,captions,{"take":attempt+1,
            "segments":6,"rate_percentages":[r+global_delta for r in VOICE_RATES],
            "pitch_hz":list(VOICE_PITCHES),"pauses_seconds":list(PAUSES),
            "source":"actual Edge TTS WordBoundary",
            "voice_duration_seconds":actual}
    raise V6Blocked("DURATION_TOLERANCE_UNREACHABLE")

def synthesize_original_score(seconds:float)->tuple[Path,Path]:
    """Fully original understated notes/texture; no samples or copyrighted OST."""
    hz=24000
    n=round(seconds*hz)
    t=np.arange(n,dtype=np.float32)/hz
    # Six quiet, slowly alternating minor-mode layers; gentle tremolo.
    chords=((110,138.59,164.81),(98,123.47,146.83),
            (82.41,123.47,164.81),(110,130.81,164.81))
    music=np.zeros(n,dtype=np.float32)
    for i in range(4):
        mask=(t>=i*seconds/4)&(t<(i+1)*seconds/4)
        tau=t[mask]-i*seconds/4
        tone=np.zeros(mask.sum(),dtype=np.float32)
        for j,frequency in enumerate(chords[i]):
            tone+=np.sin(2*np.pi*frequency*tau+j*.7).astype(np.float32)/(j+3)
        attack=np.minimum(1,tau/2.0)
        release=np.minimum(1,(seconds/4-tau)/2)
        music[mask]=.18*tone*attack*np.clip(release,0,1)
    music*=.84+.16*np.sin(2*np.pi*.13*t)
    fade=np.minimum(1,np.minimum(t/1.5,(seconds-t)/2))
    music*=np.clip(fade,0,1)
    soundtrack=WORK/"original-score.wav"
    with wave.open(str(soundtrack),"wb") as out:
        out.setnchannels(1);out.setsampwidth(2);out.setframerate(hz)
        out.writeframes((music.clip(-.9,.9)*32767).astype("<i2").tobytes())
    # One percussive stinger reused at key twists, original synthesis.
    st=np.arange(24000,dtype=np.float32)/hz
    rng=np.random.default_rng(705)
    whoosh=np.sin(2*np.pi*(190*st-60*st*st))
    tick=rng.standard_normal(len(st)).astype(np.float32)
    sfx=.25*whoosh*np.exp(-6*st)+.06*tick*np.exp(-22*st)
    sting=WORK/"original-stinger.wav"
    with wave.open(str(sting),"wb") as out:
        out.setnchannels(1);out.setsampwidth(2);out.setframerate(hz)
        out.writeframes((sfx.clip(-.95,.95)*32767).astype("<i2").tobytes())
    return soundtrack,sting

def build_preview(row:dict,audio:Path,seconds:float,captions:list[dict],
                  bg:list[Path],poses:dict[int,list[Path]],poseqa:dict,
                  voiceqa:dict)->dict:
    frames=round(seconds*FPS)
    cuts=previous.build_cuts(row,audio,frames)
    MEDIA.mkdir(parents=True,exist_ok=False)
    for i,source in enumerate(bg,1):
        shutil.copy2(source,MEDIA/("background-%02d.png"%i))
    for files in poses.values():
        for file in files:shutil.copy2(file,MEDIA/file.name)
    shutil.copy2(audio,MEDIA/"voice.mp3")
    score,sting=synthesize_original_score(seconds)
    shutil.copy2(score,MEDIA/"original-score.wav")
    shutil.copy2(sting,MEDIA/"original-stinger.wav")
    types=("close","wide","detail","wide","reaction","establish",
           "action","medium","close","final")
    roles=("hook","setup","detail","detail","rehook","twist",
           "detail","answer","rehook","answer")
    headers=("", "", "", "", "A SUSPEITA CONTINUA", "SURGE OUTRO KIRA",
             "", "", "SEM MEMÓRIAS", "")
    scenes=[]
    for i in range(SCENES):
        item="generated/otaku-v6-real-90s/background-%02d.png"%(i+1)
        scene={"id":"%02d"%(i+1),"subject":"personagens",
            "startFrame":cuts[i],"endFrame":cuts[i+1],
            "background":item,"foreground":item,
            "beatRole":roles[i],"shotType":types[i],
            "transitionStyle":"hard" if i in (0,4,5,8) else "crossfade"}
        if headers[i]:scene["headline"]=headers[i]
        if i in poses:
            files=poses[i]
            framesrc=["generated/otaku-v6-real-90s/"+x.name for x in files]
            scene["renderMode"]="multilayer"
            scene["layers"]=[{"id":"characters_%02d"%(i+1),
                  "role":"character","z":10,"src":framesrc[0],
                  "rigFrames":{"fps":.43,"frames":framesrc,
                  "playback":"pingpong" if i in (0,8) else "once"}}]
        else:
            scene["renderMode"]="master_static"
        scenes.append(scene)
    sfxat=[cuts[4],cuts[5],cuts[8]]
    cues=[{"src":"generated/otaku-v6-real-90s/original-stinger.wav",
           "startFrame":x,"endFrame":min(frames,x+26),"volume":.12}
          for x in sfxat]
    props={"id":EPISODE,"durationFrames":frames,
      "audio":"generated/otaku-v6-real-90s/voice.mp3",
      "scenes":scenes,"captions":captions,
      "hook":"L CONVIDOU O SUSPEITO?",
      "animationMode":"esqueleto2d","visualProfile":"otaku-v6-vertical",
      "characterPreset":"equilibrado",
      "backgroundMusic":{"src":"generated/otaku-v6-real-90s/original-score.wav","volume":.2},
      "soundCues":cues,"editorialProfile":"Otaku Multicena V6 - review only"}
    propsfile=WORK/"remotion-props-v6.json"
    propsfile.write_text(json.dumps(props,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    resultfile=WORK/"Otaku_Multicena_Death_Note_AutoEditorVideo_V6_90s.mp4"
    print("[OTAKU V6] REMOTION_REAL_V6_RENDER_START",flush=True)
    proc=subprocess.run(["npm","run","render:master","--",str(resultfile.resolve()),
               "--props",str(propsfile.resolve()),"--concurrency","2",
               "--codec","h264","--crf","19"],cwd=MOTION,
               capture_output=True,text=True,timeout=4200,check=False)
    if proc.returncode:
        print("[OTAKU V6] REMOTION_EXIT_%d"%proc.returncode,flush=True)
        raise V6Blocked("REMOTION_V6_RENDER_FAILED")
    if not resultfile.is_file() or resultfile.stat().st_size<1_000_000:
        raise V6Blocked("REAL_MP4_MISSING_OR_EMPTY")
    av=inspect_video(resultfile,duration_profile="short_90s_test")
    if not av.get("technical_audio_video_checked") or av.get("warnings"):
        raise V6Blocked("AUDIO_VIDEO_TECHNICAL_QA_NOT_PASSED")
    valid_animated_count=sum(1 for x in scenes if x["renderMode"]=="multilayer")
    if valid_animated_count<3:
        raise V6Blocked("NOT_ENOUGH_REVIEWABLE_CHARACTER_ANIMATIONS")
    REVIEW.mkdir(parents=True,exist_ok=False)
    shutil.copy2(resultfile,REVIEW/resultfile.name)
    with Image.open(bg[0]) as im:
        render_cover(im,"L CONVIDOU LIGHT?",REVIEW/"cover-v6.jpg",
                     focus_x=.5,focus_y=.4)
    shutil.copy2(propsfile,REVIEW/"remotion-props-v6.json")
    (REVIEW/"narration-script-v6.txt").write_text(row["narration_script"]+"\n",encoding="utf-8")
    report={
      "schema":"autoeditorvideo/90s-v6-authentic-preview/v1",
      "repo":"HelioConde/AutoEditorVideo","origin":"original Remotion, Edge TTS, gpt-image-2",
      "real_video_file":resultfile.name,"duration_seconds":av["duration_seconds"],
      "visual_profile":"full_bleed_9_16","visual_backgrounds":10,
      "animated_rgba_shots":valid_animated_count,
      "independent_rgba_pose_images":valid_animated_count*2,
      "generated_rgba_pose_images_before_qa":10,
      "actual_pose_qa":poseqa,"pose_frame_changes_real":True,
      "true_skeletal_2d_bones":False,
      "voice_segments":voiceqa,"voice_and_captions_real":True,
      "original_audio_score_and_sfx":True,"rendered_composition":"ArquivoOtakuMaster",
      "video_sha256":sha(resultfile),"av":av,
      "published":False,"youtube_uploads":0,"publishing_pause_unchanged":True,
      "humans_verified_identity_or_animation":False,"lore_reviewed_by_human":False,
      "copyright_rights_manually_approved":False,"ready_to_publish":False,
      "honest_limitations":"Foreground poses blend in 2D; no skeletal bones, lip sync or true 3D animation. Performance/visual score needs viewer inspection."
    }
    (REVIEW/"qa-v6.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("[OTAKU V6] REAL_NEW_MP4_READY_NO_YOUTUBE_UPLOAD",flush=True)
    return report

def main()->int:
    try:
        row=check_env(os.environ)
        if len(sys.argv)>1 and sys.argv[1]=="--preflight":
            print(json.dumps({"status":"V6_ONE_AUTHORIZED_OFFLINE_REVIEW_ONLY",
               "expected_image_calls":ART_REQUESTS,"youtube":False},ensure_ascii=False))
            return 0
        audio,duration,captions,voiceqa=compose_voice(row)
        print("[OTAKU V6] MEASURED_EXPRESSIVE_TTS_%.3f"%duration,flush=True)
        # Do not spend images if TTS is invalid or account is ineligible.
        key=proxy_key()
        check_proxy_accounts(key)
        bg,poses,poseqa=produce_art(row,key)
        build_preview(row,audio,duration,captions,bg,poses,poseqa,voiceqa)
        return 0
    except Exception as error:
        if isinstance(error,V6Blocked):
            print("[OTAKU V6 BLOCKED] "+str(error),file=sys.stderr)
        else:
            # Never print credentials or untrusted image-provider payloads.
            print("[OTAKU V6 BLOCKED] "+type(error).__name__,file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
