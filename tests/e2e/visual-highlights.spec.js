import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

test('silent gameplay: detects motion, reviews selection and exports an uncaptioned vertical Short',async({page},info)=>{
  test.skip(info.project.name!=='desktop-chromium','Render only once in desktop CI');
  test.setTimeout(165000);
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'shorts-motion-ui-'));
  try{
    const source=path.join(dir,'moving-silent.mp4');
    execFileSync('ffmpeg',['-hide_banner','-loglevel','error','-f','lavfi','-i',
      'testsrc2=size=320x180:rate=8:duration=13','-an','-c:v','libx264',
      '-pix_fmt','yuv420p','-y',source],{timeout:35000});
    await page.goto('/');
    await page.locator('.topbar').getByRole('button',{name:/Novo projeto/}).click();
    await page.getByRole('textbox',{name:'Nome do projeto'}).fill('Destaque silencioso');
    await page.getByRole('dialog').getByRole('button',{name:'Criar projeto',exact:true}).click();
    await page.locator('#media-file').setInputFiles(source);
    await expect(page.locator('.panel-subtitle').filter({hasText:'moving-silent.mp4'})).toBeVisible({timeout:20000});
    await expect(page.getByText('Vídeo sem transcrição: análise visual disponível.')).toBeVisible();
    await page.getByRole('combobox',{name:'Tipo de conteúdo'}).selectOption('gameplay');
    await page.getByRole('button',{name:'Analisar movimento no vídeo'}).click();
    await expect(page.locator('.shorts-analysis-summary')).toContainText(/\d+ quadros avaliados/,{timeout:45000});
    await expect(page.locator('.shorts-candidate')).toHaveCount(1);
    await expect(page.locator('.shorts-evidence')).toContainText('movimento');
    await expect(page.getByRole('button',{name:'Gerar 1 Short sem legendas'})).toBeEnabled();
    await page.getByRole('button',{name:'Gerar 1 Short sem legendas'}).click();
    await expect(page.getByText('Short automático')).toBeVisible({timeout:20000});
    await expect(page.getByText('Exportação concluída').last()).toBeVisible({timeout:145000});
    const link=page.getByRole('link',{name:'Baixar vídeo exportado'}).last();
    const response=await page.request.get(await link.getAttribute('href'));
    expect(response.status()).toBe(200);
    const output=path.join(dir,'short.mp4');
    fs.writeFileSync(output,await response.body());
    const streams=JSON.parse(execFileSync('ffprobe',['-v','error','-show_streams','-of','json',output],{encoding:'utf8'}));
    const video=streams.streams.find(x=>x.codec_type==='video');
    assertPortrait(video);
    expect(streams.streams.some(x=>x.codec_type==='subtitle')).toBe(false);
  }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
function assertPortrait(stream) {
  expect(stream).toBeDefined();
  expect(stream.width).toBe(720);
  expect(stream.height).toBe(1280);
}
