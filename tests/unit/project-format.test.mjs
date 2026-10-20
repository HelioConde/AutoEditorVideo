import test from 'node:test';
import assert from 'node:assert/strict';
import { createProjectFile,parseProjectFile,scenesFromScript,validateScenes,PROJECT_SCHEMA } from '../../src/project-format.js';

test('formato portátil abre no desktop e web, sem carregar arquivos físicos',()=>{
  const project=createProjectFile({name:'Minha live',aspect:'16:9',
    media:{originalName:'live.mp4',size:2000,duration:45},
    start:1,end:9,clips:[{start:1,end:4},{start:5,end:9}],
    script:'Olá mundo!',scenes:[{title:'Abertura',text:'Olá mundo!',duration:4}]});
  assert.equal(project.schema,PROJECT_SCHEMA);
  assert.equal(project.media.name,'live.mp4');
  assert.equal(project.media.fileName,undefined);
  assert.equal(project.edit.clips.length,2);
  const opened=parseProjectFile(JSON.parse(JSON.stringify(project)));
  assert.equal(opened.name,'Minha live');assert.equal(opened.aspect,'16:9');
  assert.deepEqual(opened.edit.clips,project.edit.clips);
  assert.equal(opened.edit.scenes[0].title,'Abertura');
});
test('manifest protege contra arquivos antigos e cortes inválidos',()=>{
  const base=createProjectFile({name:'Teste correto',start:0,end:0});
  assert.throws(()=>parseProjectFile({...base,version:99}),/incompatível/);
  assert.throws(()=>parseProjectFile({...base,name:'x'}),/nome/);
  assert.throws(()=>parseProjectFile({...base,media:{name:'x.mp4',duration:3,size:10},
    edit:{...base.edit,clips:[{start:2,end:10}]}}),/dentro/);
  assert.throws(()=>parseProjectFile({...base,edit:{...base.edit,script:'x'.repeat(4001)}}),/Roteiro/);
});
test('roteiro respeita os parágrafos e gera cenas editáveis',()=>{
  const storyboard=scenesFromScript('A primeira fala da apresentação.\n\nAgora o segundo assunto.');
  assert.equal(storyboard.length,2);
  assert.equal(storyboard[0].title,'Cena 1');
  assert.match(storyboard[1].text,/segundo assunto/);
  assert.equal(validateScenes(storyboard).error,null);
});
test('cenas rejeitam textos vazios, títulos e durações impróprias',()=>{
  assert.match(validateScenes([]).error,/1 a 6/);
  assert.match(validateScenes([{text:'oi',duration:3}]).error,/500/);
  assert.match(validateScenes([{text:'Uma boa cena',duration:20}]).error,/15/);
  assert.equal(validateScenes([{text:'Uma boa cena',duration:5}]).error,null);
});

test('temas, transições e motor neural são preservados no formato v1',()=>{
  const scenes=[{title:'Paz',text:'Música e narração',duration:4,theme:'ocean',transition:'cut'}];
  const file=createProjectFile({name:'Meu filme',scenes,script:'Música e narração',voiceEngine:'piper'});
  const reopened=parseProjectFile(file);
  assert.equal(reopened.edit.voiceEngine,'piper');
  assert.equal(reopened.edit.scenes[0].theme,'ocean');
  assert.equal(reopened.edit.scenes[0].transition,'cut');
  assert.throws(()=>parseProjectFile({...file,edit:{...file.edit,voiceEngine:'internet'}}),/Motor de voz/);
  assert.throws(()=>parseProjectFile({...file,edit:{...file.edit,scenes:[{...scenes[0],transition:'explosion'}]}}),/Transição/);
});

test('projetos portáteis incluem legendas SRT e estado opcional do burn-in',()=>{
  const cues=[{start:0,end:2,text:'Legenda em português'}];
  const x=createProjectFile({name:'Teste legenda',subtitles:cues,burnSubtitles:true});
  const parsed=parseProjectFile(x);
  assert.deepEqual(parsed.edit.subtitles,cues);
  assert.equal(parsed.edit.burnSubtitles,true);
  assert.throws(()=>parseProjectFile({...x,edit:{...x.edit,subtitles:[{start:0,end:-1,text:'x'}]}}),/tempos/);
});
