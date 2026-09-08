async(page)=>{
 const results=[];
 for(const logarithmic of [false,true,"tight"]){
  const ctx=await page.context().browser().newContext({viewport:{width:1280,height:720},deviceScaleFactor:1}),p=await ctx.newPage();
  try{
   await ctx.route('**/js/mundo.js',async route=>{const r=await route.fetch();await route.fulfill({response:r,body:(await r.text()).replace('antialias: true,',`logarithmicDepthBuffer: ${logarithmic===true}, antialias: true,`).replace('d * 0.1, 0.2',logarithmic==='tight'?'d * 0.1, 0.2':'d * 0.01, 0.2')})});
   await p.goto('http://127.0.0.1:8137/estudio/loading/runtime.html?airport=scl&aircraft=B789&situation=aproximacao');await p.waitForFunction(()=>window.__cinema);
   const result=await p.evaluate(()=>{
    const m=__cinema.mundo,c=document.createElement('canvas');c.width=1280;c.height=720;const ctx=c.getContext('2d',{willReadFrequently:true});let previous,delta=0,changed=0;
    // Tiny camera motion: the roof cannot materially move between these samples.
    for(let i=0;i<30;i++){__cinema.t=18+i*.00002;ctx.drawImage(m.renderer.domElement,0,0,1280,720);const pixels=ctx.getImageData(820,595,230,100).data;if(previous)for(let k=0;k<pixels.length;k+=4){const d=Math.abs(pixels[k]-previous[k])+Math.abs(pixels[k+1]-previous[k+1])+Math.abs(pixels[k+2]-previous[k+2]);delta+=d;if(d>30)changed++}previous=pixels}
    return{delta,changed,logDepth:m.renderer.capabilities.logarithmicDepthBuffer};
   });await p.screenshot({path:'output/playwright/roof-depth-'+logarithmic+'.png'});results.push(result);
  }finally{await ctx.close()}
 }
 await page.evaluate(r=>window.__roofDepth=r,results);
}
