
import { normalizeClips } from './clip-utils.js';

export const PROJECT_SCHEMA = 'autoeditor.project';
export const PROJECT_VERSION = 1;
export const MAX_SCENES = 6;

const text = (x, max) => typeof x === 'string' ? x.trim().slice(0,max) : '';
const finite = x => typeof x === 'number' && Number.isFinite(x);

export function scenesFromScript(input) {
  const value = text(input, 4000);
  if (!value) return [];
  const paragraphs = value.split(/\n\s*\n/).map(p=>p.replace(/\s+/g,' ').trim()).filter(Boolean);
  // Short paragraphs become scenes; long scripts are distributed over a small,
  // predictable number of scenes. Nothing here generates fictional media.
  const sentences = paragraphs.length > 1 ? paragraphs : (value.match(/[^.!?]+[.!?]+|[^.!?]+$/gu) || []);
  const chunks = [];
  for (const segment of sentences) {
    const part = segment.trim();
    if (!part) continue;
    if (chunks.length < MAX_SCENES && (chunks.length === 0 || chunks[chunks.length-1].length + part.length > 160))
      chunks.push(part);
    else chunks[chunks.length-1] = (chunks[chunks.length-1] + ' ' + part).slice(0,500);
  }
  if (chunks.length === 1 && chunks[0].length > 180) {
    const words=chunks[0].split(/\s+/);
    const groups=[];
    for(const word of words) {
      if (!groups.length || (groups[groups.length-1]+' '+word).length>145) groups.push(word);
      else groups[groups.length-1]+=' '+word;
      if(groups.length>=MAX_SCENES) break;
    }
    return groups.map((p,i)=>({title:'Cena '+(i+1),text:p.slice(0,500),duration:7}));
  }
  return chunks.slice(0,MAX_SCENES).map((p,i)=>({title:'Cena '+(i+1),text:p.slice(0,500),duration:7}));
}

export function validateScenes(input) {
  if (!Array.isArray(input) || input.length < 1 || input.length > MAX_SCENES)
    return {error:'Crie de 1 a 6 cenas.',scenes:[]};
  const scenes=[];
  for(let i=0;i<input.length;i++) {
    const s=input[i];
    if (!s || typeof s !== 'object' || Array.isArray(s)) return {error:'Cena inválida.',scenes:[]};
    const body=text(s.text,500),title=text(s.title,70)||'Cena '+(i+1);
    if (body.length < 3 || body.length > 500 || typeof s.text !== 'string' || s.text.length > 500)
      return {error:'Cada cena precisa de um texto com 3 a 500 caracteres.',scenes:[]};
    const duration=Number(s.duration ?? 7);
    if (!Number.isFinite(duration) || duration < 2 || duration > 15)
      return {error:'A duração de cada cena deve ser entre 2 e 15 segundos.',scenes:[]};
    scenes.push({title,text:body,duration:Math.round(duration*10)/10});
  }
  return {error:null,scenes};
}

export function createProjectFile({name,aspect='9:16',media=null,start=0,end=0,clips=[],script='',scenes=[]}) {
  const exported={schema:PROJECT_SCHEMA,version:PROJECT_VERSION,name:text(name,64)||'Projeto sem nome',
    aspect:aspect==='16:9'?'16:9':'9:16',
    media:media ? {name:text(media.originalName||media.name,150),size:Number(media.size)||0,duration:Number(media.duration)||0} : null,
    edit:{start:Number(start)||0,end:Number(end)||0,clips:Array.isArray(clips)?clips.map(c=>({start:Number(c.start),end:Number(c.end)})):[],
      script:text(script,4000),scenes:Array.isArray(scenes)?scenes.map(x=>({title:x.title,text:x.text,duration:x.duration})):[]}};
  return exported;
}

export function parseProjectFile(value) {
  if (!value || typeof value!=='object' || Array.isArray(value) || value.schema!==PROJECT_SCHEMA || value.version!==PROJECT_VERSION)
    throw new Error('Projeto inválido ou versão incompatível. Use um arquivo AutoEditor v1.');
  if (typeof value.name !== 'string' || value.name.trim().length < 2 || value.name.length > 64)
    throw new Error('O projeto precisa ter nome entre 2 e 64 caracteres.');
  if (!['9:16','16:9'].includes(value.aspect)) throw new Error('Formato do projeto inválido.');
  if (!value.edit || typeof value.edit!=='object' || Array.isArray(value.edit)) throw new Error('Edição ausente no projeto.');
  if (typeof value.edit.script!=='string' || value.edit.script.length>4000) throw new Error('Roteiro inválido.');
  const scenes= value.edit.scenes?.length ? validateScenes(value.edit.scenes) : {error:null,scenes:[]};
  if(scenes.error) throw new Error(scenes.error);
  const media=value.media;
  if(media!==null && media!==undefined) {
    if(!media || typeof media.name!=='string' || !media.name.trim() || media.name.length>150 ||
       !finite(media.duration) || media.duration < 0 || !finite(media.size) || media.size<0)
       throw new Error('Referência de mídia inválida.');
  }
  const clips=Array.isArray(value.edit.clips)?value.edit.clips:[];
  let parsedClips=[];
  if(clips.length) {
    const d=media?.duration;
    if(!finite(d) || d<=0) throw new Error('Cortes importados sem duração de mídia.');
    const result=normalizeClips({segments:clips,duration:d});
    if(result.error) throw new Error(result.error);
    parsedClips=result.clips;
  }
  const start=value.edit.start,end=value.edit.end;
  if(!finite(start) || !finite(end) || start<0 || end<0) throw new Error('Marcas de tempo inválidas.');
  if(media && media.duration>0 && (start>media.duration+.15 || end>media.duration+.15)) throw new Error('Marcas fora da duração do vídeo.');
  return {name:value.name.trim(),aspect:value.aspect,media:media||null,
    edit:{start,end,clips:parsedClips,script:value.edit.script,scenes:scenes.scenes}};
}

export function stringifyProjectFile(data) { return JSON.stringify(createProjectFile(data),null,2)+'\n'; }
