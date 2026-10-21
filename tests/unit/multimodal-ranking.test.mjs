import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {parseRmsLog,parseSceneLog,parseSilenceLog,candidateSignalEvidence,normalizedSignals} from '../../src/highlight-signals.js';
import {analyzeLocalMedia} from '../../server/media-analysis.mjs';
import { narrativeQuality,refineShortBoundaries } from '../../src/shorts-boundaries.js';
import {rankShortsFromTranscript} from '../../src/shorts-ranking.js';

test('FFmpeg audio sample log yields a bounded timeline without inventing silence levels',()=>{
  const log=[
    '[Parsed_ametadata_3] frame:0 pts:0 pts_time:0',
    '[Parsed_ametadata_3] lavfi.astats.Overall.RMS_level=-42.2',
    '[Parsed_ametadata_3] frame:1 pts:16000 pts_time:1',
    '[Parsed_ametadata_3] lavfi.astats.Overall.RMS_level=-20.1',
    '[Parsed_ametadata_3] frame:2 pts:32000 pts_time:2',
    '[Parsed_ametadata_3] lavfi.astats.Overall.RMS_level=-inf'
  ].join('\n');
  assert.deepEqual(parseRmsLog(log),[{time:0,db:-42.2},{time:1,db:-20.1}]);
});
test('FFmpeg showinfo timestamps yield sorted scene changes',()=>{
  const s='[Parsed_showinfo_3] n:0 pts:1 pts_time:0.5 duration:1\n'+
    '[Parsed_showinfo_3] n:1 pts:5 pts_time:2.5 duration:1';
  assert.deepEqual(parseSceneLog(s),[.5,2.5]);
});
test('multimodal ranking boosts meaningful loud moments and explains evidence',()=>{
  const cues=[
    {start:0,end:11,text:'Hoje vamos falar sobre um assunto que aconteceu no início de uma apresentação.'},
    {start:16,end:27,text:'Hoje vamos falar sobre um assunto que aconteceu no início de uma apresentação.'}
  ];
  const signals={
    audio:[{time:0,db:-38},{time:1,db:-37},{time:2,db:-39},{time:3,db:-38},{time:4,db:-37},{time:5,db:-39},{time:6,db:-38},{time:7,db:-37},{time:16,db:-18},{time:18,db:-17},{time:19,db:-19}],
    scenes:[17.5,19]
  };
  const base=rankShortsFromTranscript(cues,{duration:30,maxClips:1});
  const ranked=rankShortsFromTranscript(cues,{duration:30,maxClips:1,signals,profile:'gameplay'});
  assert.equal(base.error,null);
  assert.equal(ranked.error,null);
  assert.equal(ranked.candidates[0].start,16);
  assert.equal(ranked.candidates[0].evidence.source,'texto + áudio/vídeo');
  assert.ok(ranked.candidates[0].evidence.audioPeaks>=1);
  assert.ok(ranked.candidates[0].evidence.sceneChanges>=1);
  assert.match(ranked.candidates[0].reason,/Mudanças visuais/);
  assert.equal(normalizedSignals({audio:[{time:-1,db:90}],scenes:[Infinity]}).audio.length,0);
});
test('scene-only video and missing audio do not fabricate loudness peaks',()=>{
  const e=candidateSignalEvidence({audio:[],scenes:[4,5]},2,7,'tutorial');
  assert.equal(e.highEnergy,0);
  assert.equal(e.visualChanges,2);
  assert.equal(e.available,true);
});
test('real FFmpeg runs an offline audio + low-resolution scene analysis',async t=>{
  const check=spawnSync('ffmpeg',['-version'],{encoding:'utf8'});
  if(check.error||check.status!==0)return t.skip('ffmpeg unavailable');
  const temp=fs.mkdtempSync(path.join(os.tmpdir(),'autoeditor-analysis-'));
  try{
    const target=path.join(temp,'source.mp4');
    const made=spawnSync('ffmpeg',['-hide_banner','-loglevel','error',
      '-f','lavfi','-i','color=c=black:s=160x90:r=5:d=2',
      '-f','lavfi','-i','sine=frequency=700:sample_rate=16000:duration=2',
      '-c:v','mpeg4','-c:a','aac','-shortest','-y',target],{timeout:20000});
    assert.equal(made.status,0,made.stderr?.toString());
    const res=await analyzeLocalMedia({source:target,duration:2});
    assert.ok(res.audio.length>=1,'audio RMS should be available');
    assert.equal(res.coverage.audio,true);
    assert.equal(res.coverage.video,true);
    assert.ok(Array.isArray(res.scenes));
  }finally{fs.rmSync(temp,{force:true,recursive:true});}
});

