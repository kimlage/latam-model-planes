/* Complete operations assembled from the native field and shot sources.
 * Positions are metres in the field plate's datum, not eyeballed asset rows.
 * Parked fleet allocation is illustrative, as in fleet_placement.py.
 */
import { estadoPadrao, novoObjeto } from './estado.js';
import { novaTrilha, amostrarTrilha } from './tempo.js';

export const PRODUCOES = [
  {id:'latam-loading',nome:'Voo isolado · estudo anterior',descricao:'Estudo de 777 sem cenário. A série de loadings com aeroportos está na biblioteca cinematográfica.',uso:'4 s · interface · loop contínuo'},
  {id:'gru-decolagem',nome:'GRU · decolagem 10L',descricao:'777 em movimento, pistas, terminais, cidade e serra.',uso:'8 s · operação aérea · acompanhamento contínuo'},
  {id:'sdsc-reboque',nome:'São Carlos · entrada no hangar 9',descricao:'787, trator e barra coordenados até a entrada no hangar aberto.',uso:'16 s · manutenção · sequência operacional'},
  {id:'gru-institucional',nome:'GRU · apresentação do aeroporto',descricao:'Três planos: implantação, terminais e frota no pátio.',uso:'24 s · institucional · montagem com cortes'},
  {id:'sdsc-visita',nome:'São Carlos · visita ao MRO',descricao:'Visão da base, aproximação do hangar e acompanhamento do reboque.',uso:'16 s · apresentação técnica · três câmeras'},
];
const clone = v => JSON.parse(JSON.stringify(v));
const fetchJson = async rel => {
  const r = await fetch(new URL(rel,import.meta.url));
  if(!r.ok) throw new Error(`Não foi possível carregar a produção: ${r.status}`);
  return r.json();
};
const contexto = campo => [
  novoObjeto('cenario',campo+'_pavimentos_precisos','Pistas e pátios',{travado:true}),
  novoObjeto('cenario',campo+'_contexto','Edificações e entorno',{travado:true}),
  ...(campo==='sbgr'?[novoObjeto('cenario','sbgr_relevo','Relevo contínuo',{travado:true})]:[novoObjeto('cenario','sdsc_hangar9_interior','Interior do hangar 9',{travado:true})]),
];
const pose = (pos,alvo,fov=35)=>({pos,alvo,fov});
const plano = (nome,inicio,fim,a,b,seguir=null) => ({id:crypto.randomUUID(),nome,inicio,fim,
  curva:'linear',seguir,cameraInicio:a,cameraFim:b||clone(a)});
function base(nome,campo,duracao) {
  const d = estadoPadrao(); d.nome = nome;
  d.objetos = contexto(campo);
  d.ambiente.chao.ligado = false; d.ambiente.grade = false;
  d.ambiente.sol = {elev:38,azim:315,intensidade:2.6,cor:'#fff3df'};
  d.ambiente.envIntensidade = 1.4;
  d.ambiente.neblina = {ligado:true,densidade:1.2};
  d.linha.duracao = duracao; d.linha.loop = false;
  d.render.pixelRatioMax = 1.5; d.render.sombraPx = 2048;
  return d;
}
function estacionado(d,slug,nome,pos,yaw) {
  const o = novoObjeto('aeronave',slug,nome,{pos,rot:[0,yaw,0]});
  d.objetos.push(o); return o;
}
function trilha(d,canal,ref,rows,valor) {
  const tr = novaTrilha(canal,ref);
  tr.chaves = rows.map(r=>({t:r.t,v:valor(r),e:'linear'}));
  d.linha.trilhas.push(tr);
}

async function reboque(visita=false) {
  const data = await fetchJson('../producoes/reboque-trajetoria.json');
  const rows = data.quadros;
  const d = base(visita?'São Carlos — visita ao MRO':'São Carlos — reboque para o hangar 9','sdsc',16);
  d.producao = {fonte:data.fonte,nota:'Trajetória importada quadro a quadro do master; a entrada no hangar usa sua abertura e piso corrigidos.'};
  const a = estacionado(d,'B789','787-9 · em reboque',rows[0].aircraft.pos,rows[0].aircraft.rot[1]);
  const tug = novoObjeto('cenario','sdsc_tug_operacional','Trator · trajetória coordenada',rows[0].tug);
  const bar = novoObjeto('cenario','sdsc_barra_reboque','Barra · ligação com trem de nariz',rows[0].bar);
  d.objetos.push(tug,bar);
  for(const [ob,key] of [[a,'aircraft'],[tug,'tug'],[bar,'bar']]) {
    trilha(d,'objeto.pos',ob.id,rows,r=>r[key].pos);
    trilha(d,'objeto.rot',ob.id,rows,r=>r[key].rot);
  }
  trilha(d,'objeto.direcaoTrem',a.id,rows,r=>r.steer);
  // Real fleet stands from build_scenery.MRO_STANDS, on the MRO platform.
  estacionado(d,'B763','767 · manutenção',[902-570.18,-34.72,-(1786-979.62)],179);
  estacionado(d,'A320neo','A320 · pátio',[900-570.18,-34.72,-(1838-979.62)],179);
  const camera0 = rows[0].camera, camera1 = rows.at(-1).camera;
  d.camera = {...camera0,orto:false};
  d.linha.planos = visita ? [
    plano('01 · A base de manutenção',0,4,pose([-400,250,-1180],[270,-15,-790],44),pose([-270,195,-1120],[255,-18,-765],44)),
    plano('02 · Hangar 9 e operação',4,8,pose([-40,35,-920],[180,-23,-750],42),pose([8,16,-880],[180,-23,-730],40)),
    plano('03 · Entrada coordenada',8,16,rows[200].camera,camera1),
  ] : [plano('Reboque · aproximação e entrada',0,16,camera0,camera1)];
  // Camera endpoints retain the native composition; the director can retake it.
  if (!visita) d.linha.planos[0].caminho = [...rows.map(r=>({u:r.t/16,...r.camera})),{u:1,...camera1}];
  return d;
}

