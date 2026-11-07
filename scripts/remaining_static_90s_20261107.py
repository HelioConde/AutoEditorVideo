#!/usr/bin/env python3
"""Remaining 9 reserved AutoEditorVideo 90-120s Shorts, original STATIC artwork.

Three channel-isolated batches: Otaku Reframe EN, Gamer BR, Alchemy BR.
Uses original Remotion MasterShort, genuine Edge WordBoundary captions and
original cover generator. Does NOT use the Fofinhos or Kids assets.
"""
from __future__ import annotations

import argparse
import io
import json
import os
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from production_reservations import assert_reserved
from youtube_channel_registry import KNOWN_IDS
from narracao_shorts import ensure_voice
from legendas_precisas import captions_from_markers
from capa_cinematografica import render_cover
from kids_static_90s_20261107 import digest, run, probe, duration, story_cuts

PLAN=ROOT/"conteudos"/"lote-12-estatico-90s-20261107.json"
MOTION=ROOT/"motion-remotion"
OWNER="lote12_static_original_20261107"
WORKFLOW="AutoEditorVideo - 9 original static 90s Shorts three channels private"
IMAGE_MODEL="gpt-image-2"
FPS=30
IMAGE_BUDGET=24
EXPECTED={
    "en":("7011-noelle-black-clover","7012-maomao-apothecary","7013-shizuku-hunter"),
    "games":("game-101-minecraft-agua","game-102-roblox-obby","game-103-minecraft-creeper"),
    "alchemy":("alchemy-101-video-ia-realidade","alchemy-102-agentes-chatbot","alchemy-103-prompt-consistencia"),
}
TOKENS={"en":"YOUTUBE_EN_TOKEN_JSON","games":"YOUTUBE_GAMES_TOKEN_JSON","alchemy":"YOUTUBE_ALCHEMY_TOKEN_JSON"}
OUTPUT_ROOT=ROOT/"cloud-remaining-static-20261107"
VOICES={"en":"en-US-AriaNeural","games":"pt-BR-AntonioNeural","alchemy":"pt-BR-FranciscaNeural"}
CATEGORY={"en":"24","games":"20","alchemy":"28"}
PROFILE={"en":"original","games":"gamer-alchemy-reference","alchemy":"gamer-alchemy-reference"}
COVER={"en":"default","games":"gamer-alchemy-reference","alchemy":"gamer-alchemy-reference"}

class RemainingBlocked(ValueError):pass

def output(channel:str)->Path:
    return OUTPUT_ROOT/channel

def validate(channel:str)->list[dict]:
    if channel not in EXPECTED:
        raise RemainingBlocked("UNKNOWN_OR_KIDS_BR_CHANNEL_FORBIDDEN")
    d=json.loads(PLAN.read_text(encoding="utf-8"))
    if (d.get("schema")!="autoeditorvideo/lote-12-estatico-90s/v1"
            or d.get("production_owner")!=OWNER or d.get("target_total")!=12
            or d.get("excluded_channels")!=["br"]
            or len(d.get("episodes",[]))!=12):
        raise RemainingBlocked("ORIGINAL_12_VIDEO_MANIFEST_CHANGED")
    selected=[r for r in d["episodes"] if r.get("channel")==channel]
    if tuple(r.get("id") for r in selected)!=EXPECTED[channel]:
        raise RemainingBlocked("EXACT_THREE_ORDER_AND_IDS_REQUIRED")
    if d.get("privacy_if_uploaded") not in ("private",None):
        raise RemainingBlocked("PUBLICATION_NOT_PRIVATE")
    for row in selected:
        assert_reserved(channel,row["id"],OWNER)
        if (row.get("channel_id")!=KNOWN_IDS[channel]
                or row.get("made_for_kids") is not False
                or row.get("language")!=("en-US" if channel=="en" else "pt-BR")
                or row.get("production_state",{}).get("upload")!="not_started"):
            raise RemainingBlocked("CHANNEL_ID_LANGUAGE_OR_RESERVATION_MISMATCH")
        if (len(row.get("scenes",[]))!=8 or len(row.get("narration_script","").split())<240
                or not all(s.get("visual_instruction") and s.get("editorial_beat")
                           for s in row["scenes"])):
            raise RemainingBlocked("EDITORIAL_STORY_NOT_8_SCENES")
        if (not 1<=len(row.get("cover_text",""))<=42
                or not 1<=len(row.get("title",""))<=100
                or not row.get("description","")
                or not row.get("tags") or len(",".join(row["tags"]))>500):
            raise RemainingBlocked("SEO_OR_COVER_INVALID")
        if channel=="games" and "não são capturas de gameplay" not in row["description"].lower():
            raise RemainingBlocked("GAMEPLAY_DISCLOSURE_MISSING")
        if channel=="alchemy" and "ia" not in row["description"].lower():
            raise RemainingBlocked("AI_DISCLOSURE_MISSING")
    return selected

