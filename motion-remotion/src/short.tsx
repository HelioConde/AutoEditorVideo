import React from 'react';
import {AbsoluteFill, Audio, Img, Easing, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

type Motion='breathe'|'reveal'|'float'|'chess-slide'|'blood-drop'|'feather'|'apple-bounce';
type Layer={src:string;motion:Motion;x:number;y:number;width:number;dx:number;dy:number;delay:number};
type Caption={startFrame:number;endFrame:number;text:string};
export type ShortProps={id:string;durationFrames:number;background:string;layers:Layer[];
  audio:string;captions:Caption[];hook:string;title:string;effect:string};
const clamp={extrapolateLeft:'clamp' as const,extrapolateRight:'clamp' as const};
const ease=Easing.inOut(Easing.cubic);
const AnimatedLayer:React.FC<{part:Layer}>=({part})=>{
  const frame=useCurrentFrame();
  const f=Math.max(0,frame-part.delay);
  const move=interpolate(f,[0,36],[0,1],{...clamp,easing:ease});
  let dx=0,dy=0,rotation=0,scale=1,opacity=1;
  switch(part.motion){
    case 'breathe': scale=1+0.008*Math.sin(frame/17);dy=3*Math.sin(frame/15);break;
    case 'reveal': opacity=interpolate(frame,[0,24],[0,1],clamp);scale=1.04-.04*move;break;
    case 'float':dy=9*Math.sin(frame/15);rotation=1.5*Math.sin(frame/19);break;
    case 'chess-slide':dx=part.dx*move;dy=part.dy*move;break;
    case 'blood-drop':dy=part.dy*interpolate(f,[0,25],[0,1],{...clamp,easing:Easing.in(Easing.quad)});break;
    case 'feather':dy=part.dy*interpolate(f,[0,115],[0,1],clamp);dx=35*Math.sin(frame/17);rotation=25*Math.sin(frame/23);break;
    case 'apple-bounce':{
      const fall=interpolate(f,[0,24],[0,1],{...clamp,easing:Easing.in(Easing.quad)});
      const bounce=interpolate(f,[0,24,37,52,63,74],[0,0,-78,0,-24,0],clamp);
      dy=part.dy*fall+bounce;rotation=interpolate(f,[0,74],[0,28],clamp);break;
    }
  }
  return <Img src={staticFile(part.src)} style={{position:'absolute',left:part.x,top:part.y,
    width:part.width,height:'auto',
    transform:'translate3d('+dx+'px,'+dy+'px,0) rotate('+rotation+'deg) scale('+scale+')',
    transformOrigin:'center bottom',opacity,objectFit:'contain'}}/>;
};
export const Short:React.FC<ShortProps>=(props)=>{
  const frame=useCurrentFrame();
  const {fps}=useVideoConfig();
  const active=props.captions.find(c=>frame>=c.startFrame&&frame<c.endFrame);
  const hookOn=frame<2.2*fps;
  const zoom=1.035+frame/Math.max(props.durationFrames,1)*.03;
  return <AbsoluteFill style={{backgroundColor:'#090b15',overflow:'hidden',fontFamily:'Arial, sans-serif'}}>
    {props.background?<Img src={staticFile(props.background)} style={{width:'100%',height:'100%',objectFit:'cover',transform:'scale('+zoom+')'}}/>:null}
    <AbsoluteFill style={{background:'linear-gradient(180deg,rgba(0,0,0,.22),transparent 32%,rgba(0,0,0,.45) 100%)'}}/>
    {props.layers.map((p,i)=><AnimatedLayer key={i} part={p}/>)}
    {hookOn?<div style={{position:'absolute',top:170,left:82,right:82,color:'#fff',fontSize:80,
      textAlign:'center',fontWeight:900,textShadow:'0 5px 15px black, 0 2px 4px black',
      opacity:interpolate(frame,[0,6,59,66],[0,1,1,0],clamp)}}>{props.hook}</div>:null}
    {active?<div style={{position:'absolute',top:1345,left:100,right:100,fontSize:67,
      fontWeight:900,letterSpacing:-1.5,color:'#fff',textAlign:'center',lineHeight:1.2,
      textShadow:'4px 4px 5px black, -3px -3px 4px black, 0 0 12px black',
      WebkitTextStroke:'1px #111'}}>{active.text}</div>:null}
    {props.audio?<Audio src={staticFile(props.audio)}/>:null}
  </AbsoluteFill>;
};
