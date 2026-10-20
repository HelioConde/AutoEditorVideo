import fs from 'node:fs';
import path from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const DEFAULT_PIPER_BIN = process.platform === 'win32' ? 'piper.exe' : 'piper';

function executableAvailable(executable, args = ['--help']) {
  const result = spawnSync(executable, args, { encoding: 'utf8', timeout: 4000, windowsHide: true });
  return !result.error && result.status === 0;
}

export function getVoiceCapabilities(env = process.env, platform = process.platform) {
  const bin = env.PIPER_BIN || (platform === 'win32' ? 'piper.exe' : DEFAULT_PIPER_BIN);
  const model = env.PIPER_MODEL;
  const modelValid = typeof model === 'string' && model.endsWith('.onnx') && fs.existsSync(model) && fs.existsSync(model + '.json');
  // Piper is opt-in; never trigger downloads or use untrusted project paths as executables.
  const piper = Boolean(modelValid && executableAvailable(bin));
  const system = platform === 'win32' || executableAvailable('espeak-ng', ['--version']);
  return { system, piper };
}

export function resolveVoiceEngine(requested, available) {
  if (!['system', 'piper'].includes(requested)) throw new Error('Motor de voz inválido.');
  if (!available[requested])
    throw new Error(requested === 'piper'
      ? 'Configure PIPER_BIN e PIPER_MODEL (arquivo ONNX e seu JSON) antes de usar a voz neural.'
      : 'Instale uma voz do sistema ou eSpeak NG para narrar.');
  return requested;
}

function runProgram(executable, args, input = null, timeoutMs = 120000) {
  return new Promise((resolve, reject) => {
    const child = spawn(executable, args, { windowsHide: true, stdio: ['pipe', 'ignore', 'pipe'] });
    let errorText = '', settled = false;
    const timer = setTimeout(() => child.kill(), timeoutMs);
    const done = (error) => {
      if (settled) return;
      settled = true; clearTimeout(timer);
      error ? reject(error) : resolve();
    };
    child.stderr.on('data', chunk => { errorText = (errorText + chunk.toString()).slice(-1200); });
    child.once('error', done);
    child.once('close', code => done(code === 0 ? null : new Error(errorText || 'Motor de voz falhou: ' + code)));
    if (input === null) child.stdin.end();
    else child.stdin.end(input, 'utf8');
    child.stdin.on('error', () => {}); // process may exit before consuming stdin
  });
}

export async function synthesizeVoice({ text, outputFile, engine = 'system', env = process.env, platform = process.platform }) {
  const capabilities = getVoiceCapabilities(env, platform);
  resolveVoiceEngine(engine, capabilities);
  if (engine === 'piper') {
    await runProgram(env.PIPER_BIN || (platform === 'win32' ? 'piper.exe' : DEFAULT_PIPER_BIN),
      ['--model', env.PIPER_MODEL, '--output_file', outputFile], text + '\n');
  } else if (platform === 'win32') {
    const textFile = outputFile + '.txt';
    try {
      fs.writeFileSync(textFile, text, 'utf8');
      await runProgram('powershell.exe',
        ['-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File',
          path.join(HERE, 'tts-windows.ps1'), '-TextFile', textFile, '-OutputFile', outputFile]);
    } finally { fs.rmSync(textFile, { force: true }); }
  } else {
    const textFile = outputFile + '.txt';
    try {
      fs.writeFileSync(textFile, text, 'utf8');
      await runProgram('espeak-ng', ['-v', 'pt-br', '-s', '158', '-f', textFile, '-w', outputFile]);
    } finally { fs.rmSync(textFile, { force: true }); }
  }
  if (!fs.existsSync(outputFile) || fs.statSync(outputFile).size < 64)
    throw new Error('O motor de voz não gerou áudio válido.');
}