def environment_guard(channel:str)->None:
    e=os.environ
    if (e.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo"
            or e.get("GITHUB_REF")!="refs/heads/main"
            or e.get("GITHUB_EVENT_NAME")!="push"
            or e.get("GITHUB_RUN_ATTEMPT")!="1"
            or e.get("GITHUB_WORKFLOW")!=WORKFLOW
            or e.get("REMAINING_CHANNEL")!=channel
            or e.get("REMAINING_STATIC_BATCH_AUTHORIZED")!="yes"
            or e.get("IMAGE_MODEL")!=IMAGE_MODEL
            or e.get("MAX_IMAGE_CALLS")!=str(IMAGE_BUDGET)):
        raise RemainingBlocked("MAIN_ONE_SHOT_CHANNEL_OR_IMAGE_BUDGET_GUARD_FAILED")
    if (e.get("YOUTUBE_CLIENT_JSON") or e.get("YOUTUBE_CHANNEL_TOKEN_JSON")
            or e.get("YOUTUBE_BR_TOKEN_JSON") or e.get("YOUTUBE_KIDS_TOKEN_JSON")):
        raise RemainingBlocked("YOUTUBE_CREDENTIALS_NOT_ALLOWED_IN_RENDER")

def voice_takes(row:dict,folder:Path,channel:str)->tuple[Path,float,list[dict]]:
    import narracao_shorts as ns
    rate=0
    for attempt in range(4):
        ns.RATE="%+d%%"%rate
        take=folder/("tts-%d"%(attempt+1))
        mp3,_=ensure_voice({"script":row["narration_script"]},take,create=True,
                           engine="edge",voice=VOICES[channel])
        sec=duration(mp3)
        if not 60<=sec<=210:
            raise RemainingBlocked("TTS_VOICE_DURATION_IMPLAUSIBLE")
        print("REMAINING_TTS_%s_TAKE_%d_SECONDS_%.2f"%(row["id"],attempt+1,sec),flush=True)
        if 90<=sec<=120:
            data=json.loads((take/"marcacoes-voz.json").read_text(encoding="utf-8"))
            words=data.get("words",[])
            captions=captions_from_markers(mp3,row["narration_script"],sec,fps=FPS)
            if not captions or len(captions)<35 or len(words)<200:
                raise RemainingBlocked("REAL_WORD_CAPTION_MARKERS_MISSING")
            return mp3,sec,words
        speed=round(((1+rate/100)*(sec/105)-1)*100)
        if abs(speed-rate)<2:
            speed=rate+(4 if sec>120 else -4)
        rate=max(-25,min(35,speed))
    raise RemainingBlocked("VOICE_DURATION_90_120_NOT_ACHIEVED")

def prompt(row:dict,scene:dict,channel:str)->str:
    lead=(
        "Create ONE exceptionally clean original STILL FRAME vertical 1024x1536 "
        "for an informative 9:16 YouTube Short. Premium original cinematic editorial "
        "illustration, cohesive clear color design, beautiful realistic light, "
        "deliberate art direction, well-separated recognizable objects, detailed "
        "non-distorted anatomy. Do not copy official screenshots, anime frames, "
        "gameplay captures, logos, title cards or commercial characters verbatim. "
        "Do NOT render text, branding, copyright symbols, overlaid lettering, "
        "UI screenshots, or watermarks. Avoid hands with extra fingers, face merges, "
        "split heads, tilting limbs, visual corruption, or unnatural morphing. "
        "Subject stays within central 65% height with clear title and caption "
        "safe zones at top and bottom. The camera is 100% STILL. "
    )
    if channel=="en":
        lead+=("Independent English anime commentary using ORIGINAL symbolic illustrations; "
               "do not reproduce anime frames or protected designs. "
               "Mood: premium thoughtful Japanese fantasy editorial art, not stock photography. ")
        if row["id"].startswith("7011-"):
            lead+=("Visual bible for this episode: royal BLUE water motifs, armored "
                   "female-mage silhouette with blue light, ethereal aquatic spirit, "
                   "avoid brand-specific costume copying; follow scene instructions. ")
        elif row["id"].startswith("7012-"):
            lead+=("Visual bible: richly detailed historic East Asian palace interiors, "
                   "green herb jars, clues, humble observant apothecary, soft mystery light. ")
        else:
            lead+=("Visual bible: mysterious dark-haired young conjurer and a clearly stylized "
                   "purple household vacuum object, deep violet magical energy, clean symmetry. ")
    elif channel=="games":
        lead+=("Conceptual game-themed ORIGINAL artwork, NOT actual gameplay, "
               "not interface screenshot or false evidence of play/testing. "
               "Blocky voxel environments for Minecraft topics or abstract "
               "colorful platforming obstacle-course environments for Roblox topic. "
               "For creeper theme a distinctive ominous green blocky silhouette "
               "from a respectful distance; no copied 3D game screenshot. ")
    else:
        lead+=("Contemporary original AI and technology explainer illustrations, "
               "visual metaphors and large recognizable shapes; no fabricated "
               "screenshots of tools, no faked results or product interfaces. "
               "Simple clear thematic contrast, premium science magazine aesthetic. ")
    return lead+"Specific single frame to illustrate this narrated paragraph: "+scene["visual_instruction"]

