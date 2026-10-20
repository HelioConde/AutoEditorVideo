/**
 * Browser-only export engine.
 * The single-thread core works on static GitHub Pages without COOP/COEP headers.
 * Files never leave the user's device. The engine itself is downloaded from
 * jsDelivr on first export, so the first export needs an internet connection.
 *
 * This module intentionally contains no imports at top level, keeping FFmpeg
 * outside the first-paint bundle.
 */
import { normalizeClips } from './clip-utils.js';

export const MAX_BROWSER_BYTES = 30 * 1024 * 1024;
export const MAX_BROWSER_SECONDS = 120;
export const MAX_EXPORT_SECONDS = 20;
export const CORE_URL = 'https://cdn.jsdelivr.net/npm/@ffmpeg/core@0.12.10/dist/esm';
const MIME = new Set(['video/mp4', 'video/webm']);

export function validateBrowserVideo(file) {
  if (!file) return 'Selecione um vídeo.';
  const ext = file.name.toLowerCase().split('.').pop();
  if (!['mp4', 'webm'].includes(ext) || (file.type && !MIME.has(file.type)))
    return 'Para a versão web, escolha um vídeo MP4 ou WebM.';
  if (file.size === 0) return 'O arquivo está vazio.';
  if (file.size > MAX_BROWSER_BYTES) return 'A versão web aceita vídeos de até 30 MB. Para arquivos maiores, use a versão desktop.';
  return null;
}

export function validateBrowserRange({ start, end, duration }) {
  const a = Number(start), b = Number(end), d = Number(duration);
  if (![a, b, d].every(Number.isFinite) || d <= 0) return 'Aguarde o vídeo carregar.';
  if (a < 0 || b <= a || b > d + 0.15) return 'O fim deve ser maior que o início e estar dentro do vídeo.';
  if (b - a > MAX_EXPORT_SECONDS + 0.01) return 'A versão web exporta trechos de no máximo 20 segundos.';
  if (b - a < 0.25) return 'Selecione pelo menos 0,25 segundo.';
  return null;
}

export async function exportBrowserVideo({ file, start, end, duration, segments, aspect, onStatus, onProgress, registerCancel }) {
  const fileError = validateBrowserVideo(file);
  const rangeError = segments === undefined ? validateBrowserRange({ start, end, duration }) : null;
  const plan = normalizeClips({ segments, start, end, duration, maxTotal: MAX_EXPORT_SECONDS, maxEach: MAX_EXPORT_SECONDS });
  if (fileError || rangeError || plan.error) throw new Error(fileError || rangeError || plan.error);
  if (!['9:16', '16:9'].includes(aspect)) throw new Error('Formato de vídeo inválido.');

  // Load packages only when the user explicitly requests rendering.
  const [{ FFmpeg }, { toBlobURL, fetchFile }] = await Promise.all([
    import('@ffmpeg/ffmpeg'), import('@ffmpeg/util')
  ]);
  const engine = new FFmpeg();
  registerCancel?.(() => engine.terminate());
  let currentClipIndex = 0;
  engine.on('progress', ({ progress }) => {
    if (Number.isFinite(progress)) onProgress?.(Math.min(99, Math.max(0, Math.round((currentClipIndex + progress) / plan.clips.length * 94))));
  });
  const extension = file.name.toLowerCase().endsWith('.webm') ? 'webm' : 'mp4';
  const source = 'input.' + extension;
  const destination = 'autoeditor-export.mp4';
  try {
    onStatus?.('Baixando motor de edição (~31 MB)…');
    const [coreURL, wasmURL] = await Promise.all([
      toBlobURL(CORE_URL + '/ffmpeg-core.js', 'text/javascript'),
      toBlobURL(CORE_URL + '/ffmpeg-core.wasm', 'application/wasm'),
    ]);
    await engine.load({ coreURL, wasmURL });
    onStatus?.('Lendo vídeo no navegador…');
    await engine.writeFile(source, await fetchFile(file));
    const vertical = aspect === '9:16';
    const w = vertical ? 360 : 640;
    const h = vertical ? 640 : 360;
    const vf = 'scale=' + w + ':' + h + ':force_original_aspect_ratio=increase,crop=' + w + ':' + h + ',fps=24';
    const makeArgs = (clip, output) => [
      '-hide_banner', '-loglevel', 'error', '-i', source,
      '-ss', String(clip.start), '-t', String(clip.end - clip.start),
      '-vf', vf, '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28', '-pix_fmt', 'yuv420p',
      '-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart', '-y', output
    ];
    if (plan.clips.length === 1) {
      onStatus?.('Exportando MP4 no navegador…');
      const code = await engine.exec(makeArgs(plan.clips[0], destination), 120000);
      if (code !== 0) throw new Error('Não foi possível codificar o trecho (código ' + code + ').');
    } else {
      const parts = [];
      for (let i = 0; i < plan.clips.length; i++) {
        currentClipIndex = i;
        onStatus?.('Renderizando trecho ' + (i + 1) + '/' + plan.clips.length + '…');
        const part = 'part-' + i + '.mp4';
        const code = await engine.exec(makeArgs(plan.clips[i], part), 120000);
        if (code !== 0) throw new Error('Falha ao renderizar trecho ' + (i + 1) + ' (código ' + code + ').');
        parts.push(part);
      }
      onStatus?.('Unindo os cortes em um MP4…');
      const list = parts.map(part => "file '" + part + "'").join('\\n') + '\\n';
      // The FFmpeg virtual filesystem requires real newline separators, not literal backslash-n.
      await engine.writeFile('concat.txt', new TextEncoder().encode(list.replaceAll('\\n', '\n')));
      const code = await engine.exec(['-hide_banner', '-loglevel', 'error', '-f', 'concat',
        '-safe', '0', '-i', 'concat.txt', '-c', 'copy', '-movflags', '+faststart', '-y', destination], 120000);
      if (code !== 0) throw new Error('Não foi possível unir os cortes (código ' + code + ').');
    }
    const bytes = await engine.readFile(destination);
    if (!bytes?.byteLength) throw new Error('A exportação terminou sem gerar um arquivo.');
    onProgress?.(100);
    onStatus?.('Vídeo pronto para baixar.');
    return new Blob([bytes], { type: 'video/mp4' });
  } finally {
    // Terminate instead of keeping a second copy of large files in worker memory.
    engine.terminate();
    registerCancel?.(null);
  }
}
