import React from 'react';
import {Composition} from 'remotion';
import {Short,ShortProps} from './short';
import {MasterShort,MasterProps} from './master-short';
import {PilotShort,PilotProps} from './pilot-short';
import {EmanuellyShort,EmanuellyProps} from './emanuelly-short';
import {AlchemyDoramaShort,AlchemyDoramaProps} from './alchemy-dorama-short';
import {AlchemyDoramaMaster10s,AlchemyMaster10Props} from './alchemy-dorama-master-10s';

const legacy:ShortProps={
 id:'exemplo',durationFrames:90,background:'',layers:[],audio:'',captions:[],
 hook:'',title:'',effect:'chess'
};
const master:MasterProps={id:'exemplo',durationFrames:90,audio:'',scenes:[],captions:[],hook:''};
const pilot:PilotProps={episodeId:'kids-001-estrela-azul',channel:'kids',brand:'MiniMundo Curioso',durationFrames:840,audio:'',scenes:[{id:'01',startFrame:0,endFrame:840,headline:'OLÁ, ESTRELA!',visual:'',video:''}],captions:[]};
const emanu:EmanuellyProps={episodeId:'kids-emanuelly-ep01-p01-ovo-azul',title:'O Ovo Azul',brand:'Emanuelly e seus Amigos de Pelúcia',chapter:'EP 1 · PARTE 1/4',durationFrames:900,frames:[],captions:[],audio:'',referenceSha:'',madeForKids:true};

const alchemyDorama:AlchemyDoramaProps={
  episodeId:'alchemy-114-conquiste-princesa-ep01',title:'O Fracassado Condenado',
  durationFrames:5250,scenes:[],captions:[],audio:''
};

const alchemyMaster10:AlchemyMaster10Props={
  pilotId:'alchemy-dorama-master-layer-10s-v1',durationFrames:300,
  master:'',background:'',ren:'',king:'',elara:'',sword:'',audio:'',
  frameReferenceSha:'',noNarration:true,noYouTubeUpload:true
};

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
 <Composition id="AlchemyDoramaOriginal" component={AlchemyDoramaShort}
   durationInFrames={5250} fps={30} width={1080} height={1920}
   defaultProps={alchemyDorama}
   calculateMetadata={({props})=>({durationInFrames:Math.max(4500,Math.min(5400,props.durationFrames||5250))})}/>
 <Composition id="AlchemyDoramaMaster10s" component={AlchemyDoramaMaster10s}
   durationInFrames={300} fps={30} width={1080} height={1920}
   defaultProps={alchemyMaster10}
   calculateMetadata={({props})=>({durationInFrames:300})}/>
</>;
