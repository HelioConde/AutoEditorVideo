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
    # Fast close, brief contact, slower release. Both ends have zero velocity.
    for center, closing, opening in ((1.54, .10, .16), (5.64, .12, .19)):
        elapsed = t - center
        if -closing <= elapsed < 0:
            return float(smooth(1 + elapsed / closing))
        if 0 <= elapsed <= opening:
            return float(1 - smooth(max(0., elapsed - .02) / (opening - .02)))
    return 0.


def head_turn(t):
    return smooth((t-2.)/.86)*(1-smooth((t-3.75)/.78))


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
        # Trace both lid contours on the approved pose. Move the lash line
        # across the iris while leaving the fringe and brows in place.
        for columns, upper, lower in (
            ([429, 435, 446, 457, 469, 477], [427, 424, 422, 422, 425, 432],
             [427, 434, 440, 440, 437, 432]),
            ([521, 527, 538, 550, 561, 569], [431, 425, 420, 418, 419, 422],
             [431, 435, 436, 436, 432, 422]),
        ):
            x = np.arange(columns[0], columns[-1] + 1)
            top = np.interp(x, columns, upper)
            bottom = np.interp(x, columns, lower)
            edge = top + strength * (bottom - top)
            y0, y1 = min(upper) - 2, max(lower) + 3
            y = np.arange(y0, y1)[:, None]
            region = result[y0:y1, x[0]:x[-1]+1, :3]
            skin = source[np.rint(bottom).astype(int)+3, x, :3]
            coverage = np.clip(edge-y+1, 0, 1) * np.clip(y-top+2, 0, 1)
            taper = np.clip((bottom-top)/5, 0, 1)
            coverage *= taper * min(1., strength * 8)
            color = region*(1-coverage[:,:,None]) + skin*coverage[:,:,None]
            lash = np.clip(1.6-abs(y-edge), 0, 1) * taper * strength
            region[:] = np.rint(color*(1-lash[:,:,None]) +
                                np.array([48, 29, 25])*lash[:,:,None])
        return result

    def displacement(self,t):
        t=max(0.,min(float(t),SECONDS))
        yaw=head_turn(t)
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
        dx+=self.hair*(2.4*hair + 6*(head_turn(t-.16)-yaw))
        swing=math.sin(2*math.pi*.42*t+.3)*math.sin(math.pi*t/SECONDS)**2
        dx+=self.tie*((Y-718).clip(min=0)/460)*(3*swing + 4*breath + 6*(head_turn(t-.23)-yaw))
        gesture=smooth((t-4.15)/1.08)*(1-smooth((t-6.55)/.96))
        # Rotate the forearm around the elbow. A short anticipation and
        # delayed release give the hand a readable arc through the pose.
        anticipation = smooth((t-3.83)/.32)*(1-smooth((t-4.15)/.42))
        angle = .040*gesture - .006*anticipation
        cosine, sine = math.cos(angle), math.sin(angle)
        dx += self.arm*((1-cosine)*(X-716) + sine*(Y-1115))
        dy += self.arm*((1-cosine)*(Y-1115) - sine*(X-716))
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
            "head_yaw":round(float(head_turn(t)),3),
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
