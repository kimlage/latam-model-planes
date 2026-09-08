import './latam-cinema.js';
import {AEROPORTOS,AERONAVES,SITUACOES,situacoes,aeronaves,lerParametros,parametros,renderPronto} from './catalogo.js';
const $=id=>document.getElementById(id),cinema=$('cinema');
let c;try{c=lerParametros()}catch{c={aeroporto:'sdsc',aeronave:'B789',situacao:'reboque'}}
function options(el,keys,labels,value){el.replaceChildren(...keys.map(key=>new Option(labels[key],key,false,key===value)))}
function apply(){
 options($('airport'),Object.keys(AEROPORTOS),AEROPORTOS,c.aeroporto);options($('situation'),situacoes(c.aeroporto),SITUACOES,c.situacao);options($('aircraft'),aeronaves(c.aeroporto,c.situacao),AERONAVES,c.aeronave);
 cinema.configure(c);history.replaceState(null,'','?'+parametros(c));$('edit').href='../?loading=cinema&'+parametros(c);
 $('details').textContent=c.situacao==='aproximacao'?'A câmera se aproxima da aeronave em voo e se afasta para revelar a base. Todo o percurso é externo.':c.situacao==='sobrevoo'?'Aeronave em voo, curva suave e câmera acompanhando a passagem sobre o aeroporto.':c.situacao==='manutencao'?'Interior do hangar, aeronave estacionada e câmera em movimento pela área de manutenção.':c.situacao==='reboque'?'787, trator e barra em operação coordenada. Passagem pelo preto ao reiniciar.':c.situacao==='patio'?'Aeronave estacionada, aproximação de câmera e aeroporto ao fundo. Passagem pelo preto ao reiniciar.':'Corrida, rotação e subida, com câmera acompanhando a aeronave. Passagem pelo preto ao reiniciar.';
 cinema.dataset.mode=renderPronto(c)?'video':'3d';
}
$('airport').onchange=()=>{c.aeroporto=$('airport').value;if(!situacoes(c.aeroporto).includes(c.situacao))c.situacao=situacoes(c.aeroporto)[0];if(!aeronaves(c.aeroporto,c.situacao).includes(c.aeronave))c.aeronave=aeronaves(c.aeroporto,c.situacao)[0];apply()};
$('situation').onchange=()=>{c.situacao=$('situation').value;if(!aeronaves(c.aeroporto,c.situacao).includes(c.aeronave))c.aeronave=aeronaves(c.aeroporto,c.situacao)[0];apply()};
$('aircraft').onchange=()=>{c.aeronave=$('aircraft').value;apply()};
$('pause').onclick=()=>{const p=cinema.toggleAttribute('paused');$('pause').textContent=p?'Retomar':'Pausar';$('pause').setAttribute('aria-pressed',String(p))};
$('restart').onclick=()=>cinema.restart();$('full').onclick=()=>{document.body.classList.add('full');$('exit').focus()};
function exit(){document.body.classList.remove('full');$('full').focus()}
$('exit').onclick=exit;addEventListener('keydown',e=>{if(e.key==='Escape')exit()});apply();
