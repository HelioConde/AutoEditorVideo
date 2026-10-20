import test from 'node:test';
import assert from 'node:assert/strict';
import { WEB_DRAFT_KEY, loadWebDraft, saveWebDraft, clearWebDraft } from '../../src/web-draft.js';

function storage() {
  const entries=new Map();
  return {getItem:key=>entries.get(key)||null,setItem:(key,value)=>entries.set(key,value),
    removeItem:key=>entries.delete(key), entries};
}
test('rascunho web persiste somente manifesto portátil, não mídia física',()=>{
  const cache=storage();
  const input={name:'Meu vídeo',media:{name:'clip.mp4',size:1280,duration:10},
    start:1,end:3,clips:[{start:1,end:3}],script:'Cena de teste',
    scenes:[{title:'Intro',text:'Cena de teste',duration:4}],subtitles:[{start:1,end:2,text:'Olá'}],
    aspect:'16:9',voiceEngine:'system',burnSubtitles:false};
  assert.equal(saveWebDraft(cache,input),true);
  const serialized=cache.getItem(WEB_DRAFT_KEY);
  assert.ok(!serialized.includes('data:image')&&!serialized.includes('fileName'));
  const restored=loadWebDraft(cache);
  assert.equal(restored.project.name,'Meu vídeo');
  assert.deepEqual(restored.project.edit.clips,input.clips);
  assert.equal(restored.project.edit.subtitles[0].text,'Olá');
  assert.deepEqual(restored.project.media,{name:'clip.mp4',size:1280,duration:10});
});
test('arquivo inválido não destrói último rascunho bom',()=>{
  const cache=storage();
  assert.equal(saveWebDraft(cache,{name:'Projeto válido'}),true);
  const prior=cache.getItem(WEB_DRAFT_KEY);
  assert.equal(saveWebDraft(cache,{name:'Projeto válido',subtitles:[{start:1,end:0,text:'Falha'}]}),false);
  assert.equal(cache.getItem(WEB_DRAFT_KEY),prior);
  cache.setItem(WEB_DRAFT_KEY,'{invalido');
  assert.equal(loadWebDraft(cache),null);
  clearWebDraft(cache);
  assert.equal(cache.getItem(WEB_DRAFT_KEY),null);
});
test('armazenamento bloqueado falha sem derrubar o editor',()=>{
  const cache={getItem(){throw Error('bloqueado')},setItem(){throw Error('bloqueado')},removeItem(){throw Error('bloqueado')}};
  assert.equal(loadWebDraft(cache),null);
  assert.equal(saveWebDraft(cache,{name:'Projeto'}),false);
  assert.equal(clearWebDraft(cache),false);
});
