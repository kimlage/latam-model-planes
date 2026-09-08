async(page)=>{
 const ctx=await page.context().browser().newContext({viewport:{width:1280,height:720},acceptDownloads:true}),p=await ctx.newPage(),results=[];
 try{for(const [name,query] of [['gru-decolagem','airport=sbgr&aircraft=B77W&situation=decolagem'],['gru-a320-patio','airport=sbgr&aircraft=A320neo&situation=patio'],['sdsc-reboque','airport=sdsc&aircraft=B789&situation=reboque'],['sdsc-b789-interior','airport=sdsc&aircraft=B789&situation=manutencao'],['gru-b77w-aproximacao','airport=sbgr&aircraft=B77W&situation=aproximacao'],['scl-b789-aproximacao','airport=scl&aircraft=B789&situation=aproximacao'],['sdsc-a320-sobrevoo','airport=sdsc&aircraft=A320neo&situation=sobrevoo']]){
  await p.goto('http://127.0.0.1:8137/estudio/loading/runtime.html?'+query);await p.waitForFunction(()=>window.__cinema,{timeout:60000});
  const total=await p.evaluate(()=>{__cinema.t=1;return Math.round(__cinema.doc.linha.duracao*__cinema.doc.linha.fps)});const parts=[];
  for(let start=0;start<total;start+=150){
   const end=Math.min(total,start+150),part=String(parts.length).padStart(2,'0');
   const result=await p.evaluate(async({name,start,end})=>{const {exportarMp4}=await import('../js/exportar.js');const r=await exportarMp4(__cinema.mundo,__cinema.doc,{larg:1280,alt:720,ss:2,intervaloQuadros:[start,end]},(i,n)=>window.__renderProgress={name,start,i,n});document.querySelector('#render-download')?.remove();const a=document.createElement('a');a.id='render-download';a.href=URL.createObjectURL(r.blob);a.download=name+'.mp4';a.textContent='Download';a.style='position:fixed;z-index:999;top:0;left:0;color:white';document.body.append(a);return{bytes:r.bytes,frames:r.quadros}},{name,start,end});
   const download=p.waitForEvent('download');await p.locator('#render-download').click();await(await download).saveAs('output/realismo-parts/'+name+'-'+part+'.mp4');parts.push({part,...result});
   await p.evaluate(()=>{const a=document.querySelector('#render-download');URL.revokeObjectURL(a.href);a.remove()});
  }
  results.push({name,parts});

 }}finally{await ctx.close()}
 await page.evaluate(r=>window.__realismoRenders=r,results);
}
