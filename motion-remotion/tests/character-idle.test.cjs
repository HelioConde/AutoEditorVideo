// Test the actual TypeScript motion engine without producing paid images.
// Run inside motion-remotion after npm install: node --test tests/character-idle.test.cjs
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const ts=require('typescript');

const target=path.join(__dirname,'../src/character-idle.ts');
const source=fs.readFileSync(target,'utf8');
const transpiled=ts.transpileModule(source,{
  compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}
}).outputText;
const mod={exports:{}};
new Function('module','exports',transpiled)(mod,mod.exports);
const {characterPoseAtFrame,presetNames}=mod.exports;
const input=(overrides={})=>({
  role:'back_character',id:'l',coverage:.21,hasHeroProp:false,
  frame:65,sceneStart:0,sceneEnd:150,fps:30,
  preset:'equilibrado',enabled:true,...overrides
});

test('three presets are available and deterministic',()=>{
  assert.deepEqual(presetNames,['ultrassutil','equilibrado','vivo']);
  assert.deepEqual(characterPoseAtFrame(input()),characterPoseAtFrame(input()));
});
test('first and last frame exactly match approved preview',()=>{
  for (const frame of [0,150]){
    const pose=characterPoseAtFrame(input({frame,preset:'vivo'}));
    assert.equal(pose.translateX,0);
    assert.ok(Math.abs(pose.translateY)<1e-14);
    assert.ok(Math.abs(pose.rotateDeg)<1e-14);
    assert.equal(pose.scaleX,1);
    assert.equal(pose.scaleY,1);
  }
});
test('movement is subpixel, no clipping-sized transforms',()=>{
  for (const preset of presetNames){
    for (const id of ['light','l']){
      for (let frame=0;frame<=150;frame+=3){
        const pose=characterPoseAtFrame(input({frame,id,preset}));
        assert.equal(pose.reason,'safe');
        assert.ok(Math.abs(pose.translateX)<=.300001);
        assert.ok(Math.abs(pose.translateY)<=1.250001);
        assert.ok(Math.abs(pose.rotateDeg)<=.150001);
        assert.ok(Math.abs(pose.scaleX-1)<=.000601);
        assert.ok(Math.abs(pose.scaleY-1)<=.001001);
      }
    }
  }
});
test('hero prop and non character roles do NOT move separately',()=>{
  for (const changes of [
    {hasHeroProp:true},{role:'occluder'}, {role:'object'},
    {role:'hero_prop'}, {coverage:0.8}, {coverage:0.001},
    {enabled:false}
  ]){
    const pose=characterPoseAtFrame(input(changes));
    assert.equal(pose.enabled,false);
    assert.equal(pose.translateY,0);
    assert.equal(pose.rotateDeg,0);
  }
});
test('distinct Light and L breaths; L stronger than Light',()=>{
  const light=characterPoseAtFrame(input({id:'light',frame:42}));
  const l=characterPoseAtFrame(input({id:'l',frame:42}));
  assert.notEqual(light.translateY,l.translateY);
  let amplitudeL=0, amplitudeLight=0;
  for(let f=10;f<150;f++){
    amplitudeL=Math.max(amplitudeL,Math.abs(characterPoseAtFrame(input({frame:f,id:'l'})).translateY));
    amplitudeLight=Math.max(amplitudeLight,Math.abs(characterPoseAtFrame(input({frame:f,id:'light'})).translateY));
  }
  assert.ok(amplitudeL>amplitudeLight);
});
test('vivo stronger than ultrassutil across scene',()=>{
  const peaks={};
  for(const preset of presetNames){
    peaks[preset]=0;
    for(let frame=0;frame<=150;frame++){
      const pose=characterPoseAtFrame(input({preset,frame}));
      peaks[preset]=Math.max(peaks[preset],Math.abs(pose.translateY));
    }
  }
  assert.ok(peaks.ultrassutil<peaks.equilibrado);
  assert.ok(peaks.equilibrado<peaks.vivo);
});
test('scene frame duration controls envelope without globals/random',()=>{
  assert.equal(source.includes('Math.random('),false);
  assert.equal(source.includes('Date.now('),false);
  assert.equal(characterPoseAtFrame(input({fps:0})).enabled,false);
  assert.equal(characterPoseAtFrame(input({frame:Number.NaN})).enabled,false);
});
