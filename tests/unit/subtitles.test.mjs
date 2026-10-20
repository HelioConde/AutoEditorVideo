import test from 'node:test';
import assert from 'node:assert/strict';
import { parseSubtitleText, toSrt, remapSubtitles, validateSubtitles } from '../../src/subtitles.js';

test('SRT in Brazilian Portuguese imports and exports with millisecond precision',()=>{
  const srt='1\n00:00:00,400 --> 00:00:01,800\nOlá, mundo!\n\n2\n00:00:02,000 --> 00:00:03,500\nTudo bem?\n';
  const parsed=parseSubtitleText(srt);
  assert.equal(parsed.length,2);
  assert.equal(parsed[0].start,.4);
  assert.equal(parsed[1].text,'Tudo bem?');
  assert.deepEqual(parseSubtitleText(toSrt(parsed)),parsed);
});
test('WebVTT timestamps and basic markup supported without unsafe tags',()=>{
  const text='WEBVTT\n\n00:00:00.000 --> 00:00:01.200\n<i>Bom dia</i>\n\n';
  assert.equal(parseSubtitleText(text)[0].text,'Bom dia');
});
test('subtitles follow concatenated video trims with correct offsets',()=>{
  const cues=[{start:.1,end:1.2,text:'Primeiro'},{start:3.4,end:4.5,text:'Segundo'}];
  const mapped=remapSubtitles(cues,[{start:.5,end:1},{start:3.8,end:4.3}]);
  assert.deepEqual(mapped,[
    {start:0,end:.5,text:'Primeiro'},
    {start:.5,end:1,text:'Segundo'}
  ]);
});
test('overlapping, malformed and oversized subtitles are rejected',()=>{
  assert.match(validateSubtitles([{start:0,end:1,text:'x'},{start:.5,end:1.5,text:'y'}]).error,/sobrepor/);
  assert.match(validateSubtitles([{start:0,end:3,text:'x'.repeat(241)}]).error,/240/);
  assert.throws(()=>parseSubtitleText('not an SRT'),/Nenhuma legenda/);
  assert.throws(()=>parseSubtitleText('x'.repeat(64001)),/64 KB/);
});
