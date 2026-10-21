import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {parseMotionLog,candidateSignalEvidence,motionBurstMoments} from '../../src/highlight-signals.js';
import {rankVisualShorts,rankAutomaticShorts} from '../../src/visual-highlights.js';
import {analyzeLocalMedia} from '../../server/media-analysis.mjs';

test('motion parser returns exact YDIF samples and ignores invalid frames',()=>{
  const log=[
    'frame:0 pts:0 pts_time:0','lavfi.signalstats.YDIF=0',
    'frame:1 pts:1 pts_time:0.5','lavfi.signalstats.YDIF=11.357',
    'frame:2 pts:2 pts_time:1','lavfi.signalstats.YDIF=2500'
  ].join('\n');
  assert.deepEqual(parseMotionLog(log),[{time:0,value:0},{time:.5,value:11.36}]);
});
test('static sources and unavailable motion do not invent visual highlights',()=>{
  const staticFrames=Array.from({length:40},(_,i)=>({time:i*.5,value:0}));
  assert.match(rankVisualShorts({motion:staticFrames},{duration:20}).error,/movimento contínuo/);
  assert.match(rankVisualShorts({motion:[]},{duration:20}).error,/quadros analisados/);
  assert.match(rankAutomaticShorts([],{duration:20,signals:{motion:staticFrames}}).error,/movimento contínuo/);
  assert.match(rankVisualShorts({motion:staticFrames},{duration:7}).error,/8 segundos/);
});
test('visual activity yields reviewable non-overlapping silent Shorts, never captions',()=>{
  const movement=Array.from({length:78},(_,i)=>({time:i*.5,value:i<2?0:12+((i%7)*.5)}));
  const found=rankAutomaticShorts([],{duration:39,signals:{motion:movement,scenes:[7,17,29]},profile:'gameplay'});
  assert.equal(found.error,null);
  assert.ok(found.candidates.length>=2);
  assert.ok(found.candidates.length<=3);
  for(const candidate of found.candidates){
    assert.equal(candidate.captionsAvailable,false);
    assert.ok(candidate.duration>=8 && candidate.duration<=45);
    assert.match(candidate.evidence.source,/sem transcrição/);
    assert.ok(candidate.score>0);
  }
  for(const [i,a] of found.candidates.entries())
    for(const b of found.candidates.slice(i+1))
      assert.ok(a.end+1<=b.start||b.end+1<=a.start);
  const evidence=candidateSignalEvidence({motion:movement},0,12,'gameplay');
  assert.ok(evidence.motionActivity>0);
});
test('transcript priority remains when SRT exists',()=>{
  const cues=[{start:0,end:10,text:'Mas como encontramos uma descoberta incrível que mudou o jogo e surpreendeu toda a equipe?'}];
  const signals={motion:Array.from({length:28},(_,i)=>({time:i*.5,value:15}))};
  const ranked=rankAutomaticShorts(cues,{duration:14,signals,profile:'gameplay'});
  assert.equal(ranked.error,null);
  assert.match(ranked.candidates[0].reason,/curiosidade|destaque|Contraste/iu);
  assert.notEqual(ranked.candidates[0].captionsAvailable,false);
});
test('real FFmpeg detects motion on a video without sound',async t=>{
  const check=spawnSync('ffmpeg',['-version'],{encoding:'utf8'});
  if(check.error||check.status!==0)return t.skip('ffmpeg unavailable');
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'silent-shorts-'));
  try{
    const video=path.join(dir,'moving.mp4');
    const make=spawnSync('ffmpeg',['-hide_banner','-loglevel','error','-f','lavfi','-i',
      'testsrc2=size=160x90:rate=5:duration=13','-an','-c:v','mpeg4','-y',video],
      {timeout:30000,encoding:'utf8'});
    assert.equal(make.status,0,make.stderr);
    const signals=await analyzeLocalMedia({source:video,duration:13});
    assert.equal(signals.coverage.motion,true);
    assert.ok(signals.motion.length>=16);
    assert.ok(signals.motion.some(x=>x.value>2));
    const ranked=rankVisualShorts(signals,{duration:13,profile:'gameplay'});
    assert.equal(ranked.error,null);
    assert.equal(ranked.candidates.length,1);
  }finally{fs.rmSync(dir,{recursive:true,force:true});}
});

test('sustained action bursts outrank steady background motion',()=>{
  const motion=Array.from({length:120},(_,i)=>{
    const time=i*.5;
    const event=(time>=32&&time<34)||(time>=36&&time<38);
    return {time,value:event?30:6};
  });
  const events=motionBurstMoments({motion});
  assert.equal(events.length,2);
  const ranked=rankVisualShorts({motion},{duration:60,maxClips:3,profile:'gameplay'});
  assert.equal(ranked.error,null);
  assert.ok(ranked.candidates[0].start<=33&&ranked.candidates[0].end>=37,
    'o Short mais bem pontuado deve conter a ação e contexto ao redor');
  assert.ok(ranked.candidates[0].evidence.motionBursts>=1);
  assert.match(ranked.candidates[0].reason,/Picos de movimento sustentados/);
});
test('steady gameplay footage and a single-frame flash do not invent events',()=>{
  const uniform=Array.from({length:80},(_,i)=>({time:i*.5,value:12}));
  assert.deepEqual(motionBurstMoments({motion:uniform}),[]);
  const flash=uniform.map((x,i)=>i===32?{...x,value:72}:x);
  assert.deepEqual(motionBurstMoments({motion:flash}),[]);
  const invalid=[{time:-1,value:250},{time:4,value:NaN}];
  assert.deepEqual(motionBurstMoments({motion:invalid}),[]);
});
