import { test, expect } from '@playwright/test';

// @visual and @a11y intentionally run in the existing browser CI: screenshots
// are artifacts, not fragile pixel-exact snapshots.
test('QA visual @visual @a11y: navegação do estúdio, cinco resoluções e foco visível',async({page},testInfo)=>{
  await page.goto('/');
  const nav=page.getByRole('navigation',{name:'Ir para uma etapa do editor'});
  await expect(nav).toBeVisible();
  await expect(nav.locator('a')).toHaveCount(5);
  for(const width of [320,375,768,1280,1920]){
    await page.setViewportSize({width,height:850});
    await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth),
      {message:'A página não deve ter scroll horizontal em '+width}).toBeLessThanOrEqual(1);
    await expect(nav).toBeVisible();
    if(width===375||width===1280){
      await page.screenshot({path:testInfo.outputPath('web-workbench-'+width+'.png'),
        animations:'disabled',fullPage:false});
    }
  }
  await page.setViewportSize({width:375,height:850});
  const link=nav.getByRole('link',{name:/Legendas/});
  await link.focus();
  expect(await link.evaluate(e=>getComputedStyle(e).outlineStyle)).not.toBe('none');
  await link.click();
  await expect(page).toHaveURL(/#studio-captions$/);
  await expect(page.locator('#studio-captions')).toBeInViewport();
  await nav.getByRole('link',{name:/Roteiro/}).click();
  await expect(page).toHaveURL(/#studio-script$/);
  await expect(page.locator('#studio-script')).toBeInViewport();
  const script=page.getByRole('textbox',{name:'Roteiro'});
  expect(Number.parseFloat(await script.evaluate(e=>getComputedStyle(e).fontSize))).toBeGreaterThanOrEqual(16);
  await script.fill('Vídeo com roteiro para revisar o layout no celular.');
  await expect(script).toHaveValue('Vídeo com roteiro para revisar o layout no celular.');
});
test('QA movimento reduzido @visual: respeita preferências do sistema',async({page})=>{
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.goto('/');
  const smooth=await page.evaluate(()=>getComputedStyle(document.documentElement).scrollBehavior);
  expect(smooth).toBe('auto');
  const nav=page.getByRole('navigation',{name:'Ir para uma etapa do editor'});
  await nav.getByRole('link',{name:/Cortes/}).click();
  await expect(page).toHaveURL(/#studio-cuts$/);
});
