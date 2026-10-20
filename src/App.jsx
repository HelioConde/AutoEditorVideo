import { useEffect, useRef, useState } from 'react';
import VideoTimeline from './components/VideoTimeline.jsx';
import WorkbenchNav from './components/WorkbenchNav.jsx';
import './editor-polish.css';
import SubtitleStudio from './components/SubtitleStudio.jsx';
import { validateSubtitles } from './subtitles.js';
import { normalizeClips } from './clip-utils.js';
import ProjectExchange from './components/ProjectExchange.jsx';
import StoryStudio from './components/StoryStudio.jsx';
import ShortsStudio from './components/ShortsStudio.jsx';
import { createProjectFile } from './project-format.js';
import { createSceneImages } from './scene-canvas.js';
import {
  ArrowDownToLine, ArrowLeft, ArrowRight, Check, CheckCircle2, ChevronRight,
  CircleAlert, Clock3, Clapperboard, FileVideo2, Film, FolderClosed,
  LayoutDashboard, LoaderCircle, Menu, MoreHorizontal, Play, Plus, Scissors,
  Settings2, Sparkles, UploadCloud, Video, WandSparkles, X
} from 'lucide-react';

async function api(path, options) {
  let response;
  try { response = await fetch('/api' + path, options); }
  catch { throw new Error('Não foi possível conectar ao motor local. Inicie também o servidor da API.'); }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || 'Não foi possível concluir a operação.');
  return data;
}
const json = (value) => ({ headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(value), method: 'POST' });
const formatTime = (seconds) => {
  const safe = Math.max(0, Math.floor(Number(seconds) || 0));
  return String(Math.floor(safe / 60)).padStart(2, '0') + ':' + String(safe % 60).padStart(2, '0');
};
const formatDate = (iso) => new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(iso));
const formatSize = (bytes) => (Number(bytes || 0) / 1024 / 1024).toLocaleString('pt-BR', { maximumFractionDigits: 1 }) + ' MB';

