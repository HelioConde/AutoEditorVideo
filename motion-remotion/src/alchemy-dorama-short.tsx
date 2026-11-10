import React from 'react';
import {AbsoluteFill, Audio, Img, staticFile, useCurrentFrame} from 'remotion';

/**
 * Alchemy Dorama: same deterministic independent 2D PNG sprite-layer
 * animation strategy as Fofinho EP01 Part 3 (EmanuellyLayerStage).
 *
 * Not the Kids component: it has fixed cast/props, a 60s cap and
 * madeForKids policy. This generic scene stage allows 150-180s original
 * fiction with separate art references, a vector mission menu and
 * flashback color grading. Camera pan alone is NOT character animation.
 *
 * Each PNG referenced here must come from an approved fixed anchor,
 * with provenance and actual visual QA performed by the media pipeline.
 */
export type DoramaMotion =
  'still'|'walk'|'kneel'|'look'|'react'|'gesture'|'point'|'raise'|'reach'|'sway';
export type DoramaCamera = 'still'|'slow-push'|'slow-pull'|'drift-left'|'drift-right';
export type DoramaSprite = {
  anchorId:string; image:string;
  x:number; y:number; width:number;
  zIndex:number; motion:DoramaMotion;
  dx?:number; dy?:number;
};
export type DoramaSystemPanel = {
  kind:'mission'|'emergency'|'completed'|'anomaly';
  title:string; message:string; counter?:string;
};
export type DoramaScene = {
  number:number;
  startFrame:number; endFrame:number;
  backgroundAnchor:string; background:string;
  timeLayer:'PRESENTE'|'FLASHBACK';
  flashbackLabel?:string;
  cameraMotion:DoramaCamera;
  sprites:DoramaSprite[];
  systemPanel?:DoramaSystemPanel|null;
  effect?:'none'|'dust'|'tension'|'flash';
};
export type DoramaCaption = {startFrame:number;endFrame:number;text:string};
export type AlchemyDoramaProps = {
  episodeId:string; title:string; durationFrames:number;
  scenes:DoramaScene[]; captions:DoramaCaption[];
  audio?:string;
};
const clamp=(n:number)=>Math.max(0,Math.min(1,n));
const ease=(n:number)=>{const t=clamp(n);return t*t*(3-2*t);};
const pct=(n:number)=>String(n*100)+'%';

const Sprite:React.FC<{item:DoramaSprite;local:number;duration:number}>=
 ({item,local,duration})=>{
  const t=ease(local/Math.max(1,duration));
  const dx=item.dx??0;
  const dy=item.dy??0;
  const slide=item.motion==='walk'?(-0.035+.07*t):
    item.motion==='reach'?.03*t:
    item.motion==='point'?.018*t:
    dx*t;
  const rise=item.motion==='kneel'?.055*t:
    item.motion==='raise'?-.055*t:dy*t;
  const bob=item.motion==='walk'?Math.sin(local*.31)*4:
    item.motion==='react'?Math.sin(local*.25)*3:
    Math.sin(local*.10)*1.6;
  const tilt=item.motion==='look'?(-2*t):
    item.motion==='sway'?Math.sin(local*.11)*1.6:
    item.motion==='gesture'?Math.sin(local*.20)*1.2:0;
  return <Img src={staticFile(item.image)} style={{
    position:'absolute',zIndex:item.zIndex,
    left:pct(item.x+slide),top:pct(item.y+rise),
    width:pct(item.width),height:'auto',objectFit:'contain',
    opacity:Math.min(1,local/5),
    transform:'translate(-50%,-50%) translateY('+bob+'px) rotate('+tilt+'deg)',
    transformOrigin:'50% 75%',
  }}/>;
};

