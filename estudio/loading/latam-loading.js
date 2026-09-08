/** LATAM loading concept. Dependency-free; media URLs resolve beside this module. */
const media = new URL('./media/', import.meta.url);
const template = document.createElement('template');
template.innerHTML = `
<style>
:host{display:block;--loading-bg:#0c002f;--loading-accent:#ed1650;color:#fff;font-family:Arial,Helvetica,sans-serif;background:var(--loading-bg);border-radius:inherit;min-height:560px}
:host([hidden]){display:none}
*{box-sizing:border-box}
.scene{position:relative;isolation:isolate;min-height:inherit;height:100%;border-radius:inherit;overflow:hidden;display:flex;align-items:center;justify-content:center;background:var(--loading-bg)}
.brand{position:absolute;top:36px;left:40px;font-size:18px;font-weight:800;letter-spacing:.14em;display:flex;gap:10px;align-items:center}
.brand:before{content:'';width:4px;height:23px;border-radius:3px;background:var(--loading-accent);transform:skew(-20deg)}
.eyebrow{font-size:10px;letter-spacing:.24em;text-transform:uppercase;color:#b5a5ce;margin:0 0 14px}
.content{text-align:center;width:min(100%,800px);padding:76px 20px 56px;position:relative}
.visual{position:relative;width:min(100%,660px);aspect-ratio:16/9;margin:0 auto}
video,img{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;mask-image:radial-gradient(ellipse at center,#000 65%,transparent 100%)}
video{opacity:0}video.playing{opacity:1}
h1{font-size:clamp(26px,4.5vw,42px);font-weight:500;letter-spacing:-.035em;line-height:1.13;margin:0 0 24px}h1 span{display:block;color:#c3b4d7}
.track{width:160px;height:3px;background:#ffffff20;border-radius:4px;margin:0 auto 17px;overflow:hidden}
.bar{height:100%;width:38%;border-radius:4px;background:var(--loading-accent);animation:pass 1.6s infinite cubic-bezier(.4,0,.2,1)}
.track.determinate .bar{animation:none;width:var(--progress);transition:width .25s ease}
.status{font-size:13px;line-height:1.5;color:#c5b7d7;margin:0;min-height:20px}
.percent{font-variant-numeric:tabular-nums;margin-left:8px;color:#fff}
.retry{margin-top:16px;border:1px solid #a28daf;background:transparent;color:white;border-radius:24px;padding:10px 20px;font:inherit;cursor:pointer}
:host([paused]) .bar{animation-play-state:paused}
.retry:focus-visible{outline:3px solid #fff;outline-offset:4px}
.signature{position:absolute;bottom:28px;left:0;right:0;text-align:center;color:#8f7ca7;font-size:10px;letter-spacing:.2em;text-transform:uppercase}
:host([state="ready"]) .track .bar{animation:none;width:100%;background:#aaecd5}
:host([state="error"]) .track{visibility:hidden}
:host([size="compact"]) .scene{min-height:400px}
:host([size="compact"]) .brand{top:24px;left:24px;font-size:14px}
:host([size="compact"]) .content{padding:58px 20px 40px}
:host([size="compact"]) .visual{width:400px;max-width:100%;margin:0 auto}
:host([size="compact"]) h1{font-size:27px;margin-bottom:18px}
:host([size="compact"]) .eyebrow,:host([size="compact"]) .signature{display:none}
@keyframes pass{0%{transform:translateX(-105%)}100%{transform:translateX(265%)}}
@media(max-width:480px){:host{min-height:520px}.brand{top:26px;left:26px}.content{padding:70px 16px 60px}.visual{width:calc(100% + 32px);max-width:none;margin:4px -16px 20px}.signature{font-size:9px}.eyebrow{font-size:9px}h1{font-size:32px}}
@media(prefers-reduced-motion:reduce){video{display:none!important}.bar{animation:none;width:100%;opacity:.65}.track.determinate .bar{transition:none}}
</style>
<section class="scene" part="scene" aria-label="Carregamento LATAM">
 <div class="brand" aria-hidden="true">LATAM</div>
 <div class="content">
  <p class="eyebrow" aria-hidden="true">Uma nova viagem começa</p>
  <div class="visual" aria-hidden="true" inert><img alt="" width="800" height="450"><video muted loop playsinline preload="none" tabindex="-1"></video></div>
  <h1>Seu próximo destino<span>começa aqui.</span></h1>
  <div class="track" role="progressbar" aria-label="Carregando a aplicação"><div class="bar"></div></div>
  <p class="status" role="status" aria-live="polite" aria-atomic="true"><span class="message"></span><span class="percent" aria-hidden="true"></span></p>
  <button class="retry" hidden>Tentar novamente</button>
 </div>
 <div class="signature" aria-hidden="true">Pronto para ir mais longe</div>
</section>`;

