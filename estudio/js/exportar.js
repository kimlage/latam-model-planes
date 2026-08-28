/* exportar.js — the four ways out of the studio.
 *
 *   1. animated GIF   — client-side, gifenc, 25 fps by law (see below)
 *   2. navigable embed — an <iframe>-able HTML file that reuses js/embed.js
 *   3. scene JSON      — round-trips a composition
 *   4. PNG still       — free once (1) exists
 *
 * THE GIF LAW (this repository's, and it is arithmetic, not taste):
 * a GIF frame delay is an integer number of CENTISECONDS. 25 fps is 4 cs
 * exactly. 24 fps is 4.1666… cs, so every encoder alternates 4 and 5 and the
 * motion stutters on a 12-frame cycle. The fps menu below therefore only
 * offers rates that divide 100 evenly, and shows the delay it will write.
 * gifenc rounds delay_ms/10, so we hand it exact multiples of 10 ms.
 *
 * Dithering: gifenc does not dither at all — it maps each pixel to the nearest
 * palette entry. That matches the project's "no dithering by default" rule; it
 * also means the colour-count control is the only quality/size knob there is.
 */

import * as THREE from 'three';
import { GIFEncoder, quantize, applyPalette } from 'gifenc';
import { acharAsset, LICENCAS, licencasDe } from './frota.js';

/* fps values whose frame delay is a whole number of centiseconds. */
export const FPS_LEGAIS = [
  { fps: 25, cs: 4, rot: '25 fps — 4 cs (the project default)' },
  { fps: 20, cs: 5, rot: '20 fps — 5 cs' },
  { fps: 12.5, cs: 8, rot: '12.5 fps — 8 cs' },
  { fps: 10, cs: 10, rot: '10 fps — 10 cs' },
  { fps: 5, cs: 20, rot: '5 fps — 20 cs' },
];

/* Bytes per pixel per frame, by palette size. MEASURED on 640×360 12-frame
 * turntables of two scenes, at 2× supersampling because that is the default
 * (see README §GIF export):
 *
 *   colours                32     64    128    256
 *   "Single hero"        .035   .050   .063   .082   ← smooth sky, one aircraft
 *   "Line-up" (×5)       .111   .169   .196   .212   ← textured concrete, five
 *
 * A factor of 3 between two perfectly ordinary scenes: LZW on a 5 m sky
 * gradient and LZW on tiled concrete are not the same problem. The constants
 * below are the geometric mean of the two columns, so the estimate is honest to
 * about a factor of 2 either way. It exists to make resolution-versus-colours a
 * visible trade, not to be precise — the dialog prints the REAL size the moment
 * the encode finishes, and that number is a measurement. */
const BPP = { 32: 0.062, 64: 0.092, 128: 0.111, 256: 0.132 };

export function estimarGif ({ quadros, larg, alt, cores }) {
  const bpp = BPP[cores] ?? 0.29;
  return Math.round(quadros * larg * alt * bpp) + 800;
}

export const formatarBytes = n =>
  n < 1024 ? `${n} B`
  : n < 1048576 ? `${(n / 1024).toFixed(0)} kB`
  : `${(n / 1048576).toFixed(2)} MB`;

/* ------------------------------------------------------- frame capture --- */

/** Render one frame at an exact pixel size and hand back an RGBA buffer.
 *  `ss` is the supersample factor: render big, downsample with drawImage. */
export class Capturador {
  constructor (mundo) {
    this.mundo = mundo;
    this.lona = document.createElement('canvas');
    this.ctx = this.lona.getContext('2d', { willReadFrequently: true });
    this.salvo = null;
  }

  iniciar (larg, alt, ss = 1) {
    const m = this.mundo;
    /* The interactive loop must stop: it calls OrbitControls.update(), which
       would overwrite the camera the motion function just set — the classic
       "the GIF is 60 frames of the same picture" bug. */
    m.pausar();
    this.salvo = {
      w: m.largura, h: m.altura,
      pr: m.renderer.getPixelRatio(),
      aspect: m.camP.aspect,
    };
    this.larg = larg; this.alt = alt; this.ss = ss;
    this.lona.width = larg; this.lona.height = alt;
    m.renderer.setPixelRatio(1);
    m.renderer.setSize(larg * ss, alt * ss, false);
    m.camP.aspect = larg / alt;
    m.camP.updateProjectionMatrix();
    m.atualizarOrto();
  }

