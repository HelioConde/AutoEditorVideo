import React from 'react';
import {AbsoluteFill, Audio, Img, interpolate, staticFile,
  useCurrentFrame} from 'remotion';

/**
 * Cada quadro vem de uma EDICAO com a referencia privada local.
 * Imagens possuem poses diferentes; a animação 2D auxiliar move luzes
 * e gotas independentemente. NÃO alegar que isto é rigging articulado.
 * Todo conteúdo é Made for Kids. Não contém upload ou CTA.
 */
export type EmanuellyFrame = {
  startFrame:number; endFrame:number; image:string; cue:string; index:number;
};
export type EmanuellyCaption = {startFrame:number; endFrame:number; text:string};
export type EmanuellyProps = {
  episodeId:string; title:string; brand:string; chapter:string;
  durationFrames:number; frames:EmanuellyFrame[];
  captions:EmanuellyCaption[]; audio:string; referenceSha:string;
  madeForKids:true;
};
const clamp={extrapolateLeft:'clamp' as const,extrapolateRight:'clamp' as const};
const captionStyle:React.CSSProperties={
 position:'absolute',bottom:255,left:82,right:82,
 background:'rgba(14,35,66,.84)',color:'#fff',textAlign:'center',
 padding:'21px 24px',borderRadius:30,
 fontSize:56,fontWeight:800,fontFamily:'Arial,sans-serif',
 textShadow:'0 3px 7px #001b38',lineHeight:1.22,
};
const GlowParticles:React.FC<{frame:number;water:boolean}>=({frame,water})=>
 <svg viewBox="0 0 1080 1920" width="100%" height="100%"
   style={{position:'absolute',inset:0,pointerEvents:'none'}}>
   {Array.from({length:water?12:7},(_,i)=>{
     const angle=(i*7.2)%6.28;
     const y=(1570+(i*127)%490-frame*(water?1.3:.32))%1970;
     const x=190+(i*173)%800+Math.sin(frame/27+i)*18;
     const radius=water?14+(i%3)*7:4+(i%4)*3;
     const opacity=water?.35+(i%3)*.13:.22+(i%3)*.09;
     return <g key={i} transform={'translate('+x+','+y+')'}>
       <circle cx={0} cy={0} r={radius} fill="none"
         stroke={water?'#baf5ff':'#fff7dc'} strokeWidth={water?4:2}
         opacity={opacity}/>
       <circle cx={-radius*.32} cy={-radius*.31} r={radius*.22}
         fill="#fff" opacity={opacity}/>
     </g>;
   })}
 </svg>;

export const EmanuellyShort:React.FC<EmanuellyProps>=(props)=>{
 const frame=useCurrentFrame();
 const {frames,captions,durationFrames,brand,chapter,audio,episodeId}=props;
 const active=frames.find(b=>frame>=b.startFrame&&frame<b.endFrame);
 const idx=active?frames.indexOf(active):-1;
 const prev=idx>0?frames[idx-1]:null;
 const beatFrame=active?frame-active.startFrame:0;
 const transition=active?Math.min(1,beatFrame/9):1;
 const moveX=active?Math.sin(beatFrame/27+active.index)*4:0;
 const moveY=active?Math.sin(beatFrame/38)*5:0;
 const zoom=1.024+Math.sin(beatFrame/65)*.005;
 const water=(episodeId.includes('-p03-')||episodeId.includes('-p04-'))
   && Boolean(active&&/gotinha|gota|água|bolha|chuvisco|plim|mágica/i.test(active.cue));
 const caption=captions.find(c=>frame>=c.startFrame&&frame<c.endFrame);
 if(!frames.length)return <AbsoluteFill style={{backgroundColor:'#0d2a4a'}}/>;
 const imageStyle:React.CSSProperties={
   position:'absolute',width:'100%',height:'100%',objectFit:'cover',
   transform:'translate('+moveX+'px,'+moveY+'px) scale('+zoom+')',
 };
 return <AbsoluteFill style={{backgroundColor:'#153c5b',overflow:'hidden'}}>
   {active&&<>
     {prev&&beatFrame<9&&<Img src={staticFile(prev.image)} style={imageStyle}/>}
     <Img src={staticFile(active.image)}
       style={{...imageStyle,opacity:prev?transition:1}}/>
   </>}
   <AbsoluteFill style={{
     background:'linear-gradient(to bottom,rgba(12,28,56,.48) 0%,transparent 19%,transparent 70%,rgba(12,28,56,.43) 100%)',
     pointerEvents:'none'
   }}/>
   <GlowParticles frame={frame} water={water}/>
   <div style={{
     position:'absolute',left:54,right:54,top:89,
     display:'flex',justifyContent:'space-between',alignItems:'center',
     fontFamily:'Arial,sans-serif',fontWeight:900,color:'white',
     textShadow:'0 4px 9px rgba(0,0,0,.8)'
   }}>
     <span style={{fontSize:35}}>EMANUELLY E SEUS AMIGOS</span>
     <span style={{background:'rgba(22,60,93,.72)',padding:'12px 20px',
                   borderRadius:24,fontSize:33}}>{chapter}</span>
   </div>
   {caption&&<div style={captionStyle}>{caption.text}</div>}
   <div style={{position:'absolute',bottom:105,left:74,
     color:'#f5faff',fontFamily:'Arial,sans-serif',
     fontSize:30,fontWeight:700,opacity:.86,
     textShadow:'0 2px 6px #00172d'}}>{brand}</div>
   {audio&&<Audio src={staticFile(audio)}/>}
 </AbsoluteFill>;
};
