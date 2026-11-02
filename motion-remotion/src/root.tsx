import React from 'react';
import {Composition} from 'remotion';
import {Short,ShortProps} from './short';
import {MasterShort,MasterProps} from './master-short';

const legacy:ShortProps={
 id:'exemplo',durationFrames:90,background:'',layers:[],audio:'',captions:[],
 hook:'',title:'',effect:'chess'
};
const master:MasterProps={id:'exemplo',durationFrames:90,audio:'',scenes:[],captions:[],hook:''};

export const Root:React.FC=()=> <>
 <Composition id="ArquivoOtaku" component={Short}
   durationInFrames={90} fps={30} width={1080} height={1920} defaultProps={legacy}
   calculateMetadata={({props})=>({durationInFrames:Math.max(30,Math.min(5400,props.durationFrames||90))})}/>
 <Composition id="ArquivoOtakuMaster" component={MasterShort}
   durationInFrames={90} fps={30} width={1080} height={1920} defaultProps={master}
   calculateMetadata={({props})=>({durationInFrames:Math.max(30,Math.min(5400,props.durationFrames||90))})}/>
</>;
