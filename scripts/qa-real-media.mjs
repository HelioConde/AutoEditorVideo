#!/usr/bin/env node
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import {analyzeLocalMedia} from '../server/media-analysis.mjs';

// Exercise the production analyzer on media uploaded to this repository.
const mediaFiles=['15979800_1080_1920_30fps.mp4','public/6767176-uhd_2560_1440_25fps.mp4'];
const output=path.resolve('test-results','real-media');
fs.mkdirSync(output,{recursive:true});
function command(name,args,timeout=90000){
  const r=spawnSync(name,args,{encoding:'utf8',timeout,maxBuffer:3*1024*1024});
  assert.equal(r.status,0,
    name+' failed: '+(r.error?.message||r.stderr||'no stderr').slice(-1800));
  return r.stdout;
}
function metadata(file){
  return JSON.parse(command('ffprobe',[
    '-v','error','-show_entries',
    'format=duration,size:stream=index,codec_type,codec_name,width,height,r_frame_rate',
    '-of','json',file]));
}
const results=[];
for(const [index,relative] of mediaFiles.entries()){
  const file=path.resolve(relative);
  assert.ok(fs.existsSync(file),'Arquivo não encontrado no checkout: '+relative);
  const meta=metadata(file),video=meta.streams.find(s=>s.codec_type==='video');
  const audio=meta.streams.filter(s=>s.codec_type==='audio');
  assert.ok(video&&video.width>0&&video.height>0,relative+' deve conter vídeo legível');
  const duration=Number(meta.format.duration);
  assert.ok(Number.isFinite(duration)&&duration>1,relative+' precisa ter duração válida');
  const inspected=Math.min(duration,12);
  const signals=await analyzeLocalMedia({source:file,duration:inspected});
  assert.equal(signals.coverage.video,true,relative+' deve permitir análise visual');
  assert.ok(Array.isArray(signals.scenes));
  let meanVolumeDb=null;
  if(audio.length>0){
    assert.equal(signals.coverage.audio,true,relative+' deve permitir decodificar áudio');
    // A stream can contain encoded silence. A missing RMS sample must never
    // be mistaken for proof that a detector found (or did not find) speech.
    const volume=spawnSync('ffmpeg',['-hide_banner','-nostdin','-i',file,
      '-t',String(inspected),'-vn','-af','volumedetect','-f','null','-'],
      {encoding:'utf8',timeout:60000,maxBuffer:3*1024*1024});
    assert.equal(volume.status,0,volume.stderr?.slice(-600));
    const match=/mean_volume:\s*([^\s]+)/u.exec(volume.stderr||'');
    meanVolumeDb=match?(Number.isFinite(Number(match[1]))?Number(match[1]):match[1]):null;
  }else{
    assert.equal(signals.audio.length,0,'Não inventar energia sonora para arquivo sem áudio');
  }
  const stem='source-'+(index+1),portrait=path.join(output,stem+'-portrait.mp4');
  command('ffmpeg',['-hide_banner','-loglevel','error','-y','-ss','0','-i',file,
    '-t',String(Math.min(1.5,duration)),'-an','-vf',
    'fps=12,scale=360:640:force_original_aspect_ratio=increase,crop=360:640,setsar=1',
    '-c:v','libx264','-preset','ultrafast','-crf','30','-pix_fmt','yuv420p',
    portrait]);
  const rendered=metadata(portrait),outVideo=rendered.streams.find(s=>s.codec_type==='video');
  assert.equal(outVideo.width,360);assert.equal(outVideo.height,640);
  assert.ok(fs.statSync(portrait).size>1000);
  const snapshot=path.join(output,stem+'-preview.jpg');
  command('ffmpeg',['-hide_banner','-loglevel','error','-y','-i',portrait,
    '-frames:v','1','-q:v','3',snapshot],30000);
  const record={
    file:relative,bytes:fs.statSync(file).size,
    durationSeconds:Number(duration.toFixed(2)),
    video:{codec:video.codec_name,width:video.width,height:video.height,frameRate:video.r_frame_rate},
    audioTracks:audio.length,audioCodecs:audio.map(x=>x.codec_name),
    meanVolumeDb, noDetectedAudioEnergy:signals.audio.length===0,
    analyzedSeconds:Number(inspected.toFixed(2)),rmsSamples:signals.audio.length,
    sceneChanges:signals.scenes.length,mediaCoverage:signals.coverage,
    portraitPreview:path.basename(portrait),snapshot:path.basename(snapshot)
  };
  results.push(record);
  console.log('REAL_MEDIA_QA '+JSON.stringify(record));
}
fs.writeFileSync(path.join(output,'report.json'),JSON.stringify({
  generatedBy:'npm run qa:media',results,
  note:'Energy peaks and scene changes do not prove semantic highlights. Speech transcription remains required.'
},null,2)+'\n');
if(process.env.GITHUB_STEP_SUMMARY){
  const rows=results.map(r=>'| '+r.file+' | '+r.video.width+'x'+r.video.height+
    ' | '+r.durationSeconds+'s | '+r.audioTracks+' | '+r.rmsSamples+' | '+r.sceneChanges+' |').join('\n');
  fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
    '\n## AutoEditor — verificação com vídeos reais\n\n'+
    '| Vídeo | Resolução | Duração | Faixas de áudio | Amostras RMS | Mudanças de cena (12s) |\n'+
    '|---|---:|---:|---:|---:|---:|\n'+rows+'\n\n'+
    'Previews de Shorts 360x640 no artefato real-media-qa.\n');
}
console.log('PASS: mídias reais analisadas e convertidas para Shorts verticais.');
