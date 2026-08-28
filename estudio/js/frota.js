/* frota.js — the aircraft library.
 *
 * Reads ../export/manifest.json (the file export_frota.py writes) and turns the
 * `web` LOD rows into catalogue entries. Nothing here is hard-coded per
 * aircraft: add a twelfth jet to the fleet, re-run the exporter, and it shows
 * up in the sidebar with its own measured numbers.
 *
 * The GLBs are +Y up, metres, wheels on y = 0, nose at x ≈ 0 and tail at
 * x ≈ +L (see export/README.md §Axis). Every instance is therefore wrapped in
 * a pivot Group whose origin sits at the aircraft's X/Z bounding-box centre
 * with y = 0 at the wheels, so that
 *   - a turntable spins about the aircraft, not about its nose tip,
 *   - the gizmo lands where the eye expects it,
 *   - "snap to ground" is `pos.y = 0`.
 * The offset is measured from the loaded geometry, not read from the manifest.
 */

import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';

/* Derived from this module's own URL, not from document.baseURI: an exported
   embed is an HTML file living somewhere else entirely, and the Draco decoder
   still has to be found next to this file. */
export const BASE   = new URL('../', import.meta.url).href;         // …/estudio/
export const EXPORT = new URL('../../export/', import.meta.url).href; // …/export/

/* Preferred sidebar order: Airbus small→large, then Boeing, freighters last.
   Anything the manifest has that is not listed falls in after, in file order. */
const ORDEM = ['A319', 'A320ceo', 'A320neo', 'A321ceo', 'A321neo',
               'B763', 'B77W', 'B788', 'B789', 'B763F', 'B763BCF'];

const draco = new DRACOLoader().setDecoderPath(BASE + 'vendor/three/draco/');
const loader = new GLTFLoader().setDRACOLoader(draco);

export const catalogo = [];        // filled by carregarManifesto()
const cache = new Map();           // slug -> Promise<THREE.Group> (the pristine load)

/** Fetch and flatten the manifest. Throws with a readable message if missing. */
export async function carregarManifesto () {
  const r = await fetch(EXPORT + 'manifest.json', { cache: 'no-cache' });
  if (!r.ok) throw new Error(`manifest.json ${r.status} at ${EXPORT} — serve the repository ROOT, not estudio/`);
  const m = await r.json();

  const web = m.exportacoes.filter(e => e.lod === 'web' && e.saidas && e.saidas.glb);
  for (const e of web) {
    const v = e.verificacao || {};
    const cx = v.caixa || {};
    catalogo.push({
      slug: e.slug,
      nome: e.nome,
      matricula: e.matricula || '—',
      arquivo: EXPORT + e.saidas.glb.arquivo,          // export/web/<slug>_web.glb
      bytes: e.saidas.glb.bytes,
      triangulos: v.triangulos ?? e.triangulos_blender ?? 0,
      materiais: v.materiais ?? 0,
      // glTF box: X length, Y height, Z span (the exporter *verifies* this).
      L: cx.tamanho ? cx.tamanho[0] : e.L_ref,
      H: cx.tamanho ? cx.tamanho[1] : 0,
      env: cx.tamanho ? cx.tamanho[2] : 0,
      L_ref: e.L_ref,
      ok: v.ok !== false,
    });
  }
  catalogo.sort((a, b) => {
    const ia = ORDEM.indexOf(a.slug), ib = ORDEM.indexOf(b.slug);
    return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
  });
  return { licenca: m.licenca, gerado_por: m.gerado_por, n: catalogo.length };
}

export const acharAsset = slug => catalogo.find(c => c.slug === slug);

/** Seed the catalogue without a manifest — what an exported embed does, from
 *  the `assets` table baked into its scene JSON. Paths there are relative to
 *  the embed page, so they are left exactly as written. */
export function registrarAssets (mapa = {}) {
  for (const [slug, a] of Object.entries(mapa)) {
    if (acharAsset(slug)) continue;
    catalogo.push({
      slug, nome: a.nome || slug, matricula: a.matricula || '—',
      arquivo: a.arquivo, bytes: a.bytes || 0, triangulos: a.triangulos || 0,
      materiais: 0, L: 0, H: 0, env: 0, ok: true,
    });
  }
}

