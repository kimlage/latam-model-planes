/* Run through loading-browser.js, which installs the test-only Three.js import map. */
import {carregarProducao} from '../js/producoes.js';
import {avaliar} from '../js/tempo.js';
import {normalizarDocumento} from '../js/documento.js';
const assert=(v,m)=>{if(!v)throw Error(m);};
export async function run(){
 const results=[];
 const test=async(name,fn)=>{try{await fn();results.push({name,ok:true});}catch(e){results.push({name,ok:false,error:e.message});}};
 await test('Loop closes position, rotation, camera and velocity',async()=>{
  const d=normalizarDocumento(await carregarProducao('latam-loading')),id=d.objetos[0].id;
  const samples=[0,.04,3.96,4].map(t=>avaliar(d,t));
  assert(d.linha.loop&&d.linha.duracao===4&&d.linha.fps===25,'Loop timing');
  for(const channel of ['pos','rot']){
   const [a,b,c,z]=samples.map(s=>s.objetos.get(id)[channel]);
   a.forEach((v,i)=>{assert(Math.abs(v-z[i])<1e-8,'Open seam');assert(Math.abs((b[i]-v)-(z[i]-c[i]))<1e-8,'Velocity discontinuity');});
  }
  assert(JSON.stringify(samples[0].camera)===JSON.stringify(samples[3].camera),'Camera jump');
  assert(samples.every(s=>s.objetos.get(id).trem===false),'Gear visible');
 });
 const el=document.createElement('latam-loading');el.setAttribute('paused','');document.body.append(el);
 const q=s=>el.shadowRoot.querySelector(s);
 try{
  await test('Indeterminate status does not invent a percentage',()=>{assert(!q('.track').hasAttribute('aria-valuenow'),'Fake percent');assert(q('.percent').textContent==='','Fake text');});
  await test('Real progress clamps bounds and invalid values remain indeterminate',()=>{el.setAttribute('progress','42');assert(q('.track').getAttribute('aria-valuenow')==='42','Lost progress');el.setAttribute('progress','200');assert(q('.track').getAttribute('aria-valuenow')==='100','Unbounded');el.setAttribute('progress','abc');assert(!q('.track').hasAttribute('aria-valuenow'),'NaN exposed');el.removeAttribute('progress');});
  await test('Completion stops playback and releases busy state',()=>{el.setAttribute('state','ready');assert(el.video.paused,'Still playing');assert(q('.track').getAttribute('aria-busy')==='false','Still busy');assert(q('.message').textContent.includes('Tudo pronto'),'No completion');});
  await test('Failure has a working retry event and no progressbar',()=>{el.setAttribute('state','error');let retries=0;el.addEventListener('retry',()=>retries++);q('.retry').click();assert(retries===1&&!q('.retry').hidden,'No retry');assert(q('.track').hidden,'Progress on error');});
  await test('Status text is inserted safely',()=>{el.setAttribute('message','<img src=x onerror=alert(1)>');assert(q('.message').children.length===0,'HTML injected');});
  await test('Detached component pauses playback',()=>{el.remove();assert(el.video.paused,'Leaked playback');});
 }finally{el.remove();}
 return results;
}
