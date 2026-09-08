async(page)=>{
 const ctx=await page.context().browser().newContext({viewport:{width:1280,height:720}}),p=await ctx.newPage();
 try{
  for(const airport of ['sbgr','sdsc','scl'])for(const situation of ['sobrevoo','aproximacao',...(airport==='scl'?['patio']:[])]){
   await p.goto(`http://127.0.0.1:8137/estudio/loading/runtime.html?airport=${airport}&aircraft=B789&situation=${situation}`);await p.waitForFunction(()=>window.__cinema);await p.waitForFunction(()=>+getComputedStyle(document.querySelector('#world')).opacity===1);
   for(const t of situation==='aproximacao'?[0,5.6,6,12,20]:situation==='sobrevoo'?[0,12,23.9]:[0,6,11.9]){await p.evaluate(t=>__cinema.t=t,t);await p.screenshot({path:`output/playwright/fleet-${airport}-${situation}-${t}.png`})}
  }
  for(const aircraft of ['A319','A320ceo','A320neo','A321ceo','A321neo','B763','B77W','B788','B789','B763F','B763BCF']){
   await p.goto(`http://127.0.0.1:8137/estudio/loading/runtime.html?airport=scl&aircraft=${aircraft}&situation=aproximacao`);await p.waitForFunction(()=>window.__cinema);await p.waitForFunction(()=>+getComputedStyle(document.querySelector('#world')).opacity===1);
   for(const t of [5.6,12]){await p.evaluate(t=>__cinema.t=t,t);await p.screenshot({path:`output/playwright/fleet-type-${aircraft}-${t}.png`})}
  }
 }finally{await ctx.close()}
}