def images(row:dict,folder:Path,key:str,channel:str)->list[Path]:
    from PIL import Image,ImageOps
    from gerar_video_codex import request_image
    results=[]
    for n,scene in enumerate(row["scenes"],1):
        dest=folder/("scene-%02d.png"%n)
        if dest.exists():
            raise RemainingBlocked("IMAGE_CACHE_EXISTS_UNVERIFIED")
        raw=request_image(prompt(row,scene,channel),IMAGE_MODEL,key,"1024x1536")
        with Image.open(io.BytesIO(raw)) as im:
            im.load()
            if im.width<512 or im.height<768:
                raise RemainingBlocked("GENERATED_IMAGE_TOO_SMALL")
            ImageOps.pad(im.convert("RGB"),(1024,1536),
                         method=Image.Resampling.LANCZOS,
                         color=(18,24,43)).save(dest,"PNG")
        if dest.stat().st_size<30000:
            raise RemainingBlocked("GENERATED_IMAGE_EMPTY")
        results.append(dest)
        print("REMAINING_NEW_ART_%s_%02d_OF_08"%(row["id"],n),flush=True)
    if len({digest(p) for p in results})!=8:
        raise RemainingBlocked("DUPLICATE_AI_ILLUSTRATIONS")
    return results

def render_one(row:dict,folder:Path,voice:Path,sec:float,words:list[dict],
               images:list[Path],channel:str)->dict:
    from PIL import Image
    ns="remaining-static-20261107/"+channel+"/"+row["id"]
    public=MOTION/"public"/"generated"/ns
    if public.exists():
        raise RemainingBlocked("STATIC_RENDER_ASSET_NAMESPACE_EXISTS")
    public.mkdir(parents=True,exist_ok=False)
    for n,img in enumerate(images,1):
        shutil.copy2(img,public/("scene-%02d.png"%n))
    shutil.copy2(voice,public/"voz-master.mp3")
    cuts=story_cuts(row,words,sec)
    captions=captions_from_markers(voice,row["narration_script"],sec,fps=FPS)
    if not captions or any(len(c["words"])>3 for c in captions):
        raise RemainingBlocked("ALIGNED_WORD_CAPTIONS_NOT_VALID")
    scenes=[]
    for n in range(8):
        url="generated/"+ns+"/scene-%02d.png"%(n+1)
        scenes.append({"id":"%02d"%(n+1),"subject":"objeto","startFrame":cuts[n],
                       "endFrame":cuts[n+1],"background":url,"foreground":url,
                       "renderMode":"master_static","transitionStyle":"crossfade",
                       "shotType":"wide" if n%2==0 else "detail",
                       "beatRole":"setup" if n<2 else "answer"})
    props={"id":row["id"],"durationFrames":round(sec*FPS),
           "audio":"generated/"+ns+"/voz-master.mp3","scenes":scenes,
           "captions":captions,"hook":row["cover_text"] if channel!="en" else "",
           "visualProfile":PROFILE[channel],"animationMode":"desligada",
           "characterPreset":"equilibrado","editorialProfile":"original-static-no-rig",
           "soundCues":[]}
    p=folder/"props.json"
    p.write_text(json.dumps(props,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    mp4=folder/"final.mp4"
    run(["npm","run","render:master","--",str(mp4.resolve()),
         "--props",str(p.resolve()),"--concurrency","2","--codec","h264",
         "--crf","22"],cwd=MOTION,timeout=6000)
    cover=folder/"thumb.jpg"
    with Image.open(images[0]) as im:
        result=render_cover(im,row["cover_text"],cover,zoom=1.0,
                            focus_x=.5,focus_y=.4,template=COVER[channel])
    if result["size"]!=[1080,1920]:
        raise RemainingBlocked("OFFICIAL_COVER_WRONG_DIMENSIONS")
    data=probe(mp4)
    seconds=float(data["format"]["duration"])
    vs=[v for v in data["streams"] if v.get("codec_type")=="video"]
    audio_streams=[a for a in data["streams"] if a.get("codec_type")=="audio"]
    if (not 90<=seconds<=121 or abs(seconds-sec)>2.5 or len(vs)!=1
            or not audio_streams or vs[0].get("width")!=1080
            or vs[0].get("height")!=1920 or mp4.stat().st_size<300000):
        raise RemainingBlocked("VIDEO_DURATION_RESOLUTION_OR_AUDIO_QA_FAILED")
    with Image.open(cover) as im:
        if im.format!="JPEG" or im.size!=(1080,1920):
            raise RemainingBlocked("COVER_JPEG_1080_1920_FAILED")
    qa={"schema":"autoeditorvideo/remaining-static-original-90s-qa/v1",
        "channel":channel,"channel_id":KNOWN_IDS[channel],"episode_id":row["id"],
        "duration":round(seconds,3),"tts_seconds":round(sec,3),
        "video_dimensions":[1080,1920],"word_boundaries_synced":True,
        "image_count":8,"image_sha256":[digest(p) for p in images],
        "mp4_sha256":digest(mp4),"cover_sha256":digest(cover),
        "visual_profile":PROFILE[channel],"cover_template":COVER[channel],
        "character_warp_mesh_animation":False,"manual_visual_review":False,
        "automated_technical_qa":"passed","youtube_upload":"not_performed"}
    metadata={"id":row["id"],"channel":channel,"channel_id":KNOWN_IDS[channel],
              "title":row["title"],"description":row["description"],
              "tags":row["tags"],"categoryId":CATEGORY[channel],
              "defaultLanguage":row["language"],"selfDeclaredMadeForKids":False,
              "containsSyntheticMedia":True,"privacyStatus":"private",
              "mp4_sha256":qa["mp4_sha256"],"cover_sha256":qa["cover_sha256"]}
    (folder/"qa.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",
                                  encoding="utf-8")
    (folder/"metadata.json").write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+"\n",
                                        encoding="utf-8")
    print("REMAINING_STATIC_MP4_QA_PASSED_"+row["id"],flush=True)
    return {"id":row["id"],"duration":round(seconds,2),
            "mp4_sha256":qa["mp4_sha256"],"cover_sha256":qa["cover_sha256"]}

def produce(channel:str)->None:
    environment_guard(channel)
    rows=validate(channel)
    out=output(channel)
    if out.exists():
        raise RemainingBlocked("OUTPUT_ALREADY_EXISTS_REFUSE_DUPLICATE_RENDER")
    out.mkdir(parents=True,exist_ok=False)
    ready=[]
    for row in rows:
        folder=out/row["id"]
        folder.mkdir()
        voice,sec,words=voice_takes(row,folder,channel)
        ready.append((row,folder,voice,sec,words))
    from gerar_video_codex import proxy_key,check_proxy_accounts
    key=proxy_key()
    check_proxy_accounts(key)
    summary={"schema":"autoeditorvideo/remaining-three-static-original-90s-batch/v1",
             "owner":OWNER,"channel":channel,"target_channel_id":KNOWN_IDS[channel],
             "artifact_state":"rendered_upload_not_performed",
             "render_engine":"AutoEditorVideo/ArquivoOtakuMaster",
             "cover_engine":"AutoEditorVideo/capa_cinematografica",
             "video_count":3,"videos":[]}
    for row,folder,voice,sec,words in ready:
        arts=images(row,folder,key,channel)
        result=render_one(row,folder,voice,sec,words,arts,channel)
        summary["videos"].append(result)
        # All uploaded assets are generated fresh, never licensed or private reference photos.
        for art in arts:
            art.unlink()
        for folder_tts in folder.glob("tts-*"):
            if folder_tts.is_dir():
                shutil.rmtree(folder_tts)
        props=folder/"props.json"
        props.unlink(missing_ok=True)
    if len(summary["videos"])!=3:
        raise RemainingBlocked("PARTIAL_BATCH_DO_NOT_UPLOAD")
    (out/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,
                                               indent=2)+"\n",encoding="utf-8")
    print("REMAINING_THREE_RENDERED_FOR_PRIVATE_UPLOAD_"+channel,flush=True)

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--channel",required=True,choices=EXPECTED)
    p.add_argument("--action",choices=("validate","render"),default="validate")
    args=p.parse_args()
    try:
        if args.action=="validate":
            print("REMAINING_EDITORIAL_RESERVED_3_"+args.channel+"_"+
                  ",".join(r["id"] for r in validate(args.channel)))
        else:
            produce(args.channel)
        return 0
    except Exception as exc:
        message=str(exc) if isinstance(exc,RemainingBlocked) else type(exc).__name__
        print("REMAINING_RENDER_BLOCKED_"+message,file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
