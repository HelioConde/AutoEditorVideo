// Test the shipped TypeScript motion code, not a JS reimplementation.
// No media, AI generation, browser or paid assets are required.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const ts=require('typescript');

function load(relative) {
  const source=fs.readFileSync(path.join(__dirname,'../src',relative),'utf8');
  const transpiled=ts.transpileModule(source,{
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}
  }).outputText;
  const mod={exports:{}};
  new Function('module','exports',transpiled)(mod,mod.exports);
  return {exports:mod.exports,source};
}
const {exports:engine,source}=load('character-idle.ts');
const {characterPoseAtFrame, presetNames}=engine;
const camera=load('cinematic-motion.ts').exports;

const input=(overrides={})=>({
  role:'back_character',id:'uma personagem qualquer',
  coverage:.19,contactRisk:.07,heroRisk:0,
  heightFraction:.6,motionSeed:4123457,
  frame:66,sceneStart:0,sceneEnd:150,fps:30,
  preset:'ultrassutil',enabled:true,...overrides
});
const poses=(options={})=>Array.from({length:151},(_,frame)=>
  characterPoseAtFrame(input({...options,frame})));
const peak=(p,k)=>Math.max(...p.map(x=>Math.abs(x[k])));

test('unlimited arbitrary character names and unicode, no named Light/L rules',()=>{
  for(const id of ['Personagem_99','hero_番','uma pessoa qualquer','L','Light']){
    const pose=characterPoseAtFrame(input({id}));
    assert.equal(pose.reason,'safe');
    assert.equal(pose.enabled,true);
  }
  assert.ok(!source.includes("id==='light'"));
  assert.ok(!source.includes("id==='l'"));
  assert.deepEqual(presetNames,['ultrassutil','equilibrado','vivo']);
});

test('first and last frame exactly preserve approved pixels',()=>{
  for(const frame of [0,150,151]){
    const pose=characterPoseAtFrame(input({frame}));
    assert.equal(pose.translateX,0);
    assert.equal(pose.translateY,0);
    assert.equal(pose.rotateDeg,0);
    assert.equal(pose.scaleX,1);
    assert.equal(pose.scaleY,1);
  }
});

test('no stretching of face, torso or arms at ANY time',()=>{
  for(const preset of presetNames){
    for(const pose of poses({preset})){
      assert.equal(pose.scaleX,1);
      assert.equal(pose.scaleY,1);
      assert.ok(Math.abs(pose.translateX)<=3.200001);
      assert.ok(Math.abs(pose.translateY)<=11.800001);
      assert.ok(Math.abs(pose.rotateDeg)<=.380001);
    }
  }
});

test('high furniture contact dampens movement without making it random',()=>{
  const free=poses({contactRisk:0});
  const contacting=poses({contactRisk:.40});
  assert.ok(peak(free,'translateY')>peak(contacting,'translateY')*1.4);
  assert.ok(peak(contacting,'translateY')>0);
});

test('hero overlap freezes ONLY the attached person, not everybody in scene',()=>{
  const attached=characterPoseAtFrame(input({heroRisk:.12,hasHeroProp:true}));
  const bystander=characterPoseAtFrame(input({
    heroRisk:0,hasHeroProp:true,id:'outro personagem',motionSeed:43
  }));
  assert.equal(attached.reason,'hero-protected');
  assert.equal(attached.enabled,false);
  assert.equal(bystander.reason,'safe');
  assert.equal(bystander.enabled,true);
  // Legacy manifests without collision metadata stay conservative.
  assert.equal(characterPoseAtFrame(input({
    heroRisk:undefined,hasHeroProp:true
  })).reason,'hero-protected');
});

test('camera choreography uses shot semantics, not Death Note scene indexes',()=>{
  assert.equal(camera.profileForShot('wide_intro','79'),'establish');
  assert.equal(camera.profileForShot('portrait_reaction','19'),'reaction');
  assert.equal(camera.profileForShot('hand_detail','302'),'king');
  assert.equal(camera.profileForShot('dialogue_over_shoulder','ABC'),'duel');
  assert.equal(camera.profileForShot('endcard','last'),'final');
  assert.equal(camera.profileForShot('unknown','01'),
               camera.profileForShot('unknown','06'));
});

test('harmonics vary across characters/videos, no repetition of same fixed phase',()=>{
  const a=poses({id:'a',motionSeed:4242});
  const b=poses({id:'b',motionSeed:67890});
  assert.deepEqual(a,poses({id:'a',motionSeed:4242}));
  assert.notDeepEqual(a.map(p=>p.translateY),b.map(p=>p.translateY));
  assert.ok(peak(a,'translateY')>0.20);
  assert.ok(peak(b,'translateY')>0.20);
  assert.ok(!source.includes('Math.random('));
  assert.ok(!source.includes('Date.now('));
});

test('duration and defensive validation, no invalid transforms',()=>{
  for(const options of [
    {role:'object'}, {role:'hero_prop'}, {role:'occluder'},
    {coverage:.9},{coverage:.001},
    {fps:0},{frame:NaN},{sceneEnd:0},{enabled:false},
  ]){
    const pose=characterPoseAtFrame(input(options));
    assert.equal(pose.enabled,false);
    assert.equal(pose.scaleX,1);
    assert.equal(pose.scaleY,1);
  }
});

test('settings change amplitude but do not change source art or character identity',()=>{
  const peaks=presetNames.map(preset=>peak(poses({preset}),'translateY'));
  assert.ok(peaks[0]<peaks[1]);
  assert.ok(peaks[1]<peaks[2]);
  assert.ok(peaks[1]>=peaks[0]*1.5, 'normal character idle must be visibly stronger');
  assert.ok(poses({preset:'ultrassutil'}).every(x=>x.scaleY===1));
});
