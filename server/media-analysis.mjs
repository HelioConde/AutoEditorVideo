import { spawn } from 'node:child_process';
import { parseRmsLog, parseSceneLog, parseMotionLog, parseSilenceLog } from '../src/highlight-signals.js';

/**
 * Use the locally installed FFmpeg to sample audio loudness and visual cuts.
 * No Python, paid API, uploads or extra GPU runtime is needed.
 * Logs are capped; commands are argv arrays, never a user-supplied shell.
 */
function collectFfmpeg(executable,args,{timeoutMs=90000}={}) {
  return new Promise((resolve,reject)=>{
    const child=spawn(executable,args,{windowsHide:true,stdio:['ignore','ignore','pipe']});
    let logs='',ended=false,timedOut=false;
    const clock=setTimeout(()=>{timedOut=true;child.kill('SIGKILL');},timeoutMs);
    function done(error) {
      if(ended)return;
      ended=true;clearTimeout(clock);
      error?reject(error):resolve(logs);
    }
    child.stderr.on('data',chunk=>{
      const part=chunk.toString();
      if(logs.length<900000)logs+=part.slice(0,900000-logs.length);
      else child.kill('SIGKILL');
    });
    child.once('error',done);
    child.once('close',code=>{
      if(timedOut)return done(new Error('Tempo limite da análise audiovisual excedido.'));
      return done(code===0?null:new Error('FFmpeg não conseguiu analisar esta faixa de mídia.'));
    });
  });
}
export async function analyzeLocalMedia({source,duration,ffmpeg='ffmpeg'}) {
  const seconds=Number(duration);
  if(!Number.isFinite(seconds)||seconds<=0||seconds>600)
    throw new Error('A análise audiovisual aceita arquivos de até 10 minutos.');
  const common=['-hide_banner','-nostdin','-loglevel','info','-i',source,
    '-t',String(Math.min(seconds,600))];
  const audioArgs=[...common,'-vn','-ac','1','-ar','16000',
    '-af','silencedetect=noise=-32dB:d=0.25,asetnsamples=n=16000:p=0,astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level',
    '-f','null','-'];
  // At 2 fps / 160px this extracts scene boundaries rather than decoding
  // expensive full-resolution frames for CV inference.
  const imageArgs=[...common,'-an','-vf','fps=2,scale=160:-2,select=gt(scene\\,0.25),showinfo',
    '-f','null','-'];
  const motionArgs=[...common,'-an','-vf',
    'fps=2,scale=160:-2,signalstats,metadata=print:key=lavfi.signalstats.YDIF',
    '-f','null','-'];
  const [audio,visual,movement]=await Promise.allSettled([
    collectFfmpeg(ffmpeg,audioArgs),
    collectFfmpeg(ffmpeg,imageArgs),
    collectFfmpeg(ffmpeg,motionArgs),
  ]);
  if(audio.status==='rejected' && visual.status==='rejected' && movement.status==='rejected')
    throw new Error('FFmpeg não conseguiu analisar áudio nem vídeo.');
  return {
    audio:audio.status==='fulfilled'?parseRmsLog(audio.value):[],
    silences:audio.status==='fulfilled'?parseSilenceLog(audio.value):[],
    scenes:visual.status==='fulfilled'?parseSceneLog(visual.value):[],
    motion:movement.status==='fulfilled'?parseMotionLog(movement.value):[],
    coverage:{
      audio:audio.status==='fulfilled',
      video:visual.status==='fulfilled',
      motion:movement.status==='fulfilled'
    }
  };
}
