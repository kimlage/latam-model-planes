async(page)=>{
 const ctx=await page.context().browser().newContext({viewport:{width:1280,height:720}}),p=await ctx.newPage(),results=[];
 try{for(const aircraft of ['A319','A320ceo','A320neo','A321ceo','A321neo','B763','B77W','B788','B789','B763F','B763BCF']){
  await p.goto('http://127.0.0.1:8137/estudio/loading/runtime.html?airport=sdsc&aircraft='+aircraft+'&situation=manutencao');await p.waitForFunction(()=>window.__cinema);await p.waitForFunction(()=>+getComputedStyle(document.querySelector('#world')).opacity===1);
  const r=await p.evaluate(async()=>{
   const {Box3,Vector3,Raycaster}=await import('three'),{mundo:m,doc:d}=__cinema,a=m.objetos.get(d.objetos.find(o=>o.tipo==='aeronave').id);let inside=true,cameraSafe=true,minGap=Infinity;
   const b=new Box3().setFromObject(a);
   // Parked service equipment remains outside x=714..786 native. The 777
   // is the widest supported aircraft; the lowest roof chord is above 19 m.
   const equipmentClear=b.min.x>714-570.18&&b.max.x<786-570.18;
   const shellClear=b.min.z>-(1684-979.62)&&b.max.z<-(1593-979.62)&&b.max.y< -34.72+19;
   const floor=[];m.cena.traverse(o=>{if(o.isMesh&&o.name.includes('Hangar9_Floor'))floor.push(o)});
   const ray=new Raycaster();
   for(const wheel of a.userData.nosTrem.filter(o=>o.name.includes('Roda'))){const w=new Box3().setFromObject(wheel),c=w.getCenter(new Vector3());ray.set(new Vector3(c.x,100,c.z),new Vector3(0,-1,0));const h=ray.intersectObjects(floor,true)[0];if(!h)throw Error('No floor under wheel');minGap=Math.min(minGap,w.min.y-h.point.y)}
   for(let t=0;t<=14;t+=.25){__cinema.t=t;const c=m.cam.position;cameraSafe&&=c.x>116&&c.x<243&&c.z>-704&&c.z<-612;
    if(t<8)for(const x of [b.min.x,b.max.x])for(const y of [b.min.y,b.max.y])for(const z of [b.min.z,b.max.z]){const v=new Vector3(x,y,z).project(m.cam);inside&&=Math.abs(v.x)<1.05&&Math.abs(v.y)<1.05&&v.z>-1&&v.z<1;}
   }
   return{equipmentClear,shellClear,wideShotInside:inside,cameraSafe,wheelFloorGap:minGap,contactPatches:m.contatoInterior.children.length,shots:d.linha.planos.length};
  });
  results.push({aircraft,...r,ok:r.equipmentClear&&r.shellClear&&r.wideShotInside&&r.cameraSafe&&Math.abs(r.wheelFloorGap)<.02&&r.shots===2});
  for(const t of [0,4,7.9,8,11,13.96]){await p.evaluate(t=>__cinema.t=t,t);await p.screenshot({path:`output/playwright/interior-${aircraft}-${t}.png`})}
 }}finally{await ctx.close()}
 await page.evaluate(r=>window.__interiorQA=r,results);
}
