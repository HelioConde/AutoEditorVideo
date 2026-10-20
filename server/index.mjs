import express from 'express';
import multer from 'multer';
import { spawn, spawnSync } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { normalizeClips } from '../src/clip-utils.js';
import { parseProjectFile, validateScenes } from '../src/project-format.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(process.env.DATA_DIR || path.join(HERE, '..', 'data'));
const PROJECTS_FILE = path.join(ROOT, 'projects.json');
const UPLOADS = path.join(ROOT, 'uploads');
const TMP = path.join(ROOT, 'tmp');
const FFmpeg = process.env.FFMPEG_PATH || 'ffmpeg';
const FFprobe = process.env.FFPROBE_PATH || 'ffprobe';
const VALID_EXT = new Set(['.mp4', '.mov', '.webm', '.mkv', '.m4v']);
fs.mkdirSync(TMP, { recursive: true });
fs.mkdirSync(UPLOADS, { recursive: true });

function save(projects) {
  const temp = PROJECTS_FILE + '.tmp';
  fs.writeFileSync(temp, JSON.stringify(projects, null, 2));
  fs.renameSync(temp, PROJECTS_FILE);
}
function load() {
  if (!fs.existsSync(PROJECTS_FILE)) return [];
  const projects = JSON.parse(fs.readFileSync(PROJECTS_FILE, 'utf8'));
  return projects.map(p => ({ ...p, exports: (p.exports || []).map(j => j.status === 'processing' ? { ...j, status: 'error', error: 'Processamento interrompido. Exporte novamente.' } : j) }));
}
let projects = load();
if (projects.some(p => p.exports.some(j => j.error === 'Processamento interrompido. Exporte novamente.'))) save(projects);
const findProject = id => projects.find(p => p.id === id);
function probe(file) {
  const result = spawnSync(FFprobe, ['-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=codec_type', '-show_entries', 'format=duration', '-of', 'json', file], { encoding: 'utf8', timeout: 25000, maxBuffer: 1024 * 1024 });
  if (result.error || result.status !== 0) throw new Error('Não foi possível ler o vídeo. Verifique se o FFprobe está instalado e se o arquivo é válido.');
  const info = JSON.parse(result.stdout);
  const duration = Number(info.format?.duration);
  if (!info.streams?.some(s => s.codec_type === 'video') || !Number.isFinite(duration) || duration <= 0) throw new Error('Arquivo sem faixa de vídeo válida.');
  return Math.round(duration * 10) / 10;
}
function toolAvailable(tool) {
  const result = spawnSync(tool, ['-version'], { encoding: 'utf8', timeout: 5000 });
  return !result.error && result.status === 0;
}
const upload = multer({
  dest: TMP,
  limits: { fileSize: 512 * 1024 * 1024, files: 1 },
  fileFilter: (_req, file, cb) => {
    const ext = path.extname(file.originalname).toLowerCase();
    cb(VALID_EXT.has(ext) ? null : new Error('Formato não suportado. Use MP4, MOV, WebM ou MKV.'), VALID_EXT.has(ext));
  }
});
const publicProject = p => ({
  id: p.id, name: p.name, createdAt: p.createdAt, media: p.media || null,
  reference: p.reference || null, edit: p.edit || null,
  exports: (p.exports || []).map(({ id, status, aspect, createdAt, error, kind }) => ({ id, status, aspect, createdAt, error, kind:kind||'cuts' }))
});

