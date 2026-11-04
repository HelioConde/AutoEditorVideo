import React from 'react';
import {EmanuellyLayeredScene} from './emanuelly-layer-stage';

/**
 * Overlays 2D leves e deterministas para Fofinhos EP01.
 * Não são imagens de IA nem rigging 3D. Sem Math.random(), timers ou redes.
 * O conjunto é roteirizado por cena no Python: infância, magia e silêncio.
 * Elementos ficam predominantemente nas bordas e nunca movem o ovo/menina.
 */
export type FofinhosAmbientScenePlan = {
  index: number;
  clouds: number;
  butterflies: number;
  petals: number;
  pollen: number;
  eggSparkles: number;
  motes: number;
};

type SceneAnchor = Pick<EmanuellyLayeredScene,
  'index'|'startFrame'|'eggX'|'eggY'|'showEgg'|'night'>;

const capped = (value:number, maximum:number)=>
  Math.max(0, Math.min(maximum, Math.floor(Number(value)||0)));
const clip = (value:number, low=0, high=1)=>
  Math.max(low, Math.min(high, value));

/** A small number of simple SVG paths keeps the compositor lightweight. */
export const FofinhosAmbientEffects:React.FC<{
  scene:SceneAnchor; frame:number; plan:FofinhosAmbientScenePlan;
}>=({scene,frame,plan})=>{
  const local=Math.max(0,frame-scene.startFrame);
  // Fade out before cuts; don't let décor pop suddenly when camera changes.
  const edgeIn=clip(local/24);
  const cloudCount=scene.night?0:capped(plan.clouds,2);
  const butterflyCount=scene.night?0:capped(plan.butterflies,2);
  const petalCount=scene.night?0:capped(plan.petals,4);
  const pollenCount=scene.night?0:capped(plan.pollen,8);
  const moteCount=capped(plan.motes,6);
  const sparkleCount=scene.showEgg?capped(plan.eggSparkles,6):0;
  const eggX=clip(scene.eggX,0,1)*1080;
  const eggY=clip(scene.eggY,0,1)*1920;
  const isQuiet=scene.index>=13;
  return <svg viewBox="0 0 1080 1920"
    aria-hidden="true" focusable="false"
    style={{position:'absolute',inset:0,width:'100%',height:'100%',
      pointerEvents:'none',overflow:'hidden',opacity:edgeIn}}>
    {/* Clouds: only the opening, top-of-frame, very low opacity. */}
    {Array.from({length:cloudCount},(_,i)=>{
      const x=165+i*635+Math.sin(local/195+i*.9)*36;
      const y=318+i*80+Math.sin(local/180+i)*8;
      return <g key={'cloud-'+i} transform={'translate('+x+' '+y+')'}
        fill="#fffdf4" opacity={0.12-i*.025}>
        <ellipse cx={0} cy={15} rx={116} ry={31}/>
        <ellipse cx={-42} cy={2} rx={69} ry={35}/>
        <ellipse cx={33} cy={-9} rx={76} ry={49}/>
      </g>;
    })}
    {/* Butterflies stay at the lateral flower beds; vanish during egg discovery. */}
    {Array.from({length:butterflyCount},(_,i)=>{
      const x=(i===0?875:184)+Math.sin(local/32+i*2)*38+local*.09*(i===0?-1:1);
      const y=(i===0?1350:1170)+Math.sin(local/22+i)*43;
      const wing=.72+.28*Math.cos(local*.55+i*2);
      const tilt=Math.sin(local/29+i)*13;
      const hue=i===0?'#f0a8d8':'#ffe29d';
      const inner=i===0?'#ffe9f7':'#fff6d5';
      return <g key={'butterfly-'+i}
        transform={'translate('+x+' '+y+') rotate('+tilt+')'}
        opacity={isQuiet ? 0 : .85}>
        <g transform={'scale('+wing+' 1)'}>
          <path d="M-2 -1 C-17 -44 -47 -43 -41 -13 C-36 2 -20 11 -2 4 Z"
            fill={hue} stroke="#fff9e7" strokeWidth={2}/>
          <path d="M2 -1 C17 -44 47 -43 41 -13 C36 2 20 11 2 4 Z"
            fill={hue} stroke="#fff9e7" strokeWidth={2}/>
          <path d="M-2 3 C-20 0 -32 13 -19 24 C-9 29 -3 12 -2 5 Z"
            fill={inner}/>
          <path d="M2 3 C20 0 32 13 19 24 C9 29 3 12 2 5 Z"
            fill={inner}/>
        </g>
        <ellipse cx={0} cy={2} rx={3.8} ry={14} fill="#96765a"/>
        <path d="M-2 -8 Q-10 -19 -13 -20 M2 -8 Q10 -19 13 -20"
          stroke="#96765a" strokeWidth={1.6} fill="none"/>
      </g>;
    })}
    {/* Floating petals: sparse, outside the center/action. */}
    {Array.from({length:petalCount},(_,i)=>{
      const x=(i%2===0?180:930)+Math.sin(local/48+i*2)*47+
        Math.sin(local/130+i)*23;
      const y=980+((i*213+local*.43)%620);
      const turn=Math.sin(local/17+i)*26;
      return <ellipse key={'petal-'+i} cx={x} cy={y}
        rx={8} ry={15} fill={i%2===0?'#ffe0e8':'#fff2ae'}
        opacity={.35+(i%3)*.09}
        transform={'rotate('+turn+' '+x+' '+y+')'}/>;
    })}
    {/* Pollen: small points over the borders of the flower beds. */}
    {Array.from({length:pollenCount},(_,i)=>{
      const x=(i%2===0?130:870)+(i%3)*23+Math.sin(local/47+i)*21;
      const y=1020+(i*83)%620-Math.sin(local/38+i)*22;
      return <circle key={'pollen-'+i} cx={x} cy={y}
        r={2.4+(i%3)} fill="#fff6cd" opacity={.17+(i%3)*.055}/>;
    })}
    {/* Interior floating dust: enough atmosphere, not a fake curtain. */}
    {Array.from({length:moteCount},(_,i)=>{
      const x=155+(i*181)%760+Math.sin(local/79+i)*16;
      const y=480+(i*197)%870-Math.sin(local/86+i)*20;
      return <circle key={'mote-'+i} cx={x} cy={y}
        r={3.2+(i%2)*2} fill={scene.night?'#dce9ff':'#ffebc3'}
        opacity={scene.night ? .10 : .19}/>;
    })}
    {/* Egg-localized sparkling, not magic spread across the whole screen. */}
    {Array.from({length:sparkleCount},(_,i)=>{
      const angle=i*2.39996+local*.018;
      const radius=96+(i%3)*27+Math.sin(local/18+i)*12;
      const x=eggX+Math.cos(angle)*radius;
      const y=eggY+Math.sin(angle)*radius*.78;
      const alpha=(.15+.23*(.5+.5*Math.sin(local/12+i*1.7)))*
        (scene.night?.83:1);
      const size=5+(i%3)*2;
      return <path key={'egg-sparkle-'+i}
        d={'M'+x+' '+(y-size)+' L'+(x+size*.24)+' '+(y-size*.24)+
          ' L'+(x+size)+' '+y+' L'+(x+size*.24)+' '+(y+size*.24)+
          ' L'+x+' '+(y+size)+' L'+(x-size*.24)+' '+(y+size*.24)+
          ' L'+(x-size)+' '+y+' L'+(x-size*.24)+' '+(y-size*.24)+' Z'}
        fill={scene.night?'#ccecff':'#fff8bd'} opacity={alpha}/>;
    })}
  </svg>;
};
