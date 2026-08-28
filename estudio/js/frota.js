/* frota.js — the GLB asset library: the fleet AND the airports.
 *
 * Reads two manifests and merges them into ONE catalogue:
 *
 *   ../export/manifest.json           export_frota.py  — the 11 aircraft
 *   ../export/cenarios/manifest.json  export_cenarios.py — the airport pieces
 *
 * Nothing here is hard-coded per asset. Add a twelfth jet or a fortieth hangar,
 * re-run the exporter, and it shows up in the sidebar under its own category
 * with its own measured numbers and its own licence.
 *
 * LICENCE IS A PER-ASSET FIELD, and that is the whole point. The aircraft are
 * CC BY 4.0; the airport geometry is an OpenStreetMap derivative and is ODbL
 * 1.0 with share-alike. Both may ship — see NOTICE.md, "The airport mesh is an
 * OSM derivative" — provided the attribution travels with them. So each row
 * carries `licenca`, the licence table comes out of the scenery manifest, and
 * the studio shows the licences the OPEN SCENE actually uses rather than a
 * blanket claim about the whole page.
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

/* The sidebar's section order. The LABELS come from the manifests; only the
   order lives here, because "aircraft first" is an editorial choice and not a
   fact about the data. A category the manifests invent tomorrow falls in at the
   end rather than disappearing. */
export const ORDEM_CATEGORIAS = ['aeronave', 'estrutura', 'superficie',
                                 'veiculo', 'adereco'];

/** id -> { nome, url, atribuicao, share_alike, nota }. Filled from the scenery
 *  manifest; seeded with CC BY so an install without export/cenarios/ still
 *  attributes the fleet correctly. */
export const LICENCAS = {
  'cc-by-4.0': {
    nome: 'CC BY 4.0',
    url: 'https://creativecommons.org/licenses/by/4.0/',
    atribuicao: 'LATAM fleet 3D replicas — Kim Lage — CC BY 4.0',
    share_alike: false,
    nota: 'Original geometry built in this repository from the manufacturers\' '
        + 'published dimensional documents.',
  },
};

/** id -> human label, from the manifests. */
export const CATEGORIAS = { aeronave: 'aircraft' };

/** Which fields the scenery came from, for the licence panel and the cards. */
export const CAMPOS = {};

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
      tipo: 'aeronave',
      categoria: e.categoria || 'aeronave',
      licenca: e.licenca || 'cc-by-4.0',
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

/** The airport tier. Optional: a repository without export/cenarios/ still
 *  runs, it just has no airports. Returns how many assets it added. */
export async function carregarCenarios () {
  let m;
  try {
    const r = await fetch(EXPORT + 'cenarios/manifest.json', { cache: 'no-cache' });
    if (!r.ok) throw new Error(`cenarios/manifest.json ${r.status}`);
    m = await r.json();
  } catch (e) {
    console.warn('no airport tier —', e.message,
                 '— run  python3 export_cenarios.py  to build it');
    return { n: 0, erro: e.message };
  }
  Object.assign(LICENCAS, m.licencas || {});
  Object.assign(CATEGORIAS, m.categorias || {});
  Object.assign(CAMPOS, m.campos || {});

  let n = 0;
  for (const a of m.assets || []) {
    if (acharAsset(a.slug)) continue;
    const t = (a.caixa && a.caixa.tamanho) || [0, 0, 0];
    catalogo.push({
      slug: a.slug,
      tipo: 'cenario',
      categoria: a.categoria || 'adereco',
      licenca: a.licenca || 'odbl-1.0',
      campo: a.campo,
      nome: a.rotulo || a.slug,
      matricula: (m.campos?.[a.campo]?.rotulo || a.campo || '').split(' - ')[0],
      arquivo: EXPORT + 'cenarios/' + a.arquivo,
      bytes: a.bytes || 0,
      triangulos: a.triangulos || 0,
      faces: a.faces || 0,
      materiais: a.materiais || 0,
      L: t[0], H: t[1], env: t[2],
      nota: a.nota || '',
      datum: a.fonte?.datum || 'min',
      ok: (a.verificacao || {}).ok !== false,
    });
    n++;
  }
  ordenarCatalogo();
  return { n, marcas: m.marcas, aviso: m.aviso };
}

/** Licence ids used by a list of scene rows, in catalogue order. */
export function licencasDe (objetos = []) {
  const ids = new Set();
  for (const o of objetos) {
    if (o.tipo === 'prop') { ids.add('estudio'); continue; }
    const a = acharAsset(o.slug);
    if (a) ids.add(a.licenca);
  }
  return [...ids];
}