const MissionPanel:React.FC<{panel:DoramaSystemPanel;local:number}>=({panel,local})=>{
  const danger=panel.kind==='anomaly';
  const glow=danger?'#ff5264':'#48dcff';
  const intro=ease(local/10);
  return <div style={{
    position:'absolute',left:'9%',right:'9%',top:'18%',zIndex:100,
    border:'3px solid '+glow,borderRadius:20,
    background:'rgba(6,18,39,.89)',padding:'26px 30px 32px',
    color:'#f7fcff',fontFamily:'Arial,sans-serif',
    boxShadow:'0 0 36px '+(danger?'rgba(255,82,100,.40)':'rgba(72,220,255,.36)'),
    opacity:intro,transform:'translateY('+((1-intro)*24)+'px)',
  }}>
    <div style={{fontSize:31,letterSpacing:3,color:glow,fontWeight:900}}>
      SISTEMA DO DESTINO
    </div>
    <div style={{height:2,background:glow,opacity:.65,margin:'15px 0 18px'}}/>
    <div style={{fontSize:38,fontWeight:900,lineHeight:1.17}}>
      {panel.title}
    </div>
    <div style={{fontSize:33,lineHeight:1.30,marginTop:16}}>
      {panel.message}
    </div>
    {panel.counter&&<div style={{fontSize:35,fontWeight:900,marginTop:20,color:glow}}>
      {panel.counter}
    </div>}
  </div>;
};

export const AlchemyDoramaShort:React.FC<AlchemyDoramaProps>=(props)=>{
  const frame=useCurrentFrame();
  const scene=props.scenes.find(s=>frame>=s.startFrame&&frame<s.endFrame);
  const caption=props.captions.find(c=>frame>=c.startFrame&&frame<c.endFrame);
  if(!scene)return <AbsoluteFill style={{background:'#101b30'}}/>;
  const local=Math.max(0,frame-scene.startFrame);
  const span=Math.max(1,scene.endFrame-scene.startFrame);
  const t=ease(local/span);
  const camera=scene.cameraMotion;
  const scale=camera==='slow-push'?1.025+.03*t:
    camera==='slow-pull'?1.055-.03*t:1.025;
  const bgX=camera==='drift-left'?-15*t:camera==='drift-right'?15*t:0;
  const flashback=scene.timeLayer==='FLASHBACK';
  return <AbsoluteFill style={{background:'#111a2c',overflow:'hidden'}}>
    <Img src={staticFile(scene.background)} style={{
      position:'absolute',width:'100%',height:'100%',
      objectFit:'cover',
      transform:'translateX('+bgX+'px) scale('+scale+')',
    }}/>
    {[...scene.sprites].sort((a,b)=>a.zIndex-b.zIndex).map((item,i)=>
      <Sprite key={item.anchorId+'-'+i} item={item} local={local} duration={span}/>
    )}
    {scene.effect==='tension'&&<AbsoluteFill style={{
      background:'radial-gradient(circle,transparent 36%,rgba(12,14,30,.27) 100%)',
      pointerEvents:'none'
    }}/>}
    {flashback&&<AbsoluteFill style={{
      background:'rgba(152,99,38,.16)',pointerEvents:'none',
      boxShadow:'inset 0 0 210px 50px rgba(76,44,25,.23)',
    }}/>}
    {flashback&&local<48&&<div style={{
      position:'absolute',top:75,right:58,zIndex:70,fontSize:27,
      color:'#ffe1ae',fontFamily:'Arial,sans-serif',fontWeight:800,
      textShadow:'0 2px 8px #000',
    }}>{scene.flashbackLabel||'FLASHBACK'}</div>}
    {scene.systemPanel&&<MissionPanel panel={scene.systemPanel} local={local}/>}
    {caption&&<div style={{
      position:'absolute',zIndex:120,bottom:190,left:70,right:70,
      background:'rgba(6,15,32,.85)',color:'white',borderRadius:22,
      textAlign:'center',fontSize:48,fontWeight:800,
      lineHeight:1.24,padding:'17px 22px',fontFamily:'Arial,sans-serif',
      textShadow:'0 2px 5px #000',
    }}>{caption.text}</div>}
    {props.audio&&<Audio src={staticFile(props.audio)}/>}
  </AbsoluteFill>;
};
