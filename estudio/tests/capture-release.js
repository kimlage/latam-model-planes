async(page)=>{
 const ctx=await page.context().browser().newContext({viewport:{width:1000,height:850},acceptDownloads:true}),p=await ctx.newPage();
 try{
  await p.goto('http://127.0.0.1:8137/estudio/loading/?airport=scl&aircraft=B789&situation=aproximacao');
  await p.waitForFunction(()=>document.querySelector('latam-cinema')?.shadowRoot.querySelector('video')?.currentTime>1);
  for(let i=0;i<64;i++){
   if(i===32){await p.locator('#airport').selectOption('sdsc');await p.locator('#situation').selectOption('manutencao');}
   await p.screenshot({path:`output/release-gif/loading-${String(i).padStart(3,'0')}.png`});await p.waitForTimeout(125);
  }
  await p.locator('#edit').click();await p.waitForFunction(()=>window.__estudio?.estado?.producao?.cinema);
  await p.getByTitle('Play / pause (space)',{exact:true}).click();
  for(let i=0;i<64;i++){await p.screenshot({path:`output/release-gif/editor-${String(i).padStart(3,'0')}.png`});await p.waitForTimeout(125)}
  await p.goto('http://127.0.0.1:8137/estudio/loading/runtime.html?airport=scl&aircraft=B789&situation=patio');await p.waitForFunction(()=>window.__cinema);
  const scenes=await p.evaluate(async()=>{__cinema.t=0;const cat=await import('./catalogo.js'),{criarCenaCinema}=await import('./cenas-cinema.js'),{normalizarDocumento}=await import('../js/documento.js');const rows=[];for(const aeroporto of Object.keys(cat.AEROPORTOS))for(const situacao of cat.situacoes(aeroporto))for(const aeronave of cat.aeronaves(aeroporto,situacao)){const c={aeroporto,situacao,aeronave};rows.push({id:[aeroporto,aeronave,situacao].join('-'),config:c,video:cat.renderPronto(c),document:normalizarDocumento(await criarCenaCinema(c))})}return rows});
  const download=p.waitForEvent('download');await p.evaluate(rows=>{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(rows)],{type:'application/json'}));a.download='scenes.json';a.click()},scenes);await(await download).saveAs('output/release-scenes/scenes.json');
 }finally{await ctx.close()}
}
