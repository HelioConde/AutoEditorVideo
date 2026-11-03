import React from 'react';
import {AbsoluteFill, Audio, Img, Easing, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {openingCutAtFrame,longHoldCutAtFrame} from './cinematic-motion';
import {groupLegacyCaptionWords} from './caption-pacing';

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
  const grouped=React.useMemo(
    ()=>groupLegacyCaptionWords(props.captions,fps),
    [props.captions,fps]
  );
  const active=grouped.find(c=>frame>=c.startFrame&&frame<c.endFrame);
  const hookOn=frame<2.2*fps;
  const opener=openingCutAtFrame(frame,fps,'cinematica');
  const hold=longHoldCutAtFrame(frame,0,props.durationFrames,fps,'cinematica');
  const zoom=Math.min(1.14,1.025+frame/Math.max(props.durationFrames,1)*.015+opener.zoom+hold.zoom);
  const camera='translate('+(opener.panX+hold.panX).toFixed(2)+'px,'+
    (opener.panY+hold.panY).toFixed(2)+'px) scale('+zoom.toFixed(5)+')';
  return <AbsoluteFill style={{backgroundColor:'#090b15',overflow:'hidden',fontFamily:'Arial, sans-serif'}}>
    {/* Reframe both art and props together; static 15s openings are no longer
        possible in the cinematic preview without distorting character masks. */}
    <AbsoluteFill style={{transform:camera,transformOrigin:'center center'}}>
      {props.background?<Img src={staticFile(props.background)} style={{width:'100%',height:'100%',objectFit:'cover'}}/>:null}
      <AbsoluteFill style={{background:'linear-gradient(180deg,rgba(0,0,0,.22),transparent 32%,rgba(0,0,0,.45) 100%)'}}/>
      {props.layers.map((p,i)=><AnimatedLayer key={i} part={p}/>)}
    </AbsoluteFill>
    {hookOn?<div style={{position:'absolute',top:115,left:70,right:70,
      padding:'18px 24px',borderRadius:20,
      background:'rgba(4,7,19,.82)',border:'2px solid rgba(255,255,255,.18)',
      color:'#fff',fontSize:props.hook.length>44?65:78,lineHeight:1.10,
      textAlign:'center',fontWeight:900,textShadow:'0 6px 15px black,0 2px 5px black',
      opacity:interpolate(frame,[0,4,54,66],[0.94,1,1,0],clamp)}}>{props.hook}</div>:null}
    {active?<div style={{position:'absolute',top:1280,left:78,right:78,
      padding:'18px 25px',borderRadius:22,background:'rgba(2,5,15,.86)',
      border:'2px solid rgba(255,255,255,.18)',
      boxShadow:'0 12px 30px rgba(0,0,0,.7)',
      fontSize:77,fontWeight:900,letterSpacing:-1,color:'#fff',
      textAlign:'center',lineHeight:1.12,
      textShadow:'0 5px 12px #000',WebkitTextStroke:'2px #070914'}}>
      {active.words?.length?active.words.map((word,index)=><React.Fragment key={index}>
        {index>0?' ':null}<span style={{
          color:frame>=word.startFrame&&frame<word.endFrame?'#ffd166':'#fff',
        }}>{word.text}</span>
      </React.Fragment>):active.text}</div>:null}
    {props.audio?<Audio src={staticFile(props.audio)}/>:null}
  </AbsoluteFill>;
};
