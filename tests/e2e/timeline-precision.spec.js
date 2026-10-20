import { test, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

test('edição fina de trecho no desktop persiste ao reabrir o projeto',async({page})=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'timeline-desktop-'));
  const video=path.join(dir,'timeline.mp4');
  try{
    execFileSync('ffmpeg',['-hide_banner','-loglevel','error','-f','lavfi','-i','color=c=purple:s=160x90:r=12',
      '-t','2','-c:v','libx264','-pix_fmt','yuv420p','-y',video],{timeout:30000});
    await page.goto('/');
    await page.locator('.topbar').getByRole('button',{name:/Novo projeto/}).click();
    await page.getByRole('textbox',{name:'Nome do projeto'}).fill('Timeline QA');
    await page.getByRole('dialog').getByRole('button',{name:'Criar projeto',exact:true}).click();
    await page.locator('#media-file').setInputFiles(video);
    await expect(page.getByRole('spinbutton',{name:'Fim em segundos'})).not.toHaveValue('0');
    await page.getByRole('spinbutton',{name:'Fim em segundos'}).fill('0.8');
    await page.getByRole('button',{name:'Adicionar à sequência'}).click();
    await page.getByRole('button',{name:'Editar trecho 1'}).click();
    await page.getByRole('button',{name:'Aumentar início em 0,01 segundo'}).click();
    await page.getByRole('button',{name:'Salvar ajuste do trecho 1'}).click();
    await expect(page.locator('.filmstrip-queue-list li').first()).toContainText('00:00.01');
    await expect.poll(async()=>{
      const rows=await(await page.request.get('/api/projects')).json();
      const selected=rows.projects.find(p=>p.name==='Timeline QA');
      return selected?.edit?.clips?.[0]?.start;
    },{timeout:10000}).toBe(.01);
  }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
