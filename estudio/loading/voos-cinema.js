import * as THREE from 'three';
import {novaTrilha,novaChave} from '../js/tempo.js';
export const FROTA={A319:[33.84,3.955],A320ceo:[37.57,3.955],A320neo:[37.57,3.955],A321ceo:[44.51,3.985],A321neo:[44.51,3.985],B763:[54.94,4.61],B77W:[73.86,5.67],B788:[56.72,5.32],B789:[62.81,5.42],B763F:[54.94,4.61],B763BCF:[54.94,4.61]};
export const BASES={sbgr:{pos:[-867.47,-4.39,-1095.26],yaw:286.35,centro:[-200,-400]},sdsc:{pos:[184.79028,-34.72,-751.85095],yaw:73,centro:[200,-600]},scl:{pos:[175.26,.05,.55],yaw:92.6,centro:[0,0]}};
const rad=THREE.MathUtils.degToRad;
/** One shared trajectory drives aircraft and external camera. Local -X is the nose. */
export function montarVoo(d,c){
 const a=d.objetos.find(o=>o.tipo==='aeronave'),[L,h]=FROTA[c.aeronave],b=BASES[c.aeroporto],close=c.situacao==='aproximacao';
 const duration=24;d.linha.duracao=duration;d.linha.fps=25;
 if(close)a.nivel='alta';
 const pos=novaTrilha('objeto.pos',a.id),rot=novaTrilha('objeto.rot',a.id),gear=novaTrilha('objeto.trem',a.id);
 gear.chaves=[novaChave(0,false,'linear')];d.linha.trilhas=[pos,rot,gear];
 const path=[],side=c.aeroporto==='scl'?-1:1;
 const stops=[{t:0,pos:[-L*.95,18,45],alvo:[-L*.25,h,0]},
  {t:6,pos:[-L*.6,h+4,12],alvo:[-L*.35,h,0]},
  {t:12,pos:[-L*.1,12,40],alvo:[-L*.15,h,0]},
  {t:24,pos:[L*.7,35,L*1.25],alvo:[0,h,0]}];
 const cameraCurve=new THREE.CatmullRomCurve3(stops.map(s=>new THREE.Vector3(...s.pos)),false,'centripetal');
 const targetCurve=new THREE.CatmullRomCurve3(stops.map(s=>new THREE.Vector3(...s.alvo)),false,'centripetal');
 let previousRotation=null;
 for(let i=0;i<=240;i++){
  const t=i/10,u=t/duration;
  const p=[b.centro[0]-380+130*Math.sin(Math.PI*u),300+20*Math.sin(Math.PI*u),b.centro[1]-1900+3800*u];
  const vx=130*Math.PI*Math.cos(Math.PI*u),vz=3800,yaw=Math.atan2(vz,-vx)*180/Math.PI;
  const speed=Math.hypot(vx,vz)/duration,vertical=20*Math.PI*Math.cos(Math.PI*u)/duration;
  const headingRate=(vz*(-130*Math.PI*Math.PI*Math.sin(Math.PI*u)))/(vx*vx+vz*vz)/duration;
  const bank=Math.atan(speed*headingRate/9.80665),pitch=Math.atan2(vertical,speed)+rad(2);
  const q=new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,1,0),rad(yaw))
   .multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,0,1),-pitch))
   .multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1,0,0),bank));
  const e=new THREE.Euler().setFromQuaternion(q,'XYZ'),rotation=[e.x,e.y,e.z].map(THREE.MathUtils.radToDeg);
  if(previousRotation)rotation.forEach((v,k)=>{while(rotation[k]-previousRotation[k]>180)rotation[k]-=360;while(rotation[k]-previousRotation[k]<-180)rotation[k]+=360});
  previousRotation=rotation;
  const world=v=>new THREE.Vector3(...v).applyQuaternion(q).add(new THREE.Vector3(...p)).toArray();
  pos.chaves.push(novaChave(t,p,'linear'));rot.chaves.push(novaChave(t,rotation,'linear'));
  let camera;
  if(close){
   const cp=cameraCurve.getPointAt(u),ct=targetCurve.getPointAt(u);cp.z*=side;ct.z*=side;
   camera={pos:world(cp.toArray()),alvo:world(ct.toArray()),fov:46};
  }else{const k=L/62.81;camera={pos:world([-L*.8,28*k,85*k*side]),alvo:world([-L*.12,3,0]),fov:42+2*Math.sin(Math.PI*u)}}
  path.push({u,...camera});
 }
 d.linha.planos=[{id:crypto.randomUUID(),nome:close?'Passagem próxima · revelação da base':'Travelling aéreo · aeroporto sob as asas',inicio:0,fim:duration,curva:'linear',cameraInicio:path[0],cameraFim:path.at(-1),caminho:path}];
 a.pos=pos.chaves[0].v;a.rot=rot.chaves[0].v;
 d.camera={...path[0],orto:false};
 d.ambiente.sol.elev=24;d.ambiente.sol.azim=c.aeroporto==='scl'?240:315;d.ambiente.envIntensidade=.78;
 d.ambiente.sol.intensidade=3.25;
 d.ambiente.neblina={ligado:true,densidade:c.aeroporto==='scl'?.22:.36};
}