  /** One frame. Returns { data: Uint8ClampedArray RGBA, larg, alt }. */
  quadro (fundoOpaco = null) {
    const m = this.mundo;
    m.render();
    this.ctx.clearRect(0, 0, this.larg, this.alt);
    if (fundoOpaco) {                       // GIF has no alpha channel worth using
      this.ctx.fillStyle = fundoOpaco;
      this.ctx.fillRect(0, 0, this.larg, this.alt);
    }
    // Same task as the render call, and preserveDrawingBuffer is on: this read
    // is safe on every driver we have seen.
    this.ctx.drawImage(m.renderer.domElement, 0, 0, this.larg, this.alt);
    return this.ctx.getImageData(0, 0, this.larg, this.alt);
  }

  blobPNG () { return new Promise(r => this.lona.toBlob(r, 'image/png')); }

  terminar () {
    const m = this.mundo, s = this.salvo;
    if (!s) return;
    m.renderer.setPixelRatio(s.pr);
    m.renderer.setSize(s.w, s.h, false);
    m.camP.aspect = s.aspect;
    m.camP.updateProjectionMatrix();
    m.atualizarOrto();
    m.redimensionar();
    m.retomar();
    this.salvo = null;
  }
}

/* ------------------------------------------------------------- motion --- */
/* A motion is a function of normalised time t ∈ [0,1). It mutates the world and
 * is always bracketed by salvarPose/restaurarPose so an export leaves the scene
 * exactly as the user left it. */

const suave = t => t * t * (3 - 2 * t);           // smoothstep, for camera paths

export function construirMovimento (mundo, estado, cfg, selId) {
  const alvo0 = mundo.controles.target.clone();
  const pos0 = mundo.camP.position.clone();
  const fov0 = mundo.camP.fov;
  const obj = selId ? mundo.objetos.get(selId) : null;
  const objPos0 = obj ? obj.position.clone() : null;
  const objRot0 = obj ? obj.rotation.clone() : null;

  const restaurar = () => {
    mundo.camP.position.copy(pos0);
    mundo.controles.target.copy(alvo0);
    mundo.camP.lookAt(alvo0);
    mundo.camP.fov = fov0;
    mundo.camP.updateProjectionMatrix();
    if (obj) { obj.position.copy(objPos0); obj.rotation.copy(objRot0); obj.updateMatrixWorld(true); }
    mundo.controles.update();
  };

  let passo;
  switch (cfg.modo) {
    case 'turntable-cena': {
      // Orbit the current target at the current radius and height.
      const rel = pos0.clone().sub(alvo0);
      const raio = Math.hypot(rel.x, rel.z), y = rel.y;
      const a0 = Math.atan2(rel.z, rel.x);
      const sentido = cfg.sentido === 'anti' ? -1 : 1;
      passo = t => {
        const a = a0 + sentido * t * Math.PI * 2;
        mundo.camP.position.set(alvo0.x + raio * Math.cos(a), alvo0.y + y, alvo0.z + raio * Math.sin(a));
        mundo.camP.lookAt(alvo0);
        mundo.controles.target.copy(alvo0);
      };
      break;
    }
    case 'turntable-objeto': {
      if (!obj) throw new Error('turntable of a selected object needs a selection');
      const sentido = cfg.sentido === 'anti' ? -1 : 1;
      passo = t => { obj.rotation.y = objRot0.y + sentido * t * Math.PI * 2; obj.updateMatrixWorld(true); };
      break;
    }
    case 'caminho-camera': {
      const A = estado.poses.A, B = estado.poses.B;
      if (!A || !B) throw new Error('camera path needs both pose A and pose B stored');
      const pA = new THREE.Vector3().fromArray(A.pos), pB = new THREE.Vector3().fromArray(B.pos);
      const tA = new THREE.Vector3().fromArray(A.alvo), tB = new THREE.Vector3().fromArray(B.alvo);
      passo = t => {
        // Ping-pong so the clip loops without a jump cut back to A.
        const u = cfg.pingpong ? (t < 0.5 ? t * 2 : 2 - t * 2) : t;
        const k = suave(u);
        mundo.camP.position.lerpVectors(pA, pB, k);
        const al = new THREE.Vector3().lerpVectors(tA, tB, k);
        mundo.camP.lookAt(al);
        mundo.controles.target.copy(al);
        if (A.fov && B.fov) { mundo.camP.fov = A.fov + (B.fov - A.fov) * k; mundo.camP.updateProjectionMatrix(); }
      };
      break;
    }
    case 'objeto-movel': {
      if (!obj) throw new Error('a moving object needs a selection');
      const d = cfg.distancia || 0, sobe = cfg.subida || 0;
      const dir = new THREE.Vector3();
      if (cfg.direcao === 'nariz') dir.set(-1, 0, 0).applyQuaternion(obj.quaternion);   // nose is local −X
      else if (cfg.direcao === 'x') dir.set(1, 0, 0);
      else dir.set(0, 0, 1);
      passo = t => {
        obj.position.copy(objPos0).addScaledVector(dir, d * t);
        obj.position.y = objPos0.y + sobe * t * t;      // quadratic: reads as a climb
        obj.updateMatrixWorld(true);
      };
      break;
    }
    default:
      passo = () => {};
  }
  return { passo, restaurar };
}

