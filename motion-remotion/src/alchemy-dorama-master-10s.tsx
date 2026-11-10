import React from 'react';
import {AbsoluteFill, Audio, interpolate, Img, staticFile, useCurrentFrame} from 'remotion';

/** Single master -> 5 edits -> animated 10s scene. Manual QA before publication.
 * All cutouts are transparent PNGs on the ORIGINAL full-frame canvas.
 * This is 2D puppet animation, not skeletal rigging or full lip-sync. */
export type AlchemyMaster10Props = {
  pilotId:string; durationFrames:number;master:string;background:string;
  ren:string;king:string;elara:string;sword:string;audio:string;
  frameReferenceSha:string;noNarration:boolean;noYouTubeUpload:boolean;
};
const clamp=(x:number)=>Math.max(0,Math.min(1,x));
const smooth=(x:number)=>{const y=clamp(x);return y*y*(3-2*y);};
type LayerSpec={source:string;depth:number;origin:string;
  x:number;y:number;rotate:number;scale:number;opacity?:number};
const FullSourceCanvas:React.FC<LayerSpec>=(p)=>
  <Img src={staticFile(p.source)} style={{
    position:'absolute',top:0,left:0,width:'100%',height:'100%',
    objectFit:'cover',zIndex:p.depth,transformOrigin:p.origin,
    transform:'translate3d('+p.x.toFixed(2)+'px,'+p.y.toFixed(2)+'px,0) rotate('+
      p.rotate.toFixed(3)+'deg) scale('+p.scale.toFixed(5)+')',
    opacity:p.opacity??1,willChange:'transform',
  }}/>;

const TextLine:React.FC<{text:string;frame:number;from:number;until:number}>=
 ({text,frame,from,until})=>{
  if(frame<from||frame>=until)return null;
  const a=Math.min(smooth((frame-from)/9),smooth((until-frame)/8));
  return <div style={{
    position:'absolute',bottom:160,left:75,right:75,zIndex:51,
    textAlign:'center',fontFamily:'Arial,sans-serif',
    fontSize:43,fontWeight:900,letterSpacing:.4,lineHeight:1.2,
    color:'#fff',textShadow:'0px 3px 12px #020919, 0px 5px 4px #020919',
    opacity:a,transform:'translateY('+((1-a)*15)+'px)',
  }}>{text}</div>;
};
const SystemUI:React.FC<{frame:number}>=({frame})=>{
  const t=smooth((frame-222)/17);
  if(frame<222)return null;
  const glow=.52+.48*Math.sin((frame-222)*.18)**2;
  return <div style={{
    position:'absolute',left:'8%',right:'8%',top:'43%',zIndex:61,
    opacity:t,transform:'perspective(650px) translateY('+((1-t)*55)+
      'px) scale('+(.91+.09*t)+')',
    background:'rgba(5,23,57,.86)',border:'3px solid #62d5ff',
    boxShadow:'0 0 '+(20+28*glow)+'px rgba(20,156,255,.9), inset 0 0 38px rgba(25,95,204,.36)',
    borderRadius:15,padding:'22px 26px 24px',
    fontFamily:'Georgia,serif',color:'#eefbff',textAlign:'center',
  }}>
    <div style={{fontSize:30,fontWeight:900,letterSpacing:2,color:'#9eeaff'}}>
      ✧ SISTEMA DO DESTINO ✧
    </div>
    <div style={{height:2,margin:'16px 12px',
      background:'linear-gradient(90deg,transparent,#4fd5ff,transparent)'}}/>
    <div style={{fontFamily:'Arial,sans-serif',fontSize:28,
      fontWeight:850,letterSpacing:1.8}}>MISSÃO PRINCIPAL</div>
    <div style={{fontSize:36,margin:'18px 0 8px',fontWeight:800,lineHeight:1.18}}>
      Conquiste a princesa
    </div>
    <div style={{fontSize:34,fontWeight:900,color:'#ff7d8e',marginTop:17}}>
      Falha: MORTE
    </div>
  </div>;
};
export const AlchemyDoramaMaster10s:React.FC<AlchemyMaster10Props>=(p)=>{
  const frame=useCurrentFrame();
  const bgPush=interpolate(frame,[0,299],[1.008,1.032]);
  const breath=Math.sin(frame*.145);
  const focusRen=smooth((frame-130)/40);
  const swordMove=smooth((frame-145)/60);
  const kingGesture=smooth((frame-20)/95);
  const princessLook=smooth((frame-165)/65);
  return <AbsoluteFill style={{background:'#10131c',overflow:'hidden'}}>
    <div style={{position:'absolute',inset:0,
      transform:'scale('+bgPush.toFixed(4)+')'}}>
      <Img src={staticFile(p.background)} style={{
        position:'absolute',inset:0,width:'100%',height:'100%',objectFit:'cover',
      }}/>
    </div>
    <FullSourceCanvas source={p.king} depth={10} origin="50% 42%"
      x={-kingGesture*2.3} y={breath*.8} rotate={-.48*kingGesture}
      scale={1+kingGesture*.004}/>
    <FullSourceCanvas source={p.elara} depth={20} origin="75% 58%"
      x={-princessLook*2.5} y={-princessLook*3.0+breath*.5}
      rotate={-.38*princessLook} scale={1+princessLook*.003}/>
    <FullSourceCanvas source={p.ren} depth={30} origin="30% 82%"
      x={2*focusRen} y={-2.4*breath*focusRen}
      rotate={.55*focusRen} scale={1+.005*focusRen}/>
    <FullSourceCanvas source={p.sword} depth={40} origin="87% 23%"
      x={-9*swordMove} y={10*swordMove} rotate={-3.2*swordMove}
      scale={1}/>
    <AbsoluteFill style={{
      pointerEvents:'none',zIndex:46,
      background:'radial-gradient(ellipse at 50% 70%, transparent 34%, rgba(10,12,32,.30) 100%)',
    }}/>
    {Array.from({length:9},(_,i)=>{
      const x=(i*173+83)%1010;const y=(i*379+50+frame*(.20+.03*i))%1910;
      return <div key={i} style={{position:'absolute',zIndex:47,
        left:x,top:y,height:2+i%2,width:2+i%2,borderRadius:'50%',
        background:'#ffe9bb',opacity:.18,boxShadow:'0 0 8px #ffe9bb',
        pointerEvents:'none'}}/>;
    })}
    <TextLine text="VOCÊ ROUBOU O SELO REAL!" frame={frame} from={22} until={110}/>
    <TextLine text="EU SOU INOCENTE!" frame={frame} from={113} until={205}/>
    <SystemUI frame={frame}/>
    {p.audio&&<Audio src={staticFile(p.audio)}/>}
  </AbsoluteFill>;
};
