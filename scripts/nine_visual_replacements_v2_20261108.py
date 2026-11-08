#!/usr/bin/env python3
"""Generate 9 versioned replacements from original AutoEditorVideo scripts.

EN: canonical anime character visual policy, with image anchors and images/edits.
Gamer/Alchemy: consistent theme-specific original scene illustrations, also
using anchor edits instead of unrelated stills. Output 3 MP4s/channel, artwork
and QA; publish never happens from this script. Old videos remain untouched.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))

from production_reservations import assert_reserved
from youtube_channel_registry import KNOWN_IDS
from otaku_character_identity_policy import verify_manifest_identity,load_policy,EXPECTED_SCHEMA,IdentityBlocked,digest
import otaku_br_character_v2_20261108 as br_v2
import remaining_static_90s_20261107 as editor

PLAN=ROOT/"conteudos"/"otaku-and-channels-nine-replacements-20261108.json"
SOURCE=ROOT/"conteudos"/"lote-12-estatico-90s-20261107.json"
OUTPUT_ROOT=ROOT/"cloud-nine-visual-replacements-v2-20261108"
OWNER="all_channels_visual_replacement_v2_20261108"
WORKFLOW="AutoEditorVideo - nine image-corrected replacements EN Gamer Alchemy"
RETRY_WORKFLOW="AutoEditorVideo - retry Gamer-only V2 after exact failed original render"
HTTP400_WORKFLOW="AutoEditorVideo - Gamer V2 fix HTTP400 and private upload"
CHANNELS=("en","games","alchemy")
CALLS={"en":29,"games":27,"alchemy":27}
IDS={
    "en":("7011-noelle-black-clover-v2","7012-maomao-apothecary-v2","7013-shizuku-hunter-v2"),
    "games":("game-101-minecraft-agua-v2","game-102-roblox-obby-v2","game-103-minecraft-creeper-v2"),
    "alchemy":("alchemy-101-video-ia-realidade-v2","alchemy-102-agentes-chatbot-v2","alchemy-103-prompt-consistencia-v2")
}

editor.OUTPUT_ROOT=OUTPUT_ROOT

class ReplacementBlocked(ValueError):pass

def output(channel:str)->Path:
    return OUTPUT_ROOT/channel

def validate(channel:str)->list[dict]:
    load_policy()
    if channel not in CHANNELS:raise ReplacementBlocked("ONLY_THREE_EXACT_CHANNELS")
    d=json.loads(PLAN.read_text(encoding="utf-8"))
    original=json.loads(SOURCE.read_text(encoding="utf-8"))
    if (d.get("schema")!="autoeditorvideo/nine-cross-channel-visual-corrected-v2/v1"
            or d.get("production_owner")!=OWNER
            or d.get("source_manifest")!=str(SOURCE.relative_to(ROOT))
            or d.get("target_total")!=9
            or d.get("channel_order")!=list(CHANNELS)
            or d.get("story_unchanged") is not True
            or d.get("source_originals_preserved") is not True
            or d.get("never_remove_original_on_upload_error") is not True
            or d.get("privacy_after_qa")!="private_first_until_visual_review"
            or d.get("made_for_kids") is not False
            or d.get("visual_review_required_before_public") is not True
            or d.get("total_max_image_calls")!=83
            or d.get("max_image_calls")!=CALLS):
        raise ReplacementBlocked("REPLACEMENT_SOURCE_OR_PRIVACY_POLICY_CHANGED")
    source_rows={x["id"]:x for x in original["episodes"]}
    rows=[x for x in d["episodes"] if x.get("channel")==channel]
    if tuple(x.get("id") for x in rows)!=IDS[channel]:
        raise ReplacementBlocked("NOT_THE_3_APPROVED_CHANNEL_EPISODES")
    if len(d["episodes"])!=9:
        raise ReplacementBlocked("TOTAL_VIDEOS_NOT_NINE")
    calls=0
    for row in rows:
        assert_reserved(channel,row["id"],OWNER)
        origin=source_rows.get(row.get("original_episode_id"))
        if (origin is None
                or origin["channel"]!=channel
                or row.get("channel_id")!=KNOWN_IDS[channel]
                or row.get("old_youtube_id")!={
                    "7011-noelle-black-clover":"KamcfO3fINM","7012-maomao-apothecary":"EMFjugQJdUY",
                    "7013-shizuku-hunter":"gHGLvU0r50s","game-101-minecraft-agua":"vxgEOrT8uQE",
                    "game-102-roblox-obby":"PkixTrmD91I","game-103-minecraft-creeper":"oO_s9sbz8m4",
                    "alchemy-101-video-ia-realidade":"gfG9bNDTZMU",
                    "alchemy-102-agentes-chatbot":"C2fE9VslFCU",
                    "alchemy-103-prompt-consistencia":"QL_trwUw62c"
                }.get(origin["id"])
                or row.get("narration_script")!=origin["narration_script"]
                or row.get("title")!=origin["title"]
                or row.get("tags")!=origin["tags"]
                or row.get("made_for_kids") is not False
                or row.get("language")!=("en-US" if channel=="en" else "pt-BR")
                or row.get("render_version")!="anchor-edit-20261108-v2"
                or row.get("production_state",{}).get("youtube_id") is not None
                or row.get("production_state",{}).get("upload")!="not_started"
                or len(row.get("scenes",[]))!=8
                or any(x.get("editorial_beat")!=origin["scenes"][i]["editorial_beat"]
                       for i,x in enumerate(row["scenes"]))
                or row.get("character_identity_policy")!=(
                    EXPECTED_SCHEMA if channel=="en" else "editorial_anchor_continuity-v1")):
            raise ReplacementBlocked("STORY_CHANGE_OR_WRONG_DESTINATION_OR_VERSION")
        chars=verify_manifest_identity(row)
        if (channel=="en" and
                any(c["franchise"] not in ("Black Clover","The Apothecary Diaries","Hunter x Hunter")
                    for c in chars)):
            raise ReplacementBlocked("INCORRECT_ANIME_CHARACTER_IDENTITY")
        calls+=8+len(chars)
    if calls!=CALLS[channel]:raise ReplacementBlocked("CHANNEL_IMAGE_BUDGET_CHANGED")
    return rows

def _retry_source_confirmed(env:dict)->bool:
    if (env.get("GITHUB_EVENT_NAME")!="workflow_run"
            or env.get("GITHUB_WORKFLOW")!=RETRY_WORKFLOW):
        return False
    path=Path(env.get("GITHUB_EVENT_PATH",""))
    if not path.is_file():return False
    source=json.loads(path.read_text(encoding="utf-8")).get("workflow_run",{})
    return (
        source.get("id")==42449154499
        and source.get("name")==WORKFLOW
        and source.get("head_sha")=="0841f7523e5a50bb48ab4f6399cd95350a82a36a"
        and source.get("head_branch")=="main"
        and source.get("conclusion")=="failure"
        and source.get("repository",{}).get("full_name")=="HelioConde/AutoEditorVideo"
    )

def guard(channel:str):
    e=os.environ
    standard=(e.get("GITHUB_EVENT_NAME")=="push"
              and e.get("GITHUB_WORKFLOW")==WORKFLOW
              and e.get("MAX_IMAGE_CALLS")==str(CALLS[channel]))
    games_recovery=(channel=="games"
                    and e.get("GITHUB_WORKFLOW")==RETRY_WORKFLOW
                    and e.get("REPLACEMENTS_RETRY_APPROVED")=="yes"
                    and e.get("MAX_IMAGE_CALLS")=="33"
                    and _retry_source_confirmed(e))
    http400_recovery=(
        channel=="games"
        and e.get("GITHUB_EVENT_NAME")=="push"
        and e.get("GITHUB_WORKFLOW")==HTTP400_WORKFLOW
        and e.get("REPLACEMENTS_HTTP400_FIX_APPROVED")=="yes"
        and e.get("MAX_IMAGE_CALLS")=="33"
        and e.get("GITHUB_REF")=="refs/heads/main"
        and e.get("GITHUB_RUN_ATTEMPT")=="1"
    )
    if (e.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo"
            or e.get("GITHUB_REF")!="refs/heads/main"
            or e.get("GITHUB_RUN_ATTEMPT")!="1"
            or e.get("V2_REPLACEMENTS_RENDER_APPROVED")!="yes"
            or e.get("REPLACEMENTS_CHANNEL")!=channel
            or e.get("IMAGE_MODEL")!="gpt-image-2"
            or not (standard or games_recovery or http400_recovery)):
        raise ReplacementBlocked("EXACT_MAIN_OR_FAILED_GAMER_RECOVERY_ONE_SHOT_REQUIRED")
    if any(e.get(k) for k in ("YOUTUBE_CLIENT_JSON","YOUTUBE_CHANNEL_TOKEN_JSON",
                             "YOUTUBE_KIDS_TOKEN_JSON","YOUTUBE_BR_TOKEN_JSON",
                             "YOUTUBE_EN_TOKEN_JSON","YOUTUBE_GAMES_TOKEN_JSON")):
        raise ReplacementBlocked("NO_YOUTUBE_OAUTH_ALLOWED_IN_GENERATION")

def render(channel:str):
    guard(channel)
    rows=validate(channel)
    root=output(channel)
    if root.exists():raise ReplacementBlocked("EXISTING_OUTPUT_NO_BLIND_REGENERATION")
    root.mkdir(parents=True,exist_ok=False)
    prepared=[]
    for row in rows:
        folder=root/row["id"]
        folder.mkdir()
        audio,sec,words=editor.voice_takes(row,folder,channel)
        prepared.append((row,folder,audio,sec,words))
    from gerar_video_codex import proxy_key,check_proxy_accounts
    key=proxy_key()
    check_proxy_accounts(key)
    if os.environ.get("GITHUB_WORKFLOW")==RETRY_WORKFLOW:
        # The first Gamer render hit a provider RuntimeError during the second
        # reference edit. Allow at most one extra attempt per failing scene,
        # with a GLOBAL ceiling of six extra image calls (27 + 6 = 33).
        # Preserve the original anchor reference; never use text-only fallback.
        import master_scenes as scene_engine
        import time
        unwrapped_edit=scene_engine.request_edit
        retry_budget=[6]
        def retry_if_transient(*args,**kwargs):
            for attempt in range(2):
                try:
                    return unwrapped_edit(*args,**kwargs)
                except RuntimeError as exc:
                    msg=str(exc)
                    if (attempt>0 or retry_budget[0]==0
                            or any(code in msg for code in (
                                "HTTP 400","HTTP 401","HTTP 403","HTTP 404"))):
                        raise
                    retry_budget[0]-=1
                    print("NINE_V2_GAMER_PROVIDER_TRANSIENT_RETRY_WITH_SAME_CHARACTER_REFERENCE",flush=True)
                    time.sleep(30)
            raise ReplacementBlocked("UNREACHABLE_IMAGE_RETRY_EXIT")
        scene_engine.request_edit=retry_if_transient
    http400_mode=(channel=="games" and os.environ.get("GITHUB_WORKFLOW")==HTTP400_WORKFLOW)
    shared_gamer_extra_budget=[6]
    report={
        "schema":"autoeditorvideo/nine-visual-replacements-rendered/v2",
        "owner":OWNER,"channel":channel,"channel_id":KNOWN_IDS[channel],
        "privacy":"not_uploaded_visual_review_pending",
        "publisher":"separate_qa_gated_only",
        "image_process":"character_anchor_then_images_edits_for_every_scene",
        "max_image_calls":33 if http400_mode else CALLS[channel],
        "count":3,"videos":[]
    }
    for row,folder,audio,sec,words in prepared:
        frames,identity=br_v2.generate_anchored_art(
            row,folder,key,gamer_http400_repair=http400_mode,
            extra_edit_budget=shared_gamer_extra_budget if http400_mode else None
        )
        # Same original Remotion, canonical subtitles and thumbnails, no mesh warp.
        result=editor.render_one(row,folder,audio,sec,words,frames,channel)
        meta_path=folder/"metadata.json"
        meta=json.loads(meta_path.read_text(encoding="utf-8"))
        meta.update({
            "render_version":2,"original_episode_id":row["original_episode_id"],
            "previous_youtube_id":row["old_youtube_id"],
            "character_identity_policy":row["character_identity_policy"],
            "privacyStatus":"private",
            "replacement_review":"pending",
            "original_public_video_preserved":True,
            "new_private_upload_authorized_after_qa":True
        })
        meta_path.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n",
                             encoding="utf-8")
        qa_file=folder/"qa.json"
        qa=json.loads(qa_file.read_text(encoding="utf-8"))
        qa.update({
            "identity_policy_schema":row["character_identity_policy"],
            "identity_bible_complete":True,
            "anchor_image_sha256":identity["anchor_image_sha256"],
            "all_scene_edits_use_anchor":True,
            "scene_reference_provenance":"character-identity-provenance.json",
            "story_beat_alignment":True,
            "editorial_visual_review_status":"pending",
            "publication_qa":"not_approved"
        })
        qa_file.write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",
                           encoding="utf-8")
        result["identity_provenance_sha256"]=digest(folder/"character-identity-provenance.json")
        report["videos"].append(result)
        for scr in folder.glob("tts-*"):
            if scr.is_dir():shutil.rmtree(scr)
        (folder/"props.json").unlink(missing_ok=True)
        print("NINE_V2_"+channel+"_ORIGINAL_MP4_READY_FOR_VISUAL_REVIEW_"+row["id"],flush=True)
    if len(report["videos"])!=3:
        raise ReplacementBlocked("PARTIAL_RENDER_DO_NOT_UPLOAD")
    (root/"summary.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",
                                     encoding="utf-8")
    print("NINE_V2_"+channel.upper()+"_THREE_RENDERED_MAINTAIN_OLD_UNTOUCHED",flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--channel",choices=CHANNELS,required=True)
    p.add_argument("--action",choices=("validate","render"),default="validate")
    x=p.parse_args()
    try:
        if x.action=="render":render(x.channel)
        else:
            validate(x.channel)
            print("NINE_V2_"+x.channel.upper()+"_THREE_EPISODES_VALIDATED")
        return 0
    except Exception as exc:
        if isinstance(exc,RuntimeError):
            import re
            code=re.search(r"HTTP [0-9]{3}",str(exc))
            name="REFERENCE_EDIT_PROVIDER_"+(code.group().replace(" ","_") if code else "RUNTIME_FAILURE")
        else:
            name=str(exc) if isinstance(exc,(ReplacementBlocked,IdentityBlocked)) else type(exc).__name__
        print("NINE_V2_RENDER_BLOCKED_"+name,file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
