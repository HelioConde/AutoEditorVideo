import React from 'react';
import {Composition} from 'remotion';
import {Short,ShortProps} from './short';
import {MasterShort,MasterProps} from './master-short';
import {PilotShort,PilotProps} from './pilot-short';

const legacy:ShortProps={
 id:'exemplo',durationFrames:90,background:'',layers:[],audio:'',captions:[],
 hook:'',title:'',effect:'chess'
};
const master:MasterProps={id:'exemplo',durationFrames:90,audio:'',scenes:[],captions:[],hook:''};
const pilot:PilotProps={episodeId:'kids-001-estrela-azul',channel:'kids',brand:'MiniMundo Curioso',durationFrames:840,audio:'',scenes:[{id:'01',startFrame:0,endFrame:840,headline:'OLÁ, ESTRELA!',visual:'',video:''}],captions:[]};

export const Root:React.FC=()=> <>
 <Composition id="ArquivoOtaku" component={Short}
   durationInFrames={90} fps={30} width={1080} height={1920} defaultProps={legacy}
   calculateMetadata={({props})=>({durationInFrames:Math.max(30,Math.min(5400,props.durationFrames||90))})}/>
 <Composition id="ArquivoOtakuMaster" component={MasterShort}
   durationInFrames={90} fps={30} width={1080} height={1920} defaultProps={master}
   calculateMetadata={({props})=>({durationInFrames:Math.max(30,Math.min(5400,props.durationFrames||90))})}/>

 <Composition id="PilotoCanaisV3" component={PilotShort}
   durationInFrames={840} fps={30} width={1080} height={1920} defaultProps={pilot}
   calculateMetadata={({props})=>({durationInFrames:Math.max(30,Math.min(1800,props.durationFrames||840))})}/>
</>;
