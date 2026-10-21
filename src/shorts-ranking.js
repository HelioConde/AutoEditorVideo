import { validateSubtitles } from './subtitles.js';
import { candidateSignalEvidence } from './highlight-signals.js';
import { narrativeQuality, refineShortBoundaries } from './shorts-boundaries.js';

const MAX_SHORTS=3;
const MAX_LEN=45;
const MIN_LEN=8;
const TERMS=[
  {pattern:/\b(por que|porque|como|qual|quando|quem|será que|e se)\b/iu,weight:11,label:'Pergunta que cria curiosidade'},
  {pattern:/\b(mas|porém|só que|entretanto|apesar|na verdade)\b/iu,weight:9,label:'Contraste ou mudança de ideia'},
  {pattern:/\b(incrível|surpresa|segredo|nunca|ninguém|maior|melhor|pior|impossível|absurdo|finalmente)\b/iu,weight:8,label:'Expressão de destaque'},
  {pattern:/\b(descobri|aprendi|resultado|aconteceu|consegui|errei|ganhei|perdi|mudou|venci|conclusão)\b/iu,weight:8,label:'Resultado ou descoberta'},
  {pattern:/[!?]/u,weight:5,label:'Entonação marcada no texto'},
];
const round=n=>Math.round(n*100)/100;
const wordCount=s=>(s.trim().match(/[\p{L}\p{N}]+/gu)||[]).length;

export function rankShortsFromTranscript(subtitles,{duration,maxClips=MAX_SHORTS,signals=null,profile='podcast'}={}) {
  const checked=validateSubtitles(subtitles);
  if(checked.error)return {error:checked.error,candidates:[]};
  const endOfMedia=Number(duration);
  if(!Number.isFinite(endOfMedia)||endOfMedia<=0||endOfMedia>3600)
    return {error:'Duração da mídia inválida.',candidates:[]};
  if(!Number.isInteger(maxClips)||maxClips<1||maxClips>MAX_SHORTS)
    return {error:'Escolha de 1 a 3 Shorts.',candidates:[]};
  if(!['podcast','gameplay','tutorial'].includes(profile))
    return {error:'Perfil de análise inválido.',candidates:[]};
  const cues=checked.subtitles.filter(c=>c.start<endOfMedia && c.end<=endOfMedia+.15);
  if(!cues.length)return {error:'Transcreva ou importe legendas SRT antes de buscar destaques.',candidates:[]};

  const suggestions=[];
  for(let i=0;i<cues.length;i++){
    for(let j=i;j<cues.length;j++){
      if(j>i && cues[j].start-cues[j-1].end>3)break;
      const length=cues[j].end-cues[i].start;
      if(length>MAX_LEN)break;
      if(length<MIN_LEN)continue;
      const selected=cues.slice(i,j+1);
      const script=selected.map(x=>x.text).join(' ').replace(/\s+/gu,' ').trim();
      const words=wordCount(script);
      if(words<12)continue;
      const reasons=TERMS.filter(t=>t.pattern.test(script));
      const density=words/length;
      const idealLength=26;
      const focus=Math.max(0,19-Math.abs(length-idealLength)*.75);
      const speech=Math.min(23,words*.34);
      const fluency=Math.max(0,15-Math.abs(density-2.4)*6);
      const intro=/^[A-ZÁÉÍÓÚÂÊÔÃÕ][^.!?]{3,}/u.test(selected[0].text.trim())?2:0;
      const ending=/[.!?]\s*$/u.test(selected.at(-1).text)?7:0;
      const hook=reasons.reduce((sum,x)=>sum+x.weight,0);
      const audioVisual=candidateSignalEvidence(signals,cues[i].start,cues[j].end,profile);
      const textScore=Math.round(16+focus+speech+fluency+intro+ending+hook);
      const narrative=narrativeQuality(cues[i].text,cues[j].text);
      const contextualAdjustment=Array.isArray(signals?.silences)?narrative.adjustment:0;
      // Leave reserved headroom for actual audio/visual evidence so strong
      // transcripts do not all saturate at 99 and obscure meaningful signals.
      const score=audioVisual.available ?
        Math.max(0,Math.min(99,Math.min(86,textScore)+Math.min(13,audioVisual.bonus)+contextualAdjustment)) :
        Math.min(99,textScore);
      const title=selected[0].text.replace(/[\n\r]/gu,' ').trim().slice(0,72);
      suggestions.push({
        start:round(cues[i].start),end:round(cues[j].end),
        duration:round(length),score,title,
        reason:[reasons[0]?.label||'Fala contínua com duração adequada',...audioVisual.reasons].join(' · '),
        evidence:{text:audioVisual.available?Math.min(86,textScore):Math.min(99,textScore),audioPeaks:audioVisual.highEnergy,
          sceneChanges:audioVisual.visualChanges,signalBonus:audioVisual.bonus,coherence:contextualAdjustment,source:audioVisual.available?'texto + áudio/vídeo':'somente texto'},
        transcript:script.slice(0,360)
      });
    }
  }
  suggestions.sort((a,b)=>b.score-a.score||Math.abs(a.duration-26)-Math.abs(b.duration-26)||a.start-b.start);
  const picked=[];
  for(const candidate of suggestions){
    if(picked.some(x=>candidate.start<x.end+1 && candidate.end>x.start-1))continue;
    picked.push(candidate);
    if(picked.length>=maxClips)break;
  }
  if(!picked.length)return {error:'Não há falas contínuas suficientes para gerar Shorts de pelo menos 8 segundos.',candidates:[]};
  const refined=picked.map((candidate,i)=>{
    const firstIndex=cues.findIndex(c=>Math.abs(c.start-candidate.start)<.011);
    const lastIndex=cues.findIndex(c=>Math.abs(c.end-candidate.end)<.011);
    const bounds=refineShortBoundaries({
      start:candidate.start,end:candidate.end,duration:endOfMedia,signals,
      previousEnd:firstIndex>0?cues[firstIndex-1].end:0,
      nextStart:lastIndex>=0&&lastIndex<cues.length-1?cues[lastIndex+1].start:endOfMedia,
      maxDuration:MAX_LEN
    });
    return {...candidate,start:bounds.start,end:bounds.end,
      duration:round(bounds.end-bounds.start),rank:i+1,
      reason:candidate.reason+(bounds.adjusted?' · Limites ajustados em pausas':''),
      evidence:{...candidate.evidence,pauseAdjusted:bounds.adjusted}};
  });
  return {error:null,candidates:refined};
}
