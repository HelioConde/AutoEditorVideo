import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { whisperCapability } from '../../server/whisper.mjs';

test('Whisper remains unavailable unless both executable and local model are installed',()=>{
  assert.equal(whisperCapability({WHISPER_BIN:'missing-cli',WHISPER_MODEL:'/missing/model.bin'}),false);
  const folder=fs.mkdtempSync(path.join(os.tmpdir(),'test-whisper-settings-'));
  try{
    const fake=path.join(folder,'ggml.bin');
    fs.writeFileSync(fake,'fixture');
    assert.equal(whisperCapability({WHISPER_BIN:path.join(folder,'unavailable'),WHISPER_MODEL:fake}),false);
  } finally {fs.rmSync(folder,{recursive:true,force:true});}
});
