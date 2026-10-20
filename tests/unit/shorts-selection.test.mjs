import test from 'node:test';
import assert from 'node:assert/strict';
import { selectApprovedShorts } from '../../src/shorts-selection.js';

const candidates=[
 {start:2,end:17,score:80,title:'Destaque A'},
 {start:25,end:40,score:70,title:'Destaque B'},
 {start:55,end:69,score:60,title:'Destaque C'}
];
test('approval exports only candidates explicitly reviewed',()=>{
 const selection=selectApprovedShorts(candidates,[{start:25,end:40},{start:55,end:69}]);
 assert.equal(selection.error,null);
 assert.deepEqual(selection.candidates,[candidates[1],candidates[2]]);
 assert.deepEqual(selectApprovedShorts(candidates).candidates,candidates);
});
test('rejects stale, duplicated, empty and arbitrary ranges',()=>{
 for(const selected of [
   [],[{start:22,end:38}],[{start:2,end:17},{start:2,end:17}],
   [{start:2,end:170}],['2:17']
 ]){
   const result=selectApprovedShorts(candidates,selected);
   assert.equal(result.candidates.length,0);
   assert.ok(result.error);
 }
});
