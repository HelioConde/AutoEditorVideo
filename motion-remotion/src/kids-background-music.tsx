import React from 'react';
import {Audio, staticFile} from 'remotion';

/** The narration stays dominant. Keep the children's response pauses quiet.
 * Both tracks are user-provided, and rights require checking before upload.
 */
export type KidsMusic = {
 audio:string; source_name:string; sha256:string;
 volume:number; fade_seconds:number; rights_review:string;
};

export const KidsBackgroundMusic:React.FC<{
  music?:KidsMusic;
  durationFrames:number;
}>=({music,durationFrames})=>{
  if(!music?.audio)return null;
  // These volumes are rendering defaults, not objective loudness QA.
  const safeVolume=Math.min(0.12,Math.max(0,Number(music.volume)||0));
  const fadeFrames=Math.max(1,Math.round(Math.min(3, Math.max(.5,music.fade_seconds))*30));
  return <Audio src={staticFile(music.audio)} loop volume={(frame:number)=>{
    const fadeIn=Math.min(1,Math.max(0,frame/fadeFrames));
    const fadeOut=Math.min(1,Math.max(0,(durationFrames-frame-1)/fadeFrames));
    return safeVolume*Math.min(fadeIn,fadeOut);
  }}/>;
};