function runFFmpeg(args) {
  return new Promise((resolve, reject) => {
    let child;
    try { child = spawn(FFmpeg, args, { windowsHide: true }); }
    catch (e) { return reject(e); }
    let stderr = '';
    child.stderr.on('data', chunk => { stderr = (stderr + chunk.toString()).slice(-1800); });
    child.once('error', reject);
    child.once('close', code => {
      if (code === 0) resolve();
      else reject(new Error('FFmpeg encerrou com código ' + code + ': ' + stderr));
    });
  });
}
async function render(project, job, source, output, clips, aspect) {
  const vertical = aspect === '9:16';
  const w = vertical ? 720 : 1280, h = vertical ? 1280 : 720;
  const filter = 'scale=' + w + ':' + h + ':force_original_aspect_ratio=increase,crop=' + w + ':' + h + ',fps=30';
  // Every segment uses identical codecs, dimensions, frame rate and source
  // streams. Therefore the concat demuxer can concatenate without re-encoding.
  const makeArgs = (clip, dest) => [
    '-hide_banner', '-loglevel', 'error', '-y', '-i', source, '-ss', String(clip.start),
    '-t', String(clip.end - clip.start), '-vf', filter, '-c:v', 'libx264', '-preset', 'veryfast',
    '-crf', '23', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', dest
  ];
  let tmpFolder = null;
  try {
    if (clips.length === 1) {
      await runFFmpeg(makeArgs(clips[0], output));
    } else {
      tmpFolder = fs.mkdtempSync(path.join(UPLOADS, project.id, 'cuts-'));
      const names = [];
      for (let i = 0; i < clips.length; i++) {
        const part = 'part-' + i + '.mp4';
        await runFFmpeg(makeArgs(clips[i], path.join(tmpFolder, part)));
        names.push(part);
      }
      const listFile = path.join(tmpFolder, 'concat.txt');
      // filenames are generated internally: no user-controlled concat paths.
      fs.writeFileSync(listFile, names.map(name => "file '" + name + "'").join('\n') + '\n');
      await runFFmpeg(['-hide_banner', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', listFile, '-c', 'copy', '-movflags', '+faststart', output]);
    }
    if (!fs.existsSync(output) || fs.statSync(output).size === 0) throw new Error('Arquivo vazio');
    job.status = 'ready';
  } catch (e) {
    console.error('FFmpeg export failed:', e.message);
    job.status = 'error';
    job.error = 'Não foi possível unir os cortes. Verifique a mídia e tente novamente.';
    try { fs.unlinkSync(output); } catch {}
  } finally {
    if (tmpFolder) fs.rmSync(tmpFolder, { recursive: true, force: true });
    save(projects);
  }
}

// Narrated storyboard uses user-reviewed scene text and client-rendered PNG cards.
// Offline speech is provided by OS engines: Windows SAPI or espeak-ng on Linux.
async function runCommand(command,args) {
  return new Promise((resolve,reject)=>{
    const child=spawn(command,args,{windowsHide:true});
    let stderr='';
    child.stderr.on('data',x=>{stderr=(stderr+x.toString()).slice(-1000);});
    child.once('error',reject);
    child.once('close',code=>code===0?resolve():reject(new Error(stderr||command+' exited '+code)));
  });
}
async function renderNarration(project, job, scenes, images, aspect) {
  const folder=path.join(UPLOADS,project.id);
  const output=path.join(folder,job.filename);
  const tmp=fs.mkdtempSync(path.join(folder,'narration-'));
  try {
    const parts=[];
    for(let i=0;i<scenes.length;i++) {
      const stem='scene-'+i;
      const png=path.join(tmp,stem+'.png'),wav=path.join(tmp,stem+'.wav'),txt=path.join(tmp,stem+'.txt'),mp4=path.join(tmp,stem+'.mp4');
      const data=Buffer.from(images[i].slice('data:image/png;base64,'.length),'base64');
      if(data.byteLength>750000 || !data.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10])))
        throw new Error('Imagem da cena inválida.');
      fs.writeFileSync(png,data);
      fs.writeFileSync(txt,scenes[i].text,'utf8');
      if(process.platform==='win32') {
        await runCommand('powershell.exe',['-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
          '-File',path.join(HERE,'tts-windows.ps1'),'-TextFile',txt,'-OutputFile',wav]);
      } else {
        await runCommand('espeak-ng',['-v','pt-br','-s','158','-f',txt,'-w',wav]);
      }
      const vertical=aspect==='9:16',w=vertical?720:1280,h=vertical?1280:720;
      await runFFmpeg(['-hide_banner','-loglevel','error','-y','-loop','1','-framerate','24',
        '-i',png,'-i',wav,'-t',String(scenes[i].duration),
        '-vf','scale='+w+':'+h+',format=yuv420p','-af','apad',
        '-c:v','libx264','-preset','veryfast','-crf','24','-c:a','aac','-b:a','128k',
        '-r','24','-movflags','+faststart',mp4]);
      parts.push(path.basename(mp4));
    }
    const listFile=path.join(tmp,'concat.txt');
    fs.writeFileSync(listFile,parts.map(p=>"file '"+p+"'").join('\n')+'\n');
    await runFFmpeg(['-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',listFile,
      '-c','copy','-movflags','+faststart',output]);
    if(!fs.existsSync(output)||fs.statSync(output).size===0)throw new Error('MP4 vazio');
    job.status='ready';
  } catch(e) {
    job.status='error';job.error='Não foi possível gerar a narração. Verifique o motor de voz e os textos das cenas.';
    console.error('Narration export:',e.message);
    try{fs.unlinkSync(output);}catch{}
  } finally {
    fs.rmSync(tmp,{recursive:true,force:true});
    save(projects);
  }
}

