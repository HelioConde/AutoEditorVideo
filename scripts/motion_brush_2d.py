#!/usr/bin/env python3
"""Editable mask-and-vector 2D Motion Brush prototype (not Runway AI).

Each brushed region has a directional animation curve and soft mask.
Face, torso, hand-on-chin and joint anchors are explicitly protected. Warps
the same original RGBA with inverse flow and premultiplied alpha. No generative
inpainting, no ability to synthesize unseen body surfaces, no bone rig.
"""
from __future__ import annotations
import json
import math
from pathlib import Path

import cv2
import numpy as np

WIDTH,HEIGHT=1024,1536
DURATION=8.0

class BrushBlocked(ValueError):
    pass

def smooth(x:float)->float:
    x=max(0.,min(1.,float(x)))
    return x*x*(3.-2.*x)

def load_config(path:Path)->dict:
    config=json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema")!="autoeditorvideo/motion-brush-v1" or config.get("canvas")!=[WIDTH,HEIGHT]:
        raise BrushBlocked("MOTION_BRUSH_CONFIG_INVALID")
    if len(config.get("brushes",[]))<2 or len(config.get("protections",[]))<2:
        raise BrushBlocked("MASKS_AND_PROTECTIONS_REQUIRED")
    identifiers=set()
    for brush in config["brushes"]:
        name=brush.get("id")
        vertices=brush.get("polygon")
        if not isinstance(name,str) or name in identifiers or not isinstance(vertices,list) or len(vertices)<3:
            raise BrushBlocked("INVALID_BRUSH_ID_OR_POLYGON")
        identifiers.add(name)
        if any(len(pt)!=2 or not (0<=float(pt[0])<WIDTH and 0<=float(pt[1])<HEIGHT) for pt in vertices):
            raise BrushBlocked("BRUSH_OUTSIDE_CANVAS")
        if not 10<=brush.get("feather_px",0)<=110:
            raise BrushBlocked("MASK_FEATHER_OUTSIDE_SAFE_RANGE")
        motion=brush.get("motion",{})
        if motion.get("kind") not in ("gesture","sway") or len(motion.get("amplitude_px",[]))!=2:
            raise BrushBlocked("BRUSH_MOTION_INVALID")
        if max(abs(float(x)) for x in motion["amplitude_px"])>25:
            raise BrushBlocked("BRUSH_TOO_STRONG")
    for protection in config["protections"]:
        ellipse=protection.get("ellipse")
        if not isinstance(ellipse,list) or len(ellipse)!=4 or min(ellipse[2:])<=0:
            raise BrushBlocked("PROTECT_ELLIPSE_INVALID")
    return config

def paint_polygon(vertices:list,feather:int)->np.ndarray:
    mask=np.zeros((HEIGHT,WIDTH),np.uint8)
    points=np.array(vertices,dtype=np.int32)
    cv2.fillPoly(mask,[points],255)
    sigma=feather/2.3
    return cv2.GaussianBlur(mask.astype(np.float32)/255.,(0,0),sigmaX=sigma,sigmaY=sigma).clip(0,1)

def paint_ellipse(data:list,feather:int)->np.ndarray:
    mask=np.zeros((HEIGHT,WIDTH),np.uint8)
    x,y,rx,ry=[int(q) for q in data]
    cv2.ellipse(mask,(x,y),(rx,ry),0,0,360,255,-1)
    return cv2.GaussianBlur(mask.astype(np.float32)/255.,(0,0),
                            sigmaX=feather/2.,sigmaY=feather/2.).clip(0,1)

def motion_progress(motion:dict,second:float)->float:
    if second<=0 or second>=DURATION:
        return 0.
    if motion["kind"]=="sway":
        phase=math.sin(2*math.pi*float(motion.get("hz",.3))*second)
        envelope=math.sin(math.pi*second/DURATION)**2
        return phase*envelope
    start=float(motion["starts_at"])
    peak=float(motion["peak_at"])
    end=float(motion["ends_at"])
    if not (0<=start<peak<end<=DURATION):
        raise BrushBlocked("INVALID_GESTURE_TIMING")
    return smooth((second-start)/(peak-start))*(1-smooth((second-peak)/(end-peak)))

