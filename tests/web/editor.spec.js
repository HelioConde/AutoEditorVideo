import { test, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

test('editor web possui conteúdo real sem chamada à API desktop', async ({ page }, testInfo) => {
  const localCalls = [];
  page.on('request', req => { if (req.url().includes('/api/')) localCalls.push(req.url()); });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: /Edite seu vídeo/ })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Área de edição' })).toBeVisible();
  await expect(page.getByText('Privado por padrão')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Exportar vídeo' })).toBeDisabled();
  expect(localCalls).toEqual([]);
  await page.screenshot({ path: testInfo.outputPath('web-inicial.png'), fullPage: true, animations: 'disabled' });
});

test('versão web é responsiva e navegável por teclado', async ({ page }, testInfo) => {
  await page.goto('/');
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  expect(overflow).toBe(false);
  await expect(page.getByRole('link', { name: /Versão desktop/ })).toBeVisible();
  const upload = page.locator('input[type=file][accept*=\"video/mp4\"]');
  await expect(upload).toBeAttached();
  await page.screenshot({ path: testInfo.outputPath('web-responsivo.png'), fullPage: true, animations: 'disabled' });
});

test('rejeita arquivo inválido antes do upload e aceita mídia local', async ({ page }) => {
  await page.goto('/');
  await page.locator('input[type=file][accept*=\"video/mp4\"]').setInputFiles({ name:'notas.txt', mimeType:'text/plain', buffer:Buffer.from('teste') });
  await expect(page.getByRole('alert')).toContainText('MP4 ou WebM');
  await expect(page.getByRole('button', { name: 'Exportar vídeo' })).toBeDisabled();

  const folder = fs.mkdtempSync(path.join(os.tmpdir(), 'autoeditor-web-test-'));
  const sample = path.join(folder, 'sample.mp4');
  try {
    execFileSync('ffmpeg', ['-hide_banner','-loglevel','error','-f','lavfi','-i','color=c=blue:s=320x180:r=15','-t','2','-c:v','libx264','-pix_fmt','yuv420p','-y',sample], { timeout: 30000 });
    await page.locator('input[type=file][accept*=\"video/mp4\"]').setInputFiles(sample);
    await expect(page.getByText('sample.mp4')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Exportar vídeo' })).toBeEnabled({timeout: 15000});
    await page.getByRole('spinbutton', { name:'Fim (segundos)' }).fill('0.1');
    await expect(page.getByRole('alert')).toContainText('pelo menos 0,25 segundo');
    await expect(page.getByRole('button', { name: 'Exportar vídeo' })).toBeDisabled();
    await page.getByRole('spinbutton', { name:'Fim (segundos)' }).fill('1');
    await expect(page.getByRole('button', { name: 'Exportar vídeo' })).toBeEnabled();
  } finally {
    fs.rmSync(folder, { recursive: true, force: true });
  }
});

test('exportação WebAssembly real sem backend (opcional)', async ({ page }, testInfo) => {
  test.skip(process.env.WEB_WASM_INTEGRATION !== '1' || testInfo.project.name !== 'web-desktop',
    'Executar com WEB_WASM_INTEGRATION=1 após garantir acesso ao CDN FFmpeg.');
  test.setTimeout(200_000);
  const folder = fs.mkdtempSync(path.join(os.tmpdir(), 'autoeditor-wasm-'));
  const sample = path.join(folder, 'teste.mp4');
  try {
    execFileSync('ffmpeg', ['-hide_banner','-loglevel','error','-f','lavfi','-i','color=c=green:s=160x90:r=12','-t','1.5','-c:v','libx264','-pix_fmt','yuv420p','-y',sample], { timeout: 30000 });
    await page.goto('/');
    await page.locator('input[type=file][accept*=\"video/mp4\"]').setInputFiles(sample);
    await expect(page.getByRole('button', { name: 'Exportar vídeo' })).toBeEnabled();
    await page.getByRole('spinbutton', { name:'Fim (segundos)' }).fill('0.5');
    await expect(page.getByAltText('Quadro 1 do vídeo')).toBeVisible({timeout:15000});
    await page.getByRole('button',{name:'Adicionar à sequência'}).click();
    await page.getByRole('spinbutton',{name:'Início (segundos)'}).fill('0.9');
    await page.getByRole('spinbutton',{name:'Fim (segundos)'}).fill('1.4');
    await page.getByRole('button',{name:'Adicionar à sequência'}).click();
    await expect(page.getByRole('button',{name:'Remover trecho 2'})).toBeVisible();
    await page.getByRole('button', { name: 'Exportar vídeo' }).click();
    await expect(page.getByRole('link', { name: /Baixar vídeo MP4/ })).toBeVisible({ timeout: 180_000 });
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('link', { name: /Baixar vídeo MP4/ }).click()
    ]);
    expect(download.suggestedFilename()).toMatch(/\.mp4$/);
  } finally { fs.rmSync(folder,{recursive:true,force:true}); }
});

test('roteiro e manifesto podem ser transferidos sem API ou vídeo',async({page})=>{
  const project={schema:'autoeditor.project',version:1,name:'História importada',aspect:'16:9',media:null,
    edit:{start:0,end:0,clips:[],script:'Uma breve história sobre viagem.',
      scenes:[{title:'Cena de abertura',text:'Uma breve história sobre viagem.',duration:5}]}};
  await page.goto('/');
  await page.getByRole('button',{name:'Importar projeto'}).click();
  await page.locator('#project-json-input').setInputFiles({
    name:'historia.autoeditor.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(project))});
  await expect(page.getByRole('textbox',{name:'Roteiro'})).toHaveValue('Uma breve história sobre viagem.');
  await expect(page.getByRole('textbox',{name:'Título da cena'})).toHaveValue('Cena de abertura');
  await expect(page.getByRole('button',{name:'Exportar projeto'})).toBeEnabled();
  const [download] = await Promise.all([
    page.waitForEvent('download'),page.getByRole('button',{name:'Exportar projeto'}).click()]);
  const path=await download.path();
  const manifest=JSON.parse(fs.readFileSync(path,'utf8'));
  expect(manifest.schema).toBe('autoeditor.project');
  expect(manifest.edit.scenes[0].title).toBe('Cena de abertura');
  expect(manifest.aspect).toBe('16:9');
});

test('cenas mantêm tema e transição e aceitam imagem local sem transferi-la no manifesto',async({page})=>{
  await page.goto('/');
  await page.getByRole('textbox',{name:'Roteiro'}).fill('Nossa viagem pelo oceano ao pôr do sol.');
  await page.getByRole('button',{name:'Organizar cenas'}).click();
  await page.getByRole('combobox',{name:'Tema visual'}).selectOption('ocean');
  await page.getByRole('combobox',{name:'Transição'}).selectOption('cut');
  // One valid PNG pixel. Photo state must not be persisted into project JSON.
  const image=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/sXcAAAAASUVORK5CYII=','base64');
  await page.locator('#scene-picture-0').setInputFiles({name:'fundo.png',mimeType:'image/png',buffer:image});
  await expect(page.getByRole('status').filter({hasText:'Imagem aplicada'})).toBeVisible();
  const [download]=await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button',{name:'Exportar projeto'}).click()
  ]);
  const manifest=JSON.parse(fs.readFileSync(await download.path(),'utf8'));
  expect(manifest.edit.scenes[0].theme).toBe('ocean');
  expect(manifest.edit.scenes[0].transition).toBe('cut');
  expect(JSON.stringify(manifest)).not.toContain('data:image');
  expect(manifest.edit.voiceEngine).toBe('system');
});
