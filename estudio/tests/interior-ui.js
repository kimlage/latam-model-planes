async(page)=>{
 const ctx=await page.context().browser().newContext({viewport:{width:1440,height:1050}}),p=await ctx.newPage();const r=[];
 try{
  await p.goto('http://127.0.0.1:8137/estudio/loading/?airport=sdsc&aircraft=B789&situation=manutencao');await p.bringToFront();
  await p.waitForFunction(()=>document.querySelector('latam-cinema').video?.currentTime>2);
  r.push({name:'Interior 787 uses the 720p film',ok:await p.locator('latam-cinema').evaluate(el=>el.video.videoWidth===1280&&el.video.src.includes('sdsc-b789-interior'))});
  await p.getByRole('button',{name:'Pausar',exact:true}).click();await p.screenshot({path:'output/playwright/interior-ui-desktop.png'});
  await p.setViewportSize({width:390,height:844});await p.screenshot({path:'output/playwright/interior-ui-mobile.png'});
  r.push({name:'Mobile scene and controls fit',ok:await p.evaluate(()=>document.documentElement.scrollWidth===innerWidth)});
  await p.getByLabel('Aeronave',{exact:true}).selectOption('A320neo');await p.waitForFunction(()=>document.querySelector('latam-cinema').iframe?.contentWindow.__cinema);
  r.push({name:'A320 opens its authored indoor 3D sequence',ok:await p.locator('latam-cinema').evaluate(el=>el.iframe.contentWindow.__cinema.doc.objetos.some(o=>o.slug==='A320neo'&&o.nivel==='heroi'))});
  await p.getByRole('link',{name:'Editar câmeras e exportar ↗',exact:true}).click();await p.waitForFunction(()=>window.__estudio?.estado.producao?.cinema?.situacao==='manutencao'&&document.body.dataset.carregando==='false');
  r.push({name:'Editor receives the interior and two camera shots',ok:await p.evaluate(()=>__estudio.estado.objetos.some(o=>o.slug==='sdsc_hangar9_interior')&&__estudio.estado.linha.planos.length===2)});
 }finally{await ctx.close()}
 await page.evaluate(r=>window.__interiorUI=r,r);
}
