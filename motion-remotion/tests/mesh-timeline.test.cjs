const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const ts=require('typescript');

const src=fs.readFileSync(path.join(__dirname,'../src/pose-timeline.ts'),'utf8');
const code=ts.transpileModule(src,{compilerOptions:{
  module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020
}}).outputText;
const result={exports:{}};
new Function('module','exports',code)(result,result.exports);
const {meshFrameIndex}=result.exports;
const at=(frame,overrides={})=>meshFrameIndex({
  frame,sceneStart:0,compositionFps:30,meshFps:15,
  frameCount:120,...overrides
});
test('V7 renders 120 unique original mesh frames in exact order at 15fps',()=>{
  assert.deepEqual([0,1,2,3,4,60,238,239].map(x=>at(x)),
    [0,0,1,1,2,30,119,119]);
  let last=0;
  for(let f=0;f<240;f++){
    const index=at(f);
    assert.ok(index>=last && index-last<=1);
    last=index;
  }
});
test('V7 never renders out-of-range image indices',()=>{
  for(const opts of [
    {meshFps:0},{meshFps:-4},{frameCount:0},
    {frameCount:901},{compositionFps:NaN}
  ])assert.equal(at(100,opts),0);
  assert.equal(at(-100),0);
  assert.equal(at(9999),119);
});
test('mesh rendering is one image, never alpha crossfade',()=>{
  const src=fs.readFileSync(path.join(__dirname,'../src/master-short.tsx'),'utf8');
  assert.ok(src.includes('mesh.frames[index]'));
  assert.ok(src.includes("mode==='malha2d'?layer.meshFrames"));
  assert.ok(src.includes('return <Img key={layer.id}'));
});
