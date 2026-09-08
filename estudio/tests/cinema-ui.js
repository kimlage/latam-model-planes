async(page)=>{
 const context=await page.context().browser().newContext({viewport:{width:1440,height:1050}}),p=await context.newPage(),results=[];const check=(name,ok)=>results.push({name,ok:!!ok});
 try{
  await p.goto('http://127.0.0.1:8137/estudio/loading/');
  await p.waitForFunction(()=>document.querySelector('latam-cinema').video?.readyState>=2);
  check('Reboque only offers the calibrated 787',await p.locator('#aircraft option').count()===1&&await p.locator('#aircraft').inputValue()==='B789');
  await p.locator('latam-cinema video').evaluate(async v=>{v.pause();const seek=new Promise(r=>v.addEventListener('seeked',r,{once:true}));const frame=new Promise(r=>v.requestVideoFrameCallback(r));v.currentTime=8;await Promise.all([seek,frame]);});await p.waitForFunction(()=>+document.querySelector('latam-cinema').q('.veil').style.opacity===0);
  await p.screenshot({path:'output/playwright/cinema-final-desktop.png'});
  await p.setViewportSize({width:390,height:844});await p.screenshot({path:'output/playwright/cinema-final-mobile.png'});
  check('Mobile controls and full shot fit without horizontal overflow',await p.evaluate(()=>document.documentElement.scrollWidth===innerWidth));
  await p.getByRole('button',{name:'Ver como loading',exact:true}).click();check('Loading mode preserves complete 16:9 shot',await p.locator('latam-cinema').evaluate(el=>Math.abs(el.getBoundingClientRect().width/el.getBoundingClientRect().height-16/9)<.01));await p.keyboard.press('Escape');
  await p.getByLabel('Aeroporto',{exact:true}).selectOption('sbgr');await p.getByLabel('Situação',{exact:true}).selectOption('patio');
  await p.waitForFunction(()=>document.querySelector('latam-cinema').iframe?.contentWindow.__cinema);
  check('Airport and aircraft select an actual different document',await p.locator('latam-cinema').evaluate(el=>el.iframe.contentWindow.__cinema.doc.producao.cinema.aeroporto==='sbgr'&&el.iframe.contentWindow.__cinema.doc.objetos.some(o=>o.slug==='B789')));
  await p.getByRole('button',{name:'Pausar',exact:true}).click();await p.waitForFunction(()=>document.querySelector('latam-cinema').iframe.contentWindow.__cinema.paused);
  check('Pause reaches the 3D runtime',true);
  await p.evaluate(()=>window.postMessage({type:'cinema-error',message:'wrong source'},location.origin));
  check('Unrelated messages cannot replace the active scene',await p.locator('latam-cinema').evaluate(el=>el.q('.notice').hidden));
  await p.getByRole('link',{name:'Editar câmeras e exportar ↗',exact:true}).click();
  await p.waitForFunction(()=>window.__estudio?.estado.producao?.cinema?.aeronave==='B789',{timeout:45000});
  check('Editor opens the exact airport, aircraft and situation',await p.evaluate(()=>window.__estudio.estado.producao.cinema.aeroporto==='sbgr'&&window.__estudio.estado.producao.cinema.situacao==='patio'));
  const legacy=await p.evaluate(async()=>await(await import('./tests/regression.js')).run());
  check('Existing editor/export regression suite passes',legacy.every(r=>r.ok));
  const fade=await p.evaluate(async()=>{
   const {opacidadeTransicao:f}=await import('./js/transicao.js');const d=window.__estudio.estado;
   return f(d,0)===1&&f(d,d.linha.duracao/2)===0&&f(d,d.linha.duracao)===1&&f({...d,producao:{}},0)===0;
  });check('Editorial fade is opt-in and closes both ends',fade);
  results.push({name:'Legacy checks',count:legacy.length,ok:legacy.every(r=>r.ok)});
 }finally{await context.close()}
 const reduced=await page.context().browser().newContext({reducedMotion:'reduce'});try{
  const p=await reduced.newPage(),requests=[];p.on('request',r=>requests.push(r.url()));await p.goto('http://127.0.0.1:8137/estudio/loading/');await p.waitForFunction(()=>document.querySelector('latam-cinema')?.q('img')?.naturalWidth>0);
  check('Reduced motion renders the matching poster without downloading video',!requests.some(u=>u.endsWith('.mp4'))&&await p.locator('latam-cinema').evaluate(el=>el.video.paused));
 }finally{await reduced.close()}
 await page.evaluate(r=>window.__cinemaUIChecks=r,results);
}