function CreateDialog({ onClose, onCreate, busy }) {
  const [name, setName] = useState('');
  const inputRef = useRef(null);
  const dialogRef = useRef(null);
  useEffect(() => {
    const previous = document.activeElement;
    inputRef.current?.focus();
    function keyDown(e) {
      if (e.key === 'Escape') onClose();
      if (e.key === 'Tab') {
        const items = [...dialogRef.current.querySelectorAll('button:not([disabled]),input:not([disabled])')];
        const first = items[0], last = items[items.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    }
    document.addEventListener('keydown', keyDown);
    return () => { document.removeEventListener('keydown', keyDown); previous?.focus?.(); };
  }, [onClose]);
  return (
    <div className="modal-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <section className="modal" role="dialog" aria-modal="true" aria-labelledby="create-title" ref={dialogRef}>
        <div className="modal-top"><div className="icon-box"><Film size={21} aria-hidden="true" /></div><button className="icon-button" aria-label="Fechar janela" onClick={onClose}><X size={20} /></button></div>
        <h2 id="create-title">Um novo projeto começa aqui.</h2>
        <p>Dê um nome ao projeto. Seus arquivos ficam armazenados no seu computador.</p>
        <form onSubmit={(e) => { e.preventDefault(); if (name.trim().length >= 2) onCreate(name.trim()); }}>
          <label htmlFor="project-name">Nome do projeto</label>
          <input id="project-name" ref={inputRef} placeholder="Ex.: Melhores momentos da live" minLength={2} maxLength={64} value={name} onChange={e => setName(e.target.value)} required />
          <div className="modal-actions"><button type="button" className="btn btn-ghost" onClick={onClose}>Cancelar</button><button className="btn btn-primary" type="submit" disabled={busy || name.trim().length < 2}>{busy ? 'Criando…' : 'Criar projeto'} <ArrowRight size={16} aria-hidden="true" /></button></div>
        </form>
      </section>
    </div>
  );
}

function EmptyPreview() {
  return <div className="preview-empty">
    <div className="preview-ambient preview-ambient-one" aria-hidden="true" /><div className="preview-ambient preview-ambient-two" aria-hidden="true" />
    <div className="preview-graphic" aria-hidden="true"><span className="preview-graphic-mark"><Play size={28} fill="currentColor" /></span><span className="graphic-line line-one" /><span className="graphic-line line-two" /></div>
    <div className="preview-copy"><span className="eyebrow">ESPAÇO CRIATIVO</span><h3>Seu próximo vídeo começa aqui.</h3><p>Importe uma gravação para começar a editar.</p></div>
  </div>;
}
function Step({ number, title, description, complete = false, active = false }) {
  return <div className={'step ' + (complete ? 'complete ' : '') + (active ? 'active' : '')}>
    <div className="step-number">{complete ? <Check size={16} aria-hidden="true"/> : String(number).padStart(2, '0')}</div>
    <div><strong>{title}</strong><small>{description}</small></div>
  </div>;
}
function FutureCard({ icon: Icon, title, description }) {
  return <div className="future-card"><div className="future-icon"><Icon size={19} aria-hidden="true" /></div><div><strong>{title}</strong><p>{description}</p></div><span className="coming">Em breve</span></div>;
}

export default function App() {
  const [page, setPage] = useState('home');
  const [projects, setProjects] = useState([]);
  const [currentId, setCurrentId] = useState(null);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [notification, setNotification] = useState(null);
  const [start, setStart] = useState(0);
  const [end, setEnd] = useState(0);
  const [clips, setClips] = useState([]);
  const [script, setScript] = useState('');
  const [scenes, setScenes] = useState([]);
  const [subtitles,setSubtitles] = useState([]);
  const [analysisSignals,setAnalysisSignals] = useState(null);
  const [analysisProjectId,setAnalysisProjectId] = useState(null);
  const [analysisMediaFilename,setAnalysisMediaFilename] = useState(null);
  const [analysisBusy,setAnalysisBusy] = useState(false);
  const [transcriptionRevision,setTranscriptionRevision] = useState(null);
  const [burnSubtitles,setBurnSubtitles] = useState(false);
  const [previewTime,setPreviewTime] = useState(0);
  const [narrating, setNarrating] = useState(false);
  const [voiceEngine, setVoiceEngine] = useState('system');
  const [scenePictures, setScenePictures] = useState([]);
  const playbackEnd = useRef(null);
  const playerVideoRef = useRef(null);
  const [aspect, setAspect] = useState('9:16');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const inputRef = useRef(null);
  const current = projects.find(p => p.id === currentId);
  const ready = projects.reduce((sum,p) => sum + (p.exports || []).filter(e => e.status === 'ready').length, 0);
  const processing = projects.some(p => (p.exports || []).some(e => e.status === 'processing') || p.transcription?.status==='processing');

  async function refresh(silent = false) {
    try {
      const data = await api('/projects');
      // Merge server updates with optimistic creations. An older list response
      // must never erase a project created while the request was in flight.
      setProjects(previous => {
        const merged=new Map(data.projects.map(p=>[p.id,p]));
        for(const project of previous) if(!merged.has(project.id))merged.set(project.id,project);
        return [...merged.values()];
      });
      if (!silent) setNotification(null);
    } catch (e) { if (!silent) setNotification({ type: 'error', message: e.message }); }
    finally { if (!silent) setLoading(false); }
  }
  useEffect(() => {
    refresh();
    api('/health').then(setHealth).catch(() => setHealth({ ffmpeg: false, ffprobe: false }));
  }, []);
  useEffect(() => {
    if (!processing) return;
    const timer = window.setInterval(() => refresh(true), 1500);
    return () => window.clearInterval(timer);
  }, [processing]);
  useEffect(() => {
    // Hydrate portable edits when entering a project or replacing its media.
    const edit=current?.edit;
    setStart(edit?.start ?? 0);
    setEnd(edit?.end ?? (Number(current?.media?.duration) || 0));
    setClips(edit?.clips || []);
    setAspect(edit?.aspect || '9:16');
    setScript(edit?.script || '');
    setScenes(edit?.scenes || []);
    setSubtitles(edit?.subtitles || []);
    setTranscriptionRevision(current?.transcription?.status==='ready' ? current.transcription.updatedAt : null);
    setBurnSubtitles(edit?.burnSubtitles || false);
    setPreviewTime(0);
    setVoiceEngine(edit?.voiceEngine || 'system');
    setScenePictures([]);
    playbackEnd.current = null;
  }, [currentId, current?.media?.id]);
  useEffect(() => {
    if(current?.transcription?.status==='ready' && current?.edit?.subtitles) {
      setSubtitles(current.edit.subtitles);
      setTranscriptionRevision(current.transcription.updatedAt);
    }
  },[currentId,current?.transcription?.status,current?.transcription?.updatedAt]);
  useEffect(() => {
    if (!currentId || !current || current.transcription?.status==='processing') return;
    const timer=window.setTimeout(async()=>{
      const payload=createProjectFile({name:current.name,aspect,media:current.media||current.reference,
        start:Number(start)||0,end:Number(end)||0,clips,script,scenes,voiceEngine,subtitles,burnSubtitles});
      payload.transcriptionVersion=transcriptionRevision;
      try { await api('/projects/'+currentId+'/edit',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}); }
      catch(e){ console.warn('Não foi possível salvar a edição:',e.message); }
    },1000);
    return ()=>window.clearTimeout(timer);
  }, [currentId, current?.media?.id, aspect, start, end, clips, script, scenes, voiceEngine,subtitles,burnSubtitles,transcriptionRevision]);

  useEffect(() => { document.title = (page === 'editor' ? 'Editor' : 'Painel') + ' · AutoEditor Studio'; }, [page]);
  function openProject(id) { setCurrentId(id); setPage('editor'); setSidebarOpen(false); window.scrollTo(0,0); }
  function showHome() { setPage('home'); setSidebarOpen(false); }
  function notice(message, type = 'success') { setNotification({ message, type }); }
  async function create(name) {
    setBusy(true);
    try {
      const data = await api('/projects', json({ name }));
      setProjects(previous => [data.project, ...previous]);
      setModal(false);
      openProject(data.project.id);
      notice('Projeto criado. Agora você pode importar seu vídeo.');
    } catch (e) { notice(e.message, 'error'); }
    finally { setBusy(false); }
  }
  async function upload(file) {
    if (!file) return;
    if (!currentId) return;
    if (file.size > 512 * 1024 * 1024) { notice('Arquivo acima de 512 MB. Escolha uma gravação menor.', 'error'); return; }
    setUploading(true);
    try {
      const form = new FormData(); form.append('file', file);
      const data = await api('/projects/' + currentId + '/media', { method: 'POST', body: form });
      setProjects(previous => previous.map(p => p.id === data.project.id ? data.project : p));
      notice('Vídeo importado e pronto para editar.');
    } catch (e) { notice(e.message, 'error'); }
    finally { setUploading(false); if (inputRef.current) inputRef.current.value = ''; }
  }
  function previewSegment(segment) {
    const video = playerVideoRef.current;
    if (!video || !current?.media) return;
    playbackEnd.current = Number(segment.end);
    video.currentTime = Math.max(0, Number(segment.start));
    video.play().catch(() => notice('Não foi possível reproduzir esta prévia.', 'error'));
  }
  function stopAtSegmentEnd(event) {
    if (playbackEnd.current !== null && event.currentTarget.currentTime >= playbackEnd.current - .05) {
      event.currentTarget.pause();
      playbackEnd.current = null;
    }
  }
  async function exportVideo() {
    if (!current) return;
    setBusy(true);
    try {
      const data = await api('/projects/' + current.id + '/exports', json({ start: Number(start), end: Number(end), aspect, subtitles, burnSubtitles, ...(clips.length ? { segments: clips } : {}) }));
      setProjects(previous => previous.map(p => p.id === data.project.id ? data.project : p));
      notice('Exportação iniciada. Você pode continuar no estúdio.');
    } catch (e) { notice(e.message, 'error'); }
    finally { setBusy(false); }
  }
  async function importPortableProject(data) {
    const manifest=createProjectFile({name:data.name,aspect:data.aspect,media:data.media,
      start:data.edit.start,end:data.edit.end,clips:data.edit.clips,script:data.edit.script,scenes:data.edit.scenes,voiceEngine:data.edit.voiceEngine,subtitles:data.edit.subtitles,burnSubtitles:data.edit.burnSubtitles});
    const result=await api('/projects/import',json(manifest));
    setProjects(previous=>[result.project,...previous]);
    openProject(result.project.id);
    notice('Projeto importado. Reimporte a mídia original para ativar os cortes.');
  }
  async function requestTranscription() {
    if(!current?.media)return;
    try{
      const result=await api('/projects/'+current.id+'/transcribe',json({}));
      setProjects(previous=>previous.map(p=>p.id===result.project.id?result.project:p));
      notice('Transcrição iniciada no seu computador. Revise os textos antes de exportar.');
    }catch(e){notice(e.message,'error');}
  }
  function useShort(candidate) {
    setClips([{start:candidate.start,end:candidate.end}]);
    setStart(candidate.start);setEnd(candidate.end);
    setAspect('9:16');setBurnSubtitles(true);
    notice('Trecho adicionado à timeline em 9:16. Revise o corte e exporte quando quiser.');
    document.getElementById('studio-cuts')?.scrollIntoView({block:'start',behavior:'smooth'});
  }
  async function analyzeShortSignals() {
    if(!current?.media || analysisBusy)return false;
    setAnalysisBusy(true);
    try {
      const data=await api('/projects/'+current.id+'/signals');
      setAnalysisSignals(data.signals);
      setAnalysisProjectId(current.id);
      setAnalysisMediaFilename(current.media.fileName);
      notice('Áudio e mudanças de cena analisados localmente. Revise as sugestões.');
      return true;
    }catch(e) {
      notice('A análise audiovisual não foi concluída. Você ainda pode usar a análise textual. '+e.message,'error');
      return false;
    }finally{setAnalysisBusy(false);}
  }
  async function generateShorts(candidates,profile='podcast') {
    if(!current?.media||!candidates?.length||busy||processing)return;
    setBusy(true);
    try {
      const result=await api('/projects/'+current.id+'/shorts',json({count:candidates.length,subtitles,profile}));
      setProjects(previous=>previous.map(p=>p.id===result.project.id?result.project:p));
      notice(result.suggestions.length+' Shorts legendados iniciados. Acompanhe na seção Exportações.');
    }catch(e){notice(e.message,'error');}
    finally{setBusy(false);}
  }
  async function renderNarratedVideo(sceneList) {
    if (!current || narrating) return;
    setNarrating(true);
    try {
      const images=await createSceneImages(sceneList,aspect,scenePictures);
      const result=await api('/projects/'+current.id+'/narration',json({scenes:sceneList,images,aspect,voiceEngine}));
      setProjects(prev=>prev.map(p=>p.id===result.project.id?result.project:p));
      notice('Vídeo narrado iniciado. Acompanhe em Exportações.');
    } catch(e) { notice(e.message,'error'); }
    finally {setNarrating(false);}
  }
  const exportList = current?.exports || [];
  const exportPlan = normalizeClips({ segments: clips.length ? clips : undefined, start, end, duration: current?.media?.duration || 0, maxTotal: 600 });
  const canExport = Boolean(current?.media && health?.ffmpeg && !exportPlan.error && !validateSubtitles(subtitles).error && !busy && current.transcription?.status!=='processing');
  return <>
    <a className="skip-link" href="#main">Pular para o conteúdo</a>
    <div className="app-layout">
      <aside className={'sidebar ' + (sidebarOpen ? 'sidebar-open' : '')} aria-label="Navegação principal">
        <div className="brand"><span className="brand-mark"><Clapperboard size={22} strokeWidth={2.4} aria-hidden="true" /></span><span className="brand-name">AutoEditor<span>Studio</span></span><button className="icon-button sidebar-close" type="button" aria-label="Fechar menu" onClick={() => setSidebarOpen(false)}><X size={18} aria-hidden="true" /></button></div>
        <div className="side-section-label">WORKSPACE</div>
        <nav className="side-nav" aria-label="Seções">
          <button className={'nav-item ' + (page === 'home' ? 'active' : '')} aria-current={page === 'home' ? 'page' : undefined} onClick={showHome}><LayoutDashboard size={18} aria-hidden="true" />Visão geral</button>
          <button className={'nav-item ' + (page === 'editor' ? 'active' : '')} aria-current={page === 'editor' ? 'page' : undefined} onClick={() => currentId ? openProject(currentId) : showHome()}><Scissors size={18} aria-hidden="true" />Editor de vídeo</button>
          <button className="nav-item" onClick={() => {showHome();document.getElementById('projects-title')?.scrollIntoView({behavior:'smooth'});}}><FolderClosed size={18} aria-hidden="true" />Meus projetos<span className="nav-counter">{projects.length}</span></button>
        </nav>
        <div className="side-grow" />
        <div className="sidebar-help"><span className="help-icon"><Sparkles size={17} aria-hidden="true" /></span><strong>Crie no seu ritmo.</strong><p>Seu estúdio funciona localmente. Sem assinatura para começar.</p><button className="help-cta" onClick={() => setModal(true)}>Novo projeto <ArrowRight size={16} aria-hidden="true" /></button></div>
        <div className="sidebar-bottom"><div className={'status-dot ' + (health?.ffmpeg ? 'online' : '')}/><span>{health === null ? 'Verificando motor…' : health.ffmpeg ? 'Motor de vídeo disponível' : 'FFmpeg não encontrado'}</span><span className="version">BETA 2.5</span></div>
      </aside>
      {sidebarOpen && <button className="mobile-overlay" aria-label="Fechar ao tocar fora do menu" onClick={() => setSidebarOpen(false)} />}
      <div className="main-shell">
        <header className="topbar">
          <button className="icon-button menu-button" aria-label="Abrir menu" onClick={() => setSidebarOpen(true)}><Menu size={23} /></button>
          <div className="breadcrumb"><span>Workspace</span><ChevronRight size={15} aria-hidden="true"/><strong>{page === 'editor' ? 'Editor' : 'Visão geral'}</strong></div>
          <div className="topbar-right"><span className="topbar-local"><span className="local-circle" />Processamento local</span><button className="btn btn-primary btn-small" onClick={() => setModal(true)}><Plus size={16} aria-hidden="true" /> Novo projeto</button></div>
        </header>
        <main id="main" tabIndex={-1} className="content">
          {notification && <div className={'notice notice-' + notification.type} role="status" aria-live="polite"><span>{notification.type === 'error' ? <CircleAlert size={19} aria-hidden="true"/> : <CheckCircle2 size={19} aria-hidden="true" />}{notification.message}</span><button aria-label="Dispensar aviso" onClick={() => setNotification(null)}><X size={18}/></button></div>}
          {page === 'home' ? <>
            <div className="page-eyebrow"><span className="spark-dot"/> SEU ESPAÇO DE CRIAÇÃO</div>
            <div className="page-heading"><div><h1>Bom criar começa aqui<span className="heading-period">.</span></h1><p>Da gravação à versão final, tudo no seu espaço de trabalho.</p></div><button className="btn btn-outline" onClick={() => setModal(true)}><Plus size={17} aria-hidden="true"/> Criar projeto</button></div>
            <section className="hero">
              <div className="hero-copy"><span className="hero-pill"><Sparkles size={13} aria-hidden="true" /> SEU ESTÚDIO CRIATIVO</span><h2>Grandes histórias merecem edições simples<span>.</span></h2><p>Importe sua gravação, escolha os melhores segundos e exporte no formato certo. Sem complicar o seu fluxo.</p><button className="btn btn-dark" onClick={() => setModal(true)}>Começar a criar <ArrowRight size={18} aria-hidden="true" /></button></div>
              <div className="hero-art" aria-hidden="true"><div className="art-window"><div className="art-video"><div className="art-sun"/><div className="art-mountain m1"/><div className="art-mountain m2"/><span><Play size={22} fill="currentColor"/></span></div><div className="art-timeline"><i/><i/><i/><i/><i/></div></div><div className="floating-sticker"><Check size={15}/> PRONTO PARA CRIAR</div></div>
            </section>
            <div className="stats-grid">
              <div className="stat-card"><span className="stat-icon"><FolderClosed size={18}/></span><span className="stat-value">{projects.length}</span><span className="stat-label">Projetos criados</span></div>
              <div className="stat-card"><span className="stat-icon"><FileVideo2 size={18}/></span><span className="stat-value">{projects.filter(p => Boolean(p.media)).length}</span><span className="stat-label">Gravações importadas</span></div>
              <div className="stat-card"><span className="stat-icon"><CheckCircle2 size={18}/></span><span className="stat-value">{ready}</span><span className="stat-label">Vídeos exportados</span></div>
            </div>
            <section className="section-area" aria-labelledby="projects-title"><div className="section-heading"><div><span className="section-kicker">CONTINUE CRIANDO</span><h2 id="projects-title">Seus projetos</h2></div><span className="section-count">{projects.length} no total</span></div>
              {loading ? <p className="muted" role="status">Carregando projetos…</p> : projects.length === 0 ? <div className="empty-projects"><div className="empty-project-icon"><Film size={28} aria-hidden="true" /></div><h3>Seu primeiro projeto está esperando.</h3><p>Crie um espaço, importe uma gravação e dê vida à sua próxima edição.</p><button className="btn btn-primary" onClick={() => setModal(true)}><Plus size={17} aria-hidden="true"/> Criar primeiro projeto</button></div> : <div className="project-grid">{projects.map(p => <button key={p.id} className="project-card" onClick={() => openProject(p.id)}><span className="project-thumbnail"><Film size={31} aria-hidden="true"/>{p.media && <span className="thumbnail-tag"><Video size={12}/> Vídeo importado</span>}</span><span className="project-meta"><strong title={p.name}>{p.name}</strong><span>Criado em {formatDate(p.createdAt)}</span></span><span className="project-arrow"><ArrowRight size={17} aria-hidden="true"/></span></button>)}</div>}
            </section>
            <section className="section-area future-section" aria-labelledby="future-title"><div className="section-heading"><div><span className="section-kicker">O QUE VEM AÍ</span><h2 id="future-title">Mais tempo para criar</h2></div></div><div className="future-grid"><FutureCard icon={WandSparkles} title="Biblioteca sonora" description="Músicas e efeitos para personalizar a edição."/><FutureCard icon={Scissors} title="Corte inteligente" description="Remoção de silêncios e pausas longas."/><FutureCard icon={Settings2} title="Templates prontos" description="Layouts e animações para vídeos curtos."/></div></section>
          </> : <section className="editor-page" aria-labelledby="editor-title">
            <div className="editor-heading"><button className="back-link" onClick={showHome}><ArrowLeft size={17}/> Voltar ao painel</button><div className="editor-title-row"><div><span className="section-kicker">WORKSPACE / EDITOR</span><h1 id="editor-title">{current?.name || 'Projeto não encontrado'}</h1><p>Um fluxo simples para transformar sua gravação em vídeo.</p></div><span className="editor-version">Editor beta</span></div></div>
            {current && <WorkbenchNav compact />}
            {!current ? <div className="empty-projects"><p>Selecione ou crie um projeto para começar.</p><button className="btn btn-primary" onClick={showHome}>Ver meus projetos</button></div> :
            <div className="editor-grid"><div className="editor-primary"><div id="studio-video" className="panel preview-panel"><div className="panel-title"><span><Film size={17} aria-hidden="true"/> Pré-visualização</span><span className="panel-subtitle">{current.media ? current.media.originalName : 'Nenhuma mídia importada'}</span></div>{current.media ? <div className="video-stage"><video ref={playerVideoRef} controls preload="metadata" onTimeUpdate={e=>{stopAtSegmentEnd(e);setPreviewTime(e.currentTarget.currentTime);}} key={current.media.id} src={'/api/projects/' + current.id + '/media'} aria-label="Vídeo carregado" />
                  {subtitles.some(c=>previewTime>=c.start&&previewTime<c.end)&&
                    <div className="video-caption-overlay" aria-hidden="true">{subtitles.find(c=>previewTime>=c.start&&previewTime<c.end)?.text}</div>}
                  </div> : <EmptyPreview />}</div>
              <ShortsStudio subtitles={subtitles} duration={current.media?.duration||0}
                mediaReady={Boolean(current.media)}
                whisperAvailable={Boolean(health?.whisper)}
                transcribing={current.transcription?.status==='processing'}
                disabled={busy||processing||uploading}
                onTranscribe={requestTranscription}
                onPreview={previewSegment}
                onUse={useShort} onGenerate={generateShorts}
                onAnalyze={analyzeShortSignals} analysisBusy={analysisBusy}
                analysisSignals={analysisProjectId===currentId && analysisMediaFilename===current.media?.fileName ? analysisSignals : null}/>
              <div id="studio-cuts" className="panel trim-panel"><div className="panel-title"><span><Scissors size={18} aria-hidden="true"/> Definir trecho</span><span className="panel-subtitle">Selecione os quadros e organize cortes</span></div><VideoTimeline source={current.media ? '/api/projects/' + current.id + '/media' : null}
                  duration={current.media?.duration || 0} start={start} end={end}
                  onStartChange={setStart} onEndChange={setEnd} clips={clips} onClipsChange={setClips}
                  onPreview={previewSegment} disabled={!current.media || busy} maxTotal={600} variant="desktop" /><div className="trim-fields"><label>Início <span>(segundos)</span><input type="number" aria-label="Início em segundos" min="0" step=".1" max={current.media?.duration || 0} disabled={!current.media} value={start} onChange={e=>setStart(e.target.value)} /></label><label>Fim <span>(segundos)</span><input type="number" aria-label="Fim em segundos" min="0" step=".1" max={current.media?.duration || 0} disabled={!current.media} value={end} onChange={e=>setEnd(e.target.value)} /></label><div className="duration-pill"><Clock3 size={15}/> {formatTime(Number(end)-Number(start))}</div></div>{current.media && Number(end) <= Number(start) && <p className="field-error" role="alert">O fim deve ser maior que o início.</p>}</div>
              <div id="studio-captions" className="subtitle-workspace">
                <SubtitleStudio mode="desktop" subtitles={subtitles} onChange={setSubtitles}
                  mediaDuration={current.media?.duration||0} previewTime={previewTime}
                  disabled={busy||uploading||current.transcription?.status==='processing'} transcribing={current.transcription?.status==='processing'}
                  whisperAvailable={Boolean(health?.whisper)} onTranscribe={requestTranscription}/>
                <label className="sub-burn"><input type="checkbox" checked={burnSubtitles}
                  disabled={!current.media||busy} onChange={e=>setBurnSubtitles(e.target.checked)}/>
                  Gravar legendas no MP4 dos cortes (FFmpeg desktop)</label>
                {current.transcription?.status==='error' && <p className="field-error" role="alert">{current.transcription.error}</p>}
              </div>
              <StoryStudio mode="desktop" script={script} scenes={scenes} aspect={aspect}
                voiceEngine={voiceEngine} onVoiceEngineChange={setVoiceEngine} voiceCapabilities={health?.voices}
                scenePictures={scenePictures} onScenePicturesChange={setScenePictures}
                onChange={({script:next,scenes:nextScenes})=>{setScript(next);setScenes(nextScenes);}}
                onRender={renderNarratedVideo} renderBusy={narrating} />
              <ProjectExchange name={current.name} aspect={aspect} media={current.media||current.reference}
                start={Number(start)||0} end={Number(end)||0} clips={clips} script={script} scenes={scenes} voiceEngine={voiceEngine} subtitles={subtitles} burnSubtitles={burnSubtitles}
                onImport={importPortableProject} disabled={busy||narrating} />
              {exportList.length > 0 && <div className="panel exports-panel"><div className="panel-title"><span><ArrowDownToLine size={18}/> Exportações</span><span className="panel-subtitle">{exportList.length} arquivo(s)</span></div><ul className="export-list">{exportList.map(job=><li key={job.id}><span className="export-status-icon">{job.status==='ready'?<CheckCircle2 size={19}/>:job.status==='processing'?<LoaderCircle className="spin" size={19}/>:<CircleAlert size={19}/>}</span><div><strong>{job.kind==='narration'?'Vídeo narrado':job.kind==='short'?'Short automático':job.aspect==='9:16'?'Vídeo vertical':'Vídeo horizontal'}</strong><small>{job.status==='ready'?'Exportação concluída':job.status==='processing'?'Processando vídeo…':job.error || 'Exportação interrompida'}{job.kind==='short'&&job.title?' · '+job.title.slice(0,55):''}</small></div>{job.status==='ready'&&<a className="export-download" href={'/api/projects/'+current.id+'/exports/'+job.id+'/download'} download aria-label="Baixar vídeo exportado"><ArrowDownToLine size={17}/></a>}</li>)}</ul></div>}
            </div>
            <div className="editor-secondary"><div className="panel workflow-panel"><div className="panel-title"><span><Clapperboard size={18}/> Seu fluxo</span></div><div className="steps"><Step number={1} title="Importar vídeo" description="MP4, MOV, WebM ou MKV" complete={Boolean(current.media)} active={!current.media}/><Step number={2} title="Selecionar trecho" description="Ajuste a timeline ou monte uma sequência" complete={Boolean(current.media && Number(end)>Number(start))} active={Boolean(current.media)}/><Step number={3} title="Exportar" description="Renderize em MP4" active={Boolean(current.media)}/></div></div>
              <div className="panel upload-panel"><div className="panel-title"><span><UploadCloud size={18}/> Arquivo de origem</span></div><input id="media-file" className="visually-hidden" ref={inputRef} type="file" accept=".mp4,.mov,.webm,.mkv,video/*" onChange={e=>upload(e.target.files?.[0])} disabled={uploading}/><label className={'upload-target ' + (uploading?'uploading':'')} htmlFor="media-file"><span className="upload-icon">{uploading?<LoaderCircle className="spin" size={23}/>:<UploadCloud size={25}/>}</span><strong>{uploading?'Importando arquivo…':current.media?'Substituir gravação':'Escolher vídeo'}</strong><small>Até 512 MB · formato de vídeo</small></label>{current.media && <div className="file-detail"><FileVideo2 size={19} /><div><strong title={current.media.originalName}>{current.media.originalName}</strong><small>{formatSize(current.media.size)} · {formatTime(current.media.duration)}</small></div><CheckCircle2 size={17} className="file-check"/></div>}</div>
              <div className="panel export-panel"><div className="panel-title"><span><Settings2 size={18}/> Configurações de exportação</span></div><fieldset className="format-fieldset"><legend>Proporção do vídeo</legend><div className="aspect-group"><label className={'aspect-option '+(aspect==='9:16'?'selected':'')}><input type="radio" name="aspect" value="9:16" checked={aspect==='9:16'} onChange={()=>setAspect('9:16')}/><span className="aspect-shape portrait"/><strong>9:16</strong><small>Shorts / Reels</small></label><label className={'aspect-option '+(aspect==='16:9'?'selected':'')}><input type="radio" name="aspect" value="16:9" checked={aspect==='16:9'} onChange={()=>setAspect('16:9')}/><span className="aspect-shape landscape"/><strong>16:9</strong><small>YouTube</small></label></div></fieldset><p className="export-note">Saída MP4 · H.264 · 30 FPS · processamento local</p>{!health?.ffmpeg && <p className="engine-warning"><CircleAlert size={17}/> Instale o FFmpeg e reinicie o servidor para exportar.</p>}<button className="btn btn-primary export-button" disabled={!canExport} onClick={exportVideo}>{busy?'Iniciando…':'Exportar vídeo'}<ArrowRight size={18}/></button></div>
            </div></div>}
          </section>}
          <footer className="footer"><span>© AutoEditor Studio · Feito para criar</span><span>Arquivos e processamento no seu computador</span></footer>
        </main>
      </div>
    </div>
    {modal && <CreateDialog busy={busy} onClose={()=>setModal(false)} onCreate={create}/>}
  </>;
}
