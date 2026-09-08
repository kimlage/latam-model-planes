async (page) => {
  const errors=[],results=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8137/estudio/loading/');
  await page.evaluate(async()=>{
    const map=document.createElement('script');map.type='importmap';
    map.textContent=JSON.stringify({imports:{three:'/estudio/vendor/three/three.module.js'}});document.head.append(map);
    window.__loadingTests=await(await import('/estudio/tests/loading.js')).run();
  });
  results.push(...await page.evaluate(()=>window.__loadingTests));
  const check=(name,ok)=>results.push({name,ok:!!ok});
  await page.waitForFunction(()=>document.querySelector('latam-loading').video.readyState>=2);
  await page.locator('latam-loading video').evaluate(v=>{v.currentTime=3.9;v.play();});
  await page.waitForFunction(()=>document.querySelector('latam-loading').video.currentTime<1);
  check('Actual MP4 plays across its loop boundary',true);
  await page.getByRole('button',{name:'Simular carregamento',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('latam-loading').getAttribute('state')==='ready');
  check('Demo reaches ready and pauses the movie',await page.locator('latam-loading video').evaluate(v=>v.paused));
  await page.getByRole('button',{name:'Reiniciar prévia',exact:true}).click();
  await page.setViewportSize({width:1440,height:900});
  await page.screenshot({path:'output/playwright/loading-desktop.png'});
  await page.setViewportSize({width:390,height:844});
  check('Mobile has no horizontal or vertical overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth&&document.documentElement.scrollHeight<=innerHeight));
  await page.screenshot({path:'output/playwright/loading-mobile.png'});
  await page.getByRole('button',{name:'Em um painel',exact:true}).click();
  await page.screenshot({path:'output/playwright/loading-panel.png'});
  const browser=page.context().browser();
  const reduced=await browser.newContext({reducedMotion:'reduce'});
  try {
    const p=await reduced.newPage(),requests=[];p.on('request',r=>requests.push(r.url()));
    await p.goto('http://127.0.0.1:8137/estudio/loading/');
    await p.waitForFunction(()=>document.querySelector('latam-loading')?.shadowRoot?.querySelector('img').naturalWidth>0);
    check('Reduced motion shows poster and never requests video or 3D runtime',await p.locator('latam-loading video').evaluate(v=>v.paused&&!v.hasAttribute('src'))&&!requests.some(u=>/\.mp4|three|\.glb/.test(u)));
    await p.emulateMedia({reducedMotion:'no-preference'});
    await p.waitForFunction(()=>!document.querySelector('latam-loading').video.paused);
    await p.emulateMedia({reducedMotion:'reduce'});
    await p.waitForFunction(()=>document.querySelector('latam-loading').video.paused);
    check('Live motion preference change pauses video',await p.locator('latam-loading video').evaluate(v=>v.paused));
  } finally {await reduced.close();}
  const failure=await browser.newContext();
  try {
    const p=await failure.newPage();await p.route('**/flight.mp4',route=>route.abort());
    await p.goto('http://127.0.0.1:8137/estudio/loading/');
    await p.waitForFunction(()=>document.querySelector('latam-loading')?.video.error);
    check('Failed media retains loaded poster and loading message',await p.locator('latam-loading').evaluate(el=>el.shadowRoot.querySelector('img').naturalWidth===800&&!el.video.classList.contains('playing')&&el.shadowRoot.querySelector('.message').textContent.length>0));
  } finally {await failure.close();}
  check('No JavaScript errors',errors.length===0);
  await page.evaluate(results=>window.__loadingFinalTests=results,results);
}