function ordenarCatalogo () {
  catalogo.sort((a, b) => {
    const ca = ORDEM_CATEGORIAS.indexOf(a.categoria);
    const cb = ORDEM_CATEGORIAS.indexOf(b.categoria);
    if (ca !== cb) return (ca < 0 ? 99 : ca) - (cb < 0 ? 99 : cb);
    const ia = ORDEM.indexOf(a.slug), ib = ORDEM.indexOf(b.slug);
    if (ia >= 0 || ib >= 0) return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
    return a.slug.localeCompare(b.slug);
  });
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
      tipo: a.tipo || 'aeronave', categoria: a.categoria || 'aeronave',
      licenca: a.licenca || 'cc-by-4.0',
      arquivo: a.arquivo, bytes: a.bytes || 0, triangulos: a.triangulos || 0,
      materiais: 0, L: 0, H: 0, env: 0, ok: true,
    });
  }
}

/** Load a GLB once. Later calls share the same parsed scene. */
export function carregarGLB (slug, aoProgresso) {
  if (cache.has(slug)) return cache.get(slug);
  const asset = acharAsset(slug);
  if (!asset) return Promise.reject(new Error(`unknown asset slug "${slug}"`));

  const p = new Promise((ok, erro) => {
    loader.load(asset.arquivo,
      gltf => {
        const raiz = gltf.scene;
        /* A pavement asset RECEIVES shadows and does not cast them. It is a
           carpet: a zero-thickness plane 6 cm above the studio's own ground,
           casting into a shadow map whose texel is 26 cm on the ground at a
           27° sun, shadows ITSELF in stripes. That striping was visible across
           the whole apron of the first stand scene, and no bias tweak fixes it
           — the surface simply should not be an occluder. */
        const projeta = asset.categoria !== 'superficie';
        raiz.traverse(o => {
          if (!o.isMesh) return;
          o.castShadow = projeta;
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

/** An instance ready to drop in the scene: pivot Group, wheels at y = 0.
 *
 *  An AIRCRAFT GLB has its nose at x = 0 and its tail at x = +L, so the studio
 *  measures the loaded box and shifts the copy to put the origin at the X/Z
 *  centre. A SCENERY GLB arrives already centred by export_cenarios.py, which
 *  also VERIFIES it — and in three cases centred deliberately somewhere other
 *  than the bounding-box middle: a runway section is centred on the runway,
 *  not on the box, because a PAPI on one side alone pulls that box 21 m off the
 *  centreline. Re-centring those here silently undid the exporter's decision
 *  and put the 777 of the runway starter with its gear on the shoulder. So the
 *  shift applies to aircraft only. */
export async function instanciar (slug, aoProgresso) {
  const raiz = await carregarGLB(slug, aoProgresso);
  const asset = acharAsset(slug);
  const copia = raiz.clone(true);             // shares geometry + materials
  const c = raiz.userData.centro, t = raiz.userData.tamanho;
  if (!asset || asset.tipo !== 'cenario') copia.position.set(-c.x, 0, -c.z);

  const pivo = new THREE.Group();
  pivo.add(copia);
  pivo.userData.tamanho = t.clone();
  pivo.userData.raio = Math.hypot(t.x, t.z) / 2;
  medirTrem(pivo);
  return pivo;
}

/* --------------------------------------------------------- landing gear ---
 * Every aircraft GLB in this repository names its gear meshes: the nose leg is
 * `TremNariz_*` and the main gear is `TremP_*` (777/767/787) or
 * `TremPrincipal_*` (the A320 family). That is a fact about the exported files,
 * checked across all eleven — 15 gear nodes on an A319, 32 on a 787 — and it
 * buys the timeline two things it cannot get any other way:
 *
 *   the MAIN-GEAR CONTACT POINT, which is what an aeroplane rotates about on
 *      the runway. Rotate about the instance's own origin instead and the nose
 *      goes up while the wheels sink through the pavement.
 *   a GEAR-UP KEY, which is simply hiding those nodes.
 *
 * Measured here, where the pivot is still at the identity, so what comes out is
 * already in the pivot's own frame. Nothing is hard-coded per type; an aircraft
 * whose gear is named something else gets `trem = null` and the timeline falls
 * back to the object origin, which is stated in the flight panel rather than
 * silently wrong. */
function medirTrem (pivo) {
  const principais = [], todos = [];
  pivo.traverse(o => {
    if (!o.isMesh || !o.name) return;
    if (!o.name.startsWith('Trem')) return;
    todos.push(o);
    if (o.name.startsWith('TremP')) principais.push(o);      // TremP_ and TremPrincipal_
  });
  pivo.userData.nosTrem = todos;
  if (!principais.length) { pivo.userData.trem = null; return; }
  pivo.updateMatrixWorld(true);
  const b = new THREE.Box3();
  for (const m of principais) b.expandByObject(m);
  const c = b.getCenter(new THREE.Vector3());
  /* x is the contact's station along the fuselage, y its lowest point — which
     should be ≈ 0 because the exporter puts the wheels on y = 0, but it is
     measured rather than assumed, because "should be" is how a datum drifts. */
  pivo.userData.trem = { x: +c.x.toFixed(4), y: +b.min.y.toFixed(4), nos: principais.length };
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
