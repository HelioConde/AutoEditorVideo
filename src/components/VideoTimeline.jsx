import { useEffect, useId, useState } from 'react';
import { ArrowDown, ArrowUp, Film, Image as ImageIcon, Play, Plus, Trash2 } from 'lucide-react';
import { MAX_CLIPS, insertClip, moveClip, normalizeClips } from '../clip-utils.js';
import './timeline.css';

function pad(value) {
  const secs = Math.max(0, Number(value) || 0);
  const m = Math.floor(secs / 60).toString().padStart(2, '0');
  const s = (secs % 60).toFixed(1).padStart(4, '0');
  return m + ':' + s;
}

/** Capture actual video frames from a same-origin/blob source, without uploading media.
 * Limit thumbnails to eight JPEG data URLs; abandon captures on source change/unmount.
 */
function useThumbnails(source, count = 8) {
  const [state, setState] = useState({ source: null, images: [], loading: false });
  useEffect(() => {
    if (!source) { setState({ source: null, images: [], loading: false }); return; }
    let cancelled = false;
    const video = document.createElement('video');
    video.muted = true;
    video.preload = 'auto';
    video.playsInline = true;
    video.src = source;
    setState({ source, images: [], loading: true });
    const capture = async () => {
      try {
        await new Promise((resolve, reject) => {
          if (video.readyState >= 1) return resolve();
          video.addEventListener('loadedmetadata', resolve, { once: true });
          video.addEventListener('error', () => reject(new Error('metadata')), { once: true });
        });
        if (cancelled || !Number.isFinite(video.duration) || video.duration <= 0) return;
        const canvas = document.createElement('canvas');
        canvas.width = 160;
        canvas.height = 90;
        const ctx = canvas.getContext('2d', { willReadFrequently: false });
        if (!ctx) throw new Error('canvas');
        const frames = [];
        for (let i = 0; i < count && !cancelled; i++) {
          const target = Math.min(Math.max(0, video.duration - 0.08), video.duration * (i + .5) / count);
          await new Promise((resolve, reject) => {
            const done = () => { video.removeEventListener('seeked', done); resolve(); };
            video.addEventListener('seeked', done, { once: true });
            video.currentTime = target;
            // Some browsers don't fire seeked for a near-identical target.
            if (!video.seeking && Math.abs(video.currentTime - target) < .001) done();
            video.addEventListener('error', () => reject(new Error('seek')), { once: true });
          });
          if (cancelled) break;
          try {
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            frames.push(canvas.toDataURL('image/jpeg', .64));
          } catch { break; }
        }
        if (!cancelled) setState({ source, images: frames, loading: false });
      } catch {
        if (!cancelled) setState({ source, images: [], loading: false });
      }
    };
    capture();
    return () => {
      cancelled = true;
      video.pause();
      video.removeAttribute('src');
      video.load();
    };
  }, [source, count]);
  return state.source === source ? state : { images: [], loading: !!source };
}

