#!/usr/bin/env python3
"""Hard-locked canonical named-character image policy for Otaku BR/EN.

Generate one named-character anchor per identity, then generate every scene by
editing the anchor reference image(s), never by unrelated text-to-image.
Artwork remains original editorial illustrations, not official anime footage.
Identity records and generation provenance are precise; machine checks alone
do NOT mean the final face likeness was visually approved.
"""
from __future__ import annotations
import hashlib
import io
import json
from pathlib import Path
import re

from PIL import Image,ImageOps,ImageChops,ImageStat

ROOT=Path(__file__).resolve().parents[1]
POLICY=ROOT/"config"/"otaku-character-identity-policy.json"
EXPECTED_SCHEMA="autoeditorvideo/otaku-character-identity-policy/v1"
BANNED=("entirely fresh fictional silhouettes","original generic athlete",
        "generic athlete","generic student","simple shy school-age hero silhouette",
        "avoid brand-specific costume copying","not a reproduction of any existing copyrighted character design",
        "no exact copyrighted anime designs","avoid character likeness")

class IdentityBlocked(ValueError):
    pass

def load_policy()->dict:
    p=json.loads(POLICY.read_text(encoding="utf-8"))
    r=p.get("required_rules",{})
    required=("named_characters_must_be_recognizable",
              "canonical_hairstyle_face_costume_color_accessories",
              "story_context_scene_alignment","episode_character_anchor_before_scenes",
              "scene_generation_requires_anchor_image_edit",
              "character_consistency_across_scenes",
              "fail_closed_on_image_edit_failure",
              "block_publication_when_reference_or_identity_qa_missing",
              "no_direct_unanchored_text2image_for_story_scene",
              "never_change_policy_without_explicit_owner_instruction")
    if (p.get("schema")!=EXPECTED_SCHEMA
            or p.get("lock")!="requires_explicit_new_creator_authorization_to_change"
            or p.get("scope_channels")!=["br","en"]
            or any(r.get(name) is not True for name in required)
            or not all(any(t in declared for declared in p.get("forbidden_prompt_patterns",[])) for t in BANNED[:-1])):
        raise IdentityBlocked("CANONICAL_ANIME_CHARACTER_POLICY_UNAUTHORIZED_CHANGE")
    return p

def verify_manifest_identity(row:dict)->list[dict]:
    load_policy()
    chars=row.get("character_identity_bible")
    if not isinstance(chars,list) or not chars:
        raise IdentityBlocked("NAMED_ANIME_CHARACTERS_REQUIRED")
    keys=set()
    for char in chars:
        k=char.get("key")
        if (not isinstance(k,str) or not re.fullmatch(r"[a-z]{3,20}",k)
                or k in keys
                or not isinstance(char.get("name"),str)
                or len(char["name"])<3
                or len(char.get("canonical_appearance",""))<130):
            raise IdentityBlocked("CANONICAL_CHARACTER_BIBLE_MISSING_OR_BAD_KEY")
        keys.add(k)
    for scene in row.get("scenes",[]):
        uses=scene.get("character_keys")
        if (not isinstance(uses,list) or not uses or len(set(uses))!=len(uses)
                or any(k not in keys for k in uses)):
            raise IdentityBlocked("EVERY_ANIME_SCENE_MUST_USE_DECLARED_CHARACTER_ANCHOR")
        visual=scene.get("visual_instruction","")
        if len(visual)<60 or any(s in visual.casefold() for s in BANNED):
            raise IdentityBlocked("SCENE_GENERIC_OR_UNRELATED_TO_CHARACTER")
        for k in uses:
            name=next(c["name"] for c in chars if c["key"]==k)
            if not any(t in visual.casefold() for t in (name.casefold(),name.split()[-1].casefold(),k.casefold())):
                raise IdentityBlocked("SCENE_MUST_NAME_THE_PROTAGONIST_"+k)
    return chars

