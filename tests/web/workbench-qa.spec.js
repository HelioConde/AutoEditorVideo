import { test, expect } from '@playwright/test';

// @visual and @a11y use real Chromium layouts: screens are attached to CI.
test('QA visual @visual @a11y: entrada enxuta, etapas e ferramentas opcionais em cinco resoluções',async({page},testInfo)=>{
  await page.goto('/');
  const stages=page.getByRole('group',{name:'Etapas da edição'});
  await expect(stages).toBeVisible();
  await expect(stages.getByRole('button')).toHaveCount(3);
  await expect(stages.getByRole('button',{name:'Importar vídeo'})).toHaveAttribute('aria-current','step');
  await expect(stages.getByRole('button',{name:'Editar cortes'})).toBeDisabled();
  await expect(stages.getByRole('button',{name:'Exportar'})).toBeDisabled();
  await expect(page.locator('#studio-cuts')).toHaveCount(0);
  await expect(page.locator('#studio-captions')).toHaveCount(0);
  await expect(page.locator('#studio-script')).toHaveCount(0);
  await expect(page.locator('#studio-project')).toHaveCount(0);
  for(const width of [320,375,768,1280,1920]){
    await page.setViewportSize({width,height:850});
    await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth),
      {message:'Nenhum overflow horizontal na largura '+width}).toBeLessThanOrEqual(1);
    await expect(stages).toBeVisible();
    if(width===375||width===1280)
      await page.screenshot({path:testInfo.outputPath('web-progressive-initial-'+width+'.png'),
        animations:'disabled',fullPage:false});
  }
  await page.setViewportSize({width:375,height:850});
  const legends=page.getByRole('button',{name:/^Legendas/});
  await legends.focus();
  expect(await legends.evaluate(el=>getComputedStyle(el).outlineStyle)).not.toBe('none');
  await legends.click();
  await expect(legends).toHaveAttribute('aria-expanded','true');
  await expect(page.locator('#studio-captions')).toBeVisible();
  await page.getByRole('button',{name:/^Roteiro/}).click();
  await expect(page.locator('#studio-captions')).toHaveCount(0);
  await expect(page.locator('#studio-script')).toBeVisible();
  const script=page.getByRole('textbox',{name:'Roteiro'});
  expect(Number.parseFloat(await script.evaluate(el=>getComputedStyle(el).fontSize))).toBeGreaterThanOrEqual(16);
  await script.fill('Roteiro de demonstração das etapas para o celular.');
  await expect(script).toHaveValue('Roteiro de demonstração das etapas para o celular.');
});
test('QA movimento reduzido @visual: prefere evitar animações',async({page})=>{
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.goto('/');
  expect(await page.evaluate(()=>getComputedStyle(document.documentElement).scrollBehavior)).toBe('auto');
  await page.getByRole('button',{name:'Criar pelo roteiro'}).click();
  await expect(page.getByRole('textbox',{name:'Roteiro'})).toBeVisible();
  await page.getByRole('button',{name:/^Roteiro/}).click();
  await expect(page.locator('#studio-script')).toHaveCount(0);
});
