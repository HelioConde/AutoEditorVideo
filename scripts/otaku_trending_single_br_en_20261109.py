#!/usr/bin/env python3
"""Two unique trend-responsive original Shorts, BR Straw Hats and EN JoJo Part 7 OP.

Strictly private-first upload. Eight canonical character-anchored image edits
per episode, fresh original editorial art, real Edge TTS word timestamps,
Remotion 1080x1920 under 60 seconds. Never reuse official footage or SPIN audio.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from production_reservations import assert_reserved
from youtube_channel_registry import KNOWN_IDS
from otaku_character_identity_policy import load_policy,verify_manifest_identity,digest
import otaku_br_character_v2_20261108 as image_engine
from kids_static_90s_20261107 import probe,duration
from remaining_static_90s_20261107 import run
from legendas_precisas import captions_from_markers
from capa_cinematografica import render_cover
from shorts_duration import validate_planned_audio,validate_video
from youtube_public_tags import public_tags
import five_channel_fifteen_upload_20261108 as youtube_uploader

MANIFEST=ROOT/"conteudos"/"trending-single-br-en-20261109.json"
LAUNCH=ROOT/"conteudos"/"trending-single-br-en-launch-20261109.json"
LEDGER=ROOT/"conteudos"/"otaku-production-reservations.json"
OUTPUT=ROOT/"cloud-trending-br-en-20261109"
MOTION=ROOT/"motion-remotion"
OWNER="trending_single_br_en_20261109"
WORKFLOW="AutoEditorVideo - trending Straw Hats BR and JoJo Part 7 OP EN private"
IMAGE_MODEL="gpt-image-2"
EXPECTED={"br":"5021-one-piece-chapeus-palha-equipe","en":"7020-jojo-part-7-op-spin-kroi"}
VOICE={"br":"pt-BR-AntonioNeural","en":"en-US-AriaNeural"}
FPS=30

class TrendBlocked(ValueError):
    pass

def load():
    load_policy()
    d=json.loads(MANIFEST.read_text(encoding="utf-8"))
    if (d.get("schema")!="autoeditorvideo/trending-single-br-en-20261109/v1"
        or d.get("production_owner")!=OWNER or d.get("target_total")!=2
        or d.get("channels")!=["br","en"] or d.get("privacy")!="private_first"
        or d.get("private_only") is not True
        or d.get("public_release_requires_visual_review") is not True
        or d.get("no_duplicates") is not True
        or len(d.get("episodes",[]))!=2):
        raise TrendBlocked("TREND_MANIFEST_OR_PRIVATE_POLICY_CHANGED")
    launch=json.loads(LAUNCH.read_text(encoding="utf-8"))
    if launch != {
        "schema":"autoeditorvideo/trending-private-launch/v1",
        "date":"2026-11-09",
        "creator_authorized":True,
        "channels":["br","en"],
        "episode_ids":[EXPECTED["br"],EXPECTED["en"]],
        "visibility":"private",
        "public_release_requires_visual_review":True,
        "no_duplicate_uploads":True,
        "no_original_copyright_music_or_clips":True,
        "main_branch_only":True
    }:
        raise TrendBlocked("EXACT_USER_LAUNCH_NOT_AUTHORIZED")
    if [x.get("channel") for x in d["episodes"]]!=["br","en"]:
        raise TrendBlocked("ONE_PER_CHANNEL_REQUIRED")
    for row in d["episodes"]:
        ch=row["channel"]
        assert_reserved(ch,row["id"],OWNER)
        if (row["id"]!=EXPECTED[ch] or row.get("channel_id")!=KNOWN_IDS[ch]
            or row.get("made_for_kids") is not False
            or row.get("language")!=("pt-BR" if ch=="br" else "en-US")
            or row.get("youtube_visibility_intent")!="private_first_manual_visual_review"
            or row.get("production_state",{}).get("upload")!="not_started"
            or row.get("production_state",{}).get("youtube_id") is not None
            or len(row.get("scenes",[]))!=8
            or row.get("character_identity_policy")!="autoeditorvideo/otaku-character-identity-policy/v1"
            or row.get("narration_script")!=" ".join(x["editorial_beat"] for x in row["scenes"])
            or len(row["narration_script"].split())<100
            or len(row["narration_script"].split())>180
            or len(",".join(row["tags"]))>500
            or row["tags"][0]!=row["primary_keyword"]):
            raise TrendBlocked("WRONG_EPISODE_METADATA_OR_DURATION_PLAN_"+ch)
        verify_manifest_identity(row)
        if len(row["character_identity_bible"])>4:
            raise TrendBlocked("UNEXPECTED_CHARACTER_ANCHOR_SPEND")
        if not all(s.get("character_keys") for s in row["scenes"]):
            raise TrendBlocked("CANONICAL_IDENTITY_MISSING_IN_SCENE")
    old=ROOT/"dados/publicacoes/2026-11-08-lote15-recibos-verificados.json"
    previous=json.loads(old.read_text(encoding="utf8"))
    if any(x["episode_id"] in EXPECTED.values() for x in previous["videos"]):
        raise TrendBlocked("ALREADY_UPLOADED_EARLIER_BATCH")
    return d["episodes"]

def row_for(channel):
    return next(x for x in load() if x["channel"]==channel)

def guard(channel,action):
    e=os.environ
    if not (e.get("GITHUB_REPOSITORY")=="HelioConde/AutoEditorVideo"
        and e.get("GITHUB_REF")=="refs/heads/main"
        and e.get("GITHUB_RUN_ATTEMPT")=="1"
        and e.get("GITHUB_EVENT_NAME")=="push"
        and e.get("GITHUB_WORKFLOW")==WORKFLOW
        and e.get("TREND_CHANNEL")==channel):
        raise TrendBlocked("EXACT_ONE_SHOT_MAIN_CHANNEL_GUARD")
    if action=="render":
        if (e.get("TREND_IMAGE_RENDER_AUTHORIZED")!="yes"
            or e.get("IMAGE_MODEL")!=IMAGE_MODEL):
            raise TrendBlocked("IMAGE_RENDER_UNAUTHORIZED")
        if any(e.get(k) for k in ("YOUTUBE_CLIENT_JSON","YOUTUBE_CHANNEL_TOKEN_JSON",
                                  "YOUTUBE_BR_TOKEN_JSON","YOUTUBE_EN_TOKEN_JSON")):
            raise TrendBlocked("YOUTUBE_OAUTH_FORBIDDEN_IN_RENDER")
    elif action=="upload":
        if (e.get("TREND_PRIVATE_UPLOAD_AUTHORIZED")!="yes"
            or not e.get("YOUTUBE_CLIENT_JSON") or not e.get("YOUTUBE_CHANNEL_TOKEN_JSON")):
            raise TrendBlocked("PRIVATE_YOUTUBE_UPLOAD_AUTH_REQUIRED")
        if any(e.get(k) for k in ("PROXY_API_KEY","PROXY_ACCOUNTS_JSON",
                                  "YOUTUBE_BR_TOKEN_JSON","YOUTUBE_EN_TOKEN_JSON",
                                  "YOUTUBE_GAMES_TOKEN_JSON","YOUTUBE_KIDS_TOKEN_JSON",
                                  "YOUTUBE_ALCHEMY_TOKEN_JSON")):
            raise TrendBlocked("ISOLATED_CHANNEL_TOKEN_REQUIRED")

def voice(row,folder):
    from narracao_shorts import ensure_voice
    import narracao_shorts as ns
    rate=0
    for attempt in range(5):
        ns.RATE="%+d%%"%rate
        target=folder/("tts-%d"%(attempt+1))
        mp3,_=ensure_voice({"script":row["narration_script"]},target,create=True,
                           engine="edge",voice=VOICE[row["channel"]])
        secs=duration(mp3)
        print("TREND_VOICE_"+row["channel"]+"_TAKE_"+str(attempt+1)+"_"+str(round(secs,2)),flush=True)
        if 50<=secs<=59.2:
            validate_planned_audio(secs,stage=row["id"])
            markers=json.loads((target/"marcacoes-voz.json").read_text(encoding="utf-8"))
            words=markers.get("words",[])
            captions=captions_from_markers(mp3,row["narration_script"],secs,fps=FPS)
            if len(words)<90 or len(captions)<24:
                raise TrendBlocked("WORD_BOUNDARIES_NOT_VALID")
            return mp3,secs,words,captions
        rate=max(-24,min(26,round(((1+rate/100)*(secs/55)-1)*100)))
    raise TrendBlocked("NATURAL_TTS_DID_NOT_FIT_60S_NO_TRUNCATION")

def render_video(row,folder,audio,seconds,words,captions,frames,identity):
    from PIL import Image
    ch=row["channel"]
    ns="trending-20261109/"+ch+"/"+row["id"]
    assets=MOTION/"public"/"generated"/ns
    if assets.exists():
        raise TrendBlocked("RENDER_ASSET_NAMESPACE_EXISTS_STOP")
    assets.mkdir(parents=True,exist_ok=False)
    for n,p in enumerate(frames,1):
        shutil.copy2(p,assets/("scene-%02d.png"%n))
    shutil.copy2(audio,assets/"voz-master.mp3")
    cuts=[0]
    total=sum(len(s["editorial_beat"].split()) for s in row["scenes"])
    counts=0
    for scene in row["scenes"][:-1]:
        counts+=len(scene["editorial_beat"].split())
        idx=min(len(words)-1,round(len(words)*counts/total))
        cuts.append(round(float(words[idx]["start"])*FPS))
    cuts.append(round(seconds*FPS))
    if len(cuts)!=9 or any(b-a<FPS*3 for a,b in zip(cuts,cuts[1:])):
        raise TrendBlocked("SCENE_TIMING_TOO_SHORT")
    scenes=[]
    for i in range(8):
        path="generated/"+ns+"/scene-%02d.png"%(i+1)
        scenes.append({"id":"%02d"%(i+1),"subject":"personagem",
          "startFrame":cuts[i],"endFrame":cuts[i+1],
          "background":path,"foreground":path,
          "renderMode":"master_static","transitionStyle":"crossfade",
          "shotType":"wide" if i%2==0 else "detail",
          "beatRole":"setup" if i<2 else "answer"})
    props={"id":row["id"],"durationFrames":round(seconds*FPS),
           "audio":"generated/"+ns+"/voz-master.mp3",
           "scenes":scenes,"captions":captions,"hook":"",
           "visualProfile":"original","animationMode":"desligada",
           "characterPreset":"equilibrado",
           "editorialProfile":"canonical-character-anchored-scene-stills",
           "soundCues":[]}
    (folder/"props.json").write_text(json.dumps(props,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    mp4=folder/"final.mp4"
    run(["npm","run","render:master","--",str(mp4.resolve()),"--props",
         str((folder/"props.json").resolve()),"--concurrency","2",
         "--codec","h264","--crf","22"],cwd=MOTION,timeout=4800)
    final_sec=validate_video(mp4,stage=row["id"]+" final MP4")
    cover=folder/"thumb.jpg"
    with Image.open(frames[0]) as im:
        result=render_cover(im,row["cover_text"],cover,zoom=1.0,
                            focus_x=.5,focus_y=.4,template="default")
    if result["size"]!=[1080,1920]:
        raise TrendBlocked("COVER_DIMENSIONS_INVALID")
    info=probe(mp4)
    vs=[x for x in info["streams"] if x.get("codec_type")=="video"]
    sounds=[x for x in info["streams"] if x.get("codec_type")=="audio"]
    if (len(vs)!=1 or not sounds or vs[0].get("width")!=1080
        or vs[0].get("height")!=1920 or mp4.stat().st_size<300000):
        raise TrendBlocked("REAL_1080x1920_AUDIO_VIDEO_REQUIRED")
    qa={"schema":"autoeditorvideo/trending-br-en-original-short-qa/v1",
        "channel":ch,"channel_id":row["channel_id"],"episode_id":row["id"],
        "seconds":round(final_sec,3),"voice_seconds":round(seconds,3),
        "duration_rule_seconds_max":60,"resolution":[1080,1920],
        "image_count":8,"image_sha256":[digest(x) for x in frames],
        "named_character_anchors":identity["anchor_image_sha256"],
        "scene_edits_use_real_reference_images":True,
        "identity_provenance_sha256":digest(folder/"character-identity-provenance.json"),
        "word_boundary_captions":True,
        "mp4_sha256":digest(mp4),"cover_sha256":digest(cover),
        "automated_technical_qa":"passed",
        "editorial_visual_review_status":"pending",
        "public_release_approved":False,"youtube_upload":"not_performed"}
    metadata={"id":row["id"],"channel":ch,"channel_id":row["channel_id"],
              "title":row["title"],"description":row["description"],
              "tags":public_tags(row["tags"]),"categoryId":"24",
              "defaultLanguage":row["language"],
              "selfDeclaredMadeForKids":False,
              "containsSyntheticMedia":True,"privacyStatus":"private",
              "mp4_sha256":qa["mp4_sha256"],"cover_sha256":qa["cover_sha256"]}
    (folder/"qa.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (folder/"metadata.json").write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    summary={"schema":"autoeditorvideo/trending-original-short-output/v1",
             "channel":ch,"channel_id":row["channel_id"],"episode_id":row["id"],
             "duration":final_sec,"youtube_upload":"not_performed",
             "mp4_sha256":qa["mp4_sha256"],"cover_sha256":qa["cover_sha256"],
             "privacy":"private"}
    (folder/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("TREND_MP4_QA_PASSED_"+ch+"_"+row["id"],flush=True)

def render(channel):
    row=row_for(channel)
    guard(channel,"render")
    folder=OUTPUT/channel/row["id"]
    if folder.exists():
        raise TrendBlocked("RENDER_ALREADY_EXISTS_NO_DUPLICATE")
    folder.mkdir(parents=True,exist_ok=False)
    audio,secs,words,captions=voice(row,folder)
    from gerar_video_codex import proxy_key,check_proxy_accounts
    key=proxy_key()
    check_proxy_accounts(key)
    frames,identity=image_engine.generate_anchored_art(row,folder,key)
    render_video(row,folder,audio,secs,words,captions,frames,identity)
    for temp in folder.glob("tts-*"):
        if temp.is_dir():shutil.rmtree(temp)
    (folder/"props.json").unlink(missing_ok=True)
    print("TREND_ONE_COMPLETE_"+channel,flush=True)

def checked_media(channel):
    row=row_for(channel)
    folder=OUTPUT/channel/row["id"]
    sources=[folder/n for n in ("final.mp4","thumb.jpg","qa.json","metadata.json",
                                  "summary.json","character-identity-provenance.json")]
    if not all(x.is_file() for x in sources):
        raise TrendBlocked("MEDIA_OR_PROVENANCE_MISSING")
    qa=json.loads((folder/"qa.json").read_text(encoding="utf8"))
    md=json.loads((folder/"metadata.json").read_text(encoding="utf8"))
    provenance=json.loads((folder/"character-identity-provenance.json").read_text(encoding="utf8"))
    if (qa.get("automated_technical_qa")!="passed"
        or qa.get("channel_id")!=KNOWN_IDS[channel]
        or qa.get("episode_id")!=row["id"]
        or qa.get("public_release_approved") is not False
        or qa.get("editorial_visual_review_status")!="pending"
        or qa.get("scene_edits_use_real_reference_images") is not True
        or provenance.get("independent_text_to_image_scene_generations")!=0
        or provenance.get("scene_edit_generations")!=8
        or md.get("title")!=row["title"]
        or md.get("description")!=row["description"]
        or md.get("tags")!=public_tags(row["tags"])
        or md.get("privacyStatus")!="private"
        or md.get("channel_id")!=KNOWN_IDS[channel]
        or md.get("selfDeclaredMadeForKids") is not False
        or md.get("containsSyntheticMedia") is not True):
        raise TrendBlocked("MEDIA_QA_CHANNEL_ID_METADATA_POLICY_BLOCKED")
    if any(digest(folder/k)!=v for k,v in
           (("final.mp4",qa["mp4_sha256"]),("thumb.jpg",qa["cover_sha256"]),
            ("character-identity-provenance.json",qa["identity_provenance_sha256"]))):
        raise TrendBlocked("SHA256_CHANGED_STOP")
    actual=validate_video(folder/"final.mp4",stage="upload")
    if not 45<=actual<=60:
        raise TrendBlocked("SHORT_MAX60_RULE_FAILED")
    return {"episode_id":row["id"],"metadata":md,
            "video":folder/"final.mp4","cover":folder/"thumb.jpg",
            "sha256":qa["mp4_sha256"],"seconds":actual}

def save_receipt(path,record):
    path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf8")

def upload(channel):
    row=row_for(channel)
    guard(channel,"upload")
    item=checked_media(channel)
    output=OUTPUT/channel/row["id"]
    receipt=output/"youtube-private-receipt.json"
    if receipt.exists():
        raise TrendBlocked("RECEIPT_ALREADY_EXISTS_DO_NOT_INSERT_TWICE")
    api,playlist=youtube_uploader.youtube(channel)
    matches=youtube_uploader.scan_existing(api,playlist,item,channel)
    if len(matches)>1:
        raise TrendBlocked("MULTIPLE_OWN_YOUTUBE_MATCHES_STOP")
    record={"channel":channel,"channel_id":KNOWN_IDS[channel],
            "episode_id":row["id"],"video_sha256":item["sha256"],
            "youtube_id":None,"privacyStatus":"private","confirmed_private":False,
            "upload_state":"existing_match" if matches else "insert_started_result_uncertain"}
    save_receipt(receipt,record)
    recovered=bool(matches)
    if recovered:
        video_id=matches[0]
    else:
        try:
            video_id=youtube_uploader.insert_private(api,item)
        except Exception:
            # Never blindly call videos.insert again after an unclear result.
            video_id=None
            for delay in (12,24,35):
                time.sleep(delay)
                observed=youtube_uploader.scan_existing(api,playlist,item,channel)
                if observed:
                    video_id=observed[0]
                    recovered=True
                    break
            if not video_id:
                raise TrendBlocked("UNCERTAIN_YOUTUBE_INSERT_STOP_NO_REUPLOAD") from None
    record["youtube_id"]=video_id
    record["upload_state"]="video_id_received"
    record["reconciled_existing"]=recovered
    save_receipt(receipt,record)
    for delay in (0,12,24,35):
        if delay:time.sleep(delay)
        if youtube_uploader.verify_video(api,video_id,channel,item):
            record["confirmed_private"]=True
            record["upload_state"]="private_verified"
            save_receipt(receipt,record)
            break
    if not record["confirmed_private"]:
        raise TrendBlocked("PRIVATE_ID_AND_CHANNEL_NOT_VERIFIED_STOP")
    try:
        from googleapiclient.http import MediaFileUpload
        if not recovered:time.sleep(75)
        response=api.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(str(item["cover"]),mimetype="image/jpeg")
        ).execute()
        record["thumbnail_acknowledged"]=bool(response.get("items"))
    except Exception:
        record["thumbnail_review_required"]=True
    save_receipt(receipt,record)
    print("TREND_YOUTUBE_PRIVATE_VERIFIED_"+channel+"_"+row["id"]+"_"+video_id,flush=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--channel",required=True,choices=tuple(EXPECTED))
    ap.add_argument("--action",required=True,choices=("validate","render","upload"))
    args=ap.parse_args()
    try:
        if args.action=="validate":
            row_for(args.channel)
            print("TREND_PREFLIGHT_OK_"+args.channel,flush=True)
        elif args.action=="render":
            render(args.channel)
        else:
            upload(args.channel)
        return 0
    except Exception as exc:
        msg=str(exc) if isinstance(exc,TrendBlocked) else type(exc).__name__
        print("TREND_BLOCKED_"+args.channel+"_"+msg,file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