export function createApp() {
  const app = express();
  app.disable('x-powered-by');
  app.use(express.json({ limit: '5mb' }));
  // Do not accept cross-origin writes to the unauthenticated local-only API.
  app.use('/api', (req, res, next) => {
    if (!['POST', 'PUT', 'PATCH', 'DELETE'].includes(req.method)) return next();
    const origin = req.get('origin');
    if (origin && !new Set(['http://127.0.0.1:5173', 'http://localhost:5173', 'http://127.0.0.1:3011', 'http://localhost:3011']).has(origin))
      return res.status(403).json({ error: 'Origem não autorizada para operação local.' });
    next();
  });
  app.get('/api/health', (_req, res) => res.json({ ffmpeg: toolAvailable(FFmpeg), ffprobe: toolAvailable(FFprobe),
    narration: process.platform === 'win32' || toolAvailable('espeak-ng'), version: '2.3-beta' }));
  app.get('/api/projects', (_req, res) => res.json({ projects: projects.map(publicProject).sort((a,b) => b.createdAt.localeCompare(a.createdAt)) }));
  app.post('/api/projects', (req, res) => {
    const name = typeof req.body?.name === 'string' ? req.body.name.trim() : '';
    if (name.length < 2 || name.length > 64) return res.status(400).json({ error: 'Use um nome entre 2 e 64 caracteres.' });
    const project = { id: randomUUID(), name, createdAt: new Date().toISOString(), media: null, reference:null, edit:null, exports: [] };
    projects.unshift(project);
    save(projects);
    res.status(201).json({ project: publicProject(project) });
  });
  app.post('/api/projects/import', (req, res) => {
    let imported;
    try { imported = parseProjectFile(req.body); }
    catch(e) { return res.status(400).json({error:e.message}); }
    const project={ id:randomUUID(),name:imported.name,createdAt:new Date().toISOString(), media:null,
      reference:imported.media,edit:{...imported.edit,aspect:imported.aspect},exports:[] };
    projects.unshift(project); save(projects);
    res.status(201).json({project:publicProject(project)});
  });
  app.put('/api/projects/:id/edit', (req,res) => {
    const p=findProject(req.params.id);
    if(!p)return res.status(404).json({error:'Projeto não encontrado.'});
    let parsed;
    try {parsed=parseProjectFile({...req.body,schema:'autoeditor.project',version:1,
      name:p.name,media:p.media ? {name:p.media.originalName,size:p.media.size,duration:p.media.duration} : (p.reference||null)});}
    catch(e){return res.status(400).json({error:e.message});}
    p.edit={...parsed.edit,aspect:parsed.aspect};
    save(projects);
    res.json({project:publicProject(p)});
  });
  app.post('/api/projects/:id/media', (req, res) => {
    const project = findProject(req.params.id);
    if (!project) return res.status(404).json({ error: 'Projeto não encontrado.' });
    upload.single('file')(req, res, (error) => {
      if (error) return res.status(400).json({ error: error.code === 'LIMIT_FILE_SIZE' ? 'Limite de 512 MB excedido.' : error.message });
      if (!req.file) return res.status(400).json({ error: 'Escolha um arquivo de vídeo.' });
      try {
        const duration = probe(req.file.path);
        const ext = path.extname(req.file.originalname).toLowerCase();
        const id = randomUUID();
        const folder = path.join(UPLOADS, project.id);
        fs.mkdirSync(folder, { recursive: true });
        const filename = id + ext;
        fs.renameSync(req.file.path, path.join(folder, filename));
        const previous = project.media;
        project.media = { id, originalName: path.basename(req.file.originalname).slice(0, 150), fileName: filename, size: req.file.size, duration };
        // Apply portable cuts only if the same source was reselected.
        if (project.reference && (project.reference.name !== project.media.originalName ||
            Math.abs(project.reference.duration - duration) > .4)) {
          if(project.edit)project.edit={...project.edit,clips:[],start:0,end:duration};
        }
        project.reference=null;
        project.exports = [];
        save(projects);
        if (previous) { try { fs.unlinkSync(path.join(folder, previous.fileName)); } catch {} }
        res.json({ project: publicProject(project) });
      } catch (e) {
        try { fs.unlinkSync(req.file.path); } catch {}
        res.status(400).json({ error: e.message || 'Vídeo inválido.' });
      }
    });
  });
  app.get('/api/projects/:id/media', (req, res) => {
    const project = findProject(req.params.id);
    if (!project?.media) return res.status(404).json({ error: 'Vídeo não encontrado.' });
    res.type(path.extname(project.media.fileName));
    res.sendFile(path.join(UPLOADS, project.id, project.media.fileName), { dotfiles: 'allow' });
  });
  app.post('/api/projects/:id/exports', (req, res) => {
    const project = findProject(req.params.id);
    if (!project) return res.status(404).json({ error: 'Projeto não encontrado.' });
    if (!project.media) return res.status(400).json({ error: 'Importe um vídeo antes de exportar.' });
    if (!toolAvailable(FFmpeg)) return res.status(503).json({ error: 'FFmpeg não disponível. Instale-o e reinicie o servidor.' });
    const aspect = req.body?.aspect;
    const plan = normalizeClips({
      segments: req.body?.segments, start: req.body?.start, end: req.body?.end,
      duration: project.media.duration, maxTotal: 600, maxEach: 600
    });
    if (plan.error || !['9:16', '16:9'].includes(aspect))
      return res.status(400).json({ error: plan.error || 'Formato de exportação inválido.' });
    if (project.exports.some(j => j.status === 'processing')) return res.status(409).json({ error: 'Já existe uma exportação em andamento neste projeto.' });
    const id = randomUUID(), folder = path.join(UPLOADS, project.id);
    const job = { id, status: 'processing', aspect, createdAt: new Date().toISOString(), filename: id + '.mp4' };
    project.exports.unshift(job);
    save(projects);
    res.status(202).json({ project: publicProject(project) });
    render(project, job, path.join(folder, project.media.fileName), path.join(folder, job.filename), plan.clips, aspect);
  });
  app.post('/api/projects/:id/narration', (req,res) => {
    const p=findProject(req.params.id);
    if(!p)return res.status(404).json({error:'Projeto não encontrado.'});
    if(!toolAvailable(FFmpeg) || (process.platform!=='win32' && !toolAvailable('espeak-ng')))
      return res.status(503).json({error:'Instale FFmpeg e eSpeak NG (Linux) ou uma voz pt-BR no Windows para narrar.'});
    const checked=validateScenes(req.body?.scenes);
    if(checked.error)return res.status(400).json({error:checked.error});
    const images=req.body?.images;
    if(!Array.isArray(images)||images.length!==checked.scenes.length||images.some(x=>typeof x!=='string'||x.length>1020000||!/^data:image\/png;base64,[A-Za-z0-9+/=]+$/.test(x)))
      return res.status(400).json({error:'Envie uma imagem PNG gerada para cada cena.'});
    const aspect=req.body?.aspect;
    if(!['9:16','16:9'].includes(aspect))return res.status(400).json({error:'Proporção inválida.'});
    if(p.exports.some(e=>e.status==='processing'))return res.status(409).json({error:'Outra exportação está em andamento.'});
    const id=randomUUID(),job={id,status:'processing',aspect,kind:'narration',createdAt:new Date().toISOString(),filename:id+'.mp4'};
    p.exports.unshift(job);save(projects);
    res.status(202).json({project:publicProject(p)});
    renderNarration(p,job,checked.scenes,images,aspect);
  });
  app.get('/api/projects/:id/exports/:jobId/download', (req, res) => {
    const project = findProject(req.params.id), job = project?.exports.find(e => e.id === req.params.jobId);
    if (!project || !job || job.status !== 'ready') return res.status(404).json({ error: 'Exportação não disponível.' });
    res.download(path.join(UPLOADS, project.id, job.filename), 'autoeditor-' + job.id.slice(0,8) + '.mp4', { dotfiles: 'allow' });
  });
  app.use('/api', (_req,res) => res.status(404).json({ error: 'Rota não encontrada.' }));
  const dist = path.join(HERE, '..', 'dist');
  if (fs.existsSync(dist)) {
    app.use(express.static(dist));
    app.use((req,res) => req.method === 'GET' ? res.sendFile(path.join(dist,'index.html')) : res.status(404).end());
  }
  app.use((err,req,res,next) => { console.error(err); if (!res.headersSent) res.status(500).json({ error: 'Erro inesperado do servidor.' }); });
  return app;
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const port = Number(process.env.PORT || 3011);
  createApp().listen(port, '127.0.0.1', () => console.log('AutoEditor API: http://127.0.0.1:' + port));
}