class MotionBrush2D:
    def __init__(self,config:dict):
        self.config=config
        self.brushes=[
            (brush,paint_polygon(brush["polygon"],brush["feather_px"]))
            for brush in config["brushes"]
        ]
        protects=[paint_ellipse(p["ellipse"],p["feather_px"]) for p in config["protections"]]
        protection=np.zeros((HEIGHT,WIDTH),np.float32)
        for protect in protects:
            protection=np.maximum(protection,protect)
        self.protection=protection
        self.max_displacement=float(config["limits"]["max_displacement_px"])
        self.max_gradient=float(config["limits"]["max_neighbour_gradient"])
        self.y=np.arange(HEIGHT,dtype=np.float32)[:,None]
        self.x=np.arange(WIDTH,dtype=np.float32)[None,:]

    def displacement(self,second:float)->tuple[np.ndarray,np.ndarray]:
        dx=np.zeros((HEIGHT,WIDTH),np.float32)
        dy=np.zeros_like(dx)
        if second<=0 or second>=DURATION:
            return dx,dy
        for brush,mask in self.brushes:
            t=motion_progress(brush["motion"],second)
            vx,vy=brush["motion"]["amplitude_px"]
            weight=mask*(1-self.protection)
            dx+=weight*float(vx)*t
            dy+=weight*float(vy)*t
        length=np.sqrt(dx*dx+dy*dy)
        maximum=np.maximum(1.,length/max(1e-4,self.max_displacement))
        dx=dx/maximum
        dy=dy/maximum
        # Reduce the motion amplitude, not the safety threshold, whenever
        # neighboring pixels would shear too far apart. All brush colors,
        # face protection and start/end identity remain untouched.
        strain=max(float(np.max(np.abs(np.diff(dx,axis=1)))),
                   float(np.max(np.abs(np.diff(dy,axis=1)))),
                   float(np.max(np.abs(np.diff(dx,axis=0)))),
                   float(np.max(np.abs(np.diff(dy,axis=0)))))
        if strain>self.max_gradient:
            correction=(self.max_gradient*.98)/strain
            dx*=correction
            dy*=correction
        return dx,dy

    def quality(self,second:float)->dict:
        dx,dy=self.displacement(second)
        step=max(float(np.max(np.abs(np.diff(dx,axis=1)))),
                 float(np.max(np.abs(np.diff(dy,axis=1)))),
                 float(np.max(np.abs(np.diff(dx,axis=0)))),
                 float(np.max(np.abs(np.diff(dy,axis=0)))))
        maximum=float(np.max(np.sqrt(dx*dx+dy*dy)))
        return {"second":round(second,3),
                "max_displacement_px":round(maximum,4),
                "max_neighbour_gradient":round(step,5),
                "protections_enabled":True,
                "brushes":[{"id":brush["id"],"motion_fraction":round(
                    motion_progress(brush["motion"],second),4)}
                    for brush,_ in self.brushes],
                "within_safe_bounds":maximum<=self.max_displacement+.001 and step<=self.max_gradient}

    def warp(self,source:np.ndarray,second:float)->np.ndarray:
        if source.shape!=(HEIGHT,WIDTH,4) or source.dtype!=np.uint8:
            raise BrushBlocked("BRUSH_REQUIRES_ONE_ORIGINAL_1024X1536_RGBA")
        if second<=0 or second>=DURATION:
            return source.copy()
        dx,dy=self.displacement(second)
        # Apply one smooth, bounded reverse displacement field. Mask weights
        # prevent dragging unpainted areas; no global TPS deformation.
        mx=np.ascontiguousarray(self.x-dx,dtype=np.float32)
        my=np.ascontiguousarray(self.y-dy,dtype=np.float32)
        premul=source.astype(np.float32)/255.
        premul[:,:,:3]*=premul[:,:,3:4]
        warped=cv2.remap(premul,mx,my,cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_CONSTANT,borderValue=(0,0,0,0))
        alpha=warped[:,:,3:4]
        rgb=warped[:,:,:3]/np.maximum(alpha,1e-5)
        result=np.clip(np.concatenate([rgb,alpha],axis=2)*255.,0,255).astype(np.uint8)
        untouched=(np.abs(dx)+np.abs(dy))<.002
        result[untouched]=source[untouched]
        return result

    def debug_masks(self,source:np.ndarray)->np.ndarray:
        canvas=source.copy().astype(np.float32)
        rgb=canvas[:,:,:3]
        for index,(brush,mask) in enumerate(self.brushes):
            color=np.array([(45,210,250),(255,174,48),(230,76,190)][index%3],np.float32)
            amount=mask[:,:,None]*.46
            rgb=rgb*(1-amount)+color[None,None,:]*amount
        color=np.array((84,225,122),np.float32)
        amount=self.protection[:,:,None]*.45
        rgb=rgb*(1-amount)+color[None,None,:]*amount
        canvas[:,:,:3]=rgb
        canvas[:,:,3]=np.maximum(canvas[:,:,3],65)
        return np.clip(canvas,0,255).astype(np.uint8)
