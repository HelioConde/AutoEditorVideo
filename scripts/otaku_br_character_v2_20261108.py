#!/usr/bin/env python3
"""Re-render 5012-5014 Otaku BR with canonical recognizable anime identities.

STRICT: one new anchor per named character; every narrated scene is an
images/edits operation with the relevant anchor, never an isolated generic
text-to-image. All prior YouTube videos and MP4s remain untouched. Generates
reviewable MP4s and complete scene/anchor contact sheet source; no upload.
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
import remaining_static_90s_20261107 as renderer
from production_reservations import assert_reserved
from youtube_channel_registry import KNOWN_IDS
from otaku_character_identity_policy import (
    EXPECTED_SCHEMA,IdentityBlocked,verify_manifest_identity,load_policy,
    anchor_prompt,edit_prompt,save_image,digest,reference_collage,
    visually_distinct
)

MANIFEST=ROOT/"conteudos"/"otaku-br-three-character-faithful-v2-20261108.json"
ORIGINAL=ROOT/"conteudos"/"otaku-br-three-public-20261107.json"
OUT_ROOT=ROOT/"cloud-otaku-br-characters-v2-20261108"
OWNER="otaku_br_three_character_continuity_v2_20261108"
CHANNEL_ID="UCXGYTuBYn-0Ziqin5ajKhOw"
IDS=("5012-solo-leveling-igris-v2",
     "5013-blue-lock-isagi-v2","5014-mob-psycho-emocoes-v2")
MODEL="gpt-image-2"
MAX_CALLS=28
RENDER_WORKFLOW="Otaku Multicena BR - character-faithful V2 render and visual review"

renderer.VOICES["br"]="pt-BR-AntonioNeural"
renderer.CATEGORY["br"]="24"
renderer.PROFILE["br"]="original"
renderer.COVER["br"]="default"
renderer.OUTPUT_ROOT=OUT_ROOT

class RenderBlocked(ValueError):
    pass

def output()->Path:
    return OUT_ROOT/"br"

def validate()->list[dict]:
    load_policy()
    d=json.loads(MANIFEST.read_text(encoding="utf-8"))
    old=json.loads(ORIGINAL.read_text(encoding="utf-8"))
    if (d.get("schema")!="autoeditorvideo/otaku-br-3-character-faithful-v2/v1"
            or d.get("production_owner")!=OWNER
            or d.get("channel")!="br" or d.get("channel_id")!=CHANNEL_ID
            or KNOWN_IDS["br"]!=CHANNEL_ID or d.get("version")!=2
            or d.get("source_manifest")!=str(ORIGINAL.relative_to(ROOT))
            or d.get("target_total")!=3
            or d.get("visual_approval_required") is not True
            or d.get("replacement_delete_requires_public_processed_thumbnail") is not True
            or d.get("max_image_requests_total")!=MAX_CALLS
            or d.get("excludes")!=["en","games","kids","alchemy"]
            or d.get("unrelated_queue_50_paused_and_untouched") is not True):
        raise RenderBlocked("CANONICAL_V2_MANIFEST_OR_SOURCE_CHANGED")
    rows=d.get("episodes",[])
    if tuple(x.get("id") for x in rows)!=IDS:
        raise RenderBlocked("CANONICAL_V2_EXACT_EPISODES_WRONG")
    expected_original={x["id"]:x for x in old["episodes"]}
    total_calls=0
    for row in rows:
        assert_reserved("br",row["id"],OWNER)
        source=expected_original.get(row.get("original_episode_id"))
        if (source is None or row.get("narration_script")!=source.get("narration_script")
                or row.get("title")!=source.get("title")
                or row.get("cover_text")!=source.get("cover_text")
                or row.get("channel")!="br"
                or row.get("channel_id")!=CHANNEL_ID
                or row.get("made_for_kids") is not False
                or row.get("language")!="pt-BR"
                or row.get("render_version")!="canonical-character-anchor-edit-v2"
                or row.get("character_identity_policy")!=EXPECTED_SCHEMA
                or row.get("production_state",{}).get("youtube_id") is not None
                or row.get("production_state",{}).get("upload")!="not_started"
                or len(row.get("scenes",[]))!=8
                or any(s["editorial_beat"]!=source["scenes"][i]["editorial_beat"]
                       for i,s in enumerate(row["scenes"]))
                or any(x in row.get("visual_bible","").casefold()
                       for x in ("generic athlete","fictional silhouette","not copied exactly"))):
            raise RenderBlocked("CANONICAL_V2_STORY_OR_IDENTITIES_MISMATCH")
        characters=verify_manifest_identity(row)
        total_calls+=len(characters)+8
        allowed=d["allowed_old_video_ids_by_episode"].get(row["id"])
        if row["id"]==IDS[0]:
            if allowed!=["alHbSHUN0dA"]:raise RenderBlocked("OLD_ID_ALLOWLIST_CHANGED")
        elif allowed!=[]:raise RenderBlocked("UNKNOWN_OLD_YOUTUBE_ID_BLOCK")
    if total_calls!=MAX_CALLS:
        raise RenderBlocked("CANONICAL_V2_IMAGE_BUDGET_EXACTLY_28_REQUIRED")
    return rows

def guard()->None:
    e=os.environ
    if (e.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo"
            or e.get("GITHUB_REF")!="refs/heads/main"
            or e.get("GITHUB_RUN_ATTEMPT")!="1"
            or e.get("GITHUB_EVENT_NAME")!="push"
            or e.get("GITHUB_WORKFLOW")!=RENDER_WORKFLOW
            or e.get("OTAKU_CHARACTER_V2_RENDER_AUTHORIZED")!="yes"
            or e.get("IMAGE_MODEL")!=MODEL
            or e.get("MAX_IMAGE_CALLS")!=str(MAX_CALLS)):
        raise RenderBlocked("V2_ONE_SHOT_AUTH_AND_BUDGET_GUARD")
    if any(e.get(k) for k in (
            "YOUTUBE_CLIENT_JSON","YOUTUBE_CHANNEL_TOKEN_JSON",
            "YOUTUBE_BR_TOKEN_JSON","YOUTUBE_KIDS_TOKEN_JSON",
            "YOUTUBE_EN_TOKEN_JSON","YOUTUBE_GAMES_TOKEN_JSON")):
        raise RenderBlocked("OAUTH_FORBIDDEN_IN_IMAGE_GENERATION_JOB")

def generate_anchored_art(row:dict,folder:Path,key:str)->tuple[list[Path],dict]:
    from gerar_video_codex import request_image
    from master_scenes import request_edit
    characters=verify_manifest_identity(row)
    anchors:dict[str,Path]={}
    for char in characters:
        dest=folder/("anchor-"+char["key"]+".png")
        raw=request_image(anchor_prompt(char,row["visual_bible"]),
                          MODEL,key,"1024x1536")
        save_image(raw,dest)
        anchors[char["key"]]=dest
        print("OTAKU_CHARACTER_ANCHOR_CREATED_"+row["id"]+"_"+char["key"],flush=True)
    images=[]
    provenance=[]
    for i,scene in enumerate(row["scenes"],1):
        refs=[anchors[k] for k in scene["character_keys"]]
        composite=reference_collage(refs,folder/("reference-%02d.png"%i))
        dest=folder/("scene-%02d.png"%i)
        # Only images/edits, using one or more explicit actual reference
        # portraits; NO text-only image generation for any story scene.
        blob=request_edit(composite,edit_prompt(row,scene,characters),
                          MODEL,key,transparent=False)
        save_image(blob,dest)
        if not visually_distinct(composite,dest):
            raise RenderBlocked("SCENE_DUPLICATED_REFERENCE_POSE_OR_BACKGROUND_"+str(i))
        images.append(dest)
        provenance.append({
            "scene":i,"narration_beat_sha256":__import__("hashlib").sha256(
                scene["editorial_beat"].encode("utf-8")).hexdigest(),
            "character_keys":scene["character_keys"],
            "anchor_sha256":{k:digest(anchors[k]) for k in scene["character_keys"]},
            "reference_sha256":digest(composite),"image_sha256":digest(dest),
            "generation_endpoint":"images/edits",
            "visual_character_identity_review":"pending_manual_or_visual_model_review"
        })
        print("OTAKU_CHARACTER_EDIT_SCENE_"+row["id"]+"_%02d_OF_08"%i,flush=True)
    if len(images)!=8 or len({digest(x) for x in images})!=8:
        raise RenderBlocked("CANONICAL_V2_SCENE_COUNT_OR_IMAGE_DUPLICATES")
    state={
        "policy_schema":EXPECTED_SCHEMA,
        "named_characters":[{"key":c["key"],"name":c["name"]} for c in characters],
        "anchors_sha256":{k:digest(v) for k,v in anchors.items()},
        "anchor_image_sha256":{k:digest(v) for k,v in anchors.items()},
        "image_generation_mode":"canonical-anchor-then-reference-edits",
        "anchor_text_generations":len(characters),
        "scene_edit_generations":8,"independent_text_to_image_scene_generations":0,
        "scenes":provenance,
        "story_sequence_matches_source":True,
        "editorial_visual_review_status":"pending",
        "human_review_not_falsely_claimed":True,
        "publication_allowed":False
    }
    (folder/"character-identity-provenance.json").write_text(
        json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return images,state

def produce()->None:
    guard()
    rows=validate()
    out=output()
    if out.exists():
        raise RenderBlocked("V2_RENDER_ALREADY_HAS_OUTPUT_NO_REGENERATION")
    out.mkdir(parents=True,exist_ok=False)
    prepared=[]
    for row in rows:
        folder=out/row["id"]
        folder.mkdir()
        voice,seconds,words=renderer.voice_takes(row,folder,"br")
        prepared.append((row,folder,voice,seconds,words))
    from gerar_video_codex import proxy_key,check_proxy_accounts
    key=proxy_key()
    check_proxy_accounts(key)
    report={"schema":"autoeditorvideo/otaku-br-3-canonical-character-render/v2",
            "owner":OWNER,"channel":"br","channel_id":CHANNEL_ID,
            "publication":"none_awaiting_character_visual_review",
            "target_count":3,"original_image_calls_max":MAX_CALLS,
            "original_engine":"AutoEditorVideo/Remotion MasterShort",
            "reference_process":"character anchors followed by images/edits",
            "videos":[]}
    for row,folder,voice,seconds,words in prepared:
        frames,identity=generate_anchored_art(row,folder,key)
        summary=renderer.render_one(row,folder,voice,seconds,words,frames,"br")
        qa_path=folder/"qa.json"
        qa=json.loads(qa_path.read_text(encoding="utf-8"))
        qa.update({"identity_policy_schema":EXPECTED_SCHEMA,
                   "identity_bible_complete":True,
                   "anchor_image_sha256":identity["anchor_image_sha256"],
                   "all_scene_edits_use_anchor":True,
                   "scene_reference_provenance":"character-identity-provenance.json",
                   "scenes_aligned_to_story":True,
                   "character_appearance_maintained_by_reference":True,
                   "editorial_visual_review_status":"pending",
                   "publication_qa":"not_approved"})
        qa_path.write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",
                           encoding="utf-8")
        metadata_path=folder/"metadata.json"
        meta=json.loads(metadata_path.read_text(encoding="utf-8"))
        meta.update({"version":2,
                     "original_episode_id":row["original_episode_id"],
                     "character_identity_policy":EXPECTED_SCHEMA,
                     "publication_target":"public_after_approved_visual_review",
                     "creator_public_authorized":True})
        metadata_path.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n",
                                 encoding="utf-8")
        summary["identity_provenance_sha256"]=digest(folder/"character-identity-provenance.json")
        report["videos"].append(summary)
        for scratch in folder.glob("tts-*"):
            if scratch.is_dir():shutil.rmtree(scratch)
        (folder/"props.json").unlink(missing_ok=True)
        print("OTAKU_V2_RENDER_READY_VISUAL_REVIEW_"+row["id"],flush=True)
    if len(report["videos"])!=3:
        raise RenderBlocked("V2_PARTIAL_RENDER_NOT_UPLOADABLE")
    (out/"summary.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",
                                    encoding="utf-8")
    print("OTAKU_V2_THREE_ANCHOR_EDIT_VIDEOS_RENDERED_VISUAL_REVIEW_PENDING",flush=True)

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--action",choices=("validate","render"),default="validate")
    a=ap.parse_args()
    try:
        if a.action=="validate":
            print("OTAKU_V2_PREPARED_"+",".join(row["id"] for row in validate()))
        else:
            produce()
        return 0
    except Exception as exc:
        msg=str(exc) if isinstance(exc,(RenderBlocked,IdentityBlocked)) else type(exc).__name__
        print("OTAKU_V2_RENDER_BLOCKED_"+msg,file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
