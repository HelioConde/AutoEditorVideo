import test from 'node:test';
import assert from 'node:assert/strict';
import { nudgeBoundary, replaceClip, zoomWindow } from '../../src/clip-utils.js';

test('precisão centesimal sem perder o intervalo mínimo de 0,25 s',()=>{
  assert.deepEqual(nudgeBoundary({start:1,end:2,duration:8,boundary:'start',delta:.01}),{start:1.01,end:2});
  assert.deepEqual(nudgeBoundary({start:1,end:2,duration:8,boundary:'end',delta:-.01}),{start:1,end:1.99});
  assert.deepEqual(nudgeBoundary({start:1,end:1.25,duration:8,boundary:'start',delta:10}),{start:1,end:1.25});
  assert.deepEqual(nudgeBoundary({start:1,end:1.25,duration:8,boundary:'end',delta:-10}),{start:1,end:1.25});
  assert.deepEqual(nudgeBoundary({start:0,end:1,duration:2,boundary:'start',delta:-2}),{start:0,end:1});
  assert.deepEqual(nudgeBoundary({start:1,end:2,duration:2,boundary:'end',delta:9}),{start:1,end:2});
});
test('substituir trecho preserva ordem e limite total',()=>{
  const q=[{start:0,end:.5},{start:1,end:1.5}];
  const result=replaceClip(q,0,{start:.1,end:.65},{duration:2,maxTotal:2,maxEach:2});
  assert.equal(result.error,null);
  assert.deepEqual(result.clips,[{start:.1,end:.65},{start:1,end:1.5}]);
  assert.deepEqual(q,[{start:0,end:.5},{start:1,end:1.5}]);
  assert.match(replaceClip(q,0,{start:0,end:1},{duration:2,maxTotal:1}).error,/limite total/);
  assert.match(replaceClip(q,3,{start:0,end:1},{duration:2}).error,/não encontrado/);
});
test('zoom centralizado e dentro dos limites da fonte',()=>{
  assert.deepEqual(zoomWindow({duration:16,start:7,end:9,zoom:4}),{min:6,max:10});
  assert.deepEqual(zoomWindow({duration:16,start:0,end:1,zoom:8}),{min:0,max:2});
  assert.deepEqual(zoomWindow({duration:16,start:15,end:16,zoom:8}),{min:14,max:16});
  assert.deepEqual(zoomWindow({duration:16,start:7,end:9,zoom:1}),{min:0,max:16});
});
