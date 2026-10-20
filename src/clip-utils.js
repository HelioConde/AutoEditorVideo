export const MAX_CLIPS = 5;
export const MIN_CLIP_SECONDS = 0.25;

export function normalizeClips({ segments, start, end, duration, maxTotal = 600, maxEach = 600, maxClips = MAX_CLIPS }) {
  const source = segments === undefined ? [{ start, end }] : segments;
  if (!Array.isArray(source) || source.length < 1 || source.length > maxClips)
    return { error: 'Selecione entre 1 e ' + maxClips + ' trechos.' };
  const d = Number(duration);
  if (!Number.isFinite(d) || d <= 0) return { error: 'A duração do vídeo é inválida.' };
  let total = 0;
  const clips = [];
  for (const item of source) {
    if (!item || typeof item !== 'object' || item.start === '' || item.end === '' || item.start === null || item.end === null)
      return { error: 'Os trechos precisam ter início e fim válidos.' };
    const a = Number(item.start), b = Number(item.end);
    if (![a, b].every(Number.isFinite) || a < 0 || b > d + 0.15 || b - a < MIN_CLIP_SECONDS)
      return { error: 'Cada trecho deve estar dentro do vídeo e ter pelo menos 0,25 segundo.' };
    if (b - a > maxEach + 0.01) return { error: 'Um dos trechos ultrapassa o limite de duração.' };
    total += b - a;
    clips.push({ start: Math.round(a * 1000) / 1000, end: Math.round(b * 1000) / 1000 });
  }
  if (total > maxTotal + 0.01)
    return { error: 'A sequência selecionada ultrapassa o limite total de duração.' };
  return { clips, total: Math.round(total * 1000) / 1000, error: null };
}

export function insertClip(queue, clip, maxClips = MAX_CLIPS) {
  if (!Array.isArray(queue) || queue.length >= maxClips) return queue;
  return [...queue, { start: Number(clip.start), end: Number(clip.end) }];
}
export function moveClip(queue, index, direction) {
  const target = index + direction;
  if (index < 0 || target < 0 || index >= queue.length || target >= queue.length) return queue;
  const result = queue.slice();
  [result[index], result[target]] = [result[target], result[index]];
  return result;
}

/** Move a trim boundary in 10ms increments while retaining a valid 250ms clip. */
export function nudgeBoundary({ start, end, duration, boundary, delta }) {
  const a=Number(start),b=Number(end),d=Number(duration),n=Number(delta);
  if(![a,b,d,n].every(Number.isFinite)||d<MIN_CLIP_SECONDS || !['start','end'].includes(boundary))
    return {start:a,end:b};
  const round=x=>Math.round(x*100)/100;
  if(boundary==='start')return {start:round(Math.max(0,Math.min(b-MIN_CLIP_SECONDS,a+n))),end:b};
  return {start:a,end:round(Math.max(a+MIN_CLIP_SECONDS,Math.min(d,b+n)))};
}
/** Apply an edited clip to one position without modifying the rest of the sequence. */
export function replaceClip(queue,index,clip,{duration,maxTotal=600,maxEach=600}={}) {
  if(!Array.isArray(queue)||index<0||index>=queue.length)return {error:'Trecho não encontrado.'};
  const next=queue.map((item,i)=>i===index?{start:Number(clip.start),end:Number(clip.end)}:item);
  return normalizeClips({segments:next,duration,maxTotal,maxEach});
}
/** Zoom of the trim sliders; filmstrip thumbnails continue showing full source. */
export function zoomWindow({duration,start,end,zoom=1}) {
  const d=Number(duration);
  if(!Number.isFinite(d)||d<=0)return {min:0,max:1};
  const factor=[1,2,4,8].includes(Number(zoom))?Number(zoom):1;
  const window=Math.min(d,Math.max(.3,d/factor));
  const a=Number(start),b=Number(end);
  const mid=Math.max(0,Math.min(d,(Number.isFinite(a)&&Number.isFinite(b)?(a+b)/2:0)));
  const min=Math.max(0,Math.min(d-window,mid-window/2));
  return {min:Math.round(min*1000)/1000,max:Math.round((min+window)*1000)/1000};
}
