#!/usr/bin/env python3
"""One-shot original Alchemy anime dorama preview on GitHub Actions.

Uses existing protected gpt-image-2 image proxy, canonical fixed identity
reference assets and edits, Edge TTS and the isolated Remotion 2D stage.
Never updates source reference approval or publishes to YouTube. All images
are provisional until the creator visually reviews the MP4. Fail-closed.
"""
from __future__ import annotations

import asyncio
import base64
from hashlib import sha256
import io
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import wave

import requests
from PIL import Image, ImageOps
import edge_tts

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import alchemy_dorama_original as dorama

MODEL = "gpt-image-2"
API = "http://127.0.0.1:8080/v1/images"
TARGET = (1024, 1536)
BASE = {
"REN-01": (
"ORIGINAL Japanese television anime, anime isekai romance character model. "
"ONE young adult MAN 21 years old full body standing at rest, dark slightly messy short black hair, "
"warm amber brown eyes, a small vertical scar through LEFT eyebrow, pale tan skin, slender frame. "
"Clothing always: worn navy blue medieval tunic, beige undershirt, dark gray trousers, simple brown belt "
"with iron buckle and plain brown boots. Not a child, not real person. Clean expressive linework and "
"consistent cel shading, on genuine transparent PNG background, full figure including feet and hair, no weapons, no text."
),
"ELARA-01": (
"ORIGINAL premium anime fantasy romance character model, young adult princess 22 years old full body, "
"long silver hair with a narrow braid on the right side, violet-gray eyes, tiny beauty mark BELOW LEFT eye. "
"Identical silver tiara with one blue gemstone, elegant midnight navy-blue royal gown with silver embroidery "
"and long sleeves. Strong observant restrained facial expression, dignified posture. Genuine transparent "
"background, full figure including shoes and hair, cel shaded anime illustration. No text, no logos."
),
"VALDREN-01": (
"Original Japanese fantasy anime king character, adult male 52 years old, swept-back gray hair, short square "
"gray beard, sharp GREEN eyes. Gold royal crown with one large central ruby, burgundy mantle, black plate armor "
"with gold trim. Stern and authoritarian, full body on transparent background, premium 2D anime cel-shaded model, "
"no other people, no text, no logos."
),
"OREN-01": (
"Original anime medieval royal guard captain, adult man age 39, cropped dark brown hair, distinctive small "
"scar on RIGHT jawline, charcoal dark-steel armor with WHITE shield emblem in the center of breastplate, "
"straight posture, full body, transparent background, anime cel shading, no text."
),
"LUVA-01": (
"Anime mystery prop cutout: ONLY a LEFT HAND wearing a single black leather glove and a SILVER snake ring "
"set with one small red eye-shaped stone. Show wrist and fingers, no face, no body, no other props, "
"genuine transparent background, original anime cel-shaded closeup, no text."
),
"TRONO-01": (
"EMPTY interior of original medieval fantasy royal throne room, vertical portrait anime background without "
"any people, characters, knights or weapons. Symmetrical cool gray stone hall, marble floor engraved with "
"a large solar-circle symbol at FRONT CENTER, two tall blue stained glass windows, columns dressed with "
"burgundy banners. Weathered gold throne on exactly three stone steps at REAR CENTER, sunlight "
"from LEFT through windows, intricate consistent cinematic anime background painting. No text."
),
"ACADEMIA-01": (
"EMPTY original anime medieval knight academy training courtyard in 9:16 perspective, "
"rectangular dusty arena with three semicircular stone arches, BLUE banner with simple white lion silhouette, "
"stone tower in deep background, daylight, no people, no sword, clean anime environment background, no text."
),
"ARQUIVO-01": (
"EMPTY original anime medieval royal archive room, perspective consistent: exactly two tall oak bookcases "
"at back, wooden working table on LEFT foreground, round stained glass window centered rear, glass display "
"pedestal on RIGHT foreground (empty). Quiet moonlight through the window. 2D detailed anime background "
"painting, absolutely no people, no loose objects, no seal, no text."
),
"PROP-01": (
"One original fantasy royal gold seal medallion approximately 8cm diameter, front view anime cutout. "
"Raised engraving of a LION clearly LOOKING TO THE LEFT, a tiny diagonal CRACK at LOWER RIGHT rim. "
"Nothing else, transparent background, sharp detailed silhouette, NO letters or text."
),
"PROP-02": (
"One original fantasy royal counterfeit gold seal medallion approximately 8cm diameter, front view anime cutout. "
"Raised engraving of a LION clearly LOOKING TO THE RIGHT, smooth intact rim with NO CRACK. "
"Nothing else, transparent background, crisp detailed silhouette, NO letters or text."
),
"PROP-03": (
"Single long medieval executioner's sword, dark steel blade, straight guard, dark handle wrapped in exactly "
"three brown leather bands. Full sword, no hand or person, genuine transparent anime object cutout, no text."
),
}
POSE_PROMPTS = {
"REN-01-ajoelhado":"Change ONLY pose to both knees on ground, terrified exhausted body and raised face; same outfit, face, scar, hair. Full body.",
"REN-01-treinando":"Same Ren full-body pose struggling with a simple wooden practice sword, feet apart, shoulders slumped, determined expression. Do not change face, hair, scar, outfit.",
"REN-01-trabalhando":"Same Ren full-body leaning slightly forward inspecting an invisible display case at waist height, open palms near waist, same costume and scar. NO actual seal added.",
"REN-01-assustado":"Same Ren full-body eyes wide, startled expression, one hand near chest looking at invisible floating screen. Identical face, body, outfit, scar.",
"REN-01-apontando":"Same Ren kneeling on both knees and extending his RIGHT arm pointing forward, frightened but determined, identical full body and clothes, no extra fingers.",
"ELARA-01-observando":"Same princess standing with hands gently clasped, skeptical stare, original gown tiara hair beauty mark, no other changes.",
"ELARA-01-firme":"Same princess confidently extending one arm with palm outward ordering an execution to STOP, identical outfit, tiara, hair and beauty mark.",
"VALDREN-01-julgando":"Same king pointing one accusing hand down toward prisoner, stern anger, identical crown mantle face and armor. Full figure."
}

