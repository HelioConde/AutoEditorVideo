import React from 'react';
import {Composition} from 'remotion';
import {Short, ShortProps} from './short';
const initial: ShortProps={
  id:'exemplo', durationFrames:90, background:'', layers:[], audio:'', captions:[],
  hook:'', title:'', effect:'chess'
};
export const Root:React.FC=()=> <Composition id="ArquivoOtaku" component={Short}
  durationInFrames={90} fps={30} width={1080} height={1920} defaultProps={initial}
  calculateMetadata={({props})=>({durationInFrames:Math.max(30,Math.min(5400,props.durationFrames||90))})}/>;
