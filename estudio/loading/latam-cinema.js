import {validar,parametros,renderPronto,AEROPORTOS,AERONAVES,SITUACOES} from './catalogo.js';
const mediaRevision='20260905-depth-wing-2';
const base=new URL('./',import.meta.url);
const template=document.createElement('template');
template.innerHTML=`<style>
:host{display:block;position:relative;width:100%;aspect-ratio:16/9;background:#080a0f;color:white;overflow:hidden;font-family:Arial,Helvetica,sans-serif}*{box-sizing:border-box}.film,.media,.veil{position:absolute;inset:0}.media video,.media img,.media iframe{width:100%;height:100%;object-fit:contain;border:0;display:block}.media img{position:absolute;inset:0}.media video{position:absolute;inset:0;opacity:0}.media video.playing{opacity:1}.veil{background:#080a0f;pointer-events:none;opacity:0}.shade{position:absolute;inset:0;pointer-events:none;background:linear-gradient(#0006,transparent 24%,transparent 62%,#030612b8)}.brand{position:absolute;top:6%;left:5%;width:clamp(92px,12%,144px);pointer-events:none}.brand img{display:block;width:100%;height:auto;filter:drop-shadow(0 1px 3px #0005)}.caption{position:absolute;left:5%;bottom:8%;right:5%;display:flex;justify-content:space-between;gap:20px;align-items:end}.place{font-size:clamp(10px,1.1vw,14px);letter-spacing:.17em;text-transform:uppercase;color:#e4e7f0;margin:0 0 9px}h2{font-size:clamp(16px,2.4vw,32px);font-weight:400;letter-spacing:-.02em;margin:0}.model{margin:8px 0 0;color:#d6dbea;font-size:clamp(10px,1.1vw,14px)}.status{min-width:130px;text-align:right;font-size:clamp(10px,1vw,13px);color:#e5e8f0}.track{height:2px;width:140px;max-width:100%;margin:12px 0 0 auto;background:#ffffff40;overflow:hidden}.bar{height:100%;width:35%;background:#ff3265;animation:pass 1.5s linear infinite}.track.real .bar{animation:none;width:var(--p)}:host([paused]) .bar{animation-play-state:paused}.notice{position:absolute;inset:0;display:grid;place-content:center;text-align:center;background:#080a0f;color:#c9cedd;padding:20px;font-size:13px}.notice[hidden]{display:none}button{background:#fff;color:#111;border:0;border-radius:4px;padding:10px;margin-top:12px;cursor:pointer}@keyframes pass{from{transform:translateX(-100%)}to{transform:translateX(290%)}}@media(max-width:600px){.caption{bottom:7%;gap:8px}.model{margin-top:5px}.place{margin-bottom:5px;letter-spacing:.08em}.status{min-width:90px;max-width:115px}.track{width:90px}.brand{top:5%}}@media(prefers-reduced-motion:reduce){.bar{animation:none;width:100%;opacity:.6}}
</style><div class="film"><div class="media"></div><div class="veil"></div><div class="shade"></div></div><div class="brand"><img src="${new URL('media/latam-logo-light.svg',base).href}" alt="LATAM" width="2670" height="630"></div><div class="caption"><div><p class="place"></p><h2></h2><p class="model"></p></div><div class="status"><span role="status" class="message" aria-live="polite">Carregando sua viagem</span><div class="track" role="progressbar" aria-label="Carregamento da aplicação"><div class="bar"></div></div></div></div><div class="notice" role="status" hidden></div>`;
export class LatamCinema extends HTMLElement{
 static observedAttributes=['airport','aircraft','situation','paused','progress','message','state'];
 constructor(){super();this.attachShadow({mode:'open'}).append(template.content.cloneNode(true));this.motion=matchMedia('(prefers-reduced-motion:reduce)');this.sync=()=>this.playback();this.receive=e=>{
  if(e.origin!==location.origin||e.source!==this.iframe?.contentWindow)return;
  if(e.data.type==='cinema-ready'){this.notice('');this.playback();this.dispatchEvent(new CustomEvent('scene-ready',{detail:{mode:'3d',...this.config}}));}
  if(e.data.type==='cinema-error')this.notice(e.data.message||'Falha ao abrir cenário.',true);
 };}
 q(s){return this.shadowRoot.querySelector(s)}
 connectedCallback(){this.visible=true;this.motion.addEventListener('change',this.sync);document.addEventListener('visibilitychange',this.sync);addEventListener('message',this.receive);this.observer=new IntersectionObserver(e=>{this.visible=e[0].isIntersecting;this.playback()});this.observer.observe(this);this.queue();}
 disconnectedCallback(){this.observer?.disconnect();this.motion.removeEventListener('change',this.sync);document.removeEventListener('visibilitychange',this.sync);removeEventListener('message',this.receive);this.video?.pause();this.iframe?.remove();this.key=null;}
 attributeChangedCallback(){this.queue()}
 queue(){if(this.queued)return;this.queued=true;queueMicrotask(()=>{this.queued=false;if(this.isConnected)this.update()})}
 configure(c){validar(c);this.setAttribute('airport',c.aeroporto);this.setAttribute('aircraft',c.aeronave);this.setAttribute('situation',c.situacao)}
 update(){try{
  const c=validar({aeroporto:this.getAttribute('airport')||'sdsc',aeronave:this.getAttribute('aircraft')||'B789',situacao:this.getAttribute('situation')||'reboque'}),key=parametros(c).toString();
  if(key!==this.key){this.key=key;this.config=c;this.load()}
  const raw=this.getAttribute('progress'),n=raw!==null&&raw.trim()!==''?Number(raw):NaN,p=Number.isFinite(n)?Math.max(0,Math.min(100,n)):null;
  const state=this.getAttribute('state')||'loading',track=this.q('.track');track.classList.toggle('real',p!==null||state==='ready');track.style.setProperty('--p',`${state==='ready'?100:p??0}%`);
  if(p!==null||state==='ready')track.setAttribute('aria-valuenow',String(state==='ready'?100:p));else track.removeAttribute('aria-valuenow');
  track.setAttribute('aria-valuemin','0');track.setAttribute('aria-valuemax','100');track.hidden=state==='error';
  const text=this.getAttribute('message')||(state==='ready'?'Sua viagem está pronta':state==='error'?'Não foi possível carregar':'Carregando sua viagem');if(this.q('.message').textContent!==text)this.q('.message').textContent=text;
  this.playback();
 }catch(e){this.notice(e.message,true)}}
 notice(text,retry=false){const el=this.q('.notice');el.replaceChildren(document.createTextNode(text));el.hidden=!text;if(retry){const b=document.createElement('button');b.textContent='Tentar novamente';b.onclick=()=>this.load();el.append(b)}}
 load(){
  this.video?.pause();this.video=null;this.iframe=null;this.q('.media').replaceChildren();this.q('.veil').style.opacity=0;
  const c=this.config;this.q('.place').textContent=AEROPORTOS[c.aeroporto];this.q('h2').textContent={sobrevoo:'A base sob nossas asas',aproximacao:'Uma nova perspectiva',decolagem:'A próxima partida',patio:'Entre voos',reboque:'De volta ao hangar',manutencao:'Pronta para o próximo voo'}[c.situacao];this.q('.model').textContent=AERONAVES[c.aeronave];
  const render=renderPronto(c);this.mode=render?'video':'3d';this.notice(render?'':'Preparando o cenário 3D…');
  if(render){
   const img=document.createElement('img');img.alt='';img.src=new URL(`media/cinema/${render}-poster.png?v=${mediaRevision}`,base);this.q('.media').append(img);
   const v=document.createElement('video');this.video=v;v.muted=true;v.loop=true;v.playsInline=true;v.preload='none';v.setAttribute('aria-hidden','true');v.inert=true;this.src=new URL(`media/cinema/${render}.mp4?v=${mediaRevision}`,base).href;this.q('.media').append(v);
   v.addEventListener('playing',()=>v.classList.add('playing'));v.addEventListener('error',()=>{if(v!==this.video||!this.isConnected)return;v.classList.remove('playing');this.notice('Não foi possível carregar o filme.',true)});
   v.addEventListener('loadeddata',()=>{if(v!==this.video||!this.isConnected)return;this.dispatchEvent(new CustomEvent('scene-ready',{detail:{mode:'video',...c}}));this.playback()});
   // The exported films already contain their editorial fade.
  }else{const iframe=document.createElement('iframe');this.iframe=iframe;iframe.title=`Cena: ${AEROPORTOS[c.aeroporto]} — ${AERONAVES[c.aeronave]}`;iframe.src=new URL('runtime.html?'+this.key,base).href;this.q('.media').append(iframe)}
  this.playback();
 }
 playback(){const paused=this.hasAttribute('paused')||!this.visible||document.hidden||this.motion.matches||['ready','error'].includes(this.getAttribute('state'));
  if(this.video){if(paused){this.video.pause();if(this.motion.matches){this.video.classList.remove('playing');this.q('.veil').style.opacity=0}}else{if(!this.video.src)this.video.src=this.src;this.video.play().catch(()=>{})}}
  this.iframe?.contentWindow?.postMessage({type:'cinema-pause',paused},location.origin);
 }
 restart(){if(this.video)this.video.currentTime=0;this.iframe?.contentWindow?.postMessage({type:'cinema-restart'},location.origin)}
}
if(!customElements.get('latam-cinema'))customElements.define('latam-cinema',LatamCinema);
