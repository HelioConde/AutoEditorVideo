/** CI-only synthetic visual fixture. No child photos, official art, music or credentials. */
import React from 'react';
import {AbsoluteFill, Composition, interpolate, registerRoot, useCurrentFrame} from 'remotion';

const CloudFixture: React.FC = () => {
  const frame=useCurrentFrame();
  const eggX=interpolate(frame,[0,34],[195,244],{extrapolateRight:'clamp'});
  const eggY=interpolate(frame,[0,17,34],[520,500,520],{extrapolateRight:'clamp'});
  const spark=interpolate(frame,[0,10,20,34],[0.25,1,0.4,0.85],{extrapolateRight:'clamp'});
  const sunX=interpolate(frame,[0,34],[90,145],{extrapolateRight:'clamp'});
  return <AbsoluteFill style={{background:'linear-gradient(180deg, #9ae0ff 0%, #d9f5ff 58%, #abdd94 59%, #429a65 100%)'}}>
    <div style={{position:'absolute',top:85,left:sunX,width:100,height:100,borderRadius:'50%',background:'#fff6b5',boxShadow:'0 0 50px #fff6b5'}} />
    <div style={{position:'absolute',top:135,left:260,width:145,height:35,borderRadius:50,background:'rgba(255,255,255,.82)'}} />
    <div style={{position:'absolute',top:200,left:50,width:190,height:45,borderRadius:60,background:'rgba(255,255,255,.72)'}} />
    <div style={{position:'absolute',top:550,left:0,width:480,height:90,borderRadius:'45% 45% 0 0',background:'#66b46e'}} />
    <div style={{position:'absolute',top:eggY,left:eggX,width:92,height:125,borderRadius:'48% 48% 46% 46% / 62% 62% 35% 35%',background:'linear-gradient(100deg,#80d5ff,#3883db)',boxShadow:'12px 14px 5px rgba(33,68,38,.22)'}} />
    <div style={{position:'absolute',top:eggY+34,left:eggX+65,width:12,height:24,borderRadius:10,background:'rgba(255,255,255,.6)'}} />
    <div style={{position:'absolute',top:460,left:300,fontSize:50,color:'#fffde6',opacity:spark}}>✦</div>
    <div style={{position:'absolute',top:685,left:25,right:25,fontSize:32,fontWeight:800,textAlign:'center',color:'#245342',fontFamily:'sans-serif'}}>FOFINHOS · TESTE DE NUVEM</div>
    <div style={{position:'absolute',top:760,left:25,right:25,fontSize:20,textAlign:'center',color:'#245342',fontFamily:'sans-serif'}}>Cenário sintético · Sem recursos privados</div>
  </AbsoluteFill>;
};
const TestRoot:React.FC=()=> <Composition
  id="FofinhosCloudSmoke"
  component={CloudFixture}
  durationInFrames={36} fps={24} width={480} height={854}
/>;
registerRoot(TestRoot);