VOICE = {"NARRADOR":"pt-BR-AntonioNeural","REN":"pt-BR-FabioNeural",
         "VALDREN":"pt-BR-HumbertoNeural","ELARA":"pt-BR-FranciscaNeural",
         "OREN":"pt-BR-DonatoNeural","INSTRUTOR":"pt-BR-HumbertoNeural",
         "SISTEMA":"pt-BR-BrendaNeural"}
FRAME_RATE = 30
OUTPUT = ROOT / "assets/gerados/alchemy-dorama-original/ep01"
ART = ROOT / "assets/gerados/alchemy-dorama-original/referencias"
PUBLIC = ROOT / "motion-remotion/public/generated/alchemy-dorama-original/ep01"
PREVIEW = OUTPUT / "preview-para-revisao.mp4"
MAX_REQUESTS = 19


class PilotError(Exception):
    pass


def safe_request(key: str, prompt: str, transparent: bool, parent: Path|None) -> bytes:
    payload = {"model": MODEL, "prompt": prompt, "n": 1,
               "size": "1024x1536", "background": "transparent" if transparent else "opaque",
               "output_format": "png"}
    endpoint = "generations"
    if parent is not None:
        endpoint = "edits"
        b64 = base64.b64encode(parent.read_bytes()).decode("ascii")
        payload["images"] = [{"image_url": "data:image/png;base64,"+b64}]
    try:
        resp = requests.post(API + "/" + endpoint, json=payload,
                             headers={"Authorization": "Bearer "+key},
                             timeout=(15, 360))
    except requests.RequestException as exc:
        raise PilotError("IMAGE_PROVIDER_UNREACHABLE") from None
    if resp.status_code != 200:
        raise PilotError("IMAGE_PROVIDER_HTTP_"+str(resp.status_code))
    try:
        obj = resp.json()["data"][0]
        encoded = obj.get("b64_json") or obj.get("url")
        if encoded.startswith("data:image/"):
            encoded = encoded.split(",",1)[1]
        if encoded.startswith("http"):
            raise PilotError("REMOTE_IMAGE_NOT_ALLOWED")
        binary = base64.b64decode(encoded, validate=True)
        if len(binary) > 25_000_000:
            raise PilotError("IMAGE_EXCEEDS_MAX_SIZE")
    except (TypeError,KeyError,ValueError,IndexError) as exc:
        raise PilotError("IMAGE_BAD_RESPONSE") from None
    return binary


