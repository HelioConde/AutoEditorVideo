/**
 * Lightweight local feature extraction for Short ranking.
 * All features refer to seconds in the ORIGINAL source, never output timeline.
 * Audio energy is not emotion recognition; scene boundaries are not event labels.
 */
export function parseRmsLog(log) {
  const samples=[];
  let time=null;
  for(const line of String(log).split(/\r?\n/u)){
    const ts=/\bpts_time:\s*([0-9]+(?:\.[0-9]+)?)/u.exec(line);
    if(ts){time=Number(ts[1]);continue;}
    const db=/lavfi\.astats\.Overall\.RMS_level=(-?(?:\d+(?:\.\d+)?|inf))/iu.exec(line);
    if(db && time!==null) {
      const number=Number(db[1]);
      if(Number.isFinite(number) && samples.length<1800)
        samples.push({time:Math.round(time*100)/100,db:Math.round(number*10)/10});
      time=null;
    }
  }
  return samples;
}
export function parseSceneLog(log) {
  const times=[];
  for(const line of String(log).split(/\r?\n/u)){
    if(!line.includes('showinfo')||!line.includes('pts_time:'))continue;
    const m=/\bpts_time:\s*([0-9]+(?:\.[0-9]+)?)/u.exec(line);
    const n=m?Number(m[1]):NaN;
    if(Number.isFinite(n)&&n>=0 && times.length<1000) times.push(Math.round(n*100)/100);
  }
  return [...new Set(times)].sort((a,b)=>a-b);
}
export function normalizedSignals(value) {
  if(!value || typeof value!=='object')return {audio:[],scenes:[]};
  const audio=Array.isArray(value.audio)?value.audio.filter(x=>Number.isFinite(x?.time)&&Number.isFinite(x?.db)&&x.time>=0&&x.time<=3600&&x.db<=0&&x.db>=-120).slice(0,1800):[];
  const scenes=Array.isArray(value.scenes)?value.scenes.filter(x=>Number.isFinite(x)&&x>=0&&x<=3600).slice(0,1000):[];
  return {audio,scenes};
}
export function candidateSignalEvidence(value,start,end,profile='podcast') {
  const {audio,scenes}=normalizedSignals(value);
  const levels=audio.map(x=>x.db).sort((a,b)=>a-b);
  const median=levels.length?levels[Math.floor(levels.length/2)]:null;
  // A substantial *relative* increase in energy, not simply a loud source.
  const spikes=audio.filter(x=>x.time>=start && x.time<end && median!==null && x.db-median>=5);
  const cuts=scenes.filter(t=>t>=start && t<end);
  const highEnergy=Math.min(3,spikes.length);
  const visualChanges=Math.min(3,cuts.length);
  const bonus=profile==='gameplay' ?
    highEnergy*3 + visualChanges*4 :
    profile==='tutorial' ? highEnergy*2 + visualChanges*2 :
    highEnergy*3 + visualChanges*2;
  const reasons=[];
  if(highEnergy)reasons.push('Picos de energia no áudio');
  if(visualChanges)reasons.push('Mudanças visuais detectadas');
  return {bonus,highEnergy,visualChanges,reasons,available:audio.length>0||scenes.length>0};
}
