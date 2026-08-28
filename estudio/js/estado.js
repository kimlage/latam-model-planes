/* estado.js — the scene document.
 *
 * Everything that survives a save lives in one plain object. The three.js
 * objects are built FROM it and never hold state of their own that matters:
 * `mundo.aplicar(estado)` is idempotent and `mundo.reconstruir(estado)` can
 * rebuild the whole scene from nothing but this JSON.
 *
 * That is also why undo is a snapshot stack rather than a set of inverse
 * commands: one serialiser, one restorer, no third code path that can disagree
 * with the other two. The cost is that undo re-instantiates objects — cheap,
 * because the GLB payloads are cached and instances are `Object3D.clone()`s
 * that share geometry and materials.
 */

export const SCHEMA = 'latam-estudio/1';

let contador = 0;
export const novoId = (p = 'o') => `${p}${(++contador).toString(36)}${Date.now().toString(36).slice(-3)}`;

/** A blank document. Deep-cloned on every use — never hand out the template. */
export function estadoPadrao () {
  return {
    schema: SCHEMA,
    nome: 'untitled scene',
    ambiente: {
      sol:  { elev: 34, azim: 135, intensidade: 3.0, cor: '#fff2df' },
      envPreset: 'ceu',          // ceu | sala | nenhum
      envIntensidade: 1.0,
      fundo: 'ceu',              // ceu | cor | transparente
      fundoCor: '#0d0f14',
      neblina: { ligado: false, densidade: 4 },   // densidade in units of 1e-4
      chao: { ligado: true, tipo: 'apron', tamanho: 600 },
      grade: true,
    },
    render: {
      tone: 'aces',              // aces | agx | neutral | reinhard | linear
      exposicao: 1.0,
      sombras: true,
      sombraPx: 2048,
      aa: 1,                     // 0 none | 1 MSAA | 2 MSAA + 2x supersample on export
      pixelRatioMax: 2,
    },
    camera: {
      pos: [-70, 26, 62], alvo: [0, 4, 0], fov: 35, orto: false,
    },
    poses: { A: null, B: null },  // the two endpoints of the "camera path" GIF
    objetos: [],                  // see novoObjeto()
  };
}

/** One instance in the scene. `slug` picks the asset; the rest is placement. */
export function novoObjeto (tipo, slug, nome, extra = {}) {
  return {
    id: novoId(tipo === 'aeronave' ? 'a' : 'p'),
    tipo,                        // 'aeronave' | 'prop'
    slug,
    nome,
    pos: [0, 0, 0],
    rot: [0, 0, 0],              // degrees, XYZ order
    esc: [1, 1, 1],
    visivel: true,
    travado: false,
    ...extra,
  };
}

export const clonar = o => JSON.parse(JSON.stringify(o));

/* --------------------------------------------------------------- history */
/* A stack of states, not of commands. `registrar()` is called AFTER a mutation
 * and stores the state the user is now looking at; the cursor `i` always points
 * at the current state.
 *
 * The direction matters and the other way round is a real bug: if you push the
 * state from BEFORE the mutation, undo works and redo cannot — the post-change
 * state was never written down anywhere. This studio had that bug for an hour.
 * Each entry's label describes the action that PRODUCED it, so undoing entry i
 * is undoing pilha[i].rot. */
export class Historico {
  constructor (limite = 60) { this.limite = limite; this.pilha = []; this.i = -1; this.aoMudar = () => {}; }

  iniciar (estado) { this.pilha = [{ rot: 'open scene', s: clonar(estado) }]; this.i = 0; this.aoMudar(); }

  registrar (rot, estado) {
    this.pilha.length = this.i + 1;            // drop any redo tail
    this.pilha.push({ rot, s: clonar(estado) });
    if (this.pilha.length > this.limite) this.pilha.shift();
    this.i = this.pilha.length - 1;
    this.aoMudar();
  }

  get podeDesfazer () { return this.i > 0; }
  get podeRefazer  () { return this.i < this.pilha.length - 1; }
  get rotuloDesfazer () { return this.podeDesfazer ? this.pilha[this.i].rot : ''; }
  get rotuloRefazer  () { return this.podeRefazer  ? this.pilha[this.i + 1].rot : ''; }

  desfazer () { if (!this.podeDesfazer) return null; this.i--; this.aoMudar(); return clonar(this.pilha[this.i].s); }
  refazer  () { if (!this.podeRefazer)  return null; this.i++; this.aoMudar(); return clonar(this.pilha[this.i].s); }
}

/* ------------------------------------------------------- scene library ---
 * localStorage, one key for the whole library. Scenes are small (a few kB);
 * the 5 MB quota is never the binding constraint, the thumbnails would be, so
 * they are not stored. */
const CHAVE = 'latam-estudio/cenas/1';

export function lerBiblioteca () {
  try { return JSON.parse(localStorage.getItem(CHAVE)) || {}; }
  catch (e) { console.warn('scene library unreadable, starting empty', e); return {}; }
}
export function gravarBiblioteca (b) {
  try { localStorage.setItem(CHAVE, JSON.stringify(b)); return true; }
  catch (e) { console.error('could not save scene', e); return false; }
}
export function salvarCena (estado) {
  const b = lerBiblioteca();
  const nome = estado.nome || 'untitled scene';
  b[nome] = { ...clonar(estado), nome, salvo: new Date().toISOString() };
  return gravarBiblioteca(b) ? nome : null;
}
export function apagarCena (nome) { const b = lerBiblioteca(); delete b[nome]; gravarBiblioteca(b); }
