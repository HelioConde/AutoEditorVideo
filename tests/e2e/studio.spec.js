import { test, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

test('painel tem navegação clara, estado vazio e captura visual', async ({ page }, testInfo) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: /Bom criar começa aqui/ })).toBeVisible();
  await expect(page.locator('nav.side-nav')).toBeAttached();
  await expect(page.locator('.topbar').getByRole('button', { name: /Novo projeto/ })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath('painel.png'), fullPage: true, animations: 'disabled' });
});

test('criar projeto, navegar ao editor e voltar ao painel', async ({ page }) => {
  await page.goto('/');
  await page.locator('.topbar').getByRole('button', { name: /Novo projeto/ }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.getByRole('textbox', { name: 'Nome do projeto' }).fill('Minha primeira edição');
  await page.getByRole('dialog').getByRole('button', { name: 'Criar projeto', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Minha primeira edição' })).toBeVisible();
  await expect(page.getByText('Escolher vídeo')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Exportar vídeo' })).toBeDisabled();
  await page.getByRole('button', { name: /Voltar ao painel/ }).click();
  await expect(page.getByRole('button', { name: /Minha primeira edição/ }).first()).toBeVisible();
});

test('modal aceita teclado, valida nome e fecha com Escape', async ({ page }) => {
  await page.goto('/');
  await page.locator('.topbar').getByRole('button', { name: /Novo projeto/ }).click();
  const input = page.getByRole('textbox', { name: 'Nome do projeto' });
  await expect(input).toBeFocused();
  await expect(page.getByRole('dialog').getByRole('button', { name: 'Criar projeto', exact: true })).toBeDisabled();
  await input.fill('A');
  await expect(page.getByRole('dialog').getByRole('button', { name: 'Criar projeto', exact: true })).toBeDisabled();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
});

test('layout móvel não tem rolagem horizontal e abre o menu', async ({ page }, testInfo) => {
  await page.goto('/');
  if (testInfo.project.name.includes('mobile')) {
    await expect(page.getByRole('button', { name: 'Abrir menu' })).toBeVisible();
    await page.getByRole('button', { name: 'Abrir menu' }).click();
    await expect(page.getByRole('navigation', { name: 'Seções' })).toBeVisible();
    await page.getByRole('button', { name: 'Fechar menu' }).click();
  }
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  expect(overflow).toBe(false);
  await page.screenshot({ path: testInfo.outputPath('responsividade.png'), fullPage: true, animations: 'disabled' });
});

test('pipeline real: importa vídeo de teste, define recorte e exporta', async ({ page }) => {
  const ff = await page.request.get('/api/health');
  const tools = await ff.json();
  test.skip(!tools.ffmpeg || !tools.ffprobe, 'FFmpeg e FFprobe são necessários para o teste de renderização');
  const folder = fs.mkdtempSync(path.join(os.tmpdir(), 'autoeditor-e2e-'));
  const sample = path.join(folder, 'amostra.mp4');
  try {
    execFileSync('ffmpeg', ['-hide_banner','-loglevel','error','-f','lavfi','-i','color=c=blue:s=320x180:r=15','-t','1.5','-c:v','libx264','-pix_fmt','yuv420p','-y',sample], { timeout: 20000 });
    await page.goto('/');
    await page.locator('.topbar').getByRole('button', { name: /Novo projeto/ }).click();
    await page.getByRole('textbox', { name: 'Nome do projeto' }).fill('Teste de renderização');
    await page.getByRole('dialog').getByRole('button', { name: 'Criar projeto', exact: true }).click();
    await page.locator('#media-file').setInputFiles(sample);
    await expect(page.getByText('Vídeo importado e pronto para editar.')).toBeVisible({ timeout: 30000 });
    await page.getByRole('spinbutton', { name: 'Início em segundos' }).fill('0.1');
    await page.getByRole('spinbutton', { name: 'Fim em segundos' }).fill('1.0');
    await page.getByRole('button', { name: 'Exportar vídeo' }).click();
    await expect(page.getByText('Exportação concluída')).toBeVisible({ timeout: 90_000 });
    const downloadPath = await page.getByRole('link', { name: 'Baixar vídeo exportado' }).getAttribute('href');
    const mediaResponse = await page.request.get(downloadPath);
    expect(mediaResponse.status(), await mediaResponse.text().catch(() => 'download falhou')).toBe(200);
    expect(mediaResponse.headers()['content-type']).toContain('video/mp4');
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('link', { name: 'Baixar vídeo exportado' }).click()
    ]);
    expect(download.suggestedFilename()).toMatch(/\.mp4$/);
  } finally { fs.rmSync(folder, { recursive: true, force: true }); }
});


test('timeline com dois cortes gera MP4 concatenado de duração correta', async ({ page }) => {
  const ff = await (await page.request.get('/api/health')).json();
  test.skip(!ff.ffmpeg || !ff.ffprobe, 'FFmpeg/FFprobe não disponíveis');
  const folder = fs.mkdtempSync(path.join(os.tmpdir(), 'autoeditor-cuts-e2e-'));
  const sample = path.join(folder, 'cortes.mp4');
  const output = path.join(folder, 'joined.mp4');
  try {
    execFileSync('ffmpeg', ['-hide_banner','-loglevel','error','-f','lavfi','-i','testsrc=size=320x180:rate=15',
      '-t','3','-c:v','libx264','-pix_fmt','yuv420p','-y',sample], { timeout:30000 });
    await page.goto('/');
    await page.locator('.topbar').getByRole('button',{name:/Novo projeto/}).click();
    await page.getByRole('textbox',{name:'Nome do projeto'}).fill('Multicortes QA');
    await page.getByRole('dialog').getByRole('button',{name:'Criar projeto',exact:true}).click();
    await page.locator('#media-file').setInputFiles(sample);
    await expect(page.getByRole('button',{name:'Exportar vídeo'})).toBeEnabled();
    await expect(page.getByAltText('Quadro 1 do vídeo')).toBeVisible({timeout:15000});
    await page.getByRole('spinbutton',{name:'Início em segundos'}).fill('0.2');
    await page.getByRole('spinbutton',{name:'Fim em segundos'}).fill('0.9');
    await page.getByRole('button',{name:'Adicionar à sequência'}).click();
    await page.getByRole('spinbutton',{name:'Início em segundos'}).fill('1.8');
    await page.getByRole('spinbutton',{name:'Fim em segundos'}).fill('2.6');
    await page.getByRole('button',{name:'Adicionar à sequência'}).click();
    await expect(page.getByRole('button',{name:'Remover trecho 2'})).toBeVisible();
    await page.getByRole('button',{name:'Exportar vídeo'}).click();
    await expect(page.getByText('Exportação concluída')).toBeVisible({timeout:90000});
    const url=await page.getByRole('link',{name:'Baixar vídeo exportado'}).getAttribute('href');
    const response=await page.request.get(url);
    expect(response.status()).toBe(200);
    fs.writeFileSync(output,await response.body());
    const probe=execFileSync('ffprobe',['-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',output],{encoding:'utf8'});
    const seconds=Number(probe.trim());
    expect(seconds).toBeGreaterThan(1.2);
    expect(seconds).toBeLessThan(2.1);
  } finally { fs.rmSync(folder,{recursive:true,force:true}); }
});