def check_normalize(blob: bytes, *, transparent:bool) -> bytes:
    try:
        with Image.open(io.BytesIO(blob)) as inp:
            inp.load()
            if inp.format != "PNG" or min(inp.size)<512:
                raise PilotError("IMAGE_NOT_VALID_PNG")
            if transparent and inp.mode!="RGBA":
                raise PilotError("IMAGE_NOT_RGBA")
            if inp.size != TARGET:
                inp = ImageOps.pad(inp.convert("RGBA" if transparent else "RGB"),TARGET,
                   method=Image.Resampling.LANCZOS,color=(0,0,0,0) if transparent else (0,0,0))
            else:
                inp = inp.copy()
            if transparent:
                alpha = inp.getchannel("A")
                lo, hi = alpha.getextrema()
                if lo>25 or hi<200:
                    raise PilotError("IMAGE_ALPHA_MISSING")
            dst = io.BytesIO()
            inp.save(dst,format="PNG")
            return dst.getvalue()
    except (OSError,ValueError):
        raise PilotError("IMAGE_PNG_DECODE_FAILED") from None


def image_stage():
    reuse_only = os.environ.get("ALCH_DORAMA_REUSE_ONLY") == "1"
    if reuse_only:
        if os.environ.get("MAX_IMAGE_CALLS") != "0":
            raise PilotError("REUSE_MUST_HAVE_ZERO_IMAGE_BUDGET")
    else:
        if os.environ.get("MAX_IMAGE_CALLS") != str(MAX_REQUESTS):
            raise PilotError("IMAGE_REQUEST_BUDGET_MISMATCH")
        if os.environ.get("IMAGE_MODEL") != MODEL:
            raise PilotError("IMAGE_MODEL_NOT_APPROVED")
    key = "" if reuse_only else os.environ.get("PROXY_API_KEY","")
    if not reuse_only and len(key)<15:
        raise PilotError("IMAGE_PROXY_KEY_NOT_PRESENT")
    reference_doc = dorama.read_json(dorama.MANIFEST)
    storyboard = dorama.read_json(dorama.BOARD)
    dorama.check_storyboard(storyboard)
    needed=dorama.needed_keys(storyboard)
    needed.discard("CORREDOR-01")
    manifest = {r["id"]:r for r in reference_doc["entries"]}
    ordered=[id for id in BASE if id in needed]+[id for id in POSE_PROMPTS if id in needed]
    if len(ordered)>MAX_REQUESTS or set(ordered)!=needed:
        raise PilotError("REFERENCE_PROMPT_COVERAGE_MISMATCH")
    ART.mkdir(parents=True,exist_ok=True)
    proofs={}
    for i,id in enumerate(ordered,1):
        entry=manifest[id]
        src_id=entry.get("source_id")
        parent=ART/(src_id+".png") if src_id else None
        if src_id and (not parent or not parent.exists()):
            raise PilotError("PARENT_SOURCE_MISSING")
        if src_id:
            prompt=("EDIT ONLY this attached ORIGINAL anime character to a new POSE. "
                    "Use exact same face, identity, skin, hairstyle, eye color, costume "
                    "and proportions. Preserve full anatomy, no copied clones or added "
                    "objects. Transparent background. "+POSE_PROMPTS[id])
        else:
            prompt=BASE[id]
        transparent=entry["kind"]!="cenario"
        raw_file=ART/(id+".raw.png")
        normalized=ART/(id+".png")
        if normalized.exists():
            try:
                image_bytes = normalized.read_bytes()
                with Image.open(io.BytesIO(image_bytes)) as img:
                    img.load()
                    if img.format != "PNG" or img.size != TARGET:
                        raise PilotError("CACHE_INVALID_PNG_"+id)
                    if transparent and (img.mode != "RGBA" or img.getchannel("A").getextrema()[0] > 25):
                        raise PilotError("CACHE_MISSING_ALPHA_"+id)
                if src_id and not parent.exists():
                    raise PilotError("CACHE_PARENT_MISSING_"+id)
            except (OSError,ValueError):
                raise PilotError("CACHE_PNG_CORRUPTED_"+id) from None
        else:
            if reuse_only:
                raise PilotError("REUSE_ASSET_MISSING_"+id)
            binary=safe_request(key,prompt,transparent,parent)
            raw_file.write_bytes(binary)  # retain paid source before validation
            normalized.write_bytes(check_normalize(binary,transparent=transparent))
        proofs[id]={
            "sha256":sha256(normalized.read_bytes()).hexdigest(),
            "parent_id":src_id,
            "parent_sha256":sha256(parent.read_bytes()).hexdigest() if parent else None,
            "quality_review":"pending_visual_human_review",
        }
        print("[REF] "+str(i)+"/"+str(len(ordered))+" -> "+id+(" reused" if reuse_only else " available")+", artistic QA pending",flush=True)
    return proofs


