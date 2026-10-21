/**
 * Conservative edit decisions from text and detected pauses.
 *
 * A transcript cue is treated as a spoken interval. We never move the beginning
 * later or the end earlier than its chosen cues, and never cross neighboring
 * cues when padding with silence. Without validated pauses: leave cuts intact.
 */
const round = n => Math.round(n * 100) / 100;
const leadingConnective = /^(?:e|mas|porque|porém|então|que|pois|assim|portanto|contudo|entretanto)\b/iu;
const trailingConnective = /\b(?:e|mas|porque|porém|então|que|pois|assim|se|quando|ou)\s*[,;:]?\s*$/iu;

export function narrativeQuality(firstText, lastText) {
  const first = String(firstText || '').trim();
  const last = String(lastText || '').trim();
  let adjustment = 0;
  const reasons = [];
  if (leadingConnective.test(first)) {
    adjustment -= 7;
    reasons.push('Início depende de contexto anterior');
  }
  if (trailingConnective.test(last)) {
    adjustment -= 10;
    reasons.push('Frase parece incompleta no final');
  } else if (/[.!?][”"']?\s*$/u.test(last)) {
    adjustment += 5;
    reasons.push('Frase termina com pontuação');
  } else {
    adjustment -= 3;
    reasons.push('Final sem pontuação confirmada');
  }
  return { adjustment, reasons };
}

function silenceIntervals(signals, duration) {
  if (!Array.isArray(signals?.silences)) return [];
  return signals.silences.filter(g => g && Number.isFinite(g.start) &&
    Number.isFinite(g.end) && g.start >= 0 && g.end > g.start &&
    g.end <= duration + 0.2).slice(0, 1000);
}

/**
 * Small buffers before and after the speech, cut in/near confirmed silence.
 * Uses adjacent subtitle boundaries as hard guards against including more speech.
 */
export function refineShortBoundaries({
  start, end, duration, signals, previousEnd = 0, nextStart = duration,
  maxPadding = 0.65, maxDuration = 45,
} = {}) {
  if (![start,end,duration,previousEnd,nextStart].every(Number.isFinite) ||
      start < 0 || end <= start || duration < end)
    return {start,end,adjusted:false};
  const intervals = silenceIntervals(signals, duration);
  let from = start, to = end;
  const before = intervals
    .filter(g => g.start <= start && g.end >= start - maxPadding &&
      g.end <= start + 0.06)
    .map(g => Math.min(start, Math.max(g.start, g.end - 0.16)))
    .filter(t => t >= Math.max(previousEnd, start - maxPadding))
    .sort((a,b) => b-a);
  if (before.length) from = before[0];
  const after = intervals
    .filter(g => g.start >= end - 0.06 && g.start <= end + maxPadding && g.end >= end)
    .map(g => Math.max(end, Math.min(g.end, g.start + 0.16)))
    .filter(t => t <= Math.min(nextStart, end + maxPadding))
    .sort((a,b) => a-b);
  if (after.length) to = after[0];
  // Preserve the source content if the optional breathing room would exceed
  // the Short length limit; prefer trimming padding after the last cue.
  if (to - from > maxDuration) {
    to = Math.min(to, from + maxDuration);
    if (to < end) {to = end; from = start;}
  }
  return {start:round(from),end:round(to),
    adjusted:round(from)!==round(start)||round(to)!==round(end)};
}