test('silencedetect parser pairs actual intervals and ignores dangling starts',()=>{
  const log=['silence_start: 1.20','silence_end: 1.95 | silence_duration: 0.75','silence_start: 4.20'].join('\n');
  assert.deepEqual(parseSilenceLog(log),[{start:1.2,end:1.95}]);
});
test('narrative quality rejects unfinished speech and rewards clear ending',()=>{
  assert.ok(narrativeQuality('Mas eu pensava nisso','e porque').adjustment<0);
  assert.ok(narrativeQuality('Temos o resultado','Esta é a conclusão!').adjustment>0);
});
test('pauses only pad outside selected speech and never cross adjacent cues',()=>{
  const silences=[
    {start:.55,end:.95},{start:9,end:11.5},
    {start:12.55,end:12.95},{start:23.02,end:23.4}
  ];
  const a=refineShortBoundaries({start:1,end:9,duration:25,signals:{silences},previousEnd:0,nextStart:12});
  assert.ok(a.adjusted&&a.start<1&&a.start>=.55&&a.end>9&&a.end<12);
  const b=refineShortBoundaries({start:13,end:23,duration:26,signals:{silences},previousEnd:9,nextStart:26});
  assert.ok(b.adjusted&&b.start<13&&b.start>=9&&b.end>23&&b.end<=23.4);
  assert.deepEqual(refineShortBoundaries({start:2,end:12,duration:15,signals:{}}),
    {start:2,end:12,adjusted:false});
});
test('ranker preserves subtitles and exposes pause adjustments',()=>{
  const cues=[
    {start:1,end:9,text:'Apresentamos aqui a primeira história com começo e final bem definido para todos.'},
    {start:13,end:23,text:'Agora concluímos outra história de destaque com resposta e resultado muito importante!'}
  ];
  const signals={audio:[],scenes:[],silences:[
    {start:.55,end:.95},{start:9,end:9.35},{start:11.55,end:11.95},{start:22.02,end:22.4}
  ]};
  const ranked=rankShortsFromTranscript(cues,{duration:26,signals,maxClips:2});
  assert.equal(ranked.error,null);
  assert.equal(ranked.candidates.length,2);
  assert.ok(ranked.candidates.some(c=>c.evidence.pauseAdjusted));
  assert.ok(ranked.candidates.every(c=>c.duration<=45));
});
test('real FFmpeg extracts silence intervals from a generated WAV',async t=>{
  const check=spawnSync('ffmpeg',['-version'],{encoding:'utf8'});
  if(check.error||check.status!==0)return t.skip('ffmpeg unavailable');
  const folder=fs.mkdtempSync(path.join(os.tmpdir(),'autoeditor-pause-'));
  try{
    const wav=path.join(folder,'voice.wav');
    const args=['-hide_banner','-loglevel','error',
      '-f','lavfi','-i','aevalsrc=0:s=16000:d=0.8',
      '-f','lavfi','-i','sine=frequency=880:sample_rate=16000:duration=1.2',
      '-f','lavfi','-i','aevalsrc=0:s=16000:d=0.8',
      '-filter_complex','[0:a][1:a][2:a]concat=n=3:v=0:a=1[out]',
      '-map','[out]','-ar','16000','-c:a','pcm_s16le','-y',wav];
    const made=spawnSync('ffmpeg',args,{timeout:20000});
    assert.equal(made.status,0,made.stderr?.toString());
    const signals=await analyzeLocalMedia({source:wav,duration:2.8});
    assert.equal(signals.coverage.audio,true);
    assert.ok(signals.silences.some(x=>x.start<.15&&x.end>.5),'Should find leading silence');
  }finally{fs.rmSync(folder,{recursive:true,force:true});}
});
