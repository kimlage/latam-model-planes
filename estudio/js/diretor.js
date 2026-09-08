import { h, abrirModal, fecharModal } from './dialogos.js';
import { normalizarDocumento } from './documento.js';
import { cameraDoPlano, poseRelativa } from './planos.js';
import { avaliar } from './tempo.js';

const copia = x => JSON.parse(JSON.stringify(x));
const origemEm = (ctx, p, t) => avaliar(ctx.estado,t,id=>ctx.mundo.contextoVoo(id,ctx.estado))
  ?.objetos.get(p.seguir)?.pos || ctx.estado.objetos.find(o=>o.id===p.seguir)?.pos || [0,0,0];

export function gravarEnquadramento(ctx) {
  const e = ctx.dock.planoEditado;
  if (!e) return false;
  const p = ctx.estado.linha.planos.find(p=>p.id===e.id);
  if (!p) { ctx.dock.planoEditado = null; return false; }
  p[e.ponta] = poseRelativa(ctx.mundo.poseAtual(), origemEm(ctx,p,ctx.dock.t), p.seguir);
  ctx.registrar('Enquadramento: '+p.nome);
  ctx.dock.planoEditado = null;
  ctx.dock.cameraLivre = false;
  ctx.redesenhar();
  return true;
}

export function dlgDiretor(ctx) {
  ctx.dock.parar();
  const ps = copia(ctx.estado.linha.planos || []);
  const lista = h('div.diretor-lista');
  const erro = h('p.erro', {role:'alert'});
  const corpo = h('div.diretor', {},
    h('p.nota', {}, 'Monte cortes e movimentos de câmera. Os objetos continuam sua operação durante os cortes. “Enquadrar” abre a câmera livre; ajuste na viewport e pressione ◆ cam para gravar.'),
    lista, erro);
  const salvar = () => {
    try {
      const d = normalizarDocumento({...ctx.estado, linha:{...ctx.estado.linha,planos:ps}});
      ctx.estado.linha.planos = d.linha.planos;
      ctx.registrar('Montagem de câmeras'); ctx.redesenhar();
      return true;
    } catch(e) { erro.textContent = e.message; return false; }
  };
  const desenhar = () => {
    lista.replaceChildren();
    for (const p of ps) {
      const nome = h('input', {value:p.nome, 'aria-label':'Nome do plano', onchange:e=>p.nome=e.target.value});
      const inicio = h('input', {type:'number',min:0,max:ctx.estado.linha.duracao,step:1/ctx.estado.linha.fps,value:p.inicio,
        'aria-label':'Início do plano', onchange:e=>p.inicio=+e.target.value});
      const fim = h('input', {type:'number',min:0,max:ctx.estado.linha.duracao,step:1/ctx.estado.linha.fps,value:p.fim,
        'aria-label':'Fim do plano', onchange:e=>p.fim=+e.target.value});
      const curva = h('select', {'aria-label':'Movimento da câmera', onchange:e=>p.curva=e.target.value},
        ['linear','suave','fixa'].map(v=>h('option',{value:v,selected:p.curva===v},v)));
      const seguir = h('select', {'aria-label':'Seguir objeto'},
        h('option',{value:''},'Câmera no cenário'),
        ctx.estado.objetos.filter(o=>o.tipo==='aeronave'||o.tipo==='prop').map(o=>h('option',{value:o.id},'Seguir '+o.nome)));
      seguir.value = p.seguir || '';
      seguir.onchange = () => {
        // Change reference frame without jumping the composed endpoint poses.
        const poses = ['cameraInicio','cameraFim'].map((k,i)=>cameraDoPlano({...p,curva:'linear'}, i?p.fim:p.inicio, origemEm(ctx,p,i?p.fim:p.inicio)));
        p.seguir = seguir.value || null;
        ['cameraInicio','cameraFim'].forEach((k,i)=>p[k]=poseRelativa(poses[i],origemEm(ctx,p,i?p.fim:p.inicio),p.seguir));
      };
      const enquadrar = ponta => {
        if (!salvar()) return;
        const t = ponta==='cameraInicio' ? p.inicio : p.fim;
        ctx.dock.cameraLivre = true;
        ctx.dock.irPara(t);
        ctx.mundo.aplicarPose({...cameraDoPlano({...p,curva:'linear'},t,origemEm(ctx,p,t)),orto:false});
        ctx.dock.planoEditado = {id:p.id,ponta};
        ctx.dock.desenhar(); fecharModal();
      };
      const lente = ponta => h('label',{},ponta==='cameraInicio'?'FOV inicial':'FOV final',
        h('input',{type:'number',min:10,max:120,step:1,value:p[ponta].fov,
          onchange:e=>p[ponta].fov=+e.target.value}));
      lista.append(h('article.plano-editor',{}, nome,
        h('div.plano-campos',{},h('label',{},'Início (s)',inicio),h('label',{},'Fim (s)',fim),curva),
        seguir,h('div.plano-campos',{},lente('cameraInicio'),lente('cameraFim')),
        h('div.linha-botoes',{},
          h('button',{onclick:()=>enquadrar('cameraInicio')},'Enquadrar início'),
          h('button',{onclick:()=>enquadrar('cameraFim')},'Enquadrar fim'),
          h('button',{onclick:()=>{ps.splice(ps.indexOf(p),1);desenhar();}},'Remover plano'))));
    }
  };
  corpo.append(h('div.linha-botoes',{},
    h('button',{onclick:()=>{
      const inicio = ps.length ? Math.max(...ps.map(p=>p.fim)) : 0;
      if (inicio >= ctx.estado.linha.duracao) { erro.textContent='Aumente a duração da sequência ou encurte o último plano para abrir espaço.';return; }
      const pose = ctx.mundo.poseAtual();
      ps.push({id:crypto.randomUUID(),nome:'Plano '+(ps.length+1),inicio,
        fim:Math.min(inicio+4,ctx.estado.linha.duracao),curva:'linear',seguir:null,
        cameraInicio:copia(pose),cameraFim:copia(pose)});desenhar();
    }},'+ Plano'),
    h('button.primaria',{onclick:()=>{if(salvar()){ctx.dock.cameraLivre=false;ctx.dock.planoEditado=null;ctx.redesenhar();fecharModal();}}},'Salvar montagem')));
  desenhar(); abrirModal('Direção de câmeras', corpo);
}
