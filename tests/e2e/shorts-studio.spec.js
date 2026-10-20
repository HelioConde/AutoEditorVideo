import { test, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

test('MVP: sugere destaque e gera Short vertical independente com legenda',async({page},info)=>{
  test.skip(info.project.name!=='desktop-chromium','Executar renderização pesada apenas no desktop CI.');
  test.setTimeout(160000);
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'shorts-auto-'));
  try{
    const video=path.join(dir,'episodio.mp4');
    execFileSync('ffmpeg',['-hide_banner','-loglevel','error','-f','lavfi','-i',
      'color=c=teal:s=320x180:r=12','-f','lavfi','-i','sine=frequency=360:sample_rate=16000',
      '-t','12','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest','-y',video],
      {timeout:40000});
    await page.goto('/');
    await page.locator('.topbar').getByRole('button',{name:/Novo projeto/}).click();
    await page.getByRole('textbox',{name:'Nome do projeto'}).fill('Shorts automáticos de teste');
    await page.getByRole('dialog').getByRole('button',{name:'Criar projeto',exact:true}).click();
    await page.locator('#media-file').setInputFiles(video);
    await expect(page.locator('.video-stage video')).toBeVisible({timeout:20000});
    await expect(page.locator('.panel-subtitle').filter({hasText:'episodio.mp4'})).toBeVisible({timeout:20000});
    const cues='1\n00:00:00,100 --> 00:00:05,700\nMas sabe como consegui vencer a partida no final?\n\n'+
      '2\n00:00:05,800 --> 00:00:11,500\nEu descobri uma estratégia incrível e finalmente ganhei o jogo!\n';
    await page.locator('.sub-studio input[type=file]').setInputFiles({
      name:'episodio.srt',mimeType:'text/plain',buffer:Buffer.from(cues,'utf8')
    });
    await expect(page.getByRole('textbox',{name:'Texto da legenda'}).first()).toHaveValue(/Mas sabe como/);
    await page.getByRole('combobox',{name:'Tipo de conteúdo'}).selectOption('gameplay');
    await page.getByRole('button',{name:'Encontrar melhores momentos'}).click();
    await expect(page.locator('.shorts-analysis-summary')).toContainText('amostras de áudio',{timeout:45000});
    await expect(page.locator('.shorts-candidate')).toHaveCount(1);
    await expect(page.locator('.shorts-evidence')).toContainText('picos de áudio');
    await page.screenshot({path:info.outputPath('shorts-auto-candidates.png'),animations:'disabled',fullPage:false});
    await page.getByRole('button',{name:'Gerar 1 Short legendado'}).click();
    await expect(page.getByText('Short automático')).toBeVisible({timeout:15000});
    await expect(page.getByText('Exportação concluída').last()).toBeVisible({timeout:140000});
    const result=page.getByRole('link',{name:'Baixar vídeo exportado'}).last();
    const response=await page.request.get(await result.getAttribute('href'));
    expect(response.status()).toBe(200);
    const file=path.join(dir,'short.mp4');
    fs.writeFileSync(file,await response.body());
    const codecs=execFileSync('ffprobe',['-v','error','-show_entries','stream=codec_type',
      '-of','csv=p=0',file],{encoding:'utf8'});
    expect(codecs).toContain('video');
    expect(fs.statSync(file).size).toBeGreaterThan(5000);
  }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
