import React from 'react';
import {AbsoluteFill, Audio, OffthreadVideo, Sequence, interpolate,
  staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

/**
 * Visuais originais e vetoriais: estrelas, passarinhos e formas.
 * Producao sem conteudo de terceiros. Movimentos de objetos reais, nao zooms.
 * Games exige gravacao verificada; nunca simula gameplay.
 */
export type PilotScene = {
  id:string; startFrame:number; endFrame:number; headline:string;
  visual:string; video?:string;
};
export type PilotCaption = {startFrame:number;endFrame:number;text:string};
export type PilotProps = {
  episodeId:string;channel:'games'|'kids';durationFrames:number;
  scenes:PilotScene[];audio:string;captions:PilotCaption[];brand:string;
};
const clamp = {extrapolateLeft:'clamp' as const,extrapolateRight:'clamp' as const};
const W=1080,H=1920;
const stars = (cx:number,cy:number,r:number):string =>
  Array.from({length:10},(_,i)=>{
    const a=-Math.PI/2+i*Math.PI/5;
    const d=i%2===0?r:r*.47;
    return [cx+d*Math.cos(a),cy+d*Math.sin(a)].join(',');
  }).join(' ');
const Headline:React.FC<{text:string,kids:boolean}>=({text,kids})=>
 <div style={{
   position:'absolute',left:70,right:70,top:kids?124:145,
   display:'flex',justifyContent:'center',textAlign:'center',
   fontSize:kids?68:74,fontWeight:900,fontFamily:'Arial,sans-serif',
   letterSpacing:-1.4,lineHeight:1.18,color:'#fff',
   textShadow:'0 5px 8px rgba(0,0,0,.62)',
   padding:'14px 24px',borderRadius:24,
   background:kids?'rgba(17,52,88,.36)':'rgba(7,9,22,.72)',
 }}>{text}</div>;
const ChildStar:React.FC<{x:number;y:number;color:string;size?:number;wave?:number}>=
 ({x,y,color,size=130,wave=0})=>
 <g transform={"translate("+x+","+(y+Math.sin(wave)*8)+")"}>
   <polygon points={stars(0,0,size)} fill={color} stroke="#fff" strokeWidth={8}/>
   <ellipse cx={-size*.19} cy={-size*.07} rx={8} ry={15} fill="#17263D"/>
   <ellipse cx={size*.19} cy={-size*.07} rx={8} ry={15} fill="#17263D"/>
   <path d={"M "+(-size*.21)+" "+(size*.18)+" Q 0 "+(size*.34)+" "+(size*.21)+" "+(size*.18)}
    fill="none" stroke="#17263D" strokeWidth={7} strokeLinecap="round"/>
 </g>;
const House:React.FC<{x:number;y:number;color:string;showLabel?:boolean}>=
 ({x,y,color,showLabel=true})=>
 <g>
   <rect x={x-93} y={y} width={186} height={190} rx={16} fill={color}
     stroke="#fff" strokeWidth={7}/>
   <polygon points={(x-118)+','+y+' '+x+','+(y-122)+' '+(x+118)+','+y}
     fill={color} stroke="#fff" strokeWidth={7}/>
   <rect x={x-20} y={y+98} width={40} height={92} rx={8} fill="#f6ecce"/>
   {showLabel&&<circle cx={x+65} cy={y+42} r={11} fill="#fef9dc"/>}
 </g>;

const StarStory:React.FC<{scene:number;frame:number}>=({scene,frame})=>{
 const colors=['#f97373','#ffdb63','#4eaffb'];
 const p=Math.min(1,Math.max(0,(frame%90)/90));
 const x=scene>=3?800:scene===2?230:540;
 const selected=scene===4?Math.min(1,frame/45):0;
 return <svg viewBox="0 0 1080 1920" width="100%" height="100%">
  <defs><linearGradient id="skyS" x1="0" y1="0" x2="1" y2="1">
    <stop stopColor="#174d93"/><stop offset="1" stopColor="#26245c"/></linearGradient></defs>
  <rect width={W} height={H} fill="url(#skyS)"/>
  {Array.from({length:20},(_,i)=><circle key={i} cx={(i*197+91)%W}
    cy={(i*239+210)%1700} r={3+(i%3)*2} fill="#eff8ff" opacity={.4+(i%5)*.1}/>)}
  {scene===0?<ChildStar x={540} y={820} color={colors[2]} size={210} wave={frame/17}/>:
  scene===1?
    colors.map((color,i)=><ChildStar key={i} x={260+i*280} y={840}
      color={color} size={133} wave={frame/20+i}/>:
  scene===2?
    <><House x={600} y={970} color={colors[0]}/>
     <ChildStar x={270} y={820} color={colors[2]} wave={frame/20}/></>:
  scene===3?
    <><House x={255} y={970} color={colors[1]}/>
     <House x={805} y={970} color={colors[2]}/>
     <ChildStar x={470+p*95} y={760} color={colors[2]} wave={frame/20}/></>:
    <><House x={540} y={970} color={colors[2]}/>
     <ChildStar x={540} y={790+selected*190} color={colors[2]}
        size={140} wave={frame/22}/></>}
  <text x={540} y={1410} textAnchor="middle" fill="#d8efff"
    fontFamily="Arial" fontSize={52} fontWeight={700}>
     {['Onde está a azul?','Vermelha, amarela e azul','A vermelha não é!','Encontramos a azul!','Azul com azul!'][scene]}
  </text>
 </svg>;
};
const Bird:React.FC<{x:number;y:number;wing:number;hue:string}>=({x,y,wing,hue})=>
 <g transform={"translate("+x+","+(y+Math.sin(wing)*6)+")"}>
   <ellipse cx={0} cy={0} rx={61} ry={49} fill={hue} stroke="#fff" strokeWidth={5}/>
   <ellipse cx={-14} cy={2} rx={25} ry={18}
    fill="#fff" opacity={.7} transform={"rotate("+Math.sin(wing)*10+")"}/>
   <circle cx={22} cy={-18} r={8} fill="#233048"/>
   <polygon points="50,-6 88,8 50,20" fill="#ffc85b"/>
   <path d="M-15 41 L-20 62 M10 41 L5 62" stroke="#694b35" strokeWidth={6}/>
 </g>;
const BirdStory:React.FC<{scene:number;frame:number}>=({scene,frame})=>{
 const count=[0,2,3,5,5][scene];
 const loc=[[250,850],[700,840],[460,1070],[870,1080],[600,630]];
 const colors=['#79cdf2','#ffa97d','#fbcc5c','#a5d99f','#d5b6ff'];
 return <svg viewBox="0 0 1080 1920" width="100%" height="100%">
   <defs><linearGradient id="birdBG" x1="0" y1="0" x2="1" y2="1">
     <stop stopColor="#b7ecff"/><stop offset="1" stopColor="#dcf6c6"/></linearGradient></defs>
   <rect width={W} height={H} fill="url(#birdBG)"/>
   <ellipse cx={530} cy={1745} rx={620} ry={235} fill="#6fc78d"/>
   <rect x={490} y={820} width={94} height={930} rx={40} fill="#906643"/>
   <path d="M510 930 Q280 700 175 830 M560 925 Q850 690 940 825 M520 1110 Q360 1030 190 1110 M560 1110 Q770 1035 970 1150 M535 810 Q575 600 620 580"
     fill="none" stroke="#7b573e" strokeWidth={29} strokeLinecap="round"/>
   {[{x:235,y:750},{x:800,y:710},{x:320,y:1000},{x:845,y:1045},{x:575,y:550}].map((p,i)=>
    <ellipse key={i} cx={p.x} cy={p.y} rx={145} ry={90} fill="#66bf84" opacity={.82}/>)}
   {loc.slice(0,count).map(([x,y],i)=><Bird key={i} x={x} y={y}
      hue={colors[i]} wing={frame/8+i}/>)}
   <text x={540} y={1450} textAnchor="middle" fill="#25565a"
     fontFamily="Arial" fontSize={86} fontWeight={900}>
     {scene===0?'Vamos contar?':count+' passarinho'+(count>1?'s':'')}
   </text>
 </svg>;
};
const ShapeFace:React.FC<{x:number;y:number;kind:'square'|'triangle'|'circle';
 hue:string;size:number;frame:number}>=({x,y,kind,hue,size,frame})=>{
 const pulse=Math.sin(frame/16)*4;
 const outline={stroke:'#fff',strokeWidth:7};
 return <g transform={"translate("+x+","+(y+pulse)+")"}>
   {kind==='square'?<rect x={-size/2} y={-size/2} width={size} height={size}
      rx={12} fill={hue} {...outline}/>:
    kind==='triangle'?<polygon points={"0,"+(-size*.64)+" "+(-size*.62)+","+(size*.48)+" "+(size*.62)+","+(size*.48)}
      fill={hue} {...outline}/>:
    <circle r={size/2} fill={hue} {...outline}/>}
   <circle cx={-size*.15} cy={-size*.08} r={9} fill="#233048"/>
   <circle cx={size*.15} cy={-size*.08} r={9} fill="#233048"/>
   <path d={"M "+(-size*.16)+" "+(size*.12)+" Q 0 "+(size*.24)+" "+(size*.16)+" "+(size*.12)}
      stroke="#233048" fill="none" strokeWidth={6} strokeLinecap="round"/>
 </g>;
};
const ShapeStory:React.FC<{scene:number;frame:number}>=({scene,frame})=>{
 const q=scene>=1?{x:540,y:1040}:{x:270,y:870};
 const t=scene>=2?{x:540,y:660}:{x:790,y:850};
 const c=scene>=3?{x:540,y:1000}:{x:800,y:1360};
 return <svg viewBox="0 0 1080 1920" width="100%" height="100%">
   <defs><linearGradient id="shapeBG" x1="0" y1="0" x2="1" y2="1">
      <stop stopColor="#c6efff"/><stop offset="1" stopColor="#faf1d6"/></linearGradient></defs>
   <rect width={W} height={H} fill="url(#shapeBG)"/>
   <ellipse cx={540} cy={1580} rx={630} ry={240} fill="#a9dca8"/>
   {scene>=1&&<rect x={353} y={850} width={374} height={380} rx={12}
       fill="#80b5f2" opacity={.32}/>}
   <ShapeFace kind="square" x={q.x} y={q.y}
    size={scene>=1?365:245} hue="#79b8fa" frame={frame}/>
   <ShapeFace kind="triangle" x={t.x} y={t.y}
    size={scene>=2?416:245} hue="#ffbd69" frame={frame}/>
   {(scene>=3||scene===0)&&<ShapeFace kind="circle" x={c.x} y={c.y}
      size={scene>=3?120:180} hue="#fc83b9" frame={frame}/>}
   <text x={540} y={1510} textAnchor="middle" fill="#285570"
     fontFamily="Arial" fontSize={72} fontWeight={900}>
     {['Formas amigas','Um quadrado!','Um triângulo!','Uma janela redonda!','Nossa casinha!'][scene]}
   </text>
 </svg>;
};
const KidsScene:React.FC<{id:string;index:number}>=({id,index})=>{
 const frame=useCurrentFrame();
 if(id==='kids-001-estrela-azul') return <StarStory scene={index} frame={frame}/>;
 if(id==='kids-002-cinco-passarinhos')return <BirdStory scene={index} frame={frame}/>;
 return <ShapeStory scene={index} frame={frame}/>;
};
const Captions:React.FC<{items:PilotCaption[];kids:boolean}>=({items,kids})=>{
 const frame=useCurrentFrame();
 const selected=items.find(item=>frame>=item.startFrame&&frame<item.endFrame);
 if(!selected)return null;
 return <div style={{
   position:'absolute',bottom:300,left:90,right:90,padding:'18px 24px',
   background:kids?'rgba(18,68,90,.86)':'rgba(9,9,18,.89)',
   color:'#fff',borderRadius:26,textAlign:'center',fontFamily:'Arial,sans-serif',
   fontWeight:900,fontSize:kids?55:65,lineHeight:1.12,
   textShadow:'0 3px 5px rgba(0,0,0,.3)',
 }}>{selected.text}</div>;
};
export const PilotShort:React.FC<PilotProps>=(props)=>{
 const {durationFrames,channel,episodeId,scenes,audio,captions,brand}=props;
 const frame=useCurrentFrame();
 const {fps}=useVideoConfig();
 const kids=channel==='kids';
 if(!scenes.length)return <AbsoluteFill style={{background:'#111'}}/>;
 return <AbsoluteFill style={{background:kids?'#cce7f6':'#0b0f1b',color:'#fff'}}>
   {scenes.map((scene,index)=>{
     if(frame<scene.startFrame||frame>=scene.endFrame)return null;
     const duration=scene.endFrame-scene.startFrame;
     const opacity=interpolate(frame,[scene.startFrame,scene.startFrame+5,scene.endFrame-5,scene.endFrame],
         [1,1,1,1],clamp);
     return <AbsoluteFill key={scene.id} style={{opacity}}>
       {kids?<KidsScene id={episodeId} index={index}/>:
        scene.video?
          <OffthreadVideo src={staticFile(scene.video)} volume={0} style={{
             width:'100%',height:'100%',objectFit:'contain',
             backgroundColor:'#070c16'
          }}/>:
          <AbsoluteFill style={{background:'#111'}}/>}
       <Headline text={scene.headline} kids={kids}/>
     </AbsoluteFill>;
   })}
   <div style={{
     position:'absolute',bottom:94,right:70,color:kids?'#315f7b':'#f8fafc',
     fontFamily:'Arial,sans-serif',fontSize:32,fontWeight:700,
     opacity:kids?.8:.65
   }}>{brand}</div>
   <Captions items={captions} kids={kids}/>
   {audio&&<Audio src={staticFile(audio)}/>}
 </AbsoluteFill>;
};