async def create_voice(lines: list[dict], path: Path):
    if path.exists():
        return
    path.parent.mkdir(parents=True,exist_ok=True)
    # Microsoft Edge TTS is a separate free TTS network dependency; no Google/YouTube tokens.
    for attempt, rate in enumerate(("", "+8%")):
        try:
            speaker = lines[0]["speaker"]
            voice = VOICE.get(speaker,VOICE["NARRADOR"])
            communic = edge_tts.Communicate(" ".join(item["text"] for item in lines),
                                           voice=voice,rate=rate)
            await communic.save(str(path))
            if path.stat().st_size < 1000:
                raise PilotError("TTS_EMPTY_AUDIO")
            return
        except Exception:
            path.unlink(missing_ok=True)
            if attempt == 1:
                raise PilotError("TTS_SERVICE_UNAVAILABLE") from None


def clip_pcm(path:Path) -> bytes:
    proc = subprocess.run(["ffmpeg","-y","-v","error","-i",str(path),
                           "-f","s16le","-ac","1","-ar","24000","-"],
                           capture_output=True,check=True)
    return proc.stdout


async def voice_stage(board:dict) -> tuple[list[float],list[dict]]:
    OUTPUT.mkdir(parents=True,exist_ok=True)
    tempdir = OUTPUT / "voice_segments"
    tempdir.mkdir(exist_ok=True)
    clips=[]
    for s in board["scenes"]:
        # Scene-level voice by first speaker with full exact text. No words omitted.
        target=tempdir/("scene-"+str(s["number"]).zfill(2)+".mp3")
        await create_voice(s["spoken_lines"], target)
        clips.append(clip_pcm(target))
    durations=[len(b)/2/24000 for b in clips]
    # Preserve scene order, retain pauses, no temporal compression.
    natural=[d+.42 for d in durations]
    if sum(natural)>175:
        raise PilotError("NARRATION_EXCEEDS_175_SECONDS_EDIT_SCRIPT_FIRST")
    remaining=175-sum(natural)
    weights=[float(s["end_second"]-s["start_second"]) for s in board["scenes"]]
    scene_durations=[x+remaining*w/sum(weights) for x,w in zip(natural,weights)]
    lengths=[max(1,round(seconds*FRAME_RATE)) for seconds in scene_durations]
    delta=175*FRAME_RATE-sum(lengths)
    lengths[-1]+=delta
    audio=bytearray(175*24000*2)
    times=[]
    begin_frame=0
    for i,(clip,count) in enumerate(zip(clips,lengths)):
        start_sample=round(begin_frame/FRAME_RATE*24000)
        end_sample=start_sample+len(clip)//2
        if end_sample>len(audio)//2 or len(clip)>count*24000*2/FRAME_RATE:
            raise PilotError("VOICE_SPAN_EXCEEDS_SCENE_DURATION")
        audio[2*start_sample:2*end_sample]=clip
        times.append({"scene_number":i+1,"startFrame":begin_frame,
                      "endFrame":begin_frame+count,
                      "narration_seconds":round(durations[i],2)})
        begin_frame+=count
    wav=OUTPUT/"narracao.wav"
    with wave.open(str(wav),"wb") as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(audio)
    out=OUTPUT/"narracao.mp3"
    subprocess.run(["ffmpeg","-y","-v","error","-i",str(wav),
                    "-codec:a","libmp3lame","-qscale:a","3",str(out)],check=True)
    if not out.exists() or out.stat().st_size < 50000:
        raise PilotError("NARRATION_NOT_CREATED")
    return durations,times


