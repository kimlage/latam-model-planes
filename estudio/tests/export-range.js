async(page)=>{
 const ctx=await page.context().browser().newContext(),p=await ctx.newPage();
 try{
  await p.goto('http://127.0.0.1:8137/estudio/loading/runtime.html?airport=scl&aircraft=B789&situation=aproximacao');await p.waitForFunction(()=>window.__cinema);
  const result=await p.evaluate(async()=>{
   const {exportarSequencia}=await import('../js/exportar.js'),{mundo:m,doc:d}=__cinema;__cinema.t=3;
   const times=[],original=m.aplicarLinha;
   m.aplicarLinha=function(...args){times.push(args[1].tempo);return original.apply(this,args)};
   let r;try{r=await exportarSequencia(m,d,{larg:160,alt:90,ss:1,intervaloQuadros:[150,152]})}finally{m.aplicarLinha=original}
   let rejected=0;for(const range of [[-1,2],[2,2],[0,601],[.5,2]])try{await exportarSequencia(m,d,{larg:160,alt:90,intervaloQuadros:range})}catch(e){if(e.message.includes('Intervalo'))rejected++}
   return{times,frames:r.quadros,rejected,ok:r.quadros===2&&Math.abs(times[0]-6)<1e-8&&Math.abs(times[1]-6.04)<1e-8&&rejected===4};
  });await page.evaluate(r=>window.__exportRange=r,result);
 }finally{await ctx.close()}
}
