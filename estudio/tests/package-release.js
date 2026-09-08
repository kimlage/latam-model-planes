async(page)=>{
 const p=page,errors=[],foreign=[];p.on('pageerror',e=>errors.push(e.message));p.on('request',r=>{if(/^https?:/.test(r.url())&&!r.url().startsWith('http://127.0.0.1:8138/'))foreign.push(r.url())});
 await p.goto('http://127.0.0.1:8138/estudio/loading/runtime.html?airport=scl&aircraft=B789&situation=patio');await p.waitForFunction(()=>window.__cinema);
 const results=await p.evaluate(async()=>{
  __cinema.t=0;const m=__cinema.mundo,{normalizarDocumento}=await import('../js/documento.js'),{avaliar}=await import('../js/tempo.js'),rows=await(await fetch('../../catalogo.json')).json(),results=[];
  for(const row of rows){const response=await fetch('../../'+row.scene);if(!response.ok)throw Error(row.scene);const d=normalizarDocumento(await response.json());await m.sincronizar(d);m.aplicarAmbiente(d.ambiente);m.aplicarPose(d.camera);
   for(const fraction of [0,.5,.99]){m.aplicarTransformacoes(d);m.aplicarLinha(d,avaliar(d,d.linha.duracao*fraction));m.render();if(![...m.camP.position.toArray(),m.camP.near,m.camP.far].every(Number.isFinite))throw Error(row.id+' camera')}
   results.push({id:row.id,objects:m.objetos.size,ok:true});
  }return results;
 });await page.evaluate(data=>window.__packageQA=data,{results,errors,foreign,headless:await p.evaluate(()=>navigator.userAgent.includes('HeadlessChrome'))});
}
