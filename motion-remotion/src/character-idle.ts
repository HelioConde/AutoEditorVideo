/**
 * Subtle procedural idle motion. Does not generate pixels or claim to animate
 * real eyelids/irises: those need separately approved closed-eye assets.
 * All values are deterministic per frame, character and shot.
 *
 * One whole-character alpha layer can breathe / lean by subpixel amounts, but
 * rotating the head alone or blinking requires a different cutout. Do not
 * deform masks contaminated with hero objects or much of the frame.
 */
export type CharacterPreset='ultrassutil'|'equilibrado'|'vivo';
export type CharacterRole='back_character'|'front_character'|string;
export type CharacterPose={
  enabled:boolean;
  translateX:number;
  translateY:number;
  scaleX:number;
  scaleY:number;
  rotateDeg:number;
  reason:'safe'|'off'|'hero-protected'|'mask-unsafe';
};

type Amp={breathingPx:number;shoulderFraction:number;headTiltDeg:number;driftPx:number};
const PRESETS:Record<CharacterPreset,Amp>={
  ultrassutil:{breathingPx:0.52,shoulderFraction:0.00027,headTiltDeg:0.055,driftPx:0.16},
  equilibrado:{breathingPx:0.88,shoulderFraction:0.00042,headTiltDeg:0.092,driftPx:0.22},
  vivo:{breathingPx:1.19,shoulderFraction:0.00058,headTiltDeg:0.145,driftPx:0.29},
};

const flat=(reason:CharacterPose['reason']):CharacterPose=>({
  enabled:false,translateX:0,translateY:0,
  scaleX:1,scaleY:1,rotateDeg:0,reason
});
const finite=(x:number,low:number,high:number)=>Math.max(low,Math.min(high,x));

/** Independent Light/L breathing cycles so both figures don't sway together. */
export const characterPoseAtFrame=(args:{
  role:CharacterRole;
  id:string;
  coverage:number;
  hasHeroProp:boolean;
  frame:number;
  sceneStart:number;
  sceneEnd:number;
  fps:number;
  preset:CharacterPreset;
  enabled:boolean;
  shotType?:string;
}):CharacterPose=>{
  const {role,id,coverage,hasHeroProp,frame,sceneStart,sceneEnd,fps,preset,enabled}=args;
  if(!enabled)return flat('off');
  if(hasHeroProp)return flat('hero-protected');
  if(!['back_character','front_character'].includes(role)||
     !['l','light','subject'].includes(id)||
     !Number.isFinite(coverage)||coverage<0.025||coverage>0.55||
     !Number.isFinite(fps)||fps<=0||!Number.isFinite(frame)||
     !Number.isFinite(sceneStart)||!Number.isFinite(sceneEnd)||
     !Number.isFinite(PRESETS[preset]?.breathingPx)){
    return flat('mask-unsafe');
  }
  const duration=Math.max(1,sceneEnd-sceneStart);
  const elapsed=finite((frame-sceneStart)/fps,0,duration/fps);
  const t=finite((frame-sceneStart)/duration,0,1);
  // Fades the first and last ~20% of the shot to the approved still.
  // Exact zeros avoid floating-point residue on the first and final frames.
  const envelope=t<=0||t>=1?0:Math.pow(Math.sin(Math.PI*t),2);
  // Real-time breathing instead of scene-relative oscillation; L breathes
  // slightly faster and more visibly than Light.
  const isLight=id==='light';
  const frequency=isLight?0.255:0.305; // 3.92 s / 3.28 s per breath
  const phase=isLight?0.67:2.08;
  const breath=Math.sin(2*Math.PI*frequency*elapsed+phase);
  const nod=Math.sin(2*Math.PI*(frequency*0.53)*elapsed+phase+0.4);
  const shoulder=Math.sin(2*Math.PI*frequency*elapsed+phase+1.1);
  // More foregrounded or large layers are less safe to transform.
  const coverageScale=finite((0.55-coverage)/0.45,0.23,1);
  const frontScale=role==='front_character'?0.72:1;
  const identityScale=isLight?0.77:1.0;
  const magnitude=coverageScale*frontScale*identityScale*envelope;
  const p=PRESETS[preset];
  return {
    enabled:true,
    translateX:finite(p.driftPx*nod*magnitude,-0.30,0.30),
    translateY:finite(p.breathingPx*breath*magnitude,-1.25,1.25),
    scaleX:1+finite(p.shoulderFraction*shoulder*magnitude,-0.0006,0.0006),
    scaleY:1+finite(p.shoulderFraction*breath*magnitude*1.6,-0.001,0.001),
    rotateDeg:finite(p.headTiltDeg*nod*magnitude,-0.15,0.15),
    reason:'safe'
  };
};

/** Utility used by tests/diagnostics and UI when presenting alternatives. */
export const presetNames:CharacterPreset[]=['ultrassutil','equilibrado','vivo'];