def compose(board:dict,times:list[dict]):
    PUBLIC.mkdir(parents=True,exist_ok=True)
    # Render using the very same composition implemented in the repo,
    # with provisional assets in an isolated Actions working directory.
    for name in dorama.needed_keys(board):
        shutil.copy2(ART/(name+".png"),PUBLIC/(name+".png"))
    shutil.copy2(OUTPUT/"narracao.mp3",PUBLIC/"narracao.mp3")
    shots=[]
    captions=[]
    for shot,timespan in zip(board["scenes"],times):
        num=shot["number"];bg=shot["background_anchor"]
        sprites=[]
        for parent in shot["character_anchors"]+[
            x for x in shot["item_anchors"] if x not in ("UI-01","UI-02")
        ]:
            pose=dorama.selected_asset(num,parent)
            if parent not in dorama.POSITIONS.get(bg,{}):
                raise PilotError("STAGE_MISSING_CHARACTER_POSITION")
            x,y,width,z=dorama.POSITIONS[bg][parent]
            sprites.append({"anchorId":parent,
                 "poseAssetId":pose,
                 "image":"generated/alchemy-dorama-original/ep01/"+pose+".png",
                 "x":x,"y":y,"width":width,"zIndex":z,
                 "motion":dorama.MOTIONS.get((num,parent),"still")})
        timeline={
            "number":num,
            "startFrame":timespan["startFrame"],
            "endFrame":timespan["endFrame"],
            "backgroundAnchor":bg,
            "background":"generated/alchemy-dorama-original/ep01/"+bg+".png",
            "timeLayer":shot["time_layer"],
            "flashbackLabel":(
                "7 DIAS ANTES" if num==3 else "NAQUELA NOITE" if num==6 else ""
            ),
            "cameraMotion":dorama.CAMERAS.get(num,"still"),
            "sprites":sprites,"systemPanel":dorama.PANELS.get(num),
            "effect":"tension" if num in (1,9,16) else "none",
        }
        shots.append(timeline)
        text=" ".join(line["text"] for line in shot["spoken_lines"])
        if text:
            captions.append({"startFrame":timespan["startFrame"],
                             "endFrame":min(timespan["endFrame"],
                               timespan["startFrame"]+
                               max(1,round(timespan["narration_seconds"]*FRAME_RATE))),
                             "text":text[:135]+"…" if len(text)>135 else text})
    props={"episodeId":dorama.EPISODE,
           "title":board["episode_title"],"durationFrames":5250,
           "scenes":shots,"captions":captions,
           "audio":"generated/alchemy-dorama-original/ep01/narracao.mp3"}
    props_file=ROOT/"motion-remotion/props-alchemy-dorama-cloud-pilot.json"
    props_file.write_text(json.dumps(props,ensure_ascii=False,indent=2),encoding="utf-8")
    return props_file


def render(props:Path,proofs:dict, dur:list[float]) -> dict:
    runner=ROOT/"motion-remotion"
    PREVIEW.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run(["npx","remotion","render","src/index.ts","AlchemyDoramaOriginal",
                    str(PREVIEW.resolve()),"--props",str(props.resolve()),
                    "--codec","h264","--concurrency","2","--log","error"],
                   cwd=runner,check=True,timeout=3600)
    info=subprocess.run(["ffprobe","-v","error","-of","json","-show_streams",
                         "-show_format",str(PREVIEW)],capture_output=True,
                         text=True,check=True)
    obj=json.loads(info.stdout)
    video=next((x for x in obj["streams"] if x["codec_type"]=="video"),None)
    audio=next((x for x in obj["streams"] if x["codec_type"]=="audio"),None)
    d=float(obj["format"]["duration"])
    if not video or not audio or (video["width"],video["height"])!=(1080,1920):
        raise PilotError("FINAL_VIDEO_MISSING_VIDEO_OR_AUDIO_OR_WRONG_DIMENSIONS")
    if not 150<=d<=180:
        raise PilotError("FINAL_VIDEO_DURATION_MISMATCH")
    return {"schema":"alchemy-dorama-real-cloud-preview/v1","channel":"alchemy",
            "episode_id":dorama.EPISODE,
            "duration_seconds":round(d,2),"shots":16,
            "video_sha256":sha256(PREVIEW.read_bytes()).hexdigest(),
            "reference_sha256":proofs,"voice_segment_duration_seconds":dur,
            "status":"real_ai_original_art_unreviewed_preview",
            "artistic_human_review":"PENDING",
            "music":"none","youtube_uploads":0,
            "youtube_publication_authorized":False,
            "visual_reference_approval":"PENDING",
            "file":str(PREVIEW.relative_to(ROOT))}


def main():
    try:
        board=dorama.read_json(dorama.BOARD)
        dorama.check_storyboard(board)
        proofs=image_stage()
        print("[PILOTO] ORIGINAL_ART_RECEIVED",len(proofs),flush=True)
        durations,times=asyncio.run(voice_stage(board))
        props=compose(board,times)
        report=render(props,proofs,durations)
        (OUTPUT/"qa-preview.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("[PILOTO] MP4_RENDERED_FOR_REVIEW_NOT_PUBLISHED",flush=True)
        return 0
    except PilotError as exc:
        print("[PILOTO BLOQUEADO] "+str(exc),file=sys.stderr)
        return 1
    except FileNotFoundError:
        print("[PILOTO BLOQUEADO] MISSING_REQUIRED_FILE_OR_EXECUTABLE",file=sys.stderr)
        return 1
    except subprocess.CalledProcessError:
        print("[PILOTO BLOQUEADO] MEDIA_COMMAND_FAILED",file=sys.stderr)
        return 1
    except Exception as exc:
        # Keep provider secrets, exact filenames and foreign exception bodies out of logs.
        print("[PILOTO BLOQUEADO] INTERNAL_STAGE_FAILED_TYPE_"+type(exc).__name__,file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
