async(page)=>{
 const ctx=await page.context().browser().newContext({viewport:{width:1280,height:720},acceptDownloads:true}),p=await ctx.newPage(),results=[];
 try{for(const [name,query] of [['gru-b77w-aproximacao','airport=sbgr&aircraft=B77W&situation=aproximacao'],['scl-b789-aproximacao','airport=scl&aircraft=B789&situation=aproximacao'],['sdsc-a320-sobrevoo','airport=sdsc&aircraft=A320neo&situation=sobrevoo']]){
  await p.goto('http://127.0.0.1:8137/estudio/loading/runtime.html?'+query);await p.waitForFunction(()=>window.__cinema,{timeout:60000});
  const result=await p.evaluate(async name=>{__cinema.t=1;__cinema.doc.linha.fps=20;const {exportarMp4}=await import('../js/exportar.js');const r=await exportarMp4(__cinema.mundo,__cinema.doc,{larg:1280,alt:720,ss:2},(i,n)=>window.__renderProgress={name,i,n});const a=document.createElement('a');a.id='render-download';a.href=URL.createObjectURL(r.blob);a.download=name+'.mp4';a.textContent='Download';a.style='position:fixed;z-index:999;top:0;left:0;color:white';document.body.append(a);return{bytes:r.bytes,frames:r.quadros}},name);
  const download=p.waitForEvent('download');await p.locator('#render-download').click();await(await download).saveAs('estudio/loading/media/cinema/'+name+'.mp4');results.push({name,...result});
 }}finally{await ctx.close()}
 await page.evaluate(r=>window.__fleetRenders=r,results);
}
