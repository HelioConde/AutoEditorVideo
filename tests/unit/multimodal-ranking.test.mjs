import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {parseRmsLog,parseSceneLog,candidateSignalEvidence,normalizedSignals} from '../../src/highlight-signals.js';
import {analyzeLocalMedia} from '../../server/media-analysis.mjs';
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
  const ranked=rankShortsFromTranscript(cues,{duration:25,maxClips:1,signals,profile:'gameplay'});
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