/* ---------------------------------------------------------------- GIF --- */

/**
 * Encode the scene to an animated GIF.
 * @param cfg { modo, quadros, fps, larg, alt, cores, loop, ss, matte, sentido, ... }
 * @param aoProgresso (feito, total, fase)
 */
export async function exportarGif (mundo, estado, cfg, selId, aoProgresso = () => {}) {
  const fps = FPS_LEGAIS.find(f => f.fps === cfg.fps) || FPS_LEGAIS[0];
  const atrasoMs = fps.cs * 10;                       // exact multiple of 10 ms
  const N = Math.max(2, Math.round(cfg.quadros));
  const mov = construirMovimento(mundo, estado, cfg, selId);
  const cap = new Capturador(mundo);
  const matte = estado.ambiente.fundo === 'transparente' ? (cfg.matte || '#0d0f14') : null;

  cap.iniciar(cfg.larg, cfg.alt, cfg.ss || 1);
  try {
    /* Pass 1 — a global palette from four sampled frames. A per-frame palette
       looks marginally better on a single frame and flickers across a loop;
       one table for the whole clip is both smaller and steadier. */
    aoProgresso(0, N, 'sampling colours');
    const amostras = [];
    for (const t of [0, 0.25, 0.5, 0.75]) {
      mov.passo(t);
      const q = cap.quadro(matte);
      // Every 7th pixel: enough colour statistics, a fraction of the work.
      const passoAm = 7 * 4;
      for (let i = 0; i < q.data.length; i += passoAm) amostras.push(q.data[i], q.data[i + 1], q.data[i + 2], 255);
    }
    const paleta = quantize(new Uint8Array(amostras), cfg.cores, { format: 'rgb565' });

    /* Pass 2 — render, index against the palette, write. */
    const gif = GIFEncoder();
    for (let i = 0; i < N; i++) {
      mov.passo(i / N);
      const q = cap.quadro(matte);
      const idx = applyPalette(q.data, paleta, 'rgb565');
      gif.writeFrame(idx, cfg.larg, cfg.alt, {
        palette: i === 0 ? paleta : undefined,
        delay: atrasoMs,
        repeat: cfg.loop ? 0 : -1,          // 0 = forever, −1 = play once
        first: i === 0,
      });
      if (i % 2 === 0) { aoProgresso(i, N, 'encoding'); await new Promise(r => setTimeout(r)); }
    }
    gif.finish();
    const bytes = gif.bytes();
    aoProgresso(N, N, 'done');
    return { blob: new Blob([bytes], { type: 'image/gif' }), bytes: bytes.length, quadros: N, cs: fps.cs };
  } finally {
    cap.terminar();
    mov.restaurar();
    mundo.render();
  }
}

