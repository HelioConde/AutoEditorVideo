import React from 'react';
import {AbsoluteFill,Audio,Img,interpolate,staticFile,useCurrentFrame,useVideoConfig} from 'remotion';
import {AnimationMode,cannotMoveSeparately,motionAtFrame} from './cinematic-motion';
import {CharacterPreset,characterPoseAtFrame} from './character-idle';

export type SemanticLayer={
  id:string;role:string;z:number;src:string;
  alphaCoverage?:number;anchorX?:number;anchorY?:number;
  contactRisk?:number;heroRisk?:number;heightFraction?:number;motionSeed?:number;
  rigFrames?:{fps:number;frames:string[]}
};
export type Scene={
  id:string;subject:'personagens'|'objeto';startFrame:number;endFrame:number;
  background:string;foreground:string;renderMode?:string;layers?:SemanticLayer[];
  shotType?:string;cameraAngle?:string;focusSubject?:string;action?:string;
  transitionStyle?:'hard'|'crossfade';beatRole?:string
};
export type Caption={startFrame:number;endFrame:number;text:string;
  words?:{startFrame:number;endFrame:number;text:string}[]};
export type MasterProps={
  id:string;durationFrames:number;audio:string;scenes:Scene[];
  captions:Caption[];hook:string;animationMode?:AnimationMode;
  characterPreset?:CharacterPreset;editorialProfile?:string
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
  const normalized=Math.max(0,Math.min(1,
    (frame-scene.startFrame)/Math.max(1,scene.endFrame-scene.startFrame)));
  // If a hand/prop is attached to a character, don't displace that person
  // away from it. A tiny common camera pulse adds life without breaking Z.
  const heroPulse=hasHero&&mode==='cinematica'
    ?Math.sin(frame/fps*2*Math.PI*0.27)*
      Math.pow(Math.sin(Math.PI*normalized),2)*1.05:0;
  // Stronger purposeful camera push on the first 7 seconds. Unlike random
  // shake, this starts on frame 1 and stays within approved image margins.
  // Other shots retain the calm cinematic choreography.
  const opening=mode==='cinematica' && scene.startFrame<fps*7;
  const local=Math.max(0,Math.min(1,
    (frame-scene.startFrame)/Math.max(1,Math.min(scene.endFrame,fps*7)-scene.startFrame)));
  const openingEase=opening?1-Math.pow(1-local,2):0;
  const openingZoom=openingEase*0.045;
  const camera='translate('+(motion.panX+(opening?openingEase*8:0)).toFixed(3)+'px,'+
    (motion.panY+heroPulse+(opening?openingEase*-7:0)).toFixed(3)+
    'px) scale('+(motion.zoom+openingZoom).toFixed(5)+')';
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
            contactRisk:layer.contactRisk,heroRisk:layer.heroRisk,
            heightFraction:layer.heightFraction,motionSeed:layer.motionSeed,
            hasHeroProp:hasHero,frame,sceneStart:scene.startFrame,
            sceneEnd:scene.endFrame,fps,preset,
            enabled:mode==='cinematica',shotType:scene.shotType,
          });
          // Rigby2D exports actual skeletal poses, one RGBA frame per pose.
          // All poses retain original 1024x1536 canvas coordinates. Do not
          // stack procedural transforms on top of authored bones.
          const rig=mode==='esqueleto2d'?layer.rigFrames:undefined;
          const rigIndex=rig?.frames.length && Number.isFinite(rig.fps)
            ? Math.floor(Math.max(0,frame-scene.startFrame)*rig.fps/fps)%rig.frames.length
            : 0;
          const imageSource=rig?.frames[rigIndex]||layer.src;
          // Furniture, board and large hero masks are always STATIC in scene
          // coordinates. Never animate a chess piece independently if its
          // alpha also contains a hand/arm or another person's sleeve.
          const staticLayer=cannotMoveSeparately(layer.role);
          // Never stretch an entire painted character. Rigid-body motion
          // avoids the torso distortion seen in the original trial.
          const transform=!staticLayer && pose.enabled
            ? 'translate('+pose.translateX.toFixed(3)+'px,'+
              pose.translateY.toFixed(3)+'px) rotate('+pose.rotateDeg.toFixed(4)+
              'deg)'
            : undefined;
          return <Img key={layer.id} src={staticFile(imageSource)} style={{
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
  const hardCut=current.transitionStyle==='hard' ||
    ['hook','rehook','twist','ryuk_reveal'].includes(current.beatRole||'');
  const fade=previous && !hardCut?interpolate(frame,
    [current.startFrame,current.startFrame+5],[0,1],clamp):1;
  const caption=captions.find(c=>frame>=c.startFrame&&frame<c.endFrame);
  return <AbsoluteFill style={{background:'#080a14',fontFamily:'Arial,sans-serif'}}>
    {previous&&fade<1?<Shot scene={previous} opacity={1} mode={animationMode} preset={characterPreset}/>:null}
    <Shot scene={current} opacity={fade} mode={animationMode} preset={characterPreset}/>
    <AbsoluteFill style={{background:'linear-gradient(180deg,rgba(0,0,0,.15),transparent 20%,rgba(0,0,0,.13) 55%,rgba(0,0,0,.65) 100%)'}}/>
    {hook&&frame<fps*2.2?<div style={{position:'absolute',top:102,left:75,right:75,
      fontSize:76,lineHeight:1.08,color:'#fff',textAlign:'center',fontWeight:900,
      letterSpacing:'0.016em',
      WebkitTextStroke:'1.2px rgba(4,7,18,.95)',
      textShadow:'0 5px 18px rgba(0,0,0,.95), 0 0 15px rgba(252,78,78,.45), 0 0 3px #fff',
      filter:'drop-shadow(0 7px 8px rgba(0,0,0,.8))',
      transform:'scale('+interpolate(frame,[0,8,fps*2],[.92,1.025,1],clamp)+')',
      opacity:interpolate(frame,[0,3,fps*1.8,fps*2.2],[.85,1,1,0],clamp)}}>{hook}</div>:null}
    {caption?<div style={{position:'absolute',top:1288,left:88,right:88,
      padding:'10px 16px',borderRadius:18,
      background:'linear-gradient(90deg,transparent,rgba(3,6,17,.56) 14%,rgba(3,6,17,.56) 86%,transparent)',
      fontSize:65,lineHeight:1.15,fontWeight:900,textAlign:'center',color:'#fff',
      WebkitTextStroke:'1px rgba(2,4,15,.85)',
      textShadow:'0 4px 9px #000,0 0 13px rgba(240,240,255,.24)'}}>
      {caption.words?.length
        ? caption.words.map((word,index)=>{
          const active=frame>=word.startFrame && frame<word.endFrame;
          return <React.Fragment key={index}>
            {index>0?' ':null}
            <span style={{
              color:active?'#ffd166':'#fff',
              textShadow:active?'0 0 16px rgba(255,195,75,.6),0 4px 8px #000':undefined,
            }}>{word.text}</span>
          </React.Fragment>;
        }):caption.text}
    </div>:null}
    {audio?<Audio src={staticFile(audio)}/>:null}
  </AbsoluteFill>;
};
