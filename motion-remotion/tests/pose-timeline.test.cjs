// Execute the real TypeScript pose timeline without rendering any images/video.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const ts=require('typescript');
const source=fs.readFileSync(path.join(__dirname,'../src/pose-timeline.ts'),'utf8');
const output=ts.transpileModule(source,{
  compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}
}).outputText;
const exportsModule={exports:{}};
new Function('module','exports',output)(exportsModule,exportsModule.exports);
const {poseFrameIndex}=exportsModule.exports;
const at=(frame,playback='pingpong',extras={})=>
  poseFrameIndex({frame,sceneStart:0,compositionFps:30,rigFps:5,
    frameCount:3,playback,...extras});

test('pingpong sequence reverses rather than snapping from last to first',()=>{
  const frames=[0,6,12,18,24,30,36,42,48].map(f=>at(f));
  assert.deepEqual(frames,[0,1,2,1,0,1,2,1,0]);
  for(let i=1;i<frames.length;i++){
    assert.ok(Math.abs(frames[i]-frames[i-1])<=1);
  }
});
test('once playback holds last pose rather than looping',()=>{
  assert.deepEqual([0,6,12,18,24,120].map(f=>at(f,'once')),[0,1,2,2,2,2]);
});
test('explicit loop mode supports artist approved repeating loops',()=>{
  assert.deepEqual([0,6,12,18,24].map(f=>at(f,'loop')),[0,1,2,0,1]);
});
test('bad clocks, empty art and negative frames cannot produce invalid index',()=>{
  for(const args of [
    {frameCount:0},{rigFps:0},{compositionFps:0},
    {frame:NaN},{frameCount:Infinity}
  ])assert.equal(at(10,'pingpong',args),0);
  assert.equal(at(-45),0);
});
test('master uses the compiled helper for real posed layers',()=>{
  const master=fs.readFileSync(path.join(__dirname,'../src/master-short.tsx'),'utf8');
  assert.ok(master.includes("import {RigPlayback,poseFrameIndex} from './pose-timeline'"));
  assert.ok(master.includes("frameCount:rig.frames.length,playback:rig.playback"));
  assert.ok(!master.includes(")%rig.frames.length"));
});
