/* editor.js — selection, gizmos, and everything that mutates placement.
 *
 * Multi-select works by attaching the gizmo to a pivot Object3D placed at the
 * selection centroid and, only for the duration of a drag, re-parenting the
 * selected objects under it with Object3D.attach() (which preserves world
 * transforms). A single selection skips the pivot entirely and drives the
 * object directly, so the common case has no attach/detach float drift.
 *
 * three r169 note: TransformControls is no longer an Object3D — its visual part
 * comes from getHelper(). Adding the controller itself to the scene is the
 * classic silent failure here (no gizmo, no error).
 */

import * as THREE from 'three';
import { TransformControls } from 'three/addons/controls/TransformControls.js';

export class Editor {
  constructor (mundo, estado, historico) {
    this.mundo = mundo;
    this.estado = estado;
    this.historico = historico;
    this.selecao = [];                 // array of object ids

    this.pivo = new THREE.Object3D();
    this.pivo.name = 'pivo-selecao';
    mundo.cena.add(this.pivo);

    const tc = new TransformControls(mundo.cam, mundo.renderer.domElement);
    tc.setSize(0.85);
    tc.addEventListener('dragging-changed', e => {
      mundo.controles.enabled = !e.value;
      // The re-parenting has to bracket the drag: attach BEFORE the pivot moves
      // (attach preserves world transforms, so attaching afterwards would pin
      // the objects where they already are and the drag would do nothing), and
      // detach after. One history entry per drag, written at the end.
      if (e.value) this.iniciarArrasto();
      else { this.finalizarArrasto(); this.registrar(`${tc.mode} ${this.selecao.length} object(s)`); }
    });
    tc.addEventListener('objectChange', () => {
      this.escreverDeVolta();
      this.aoMudarTransformacao();
    });
    mundo.cena.add(tc.getHelper());
    this.gizmo = tc;

    /* callbacks the UI plugs into */
    this.aoMudarSelecao = () => {};
    this.aoMudarTransformacao = () => {};
    this.aoMudarDoc = () => {};

    this.ligarPonteiro();
    this.ligarTeclado();
  }

  /* ------------------------------------------------------------ helpers */
  /** Call AFTER the document has been mutated — see Historico. */
  registrar (rot) { this.historico.registrar(rot, this.estado); this.aoMudarDoc(); }

  docDe (id) { return this.estado.objetos.find(o => o.id === id); }
  obj3dDe (id) { return this.mundo.objetos.get(id); }

  get selecionados () { return this.selecao.map(id => this.docDe(id)).filter(Boolean); }

  /* ---------------------------------------------------------- selection */
  selecionar (ids, aditivo = false) {
    const novos = aditivo
      ? [...new Set([...this.selecao, ...ids])]
      : [...new Set(ids)];
    this.selecao = novos.filter(id => {
      const d = this.docDe(id);
      return d && !d.travado && d.visivel;
    });
    this.atualizarGizmo();
    this.aoMudarSelecao();
  }

  alternar (id) {
    if (this.selecao.includes(id)) this.selecao = this.selecao.filter(i => i !== id);
    else this.selecao = [...this.selecao, id];
    this.atualizarGizmo();
    this.aoMudarSelecao();
  }

  limparSelecao () { this.selecao = []; this.atualizarGizmo(); this.aoMudarSelecao(); }

  atualizarGizmo () {
    const m = this.mundo;
    if (!this.selecao.length) {
      this.gizmo.detach();
      m.caixaSel.visible = false;
      return;
    }
    if (this.selecao.length === 1) {
      const o = this.obj3dDe(this.selecao[0]);
      if (!o) { this.gizmo.detach(); m.caixaSel.visible = false; return; }
      this.gizmo.attach(o);
    } else {
      const b = m.caixaDe(this.selecao);
      if (!b) { this.gizmo.detach(); m.caixaSel.visible = false; return; }
      this.pivo.position.copy(b.getCenter(new THREE.Vector3()));
      this.pivo.rotation.set(0, 0, 0);
      this.pivo.scale.set(1, 1, 1);
      this.pivo.updateMatrixWorld(true);
      this.gizmo.attach(this.pivo);
    }
    const cx = m.caixaDe(this.selecao);
    if (cx) { m.caixaSel.box.copy(cx); m.caixaSel.visible = true; }
  }

  /** Drag start: put the selection under the pivot so it follows the gizmo. */
  iniciarArrasto () {
    if (this.selecao.length < 2 || this.gizmo.object !== this.pivo) return;
    this.pivo.updateMatrixWorld(true);
    for (const id of this.selecao) {
      const o = this.obj3dDe(id);
      if (o && o.parent !== this.pivo) this.pivo.attach(o);
    }
  }

  /** Drag end: put them back under the scene root, then read the result. */
  finalizarArrasto () {
    for (const id of this.selecao) {
      const o = this.obj3dDe(id);
      if (o && o.parent === this.pivo) this.mundo.raizObjetos.attach(o);
    }
    this.escreverDeVolta();
    this.atualizarGizmo();
    this.aoMudarTransformacao();
  }

  /** Read the live transforms back into the document. Never re-parents. */
  escreverDeVolta () {
    for (const id of this.selecao) {
      const o = this.obj3dDe(id), d = this.docDe(id);
      if (!o || !d) continue;
      if (o.parent === this.pivo) {
        // World transform, decomposed, so the document stays parent-free.
        o.updateWorldMatrix(true, false);
        const p = new THREE.Vector3(), q = new THREE.Quaternion(), s = new THREE.Vector3();
        o.matrixWorld.decompose(p, q, s);
        const e = new THREE.Euler().setFromQuaternion(q, 'XYZ');
        d.pos = p.toArray().map(n => +n.toFixed(4));
        d.rot = [e.x, e.y, e.z].map(r => +THREE.MathUtils.radToDeg(r).toFixed(3));
        d.esc = s.toArray().map(n => +n.toFixed(4));
      } else {
        this.mundo.lerTransformacao(d);
      }
    }
    const cx = this.mundo.caixaDe(this.selecao);
    if (cx) { this.mundo.caixaSel.box.copy(cx); this.mundo.caixaSel.visible = true; }
  }

