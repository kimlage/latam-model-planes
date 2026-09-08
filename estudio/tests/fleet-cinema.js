async(page)=>{
 const ctx=await page.context().browser().newContext({viewport:{width:1280,height:720}}),p=await ctx.newPage();const errors=[];p.on('pageerror',e=>errors.push(e.message));
 try{
  await p.goto('http://127.0.0.1:8137/estudio/loading/runtime.html?airport=scl&aircraft=B789&situation=patio');await p.waitForFunction(()=>window.__cinema);await p.waitForFunction(()=>+getComputedStyle(document.querySelector('#world')).opacity===1);
  const matrix=await p.evaluate(async()=>{
   __cinema.t=0;const cat=await import('./catalogo.js'),{criarCenaCinema}=await import('./cenas-cinema.js'),{normalizarDocumento}=await import('../js/documento.js'),{avaliar}=await import('../js/tempo.js');const rows=[];
   for(const aeroporto of Object.keys(cat.AEROPORTOS))for(const situacao of cat.situacoes(aeroporto))for(const aeronave of cat.aeronaves(aeroporto,situacao)){
    const c={aeroporto,situacao,aeronave},d=normalizarDocumento(await criarCenaCinema(c));let finite=true,moving=false;let last;
    for(let t=0;t<=d.linha.duracao;t+=.25){const ov=avaliar(d,t);finite&&=!!ov.camera&&[...ov.camera.pos,...ov.camera.alvo,ov.camera.fov].every(Number.isFinite);if(last)moving||=ov.camera.pos.some((v,i)=>Math.abs(v-last[i])>.001);last=ov.camera.pos;}
    rows.push({...c,ok:finite&&moving,shots:d.linha.planos.length});
   }
   return rows;
  });
  const rendered=[];
  for(const airport of ['sbgr','sdsc','scl'])for(const situation of ['patio','sobrevoo','aproximacao']){
   await p.goto(`http://127.0.0.1:8137/estudio/loading/runtime.html?airport=${airport}&aircraft=B789&situation=${situation}`);await p.waitForFunction(()=>window.__cinema);await p.waitForFunction(()=>+getComputedStyle(document.querySelector('#world')).opacity===1);
   for(const t of situation==='aproximacao'?[0,5.6,6,12,20]:situation==='sobrevoo'?[0,12,23.9]:[0,6,11.9]){
    await p.evaluate(t=>__cinema.t=t,t);await p.screenshot({path:`output/playwright/fleet-${airport}-${situation}-${t}.png`});
    rendered.push(await p.evaluate(()=>({config:__cinema.doc.producao.cinema,t:__cinema.t,near:__cinema.mundo.cam.near,aproximacao:!!__cinema.mundo.aproximacao?.visible})));
   }
  }
  await page.evaluate(r=>window.__fleetQA=r,{matrix,rendered,errors});
 }finally{await ctx.close()}
}