export async function carregarProducao(id) {
  if(id==='latam-loading') {
    const d = estadoPadrao();
    d.nome = 'LATAM — loading em voo';
    d.ambiente.chao.ligado = false; d.ambiente.grade = false;
    d.ambiente.fundo = 'transparente';
    d.ambiente.sol = {elev:45,azim:315,intensidade:3,cor:'#fff5ed'};
    d.ambiente.envIntensidade = 1.6;
    d.render.sombras = false; d.render.exposicao = 1.12;
    d.linha.duracao = 4; d.linha.fps = 25; d.linha.loop = true;
    const a = novoObjeto('aeronave','B77W','777 · voo contínuo',{nivel:'heroi'});
    d.objetos = [a];
    const rows = Array.from({length:101},(_,i)=>({t:i/25,phase:2*Math.PI*i/100}));
    trilha(d,'objeto.pos',a.id,rows,r=>[0,.45*Math.sin(r.phase),0]);
    trilha(d,'objeto.rot',a.id,rows,r=>[1.2*Math.sin(r.phase),0,.3*Math.sin(r.phase)]);
    trilha(d,'objeto.trem',a.id,[{t:0}],()=>false);
    const cam = pose([-92,46,105],[0,6,0],30);
    d.camera = {...clone(cam),orto:false};
    d.linha.planos = [plano('Voo · câmera de acompanhamento',0,4,cam)];
    return d;
  }
  if(id==='sdsc-reboque'||id==='sdsc-visita') return reboque(id==='sdsc-visita');
  if(id==='gru-decolagem') {
    const d = await fetchJson('../clipe_gru_777_v1.json');
    d.nome = 'GRU — decolagem 10L com entorno completo';
    d.objetos = d.objetos.filter(o=>o.tipo==='aeronave');
    d.objetos.push(...contexto('sbgr'));
    d.linha.loop = false; d.linha.planos = [];
    const cameras = d.linha.trilhas.filter(t=>t.canal.startsWith('camera.'));
    const sample = t => {
      const c = {pos:clone(d.camera.pos),alvo:clone(d.camera.alvo),fov:d.camera.fov};
      for(const tr of cameras) c[tr.canal.split('.')[1]] = amostrarTrilha(tr,t);
      return c;
    };
    const fim = d.linha.duracao;
    const p = plano('Decolagem · acompanhamento da rotação e subida',0,fim,sample(0),sample(fim));
    p.caminho = Array.from({length:160},(_,i)=>({u:i/159,...sample(fim*i/159)}));
    d.linha.planos = [p];
    d.linha.trilhas = d.linha.trilhas.filter(t=>!t.canal.startsWith('camera.'));
    d.ambiente.neblina.densidade = 1.2;
    d.render.pixelRatioMax = 1.5;
    return d;
  }
  if(id!=='gru-institucional') throw new Error('Produção desconhecida: '+id);
  const d = base('GRU — aeroporto, terminais e frota','sbgr',24);
  // Stand centres, apron datum and compass heading from SBGR_STANDS.
  for(const [slug,stand,x,y] of [['A320neo','G303',5,613],['A321neo','G310',203,639],
    ['A320ceo','G403',300,640],['B789','G502',600,670],['B77W','G510',846,727]]) {
    estacionado(d,slug,slug+' · '+stand,[x-1713.47,-4.39,-(y+403.26)],286.35);
  }
  const hero = d.objetos.at(-1);
  d.linha.planos = [
    plano('01 · Aeroporto na cidade',0,8,pose([-1350,700,-100],[0,0,-400],46),pose([-900,480,-150],[-50,0,-500],46)),
    plano('02 · Terminais e pátios',8,16,pose([-1250,140,-800],[-1150,0,-1100],43),pose([-1050,100,-810],[-1100,0,-1110],43)),
    plano('03 · Frota LATAM',16,24,pose([-92,26,84],[0,6,0],36),pose([-60,18,105],[0,6,0],36),hero.id),
  ];
  d.camera = {...clone(d.linha.planos[0].cameraInicio),orto:false};
  return d;
}
