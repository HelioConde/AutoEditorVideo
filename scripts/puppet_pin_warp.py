#!/usr/bin/env python3
"""True pinned 2D image warping, independent of the anime/video project.

Fixed pins lock the background/border and stable hips; movable pins control
head, hand, elbow and chest. Inverse thin-plate-spline (TPS) interpolation
warps ONE original RGBA texture; it is not crossfading unrelated poses.
CPU/OpenCV only. Pins may be tuned for a different source illustration.
"""
from __future__ import annotations
import math
import cv2
import numpy as np

WIDTH, HEIGHT = 1024, 1536
SECONDS = 8
# Calibrated on the original V6 foreground PNG "pose-05-1.png".
# Coordinates are image pixels, not sprite-sheet or background positions.
PINS = {
 "hair_crown": (500,247), "forehead_left":(394,398),
 "forehead_right":(608,401), "cheek_left":(415,496),
 "cheek_right":(580,495), "chin":(510,546), "neck":(519,588),
 "shoulder_left":(270,671), "shoulder_right":(741,676),
 "chest_left":(423,796), "chest_right":(647,807),
 "sternum":(532,865), "hand_chin":(478,587),
 "hand_chin_lower":(450,651), "elbow_left":(289,814),
 "elbow_right":(766,1059), "wrist_right":(738,1298),
 "fingertips_right":(739,1401), "hip_left":(366,1133),
 "hip_right":(654,1137), "belt":(516,1150),
 "hem_left":(258,1304), "hem_right":(696,1303),
 "foot_left":(320,1480), "foot_right":(684,1480),
}
# Explicit stationary pins: no image-border movement or whole-body sliding.
for i,point in enumerate(((0,0),(512,0),(1023,0),(0,500),
                           (1023,500),(0,920),(1023,920),
                           (0,1535),(512,1535),(1023,1535))):
    PINS[f"fixed_border_{i:02d}"] = point

NAMES=tuple(PINS)
SOURCE=np.array(list(PINS.values()),dtype=np.float64)
UNIT=SOURCE/np.array([WIDTH,HEIGHT],dtype=np.float64)
COARSE=(128,192) # Inverse sampling mesh for CPU, upscaled to full-res remap.

def smooth(t:float)->float:
    t=max(0.,min(1.,t))
    return t*t*(3.-2.*t)

def pin_offsets(second:float)->dict[str,tuple[float,float]]:
    """Motion story: breathe, look sideways, consider, lift free right hand."""
    t=max(0.,min(float(second),SECONDS))
    envelope=math.sin(math.pi*t/SECONDS)**2
    breath=math.sin(t*2*math.pi*.30)*envelope
    glance=(smooth((t-1.35)/.7)-smooth((t-3.35)/.7))*.94*envelope
    contemplate=(smooth((t-3.4)/.65)-smooth((t-6.6)/.65))*envelope
    gesture=(smooth((t-4.05)/.8)-smooth((t-6.6)/.9))*envelope
    return {
        "hair_crown":(18*glance,-2*glance),
        "forehead_left":(13*glance,-1*glance),
        "forehead_right":(15*glance,-2*glance),
        "cheek_left":(8*glance,1*glance),
        "cheek_right":(9*glance,1*glance),
        "chin":(4*glance,2*glance),
        "hand_chin":(-15*contemplate,15*contemplate),
        "hand_chin_lower":(-12*contemplate,12*contemplate),
        "elbow_left":(-7*contemplate,3*contemplate),
        "elbow_right":(32*gesture,-28*gesture),
        "wrist_right":(58*gesture,-65*gesture),
        "fingertips_right":(65*gesture,-76*gesture),
        "chest_left":(2*breath,-2*breath),
        "chest_right":(-2*breath,-2*breath),
        "sternum":(0,-3*breath),
        "shoulder_left":(-1*breath,-1*breath),
        "shoulder_right":(1*breath,-1*breath)
    }

def pin_positions(second:float)->dict[str,tuple[float,float]]:
    offsets=pin_offsets(second)
    return {name:(float(x+offsets.get(name,(0,0))[0]),
                  float(y+offsets.get(name,(0,0))[1]))
            for name,(x,y) in PINS.items()}

def _kernel(dist_sq:np.ndarray)->np.ndarray:
    return dist_sq*np.log(np.maximum(dist_sq,1e-9))

def _inverse_tps(second:float)->tuple[np.ndarray,np.ndarray]:
    """Map DESTINATION pixels back to SOURCE with stationary/moving pins."""
    dest=np.array(list(pin_positions(second).values()),dtype=np.float64)
    dest/=np.array([WIDTH,HEIGHT],dtype=np.float64)
    count=len(dest)
    difference=dest[:,None,:]-dest[None,:,:]
    k=_kernel(np.sum(difference*difference,axis=2))
    k+=np.eye(count)*.000005
    p=np.column_stack([np.ones(count),dest])
    matrix=np.block([[k,p],[p.T,np.zeros((3,3))]])
    coeff=np.linalg.solve(matrix,np.vstack([UNIT,np.zeros((3,2))]))
    grid_w,grid_h=COARSE
    yy,xx=np.mgrid[0:grid_h,0:grid_w]
    samples=np.column_stack([xx.ravel()/(grid_w-1),
                             yy.ravel()/(grid_h-1)])
    differences=samples[:,None,:]-dest[None,:,:]
    kernel=_kernel(np.sum(differences*differences,axis=2))
    affine=np.column_stack([np.ones(len(samples)),samples])
    mapped=(kernel@coeff[:count]+affine@coeff[count:]).reshape(
        grid_h,grid_w,2)
    mx=cv2.resize(mapped[:,:,0].astype(np.float32),
                  (WIDTH,HEIGHT),interpolation=cv2.INTER_LINEAR)*WIDTH
    my=cv2.resize(mapped[:,:,1].astype(np.float32),
                  (WIDTH,HEIGHT),interpolation=cv2.INTER_LINEAR)*HEIGHT
    return mx,my

from functools import lru_cache

@lru_cache(maxsize=1)
def _identity_tps()->tuple[np.ndarray,np.ndarray]:
    return _inverse_tps(0.)

def warp_rgba(image:np.ndarray,second:float)->np.ndarray:
    """Pixel-safe premultiplied alpha, one original source, no ghost poses."""
    if image.shape!=(HEIGHT,WIDTH,4) or image.dtype!=np.uint8:
        raise ValueError("PIN_SOURCE_MUST_BE_ORIGINAL_1024x1536_RGBA")
    if second<=0 or second>=SECONDS:
        return image.copy()
    mx,my=_inverse_tps(second)
    # Cancel the TPS sampling grid's own subpixel identity offset.
    # Otherwise the first nonzero frame causes a whole-body blur/flash.
    base_x,base_y=_identity_tps()
    mx=mx-base_x+np.arange(WIDTH,dtype=np.float32)[None,:]
    my=my-base_y+np.arange(HEIGHT,dtype=np.float32)[:,None]
    normalized=image.astype(np.float32)/255.
    alpha=normalized[:,:,3:4]
    pre=np.concatenate([normalized[:,:,:3]*alpha,alpha],axis=2)
    result=cv2.remap(pre,mx,my,interpolation=cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_CONSTANT,borderValue=(0,0,0,0))
    out_alpha=result[:,:,3:4]
    rgb=result[:,:,:3]/np.maximum(out_alpha,0.0001)
    return np.clip(np.concatenate([rgb,out_alpha],axis=2)*255.,
                   0,255).astype(np.uint8)
