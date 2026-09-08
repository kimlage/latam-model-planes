async(page)=>{
 const ctx=await page.context().browser().newContext({viewport:{width:1280,height:720}}),p=await ctx.newPage();
 try{
  await p.goto('http://127.0.0.1:8137/estudio/loading/runtime.html?airport=sbgr&aircraft=B789&situation=sobrevoo');await p.waitForFunction(()=>window.__cinema);
  const results=await p.evaluate(async()=>{
   __cinema.t=0;__cinema.mundo.pausar();const {mundo:m}=__cinema;const cat=await import('./catalogo.js'),{criarCenaCinema}=await import('./cenas-cinema.js'),{avaliar}=await import('../js/tempo.js'),{Box3,Vector3,Raycaster}=await import('three');const results=[];
   for(const airport of Object.keys(cat.AEROPORTOS))for(const aircraft of Object.keys(cat.AERONAVES)){
    const d=await criarCenaCinema({aeroporto:airport,aeronave:aircraft,situacao:'patio'});await m.sincronizar(d);m.aplicarAmbiente(d.ambiente);m.aplicarPose(d.camera);
    const a=m.objetos.get(d.objetos.find(o=>o.tipo==='aeronave').id),b=new Box3().setFromObject(a);let framed=true,minGap=Infinity,maxGap=-Infinity;const pavement=m.objetos.get(d.objetos.find(o=>o.slug.endsWith('_pavimentos_precisos')).id);
    for(const wheel of a.userData.nosTrem.filter(o=>o.name.includes('Roda'))){const wb=new Box3().setFromObject(wheel),c=wb.getCenter(new Vector3()),r=new Raycaster(new Vector3(c.x,100,c.z),new Vector3(0,-1,0)),h=r.intersectObject(pavement,true)[0];const gap=h?wb.min.y-h.point.y:Infinity;minGap=Math.min(minGap,gap);maxGap=Math.max(maxGap,gap)}
    for(const t of [0,6,11.9]){m.aplicarTransformacoes(d);m.aplicarLinha(d,avaliar(d,t));m.render();for(const x of [b.min.x,b.max.x])for(const y of [b.min.y,b.max.y])for(const z of [b.min.z,b.max.z]){const v=new Vector3(x,y,z).project(m.cam);framed&&=Math.abs(v.x)<1.05&&Math.abs(v.y)<1.05&&v.z>-1&&v.z<1}}
    const flight=await criarCenaCinema({aeroporto:airport,aeronave:aircraft,situacao:'aproximacao'});await m.sincronizar(flight);m.aplicarPose(flight.camera);let gearHidden=true,cabin=true,restored=true;
    const fa=m.objetos.get(flight.objetos.find(o=>o.tipo==='aeronave').id);
    for(const t of [0,5.9,6,12,23.9,0]){m.aplicarTransformacoes(flight);m.aplicarLinha(flight,avaliar(flight,t));m.render();gearHidden&&=fa.userData.nosTrem.every(o=>!o.visible);cabin&&=!m.cockpit?.visible&&fa.visible;if(t===0)restored&&=fa.visible;}
    results.push({airport,aircraft,fans:fa.userData.fans.length,framed,minGap,maxGap,gearHidden,cabin,restored,ok:fa.userData.fans.length===2&&framed&&Math.abs(minGap)<.03&&Math.abs(maxGap)<.03&&gearHidden&&cabin&&restored});
   }
   return results;
  });await page.evaluate(r=>window.__fleetGeometry=r,results);
 }finally{await ctx.close()}
}
