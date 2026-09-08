async(page)=>{
 const ctx=await page.context().browser().newContext({viewport:{width:960,height:540},acceptDownloads:true});const p=await ctx.newPage();const results=[];
 try{for(const [name,query] of [['sdsc-reboque','airport=sdsc&aircraft=B789&situation=reboque'],['sdsc-b789-interior','airport=sdsc&aircraft=B789&situation=manutencao']]){
  await p.goto('http://127.0.0.1:8137/estudio/loading/runtime.html?'+query);await p.waitForFunction(()=>window.__cinema,{timeout:45000});
  const result=await p.evaluate(async name=>{__cinema.t=1;const {exportarMp4}=await import('../js/exportar.js');const r=await exportarMp4(__cinema.mundo,__cinema.doc,{larg:name==='sdsc-b789-interior'?1280:960,alt:name==='sdsc-b789-interior'?720:540,ss:2},(i,n)=>window.__renderProgress={i,n});const a=document.createElement('a');a.id='render-download';a.href=URL.createObjectURL(r.blob);a.download=name+'.mp4';a.textContent='Download';a.style='position:fixed;z-index:999;top:0;left:0;color:white';document.body.append(a);return{bytes:r.bytes,frames:r.quadros}},name);
  const download=p.waitForEvent('download');await p.locator('#render-download').click();await(await download).saveAs('estudio/loading/media/cinema/'+name+'.mp4');results.push({name,...result});
 }}finally{await ctx.close()}
 await page.evaluate(r=>window.__renders=r,results);
}
