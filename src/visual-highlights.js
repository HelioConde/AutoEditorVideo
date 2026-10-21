import { normalizedSignals, candidateSignalEvidence, motionBurstMoments } from './highlight-signals.js';
import { rankShortsFromTranscript } from './shorts-ranking.js';

/**
 * Motion-only fallback for silent clips. YDIF measures inter-frame difference,
 * not scene meaning. Reject static sources; never synthesize subtitles.
 */
export function rankVisualShorts(signals,{duration,maxClips=3,profile='gameplay'}={}) {
  const d=Number(duration);
  if(!Number.isFinite(d)||d<8||d>600)
    return {error:'A análise visual aceita vídeos de 8 segundos a 10 minutos.',candidates:[]};
  if(!Number.isInteger(maxClips)||maxClips<1||maxClips>3)
    return {error:'Escolha de 1 a 3 Shorts.',candidates:[]};
  if(!['gameplay','podcast','tutorial'].includes(profile))
    return {error:'Perfil de análise inválido.',candidates:[]};
  const {motion,scenes}=normalizedSignals(signals);
  if(motion.length<8)
    return {error:'Não há quadros analisados suficientes para sugerir momentos sem fala.',candidates:[]};

  const target=Math.min(d,profile==='gameplay'?12:profile==='tutorial'?16:18);
  const bursts=motionBurstMoments(signals);
  const starts=new Set([0,Math.max(0,Math.round((d-target)*100)/100)]);
  for(let n=3;n<d-target;n+=3)starts.add(n);
  // Make a candidate with contextual lead-in around each sustained motion
  // change; the previous fixed 3-second grid sometimes clipped the event.
  for(const event of bursts) {
    const start=Math.max(0,Math.min(d-target,event.time-target*.4));
    starts.add(Math.round(start*100)/100);
  }
  const options=[];
  for(const start of [...starts].sort((a,b)=>a-b)){
    const end=Math.min(d,start+target);
    const samples=motion.filter(x=>x.time>=start&&x.time<end);
    // Do not claim a highlight from a couple of isolated frames.
    if(samples.length<Math.max(8,(end-start)*.75))continue;
    const mean=samples.reduce((acc,x)=>acc+x.value,0)/samples.length;
    const active=samples.filter(x=>x.value>=2).length/samples.length;
    const events=bursts.filter(x=>x.time>=start&&x.time<end);
    // A quiet clip with a brief but sustained action may be interesting even
    // if average movement is low. Single-frame flashes are not events.
    if((mean<1.5||active<.3)&&!events.length)continue;
    const evidence=candidateSignalEvidence(signals,start,end,profile);
    const sceneCount=scenes.filter(x=>x>=start&&x<end).length;
    const score=Math.min(95,Math.round(14+Math.min(28,mean*2.3)+active*16+
      Math.min(12,sceneCount*4)+Math.min(15,evidence.highEnergy*5)+
      Math.min(15,events.length*5)));
    const startTime=Math.round(start*100)/100,endTime=Math.round(end*100)/100;
    options.push({
      start:startTime,end:endTime,duration:Math.round((end-start)*100)/100,
      title:'Trecho visual '+format(startTime)+'–'+format(endTime),
      score,reason:'Movimento visual'+(events.length?' · Picos de movimento sustentados':' contínuo')+
        (sceneCount?' · Mudanças de cena':''),
      transcript:'Sem fala transcrita. Analise a prévia antes de exportar.',
      captionsAvailable:false,
      evidence:{text:0,audioPeaks:evidence.highEnergy,sceneChanges:Math.min(3,sceneCount),
        motionActivity:Math.round(mean*100)/100,motionBursts:events.length,signalBonus:score,
        source:'movimento de imagem (sem transcrição)'}
    });
  }
  options.sort((a,b)=>b.score-a.score||a.start-b.start);
  const candidates=[];
  for(const option of options){
    if(candidates.some(x=>option.start<x.end+1&&option.end>x.start-1))continue;
    candidates.push({...option,rank:candidates.length+1});
    if(candidates.length>=maxClips)break;
  }
  if(!candidates.length)return {error:'O vídeo não apresentou movimento contínuo suficiente. Use cortes manuais ou uma transcrição.',candidates:[]};
  return {error:null,candidates};
}
function format(s){
  const n=Math.floor(s);
  return String(Math.floor(n/60)).padStart(2,'0')+':'+String(n%60).padStart(2,'0');
}
export function rankAutomaticShorts(subtitles,options={}) {
  return Array.isArray(subtitles)&&subtitles.length
    ? rankShortsFromTranscript(subtitles,options)
    : rankVisualShorts(options.signals,options);
}
