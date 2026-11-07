#!/usr/bin/env python3
"""V10 deterministic 2D performance brush for ONE approved original RGBA.

This is not generative video. Unlike arbitrary motion-field nudges, performance
beats use localized masks and explicit eye/neck/hand keyframes. Each frame
comes from the same original PNG; do not interpolate independent subjects.
Landmarks below are calibrated only for the verified V6 pose-05-1 PNG.
"""
from __future__ import annotations
import math
import cv2
import numpy as np

WIDTH,HEIGHT=1024,1536
SECONDS=8.
X=np.arange(WIDTH,dtype=np.float32)[None,:]
Y=np.arange(HEIGHT,dtype=np.float32)[:,None]

def smooth(x):
    p=np.clip(x,0.,1.)
    return p*p*(3-2*p)

def ellipse(cx,cy,rx,ry,feather=25):
    dist=np.sqrt(((X-cx)/rx)**2+((Y-cy)/ry)**2)
    return np.asarray(1-smooth((dist-.80)/(.35+feather/1000)),dtype=np.float32)

def polygon(vertices,sigma):
    mask=np.zeros((HEIGHT,WIDTH),np.uint8)
    cv2.fillPoly(mask,[np.asarray(vertices,dtype=np.int32)],255)
    return cv2.GaussianBlur(mask.astype(np.float32)/255,(0,0),sigmaX=sigma,sigmaY=sigma)

def blink_envelope(t):
    return max((max(0.,(1+math.cos(math.pi*(t-center)/.22))/2)**1.35
        if abs(t-center)<.22 else 0.) for center in (1.54,5.64))

