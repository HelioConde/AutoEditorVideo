/** Stable playback for authored RGBA pose sequences. No synthetic rigging. */
export type RigPlayback='pingpong'|'once'|'loop';
export type PoseTimelineArgs={
  frame:number;sceneStart:number;compositionFps:number;
  rigFps:number;frameCount:number;playback?:RigPlayback;
};

/**
 * Pingpong avoids the last-frame-to-first-frame teleport common in a raw loop.
 * "once" holds the last pose for a one-way gesture; "loop" is intentional
 * for seamlessly animated artist-authored cycles.
 */
export const poseFrameIndex=({
  frame,sceneStart,compositionFps,rigFps,frameCount,playback='pingpong'
}:PoseTimelineArgs):number=>{
  if(![frame,sceneStart,compositionFps,rigFps,frameCount].every(Number.isFinite)
    || compositionFps<=0 || rigFps<=0 || !Number.isInteger(frameCount)
    || frameCount<2 || frameCount>24){
    return 0;
  }
  const progress=Math.max(0,frame-sceneStart);
  const steps=Math.floor(progress*rigFps/compositionFps);
  if(playback==='once')return Math.min(frameCount-1,steps);
  if(playback==='loop')return steps%frameCount;
  const period=2*(frameCount-1);
  const p=steps%period;
  return p<frameCount?p:period-p;
};