export class LatamLoading extends HTMLElement {
  static observedAttributes = ['progress','message','state','paused'];
  constructor() {
    super(); this.attachShadow({mode:'open'}).append(template.content.cloneNode(true));
    this.video = this.shadowRoot.querySelector('video');
    this.video.muted = true;
    this.shadowRoot.querySelector('img').src = new URL('poster.png',media).href;
    this.motion = matchMedia('(prefers-reduced-motion: reduce)');
    this.syncPlayback = () => {
      const play = this.isConnected && this.visible && !document.hidden && !this.motion.matches && !this.hasAttribute('paused') && !['ready','error'].includes(this.getAttribute('state'));
      if(play) {
        if(!this.video.hasAttribute('src')) this.video.src = new URL('flight.mp4',media).href;
        this.video.play().catch(()=>this.video.classList.remove('playing'));
      } else {this.video.pause();}
    };
    this.video.addEventListener('playing',()=>this.video.classList.add('playing'));
    this.video.addEventListener('error',()=>this.video.classList.remove('playing'));
    this.shadowRoot.querySelector('.retry').addEventListener('click',()=>this.dispatchEvent(new CustomEvent('retry',{bubbles:true,composed:true})));
  }
  connectedCallback() {
    this.motion.addEventListener('change',this.syncPlayback);
    document.addEventListener('visibilitychange',this.syncPlayback);
    this.observer = new IntersectionObserver(entries=>{this.visible=entries[0].isIntersecting;this.syncPlayback();});
    this.observer.observe(this); this.update();
  }
  disconnectedCallback() {
    this.observer?.disconnect(); this.video.pause();
    this.motion.removeEventListener('change',this.syncPlayback);
    document.removeEventListener('visibilitychange',this.syncPlayback);
  }
  attributeChangedCallback(){this.update();}
  update() {
    const state=this.getAttribute('state') || 'loading';
    const raw=this.getAttribute('progress');
    const n=raw!==null && raw.trim()!=='' ? Number(raw) : NaN;
    const progress=Number.isFinite(n)?Math.max(0,Math.min(100,n)):null;
    const track=this.shadowRoot.querySelector('.track');
    track.classList.toggle('determinate',progress!==null);
    track.style.setProperty('--progress',`${progress??0}%`);
    if(progress!==null || state==='ready') track.setAttribute('aria-valuenow',state==='ready'?'100':String(progress));
    else track.removeAttribute('aria-valuenow');
    track.setAttribute('aria-valuemin','0');track.setAttribute('aria-valuemax','100');
    track.hidden=state==='error';
    track.setAttribute('aria-busy',String(state==='loading'));
    const message=this.getAttribute('message') || (state==='ready'?'Tudo pronto. Boa viagem!':state==='error'?'Não foi possível carregar. Vamos tentar de novo?':'Preparando sua experiência');
    const label=this.shadowRoot.querySelector('.message');
    if(label.textContent!==message) label.textContent=message;
    // Percent updates stay outside the live announcement; progressbar exposes the real value.
    this.shadowRoot.querySelector('.percent').textContent=progress!==null&&state==='loading'?`${Math.round(progress)}%`:'';
    this.shadowRoot.querySelector('.retry').hidden=state!=='error';
    this.syncPlayback();
  }
}
if(!customElements.get('latam-loading')) customElements.define('latam-loading',LatamLoading);
