import express from 'express';
import multer from 'multer';
import { spawn, spawnSync } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

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
  exports: (p.exports || []).map(({ id, status, aspect, createdAt, error }) => ({ id, status, aspect, createdAt, error }))
});
function render(project, job, source, output, start, length, aspect) {
  const vertical = aspect === '9:16';
  const w = vertical ? 720 : 1280, h = vertical ? 1280 : 720;
  const filter = 'scale=' + w + ':' + h + ':force_original_aspect_ratio=increase,crop=' + w + ':' + h + ',fps=30';
  const args = ['-hide_banner', '-loglevel', 'error', '-y', '-i', source, '-ss', String(start), '-t', String(length),
    '-vf', filter, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-pix_fmt', 'yuv420p',
    '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', output];
  let process;
  try { process = spawn(FFmpeg, args, { windowsHide: true }); }
  catch { job.status = 'error'; job.error = 'Não foi possível iniciar o FFmpeg.'; save(projects); return; }
  let stderr = '';
  process.stderr.on('data', chunk => { stderr = (stderr + chunk.toString()).slice(-1200); });
  process.on('error', () => { job.status = 'error'; job.error = 'Não foi possível iniciar o FFmpeg.'; save(projects); });
  process.on('close', code => {
    if (job.status === 'error') return;
    if (code === 0 && fs.existsSync(output) && fs.statSync(output).size > 0) job.status = 'ready';
    else { job.status = 'error'; job.error = 'A exportação falhou. Verifique o arquivo original e tente novamente.'; try { fs.unlinkSync(output); } catch {} }
    save(projects);
    if (code !== 0) console.error('FFmpeg export failed:', stderr);
  });
}

export function createApp() {
  const app = express();
  app.disable('x-powered-by');
  app.use(express.json({ limit: '50kb' }));
  // Do not accept cross-origin writes to the unauthenticated local-only API.
  app.use('/api', (req, res, next) => {
    if (!['POST', 'PUT', 'PATCH', 'DELETE'].includes(req.method)) return next();
    const origin = req.get('origin');
    if (origin && !new Set(['http://127.0.0.1:5173', 'http://localhost:5173', 'http://127.0.0.1:3011', 'http://localhost:3011']).has(origin))
      return res.status(403).json({ error: 'Origem não autorizada para operação local.' });
    next();
  });
  app.get('/api/health', (_req, res) => res.json({ ffmpeg: toolAvailable(FFmpeg), ffprobe: toolAvailable(FFprobe), version: '2.0-beta' }));
  app.get('/api/projects', (_req, res) => res.json({ projects: projects.map(publicProject).sort((a,b) => b.createdAt.localeCompare(a.createdAt)) }));
  app.post('/api/projects', (req, res) => {
    const name = typeof req.body?.name === 'string' ? req.body.name.trim() : '';
    if (name.length < 2 || name.length > 64) return res.status(400).json({ error: 'Use um nome entre 2 e 64 caracteres.' });
    const project = { id: randomUUID(), name, createdAt: new Date().toISOString(), media: null, exports: [] };
    projects.unshift(project);
    save(projects);
    res.status(201).json({ project: publicProject(project) });
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
    res.sendFile(path.join(UPLOADS, project.id, project.media.fileName));
  });
  app.post('/api/projects/:id/exports', (req, res) => {
    const project = findProject(req.params.id);
    if (!project) return res.status(404).json({ error: 'Projeto não encontrado.' });
    if (!project.media) return res.status(400).json({ error: 'Importe um vídeo antes de exportar.' });
    if (!toolAvailable(FFmpeg)) return res.status(503).json({ error: 'FFmpeg não disponível. Instale-o e reinicie o servidor.' });
    const start = Number(req.body?.start), end = Number(req.body?.end), aspect = req.body?.aspect;
    if (!Number.isFinite(start) || !Number.isFinite(end) || start < 0 || end <= start + 0.24 || end > project.media.duration + 0.1 || end - start > 600 || !['9:16', '16:9'].includes(aspect))
      return res.status(400).json({ error: 'Selecione um trecho válido de até 10 minutos e um formato de exportação.' });
    if (project.exports.some(j => j.status === 'processing')) return res.status(409).json({ error: 'Já existe uma exportação em andamento neste projeto.' });
    const id = randomUUID(), folder = path.join(UPLOADS, project.id);
    const job = { id, status: 'processing', aspect, createdAt: new Date().toISOString(), filename: id + '.mp4' };
    project.exports.unshift(job);
    save(projects);
    res.status(202).json({ project: publicProject(project) });
    render(project, job, path.join(folder, project.media.fileName), path.join(folder, job.filename), start, end - start, aspect);
  });
  app.get('/api/projects/:id/exports/:jobId/download', (req, res) => {
    const project = findProject(req.params.id), job = project?.exports.find(e => e.id === req.params.jobId);
    if (!project || !job || job.status !== 'ready') return res.status(404).json({ error: 'Exportação não disponível.' });
    res.download(path.join(UPLOADS, project.id, job.filename), 'autoeditor-' + job.id.slice(0,8) + '.mp4');
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
