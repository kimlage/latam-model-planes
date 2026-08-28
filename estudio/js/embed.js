/* embed.js — the runtime an exported embed loads.
 *
 * The whole point of this file is that an embed is NOT a second renderer with
 * its own idea of what a scene looks like. It builds the same Mundo the studio
 * builds, from the same document, and simply never constructs the editor. If a
 * scene looks right in the studio it looks right in the embed, or one of them
 * is broken and both are wrong in the same place.
 *
 * The timeline arrives the same way and for the same reason: `avaliar()` is the
 * studio's evaluator, `mundo.aplicarLinha()` is the studio's projection, and
 * this file adds a clock and four buttons. An embed that played the clip
 * through its own interpolator would eventually disagree with the studio about
 * a curve, and nobody would know which one was right.
 *
 * The generated HTML supplies its own asset table (slug → GLB URL relative to
 * the embed page), so the embed does not need export/manifest.json.
 */

import { Mundo } from './mundo.js';
import { registrarAssets } from './frota.js';
import { avaliar, temAnimacao, quadros } from './tempo.js';

/**
 * @param {HTMLElement} el   container; it is sized by CSS, the canvas fills it
 * @param {object} doc       a scene document (schema latam-estudio/1) + .assets
 * @param {object} opc       { autoGirar, velocidadeGiro, zoom, pan, tocar, transporte }
 */
export async function montar (el, doc, opc = {}) {
  if (!doc || doc.schema !== 'latam-estudio/1') {
    throw new Error('not a latam-estudio/1 scene document');
  }
  registrarAssets(doc.assets || {});

  const m = new Mundo(el);
  m.aplicarRender(doc.render);
  m.aplicarAmbiente(doc.ambiente);
  await m.sincronizar(doc);
  m.aplicarAmbiente(doc.ambiente);          // again: the shadow camera needs the real scene radius

  m.aplicarPose({ pos: doc.camera.pos, alvo: doc.camera.alvo, fov: doc.camera.fov });
  if (doc.camera.orto) m.usarOrto(true);

  const c = m.controles;
  c.enableZoom = opc.zoom !== false;
  c.enablePan = opc.pan !== false;
  c.autoRotate = !!opc.autoGirar;
  c.autoRotateSpeed = opc.velocidadeGiro ?? 0.4;
  c.minDistance = 2;
  c.maxDistance = 12000;

  /* ------------------------------------------------------------ timeline */
  const linha = doc.linha;
  const anima = temAnimacao(linha);
  const ctxVoo = id => m.contextoVoo(id, doc);
  /* `t` is snapped to the frame grid; `tBruto` is the clock it comes from. The
     two must not be the same variable — see tempoui.js §avancar for the bug
     that costs you (a 120 Hz display advancing a 20 fps timeline by 0.17 of a
     frame, rounding back, and never moving). */
  let t = 0, tBruto = 0, tocando = anima && opc.tocar !== false;
  let transporte = null;

  const aplicar = () => {
    if (!anima) return null;
    const ov = avaliar(doc, t, ctxVoo);
    m.aplicarTransformacoes(doc);
    m.aplicarLinha(doc, ov);
    if (transporte) transporte.sincronizar(t, tocando);
    return ov;
  };

  if (anima && opc.transporte !== false) transporte = fazerTransporte(el, linha, {
    aoTocar: v => { tocando = v; aplicar(); },
    aoTempo: v => { t = Math.round(v * linha.fps) / linha.fps; tBruto = t; aplicar(); },
    tocando: () => tocando,
  });

  aplicar();

  let anterior = performance.now();
  m.iniciarLoop(() => {
    const agora = performance.now();
    const dt = Math.min(0.25, (agora - anterior) / 1000);
    anterior = agora;
    if (anima && tocando) {
      tBruto += dt;
      if (tBruto >= linha.duracao) {
        tBruto = linha.loop === false ? linha.duracao : tBruto % linha.duracao;
      }
      /* Snapped to the frame grid, so the embed shows the same frames the GIF
         contains rather than in-between poses that were never exported. */
      t = Math.min(linha.duracao, Math.round(tBruto * linha.fps) / linha.fps);
    }
    const ov = aplicar();
    /* While the camera track is running the controls do not get a turn, or
       OrbitControls.update() overwrites the pose the track just set. Pause the
       clip and the viewer gets the scene back, from wherever the camera is. */
    if (!(ov && ov.camera && tocando)) c.update();
    m.render();
  });

  /* Same reason index.html exposes window.__estudio: this is how an embed gets
     driven and checked from the console when it does not look right. */
  window.__embed = m;
  window.__embed.linha = { get t () { return t; }, set t (v) { t = tBruto = v; aplicar(); },
                           get tocando () { return tocando; },
                           set tocando (v) { tocando = v; },
                           quadros: anima ? quadros(linha) : 0 };
  return m;
}

/* A transport bar, built here rather than written into the generated HTML, so
 * every embed gets the same one and a fix reaches all of them. */
function fazerTransporte (el, linha, cb) {
  const barra = document.createElement('div');
  barra.id = 'transporte';
  barra.innerHTML =
    `<button data-a="tocar" title="Play / pause">⏸</button>`
    + `<button data-a="inicio" title="Back to the start">⏮</button>`
    + `<input type="range" min="0" max="${quadros(linha)}" step="1" value="0">`
    + `<span></span>`;
  const st = document.createElement('style');
  st.textContent =
    `#transporte{position:fixed;left:10px;right:10px;bottom:34px;display:flex;gap:8px;
      align-items:center;background:rgba(13,15,20,.72);border:1px solid #262a36;
      border-radius:7px;padding:5px 8px;backdrop-filter:blur(6px);
      font:11px/1.4 -apple-system,"Segoe UI",Roboto,sans-serif;color:#e6e7ea}
     #transporte button{background:#171b25;color:#e6e7ea;border:1px solid #262a36;
      border-radius:5px;padding:2px 8px;cursor:pointer;font:inherit}
     #transporte input{flex:1;accent-color:#8fa6ff}
     #transporte span{font-variant-numeric:tabular-nums;color:#9aa0ae;min-width:96px;
      text-align:right}`;
  document.head.append(st);
  el.parentElement.append(barra);

  const bTocar = barra.querySelector('[data-a="tocar"]');
  const faixa = barra.querySelector('input');
  const leitura = barra.querySelector('span');
  bTocar.onclick = () => cb.aoTocar(!cb.tocando());
  barra.querySelector('[data-a="inicio"]').onclick = () => cb.aoTempo(0);
  faixa.oninput = () => { cb.aoTocar(false); cb.aoTempo(+faixa.value / linha.fps); };

  return {
    sincronizar (t, tocando) {
      bTocar.textContent = tocando ? '⏸' : '▶';
      if (document.activeElement !== faixa) faixa.value = Math.round(t * linha.fps);
      leitura.textContent = `${t.toFixed(2)} / ${linha.duracao.toFixed(2)} s`;
    },
  };
}