/* ---------------------------------------------------------------- PNG --- */

export async function exportarPng (mundo, cfg) {
  const cap = new Capturador(mundo);
  cap.iniciar(cfg.larg, cfg.alt, cfg.ss || 2);
  try {
    cap.quadro(cfg.matte || null);
    const blob = await cap.blobPNG();
    return { blob, bytes: blob.size };
  } finally {
    cap.terminar();
    mundo.render();
  }
}

/* --------------------------------------------------------------- JSON --- */

/* ------------------------------------------------------------- licence ---
 * A scene's licence is the UNION of the licences of the assets actually in it,
 * and it is computed, never assumed. A scene of nothing but aircraft is CC BY
 * 4.0. Put one GRU hangar in it and it also carries ODbL 1.0 with share-alike,
 * because the airport geometry is an OpenStreetMap derivative — which is
 * allowed, and is exactly why the attribution has to travel. */

export const LICENCA_ESTUDIO = {
  nome: 'CC BY 4.0 (authored props)',
  url: 'https://creativecommons.org/licenses/by/4.0/',
  atribuicao: 'LATAM fleet 3D replicas — Kim Lage — CC BY 4.0',
  share_alike: false,
  nota: 'Grounds, sky and massing authored in estudio/js/props.js. '
      + 'No survey data of any real airport.',
};

export const resolverLicenca = id =>
  (id === 'estudio' ? LICENCA_ESTUDIO : LICENCAS[id]) || null;

/** [{ id, nome, url, atribuicao, share_alike, nota }] for the open scene. */
export function licencasDaCena (estado) {
  const vistos = new Set();
  const out = [];
  for (const id of licencasDe(estado.objetos)) {
    const l = resolverLicenca(id);
    if (!l || vistos.has(id)) continue;
    vistos.add(id);
    out.push({ id, ...l });
  }
  if (!out.length) out.push({ id: 'cc-by-4.0', ...resolverLicenca('cc-by-4.0') });
  return out;
}

/** The attribution block, one line per licence, as plain text. */
export const textoAtribuicao = estado =>
  licencasDaCena(estado).map(l => l.atribuicao).join('\n');

/** The document, plus the asset table an embed needs to resolve GLB paths. */
export function documentoParaJson (estado, mundo, { comAssets = false, baseGlb = '', baseCen = '' } = {}) {
  const doc = JSON.parse(JSON.stringify(estado));
  delete doc.vista; delete doc.quadro; delete doc.assentar;   // load-time hints
  doc.camera = {
    pos: mundo.camP.position.toArray().map(n => +n.toFixed(3)),
    alvo: mundo.controles.target.toArray().map(n => +n.toFixed(3)),
    fov: mundo.camP.fov,
    orto: mundo.cam === mundo.camO,
  };
  doc.gerado = new Date().toISOString();
  /* Both fields, on purpose: `licencas` is the machine-readable table a tool
     can act on, `licenca` is the one line a human reads. */
  doc.licencas = licencasDaCena(estado);
  doc.licenca = textoAtribuicao(estado);
  if (comAssets) {
    doc.assets = {};
    for (const o of doc.objetos) {
      if (o.tipo === 'prop' || doc.assets[o.slug]) continue;
      const a = acharAsset(o.slug);
      if (!a) continue;
      const base = a.tipo === 'cenario' ? (baseCen || baseGlb) : baseGlb;
      doc.assets[o.slug] = {
        arquivo: base + a.arquivo.split('/').pop(),
        nome: a.nome, matricula: a.matricula,
        tipo: a.tipo, categoria: a.categoria, licenca: a.licenca,
        bytes: a.bytes, triangulos: a.triangulos,
      };
    }
  }
  return doc;
}

/* -------------------------------------------------------------- embed --- */

