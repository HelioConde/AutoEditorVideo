import React from 'react';
import {AbsoluteFill,Audio,Img,Sequence,interpolate,staticFile,useCurrentFrame,useVideoConfig} from 'remotion';
import {AnimationMode,cannotMoveSeparately,motionAtFrame,openingCutAtFrame,longHoldCutAtFrame} from './cinematic-motion';
import {CharacterPreset,characterPoseAtFrame} from './character-idle';
import {RigPlayback,poseFrameIndex} from './pose-timeline';
import {meshFrameIndex} from './pose-timeline';

export type SemanticLayer={
  id:string;role:string;z:number;src:string;
  alphaCoverage?:number;anchorX?:number;anchorY?:number;
  contactRisk?:number;heroRisk?:number;heightFraction?:number;motionSeed?:number;
  rigFrames?:{fps:number;frames:string[];playback?:RigPlayback}
  // Baked frames from a continuous mesh deformation of ONE original RGBA.
  // No opacity crossfades between distinct characters.
  meshFrames?:{fps:number;frames:string[]}
};
export type Scene={
  id:string;subject:'personagens'|'objeto';startFrame:number;endFrame:number;
  background:string;foreground:string;renderMode?:string;layers?:SemanticLayer[];
  shotType?:string;cameraAngle?:string;focusSubject?:string;action?:string;
  transitionStyle?:'hard'|'crossfade';beatRole?:string;headline?:string
};
export type Caption={startFrame:number;endFrame:number;text:string;
  words?:{startFrame:number;endFrame:number;text:string}[]};
export type SoundCue={src:string;startFrame:number;endFrame:number;volume:number};
export type BackgroundMusic={src:string;volume:number};
export type MasterProps={
  id:string;durationFrames:number;audio:string;scenes:Scene[];
  captions:Caption[];hook:string;animationMode?:AnimationMode;
  characterPreset?:CharacterPreset;editorialProfile?:string;
  visualProfile?:'original'|'gamer-alchemy-reference'|'otaku-v6-vertical';
  soundCues?:SoundCue[];backgroundMusic?:BackgroundMusic;
};
const clamp={extrapolateLeft:'clamp' as const,extrapolateRight:'clamp' as const};

