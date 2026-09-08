async(page)=>{
 const ctx=await page.context().browser().newContext({viewport:{width:1440,height:1050}}),p=await ctx.newPage(),results=[];
 try{
  await p.goto('http://127.0.0.1:8137/estudio/loading/?airport=scl&aircraft=B789&situation=cockpit');
  await p.waitForFunction(()=>document.querySelector('#situation')?.value==='aproximacao');
  results.push({name:'Legacy cockpit URL opens external approximation',ok:await p.evaluate(()=>location.search.includes('situation=aproximacao')&&!Array.from(document.querySelector('#situation').options).some(o=>o.value==='cockpit'))});
  await p.waitForFunction(()=>{const v=document.querySelector('latam-cinema').shadowRoot.querySelector('video');return v?.readyState>=2&&v.currentTime>2&&v.classList.contains('playing')});
  await p.screenshot({path:'output/playwright/fleet-ui-desktop.png'});
  await p.setViewportSize({width:390,height:844});
  await p.evaluate(()=>new Promise(r=>document.querySelector('latam-cinema').shadowRoot.querySelector('video').requestVideoFrameCallback(()=>requestAnimationFrame(r))));
  await p.screenshot({path:'output/playwright/fleet-ui-mobile.png'});
  for(const airport of ['sbgr','sdsc','scl']){
   await p.locator('#airport').selectOption(airport);await p.locator('#situation').selectOption('sobrevoo');
   results.push({name:airport+' all fleet and external situations',ok:await p.evaluate(()=>document.querySelector('#aircraft').options.length===11&&!Array.from(document.querySelector('#situation').options).some(o=>o.value==='cockpit'))});
  }
  await p.locator('#aircraft').selectOption('B763F');await p.locator('#situation').selectOption('aproximacao');
  await p.locator('#edit').click();await p.waitForFunction(()=>window.__estudio?.estado?.producao?.cinema?.aeronave==='B763F');
  results.push({name:'Editor opens exact external sequence',ok:await p.evaluate(()=>__estudio.estado.producao.cinema.situacao==='aproximacao'&&!__estudio.estado.producao.cockpit&&__estudio.estado.objetos.some(o=>o.slug==='scl_relevo'))});
  await page.evaluate(r=>window.__fleetUI=r,{results,headless:await p.evaluate(()=>navigator.userAgent.includes('HeadlessChrome'))});
 }finally{await ctx.close()}
}
