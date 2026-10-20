export const MAX_CLIPS = 5;
export const MIN_CLIP_SECONDS = 0.25;

export function normalizeClips({ segments, start, end, duration, maxTotal = 600, maxEach = 600, maxClips = MAX_CLIPS }) {
  const source = segments === undefined ? [{ start, end }] : segments;
  if (!Array.isArray(source) || source.length < 1 || source.length > maxClips)
    return { error: 'Selecione entre 1 e ' + maxClips + ' trechos.' };
  const d = Number(duration);
  if (!Number.isFinite(d) || d <= 0) return { error: 'A duração do vídeo é inválida.' };
  let total = 0;
  const clips = [];
  for (const item of source) {
    if (!item || typeof item !== 'object' || item.start === '' || item.end === '' || item.start === null || item.end === null)
      return { error: 'Os trechos precisam ter início e fim válidos.' };
    const a = Number(item.start), b = Number(item.end);
    if (![a, b].every(Number.isFinite) || a < 0 || b > d + 0.15 || b - a < MIN_CLIP_SECONDS)
      return { error: 'Cada trecho deve estar dentro do vídeo e ter pelo menos 0,25 segundo.' };
    if (b - a > maxEach + 0.01) return { error: 'Um dos trechos ultrapassa o limite de duração.' };
    total += b - a;
    clips.push({ start: Math.round(a * 1000) / 1000, end: Math.round(b * 1000) / 1000 });
  }
  if (total > maxTotal + 0.01)
    return { error: 'A sequência selecionada ultrapassa o limite total de duração.' };
  return { clips, total: Math.round(total * 1000) / 1000, error: null };
}

export function insertClip(queue, clip, maxClips = MAX_CLIPS) {
  if (!Array.isArray(queue) || queue.length >= maxClips) return queue;
  return [...queue, { start: Number(clip.start), end: Number(clip.end) }];
}
export function moveClip(queue, index, direction) {
  const target = index + direction;
  if (index < 0 || target < 0 || index >= queue.length || target >= queue.length) return queue;
  const result = queue.slice();
  [result[index], result[target]] = [result[target], result[index]];
  return result;
}
