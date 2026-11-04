import React from 'react';
import {AbsoluteFill, Img, staticFile} from 'remotion';

/** Fixed garden/bedroom; character and egg move independently.
 * These are 2D sprite transforms, not articulated character rigging.
 */
export type EmanuellyLayeredScene = {
 index:number; startFrame:number; endFrame:number;
 background:string; pose?:string; egg:string; showEgg:boolean;
 poseX:number; poseY:number; poseSize:number;
 eggX:number; eggY:number; eggSize:number;
 animation:'still'|'walk'|'approach'|'lift'|'prepare'|'promise'|'rock'|'wonder';
 magic?:boolean; night?:boolean;
};
const clamp=(n:number)=>Math.max(0,Math.min(1,n));
const ease=(n:number)=>{const t=clamp(n);return t*t*(3-2*t);};
const pct=(n:number)=>String(n*100)+'%';

export const EmanuellyLayerStage:React.FC<{
  scene:EmanuellyLayeredScene; frame:number;
}>=({scene,frame})=>{
  const local=Math.max(0,frame-scene.startFrame);
  const duration=Math.max(1,scene.endFrame-scene.startFrame);
  const t=ease(local/duration);
  const walk=scene.animation==='walk'||scene.animation==='approach';
  const horizontal=walk?(-.12+.15*t):0;
  const bob=walk?Math.sin(local*.4)*4:
    scene.animation==='prepare'?Math.sin(local*.11)*2:0;
  const eggRock=scene.animation==='rock'?Math.sin(local*.44)*8:
    scene.animation==='lift'?-11*t:0;
  const eggFloat=(scene.animation==='lift'?-0.10*t:0)+
    (scene.animation==='rock'?Math.sin(local*.23)*.004:0);
  const eggGlow=scene.animation==='rock'?
    .3+.15*Math.sin(local*.35):.09;
  const charOpacity=scene.pose?Math.min(1,local/5):0;
  return <AbsoluteFill style={{overflow:'hidden'}}>
    <Img src={staticFile(scene.background)}
      style={{position:'absolute',width:'100%',height:'100%',objectFit:'cover'}}/>
    {scene.night&&<AbsoluteFill style={{
      backgroundColor:'rgba(14,25,70,.35)',pointerEvents:'none',
    }}/>}
    {scene.pose&&<Img src={staticFile(scene.pose)}
      style={{
        position:'absolute',
        width:pct(scene.poseSize),height:'82%',
        objectFit:'contain',objectPosition:'bottom center',
        left:pct(scene.poseX+horizontal),top:pct(scene.poseY),
        opacity:charOpacity,
        transform:'translateX(-50%) translateY('+bob+'px)',
      }}/>}
    {scene.showEgg&&<>
      <div style={{
        position:'absolute',width:pct(scene.eggSize*1.12),
        height:pct(scene.eggSize*.75),
        left:pct(scene.eggX),top:pct(scene.eggY+eggFloat),
        transform:'translate(-50%,-50%)',borderRadius:'50%',
        background:'rgba(95,204,255,'+eggGlow+')',
        filter:'blur(22px)',pointerEvents:'none',
      }}/>
      <Img src={staticFile(scene.egg)}
        style={{
          position:'absolute',width:pct(scene.eggSize),height:'auto',
          objectFit:'contain',
          left:pct(scene.eggX),top:pct(scene.eggY+eggFloat),
          transform:'translate(-50%,-50%) rotate('+eggRock+'deg)',
          transformOrigin:'50% 75%',
        }}/>
    </>}
    {scene.magic&&<svg viewBox="0 0 1080 1920" width="100%" height="100%"
      style={{position:'absolute',inset:0,pointerEvents:'none'}}>
      {Array.from({length:14},(_,i)=>{
        const x=120+(i*157)%810+Math.sin(local/24+i)*12;
        const y=510+(i*193)%720-Math.sin(local/28+i)*12;
        const alpha=.2+.26*(.5+.5*Math.sin(local/11+i));
        return <g key={i} transform={'translate('+x+','+y+')'} opacity={alpha}>
          <path d="M0 -11 L3 -3 L11 0 L3 3 L0 11 L-3 3 L-11 0 L-3 -3 Z"
            fill="#fff4b9"/>
        </g>;
      })}
    </svg>}
  </AbsoluteFill>;
};
