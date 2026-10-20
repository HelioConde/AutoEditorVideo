import test from 'node:test';
import assert from 'node:assert/strict';
import { rankShortsFromTranscript } from '../../src/shorts-ranking.js';

const transcript=[
  {start:0,end:5,text:'Hoje estamos conversando sobre alguns conceitos gerais.'},
  {start:5,end:12,text:'A reunião começou e todos trouxeram suas opiniões.'},
  {start:12,end:21,text:'Falamos sobre planejamento, organização e próximas etapas.'},
  {start:27,end:34,text:'Mas sabe como consegui virar a partida no final?'},
  {start:34,end:43,text:'Eu descobri uma estratégia incrível que ninguém conhecia.'},
  {start:43,end:51,text:'O resultado mudou e finalmente vencemos a partida!'},
  {start:57,end:66,text:'Esta parte traz uma explicação sobre procedimentos tradicionais.'},
  {start:66,end:75,text:'O tópico continua explicando um fluxo de trabalho rotineiro.'}
];
test('prioriza trecho com curiosidade, contraste e resultado sem invadir as pausas',()=>{
  const {error,candidates}=rankShortsFromTranscript(transcript,{duration:80,maxClips:3});
  assert.equal(error,null);
  assert.ok(candidates.length>=2);
  assert.equal(candidates[0].start,27);
  assert.equal(candidates[0].end,51);
  for(const c of candidates){
    assert.ok(c.duration>=8 && c.duration<=45);
    assert.ok(c.score>=0 && c.score<=99);
    assert.ok(c.reason.length>2);
  }
  for(const [i,c] of candidates.entries())for(const next of candidates.slice(i+1))
    assert.ok(c.end+1<=next.start || next.end+1<=c.start);
});
test('sugestões são determinísticas e limitadas a três',()=>{
  const a=rankShortsFromTranscript(transcript,{duration:80,maxClips:2});
  const b=rankShortsFromTranscript(transcript,{duration:80,maxClips:2});
  assert.deepEqual(a,b);
  assert.ok(a.candidates.length<=2);
});
test('sem transcrição válida não finge escolher melhores momentos',()=>{
  assert.match(rankShortsFromTranscript([],{duration:50}).error,/Transcreva/);
  assert.match(rankShortsFromTranscript([{start:0,end:2,text:'Oi'}],{duration:2}).error,/Não há falas/);
  assert.match(rankShortsFromTranscript([{start:0,end:12,text:'Frase longa com contexto e mais palavras para gerar um short.'}],{duration:13,maxClips:4}).error,/1 a 3/);
});
