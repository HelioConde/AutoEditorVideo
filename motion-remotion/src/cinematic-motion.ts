/**
 * Original, deterministic animation choreography for still-image Shorts.
 *
 * NEVER move the table, board or king+hand independently: current alpha masks
 * include whole sleeves and large body areas. Characters can breathe with a
 * tiny in-place transform, while the whole frame has a cinematic camera move.
 * First frame retains the exact approved scene preview.
 */
export type AnimationMode='cinematica'|'desligada'|'esqueleto2d';
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
  establish:{zoom:1.035,x:-5,y:-8,fill:0.038,focus:0.0},
  duel:     {zoom:1.052,x:10,y:-6,fill:0.040,focus:0.0},
  king:     {zoom:1.078,x:-11,y:-15,fill:0.060,focus:0.32},
  reaction: {zoom:1.052,x:8,y:-9,fill:0.042,focus:0.0},
  reply:    {zoom:1.065,x:9,y:-13,fill:0.060,focus:0.30},
  final:    {zoom:1.043,x:0,y:-12,fill:0.051,focus:0.46},
};

export const motionAtFrame=(
    frame:number,startFrame:number,endFrame:number,
    shotType:string|undefined,sceneId:string,
    mode:AnimationMode='cinematica'):Camera=>{
  if(mode==='desligada')return {zoom:1,panX:0,panY:0,fill:0,focus:0,breath:0,lighting:0};
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

// Per-character idle motion is implemented by character-idle.ts using
// automatic geometry from the source PNGs (no fixed names or episode IDs).

export const cannotMoveSeparately=(role:string)=>[
  'occluder','object','hero_prop'
].includes(role);
