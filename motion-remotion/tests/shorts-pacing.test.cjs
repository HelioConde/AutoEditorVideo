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
const camera=load('cinematic-motion.ts').exports;
const opening=camera.openingCutAtFrame;
const hold=camera.longHoldCutAtFrame;
const captions=load('caption-pacing.ts').exports.groupLegacyCaptionWords;
const master=fs.readFileSync(path.join(__dirname,'../src/master-short.tsx'),'utf8');
const legacy=fs.readFileSync(path.join(__dirname,'../src/short.tsx'),'utf8');

test('opening camera is continuous, centered and visibly zooms in/out',()=>{
  const fps=30;
  assert.deepEqual(opening(0,fps,'cinematica'),
    {zoom:0,panX:0,panY:0,beat:0});
  assert.ok(opening(30,fps,'cinematica').zoom>.01);
  assert.ok(opening(75,fps,'cinematica').zoom>.035);
  assert.ok(opening(120,fps,'cinematica').zoom>.01);
  assert.equal(opening(150,fps,'cinematica').zoom,0);
  let previous=opening(0,fps,'cinematica');
  for(let f=1;f<=151;f++){
    const now=opening(f,fps,'cinematica');
    assert.ok(Math.abs(now.zoom-previous.zoom)<.001);
    assert.equal(now.panX,0);
    assert.equal(now.panY,0);
    previous=now;
  }
});

test('long holds breathe without a single abrupt camera reposition',()=>{
  const fps=30;
  const duration=450;
  assert.equal(hold(120,0,duration,fps,'cinematica').zoom,0);
  assert.equal(hold(150,0,duration,fps,'cinematica').zoom,0);
  assert.ok(hold(205,0,duration,fps,'cinematica').zoom>.008);
  assert.equal(hold(duration,0,duration,fps,'cinematica').zoom,0);
  for(const sceneStart of [0,180]){
    let previous=hold(sceneStart,sceneStart,duration,fps,'cinematica');
    for(let f=sceneStart+1;f<=duration;f++){
      const now=hold(f,sceneStart,duration,fps,'cinematica');
      assert.ok(Math.abs(now.zoom-previous.zoom)<.003,
        'Unexpected jump at frame '+f+' for start '+sceneStart);
      assert.equal(now.panX,0);
      assert.equal(now.panY,0);
      previous=now;
    }
  }
});

test('camera zoom helper is disabled with motion off or skeletal art',()=>{
  for(const mode of ['desligada','esqueleto2d']){
    assert.deepEqual(opening(45,30,mode),{zoom:0,panX:0,panY:0,beat:-1});
    assert.deepEqual(hold(201,0,450,30,mode),{zoom:0,panX:0,panY:0,beat:-1});
  }
  assert.equal(opening(NaN,30,'cinematica').zoom,0);
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
  assert.ok(master.includes('longHoldCutAtFrame(frame,scene.startFrame,scene.endFrame,fps,mode)'));
  assert.ok(legacy.includes('longHoldCutAtFrame(frame,0,props.durationFrames,fps'));
  assert.ok(legacy.includes("openingCutAtFrame(frame,fps,'cinematica')"));
  assert.ok(master.includes("safeZoom=Math.min(1.115"));
  assert.ok(legacy.includes("background:'rgba(2,5,15,.86)'"));
  assert.ok(master.includes("background:'rgba(2,5,15,.85)'"));
  // V6 moves captions into the mobile-safe zone, while all legacy
  // compositions retain their exact historic caption baseline.
  assert.ok(master.includes("top:visualProfile==='otaku-v6-vertical'?1360:1258"));
  assert.ok(legacy.includes('top:1280'));
  assert.ok(master.includes("left:visualProfile==='otaku-v6-vertical'?116:78"));
  assert.ok(master.includes("fontSize:visualProfile==='otaku-v6-vertical'?65:79"));
});
