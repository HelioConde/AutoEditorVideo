// Runs shipped TypeScript logic through TypeScript transpilation, no media/AI.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const ts=require('typescript');

function load(relative) {
  const source=fs.readFileSync(path.join(__dirname,'../src',relative),'utf8');
  const js=ts.transpileModule(source,{
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}
  }).outputText;
  const module={exports:{}};
  new Function('module','exports',js)(module,module.exports);
  return {exports:module.exports,source};
}
const opening=load('cinematic-motion.ts').exports.openingCutAtFrame;
const captions=load('caption-pacing.ts').exports.groupLegacyCaptionWords;
const master=fs.readFileSync(path.join(__dirname,'../src/master-short.tsx'),'utf8');
const legacy=fs.readFileSync(path.join(__dirname,'../src/short.tsx'),'utf8');

test('first five seconds have obvious camera cuts without fabricated body movement',()=>{
  const fps=30;
  const initial=opening(0,fps,'cinematica');
  assert.deepEqual(initial,{zoom:0,panX:0,panY:0,beat:0});
  const early=opening(30,fps,'cinematica');
  assert.ok(early.zoom>.02);
  const beforeFirst=opening(37,fps,'cinematica');
  const firstCut=opening(38,fps,'cinematica');
  assert.ok(firstCut.zoom-beforeFirst.zoom>.02);
  assert.equal(firstCut.beat,1);
  const beforeSecond=opening(73,fps,'cinematica');
  const secondCut=opening(74,fps,'cinematica');
  assert.ok(beforeSecond.zoom-secondCut.zoom>.03);
  assert.equal(secondCut.beat,2);
  assert.equal(opening(150,fps,'cinematica').zoom,0);
  assert.equal(opening(150,fps,'cinematica').beat,-1);
  for(let f=0;f<151;f++){
    const shot=opening(f,fps,'cinematica');
    assert.ok(Number.isFinite(shot.zoom) && shot.zoom>=0 && shot.zoom<=.09);
    assert.ok(Math.abs(shot.panX)<=24.01);
    assert.ok(Math.abs(shot.panY)<=16.01);
  }
});

test('disabled or skeletal modes never add virtual cuts',()=>{
  for(const mode of ['desligada','esqueleto2d']){
    assert.deepEqual(opening(45,30,mode),{zoom:0,panX:0,panY:0,beat:-1});
  }
  assert.equal(opening(Number.NaN,30,'cinematica').zoom,0);
  assert.equal(opening(45,0,'cinematica').zoom,0);
});

test('legacy per-word captions become three-word phrases with real timing',()=>{
  const words=['Misa','estava','atrás','do','único','Kira'];
  const inputs=words.map((text,i)=>({
    text,startFrame:i*9,endFrame:i*9+7
  }));
  const grouped=captions(inputs,30);
  assert.equal(grouped.length,2);
  assert.equal(grouped[0].text,'Misa estava atrás');
  assert.equal(grouped[1].text,'do único Kira');
  assert.deepEqual(grouped[0].words.map(w=>w.startFrame),[0,9,18]);
  assert.equal(grouped[1].endFrame,52);
});

test('word breaks preserve punctuation, long gaps, and existing phrases',()=>{
  const input=[
    {text:'Quem?',startFrame:0,endFrame:8},
    {text:'Ele',startFrame:9,endFrame:16},
    {text:'mentiu.',startFrame:17,endFrame:24},
    {text:'Depois',startFrame:50,endFrame:60},
    {text:'Misa e Light',startFrame:61,endFrame:84}
  ];
  const grouped=captions(input,30);
  assert.deepEqual(grouped.map(g=>g.text),
    ['Quem?','Ele mentiu.','Depois','Misa e Light']);
  assert.equal(grouped[3].words,undefined);
});

test('both renderers consume opening cuts and keep captions off the face',()=>{
  assert.ok(master.includes('openingCutAtFrame(frame,fps,mode)'));
  assert.ok(legacy.includes("openingCutAtFrame(frame,fps,'cinematica')"));
  assert.ok(master.includes("safeZoom=Math.min(1.14"));
  assert.ok(legacy.includes("background:'rgba(2,5,15,.86)'"));
  assert.ok(master.includes("background:'rgba(2,5,15,.85)'"));
  assert.ok(master.includes('top:1258') && legacy.includes('top:1280'));
});
