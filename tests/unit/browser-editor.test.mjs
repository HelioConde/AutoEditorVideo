import test from 'node:test';
import assert from 'node:assert/strict';
import { MAX_BROWSER_BYTES, MAX_EXPORT_SECONDS, validateBrowserVideo, validateBrowserRange } from '../../src/browser-ffmpeg.js';

test('browser allows MP4/WebM and rejects unrecognized extensions', () => {
  assert.equal(validateBrowserVideo({ name:'clip.mp4', type:'video/mp4', size:1024 }), null);
  assert.equal(validateBrowserVideo({ name:'clip.webm', type:'video/webm', size:1024 }), null);
  assert.match(validateBrowserVideo({ name:'clip.exe', type:'', size:1024 }), /MP4 ou WebM/);
  assert.match(validateBrowserVideo({ name:'clip.mp4', type:'video/mp4', size:0 }), /vazio/);
  assert.match(validateBrowserVideo({ name:'clip.mp4', type:'video/mp4', size:MAX_BROWSER_BYTES+1 }), /30 MB/);
});
test('browser validates ranges before export', () => {
  assert.equal(validateBrowserRange({ start:0, end:4, duration:5 }), null);
  assert.match(validateBrowserRange({ start:4, end:2, duration:5 }), /maior que/);
  assert.match(validateBrowserRange({ start:-1, end:2, duration:5 }), /maior que/);
  assert.match(validateBrowserRange({ start:0, end:MAX_EXPORT_SECONDS+1, duration:90 }), /20 segundos/);
  assert.match(validateBrowserRange({ start:0, end:.1, duration:90 }), /0,25/);
  assert.match(validateBrowserRange({ start:1, end:20, duration:5 }), /dentro do vídeo/);
});
