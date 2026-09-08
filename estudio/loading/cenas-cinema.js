import {carregarProducao} from '../js/producoes.js';
import {estadoPadrao,novoObjeto} from '../js/estado.js';
import {validar,nome} from './catalogo.js';
const clone=v=>JSON.parse(JSON.stringify(v));
import {FROTA,BASES,montarVoo} from './voos-cinema.js';
const comprimento=Object.fromEntries(Object.entries(FROTA).map(([k,v])=>[k,v[0]]));
export async function criarCenaCinema(config){
 const c=validar(config);let d;
 if(c.situacao==='reboque')d=await carregarProducao('sdsc-reboque');
 else if(c.situacao==='decolagem'){
  d=await carregarProducao('gru-decolagem');
  const a=d.objetos.find(o=>o.tipo==='aeronave');a.slug=c.aeronave;a.nome=Aeronave(c);a.nivel=c.aeronave==='B77W'?'heroi':'web';
  const k=Math.sqrt(comprimento[c.aeronave]/74.03);
  for(const p of d.linha.planos){
   for(const pose of [p.cameraInicio,p.cameraFim,...p.caminho||[]])pose.pos=pose.pos.map((v,i)=>pose.alvo[i]+(v-pose.alvo[i])*k);
  }
  d.camera={...clone(d.linha.planos[0].cameraInicio),orto:false};
 }else{
  d=estadoPadrao();d.linha.duracao=12;d.linha.fps=25;
  d.ambiente.chao.ligado=false;d.ambiente.grade=false;d.ambiente.sol={elev:30,azim:315,intensidade:2.8,cor:'#fff1df'};d.ambiente.envIntensidade=1.4;
  const gru=c.aeroporto==='sbgr',base=BASES[c.aeroporto];
  // Open apron staging: clear fixed jet bridges / service equipment and use the clear hangar 9 forecourt.
  const a=novoObjeto('aeronave',c.aeronave,Aeronave(c),{pos:base.pos,rot:[0,base.yaw,0],nivel:c.aeronave==='B77W'?'heroi':'web'});
  d.objetos=[novoObjeto('cenario',c.aeroporto+'_pavimentos_precisos','Pátios e pistas',{travado:true}),novoObjeto('cenario',c.aeroporto+'_contexto','Aeroporto e entorno',{travado:true}),a];
  if(gru||c.aeroporto==='scl')d.objetos.push(novoObjeto('cenario',c.aeroporto+'_relevo','Relevo contínuo',{travado:true}));
  if(c.aeroporto==='scl')d.ambiente.neblina={ligado:true,densidade:.08};
  const k=Math.sqrt(comprimento[c.aeronave]/74.03),offset=gru?[[-92,26,84],[-60,18,105]]:[[-125,32,-85],[-105,24,-110]];
  const poses=offset.map(pos=>({pos:pos.map(v=>v*k),alvo:[0,6*k,0],fov:36}));
  d.linha.planos=[{id:crypto.randomUUID(),nome:'Aproximação · aeronave no aeroporto',inicio:0,fim:12,curva:'linear',seguir:a.id,cameraInicio:poses[0],cameraFim:poses[1]}];
  d.camera={pos:poses[0].pos.map((v,i)=>v+a.pos[i]),alvo:poses[0].alvo.map((v,i)=>v+a.pos[i]),fov:36,orto:false};
 }
 if(c.aeroporto==='sdsc'&&!d.objetos.some(o=>o.slug==='sdsc_hangar9_interior'))d.objetos.push(novoObjeto('cenario','sdsc_hangar9_interior','Interior do hangar 9',{travado:true}));
 if(c.situacao==='manutencao'){
  const a=d.objetos.find(o=>o.tipo==='aeronave');a.pos=[179.82,-34.72,-660.38];a.rot=[0,90,0];a.nivel=c.aeronave==='B789'?'alta':'heroi';
  d.linha.duracao=14;d.ambiente.envPreset='sala';d.ambiente.envIntensidade=.3;d.ambiente.sol.intensidade=1.8;d.render.exposicao=1.05;
  const inicio={pos:[121,-26,-630],alvo:[180,-27,-660],fov:62},fim={pos:[125,-24,-625],alvo:[180,-27,-660],fov:62};
  d.linha.planos=[{id:crypto.randomUUID(),nome:'Interior · aproximação pela área de manutenção',inicio:0,fim:8,curva:'suave',cameraInicio:inicio,cameraFim:fim}];
  d.linha.planos.push({id:crypto.randomUUID(),nome:'Detalhe · motor e área de trabalho',inicio:8,fim:14,curva:'suave',cameraInicio:{pos:[133,-30,-627],alvo:[166,-31,-652],fov:52},cameraFim:{pos:[136,-30,-631],alvo:[166,-31,-652],fov:52}});
  const k= comprimento[c.aeronave]/62.81;
  for(const pose of [d.linha.planos[1].cameraInicio,d.linha.planos[1].cameraFim])for(const key of ['pos','alvo'])pose[key]=pose[key].map((v,i)=>a.pos[i]+(v-a.pos[i])*k);
  d.camera={...clone(inicio),orto:false};
 }
 if(['sobrevoo','aproximacao'].includes(c.situacao))montarVoo(d,c);
 d.nome=nome(c);d.linha.loop=true;d.render.pixelRatioMax=1.5;
 d.producao={...d.producao,cinema:c,transicao:'fade-black',nota:'Plano operacional repetido com passagem pelo preto. Trajetória cinematográfica; não simula desempenho certificado da aeronave.'};
 return d;
}
function Aeronave(c){return c.aeronave+' · protagonista';}
