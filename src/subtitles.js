/**
 * Subtitle cues and SubRip interchange shared across web and desktop.
 * JSON is intentionally bounded to avoid untrusted large payloads.
 */
export const MAX_SUBTITLES=120;
export const MAX_SUBTITLE_SECONDS=3600;
export const MAX_SUBTITLE_CHARS=240;

export function validateSubtitles(value) {
  if(!Array.isArray(value) || value.length>MAX_SUBTITLES)
    return {error:'Use até 120 legendas.',subtitles:[]};
  const result=[];
  for(let i=0;i<value.length;i++) {
    const item=value[i];
    if(!item || typeof item!=='object' || Array.isArray(item)) return {error:'Legenda inválida.',subtitles:[]};
    const start=item.start, end=item.end, text=item.text;
    if(typeof start!=='number'||!Number.isFinite(start)||typeof end!=='number'||!Number.isFinite(end)
      ||start<0||end>MAX_SUBTITLE_SECONDS||end-start<.08)
      return {error:'Revise os tempos das legendas.',subtitles:[]};
    if(typeof text!=='string'||!text.trim()||text.length>MAX_SUBTITLE_CHARS
      ||/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/u.test(text))
      return {error:'Cada legenda deve ter texto com até 240 caracteres.',subtitles:[]};
    result.push({start:Math.round(start*1000)/1000,end:Math.round(end*1000)/1000,text:text.trim()});
  }
  result.sort((a,b)=>a.start-b.start||a.end-b.end);
  for(let i=1;i<result.length;i++){
    if(result[i].start<result[i-1].end-.01)
      return {error:'As legendas não podem se sobrepor.',subtitles:[]};
  }
  return {error:null,subtitles:result};
}

function timestampSeconds(raw) {
  const match=/^(?:(\d{1,2}):)?(\d{2}):(\d{2})[,.](\d{3})$/u.exec(raw.trim());
  if(!match)return NaN;
  const h=Number(match[1]||0),m=Number(match[2]),s=Number(match[3]),ms=Number(match[4]);
  if(m>=60||s>=60)return NaN;
  return ((h*60+m)*60+s)+ms/1000;
}
function stamp(seconds) {
  const ms=Math.round(seconds*1000),h=Math.floor(ms/3600000),m=Math.floor(ms/60000)%60,s=Math.floor(ms/1000)%60;
  return String(h).padStart(2,'0')+':'+String(m).padStart(2,'0')+':'+String(s).padStart(2,'0')+','+String(ms%1000).padStart(3,'0');
}
export function parseSubtitleText(input) {
  if(typeof input!=='string'||input.length>64000)throw new Error('Arquivo de legendas acima do limite (64 KB).');
  const lines=input.replace(/^\uFEFF/u,'').replace(/\r\n?/gu,'\n').split('\n');
  if(lines[0]?.startsWith('WEBVTT'))lines.shift();
  const blocks=lines.join('\n').split(/\n\s*\n/u).filter(s=>s.trim());
  const cues=[];
  for(const block of blocks) {
    const rows=block.trim().split('\n').map(x=>x.trim());
    const index=rows.findIndex(x=>x.includes('-->'));
    if(index<0)continue;
    const match=/^([0-9:.,]+)\s*-->\s*([0-9:.,]+)/u.exec(rows[index]);
    if(!match)throw new Error('Horário inválido no SRT/VTT.');
    const start=timestampSeconds(match[1]),end=timestampSeconds(match[2]);
    const text=rows.slice(index+1).join('\n').replace(/<[^>]*>/gu,'').trim();
    cues.push({start,end,text});
  }
  if(!cues.length)throw new Error('Nenhuma legenda encontrada no arquivo.');
  const checked=validateSubtitles(cues);
  if(checked.error)throw new Error(checked.error);
  return checked.subtitles;
}
export function toSrt(input) {
  const validated=validateSubtitles(input);
  if(validated.error)throw new Error(validated.error);
  return validated.subtitles.map((cue,i)=>
    String(i+1)+'\n'+stamp(cue.start)+' --> '+stamp(cue.end)+'\n'+cue.text.replace(/<[^>]*>/gu,'')+'\n'
  ).join('\n');
}

/** Transform absolute source timestamps into times in the concatenated export. */
export function remapSubtitles(subtitles,segments) {
  const checked=validateSubtitles(subtitles);
  if(checked.error)throw new Error(checked.error);
  const output=[];
  let elapsed=0;
  for(const segment of segments) {
    for(const cue of checked.subtitles) {
      const begin=Math.max(segment.start,cue.start),end=Math.min(segment.end,cue.end);
      if(end-begin>=.08)output.push({
        start:Math.round((elapsed+begin-segment.start)*1000)/1000,
        end:Math.round((elapsed+end-segment.start)*1000)/1000,
        text:cue.text
      });
    }
    elapsed+=segment.end-segment.start;
  }
  return validateSubtitles(output).subtitles;
}
