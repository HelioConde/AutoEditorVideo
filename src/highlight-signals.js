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
  if(!value || typeof value!=='object')return {audio:[],scenes:[],motion:[]};
  const audio=Array.isArray(value.audio)?value.audio.filter(x=>Number.isFinite(x?.time)&&Number.isFinite(x?.db)&&x.time>=0&&x.time<=3600&&x.db<=0&&x.db>=-120).slice(0,1800):[];
  const scenes=Array.isArray(value.scenes)?value.scenes.filter(x=>Number.isFinite(x)&&x>=0&&x<=3600).slice(0,1000):[];
  const motion=Array.isArray(value.motion)?value.motion.filter(x=>Number.isFinite(x?.time)&&Number.isFinite(x?.value)&&x.time>=0&&x.time<=3600&&x.value>=0&&x.value<=255).slice(0,1800):[];
  return {audio,scenes,motion};
}
export function candidateSignalEvidence(value,start,end,profile='podcast') {
  const {audio,scenes,motion}=normalizedSignals(value);
  const levels=audio.map(x=>x.db).sort((a,b)=>a-b);
  const median=levels.length?levels[Math.floor(levels.length/2)]:null;
  // A substantial *relative* increase in energy, not simply a loud source.
  const spikes=audio.filter(x=>x.time>=start && x.time<end && median!==null && x.db-median>=5);
  const cuts=scenes.filter(t=>t>=start && t<end);
  const movement=motion.filter(x=>x.time>=start&&x.time<end);
  const avgMotion=movement.length?movement.reduce((sum,x)=>sum+x.value,0)/movement.length:0;
  const motionActivity=movement.length>=Math.max(4,(end-start)*.75)&&avgMotion>=2?Math.min(3,Math.floor(avgMotion/4)+1):0;
  const highEnergy=Math.min(3,spikes.length);
  const visualChanges=Math.min(3,cuts.length);
  const bonus=profile==='gameplay' ?
    highEnergy*3 + visualChanges*4 + motionActivity*2 :
    profile==='tutorial' ? highEnergy*2 + visualChanges*2 + motionActivity :
    highEnergy*3 + visualChanges*2 + motionActivity;
  const reasons=[];
  if(highEnergy)reasons.push('Picos de energia no áudio');
  if(visualChanges)reasons.push('Mudanças visuais detectadas');
  if(motionActivity)reasons.push('Movimento entre quadros');
  return {bonus,highEnergy,visualChanges,motionActivity,reasons,available:audio.length>0||scenes.length>0||motion.length>0};
}

/** Brightness change between sampled frames (FFmpeg signalstats YDIF, 0-255). */
export function parseMotionLog(log) {
  const motion=[];
  let time=null;
  for(const line of String(log).split(/\r?\n/u)){
    const ts=/\bpts_time:\s*([0-9]+(?:\.[0-9]+)?)/u.exec(line);
    if(ts){time=Number(ts[1]);continue;}
    const diff=/lavfi\.signalstats\.YDIF=([0-9]+(?:\.[0-9]+)?)/u.exec(line);
    if(diff && time!==null){
      const value=Number(diff[1]);
      if(Number.isFinite(value) && value>=0 && value<=255 && motion.length<1800)
        motion.push({time:Math.round(time*100)/100,value:Math.round(value*100)/100});
      time=null;
    }
  }
  return motion;
}

/** Parse pairs emitted by FFmpeg silencedetect, ignoring unfinished intervals. */
export function parseSilenceLog(log) {
  const result=[];
  let start=null;
  for(const line of String(log).split(/\r?\n/u)) {
    const begin=/\bsilence_start:\s*([0-9]+(?:\.[0-9]+)?)/u.exec(line);
    if(begin)start=Number(begin[1]);
    const finish=/\bsilence_end:\s*([0-9]+(?:\.[0-9]+)?)/u.exec(line);
    if(finish && start!==null) {
      const end=Number(finish[1]);
      if(Number.isFinite(start)&&Number.isFinite(end)&&end-start>=.22&&start>=0&&result.length<1000)
        result.push({start:Math.round(start*100)/100,end:Math.round(end*100)/100});
      start=null;
    }
  }
  return result;
}

/**
 * Find sustained bursts relative to the source's usual frame activity.
 * Single-frame flashes are ignored; a stationary source stays stationary.
 * These are visual novelty markers, NOT semantic detections of game events.
 */
export function motionBurstMoments(value,{maxEvents=24}={}) {
  const {motion}=normalizedSignals(value);
  if(motion.length<8)return [];
  const ordered=motion.map(x=>x.value).sort((a,b)=>a-b);
  const median=ordered[Math.floor(ordered.length/2)];
  const threshold=Math.max(4,median+Math.max(3,median*.6));
  const high=motion.filter(x=>x.value>=threshold).sort((a,b)=>a.time-b.time);
  const groups=[];
  for(const point of high) {
    const previous=groups.at(-1);
    if(previous && point.time-previous.last<=1.1) {
      previous.last=point.time;
      previous.count++;
      previous.peak=Math.max(previous.peak,point.value);
    }else groups.push({first:point.time,last:point.time,count:1,peak:point.value});
  }
  // Prefer the strongest changes but do not interpret one corrupted frame
  // or a tiny one-frame flash as a meaningful event.
  return groups.filter(g=>g.count>=2)
    .sort((a,b)=>(b.peak-threshold)-(a.peak-threshold)||a.first-b.first)
    .slice(0,Math.max(0,Math.min(24,maxEvents)))
    .map(g=>({time:Math.round(((g.first+g.last)/2)*100)/100,
      strength:Math.round((g.peak-threshold)*100)/100,
      samples:g.count}))
    .sort((a,b)=>a.time-b.time);
}
