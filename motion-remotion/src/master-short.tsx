import React from 'react';
import {AbsoluteFill,Audio,Img,interpolate,staticFile,useCurrentFrame,useVideoConfig} from 'remotion';
import {AnimationMode,cannotMoveSeparately,motionAtFrame} from './cinematic-motion';
import {CharacterPreset,characterPoseAtFrame} from './character-idle';

export type SemanticLayer={
  id:string;role:string;z:number;src:string;
  alphaCoverage?:number;anchorX?:number;anchorY?:number
};
export type Scene={
  id:string;subject:'personagens'|'objeto';startFrame:number;endFrame:number;
  background:string;foreground:string;renderMode?:string;layers?:SemanticLayer[];
  shotType?:string;cameraAngle?:string;focusSubject?:string;action?:string
};
export type Caption={startFrame:number;endFrame:number;text:string};
export type MasterProps={
  id:string;durationFrames:number;audio:string;scenes:Scene[];
  captions:Caption[];hook:string;animationMode?:AnimationMode;
  characterPreset?:CharacterPreset
};
const clamp={extrapolateLeft:'clamp' as const,extrapolateRight:'clamp' as const};

const Shot:React.FC<{scene:Scene;opacity:number;mode:AnimationMode;preset:CharacterPreset}>=({scene,opacity,mode,preset})=>{
  const frame=useCurrentFrame();
  const {fps}=useVideoConfig();
  const motion=motionAtFrame(frame,scene.startFrame,scene.endFrame,
                            scene.shotType,scene.id,mode);
  const hasHero=Boolean(scene.layers?.some(l=>l.role==='hero_prop'));
  const urlbg=staticFile(scene.background);
  const urlfg=staticFile(scene.foreground);
  // Image master has the 2:3 ratio. Never fill/cover the portrait: it would
  // crop heads or board. The WHOLE content, including the table, moves under
  // one fixed camera. This avoids character/prop penetration.
  const camera='translate('+motion.panX.toFixed(3)+'px,'+
    motion.panY.toFixed(3)+'px) scale('+motion.zoom.toFixed(5)+')';
  const ordered=(scene.layers||[]).slice().sort((a,b)=>a.z-b.z);
  return <AbsoluteFill style={{opacity,background:'#070912',overflow:'hidden'}}>
    <Img src={urlbg} style={{position:'absolute',inset:0,width:'100%',height:'100%',
      objectFit:'cover',filter:'blur(60px) brightness(.34)',transform:'scale(1.25)'}}/>
    <div style={{position:'absolute',left:70,top:245,width:940,height:1410,
      transform:camera,transformOrigin:'center center',overflow:'hidden'}}>
      <Img src={urlbg} style={{position:'absolute',inset:0,width:'100%',height:'100%',
        objectFit:'contain'}}/>
      {scene.renderMode==='multilayer' && ordered.length
        ? ordered.map(layer=>{
          const pose=characterPoseAtFrame({
            role:layer.role,id:layer.id,coverage:layer.alphaCoverage ?? NaN,
            hasHeroProp:hasHero,frame,sceneStart:scene.startFrame,
            sceneEnd:scene.endFrame,fps,preset,
            enabled:mode==='cinematica',shotType:scene.shotType,
          });
          // Furniture, board and large hero masks are always STATIC in scene
          // coordinates. Never animate a chess piece independently if its
          // alpha also contains a hand/arm or another person's sleeve.
          const staticLayer=cannotMoveSeparately(layer.role);
          const transform=!staticLayer && pose.enabled
            ? 'translate('+pose.translateX.toFixed(3)+'px,'+
              pose.translateY.toFixed(3)+'px) rotate('+pose.rotateDeg.toFixed(4)+
              'deg) scale('+pose.scaleX.toFixed(6)+','+
              pose.scaleY.toFixed(6)+')'
            : undefined;
          return <Img key={layer.id} src={staticFile(layer.src)} style={{
            position:'absolute',inset:0,width:'100%',height:'100%',
            objectFit:'contain',zIndex:layer.z,
            transform,
            transformOrigin:(layer.anchorX ?? 50)+'% '+(layer.anchorY ?? 80)+'%',
          }}/>;
        })
        : <Img src={urlfg} style={{position:'absolute',inset:0,width:'100%',height:'100%',
          objectFit:'contain'}}/>}
      {mode==='cinematica'?<>
        {/* In-scene colored bounce light, always tiny and slowly varying.
            No flashes, jitter, or fabricated movement of faces/pieces. */}
        <div style={{position:'absolute',inset:0,zIndex:100,pointerEvents:'none',
          background:'linear-gradient(122deg, rgba(16,81,196,.45) 0%, transparent 48%, rgba(224,26,36,.37) 100%)',
          mixBlendMode:'screen',opacity:motion.fill}}/>
        {motion.focus>0?<div style={{position:'absolute',inset:0,zIndex:101,
          pointerEvents:'none',background:
            'radial-gradient(ellipse at 50% 68%,rgba(242,215,156,.16),transparent 42%)',
          mixBlendMode:'screen',opacity:motion.focus}}/>:null}
      </>:null}
    </div>
  </AbsoluteFill>;
};

export const MasterShort:React.FC<MasterProps>=({
  scenes,audio,captions,hook,animationMode='cinematica',
  characterPreset='equilibrado'
})=>{
  const frame=useCurrentFrame();
  const {fps}=useVideoConfig();
  if(!scenes.length)return <AbsoluteFill style={{background:'#080a14'}}/>;
  let idx=scenes.findIndex(s=>frame>=s.startFrame&&frame<s.endFrame);
  if(idx<0)idx=frame<scenes[0].startFrame?0:scenes.length-1;
  const current=scenes[idx];
  const previous=idx>0?scenes[idx-1]:null;
  const fade=previous?interpolate(frame,
    [current.startFrame,current.startFrame+7],[0,1],clamp):1;
  const caption=captions.find(c=>frame>=c.startFrame&&frame<c.endFrame);
  return <AbsoluteFill style={{background:'#080a14',fontFamily:'Arial,sans-serif'}}>
    {previous&&fade<1?<Shot scene={previous} opacity={1} mode={animationMode} preset={characterPreset}/>:null}
    <Shot scene={current} opacity={fade} mode={animationMode} preset={characterPreset}/>
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
