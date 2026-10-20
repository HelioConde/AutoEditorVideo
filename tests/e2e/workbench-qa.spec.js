import { test, expect } from '@playwright/test';
test('QA desktop @visual @a11y: navegação do workspace e foco em ações',async({page},testInfo)=>{
  await page.goto('/');
  await page.locator('.topbar').getByRole('button',{name:/Novo projeto/}).click();
  await page.getByRole('textbox',{name:'Nome do projeto'}).fill('QA Interface e Acessibilidade');
  await page.getByRole('dialog').getByRole('button',{name:'Criar projeto',exact:true}).click();
  const nav=page.getByRole('navigation',{name:'Ir para uma etapa do editor'});
  await expect(nav.locator('a')).toHaveCount(5);
  for(const width of [320,375,768,1280,1920]){
    await page.setViewportSize({width,height:850});
    await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth),
      {message:'Sem scroll horizontal em '+width}).toBeLessThanOrEqual(1);
    if(width===375||width===1280){
      await page.screenshot({path:testInfo.outputPath('desktop-workbench-'+width+'.png'),
        animations:'disabled',fullPage:false});
    }
  }
  const link=nav.getByRole('link',{name:/Legendas/});
  await link.focus();
  expect(await link.evaluate(e=>getComputedStyle(e).outlineStyle)).not.toBe('none');
  await link.click();
  await expect(page).toHaveURL(/#studio-captions$/);
  await expect(page.locator('#studio-captions')).toBeInViewport();
  await nav.getByRole('link',{name:/Projeto/}).click();
  await expect(page.locator('#studio-project')).toBeInViewport();
  await expect(page.getByRole('button',{name:'Exportar projeto'})).toBeEnabled();
});
