import React from 'react';
import {Composition} from 'remotion';
import {Short,ShortProps} from './short';
import {MasterShort,MasterProps} from './master-short';
import {PilotShort,PilotProps} from './pilot-short';
import {EmanuellyShort,EmanuellyProps} from './emanuelly-short';

const legacy:ShortProps={
 id:'exemplo',durationFrames:90,background:'',layers:[],audio:'',captions:[],
 hook:'',title:'',effect:'chess'
};
const master:MasterProps={id:'exemplo',durationFrames:90,audio:'',scenes:[],captions:[],hook:''};
const pilot:PilotProps={episodeId:'kids-001-estrela-azul',channel:'kids',brand:'MiniMundo Curioso',durationFrames:840,audio:'',scenes:[{id:'01',startFrame:0,endFrame:840,headline:'OLÁ, ESTRELA!',visual:'',video:''}],captions:[]};
const emanu:EmanuellyProps={episodeId:'kids-emanuelly-ep01-p01-ovo-azul',title:'O Ovo Azul',brand:'Emanuelly e seus Amigos de Pelúcia',chapter:'EP 1 · PARTE 1/4',durationFrames:900,frames:[],captions:[],audio:'',referenceSha:'',madeForKids:true};

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
 <Composition id="EmanuellySerieV1" component={EmanuellyShort}
   durationInFrames={900} fps={30} width={1080} height={1920} defaultProps={emanu}
   calculateMetadata={({props})=>({durationInFrames:Math.max(30,Math.min(1800,props.durationFrames||900))})}/>
 <Composition id="FofinhosEP01Canonico" component={EmanuellyShort}
   durationInFrames={1800} fps={30} width={1080} height={1920} defaultProps={{...emanu,
    episodeId:'fofinhos-ep01-parte01-canonico',brand:'Fofinhos',chapter:'EP 01 · O OVO AZUL'}}
   calculateMetadata={({props})=>({durationInFrames:Math.max(30,Math.min(18000,props.durationFrames||1800))})}/>
</>;
