async(page)=>{
 const ctx=await page.context().browser().newContext({viewport:{width:1280,height:720}}),p=await ctx.newPage(),errors=[],results=[];
 p.on('console',m=>{if(m.type()==='error')errors.push(m.text())});p.on('pageerror',e=>errors.push(e.message));
 try{
  for(const [base,model,situation] of [['scl','B789','aproximacao'],['sbgr','B77W','aproximacao'],['sdsc','A320neo','sobrevoo'],['sdsc','B789','manutencao'],['scl','B763F','patio']]){
   await p.goto(`http://127.0.0.1:8137/estudio/loading/runtime.html?airport=${base}&aircraft=${model}&situation=${situation}`);await p.waitForFunction(()=>window.__cinema);await p.waitForFunction(()=>+getComputedStyle(document.querySelector('#world')).opacity===1);
   const r=await p.evaluate(async()=>{
    const {mundo:m,doc:d}=__cinema,{Vector3,Box3}=await import('three');__cinema.t=0;
    const a=m.objetos.get(d.objetos.find(o=>o.tipo==='aeronave').id),isFlight=['sobrevoo','aproximacao'].includes(d.producao.cinema.situacao),fans=a.userData.fans||[];
    let maxStep=0,maxAngle=0,minSpeed=Infinity,lastPos=null,lastQ=null,surfaces=0,renderPrograms=true;
    m.cena.traverse(o=>{for(const mat of [].concat(o.material||[]))if(mat.userData.surfaceDetail)surfaces++});
    for(let t=0;t<=d.linha.duracao;t+=.05){__cinema.t=t;if(lastPos){const step=a.position.distanceTo(lastPos);maxStep=Math.max(maxStep,step);minSpeed=Math.min(minSpeed,step/.05);maxAngle=Math.max(maxAngle,a.quaternion.angleTo(lastQ))}lastPos=a.position.clone();lastQ=a.quaternion.clone()}
    for(const program of m.renderer.info.programs||[])if(program.diagnostics?.runnable===false)renderPrograms=false;
    __cinema.t=1;const fanMoved=fans.length>=2&&fans.every(f=>Math.abs(f.rotation.x-24)<1e-6);
    m.aplicarTransformacoes(d);const fanReset=fans.every(f=>f.rotation.x===0);
    return{isFlight,surfaces,renderPrograms,maxStep,maxAngle,minSpeed,fanCount:fans.length,fanMoved,fanReset,ok:surfaces>0&&renderPrograms&&fanReset&&(!isFlight||(fanMoved&&minSpeed>150&&maxStep<9&&maxAngle<.015))};
   });results.push({base,model,situation,...r});
   for(const t of situation==='manutencao'?[4,11]:situation==='patio'?[0,6,11.9]:[0,4,8,12,18,23.9]){await p.evaluate(t=>__cinema.t=t,t);await p.screenshot({path:`output/playwright/realismo-${base}-${model}-${situation}-${t}.png`})}
  }
  await page.evaluate(r=>window.__realismo=r,{results,errors});
 }finally{await ctx.close()}
}
