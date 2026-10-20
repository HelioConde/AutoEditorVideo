import fs from 'node:fs';
import path from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import { parseSubtitleText } from '../src/subtitles.js';

/** Optional offline whisper.cpp executable. No model or upload is fetched. */
export function whisperCapability(env=process.env) {
  const bin=env.WHISPER_BIN || (process.platform==='win32'?'whisper-cli.exe':'whisper-cli');
  const model=env.WHISPER_MODEL;
  if(typeof model!=='string'||!fs.existsSync(model)||!fs.statSync(model).isFile())
    return false;
  const probe=spawnSync(bin,['--help'],{encoding:'utf8',timeout:5000,windowsHide:true});
  // Certain whisper-cli builds use 0 or 1 for --help; existence is what matters.
  return !probe.error && [0,1].includes(probe.status);
}
function call(executable,args,timeout=300000) {
  return new Promise((resolve,reject)=>{
    const child=spawn(executable,args,{windowsHide:true,stdio:['ignore','ignore','pipe']});
    let stderr='';
    const timer=setTimeout(()=>child.kill(),timeout);
    let resolved=false;
    const done=e=>{if(resolved)return;resolved=true;clearTimeout(timer);e?reject(e):resolve();};
    child.stderr.on('data',buf=>{stderr=(stderr+buf.toString()).slice(-1000);});
    child.once('error',done);
    child.once('close',code=>done(code===0?null:new Error(stderr||'Processo falhou: '+code)));
  });
}
export async function transcribeLocalAudio({source,tmp,ffmpeg='ffmpeg',env=process.env}) {
  if(!whisperCapability(env))
    throw new Error('Whisper.cpp indisponível. Configure WHISPER_BIN e WHISPER_MODEL.');
  const wav=path.join(tmp,'audio.wav'),output=path.join(tmp,'transcription');
  await call(ffmpeg,['-hide_banner','-loglevel','error','-y','-i',source,'-vn','-ar','16000','-ac','1',
    '-c:a','pcm_s16le',wav],300000);
  const bin=env.WHISPER_BIN||(process.platform==='win32'?'whisper-cli.exe':'whisper-cli');
  await call(bin,['-m',env.WHISPER_MODEL,'-f',wav,'-l','pt','-osrt','-of',output],300000);
  const file=output+'.srt';
  if(!fs.existsSync(file))throw new Error('O Whisper não gerou legendas SRT.');
  const captions=fs.readFileSync(file,'utf8');
  return parseSubtitleText(captions);
}