  /* ------------------------------------------------------------ picking */
  ligarPonteiro () {
    const el = this.mundo.renderer.domElement;
    const ray = new THREE.Raycaster();
    let x0 = 0, y0 = 0, t0 = 0;

    el.addEventListener('pointerdown', e => { x0 = e.clientX; y0 = e.clientY; t0 = performance.now(); });
    el.addEventListener('pointerup', e => {
      if (Math.hypot(e.clientX - x0, e.clientY - y0) > 4) return;   // that was an orbit
      if (performance.now() - t0 > 500) return;
      if (this.gizmo.dragging) return;

      const r = el.getBoundingClientRect();
      const p = new THREE.Vector2(
        ((e.clientX - r.left) / r.width) * 2 - 1,
        -((e.clientY - r.top) / r.height) * 2 + 1);
      ray.setFromCamera(p, this.mundo.cam);
      const hits = ray.intersectObjects(this.mundo.raizObjetos.children, true);
      const alvo = hits.length ? this.raiz(hits[0].object) : null;
      const id = alvo?.userData?.id;
      if (!id) { if (!e.shiftKey) this.limparSelecao(); return; }
      const d = this.docDe(id);
      if (d?.travado) return;
      if (e.shiftKey) this.alternar(id); else this.selecionar([id]);
    });
  }

  raiz (o) {
    let n = o;
    while (n && !n.userData.id) n = n.parent;
    return n;
  }

  /* ----------------------------------------------------------- keyboard */
  ligarTeclado () {
    addEventListener('keydown', e => {
      const alvo = e.target;
      if (alvo && (alvo.tagName === 'INPUT' || alvo.tagName === 'SELECT' || alvo.tagName === 'TEXTAREA')) return;
      const cmd = e.metaKey || e.ctrlKey;

      if (cmd && e.key.toLowerCase() === 'z') { e.preventDefault(); this.aoAtalho(e.shiftKey ? 'refazer' : 'desfazer'); return; }
      if (cmd && e.key.toLowerCase() === 'd') { e.preventDefault(); this.aoAtalho('duplicar'); return; }
      if (cmd) return;

      switch (e.key.toLowerCase()) {
        case 'w': this.modo('translate'); break;
        case 'e': this.modo('rotate'); break;
        case 'r': this.modo('scale'); break;
        case 'q': this.espaco(this.gizmo.space === 'world' ? 'local' : 'world'); break;
        case 'x': this.eixo('X'); break;
        case 'y': this.eixo('Y'); break;
        case 'z': this.eixo('Z'); break;
        case 'f': this.aoAtalho('enquadrar-sel'); break;
        case 'a': this.aoAtalho('enquadrar-tudo'); break;
        case 'g': this.aoAtalho('chao'); break;
        case 'escape': this.limparSelecao(); break;
        case 'delete': case 'backspace': e.preventDefault(); this.aoAtalho('apagar'); break;
      }
    });
  }
  aoAtalho () {}          // main.js replaces this

  modo (m) { this.gizmo.setMode(m); this.aoMudarSelecao(); }
  espaco (s) { this.gizmo.setSpace(s); this.aoMudarSelecao(); }

  /** X/Y/Z toggles a single-axis constraint; pressing the same axis frees it. */
  eixo (a) {
    const g = this.gizmo;
    const so = { X: g.showX && !g.showY && !g.showZ, Y: g.showY && !g.showX && !g.showZ, Z: g.showZ && !g.showX && !g.showY };
    if (so[a]) { g.showX = g.showY = g.showZ = true; }
    else { g.showX = a === 'X'; g.showY = a === 'Y'; g.showZ = a === 'Z'; }
  }

  snap (mov, rot) {
    this.gizmo.setTranslationSnap(mov > 0 ? mov : null);
    this.gizmo.setRotationSnap(rot > 0 ? THREE.MathUtils.degToRad(rot) : null);
  }

  /* --------------------------------------------------------- operations */

  /** Drop the selection so its lowest point rests on y = 0. */
  aoChao () {
    if (!this.selecao.length) return;
    for (const id of this.selecao) {
      const o = this.obj3dDe(id), d = this.docDe(id);
      if (!o || !d) continue;
      o.updateMatrixWorld(true);
      const b = new THREE.Box3().setFromObject(o);
      d.pos[1] = +(d.pos[1] - b.min.y).toFixed(4);
    }
    this.mundo.aplicarTransformacoes(this.estado);
    this.atualizarGizmo();
    this.aoMudarTransformacao();
    this.registrar('snap to ground');
  }

  travar (id, v) {
    const d = this.docDe(id); if (!d) return;
    d.travado = v;
    if (v) this.selecao = this.selecao.filter(i => i !== id);
    this.atualizarGizmo();
    this.aoMudarSelecao();
    this.registrar(v ? 'lock' : 'unlock');
  }

  ocultar (id, v) {
    const d = this.docDe(id); if (!d) return;
    d.visivel = !v;
    if (v) this.selecao = this.selecao.filter(i => i !== id);
    this.mundo.aplicarTransformacoes(this.estado);
    this.atualizarGizmo();
    this.aoMudarSelecao();
    this.registrar(v ? 'hide' : 'show');
  }
}
