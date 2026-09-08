async(page)=>{
 const ctx=await page.context().browser().newContext({viewport:{width:1280,height:720}}),p=await ctx.newPage();
 try{
  await p.goto('http://127.0.0.1:8137/estudio/?loading=cinema&airport=scl&aircraft=B763F&situation=aproximacao');await p.waitForFunction(()=>window.__estudio?.estado?.producao?.cinema?.aeroporto==='scl');
  const r=await p.evaluate(async()=>({productions:await(await import('./tests/producoes.js')).run(),regression:await(await import('./tests/regression.js')).run()}));
  await page.evaluate(r=>window.__fleetRegression=r,r);
 }finally{await ctx.close()}
}
