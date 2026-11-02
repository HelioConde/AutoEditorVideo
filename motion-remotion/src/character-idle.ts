/**
 * Generic 2D idle animation for ANY character extracted as an RGBA scene layer.
 *
 * No hardcoded episode, name, number, or shot-specific motion. Avoid stretching
 * the flattened body: use rigid 2D translation and very small pivoted rotation.
 * The optional per-layer geometry is measured offline from EXISTING alpha masks.
 * No new AI images, keyframes, body-part exports or manual staging are needed.
 */
export type CharacterPreset='ultrassutil'|'equilibrado'|'vivo';
export type CharacterRole=string;
export type CharacterPose={
  enabled:boolean;
  translateX:number;
  translateY:number;
  scaleX:number;
  scaleY:number;
  rotateDeg:number;
  reason:'safe'|'off'|'hero-protected'|'mask-unsafe';
};

type Amplitude={vertical:number;horizontal:number;rotation:number};
const PRESETS:Record<CharacterPreset,Amplitude>={
  // The previously approved ultrassutil is the starting intensity.
  ultrassutil:{vertical:3.2,horizontal:0.65,rotation:0.12},
  equilibrado:{vertical:5.2,horizontal:1.1,rotation:0.18},
  vivo:{vertical:7.5,horizontal:1.7,rotation:0.25},
};
const clamp=(x:number,a:number,b:number)=>Math.max(a,Math.min(b,x));
const smoothstep=(x:number)=>{
  const t=clamp(x,0,1);
  return t*t*(3-2*t);
};
const flat=(reason:CharacterPose['reason']):CharacterPose=>({
  enabled:false,translateX:0,translateY:0,scaleX:1,scaleY:1,
  rotateDeg:0,reason,
});
const valid=(x:number)=>Number.isFinite(x);
const seedOf=(name:string):number=>{
  // FNV1a hash: deterministic for every arbitrary character name, including
  // "personagem-17", accents or non-Latin text (utf16 code units).
  let h=2166136261>>>0;
  for(let i=0;i<name.length;i++)h=Math.imul(h^name.charCodeAt(i),16777619)>>>0;
  return h>>>0;
};

export const characterPoseAtFrame=(args:{
  role:CharacterRole;
  id:string;
  coverage:number;
  /** Fraction of character mask near furniture/another non-character object. */
  contactRisk?:number;
  /** Fraction touching the independently layered hand/hero object. */
  heroRisk?:number;
  /** Stable per-character/per-scene seed, independent of any named show. */
  motionSeed?:number;
  /** Character occupied fraction of canvas height (optional). */
  heightFraction?:number;
  frame:number;
  sceneStart:number;
  sceneEnd:number;
  fps:number;
  preset:CharacterPreset;
  enabled:boolean;
  /** Legacy field; a hero elsewhere in the scene is NOT a reason to freeze. */
  hasHeroProp?:boolean;
  shotType?:string;
}):CharacterPose=>{
  const {role,id,coverage,frame,sceneStart,sceneEnd,fps,preset,enabled}=args;
  if(!enabled)return flat('off');
  if(!['back_character','front_character'].includes(role)||
     typeof id!=='string'||!id.trim()||
     !valid(coverage)||coverage<0.015||coverage>0.72||
     !valid(frame)||!valid(sceneStart)||!valid(sceneEnd)||
     sceneEnd<=sceneStart||!valid(fps)||fps<=0||!PRESETS[preset]){
    return flat('mask-unsafe');
  }
  const heroRisk=valid(args.heroRisk??NaN)
    ?clamp(args.heroRisk!,0,1)
    :(args.hasHeroProp?0.065:0);
  // The hero object could contain fingers/sleeves that physically attach to
  // this exact character. Do not animate that character independently.
  if(heroRisk>=0.04)return flat('hero-protected');

  const contactRisk=valid(args.contactRisk??NaN)
    ?clamp(args.contactRisk!,0,1):0.12;
  const extent=valid(args.heightFraction??NaN)
    ?clamp(args.heightFraction!,0,1):0.55;

  // Contact-aware amplitude. A tight table/seat contact is mostly static.
  // Free-standing characters retain the tested ultrassutil range.
  const contactScale=clamp(1-contactRisk*2.15,0.37,1);
  const extentScale=extent>0.75?0.87:1;
  const heroScale=clamp(1-heroRisk*15,0.48,1);
  const strength=contactScale*extentScale*heroScale;

  const t=clamp((frame-sceneStart)/(sceneEnd-sceneStart),0,1);
  const envelope=(t<=0||t>=1)?0:
    smoothstep(t/0.11)*smoothstep((1-t)/0.11);
  // Derive the rhythm from the character's ACTUAL identity and image hash,
  // not fixed scene 01..06 or "l"/"light". Two harmonics disrupt mechanical
  // looping without introducing any random flicker or high-frequency shake.
  const seed=valid(args.motionSeed??NaN)
    ?Math.floor(Math.abs(args.motionSeed!))>>>0
    :seedOf(id);
  const phase=(seed%1009)/1009*2*Math.PI;
  const frequency=0.24+((seed>>>11)%101)/101*0.075;
  const seconds=(frame-sceneStart)/fps;
  const breathe=(Math.sin(2*Math.PI*frequency*seconds+phase)-
    Math.sin(phase))*0.82+
    0.18*(Math.sin(2*Math.PI*frequency*0.53*seconds+phase*0.83)-
    Math.sin(phase*0.83));
  const lean=(Math.sin(2*Math.PI*frequency*0.49*seconds+phase+0.9)-
    Math.sin(phase+0.9))*0.70+
    (Math.sin(2*Math.PI*frequency*0.23*seconds+phase*0.5)-
    Math.sin(phase*0.5))*0.30;
  const amp=PRESETS[preset];
  return {
    enabled:true,
    translateX:clamp(amp.horizontal*lean*strength*envelope,-1.7,1.7),
    translateY:clamp(amp.vertical*breathe*strength*envelope,-7.5,7.5),
    scaleX:1,
    scaleY:1,
    rotateDeg:clamp(amp.rotation*lean*strength*envelope,-0.25,0.25),
    reason:'safe',
  };
};
export const presetNames:CharacterPreset[]=['ultrassutil','equilibrado','vivo'];
