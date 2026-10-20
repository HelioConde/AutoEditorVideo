import { lazy, Suspense, useEffect, useId, useRef, useState } from 'react';
const VideoTimeline=lazy(()=>import('./components/VideoTimeline.jsx'));
import { browserStorage, clearWebDraft, loadWebDraft, saveWebDraft } from './web-draft.js';
import './editor-polish.css';
const SubtitleStudio=lazy(()=>import('./components/SubtitleStudio.jsx'));
import { normalizeClips } from './clip-utils.js';
const ProjectExchange=lazy(()=>import('./components/ProjectExchange.jsx'));
const StoryStudio=lazy(()=>import('./components/StoryStudio.jsx'));
import {
  ArrowDownToLine, ArrowRight, BadgeCheck, Check, Clapperboard,
  Clock3, FileVideo2, Film, Globe2, HardDrive, Info, LoaderCircle,
  Monitor, Play, RotateCcw, Scissors, ShieldCheck, Sparkles, UploadCloud, X
} from 'lucide-react';
import {
  exportBrowserVideo, MAX_BROWSER_BYTES, MAX_BROWSER_SECONDS,
  MAX_EXPORT_SECONDS, validateBrowserRange, validateBrowserVideo
} from './browser-ffmpeg.js';

function minutes(seconds) {
  const s = Math.max(0, Math.floor(Number(seconds) || 0));
  return String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0');
}
function durationLabel(seconds) {
  return Math.max(0, Number(seconds || 0)).toFixed(1).replace('.', ',') + ' s';
}
function size(bytes) {
  return (bytes / 1024 / 1024).toLocaleString('pt-BR', { maximumFractionDigits: 1 }) + ' MB';
}
function Stage({ number, title, completed, current, onClick, disabled }) {
  return <button type="button" onClick={onClick} disabled={disabled}
    aria-current={current ? 'step' : undefined}
    className={'web-step web-step-action ' + (completed ? 'web-step-done ' : '') + (current ? 'web-step-current' : '')}>
    <span className="web-step-count" aria-hidden="true">{completed ? <Check size={15}/> : number}</span><span>{title}</span>
  </button>;
}

