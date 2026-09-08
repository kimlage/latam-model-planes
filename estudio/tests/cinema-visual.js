async(page)=>{
 const context=await page.context().browser().newContext({viewport:{width:960,height:540}}),testPage=await context.newPage(),results=[];
 const configs=[];for(const aeroporto of ['sbgr','sdsc'])for(const situacao of aeroporto==='sbgr'?['decolagem','patio']:['reboque','patio'])for(const aeronave of situacao==='reboque'?['B789']:['B77W','B789','A320neo'])configs.push({aeroporto,situacao,aeronave});
 try{
  for(const c of configs){
   const key=`${c.aeroporto}-${c.aeronave}-${c.situacao}`;
   await testPage.goto('http://127.0.0.1:8137/estudio/loading/runtime.html?'+`airport=${c.aeroporto}&aircraft=${c.aeronave}&situation=${c.situacao}`);
   await testPage.waitForFunction(()=>window.__cinema,{timeout:45000});
   const check=await testPage.evaluate(async()=>{
    const {mundo:m,doc:d}=window.__cinema,{Box3,Vector3}=await import('three');
    const protagonist=d.objetos.find(o=>o.tipo==='aeronave');let finite=true,inside=true,minY=Infinity, cameraMoved=false;let first;
    for(let t=.6;t<d.linha.duracao-.5;t+=.5){window.__cinema.t=t;
     const camera=m.cam.position.toArray();if(!first)first=camera;else if(camera.some((v,i)=>Math.abs(v-first[i])>.1))cameraMoved=true;
     const b=new Box3().setFromObject(m.objetos.get(protagonist.id));minY=Math.min(minY,b.min.y);
     for(const x of [b.min.x,b.max.x])for(const y of [b.min.y,b.max.y])for(const z of [b.min.z,b.max.z]){
      const p=new Vector3(x,y,z).project(m.cam);finite&&=[p.x,p.y,p.z].every(Number.isFinite);inside&&=Math.abs(p.x)<1.05&&Math.abs(p.y)<1.05&&p.z>-1&&p.z<1;
     }
    }
    return {finite,inside,cameraMoved,minY,objects:m.objetos.size,aircraft:protagonist.slug};
   });
   results.push({key,...check,ok:check.finite&&check.inside&&check.cameraMoved&&check.aircraft===c.aeronave});
   await testPage.waitForFunction(()=>+getComputedStyle(document.querySelector('#world')).opacity===1);
   for(let i=0;i<5;i++){
    await testPage.evaluate(i=>window.__cinema.t=(window.__cinema.doc.linha.duracao-.04)*i/4,i);
    await testPage.screenshot({path:`output/playwright/qa-cinema/after-${key}-${i}.png`});
   }

  }
 }finally{await context.close()}
 await page.evaluate(r=>window.__cinemaChecks=r,results);
}
