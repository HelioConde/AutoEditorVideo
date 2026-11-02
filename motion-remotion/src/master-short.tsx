import React from 'react';
import {AbsoluteFill,Audio,Img,interpolate,staticFile,useCurrentFrame,useVideoConfig} from 'remotion';

export type Scene={id:string;subject:'personagens'|'objeto';startFrame:number;endFrame:number;background:string;foreground:string};
export type Caption={startFrame:number;endFrame:number;text:string};
export type MasterProps={id:string;durationFrames:number;audio:string;scenes:Scene[];captions:Caption[];hook:string};
const clamp={extrapolateLeft:'clamp' as const,extrapolateRight:'clamp' as const};

const Shot:React.FC<{scene:Scene;opacity:number}>=({scene,opacity})=>{
  const frame=useCurrentFrame();
  const elapsed=Math.max(0,frame-scene.startFrame);
  const length=Math.max(1,scene.endFrame-scene.startFrame);
  const ratio=Math.min(1,elapsed/length);
  const zoom=1+0.017*ratio;
  const drift=(scene.subject==='objeto'?4:1.8)*Math.sin(elapsed/26);
  const bob=(scene.subject==='objeto'?3:1.3)*Math.sin(elapsed/31);
  const urlbg=staticFile(scene.background);
  const urlfg=staticFile(scene.foreground);
  // Imagem-mãe tem razão 2:3. 940x1410 preserva o quadro INTEIRO
  // e deixa margem lateral para os personagens; jamais usar cover no original.
  const aligned={position:'absolute' as const,left:70,top:245,width:940,height:1410,
                 objectFit:'contain' as const};
  return <AbsoluteFill style={{opacity,background:'#070912',overflow:'hidden'}}>
    <Img src={urlbg} style={{position:'absolute',inset:0,width:'100%',height:'100%',
      objectFit:'cover',filter:'blur(60px) brightness(.34)',transform:'scale(1.25)'}}/>
    <div style={{position:'absolute',left:70,top:245,width:940,height:1410,
      transform:'scale('+zoom+')',transformOrigin:'center center',overflow:'hidden'}}>
      <Img src={urlbg} style={{position:'absolute',inset:0,width:'100%',height:'100%',objectFit:'contain'}}/>
      <Img src={urlfg} style={{position:'absolute',inset:0,width:'100%',height:'100%',
        objectFit:'contain',transform:'translate('+drift+'px,'+bob+'px)'}}/>
    </div>
  </AbsoluteFill>;
};

export const MasterShort:React.FC<MasterProps>=({scenes,audio,captions,hook,durationFrames})=>{
  const frame=useCurrentFrame();
  const {fps}=useVideoConfig();
  if(!scenes.length)return <AbsoluteFill style={{background:'#080a14'}}/>;
  let idx=scenes.findIndex(s=>frame>=s.startFrame&&frame<s.endFrame);
  if(idx<0)idx=frame<scenes[0].startFrame?0:scenes.length-1;
  const current=scenes[idx];
  const previous=idx>0?scenes[idx-1]:null;
  const fade=previous?interpolate(frame,[current.startFrame,current.startFrame+7],[0,1],clamp):1;
  const caption=captions.find(c=>frame>=c.startFrame&&frame<c.endFrame);
  return <AbsoluteFill style={{background:'#080a14',fontFamily:'Arial,sans-serif'}}>
    {previous&&fade<1?<Shot scene={previous} opacity={1}/>:null}
    <Shot scene={current} opacity={fade}/>
    <AbsoluteFill style={{background:'linear-gradient(180deg,rgba(0,0,0,.15),transparent 20%,rgba(0,0,0,.13) 55%,rgba(0,0,0,.65) 100%)'}}/>
    {hook&&frame<fps*2.2?<div style={{position:'absolute',top:100,left:75,right:75,
      fontSize:76,lineHeight:1.1,color:'#fff',textAlign:'center',fontWeight:900,
      textShadow:'0 4px 14px #000,0 1px 5px #000',
      opacity:interpolate(frame,[0,6,fps*1.8,fps*2.2],[0,1,1,0],clamp)}}>{hook}</div>:null}
    {caption?<div style={{position:'absolute',top:1290,left:88,right:88,
      fontSize:65,lineHeight:1.18,fontWeight:900,textAlign:'center',color:'#fff',
      textShadow:'0 3px 7px #000,3px 3px 5px #000,-2px -2px 6px #000'}}>{caption.text}</div>:null}
    {audio?<Audio src={staticFile(audio)}/>:null}
  </AbsoluteFill>;
};
