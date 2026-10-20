import { test, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'autoeditor-api-'));
process.env.DATA_DIR = tmp;
const { createApp } = await import('./index.mjs');
const server = createApp().listen(0, '127.0.0.1');
await new Promise(resolve => server.once('listening', resolve));
const origin = 'http://127.0.0.1:' + server.address().port;
after(async () => { await new Promise(resolve => server.close(resolve)); fs.rmSync(tmp,{recursive:true,force:true}); });
async function request(url, body, headers = {}) {
  const response = await fetch(origin + '/api' + url, { method: 'POST', headers: { 'Content-Type': 'application/json', ...headers }, body: JSON.stringify(body) });
  return { status: response.status, data: await response.json() };
}
test('API lista projetos e expõe estado do motor', async () => {
  const response = await fetch(origin + '/api/health');
  assert.equal(response.status, 200);
  const health = await response.json();
  assert.equal(typeof health.ffmpeg, 'boolean');
  const list = await (await fetch(origin + '/api/projects')).json();
  assert.deepEqual(list.projects, []);
});
test('criação persiste e preserva nome do projeto', async () => {
  const created = await request('/projects', { name: '  Teste vídeo  ' });
  assert.equal(created.status, 201);
  assert.equal(created.data.project.name, 'Teste vídeo');
  const all = await (await fetch(origin + '/api/projects')).json();
  assert.equal(all.projects[0].id, created.data.project.id);
});
test('validação impede nomes vazios e projetos inexistentes', async () => {
  assert.equal((await request('/projects', { name: ' ' })).status, 400);
  assert.equal((await request('/projects/inexistente/exports', { start:0,end:1,aspect:'9:16' })).status, 404);
});
test('API recusa origem cruzada em operações de escrita', async () => {
  assert.equal((await request('/projects', { name:'Não deve criar' }, { Origin:'https://site-externo.example' })).status, 403);
});
test('API não permite exportação sem mídia', async () => {
  const created = await request('/projects', { name:'Sem mídia' });
  const response = await request('/projects/' + created.data.project.id + '/exports', { start:0,end:1,aspect:'9:16' });
  assert.equal(response.status, 400);
});

test('importa edição portável sem exigir o vídeo original', async () => {
  const data={schema:'autoeditor.project',version:1,name:'História portável',aspect:'9:16',
    media:{name:'original.mp4',size:4000,duration:12},
    edit:{start:1,end:3,clips:[{start:1,end:3}],script:'Era uma vez.',
      scenes:[{title:'Abertura',text:'Era uma vez.',duration:3}]}};
  const imported=await request('/projects/import',data);
  assert.equal(imported.status,201);
  assert.equal(imported.data.project.media,null);
  assert.equal(imported.data.project.reference.name,'original.mp4');
  assert.equal(imported.data.project.edit.scenes[0].text,'Era uma vez.');
  const id=imported.data.project.id;
  const save=await fetch(origin+'/api/projects/'+id+'/edit',{method:'PUT',
    headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  assert.equal(save.status,200);
  const found=await(await fetch(origin+'/api/projects')).json();
  const project=found.projects.find(p=>p.id===id);
  assert.equal(project.edit.clips.length,1);
});
test('rejeita JSON de projeto fora do formato e imagens arbitrárias',async()=>{
  assert.equal((await request('/projects/import',{schema:'wrong',version:1})).status,400);
  const created=await request('/projects',{name:'Roteiro QA'});
  const id=created.data.project.id;
  const response=await request('/projects/'+id+'/narration',{scenes:[],images:[],aspect:'9:16'});
  assert.ok([400,503].includes(response.status));
});
