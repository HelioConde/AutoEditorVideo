import { test, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

test('rascunho local restaura roteiro e legenda sem armazenar mídia', async ({page}) => {
  await page.goto('/');
  await page.getByRole('textbox',{name:'Roteiro'}).fill('Uma introdução para o AutoEditor Studio.');
  await page.getByRole('button',{name:'Organizar cenas'}).click();
  await page.getByRole('button',{name:'Nova legenda'}).click();
  await page.getByRole('textbox',{name:'Texto da legenda'}).fill('Olá, edição local.');
  // Wait for the *latest* debounced edit, not a status from an earlier autosave.
  await expect.poll(()=>page.evaluate(()=>{
    const raw=localStorage.getItem('autoeditor:web-draft:v1');
    if(!raw)return '';
    return JSON.parse(raw).project?.edit?.subtitles?.[0]?.text||'';
  }),{timeout:10000}).toBe('Olá, edição local.');
  const manifest=await page.evaluate(()=>JSON.parse(localStorage.getItem('autoeditor:web-draft:v1')));
  expect(manifest.project.edit.script).toContain('introdução');
  expect(JSON.stringify(manifest)).not.toContain('data:image');
  await page.reload();
  await expect(page.getByRole('textbox',{name:'Roteiro'})).toHaveValue('Uma introdução para o AutoEditor Studio.');
  await expect(page.getByRole('textbox',{name:'Texto da legenda'})).toHaveValue('Olá, edição local.');
  await page.getByRole('button',{name:'Limpar rascunho'}).click();
  await expect(page.getByRole('textbox',{name:'Roteiro'})).toHaveValue('');
  await page.reload();
  await expect(page.getByRole('textbox',{name:'Roteiro'})).toHaveValue('');
  await expect(page.getByRole('textbox',{name:'Texto da legenda'})).toHaveCount(0);
});
test('timeline edita trecho salvo com zoom e incremento de centésimos', async ({page}) => {
  const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'timeline-web-'));
  const video=path.join(tmp,'timeline.mp4');
  try{
    execFileSync('ffmpeg',['-hide_banner','-loglevel','error','-f','lavfi','-i','color=c=olive:s=160x90:r=12',
      '-t','2','-c:v','libx264','-pix_fmt','yuv420p','-y',video],{timeout:30000});
    await page.goto('/');
    await page.locator('input[type=file][accept*="video/mp4"]').setInputFiles(video);
    await expect(page.getByRole('button',{name:'Exportar vídeo'})).toBeEnabled();
    await page.getByRole('spinbutton',{name:'Fim (segundos)'}).fill('0.8');
    await page.getByRole('button',{name:'Adicionar à sequência'}).click();
    await page.getByRole('button',{name:'Editar trecho 1'}).click();
    await expect(page.getByRole('status').filter({hasText:'Editando trecho 1'})).toBeVisible();
    await page.getByRole('combobox',{name:'Zoom dos controles de corte'}).selectOption('4');
    await page.getByRole('button',{name:'Aumentar início em 0,01 segundo'}).click();
    await page.getByRole('button',{name:'Salvar ajuste do trecho 1'}).click();
    await expect(page.locator('.filmstrip-queue-list li').first()).toContainText('00:00.01');
    await expect(page.getByRole('button',{name:'Exportar vídeo'})).toBeEnabled();
  }finally{fs.rmSync(tmp,{recursive:true,force:true});}
});
