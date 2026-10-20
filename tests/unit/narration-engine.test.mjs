import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { getVoiceCapabilities, resolveVoiceEngine, synthesizeVoice } from '../../server/tts.mjs';
import { sceneVideoFilters } from '../../server/index.mjs';

test('Piper neural is explicitly opt-in and requires model, config and executable',()=>{
  const unconfigured=getVoiceCapabilities({PIPER_BIN:'file-not-found',PIPER_MODEL:'/not-found/voice.onnx'});
  assert.equal(unconfigured.piper,false);
  assert.throws(()=>resolveVoiceEngine('piper',unconfigured),/Configure PIPER_BIN/);
  assert.throws(()=>resolveVoiceEngine('remote',unconfigured),/inválido/);
});

test('render uses fades only for scene transitions configured as fade',()=>{
  const scenes=[{transition:'fade'},{transition:'cut'},{transition:'fade'}];
  const a=sceneVideoFilters({width:720,height:1280,index:0,scenes,duration:3});
  const b=sceneVideoFilters({width:720,height:1280,index:1,scenes,duration:4});
  const c=sceneVideoFilters({width:720,height:1280,index:2,scenes,duration:5});
  assert.match(a.video,/fade=t=in/);
  assert.doesNotMatch(a.video,/fade=t=out/);
  assert.doesNotMatch(b.video,/fade=t=in/);
  assert.match(b.video,/fade=t=out/);
  assert.match(c.video,/fade=t=in/);
  assert.match(c.video,/fade=t=out/);
  assert.match(c.audio,/afade/);
});

test('Piper binary interface accepts text on stdin and writes WAV (mock, no neural model)',async t=>{
  if(process.platform==='win32')return t.skip('Uses POSIX executable with Node shebang');
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'studio-piper-mock-'));
  try{
    const voice=path.join(dir,'pt_BR-test.onnx');
    fs.writeFileSync(voice,'TEST-ONLY');
    fs.writeFileSync(voice+'.json','{}');
    const binary=path.join(dir,'piper-mock');
    const source=`#!/usr/bin/env node
const fs=require('node:fs');
const args=process.argv.slice(2);
if(args.includes('--help'))process.exit(0);
if(!args.includes('--model')||!args.includes('--output_file'))process.exit(2);
let text='';
process.stdin.setEncoding('utf8');
process.stdin.on('data',chunk=>text+=chunk);
process.stdin.on('end',()=>{
  if(!text.includes('Olá'))process.exit(3);
  const output=args[args.indexOf('--output_file')+1];
  const samples=16000,buf=Buffer.alloc(44+samples*2);
  buf.write('RIFF',0);buf.writeUInt32LE(buf.length-8,4);buf.write('WAVEfmt ',8);
  buf.writeUInt32LE(16,16);buf.writeUInt16LE(1,20);buf.writeUInt16LE(1,22);
  buf.writeUInt32LE(16000,24);buf.writeUInt32LE(32000,28);
  buf.writeUInt16LE(2,32);buf.writeUInt16LE(16,34);buf.write('data',36);
  buf.writeUInt32LE(samples*2,40);fs.writeFileSync(output,buf);
});
`;
    fs.writeFileSync(binary,source,{mode:0o755});
    fs.chmodSync(binary,0o755);
    const env={PIPER_BIN:binary,PIPER_MODEL:voice};
    assert.equal(getVoiceCapabilities(env,'linux').piper,true);
    const dest=path.join(dir,'voice.wav');
    await synthesizeVoice({text:'Olá, mundo!',outputFile:dest,engine:'piper',env,platform:'linux'});
    assert.ok(fs.statSync(dest).size>1000);
  } finally {fs.rmSync(dir,{recursive:true,force:true});}
});
