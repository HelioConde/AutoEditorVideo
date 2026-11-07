#!/usr/bin/env python3
"""Check authored transparent character pose sequences without generating media.

This is a geometry/pixel-difference preflight, NOT proof that motion, expression,
identity or contact with props is semantically correct. Human review stays required.
"""
from __future__ import annotations

from pathlib import Path
import math

from PIL import Image, ImageChops

CANVAS=(1024,1536)
THUMB=(256,384)
EDGE_MARGIN=8

class PoseBlocked(ValueError):
    pass

def inspect_poses(files:list[Path])->dict:
    if not isinstance(files,list) or not 2<=len(files)<=12:
        raise PoseBlocked("REQUIRE_2_TO_12_REAL_POSE_FRAMES")
    centers=[]
    extents=[]
    coverages=[]
    previous=None
    changes=[]
    for file in files:
        with Image.open(file) as original:
            original.load()
            if original.mode!="RGBA" or original.size!=CANVAS:
                raise PoseBlocked("POSE_MUST_BE_1024x1536_RGBA")
            image=original.copy()
        alpha=image.getchannel("A")
        bbox=alpha.getbbox()
        if bbox is None:
            raise PoseBlocked("EMPTY_POSE")
        left,top,right,bottom=bbox
        if (left<EDGE_MARGIN or top<EDGE_MARGIN or
            right>CANVAS[0]-EDGE_MARGIN or bottom>CANVAS[1]-EDGE_MARGIN):
            raise PoseBlocked("POSE_CUT_OFF_AT_FRAME_EDGE")
        w,h=right-left,bottom-top
        if w<35 or h<35:
            raise PoseBlocked("POSE_TOO_SMALL_FOR_ANIMATION")
        histogram=alpha.histogram()
        visible=sum(histogram[32:])
        if visible/CANVAS[0]/CANVAS[1]<.003:
            raise PoseBlocked("POSE_ALPHA_COVERAGE_TOO_SMALL")
        center=((left+right)/2/CANVAS[0],(top+bottom)/2/CANVAS[1])
        centers.append(center)
        extents.append((w,h))
        coverages.append(visible)
        thumbnail=image.resize(THUMB,Image.Resampling.BILINEAR)
        if previous is not None:
            previous_thumb,prior_center,prior_extent,prior_coverage=previous
            travel=math.hypot(center[0]-prior_center[0],
                              center[1]-prior_center[1])
            if travel>.13:
                raise PoseBlocked("POSE_TELEPORTS_BETWEEN_FRAMES")
            if not .72<=visible/prior_coverage<=1.38:
                raise PoseBlocked("POSE_OPACITY_OR_SIZE_JUMP")
            if not all(.70<=extent/prev_extent<=1.42
                       for extent,prev_extent in zip((w,h),prior_extent)):
                raise PoseBlocked("POSE_BOUNDING_BOX_JUMPS")
            # Compare visible RGB and alpha, not hashes: identical pixels can be
            # re-encoded as different files. Both mouth expressions (RGB changes)
            # and limb movements (alpha changes) are valid authored frames.
            # Transparent RGB can contain arbitrary invisible pixel data from
            # image providers. Ignore it rather than falsely approving motion
            # that will never appear in the composed video.
            before_alpha=previous_thumb.getchannel("A")
            after_alpha=thumbnail.getchannel("A")
            black=Image.new("RGB",THUMB,(0,0,0))
            before_visible=Image.composite(
                previous_thumb.convert("RGB"),black,before_alpha)
            after_visible=Image.composite(
                thumbnail.convert("RGB"),black,after_alpha)
            rgb=ImageChops.difference(before_visible,after_visible)
            lum=rgb.convert("L")
            alpha_delta=ImageChops.difference(before_alpha,after_alpha)
            visual=ImageChops.lighter(lum,alpha_delta)
            changed=visual.point(lambda x:255 if x>=25 else 0).histogram()[255]
            small_visible=min(visible,prior_coverage)*THUMB[0]*THUMB[1]/(CANVAS[0]*CANVAS[1])
            fraction=changed/max(1,small_visible)
            if fraction<.008:
                raise PoseBlocked("POSE_FRAMES_VISUALLY_IDENTICAL")
            changes.append(round(fraction,4))
        previous=(thumbnail,center,(w,h),visible)
    return {
        "pose_frame_count":len(files),
        "minimum_changed_subject_fraction":min(changes),
        "maximum_subject_center_shift":round(
            max((math.hypot(b[0]-a[0],b[1]-a[1])
                 for a,b in zip(centers,centers[1:])),default=0),4),
        "edge_margin_pixels":EDGE_MARGIN,
        "technical_pose_geometry_checked":True,
        "actual_character_identity_or_action_verified":False,
        "human_visual_review_required":True,
    }
