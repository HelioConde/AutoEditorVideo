/**
 * Automatic, visibly readable 2D character idle animation.
 *
 * Light and L are already cut out as separate transparent PNG layers.
 * Animate those approved layers in Remotion; NO skeletal editor, manual
 * body-part separation, additional AI images, or export pipeline is required.
 *
 * This is whole-character 2D puppet motion (breathing, sway, slight lean).
 * It does not fabricate facial expressions, blinks or arm articulation.
 * The table, board and king/hand composites must never be independently moved.
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

type Amp={
  breathingPx:number;
  shoulderFraction:number;
  leanDeg:number;
  driftPx:number;
};

// Previous versions were often <1px *after* size-based damping and fade.
// These are 2D source-canvas pixels (the canvas is 1024x1536).
// Bigger transforms are intentionally kept below a cinematic "puppet wobble".
const PRESETS:Record<CharacterPreset,Amp>={
  ultrassutil:{breathingPx:3.2,shoulderFraction:0.0020,leanDeg:0.32,driftPx:1.4},
  equilibrado:{breathingPx:6.0,shoulderFraction:0.0038,leanDeg:0.70,driftPx:2.8},
  vivo:{breathingPx:10.0,shoulderFraction:0.0060,leanDeg:1.14,driftPx:4.6},
};

const flat=(reason:CharacterPose['reason']):CharacterPose=>({
  enabled:false,translateX:0,translateY:0,
  scaleX:1,scaleY:1,rotateDeg:0,reason
});
const clamp=(x:number,a:number,b:number)=>Math.max(a,Math.min(b,x));
const smoothstep=(x:number)=>{
  const t=clamp(x,0,1);
  return t*t*(3-2*t);
};
const finite=(x:number)=>Number.isFinite(x);

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
  if(!['back_character','front_character'].includes(role) ||
     !['l','light','subject'].includes(id) ||
     !finite(coverage)||coverage<0.020||coverage>0.58 ||
     !finite(fps)||fps<=0||!finite(frame)||
     !finite(sceneStart)||!finite(sceneEnd)||sceneEnd<=sceneStart||
     !PRESETS[preset]){
    return flat('mask-unsafe');
  }

  const duration=sceneEnd-sceneStart;
  const t=clamp((frame-sceneStart)/duration,0,1);
  const elapsed=t*duration/fps;

  // Exact zero at scene boundaries, with a sustained (not sin²-damped)
  // motion envelope for most of the shot. Fade avoids snapping on cuts.
  const envelope=(t<=0||t>=1)?0:
    smoothstep(t/0.13)*smoothstep((1-t)/0.13);
  const isLight=id==='light';
  const frequency=isLight?0.235:0.290; // Light ~4.25s, L ~3.45s
  const phase=isLight?0.53:1.74;
  const breath=Math.sin(2*Math.PI*frequency*elapsed+phase);
  const lean=Math.sin(2*Math.PI*frequency*0.52*elapsed+phase+0.8);
  const shoulders=Math.sin(2*Math.PI*frequency*elapsed+phase+0.9);
  // Preserve table contact more tightly for large / front silhouettes.
  const coverageScale=clamp((0.70-coverage)/0.56,0.38,1);
  const frontScale=role==='front_character'?0.87:1;
  const identityScale=isLight?0.84:1;
  const magnitude=envelope*coverageScale*frontScale*identityScale;
  const presetValues=PRESETS[preset];
  return {
    enabled:true,
    translateX:clamp(presetValues.driftPx*lean*magnitude,-4.6,4.6),
    translateY:clamp(presetValues.breathingPx*breath*magnitude,-10,10),
    scaleX:1+clamp(presetValues.shoulderFraction*shoulders*magnitude,-0.006,0.006),
    scaleY:1+clamp(presetValues.shoulderFraction*breath*magnitude*1.15,-0.007,0.007),
    rotateDeg:clamp(presetValues.leanDeg*lean*magnitude,-1.14,1.14),
    reason:'safe',
  };
};

export const presetNames:CharacterPreset[]=['ultrassutil','equilibrado','vivo'];