export default function WebApp() {
  const id = useId();
  const [initialDraft] = useState(()=>loadWebDraft(browserStorage()));
  const initialProject=initialDraft?.project;
  const initialEdit=initialProject?.edit;
  const videoRef = useRef(null);
  const fileInput = useRef(null);
  const cancelRef = useRef(null);
  const [file, setFile] = useState(null);
  const [phase,setPhase] = useState('import');
  const [openTool,setOpenTool] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [duration, setDuration] = useState(0);
  const [start, setStart] = useState(initialEdit?.start ?? 0);
  const [end, setEnd] = useState(initialEdit?.end ?? 0);
  const [clips, setClips] = useState(initialEdit?.clips || []);
  const [script,setScript] = useState(initialEdit?.script || '');
  const [scenes,setScenes] = useState(initialEdit?.scenes || []);
  const [subtitles,setSubtitles] = useState(initialEdit?.subtitles || []);
  const [burnSubtitles,setBurnSubtitles] = useState(initialEdit?.burnSubtitles || false);
  const [previewTime,setPreviewTime] = useState(0);
  const [voiceEngine,setVoiceEngine] = useState(initialEdit?.voiceEngine || 'system');
  const [scenePictures,setScenePictures] = useState([]);
  const [reference,setReference] = useState(initialProject?.media || null);
  const [projectName,setProjectName] = useState(initialProject?.name || 'Meu projeto web');
  const [draftMessage,setDraftMessage] = useState(initialDraft ?
    'Rascunho restaurado neste navegador. Selecione o vídeo original para recuperar os cortes.' :
    'Rascunho local: alterações salvas automaticamente neste navegador.');
  const previewEndRef = useRef(null);
  const [aspect, setAspect] = useState(initialProject?.aspect || '9:16');
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');
  const [progress, setProgress] = useState(0);
  const [busy, setBusy] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [outputSize, setOutputSize] = useState(0);

  useEffect(() => {
    document.title = 'AutoEditor Studio Web — Editor online gratuito';
    return () => { cancelRef.current?.(); };
  }, []);
  useEffect(() => {
    if (!file) { setPreviewUrl(null); return; }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  useEffect(() => {
    return () => { if (downloadUrl) URL.revokeObjectURL(downloadUrl); };
  }, [downloadUrl]);
  useEffect(()=>{
    if(busy)return;
    const timer=window.setTimeout(()=>{
      const success=saveWebDraft(browserStorage(),{
        name:projectName,aspect,
        media:reference || (file&&duration>0 ? {name:file.name,size:file.size,duration}:null),
        start:Number(start)||0,end:Number(end)||0,clips,script,scenes,voiceEngine,subtitles,burnSubtitles
      });
      setDraftMessage(success ? 'Rascunho salvo neste navegador. Vídeo e imagens não são armazenados.' :
        'Não foi possível salvar. Exporte o projeto em JSON para preservá-lo.');
    },650);
    return ()=>window.clearTimeout(timer);
  },[file,duration,reference,projectName,aspect,start,end,clips,script,scenes,voiceEngine,subtitles,burnSubtitles,busy]);

  function openOptional(tool) {
    setOpenTool(tool);
    requestAnimationFrame(()=>document.getElementById('studio-'+tool)?.scrollIntoView({block:'start',behavior:'smooth'}));
  }
  function toggleTool(tool) {
    setOpenTool(previous=>previous===tool?null:tool);
  }

  function clearResult() {
    setDownloadUrl(null);
    setOutputSize(0);
    setProgress(0);
    setStatus('');
  }

  function selectFile(selected) {
    if (!selected || busy) return;
    const issue = validateBrowserVideo(selected);
    if (reference && reference.name !== selected.name) {
      setError('Este projeto usa o vídeo '+reference.name+'. Selecione esse mesmo arquivo para recuperar os cortes.');
      if(fileInput.current)fileInput.current.value='';
      return;
    }
    if (issue) { setError(issue); if (fileInput.current) fileInput.current.value = ''; return; }
    setError('');
    clearResult();
    setDuration(0);
    if (!reference) {setStart(0);setEnd(0);setClips([]);}
    setFile(selected);
    setPhase('import');
  }

  function onMetadata(e) {
    const value = Number(e.currentTarget.duration);
    if (!Number.isFinite(value) || value <= 0) {
      setError('Não foi possível identificar a duração do vídeo.');
      return;
    }
    if (value > MAX_BROWSER_SECONDS) {
      setFile(null);
      setError('A versão web aceita vídeos de até 2 minutos. Para gravações maiores, use a versão desktop.');
      if (fileInput.current) fileInput.current.value = '';
      return;
    }
    setDuration(value);
    if (reference && Math.abs(reference.duration - value) > .4) {
      setStart(0);setEnd(Math.min(MAX_EXPORT_SECONDS,Math.floor(value*10)/10));setClips([]);
      setError('A duração não corresponde ao projeto importado. Os cortes foram limpos para evitar usar o vídeo errado.');
    } else if (!reference) {
      setStart(0);setEnd(Math.min(MAX_EXPORT_SECONDS,Math.floor(value*10)/10));
    }
    setReference(null);
    setPhase('edit');
  }

  function onVideoError() {
    setError('O navegador não conseguiu reproduzir esta mídia. Experimente um MP4 H.264 ou WebM compatível.');
  }

  function newFile() {
    if (busy) return;
    setPhase('import');
    setFile(null);
    setDuration(0);
    setClips([]);
    setReference(null);
    setError('');
    clearResult();
    if (fileInput.current) fileInput.current.value = '';
  }

  function previewSegment(segment) {
    const video = videoRef.current;
    if (!video) return;
    previewEndRef.current = Number(segment.end);
    video.currentTime = Math.max(0, Number(segment.start));
    video.play().catch(() => setError('O navegador não conseguiu reproduzir esta prévia.'));
  }
  function stopAtSegmentEnd(e) {
    if (previewEndRef.current !== null && e.currentTarget.currentTime >= previewEndRef.current - .05) {
      e.currentTarget.pause();
      previewEndRef.current = null;
    }
  }
  async function createVideo() {
    if (!file || busy) return;
    const issue = clips.length ? normalizeClips({ segments: clips, duration, maxTotal: 20, maxEach: 20 }).error : validateBrowserRange({ start, end, duration });
    if (issue) { setError(issue); return; }
    setError('');
    clearResult();
    setBusy(true);
    try {
      const blob = await exportBrowserVideo({
        file, start: Number(start), end: Number(end), duration, aspect,
        ...(clips.length ? { segments: clips } : {}),
        onStatus: setStatus, onProgress: setProgress,
        registerCancel: fn => { cancelRef.current = fn; }
      });
      setDownloadUrl(URL.createObjectURL(blob));
      setOutputSize(blob.size);
      setStatus('Exportação concluída. Baixe seu vídeo.');
    } catch (err) {
      console.error('Falha ao exportar vídeo na web', err);
      setError('Não foi possível exportar: ' + (err?.message || 'erro inesperado') + '.');
      setStatus('');
    } finally {
      cancelRef.current = null;
      setBusy(false);
    }
  }

  function resetDraft() {
    if(busy)return;
    clearWebDraft(browserStorage());
    setFile(null);setDuration(0);setStart(0);setEnd(0);setClips([]);
    setPhase('import');setOpenTool(null);
    setScript('');setScenes([]);setSubtitles([]);setBurnSubtitles(false);setVoiceEngine('system');
    setAspect('9:16');setReference(null);setScenePictures([]);setProjectName('Meu projeto web');
    setError('');clearResult();
    if(fileInput.current)fileInput.current.value='';
    setDraftMessage('Rascunho apagado. Você pode começar um novo projeto.');
  }
  async function importPortableProject(incoming) {
    if (busy) throw new Error('Conclua a exportação atual antes de importar.');
    const edit=incoming.edit;
    setFile(null);setDuration(0);
    setPhase('import');setOpenTool('project');
    if(fileInput.current)fileInput.current.value='';
    setProjectName(incoming.name);
    setAspect(incoming.aspect);
    setScript(edit.script);setScenes(edit.scenes);setVoiceEngine(edit.voiceEngine || 'system');
    setSubtitles(edit.subtitles||[]);setBurnSubtitles(edit.burnSubtitles||false);
    setScenePictures([]);
    setClips(edit.clips);setStart(edit.start);setEnd(edit.end);
    setReference(incoming.media);
    setError('');
    clearResult();
  }
  const validRange = file && !(clips.length ? normalizeClips({ segments: clips, duration, maxTotal: 20, maxEach: 20 }).error : validateBrowserRange({ start, end, duration }));
  const canExport = Boolean(validRange && !busy && !error);
  const canTrim = Boolean(file && duration > 0);
  const inputId = id + '-upload';

  return (
    <>
      <a className="skip-link" href="#web-main">Pular para o editor</a>
      <div className="web-shell">
        <header className="web-topbar">
          <div className="web-navbar">
            <a href={import.meta.env.BASE_URL} className="web-brand" aria-label="AutoEditor Studio Web, página inicial"><span className="brand-mark"><Clapperboard size={22} aria-hidden="true" /></span><span className="brand-name">AutoEditor<span>Studio</span></span><span className="web-badge">WEB</span></a>
            <nav aria-label="Navegação web" className="web-nav">
              <a className="web-nav-active" href="#web-main">Editor</a>
              <a href="#como-funciona">Como funciona</a>
              <a href="https://github.com/HelioConde/AutoEditorVideo" target="_blank" rel="noopener noreferrer">GitHub <span aria-hidden="true">↗</span></a>
            </nav>
            <a href="https://github.com/HelioConde/AutoEditorVideo#executar-no-windows" className="web-desktop-link">Versão desktop <ArrowRight size={16} aria-hidden="true" /></a>
          </div>
        </header>
        <main id="web-main" className="web-main">
          <section className="web-intro" aria-labelledby="web-title">
            <div className="web-intro-eyebrow"><Sparkles size={14} aria-hidden="true" /> SEU ESTÚDIO, EM QUALQUER LUGAR</div>
            <h1 id="web-title">Edite seu vídeo.<br/><span>Do seu jeito.</span></h1>
            <p>Importe, recorte e exporte vídeos direto do navegador — sem instalar programas e sem enviar seus arquivos a um servidor.</p>
            <div className="web-chips"><span><ShieldCheck size={15} aria-hidden="true"/> Privado por padrão</span><span><Globe2 size={15} aria-hidden="true"/> Funciona no navegador</span><span><BadgeCheck size={15} aria-hidden="true"/> Sem conta</span></div>
          </section>

          <section className="web-studio" aria-labelledby="studio-title">
            <div className="web-studio-head">
              <div><div className="section-kicker">SEU WORKSPACE</div><h2 id="studio-title">Área de edição</h2></div>
              <span className="web-local-label"><span className="local-circle"/> Edição privada e local</span>
            </div>

            <div className="web-progressive-steps" role="group" aria-label="Etapas da edição">
              <Stage number="01" title="Importar vídeo" current={phase==='import'} completed={Boolean(file)}
                onClick={()=>setPhase('import')} disabled={busy}/>
              <Stage number="02" title="Editar cortes" current={phase==='edit'} completed={Boolean(file && validRange && phase==='export')}
                onClick={()=>setPhase('edit')} disabled={!file || busy}/>
              <Stage number="03" title="Exportar" current={phase==='export'} completed={Boolean(downloadUrl)}
                onClick={()=>setPhase('export')} disabled={!file || busy}/>
            </div>
            <p className="web-phase-description">
              {phase==='import' ? 'Primeiro, escolha o vídeo. As ferramentas de edição aparecerão na próxima etapa.' :
                phase==='edit' ? 'Ajuste os cortes e a sequência. Depois, avance para a exportação.' :
                'Escolha a proporção e gere seu MP4. O vídeo continua no seu dispositivo.'}
            </p>
            {error && <div className="web-error web-global-error" role="alert"><Info size={19} aria-hidden="true"/>
              <span>{error}</span><button type="button" aria-label="Fechar aviso de erro" onClick={()=>setError('')}><X size={16}/></button></div>}
            <div className={'web-columns web-progressive-columns web-phase-'+phase}>
              <div className="web-primary">
                <div id="studio-video" className="web-preview-panel">
                  <div className="web-panel-heading"><strong><Film size={18} aria-hidden="true"/> Pré-visualização</strong>{file && <button className="web-text-btn" onClick={newFile} disabled={busy}><RotateCcw size={15} aria-hidden="true" /> Trocar vídeo</button>}</div>
                  {!file ? <label className="web-droparea" htmlFor={inputId}>
                    <span className="web-upload-illustration"><UploadCloud size={38} aria-hidden="true"/></span>
                    <strong>Comece com um vídeo</strong>
                    <span>Escolha um MP4 ou WebM com até 30 MB e 2 minutos.</span>
                    <span className="web-upload-cta">Escolher arquivo <ArrowRight size={17} aria-hidden="true"/></span>
                  </label> : <div className="web-video-area"><video ref={videoRef} controls playsInline preload="metadata" src={previewUrl || undefined} onLoadedMetadata={onMetadata} onError={onVideoError} onTimeUpdate={e=>{stopAtSegmentEnd(e);setPreviewTime(e.currentTarget.currentTime);}} aria-label="Pré-visualização do vídeo selecionado" />
                  {subtitles.some(c=>previewTime>=c.start&&previewTime<c.end) &&
                    <div className="video-caption-overlay" aria-hidden="true">{subtitles.find(c=>previewTime>=c.start&&previewTime<c.end)?.text}</div>}</div>}
                  <input id={inputId} ref={fileInput} className="visually-hidden" type="file" accept=".mp4,.webm,video/mp4,video/webm" disabled={busy} onChange={e => selectFile(e.target.files?.[0])}/>
                  {file && <div className="web-file-row"><FileVideo2 size={21} aria-hidden="true"/><div><strong title={file.name}>{file.name}</strong><span>{size(file.size)} {duration ? '· ' + minutes(duration) : '· Lendo duração…'}</span></div><Check size={17} aria-hidden="true"/></div>}
                </div>
                {phase==='edit' && <Suspense fallback={<div className="web-tool-loading" role="status">Carregando timeline…</div>}>
                <div id="studio-cuts" className="web-panel web-cut-panel">
                  <div className="web-panel-heading"><strong><Scissors size={18} aria-hidden="true"/> Recortar vídeo</strong><span className="web-muted">Trechos somados até 20 segundos</span></div>
                  <VideoTimeline variant="web" source={previewUrl} duration={duration} start={start} end={end}
                    onStartChange={value => { setStart(value); clearResult(); }}
                    onEndChange={value => { setEnd(value); clearResult(); }}
                    clips={clips} onClipsChange={value => { setClips(value); clearResult(); }}
                    onPreview={previewSegment} disabled={!canTrim || busy} maxTotal={20} maxEach={20} /><div className="web-controls">
                    <label htmlFor={id+'-start'}>Início (segundos)<input id={id+'-start'} type="number" step=".1" min="0" max={duration || 0} disabled={!canTrim || busy} value={start} onChange={e => {setStart(e.target.value);clearResult();}} /></label>
                    <label htmlFor={id+'-end'}>Fim (segundos)<input id={id+'-end'} type="number" step=".1" min="0" max={duration || 0} disabled={!canTrim || busy} value={end} onChange={e => {setEnd(e.target.value);clearResult();}} /></label>
                    <div className="web-selection-length"><Clock3 size={17} aria-hidden="true"/><div><small>Duração do corte</small><strong>{durationLabel(Number(end) - Number(start))}</strong></div></div>
                  </div>
                  {canTrim && !validRange && <p className="web-validation" role="alert">{clips.length ? normalizeClips({ segments: clips, duration, maxTotal: 20, maxEach: 20 }).error : validateBrowserRange({ start, end, duration })}</p>}
                </div>
                  <div className="web-phase-next">
                    <p>Pronto para criar o arquivo? A escolha do formato fica na última etapa.</p>
                    <button type="button" disabled={!file||busy} onClick={()=>setPhase('export')}>Continuar para exportação <ArrowRight size={16} aria-hidden="true"/></button>
                  </div>
                </Suspense>}
                {phase==='import' && <div className="web-start-options" aria-label="Outras formas de começar">
                  <p>Ou comece de outra forma</p>
                  <div>
                    <button type="button" onClick={()=>openOptional('script')}><Sparkles size={17} aria-hidden="true"/> Criar pelo roteiro</button>
                    <button type="button" onClick={()=>openOptional('project')}><FileVideo2 size={17} aria-hidden="true"/> Abrir projeto salvo</button>
                  </div>
                </div>}
              </div>
              {phase==='export' && <>
              <div className="web-side">
                <div className="web-panel web-settings">
                  <div className="web-panel-heading"><strong><Monitor size={18} aria-hidden="true"/> Configurar exportação</strong></div>
                  <fieldset disabled={busy}><legend>Formato do vídeo</legend>
                    <div className="web-aspects">
                      <label className={aspect === '9:16' ? 'web-aspect selected' : 'web-aspect'}>
                        <input type="radio" name="web-aspect" value="9:16" checked={aspect === '9:16'} onChange={()=>{setAspect('9:16');clearResult();}}/>
                        <span className="web-format-symbol portrait"/><strong>9:16</strong><small>Shorts · Reels</small>
                      </label>
                      <label className={aspect === '16:9' ? 'web-aspect selected' : 'web-aspect'}>
                        <input type="radio" name="web-aspect" value="16:9" checked={aspect === '16:9'} onChange={()=>{setAspect('16:9');clearResult();}}/>
                        <span className="web-format-symbol landscape"/><strong>16:9</strong><small>YouTube</small>
                      </label>
                    </div>
                  </fieldset>
                  <div className="web-quality"><span>Resolução</span><strong>{aspect === '9:16' ? '360 × 640' : '640 × 360'}</strong></div>
                  <div className="web-quality"><span>Saída</span><strong>MP4 · H.264</strong></div>
                  <div className="web-quality"><span>Motor</span><strong>FFmpeg WebAssembly</strong></div>
                  <div className="web-info"><Info size={18} aria-hidden="true"/><span>A primeira exportação baixa o motor (~31 MB). Renderizar no navegador pode ser mais lento que na versão desktop.</span></div>
                  {error && <div className="web-error" role="alert"><Info size={19} aria-hidden="true"/><span>{error}</span><button type="button" aria-label="Fechar aviso de erro" onClick={()=>setError('')}><X size={16}/></button></div>}
                  {busy && <div className="web-processing" role="status" aria-live="polite"><span><LoaderCircle size={17} className="spin" aria-hidden="true"/>{status || 'Preparando exportação…'}</span><div className="web-progress-track" role="progressbar" aria-label="Progresso da exportação" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress}><div style={{width:progress+'%'}}/></div></div>}
                  {downloadUrl ? <a className="web-export-button" href={downloadUrl} download="AutoEditor-Studio-Web.mp4"><ArrowDownToLine size={19} aria-hidden="true"/> Baixar vídeo MP4 ({size(outputSize)})</a> : <button className="web-export-button" type="button" onClick={createVideo} disabled={!canExport}>{busy ? <LoaderCircle size={19} className="spin" aria-hidden="true"/> : <Play size={17} fill="currentColor" aria-hidden="true"/>}{busy ? 'Processando…' : 'Exportar vídeo'}</button>}
                  {downloadUrl && <p className="web-ready" role="status"><BadgeCheck size={17} aria-hidden="true"/> Exportação concluída. Seu vídeo está pronto.</p>}
                </div>
                <div className="web-privacy"><ShieldCheck size={23} aria-hidden="true"/><div><strong>Seus arquivos, seu controle.</strong><p>Vídeos são processados no navegador. O motor WebAssembly é baixado de um CDN; o arquivo de vídeo não é enviado ao CDN nem ao GitHub.</p></div></div>
              </div>
              </>}
            </div>
            <section className="web-optional" aria-labelledby="optional-heading">
              <div className="web-optional-heading">
                <div><span className="section-kicker">PERSONALIZE QUANDO QUISER</span><h3 id="optional-heading">Ferramentas adicionais</h3>
                  <p>Você não precisa configurar tudo. Abra somente o recurso que vai usar.</p></div>
              </div>
              <div className="web-optional-selector" role="group" aria-label="Escolher ferramenta adicional">
                <button type="button" aria-expanded={openTool==='captions'} aria-controls="studio-captions"
                  className={openTool==='captions'?'active':''} onClick={()=>toggleTool('captions')}>
                  <span><Scissors size={16} aria-hidden="true"/> Legendas</span><small>{subtitles.length?subtitles.length+' trecho(s)':'Opcional'}</small>
                </button>
                <button type="button" aria-expanded={openTool==='script'} aria-controls="studio-script"
                  className={openTool==='script'?'active':''} onClick={()=>toggleTool('script')}>
                  <span><Sparkles size={16} aria-hidden="true"/> Roteiro</span><small>{scenes.length?scenes.length+' cena(s)':'Opcional'}</small>
                </button>
                <button type="button" aria-expanded={openTool==='project'} aria-controls="studio-project"
                  className={openTool==='project'?'active':''} onClick={()=>toggleTool('project')}>
                  <span><HardDrive size={16} aria-hidden="true"/> Meu projeto</span><small>Salvar ou importar</small>
                </button>
              </div>
              {openTool==='captions' && <Suspense fallback={<div className="web-tool-loading" role="status">Abrindo legendas…</div>}>
            <div id="studio-captions" className="web-captions"><SubtitleStudio mode="web" subtitles={subtitles} onChange={setSubtitles}
              mediaDuration={duration} previewTime={previewTime} disabled={busy} /></div>
              </Suspense>}
              {openTool==='script' && <Suspense fallback={<div className="web-tool-loading" role="status">Abrindo roteiro…</div>}><div className="web-single-tool">
<StoryStudio mode="web" aspect={aspect} script={script} scenes={scenes}
                scenePictures={scenePictures} onScenePicturesChange={setScenePictures}
                onChange={({script:next,scenes:nextScenes})=>{setScript(next);setScenes(nextScenes);}} />
              </div></Suspense>}
              {openTool==='project' && <Suspense fallback={<div className="web-tool-loading" role="status">Abrindo projeto…</div>}><div className="web-single-tool">
<ProjectExchange name={projectName} aspect={aspect} media={file?{name:file.name,size:file.size,duration}:reference}
                start={Number(start)||0} end={Number(end)||0} clips={clips} script={script} scenes={scenes} voiceEngine={voiceEngine} subtitles={subtitles} burnSubtitles={burnSubtitles}
                onImport={importPortableProject} disabled={busy} />
              </div></Suspense>}
            </section>
            <details className="web-draft-details">
              <summary><ShieldCheck size={16} aria-hidden="true"/> Rascunho no navegador <span>Como o seu progresso é salvo</span></summary>
            <div className="web-draft-bar" aria-label="Rascunho local do editor">
              <div><strong>Projeto neste navegador</strong><p>{draftMessage}</p></div>
              <button type="button" disabled={busy} onClick={resetDraft}>Limpar rascunho</button>
            </div>
            </details>
          </section>
          <section className="web-bottom" id="como-funciona" aria-labelledby="about-title"><div><span className="section-kicker">POR QUE A VERSÃO WEB?</span><h2 id="about-title">Simples de abrir.<br/>Fácil de criar.</h2><p>Uma primeira versão para cortes rápidos. Quer importar arquivos maiores, montar vídeos longos ou exportar em HD? O projeto desktop tem mais capacidade.</p><a href="https://github.com/HelioConde/AutoEditorVideo" className="web-bottom-link">Conhecer a versão desktop <ArrowRight size={18}/></a></div><div className="web-bottom-features"><div><HardDrive size={21}/><strong>Sem uploads para servidor</strong><p>O arquivo fica no dispositivo durante a edição.</p></div><div><Clock3 size={21}/><strong>Ideal para cortes curtos</strong><p>Exporte trechos de até 20 segundos por vez.</p></div></div></section>
          <footer className="web-footer"><span>© AutoEditor Studio · Ferramentas para contar boas histórias</span><a href="https://github.com/HelioConde/AutoEditorVideo">Código aberto no GitHub ↗</a></footer>
        </main>
      </div>
    </>
  );
}