export default function VideoTimeline({
  source, duration, start, end, onStartChange, onEndChange,
  clips, onClipsChange, onPreview, disabled = false, maxTotal = 600,
  maxEach = 600, variant = 'desktop'
}) {
  const id = useId();
  const thumbs = useThumbnails(source);
  const max = Math.max(.1, Number(duration) || .1);
  const left = Math.max(0, Math.min(100, Number(start) / max * 100));
  const right = Math.max(0, Math.min(100, 100 - Number(end) / max * 100));
  const current = normalizeClips({ start, end, duration, maxTotal, maxEach });
  const queued = clips.length ? normalizeClips({ segments: clips, duration, maxTotal, maxEach }) : null;
  const remaining = maxTotal - (queued?.total || 0);
  const canAdd = Boolean(!disabled && !current.error && clips.length < MAX_CLIPS && Number(end) - Number(start) <= remaining + .01);
  const formatTotal = pad(queued?.total || 0);
  return (
    <section className={'filmstrip-editor filmstrip-' + variant} aria-label="Timeline visual">
      <div className="filmstrip-header">
        <span><ImageIcon size={16} aria-hidden="true" /> Miniaturas reais do vídeo</span>
        <span className="filmstrip-duration">{pad(duration)} de duração</span>
      </div>
      <div className="filmstrip-frames" aria-label="Quadros do vídeo">
        {thumbs.images.length > 0 ? thumbs.images.map((url, i) => <img key={i} src={url} alt={'Quadro ' + (i + 1) + ' do vídeo'} loading="lazy" />) :
          <div className="filmstrip-placeholder" role="status">{thumbs.loading ? 'Gerando miniaturas do vídeo…' : (source ? 'Miniaturas não disponíveis para este vídeo' : 'Importe um vídeo para visualizar a timeline')}</div>}
        <div className="filmstrip-selection" style={{ left: left + '%', right: right + '%' }} aria-hidden="true" />
      </div>
      <div className="filmstrip-sliders">
        <label htmlFor={id+'-start'}>Arrastar início <strong>{pad(start)}</strong></label>
        <input id={id+'-start'} aria-label="Arrastar início" type="range" min="0" max={max} step=".1" value={Math.min(max, Number(start)||0)} disabled={disabled} onChange={e => onStartChange(e.target.value)} />
        <label htmlFor={id+'-end'}>Arrastar fim <strong>{pad(end)}</strong></label>
        <input id={id+'-end'} aria-label="Arrastar fim" type="range" min="0" max={max} step=".1" value={Math.min(max, Number(end)||0)} disabled={disabled} onChange={e => onEndChange(e.target.value)} />
      </div>
      <div className="filmstrip-actions">
        <button type="button" className="filmstrip-button" disabled={disabled || !!current.error} onClick={() => onPreview({ start: Number(start), end: Number(end) })}>
          <Play size={15} aria-hidden="true"/> Prévia do trecho
        </button>
        <button type="button" className="filmstrip-button filmstrip-add" disabled={!canAdd} onClick={() => onClipsChange(insertClip(clips, { start, end }))}>
          <Plus size={15} aria-hidden="true"/> Adicionar à sequência
        </button>
      </div>
      <div className="filmstrip-queue" aria-label="Sequência de trechos">
        <div className="filmstrip-queue-heading"><span><Film size={16} aria-hidden="true"/> Sequência de cortes</span><span>{clips.length}/{MAX_CLIPS} · {formatTotal}</span></div>
        {clips.length === 0 ? <p className="filmstrip-hint">Adicione trechos para montar um vídeo com vários cortes. Sem trechos adicionados, a exportação usa apenas a seleção atual.</p> :
          <ol className="filmstrip-queue-list">
            {clips.map((c, i) => <li key={i}>
              <strong>Trecho {i+1}</strong><span>{pad(c.start)} → {pad(c.end)}</span>
              <div className="filmstrip-queue-buttons">
                <button type="button" aria-label={'Prévia do trecho ' + (i+1)} onClick={() => onPreview(c)} disabled={disabled}><Play size={15}/></button>
                <button type="button" aria-label={'Subir trecho ' + (i+1)} onClick={() => onClipsChange(moveClip(clips,i,-1))} disabled={disabled || i===0}><ArrowUp size={15}/></button>
                <button type="button" aria-label={'Descer trecho ' + (i+1)} onClick={() => onClipsChange(moveClip(clips,i,1))} disabled={disabled || i===clips.length-1}><ArrowDown size={15}/></button>
                <button type="button" aria-label={'Remover trecho ' + (i+1)} onClick={() => onClipsChange(clips.filter((_,n)=>i!==n))} disabled={disabled}><Trash2 size={15}/></button>
              </div>
            </li>)}
          </ol>}
        {clips.length>0 && <p className="filmstrip-queue-note">Na exportação, apenas os trechos desta sequência serão unidos na ordem exibida. {queued?.error || ''}</p>}
      </div>
    </section>
  );
}
