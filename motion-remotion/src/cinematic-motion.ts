/**
 * Original, deterministic animation choreography for still-image Shorts.
 *
 * NEVER move the table, board or king+hand independently: current alpha masks
 * include whole sleeves and large body areas. Characters can breathe with a
 * tiny in-place transform, while the whole frame has a cinematic camera move.
 * First frame retains the exact approved scene preview.
 */
export type AnimationMode='cinematica'|'desligada'|'esqueleto2d'|'malha2d'|'pins2d';
export type ShotProfile='establish'|'duel'|'king'|'reaction'|'reply'|'final';

type Camera={zoom:number;panX:number;panY:number;fill:number;focus:number;breath:number;lighting:number};

const clamp=(v:number,min:number,max:number)=>Math.min(max,Math.max(min,v));
const ease=(v:number)=>{const x=clamp(v,0,1);return x*x*(3-2*x);};
const interpolate=(a:number,b:number,t:number)=>a+(b-a)*t;

export const profileForShot=(shotType:string|undefined,_sceneId:string):ShotProfile=>{
  // These categories work across productions, genres and arbitrary scene ids.
  // Previous logic assigned camera behavior by numbered Death Note shots.
  const name=(shotType||'').toLowerCase();
  if(/final|closing|outro|endcard|checkmate|top_board/.test(name))return 'final';
  if(/wide|establish|overview|opening|intro|landscape/.test(name))return 'establish';
  if(/reaction|close|portrait|emotion|face/.test(name))return 'reaction';
  if(/reply|response|answer/.test(name))return 'reply';
  if(/hand|move|action|detail|item|object|macro|king/.test(name))return 'king';
  if(/duel|dialog|conversation|shoulder|(^|_)ots(_|$)/.test(name))return 'duel';
  return 'establish';
};

// All pan values are in pixels inside the 940x1410 portrait content.
// Deliberately no camera shake / random jitter / object deformation.
const profiles:Record<ShotProfile,{zoom:number;x:number;y:number;fill:number;focus:number}> = {
  // Stable framing: subtle progressive push/pull; never a sudden camera jump.
  // The image and every RGBA character/prop layer use the same camera matrix.
  establish:{zoom:1.038,x:-1.2,y:-1.4,fill:0.025,focus:0.0},
  duel:     {zoom:1.042,x:1.0,y:-1.4,fill:0.027,focus:0.0},
  king:     {zoom:1.048,x:-1.2,y:-1.0,fill:0.033,focus:0.25},
  reaction: {zoom:1.046,x:1.0,y:-1.0,fill:0.028,focus:0.0},
  reply:    {zoom:1.045,x:1.0,y:-1.6,fill:0.029,focus:0.22},
  final:    {zoom:1.034,x:0,y:-1.2,fill:0.025,focus:0.35},
};

export const motionAtFrame=(
    frame:number,startFrame:number,endFrame:number,
    shotType:string|undefined,sceneId:string,
    mode:AnimationMode='cinematica'):Camera=>{
  if(mode==='desligada'||mode==='malha2d'||mode==='pins2d')return {zoom:1,panX:0,panY:0,fill:0,focus:0,breath:0,lighting:0};
  const duration=Math.max(1,endFrame-startFrame);
  const t=clamp((frame-startFrame)/duration,0,1);
  const smooth=ease(t);
  const profile=profiles[profileForShot(shotType,sceneId)];
  // First frame is exact approved composition. Movement develops gently.
  // Breathing fades to zero at scene boundaries to prevent a cut jerk.
  const envelope=Math.pow(Math.sin(Math.PI*t),2);
  // Two slow breaths per 5 seconds, bounded in normalized scene time.
  const breathe=envelope*Math.sin(t*Math.PI*3.2);
  // No flicker / flashes: a gentle red-blue light modulation.
  const light=envelope*(0.74+0.26*Math.sin(t*Math.PI*2.0));
  const emphasis=profile.focus*envelope*
    Math.exp(-Math.pow((t-0.56)/0.21,2));
  return {
    zoom:interpolate(1,profile.zoom,smooth),
    panX:profile.x*smooth,
    panY:profile.y*smooth,
    fill:profile.fill*light,
    focus:emphasis,
    breath:breathe,
    lighting:light,
  };
};



/**
 * Continuous zoom-in/out for the opening. Former versions made virtual jump
 * cuts at 1.25s / 2.45s, which caused visibly disorienting flicker.
 *
 * A smooth sine envelope starts moving at frame zero, peaks around 2.5s,
 * and returns to zero by frame 5 WITHOUT a transform discontinuity.
 * Pan deliberately remains zero so the viewer can see character animation.
 * The legacy function name is retained for existing renderers, but it no
 * longer performs any cut.
 */
export const openingCutAtFrame=(frame:number,fps:number,
                               mode:AnimationMode):{zoom:number;panX:number;panY:number;beat:number}=>{
  const flat={zoom:0,panX:0,panY:0,beat:-1};
  if(mode!=='cinematica'||!Number.isFinite(frame)||!Number.isFinite(fps)||
     frame<0||fps<=0||frame>=5*fps)return flat;
  const phase=Math.PI*clamp(frame/fps/5,0,1);
  return {zoom:Math.sin(phase)*.040,panX:0,panY:0,beat:0};
};

/**
 * A long still must remain alive WITHOUT fake cuts. Use a smooth breathing
 * zoom in/out of at most 2.2%, no pan, and fade motion near scene edges.
 * A multilayer scene can show the (separately composed) character idle motion
 * underneath this camera; a flattened PNG only supports whole-image zoom.
 */
export const longHoldCutAtFrame=(
    frame:number,startFrame:number,endFrame:number,fps:number,
    mode:AnimationMode):{zoom:number;panX:number;panY:number;beat:number}=>{
  const flat={zoom:0,panX:0,panY:0,beat:-1};
  if(mode!=='cinematica'||![frame,startFrame,endFrame,fps].every(Number.isFinite)||
     fps<=0||frame<startFrame||frame>=endFrame||
     endFrame-startFrame<4.5*fps)return flat;
  const start=Math.max(startFrame,5*fps);
  if(frame<start)return flat;
  const elapsed=(frame-start)/fps;
  const remaining=(endFrame-frame)/fps;
  const fadeIn=ease(elapsed/.45);
  const fadeOut=ease(remaining/.45);
  const cycle=Math.sin(Math.PI*elapsed/4.6);
  return {
    zoom:.022*cycle*cycle*fadeIn*fadeOut,
    panX:0,panY:0,
    beat:0,
  };
};

// Per-character idle motion is implemented by character-idle.ts using
// automatic geometry from the source PNGs (no fixed names or episode IDs).

export const cannotMoveSeparately=(role:string)=>[
  'occluder','object','hero_prop'
].includes(role);