/**
 * Build the embed HTML.
 * @param modo 'relativo' — the file is saved INSIDE estudio/ (default)
 *             'irmao'    — the file sits next to the GLBs, estudio/ alongside
 *             'url'      — everything under an absolute base URL
 */
export function construirEmbed (estado, mundo, cfg) {
  const baseEstudio = cfg.modo === 'url' ? cfg.baseEstudio.replace(/\/?$/, '/')
                    : cfg.modo === 'irmao' ? 'estudio/'
                    : './';
  const baseGlb = cfg.modo === 'url' ? cfg.baseGlb.replace(/\/?$/, '/')
                : cfg.modo === 'irmao' ? './'
                : '../export/web/';
  const baseCen = cfg.modo === 'url' ? (cfg.baseCen || cfg.baseGlb).replace(/\/?$/, '/')
                : cfg.modo === 'irmao' ? './'
                : '../export/cenarios/';

  const doc = documentoParaJson(estado, mundo, { comAssets: true, baseGlb, baseCen });
  const titulo = (estado.nome || 'LATAM fleet scene').replace(/[<&]/g, '');
  const lics = licencasDaCena(estado);
  const escapar = t => String(t).replace(/[<>&]/g, c => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;' }[c]));

  return `<!doctype html>
<!-- LATAM fleet — scene embed, generated by estudio/ on ${new Date().toISOString().slice(0, 10)}.

     Needs, relative to THIS file:
       ${baseEstudio}vendor/three/…      three.js r169 + Draco decoder
       ${baseEstudio}js/embed.js         the ~120-line runtime (imports mundo.js, props.js, frota.js)
       ${baseGlb}<slug>_web.glb   the aircraft, listed in doc.assets below

     LICENCES THIS SCENE CARRIES — computed from the assets actually in it,
     and they travel with the file because that is what they require:
${lics.map(l => `       ${l.atribuicao}\n         ${l.url}${l.share_alike ? '   [SHARE-ALIKE]' : ''}`).join('\n')}
-->
<html lang="en"><head>
<meta charset="utf-8">
<title>${titulo}</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  html,body{margin:0;height:100%;overflow:hidden;background:${estado.ambiente.fundoCor};
    font:12px/1.4 -apple-system,"Segoe UI",Roboto,sans-serif;color:#e6e7ea}
  #cena{position:fixed;inset:0}
  #cred{position:fixed;left:10px;bottom:8px;right:10px;color:#9aa0ae;font-size:11px;
    background:rgba(13,15,20,.6);padding:3px 7px;border-radius:5px;pointer-events:auto;
    line-height:1.5}
  #cred a{color:#8fa6ff;text-decoration:none}
</style>
</head><body>
<div id="cena"></div>
<div id="cred">${lics.map(l =>
    `<a href="${l.url}" target="_blank" rel="noopener">${escapar(l.atribuicao)}</a>`).join(' &middot; ')}
  &middot; drag to orbit, scroll to zoom</div>
<script type="importmap">
{ "imports": {
  "three": "${baseEstudio}vendor/three/three.module.js",
  "three/addons/": "${baseEstudio}vendor/three/addons/"
} }
</script>
<script type="module">
import { montar } from '${baseEstudio}js/embed.js';
const doc = ${JSON.stringify(doc, null, 1)};
montar(document.getElementById('cena'), doc, {
  autoGirar: ${cfg.autoGirar ? 'true' : 'false'},
  velocidadeGiro: ${(cfg.velocidadeGiro ?? 0.4).toFixed(2)},
  zoom: ${cfg.zoom !== false},
  pan: ${cfg.pan !== false}
}).catch(e => {
  document.getElementById('cena').innerHTML =
    '<p style="padding:20px;color:#ff8f8f;font-family:monospace">' + e.message + '</p>';
});
</script>
</body></html>
`;
}

/* -------------------------------------------------------------- output --- */

export function baixar (blob, nome) {
  const u = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = u; a.download = nome;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(u), 4000);
}

export const nomeArquivo = (nome, ext) =>
  (nome || 'cena').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 48) + '.' + ext;