def anchor_prompt(char:dict,visual_bible:str)->str:
    return (
      "Produce one premium vertical 1024x1536 original anime editorial "
      "CHARACTER IDENTITY REFERENCE on a simple neutral lit background. "
      "Draw the SPECIFIC NAMED CANONICAL ANIME CHARACTER, recognizable as "
      +char["name"]+" from "+char["franchise"]+". "
      "Preserve the iconic recognizable hairstyle, face, eye color, signature "
      "costume, accessories, palette, silhouette, proportions and expression; "
      "not a generic substitute, not a random OC or silhouette. "
      "Canonical appearance specification: "+char["canonical_appearance"]+". "
      "Episode's coherent artistic treatment: "+visual_bible+". "
      "Single character, full head visible, upper body and costume identifiable, "
      "natural clean anatomy and hands, detailed face, balanced cinematic lighting, "
      "original illustrated pose/composition. NO official frame or screenshot, "
      "NO text, title, logo, watermark, panels or fake UI."
    )

def edit_prompt(row:dict,scene:dict,chars:list[dict])->str:
    selected=[c for c in chars if c["key"] in scene["character_keys"]]
    lines=["Reference image(s) show the same NAMEABLE, CANONICALLY RECOGNIZABLE "
           "anime character(s) who MUST stay consistent in the new scene.",
           "Create ONE wholly NEW 1024x1536 cinematic anime editorial composition "
           "based on the reference portrait(s); this is a scene change, not a "
           "copy or a collage of the identity reference.",
           "Do not re-invent their faces, hair, eyes, costume, silhouette or "
           "signature accessories. Preserve each person's unique identity "
           "through pose changes and background change. Never replace the "
           "named character with generic original people."]
    for i,c in enumerate(selected,1):
        lines.append("IDENTITY "+str(i)+": "+c["name"]+" from "+c["franchise"]+
                     ". Must preserve: "+c["canonical_appearance"])
    lines.extend(["STORY ACTION/FRAME THAT MUST BE ILLUSTRATED: "+
                  scene["visual_instruction"]+".",
                  "Corresponding narration: "+scene["editorial_beat"]+".",
                  "Make the actions, setting and story accurately match the "
                  "named franchise. Portrait 1024x1536, single frame, no "
                  "split screen, NO official anime screenshot, no lettering, "
                  "watermarks, logos, artificial subtitles or title card. "
                  "Natural consistent anatomical proportions and distinct "
                  "unbroken heads, hands and feet; keep faces legible.",
                  "Visual treatment: "+row["visual_bible"]])
    return " ".join(lines)

def save_image(blob:bytes,target:Path)->None:
    if target.exists():
        raise IdentityBlocked("ANCHOR_OR_SCENE_ALREADY_EXISTS_NO_BLIND_REGEN")
    with Image.open(io.BytesIO(blob)) as im:
        im.load()
        if im.width<512 or im.height<768:
            raise IdentityBlocked("IDENTITY_IMAGE_SMALL")
        ImageOps.pad(im.convert("RGB"),(1024,1536),
                     method=Image.Resampling.LANCZOS,
                     color=(14,19,32)).save(target,"PNG")
    if target.stat().st_size<30_000:
        raise IdentityBlocked("IDENTITY_IMAGE_TOO_SMALL_FILE")

def digest(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for part in iter(lambda:f.read(1024*1024),b""):
            h.update(part)
    return h.hexdigest()

def reference_collage(paths:list[Path],output:Path)->Path:
    if not 1<=len(paths)<=3:
        raise IdentityBlocked("BAD_REFERENCES")
    if len(paths)==1:return paths[0]
    if output.exists():
        raise IdentityBlocked("REFERENCE_COLLAGE_ALREADY_EXISTS")
    from PIL import Image,ImageDraw
    result=Image.new("RGB",(1024,1536),(17,19,28))
    col=1024//len(paths)
    for i,path in enumerate(paths):
        with Image.open(path) as img:
            img.load()
            source=ImageOps.contain(img.convert("RGB"),(col,1250),
                                    method=Image.Resampling.LANCZOS)
            result.paste(source,(i*col+(col-source.width)//2,140))
    result.save(output,"PNG")
    return output

def visually_distinct(first:Path,second:Path,minimum_mean_diff:float=3.0)->bool:
    with Image.open(first) as a,Image.open(second) as b:
        a.load();b.load()
        aa=a.convert("RGB").resize((64,96))
        bb=b.convert("RGB").resize((64,96))
        diff=ImageChops.difference(aa,bb)
        value=sum(ImageStat.Stat(diff).mean)/3
        return value>=minimum_mean_diff