/** Load a GLB once. Later calls share the same parsed scene. */
export function carregarGLB (slug, aoProgresso) {
  if (cache.has(slug)) return cache.get(slug);
  const asset = acharAsset(slug);
  if (!asset) return Promise.reject(new Error(`unknown aircraft slug "${slug}"`));

  const p = new Promise((ok, erro) => {
    loader.load(asset.arquivo,
      gltf => {
        const raiz = gltf.scene;
        raiz.traverse(o => {
          if (!o.isMesh) return;
          o.castShadow = true;
          o.receiveShadow = true;
        });
        // Measure once, here, on the geometry as loaded.
        const caixa = new THREE.Box3().setFromObject(raiz);
        raiz.userData.caixa = caixa;
        raiz.userData.centro = caixa.getCenter(new THREE.Vector3());
        raiz.userData.tamanho = caixa.getSize(new THREE.Vector3());
        ok(raiz);
      },
      ev => aoProgresso && ev.total && aoProgresso(ev.loaded / ev.total),
      e => erro(new Error(`failed to load ${asset.arquivo}: ${e.message || e}`)));
  });
  cache.set(slug, p);
  return p;
}

/** An instance ready to drop in the scene: pivot Group, wheels at y = 0. */
export async function instanciar (slug, aoProgresso) {
  const raiz = await carregarGLB(slug, aoProgresso);
  const copia = raiz.clone(true);             // shares geometry + materials
  const c = raiz.userData.centro, t = raiz.userData.tamanho;
  copia.position.set(-c.x, 0, -c.z);          // pivot at the X/Z centre, ground datum kept

  const pivo = new THREE.Group();
  pivo.add(copia);
  pivo.userData.tamanho = t.clone();
  pivo.userData.raio = Math.hypot(t.x, t.z) / 2;
  return pivo;
}

/** Bytes already fetched, for the status line. */
export function bytesCarregados () {
  let n = 0;
  for (const slug of cache.keys()) { const a = acharAsset(slug); if (a) n += a.bytes; }
  return n;
}

/* ------------------------------------------------------------ thumbnails -
 * Rendered from the real GLB in a tiny throwaway context, then cached in
 * localStorage as a JPEG data URL. One at a time, lowest priority: the sidebar
 * is usable before any of them arrive. */
const MINI_CHAVE = 'latam-estudio/miniaturas/2';
let miniCache = {};
try { miniCache = JSON.parse(localStorage.getItem(MINI_CHAVE)) || {}; } catch (e) { miniCache = {}; }

let miniRenderer = null, fila = [], rodando = false;

function obterMiniRenderer () {
  if (miniRenderer) return miniRenderer;
  miniRenderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  miniRenderer.setSize(168, 114, false);
  miniRenderer.setPixelRatio(1);
  miniRenderer.outputColorSpace = THREE.SRGBColorSpace;
  miniRenderer.toneMapping = THREE.ACESFilmicToneMapping;
  return miniRenderer;
}

async function fazerMiniatura (slug) {
  if (miniCache[slug]) return miniCache[slug];
  const raiz = await carregarGLB(slug);
  const r = obterMiniRenderer();
  const cena = new THREE.Scene();
  const obj = raiz.clone(true);
  cena.add(obj);
  cena.add(new THREE.HemisphereLight(0xcddcff, 0x2a2620, 1.4));
  const sol = new THREE.DirectionalLight(0xfff2df, 2.6);
  sol.position.set(-1.4, 1.8, 1.1);
  cena.add(sol);

  const cx = raiz.userData.centro, tam = raiz.userData.tamanho;
  const cam = new THREE.PerspectiveCamera(32, 168 / 114, 0.5, 4000);
  const raio = tam.length() / 2;
  const d = raio / Math.sin(THREE.MathUtils.degToRad(32) / 2) * 0.62;
  cam.position.set(cx.x - d * 0.70, cx.y + d * 0.30, cx.z + d * 0.62);
  cam.lookAt(cx);
  r.render(cena, cam);

  const url = r.domElement.toDataURL('image/jpeg', 0.72);
  cena.clear();
  miniCache[slug] = url;
  try { localStorage.setItem(MINI_CHAVE, JSON.stringify(miniCache)); } catch (e) { /* quota: cache in memory only */ }
  return url;
}

async function bombear () {
  if (rodando) return;
  rodando = true;
  while (fila.length) {
    const { slug, ok } = fila.shift();
    try { ok(await fazerMiniatura(slug)); }
    catch (e) { console.warn('thumbnail failed for', slug, e); ok(null); }
    await new Promise(r => setTimeout(r, 0));
  }
  rodando = false;
  if (miniRenderer) { miniRenderer.dispose(); miniRenderer.forceContextLoss?.(); miniRenderer = null; }
}

/** Queue a thumbnail. Resolves with a data URL, or null if it could not render. */
export function miniatura (slug) {
  if (miniCache[slug]) return Promise.resolve(miniCache[slug]);
  return new Promise(ok => { fila.push({ slug, ok }); bombear(); });
}
