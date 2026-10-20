
import { normalizeClips } from './clip-utils.js';
import { validateSubtitles } from './subtitles.js';
import { SCENE_THEMES, SCENE_TRANSITIONS, defaultSceneTheme } from './scene-presets.js';

export const PROJECT_SCHEMA = 'autoeditor.project';
export const PROJECT_VERSION = 1;
export const MAX_SCENES = 6;

const text = (x, max) => typeof x === 'string' ? x.trim().slice(0,max) : '';
const finite = x => typeof x === 'number' && Number.isFinite(x);

export function scenesFromScript(input) {
  const value=text(input,4000);
  if(!value) return [];
  const paragraphs=value.split(/\n\s*\n/).map(s=>s.replace(/\s+/g,' ').trim()).filter(Boolean);
  const sections=paragraphs.length>1?paragraphs:(value.match(/[^.!?]+[.!?]+|[^.!?]+$/gu)||[]).map(s=>s.trim()).filter(Boolean);
  const result=[];
  for(const section of sections) {
    // Paragraph boundaries become scene boundaries unless at the scene limit.
    const words=section.split(/\s+/);
    let chunk='';
    for(const word of words) {
      if(chunk && (chunk+' '+word).length>280 && result.length<MAX_SCENES-1) {
        result.push(chunk);
        chunk=word;
      } else {
        chunk=(chunk?chunk+' ':'')+word;
      }
    }
    if(chunk) {
      if(result.length>=MAX_SCENES) result[MAX_SCENES-1]=(result[MAX_SCENES-1]+' '+chunk).slice(0,500);
      else result.push(chunk.slice(0,500));
    }
  }
  return result.slice(0,MAX_SCENES).map((body,i)=>({title:'Cena '+(i+1),text:body,duration:7}));
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
    const theme=s.theme === undefined ? defaultSceneTheme(i) : s.theme;
    const transition=s.transition === undefined ? 'fade' : s.transition;
    if(!SCENE_THEMES.some(item=>item.id===theme))return {error:'Tema visual de cena inválido.',scenes:[]};
    if(!SCENE_TRANSITIONS.some(item=>item.id===transition))return {error:'Transição de cena inválida.',scenes:[]};
    scenes.push({title,text:body,duration:Math.round(duration*10)/10,theme,transition});
  }
  return {error:null,scenes};
}

export function createProjectFile({name,aspect='9:16',media=null,start=0,end=0,clips=[],script='',scenes=[],voiceEngine='system',subtitles=[],burnSubtitles=false}) {
  const exported={schema:PROJECT_SCHEMA,version:PROJECT_VERSION,name:text(name,64)||'Projeto sem nome',
    aspect:aspect==='16:9'?'16:9':'9:16',
    media:media ? {name:text(media.originalName||media.name,150),size:Number(media.size)||0,duration:Number(media.duration)||0} : null,
    edit:{start:Number(start)||0,end:Number(end)||0,clips:Array.isArray(clips)?clips.map(c=>({start:Number(c.start),end:Number(c.end)})):[],
      script:text(script,4000),voiceEngine,subtitles,burnSubtitles:Boolean(burnSubtitles),scenes:Array.isArray(scenes)?scenes.map(x=>({title:x.title,text:x.text,duration:x.duration,theme:x.theme,transition:x.transition})):[]}};
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
  const validatedCues=validateSubtitles(value.edit.subtitles??[]);
  if(validatedCues.error)throw new Error(validatedCues.error);
  const burnSubtitles=value.edit.burnSubtitles??false;
  if(typeof burnSubtitles!=='boolean')throw new Error('Opção de legendar o vídeo inválida.');
  const voiceEngine=value.edit.voiceEngine ?? 'system';
  if(!['system','piper'].includes(voiceEngine))throw new Error('Motor de voz inválido.');
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
    edit:{start,end,clips:parsedClips,script:value.edit.script,scenes:scenes.scenes,voiceEngine,subtitles:validatedCues.subtitles,burnSubtitles}};
}

export function stringifyProjectFile(data) { return JSON.stringify(createProjectFile(data),null,2)+'\n'; }
