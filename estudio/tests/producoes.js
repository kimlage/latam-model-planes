/* Browser integration checks: await (await import('./tests/producoes.js')).run(). */
import * as THREE from 'three';
import { PRODUCOES, carregarProducao } from '../js/producoes.js';
import { normalizarDocumento } from '../js/documento.js';
import { avaliar } from '../js/tempo.js';
import { planoEm, cameraDoPlano } from '../js/planos.js';
import { documentoParaJson, exportarSequencia } from '../js/exportar.js';
import { gravarEnquadramento } from '../js/diretor.js';

const assert = (v,m) => {if(!v) throw new Error(m);};
const clone = v=>JSON.parse(JSON.stringify(v));
const close = (a,b,eps=1e-5)=>a.every((x,i)=>Math.abs(x-b[i])<eps);
export async function run() {
  const app = window.__estudio, before=clone(app.estado), result=[];
  const storage = Object.fromEntries(Object.keys(localStorage).filter(k=>k.startsWith('latam-estudio/')).map(k=>[k,localStorage.getItem(k)]));
  const test = async (name,fn)=>{try{await fn();result.push({name,ok:true});}catch(e){result.push({name,ok:false,error:e.message});}};
  try {
    for(const p of PRODUCOES) await test(p.id+': load, finite animation and portable assets',async()=>{
      const d = normalizarDocumento(await carregarProducao(p.id));
      assert(d.linha.planos.length>0,'No authored cameras');
      await app.carregarDocumento(d);
      assert(app.mundo.objetos.size===d.objetos.length,'Partial world');
      for(let t=0;t<=d.linha.duracao;t+=0.2){
        const ov=avaliar(d,t,id=>app.mundo.contextoVoo(id,d));
        assert(ov.camera && [...ov.camera.pos,...ov.camera.alvo,ov.camera.fov].every(Number.isFinite),'Nonfinite camera');
        for(const v of ov.objetos.values()) assert((v.pos||[]).every(Number.isFinite),'Nonfinite motion');
      }
      const out=clone(documentoParaJson(d,app.mundo,{comAssets:true}));
      assert(Object.keys(out.assets).length>0,'Assets missing in export');
      const contexto=d.objetos.find(o=>o.slug.endsWith('_contexto'));
      if(contexto) assert(out.assets[contexto.slug].categoria==='ambiente','Context category lost');
      assert(normalizarDocumento(out).linha.planos.length===d.linha.planos.length,'Shot serialization lost');
    });
    await app.carregarDocumento(await carregarProducao('sdsc-visita'));
    await test('Cuts select incoming camera at exact boundaries and final frame',()=>{
      const l=app.estado.linha;
      assert(planoEm(l,3.999).id===l.planos[0].id,'Outgoing shot');
      assert(planoEm(l,4).id===l.planos[1].id,'Incoming shot');
      assert(planoEm(l,16).id===l.planos[2].id,'Final shot');
    });
    await test('Overlaps and orphan follow targets are rejected before replacing the scene',()=>{
      for(const kind of ['overlap','orphan']) {
        const d=clone(app.estado);
        if(kind==='overlap')d.linha.planos[1].inicio=3;
        else d.linha.planos[1].seguir='missing';
        let error;try{normalizarDocumento(d);}catch(e){error=e;}
        assert(error,'Invalid '+kind+' accepted');
      }
    });
    await test('Ground probe ignores hangar roof while aircraft is entering',()=>{
      const d=app.estado, a=d.objetos.find(o=>o.slug==='B789');
      const sample=app.mundo.sondaTerreno(a.id,d)(179.82,-685);
      assert(Math.abs(sample-(-34.72))<0.12,'Wrong hangar datum '+sample);
    });
    await test('Grass stays below concrete across the tow apron',()=>{
      const plate=app.mundo.objetos.get(app.estado.objetos.find(o=>o.slug==='sdsc_pavimentos_precisos').id);
      const ray=new THREE.Raycaster();
      for(const [x,z] of [[100,-720],[150,-750],[180,-780],[220,-750]]) {
        ray.set(new THREE.Vector3(x,1000,z),new THREE.Vector3(0,-1,0));
        const hits=ray.intersectObject(plate,true);
        const material=h=>Array.isArray(h.object.material)?h.object.material[h.face.materialIndex].name:h.object.material.name;
        const concrete=hits.find(h=>material(h).includes('Concrete'));
        const grass=hits.find(h=>material(h).includes('CropPasture'));
        assert(concrete && (!grass || concrete.point.y-grass.point.y>0.02),'Grass intersects concrete at '+x+','+z);
      }
    });
    await test('Towed landing gear stays at the apron datum across the whole sequence',()=>{
      const d=app.estado, a=d.objetos.find(o=>o.slug==='B789');
      for(const t of [0,4,8,12,15.96]) {
        app.dock.irPara(t);
        const o=app.mundo.objetos.get(a.id), b=new THREE.Box3();
        for(const m of o.userData.nosTrem)b.expandByObject(m);
        assert(Math.abs(b.min.y+34.72)<0.12,'Wheels float/sink at '+t+': '+b.min.y);
      }
    });
    await test('Following camera uses evaluated moving position, without mutating the document',()=>{
      const d=clone(app.estado), p=d.linha.planos[0], a=d.objetos.find(o=>o.slug==='B789');
      p.seguir=a.id;p.cameraInicio={pos:[-90,30,70],alvo:[0,7,0],fov:35};p.cameraFim=clone(p.cameraInicio);
      const frozen=JSON.stringify(d), ov=avaliar(d,2);
      assert(close(ov.camera.alvo,ov.objetos.get(a.id).pos.map((v,i)=>v+[0,7,0][i])),'Follow failed');
      assert(JSON.stringify(d)===frozen,'Evaluation mutated document');
    });
    await test('Viewport camera retake updates the selected endpoint and history',()=>{
      const p=app.estado.linha.planos[0], history=app.historico;
      app.dock.cameraLivre=true;app.dock.planoEditado={id:p.id,ponta:'cameraInicio'};
      app.dock.irPara(0);app.mundo.camP.position.x+=10;
      const pos=app.mundo.camP.position.toArray();
      let recorded=false;
      assert(gravarEnquadramento({estado:app.estado,mundo:app.mundo,dock:app.dock,
        registrar:()=>{recorded=true;},redesenhar:()=>app.dock.desenhar()}),'No retake');
      assert(close(p.cameraInicio.pos,pos,0.0011)&&recorded&&!app.dock.cameraLivre,'Retake not saved');
    });
    await test('Imported camera path retains exact endpoints after a retake',async()=>{
      const d=await carregarProducao('gru-decolagem'), p=d.linha.planos[0];
      p.cameraInicio.pos[0]+=12;p.cameraFim.alvo[2]-=5;
      assert(close(cameraDoPlano(p,0).pos,p.cameraInicio.pos),'Start endpoint');
      assert(close(cameraDoPlano(p,p.fim).alvo,p.cameraFim.alvo),'End endpoint');
    });
    await test('Cancel and sequence memory limit restore the renderer',async()=>{
      for(const cancel of [true,false]) {
        const controller=new AbortController();if(cancel)controller.abort();
        const before=app.mundo.poseAtual(), size=app.mundo.renderer.getSize(new THREE.Vector2());
        let error;
        try { await exportarSequencia(app.mundo,app.estado,{larg:160,alt:90,ss:1,quadros:2,maxBytes:1,signal:controller.signal}); }
        catch(e){error=e;}
        assert(error && (cancel?error.name==='AbortError':error.message.includes('512 MB')),'Expected bounded export failure');
        assert(close(app.mundo.poseAtual().pos,before.pos,0.002),'Camera not restored');
        assert(app.mundo.renderer.getSize(new THREE.Vector2()).equals(size),'Render size not restored');
      }
    });
  } finally {
    await app.carregarDocumento(before);
    for(const k of Object.keys(localStorage).filter(k=>k.startsWith('latam-estudio/')))if(!(k in storage))localStorage.removeItem(k);
    for(const [k,v]of Object.entries(storage))localStorage.setItem(k,v);
  }
  console.table(result); return result;
}