const Shot:React.FC<{scene:Scene;opacity:number;mode:AnimationMode;preset:CharacterPreset;profile?:MasterProps['visualProfile']}>=({scene,opacity,mode,preset,profile})=>{
  const v6=profile==='otaku-v6-vertical';
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
  // Smooth centered zoom only: no internal camera jump cuts or large pans.
  // Safe separated RGBA characters can visibly idle without camera competition.
  const opener=openingCutAtFrame(frame,fps,mode);
  const hold=longHoldCutAtFrame(frame,scene.startFrame,scene.endFrame,fps,mode);
  const safeZoom=Math.min(1.115,motion.zoom+opener.zoom+hold.zoom);
  const camera='translate('+(motion.panX+opener.panX+hold.panX).toFixed(3)+'px,'+
    (motion.panY+heroPulse+opener.panY+hold.panY).toFixed(3)+
    'px) scale('+safeZoom.toFixed(5)+')';
  const ordered=(scene.layers||[]).slice().sort((a,b)=>a.z-b.z);
  return <AbsoluteFill style={{opacity,background:'#070912',overflow:'hidden'}}>
    <Img src={urlbg} style={{position:'absolute',inset:0,width:'100%',height:'100%',
      objectFit:'cover',filter:'blur(60px) brightness(.34)',transform:'scale(1.25)'}}/>
    <div style={{position:'absolute',left:v6?0:70,top:v6?0:245,
      width:v6?1080:940,height:v6?1920:1410,
      transform:camera,transformOrigin:'center center',overflow:'hidden'}}>
      <Img src={urlbg} style={{position:'absolute',inset:0,width:'100%',height:'100%',
        objectFit:v6?'cover':'contain'}}/>
      {(scene.renderMode==='multilayer'||scene.renderMode==='mesh2d') && ordered.length
        ? ordered.map(layer=>{
          // V7: every frame comes from one and the same RGBA illustration.
          // One layer at a time avoids the duplicate/ghost artifacts of V6.
          const mesh=mode==='malha2d'?layer.meshFrames:mode==='pins2d'?layer.meshFrames:mode==='brush2d'?layer.meshFrames:undefined;
          if(mesh?.frames.length){
            const index=meshFrameIndex({
              frame,sceneStart:scene.startFrame,
              compositionFps:fps,meshFps:mesh.fps,
              frameCount:mesh.frames.length
            });
            return <Img key={layer.id} src={staticFile(mesh.frames[index])}
              style={{position:'absolute',inset:0,width:'100%',height:'100%',
                objectFit:v6?'cover':'contain',zIndex:layer.z}}/>;
          }
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
          // Prefer a reversible authored gesture over jumping from the
          // last painted pose directly back to the first.
          const rigIndex=rig?.frames.length
            ? poseFrameIndex({frame,sceneStart:scene.startFrame,
                compositionFps:fps,rigFps:rig.fps,
                frameCount:rig.frames.length,playback:rig.playback})
            : 0;
          const imageSource=rig?.frames[rigIndex]||layer.src;
          // V6 soft morphs between REAL authored RGBA poses; never
          // represent a pan or still-image zoom as character animation.
          const rawProgress=rig?.frames.length
            ? Math.max(0,(frame-scene.startFrame)*rig.fps/fps):0;
          const rigStep=Math.floor(rawProgress);
          const blendLinear=rawProgress-rigStep;
          const rigBlend=blendLinear*blendLinear*(3-2*blendLinear);
          const nextIndex=rig?.frames.length
            ? poseFrameIndex({frame:scene.startFrame+
                (rigStep+1)*fps/rig.fps,sceneStart:scene.startFrame,
                compositionFps:fps,rigFps:rig.fps,
                frameCount:rig.frames.length,playback:rig.playback})
            : rigIndex;
          const nextSource=rig?.frames[nextIndex]||imageSource;
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
          const poseStyle:React.CSSProperties={
            position:'absolute',inset:0,width:'100%',height:'100%',
            objectFit:v6?'cover':'contain',zIndex:layer.z,
            transform,
            transformOrigin:(layer.anchorX ?? 50)+'% '+(layer.anchorY ?? 80)+'%',
          };
          if(v6 && rig && rig.frames.length>=2 && nextIndex!==rigIndex){
            return <React.Fragment key={layer.id}>
              <Img src={staticFile(imageSource)} style={{...poseStyle,opacity:1-rigBlend}}/>
              <Img src={staticFile(nextSource)} style={{...poseStyle,opacity:rigBlend}}/>
            </React.Fragment>;
          }
          return <Img key={layer.id} src={staticFile(imageSource)} style={poseStyle}/>;
        })
        : <Img src={urlfg} style={{position:'absolute',inset:0,width:'100%',height:'100%',
          objectFit:v6?'cover':'contain'}}/>}
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
  characterPreset='equilibrado',visualProfile='original',
  soundCues=[],backgroundMusic
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
    [current.startFrame,current.startFrame+10],[0,1],clamp):1;
  const caption=captions.find(c=>frame>=c.startFrame&&frame<c.endFrame);
  return <AbsoluteFill style={{background:'#080a14',fontFamily:'Arial,sans-serif'}}>
    {previous&&fade<1?<Shot scene={previous} opacity={1} mode={animationMode} preset={characterPreset} profile={visualProfile}/>:null}
    <Shot scene={current} opacity={fade} mode={animationMode} preset={characterPreset} profile={visualProfile}/>
    <AbsoluteFill style={{background:'linear-gradient(180deg,rgba(0,0,0,.15),transparent 20%,rgba(0,0,0,.13) 55%,rgba(0,0,0,.65) 100%)'}}/>
    {visualProfile==='gamer-alchemy-reference' && hook
      ? <div style={{
        position:'absolute',top:73,left:66,right:66,
        fontSize:77,lineHeight:1.01,color:'#fff',textAlign:'center',
        fontFamily:'Arial,DejaVu Sans,sans-serif',fontWeight:900,
        letterSpacing:'0.018em',whiteSpace:'pre-line',
        WebkitTextStroke:'1px rgba(0,0,0,.85)',
        textShadow:'0 5px 10px #000,0 1px 3px #000'
      }}>{hook}</div>
      : hook && frame<fps*2.2
        ? <div style={{position:'absolute',top:visualProfile==='otaku-v6-vertical'?205:102,
          left:visualProfile==='otaku-v6-vertical'?112:75,
          right:visualProfile==='otaku-v6-vertical'?112:75,
          fontSize:visualProfile==='otaku-v6-vertical'?68:76,
          lineHeight:1.08,color:'#fff',textAlign:'center',fontWeight:900,
          letterSpacing:'0.016em',
          WebkitTextStroke:'1.2px rgba(4,7,18,.95)',
          textShadow:'0 5px 18px rgba(0,0,0,.95), 0 0 15px rgba(252,78,78,.45), 0 0 3px #fff',
          filter:'drop-shadow(0 7px 8px rgba(0,0,0,.8))',
          transform:'scale('+interpolate(frame,[0,8,fps*2],[.92,1.025,1],clamp)+')',
          opacity:interpolate(frame,[0,3,fps*1.8,fps*2.2],[.85,1,1,0],clamp)}}>{hook}</div>
        :null}
    {current.headline && frame-current.startFrame<fps*1.65 &&
      ['rehook','answer','rule_confirm','cta'].includes(current.beatRole||'')
      ? <div style={{position:'absolute',top:200,left:98,right:98,
        padding:'22px 30px',borderRadius:22,
        border:'2px solid rgba(255,113,139,.55)',
        background:'linear-gradient(100deg,rgba(11,8,31,.93),rgba(72,10,40,.85))',
        boxShadow:'0 16px 36px rgba(0,0,0,.5),0 0 32px rgba(240,45,83,.18)',
        textAlign:'center',fontWeight:900,fontSize:55,lineHeight:1.07,
        letterSpacing:'0.04em',color:'#fff',
        textShadow:'0 3px 8px #000,0 0 12px rgba(255,180,180,.35)',
        opacity:interpolate(frame-current.startFrame,[0,5,fps*1.38,fps*1.65],[0,1,1,0],clamp),
        transform:'translateY('+interpolate(frame-current.startFrame,[0,8],[22,0],clamp)+'px)',
      }}>{current.headline}</div>:null}
    {caption?<div style={visualProfile==='gamer-alchemy-reference'
      ? {position:'absolute',top:1272,left:94,right:94,
        padding:'19px 28px',borderRadius:17,
        background:'rgba(6,10,19,.9)',
        border:'2px solid rgba(225,235,255,.15)',
        boxShadow:'0 10px 28px rgba(0,0,0,.65)',
        fontSize:67,lineHeight:1.16,fontWeight:900,textAlign:'center',color:'#fff',
        fontFamily:'Arial,DejaVu Sans,sans-serif',
        WebkitTextStroke:'1px rgba(1,3,9,.85)',
        textShadow:'0 3px 8px #000'}
      : {position:'absolute',top:visualProfile==='otaku-v6-vertical'?1360:1258,
        left:visualProfile==='otaku-v6-vertical'?116:78,
        right:visualProfile==='otaku-v6-vertical'?116:78,
        padding:visualProfile==='otaku-v6-vertical'?'16px 22px':'18px 25px',borderRadius:22,
        background:'rgba(2,5,15,.85)',
        border:'2px solid rgba(255,255,255,.18)',
        boxShadow:'0 12px 32px rgba(0,0,0,.68)',
        fontSize:visualProfile==='otaku-v6-vertical'?65:79,
        lineHeight:1.12,fontWeight:900,textAlign:'center',color:'#fff',
        WebkitTextStroke:'2px rgba(1,3,9,.96)',
        textShadow:'0 5px 13px #000,0 0 15px rgba(240,240,255,.2)'}}>
      {caption.words?.length
        ? caption.words.map((word,index)=>{
          const active=frame>=word.startFrame && frame<word.endFrame;
          return <React.Fragment key={index}>
            {index>0?' ':null}
            <span style={{
              color:active?'#ffd166':'#fff',
              textShadow:active?'0 0 9px rgba(255,197,76,.45),0 3px 6px #000':undefined,
            }}>{word.text}</span>
          </React.Fragment>;
        }):caption.text}
    </div>:null}
    {backgroundMusic?.src?<Audio src={staticFile(backgroundMusic.src)}
      volume={Math.min(.20,Math.max(0,backgroundMusic.volume))}/>:null}
    {soundCues.filter(c=>c.startFrame>=0 && c.endFrame>c.startFrame &&
      c.startFrame<Number.MAX_SAFE_INTEGER).map((cue,i)=>
      <Sequence key={i} from={cue.startFrame}
        durationInFrames={cue.endFrame-cue.startFrame}>
        <Audio src={staticFile(cue.src)}
          volume={Math.min(.40,Math.max(0,cue.volume))}/>
      </Sequence>
    )}
    {audio?<Audio src={staticFile(audio)}/>:null}
  </AbsoluteFill>;
};
