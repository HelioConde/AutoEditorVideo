import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeClips, insertClip, moveClip, MAX_CLIPS } from '../../src/clip-utils.js';

test('mantém compatibilidade com recorte único', () => {
  const plan = normalizeClips({ start:0.5,end:2.5,duration:10 });
  assert.equal(plan.error, null);
  assert.equal(plan.total, 2);
  assert.deepEqual(plan.clips, [{ start:0.5,end:2.5 }]);
});

test('valida e organiza vários cortes preservando a ordem', () => {
  const plan = normalizeClips({ segments:[{start:4,end:5.2},{start:0,end:1}], duration:6,maxTotal:4 });
  assert.equal(plan.error,null);
  assert.equal(plan.clips.length,2);
  assert.equal(plan.total,2.2);
  const reordered=moveClip(plan.clips,1,-1);
  assert.deepEqual(reordered.map(x=>x.start),[0,4]);
  assert.deepEqual(plan.clips.map(x=>x.start),[4,0]);
});

test('rejeita cortes inválidos e limita a duração total', () => {
  assert.match(normalizeClips({ segments:[],duration:10 }).error,/entre 1/);
  assert.match(normalizeClips({ segments:[{start:1,end:1.1}],duration:10 }).error,/0,25/);
  assert.match(normalizeClips({ segments:[{start:2,end:11}],duration:10 }).error,/dentro/);
  assert.match(normalizeClips({ segments:[{start:0,end:2},{start:4,end:7}],duration:10,maxTotal:4 }).error,/total/);
  assert.match(normalizeClips({ segments:Array.from({length:6},(_,i)=>({start:i,end:i+.5})),duration:10 }).error,/entre 1/);
  assert.match(normalizeClips({ segments:[{start:null,end:2}],duration:10 }).error,/válidos/);
});

test('fila permite até cinco cortes e operações de ordenação são puras',()=>{
  const original=[{start:0,end:1}];
  const second=insertClip(original,{start:2,end:3});
  assert.equal(second.length,2);assert.equal(original.length,1);
  assert.equal(moveClip(second,0,-1),second);
  assert.equal(insertClip(Array.from({length:MAX_CLIPS},()=>({start:0,end:1})),{start:1,end:2}).length,MAX_CLIPS);
});
