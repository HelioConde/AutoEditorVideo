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
 kitty?:string|null; kittyX?:number; kittyY?:number; kittySize?:number;
 kittenMotion?:'idle'|'pop'|'meow'|'paws'|'hop'|'snuggle'|'approach';
 nest?:string|null; nestX?:number; nestY?:number; nestSize?:number;
 water?:string|null; waterCount?:number;
 waterX?:number; waterY?:number; waterSize?:number;
 futureGlow?:boolean;
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
    {scene.nest&&<Img src={staticFile(scene.nest)}
      style={{
        position:'absolute',width:pct(scene.nestSize??.34),
        height:'auto',objectFit:'contain',
        left:pct(scene.nestX??.67),top:pct(scene.nestY??.82),
        transform:'translate(-50%,-50%)',
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
    {scene.kitty&&<Img src={staticFile(scene.kitty)}
      style={{
        position:'absolute',
        width:pct(scene.kittySize??.23),height:'auto',
        objectFit:'contain',
        left:pct((scene.kittyX??.67)+
          (scene.kittenMotion==='approach'?
            -.16*(1-t):0)),
        top:pct((scene.kittyY??.76)+
          (scene.kittenMotion==='pop'?
            .09*(1-t):0)),
        transform:'translate(-50%,-50%) translateY('+
          (scene.kittenMotion==='hop'?
            (-18*Math.abs(Math.sin(local*.23))):
           scene.kittenMotion==='paws'?(-6*Math.sin(local*.35)):
           scene.kittenMotion==='snuggle'?(2*Math.sin(local*.15)):0)+
          'px) rotate('+
          (scene.kittenMotion==='meow'?
            (3*Math.sin(local*.2)):0)+'deg)',
        opacity:scene.kittenMotion==='pop'?Math.min(1,t*2):1,
      }}/>}
    {scene.water&&Array.from({
      length:Math.max(0,Math.min(6,scene.waterCount??0)),
    },(_,i)=><Img key={i} src={staticFile(scene.water!)}
      style={{
        position:'absolute',
        width:pct(scene.waterSize??.07),height:'auto',
        left:pct((scene.waterX??.56)+
          (i-1)*.07+Math.sin(local*.04+i)*.025),
        top:pct((scene.waterY??.61)-
          Math.abs(Math.sin(local*.06+i))* .065),
        transform:'translate(-50%,-50%) rotate('+
          (Math.sin(local*.045+i)*12)+'deg)',
        opacity:Math.min(1,local/10),
      }}/>)}
    {scene.futureGlow&&<svg viewBox="0 0 1080 1920"
      style={{position:'absolute',inset:0,width:'100%',height:'100%',
              pointerEvents:'none'}}>
      {Array.from({length:2},(_,i)=>{
        const x=370+i*315;
        const y=1150-25*Math.sin(local*.025+i);
        const a=.13+.15*Math.abs(Math.sin(local*.032+i));
        return <g key={i}>
          <ellipse cx={x} cy={y} rx={94} ry={139}
            fill="#f7f2fe" opacity={a}/>
          <ellipse cx={x} cy={y} rx={108} ry={158}
            fill="none" stroke="#fff7fc" strokeWidth={7} opacity={a}/>
        </g>;
      })}
    </svg>}
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