class PerformanceBrush2D:
    def __init__(self):
        self.head=ellipse(505,425,183,218,30)
        self.hair=polygon([
            (346,249),(417,217),(527,216),(619,245),(669,315),
            (627,422),(576,423),(510,405),(444,430),(350,394)],20)
        self.chest=ellipse(520,854,300,260,25)
        self.tie=polygon([
            (492,689),(537,693),(551,762),(558,1015),
            (557,1173),(491,1165),(484,935)],20)
        self.arm=polygon([
            (703,1115),(775,1128),(818,1420),(767,1500),
            (681,1489),(676,1282)],24)
        self.sleeve=polygon([
            (280,685),(399,676),(466,748),(470,910),
            (336,1000),(219,891)],28)
        self.neck=ellipse(506,624,124,115,20)

    def _blink(self,source,t):
        strength=blink_envelope(t)
        if strength<.005:
            return source
        result=source.copy()
        # Annotated eyes only. Reuse original skin directly below each eye,
        # keep alpha unchanged and add a narrow antialiased eyelid crease.
        for cx,cy,rx,ry in ((453,438,32,17),(557,437,34,17)):
            x0,x1=cx-rx-7,cx+rx+8
            y0,y1=cy-ry-7,cy+ry+8
            roi=result[y0:y1,x0:x1].astype(np.float32)
            xx=np.arange(x0,x1,dtype=np.float32)[None,:]
            yy=np.arange(y0,y1,dtype=np.float32)[:,None]
            mask=np.clip(2.3*np.maximum(0,1-(
                ((xx-cx)/rx)**2+((yy-cy)/ry)**2)),0,1)
            mask=cv2.GaussianBlur(mask,(0,0),sigmaX=2.2)
            # No invented iris/identity. Sample and soften skin of the source.
            pixels=source[min(HEIGHT-1,cy+25),x0:x1,:3].astype(np.float32)
            pixels=cv2.GaussianBlur(pixels[None,:,:],(0,0),sigmaX=3)[0]
            skin=np.broadcast_to(pixels[None,:,:],roi[:,:,:3].shape).copy()
            skin*=1-.06*np.clip(-(yy-cy)/ry,0,1)[:,:,None]
            strength_mask=mask[:,:,None]*strength
            roi[:,:,:3]=roi[:,:,:3]*(1-strength_mask)+skin*strength_mask
            line=np.zeros((y1-y0,x1-x0,3),np.uint8)
            points=np.asarray([[
                (cx-rx+5-x0,cy-2-y0),(cx-8-x0,cy+1-y0),
                (cx+7-x0,cy+1-y0),(cx+rx-4-x0,cy-3-y0)
            ]],dtype=np.int32)
            cv2.polylines(line,points,False,(44,28,28),2,lineType=cv2.LINE_AA)
            ink=cv2.cvtColor(line,cv2.COLOR_RGB2GRAY).astype(np.float32)
            ink=(ink/max(1,float(line.max())))[:,:,None]*strength
            roi[:,:,:3]=roi[:,:,:3]*(1-ink)+np.array(
                [43,29,25],dtype=np.float32)[None,None,:]*ink
            result[y0:y1,x0:x1]=np.uint8(np.clip(roi,0,255))
        return result

    def displacement(self,t):
        t=max(0.,min(float(t),SECONDS))
        yaw=smooth((t-2.)/.86)*(1-smooth((t-3.75)/.78))
        nod=smooth((t-4.13)/.69)*(1-smooth((t-6.45)/.78))
        theta=(.026*yaw-.012*nod)
        # Same affine transform throughout the face core: nose-eye geometry
        # is rigid rather than independently dragging each facial feature.
        dx=self.head*((550-Y)*theta+2.5*yaw)
        dy=self.head*((X-505)*theta+3.7*nod)
        breath=math.sin(2*math.pi*.28*t)*math.sin(math.pi*t/SECONDS)**2
        dx+=self.chest*(X-520)/330*.004*breath*220
        dy+=self.chest*(-2.6*breath)
        hair=math.sin(2*math.pi*.48*t)*math.sin(math.pi*t/SECONDS)**2
        dx+=self.hair*(6.5*hair)
        swing=math.sin(2*math.pi*.42*t+.3)*math.sin(math.pi*t/SECONDS)**2
        dx+=self.tie*((Y-718).clip(min=0)/460)*(11*swing)
        gesture=smooth((t-4.15)/1.08)*(1-smooth((t-6.55)/.96))
        dx+=self.arm*gesture*(15*((Y-1110)/370).clip(0,1))
        dy+=self.arm*gesture*(-6*((Y-1110)/370).clip(0,1))
        thinking=smooth((t-1.15))*(1-smooth((t-2.95)/.8))
        dy+=self.sleeve*(-2.5*thinking)
        dx+=self.neck*(2*yaw)
        return np.asarray(dx,np.float32),np.asarray(dy,np.float32)

    def quality(self,t):
        dx,dy=self.displacement(t)
        gradient=max(float(np.max(abs(np.diff(dx,axis=0)))),
                     float(np.max(abs(np.diff(dx,axis=1)))),
                     float(np.max(abs(np.diff(dy,axis=0)))),
                     float(np.max(abs(np.diff(dy,axis=1)))))
        max_motion=float(np.max(np.sqrt(dx*dx+dy*dy)))
        return {
            "second":round(t,3),
            "maximum_motion_px":round(max_motion,3),
            "max_local_shear":round(gradient,4),
            "blink_fraction":round(blink_envelope(t),3),
            "head_yaw":round(float(smooth((t-2.)/.86)*(1-smooth((t-3.75)/.78))),3),
            "arm_beat":round(float(smooth((t-4.15)/1.08)*(1-smooth((t-6.55)/.96))),3),
            "safe":max_motion<19 and gradient<.28
        }

    def warp(self,source,t):
        if source.shape!=(HEIGHT,WIDTH,4) or source.dtype!=np.uint8:
            raise ValueError("ONE_ORIGINAL_1024X1536_RGBA_REQUIRED")
        if t<=0 or t>=SECONDS:
            return source.copy()
        image=self._blink(source,t)
        dx,dy=self.displacement(t)
        premul=image.astype(np.float32)/255
        premul[:,:,:3]*=premul[:,:,3:4]
        remap_x=np.asarray(X-dx,dtype=np.float32)
        remap_y=np.asarray(Y-dy,dtype=np.float32)
        remapped=cv2.remap(premul,remap_x,remap_y,cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_CONSTANT,
                          borderValue=(0,0,0,0))
        a=remapped[:,:,3:4]
        rgb=remapped[:,:,:3]/np.maximum(a,1e-5)
        return np.uint8(np.clip(np.concatenate([rgb,a],axis=2)*255,0,255))
