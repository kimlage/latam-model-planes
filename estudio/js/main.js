/* main.js — boot and wiring.
 *
 * Reads the fleet manifest, builds the world, binds every control in the two
 * side columns to the scene document, and owns the render loop. Anything with
 * real logic lives in its own module; this file is the switchboard.
 */

import * as THREE from 'three';
import { estadoPadrao, novoObjeto, clonar, Historico, lerBiblioteca, salvarCena, apagarCena } from './estado.js';
import { carregarManifesto, catalogo, miniatura, bytesCarregados, acharAsset } from './frota.js';
import { PROPS, RIGS } from './props.js';
import { Mundo } from './mundo.js';
import { Editor } from './editor.js';
import { CENAS_BASE, ROTULOS_BASE, cenaBase } from './cenas.js';
import { h, dlgExportar, dlgLicenca, fecharModal } from './dialogos.js';
import { formatarBytes } from './exportar.js';

const $ = id => document.getElementById(id);

let estado = estadoPadrao();
const historico = new Historico();
let mundo, editor;
let falhas = [];

/* ------------------------------------------------------------------ boot */

async function iniciar () {
  mundo = new Mundo($('viewport'));
  editor = new Editor(mundo, estado, historico);

  editor.aoMudarSelecao = () => { desenharOutliner(); sincronizarTransform(); };
  editor.aoMudarTransformacao = () => sincronizarTransform();
  editor.aoMudarDoc = () => atualizarBotoesHistorico();
  editor.aoAtalho = atalho;
  historico.aoMudar = atualizarBotoesHistorico;

  ligarInspetor();
  ligarBarra();
  ligarHud();
  ligarArrastar();

  try {
    const info = await carregarManifesto();
    $('cnt-frota').textContent = `${info.n} exported`;
  } catch (e) {
    $('lista-frota').innerHTML =
      `<p class="nota" style="color:#ff8f8f">${e.message}<br><br>Run
       <code>python3 -m http.server 8000</code> in the repository root and open
       <code>/estudio/</code>.</p>`;
    console.error(e);
  }
  construirBiblioteca();

  mundo.aplicarRender(estado.render);
  mundo.aplicarAmbiente(estado.ambiente);
  sincronizarInspetor();
  historico.iniciar(estado);

  mundo.iniciarLoop(() => {
    mundo.controles.update();
    mundo.render();
    contarQuadro();
  });

  /* Debug handle. Deliberate: it is how this page was driven and verified from
     the console, and it is the only way to script the studio from outside. */
  window.__estudio = { mundo, editor, estado, historico, carregarDocumento, adicionar, atalho };

  // Open on something worth looking at rather than an empty grid.
  await carregarDocumento(cenaBase('heroi'));
}

/* -------------------------------------------------------------- sidebar */

function construirBiblioteca () {
  const lf = $('lista-frota');
  lf.textContent = '';
  for (const a of catalogo) {
    const img = h('img.thumb', { alt: '' });
    miniatura(a.slug).then(u => { if (u) img.src = u; }).catch(() => {});
    const card = h('div.card', {
      draggable: 'true', title: `${a.nome} · ${a.matricula}\n${a.L.toFixed(2)} m long · ${a.env.toFixed(2)} m span\n${a.triangulos.toLocaleString()} triangles · ${formatarBytes(a.bytes)}`,
      onclick: () => adicionar('aeronave', a.slug, a.nome),
      ondragstart: e => e.dataTransfer.setData('text/plain', `aeronave:${a.slug}:${a.nome}`),
    },
      img,
      h('div', {},
        h('div.n', {}, a.nome),
        h('div.m', {}, `${a.matricula} · ${a.L.toFixed(1)} m · ${(a.triangulos / 1000).toFixed(0)}k tris`)));
    card.dataset.busca = `${a.nome} ${a.matricula} ${a.slug}`.toLowerCase();
    lf.append(card);
  }

  const lp = $('lista-props');
  lp.textContent = '';
  for (const [slug, def] of Object.entries(PROPS)) {
    const card = h('div.card', {
      draggable: 'true', title: def.rotulo,
      onclick: () => adicionar('prop', slug, def.rotulo),
      ondragstart: e => e.dataTransfer.setData('text/plain', `prop:${slug}:${def.rotulo}`),
    },
      h('div.thumb', { style: 'display:grid;place-items:center;color:#5c6478;font-size:18px' }, '▦'),
      h('div', {}, h('div.n', {}, def.rotulo), h('div.m', {}, def.medidas)));
    card.dataset.busca = `${def.rotulo} ${slug}`.toLowerCase();
    lp.append(card);
  }

  const lr = $('lista-rigs');
  lr.textContent = '';
  for (const [chave, r] of Object.entries(RIGS)) {
    const card = h('div.card', { title: r.desc, onclick: () => aplicarRig(chave) },
      h('div.thumb', { style: 'display:grid;place-items:center;color:#c9a24a;font-size:18px' }, '☀'),
      h('div', {}, h('div.n', {}, r.rotulo), h('div.m', {}, r.desc)));
    card.dataset.busca = `${r.rotulo} ${r.desc}`.toLowerCase();
    lr.append(card);
  }

  $('busca').addEventListener('input', e => {
    const q = e.target.value.trim().toLowerCase();
    document.querySelectorAll('.card').forEach(c =>
      c.classList.toggle('oculto', !!q && !(c.dataset.busca || '').includes(q)));
  });

  desenharCenas();
}

function desenharCenas () {
  const lb = $('lista-cenas-base');
  lb.textContent = '';
  for (const chave of Object.keys(CENAS_BASE)) {
    lb.append(h('div.linha', { onclick: () => carregarDocumento(cenaBase(chave)) },
      h('span.rot', {}, ROTULOS_BASE[chave]),
      h('span.tag', {}, 'starter')));
  }

  const lu = $('lista-cenas-user');
  lu.textContent = '';
  const bib = lerBiblioteca();
  const nomes = Object.keys(bib).sort();
  if (!nomes.length) lu.append(h('p.nota', {}, 'Nothing saved yet. “Save scene” puts the current composition here.'));
  for (const nome of nomes) {
    lu.append(h('div.linha', { onclick: e => { if (e.target.tagName !== 'BUTTON') carregarDocumento(clonar(bib[nome])); } },
      h('span.rot', { title: `saved ${bib[nome].salvo || '?'}` }, nome),
      h('button.mini', { title: 'duplicate', onclick: () => { const c = clonar(bib[nome]); c.nome = `${nome} copy`; salvarCena(c); desenharCenas(); } }, '⧉'),
      h('button.mini', { title: 'rename', onclick: () => { const n = prompt('New name', nome); if (n && n !== nome) { const c = clonar(bib[nome]); c.nome = n; salvarCena(c); apagarCena(nome); desenharCenas(); } } }, '✎'),
      h('button.mini', { title: 'delete', onclick: () => { if (confirm(`Delete scene “${nome}”?`)) { apagarCena(nome); desenharCenas(); } } }, '✕')));
  }
}

/* ------------------------------------------------------------- documents */

function substituirEstado (novo) {
  for (const k of Object.keys(estado)) delete estado[k];
  Object.assign(estado, novo);
}

function mostrarCarga (txt, frac) {
  const c = $('carga');
  c.hidden = false;
  c.querySelector('span').textContent = txt;
  c.querySelector('i').style.width = `${Math.round((frac || 0) * 100)}%`;
}
const esconderCarga = () => { $('carga').hidden = true; };

async function carregarDocumento (doc) {
  fecharModal();
  const base = estadoPadrao();
  // Merge so an older or hand-edited JSON still opens with sane defaults.
  const novo = {
    ...base, ...doc,
    ambiente: { ...base.ambiente, ...(doc.ambiente || {}),
      sol: { ...base.ambiente.sol, ...(doc.ambiente?.sol || {}) },
      chao: { ...base.ambiente.chao, ...(doc.ambiente?.chao || {}) },
      neblina: { ...base.ambiente.neblina, ...(doc.ambiente?.neblina || {}) } },
    render: { ...base.render, ...(doc.render || {}) },
    poses: { ...base.poses, ...(doc.poses || {}) },
    objetos: (doc.objetos || []).map(o => ({ ...novoObjeto(o.tipo, o.slug, o.nome), ...o })),
  };
  substituirEstado(novo);
  editor.selecao = [];
  editor.atualizarGizmo();

  mostrarCarga('loading assets…', 0);
  mundo.aplicarRender(estado.render);
  mundo.aplicarAmbiente(estado.ambiente);
  await mundo.sincronizar(estado, (f, t, nome) => mostrarCarga(`${nome} — ${f}/${t}`, f / t));
  mundo.aplicarAmbiente(estado.ambiente);      // the shadow camera needs the real scene radius
  esconderCarga();

  mundo.camP.fov = estado.camera.fov || 35;
  mundo.camP.updateProjectionMatrix();
  if (doc.camera && doc.camera.pos) {
    mundo.aplicarPose(doc.camera);
    if (doc.camera.orto) { estado.camera.orto = true; mundo.usarOrto(true); }
  } else {
    /* A starter scene carries a direction, not a position: frame what is here.
       Frame the AIRCRAFT, not everything — a 240 m backdrop card or a terminal
       block would otherwise decide the shot and leave the jet a speck. The
       "frame all" button still frames all of it. */
    const aeronaves = estado.objetos.filter(o => o.tipo === 'aeronave').map(o => o.id);
    mundo.vista(doc.vista || 'tres-quartos', mundo.caixaDe(aeronaves) || mundo.caixaTudo());
  }
  $('nome-cena').value = estado.nome;
  sincronizarInspetor();
  desenharOutliner();
  sincronizarTransform();
  historico.iniciar(estado);
}

/* ------------------------------------------------------------ operations */

/** A spot on the ground that does not sit inside anything already placed. */
function posicaoLivre (raioNovo, perto) {
  const alvo = perto || mundo.controles.target;
  const base = new THREE.Vector3(alvo.x, 0, alvo.z);
  const ocupados = [...mundo.objetos.values()].map(o => {
    const b = new THREE.Box3().setFromObject(o);
    const c = b.getCenter(new THREE.Vector3()), s = b.getSize(new THREE.Vector3());
    return { c, r: Math.hypot(s.x, s.z) / 2 };
  });
  const passo = Math.max(20, raioNovo * 1.2);
  for (let k = 0; k < 24; k++) {
    const dz = ((k + 1) >> 1) * passo * (k % 2 ? -1 : 1);
    const p = new THREE.Vector3(base.x, 0, base.z + (k ? dz : 0));
    const bate = ocupados.some(o => Math.hypot(o.c.x - p.x, o.c.z - p.z) < (o.r + raioNovo) * 0.85);
    if (!bate) return p;
  }
  return base;
}

async function adicionar (tipo, slug, nome, ponto) {
  const d = novoObjeto(tipo, slug, nome);
  estado.objetos.push(d);
  mostrarCarga(`loading ${nome}…`, 0.4);
  await mundo.sincronizar(estado);
  esconderCarga();
  const o = mundo.objetos.get(d.id);
  if (o) {
    const b = new THREE.Box3().setFromObject(o);
    const s = b.getSize(new THREE.Vector3());
    const p = posicaoLivre(Math.hypot(s.x, s.z) / 2, ponto);
    d.pos = [+p.x.toFixed(3), 0, +p.z.toFixed(3)];
    mundo.aplicarTransformacoes(estado);
  }
  mundo.aplicarAmbiente(estado.ambiente);      // shadow frustum follows the scene
  editor.selecionar([d.id]);
  desenharOutliner();
  historico.registrar(`add ${nome}`, estado);
}

async function duplicar () {
  const sel = editor.selecionados;
  if (!sel.length) return;
  const novos = [];
  for (const d of sel) {
    const c = { ...clonar(d), id: novoObjeto(d.tipo, d.slug, d.nome).id };
    c.pos = [d.pos[0], d.pos[1], d.pos[2] + 50];
    estado.objetos.push(c);
    novos.push(c.id);
  }
  await mundo.sincronizar(estado);
  editor.selecionar(novos);
  desenharOutliner();
  historico.registrar(`duplicate ${sel.length}`, estado);
}

async function apagar () {
  const sel = editor.selecao;
  if (!sel.length) return;
  const n = sel.length;
  estado.objetos = estado.objetos.filter(o => !sel.includes(o.id));
  editor.selecao = [];
  await mundo.sincronizar(estado);
  editor.atualizarGizmo();
  desenharOutliner();
  sincronizarTransform();
  historico.registrar(`delete ${n}`, estado);
}

function aplicarRig (chave) {
  const r = RIGS[chave];
  Object.assign(estado.ambiente, { ...r.ambiente, sol: { ...estado.ambiente.sol, ...r.ambiente.sol } });
  Object.assign(estado.render, r.render);
  mundo.aplicarRender(estado.render);
  mundo.aplicarAmbiente(estado.ambiente);
  sincronizarInspetor();
  historico.registrar(`light rig: ${r.rotulo}`, estado);
}

async function aplicarSnapshot (s) {
  if (!s) return;
  substituirEstado(s);
  editor.selecao = editor.selecao.filter(id => estado.objetos.some(o => o.id === id));
  mundo.aplicarRender(estado.render);
  await mundo.sincronizar(estado);
  mundo.aplicarAmbiente(estado.ambiente);
  editor.atualizarGizmo();
  sincronizarInspetor();
  desenharOutliner();
  sincronizarTransform();
  $('nome-cena').value = estado.nome;
}

function atalho (nome) {
  switch (nome) {
    case 'desfazer': aplicarSnapshot(historico.desfazer()); break;
    case 'refazer': aplicarSnapshot(historico.refazer()); break;
    case 'duplicar': duplicar(); break;
    case 'apagar': apagar(); break;
    case 'chao': editor.aoChao(); break;
    case 'enquadrar-sel': {
      const b = mundo.caixaDe(editor.selecao);
      mundo.enquadrar(b || mundo.caixaTudo());
      break;
    }
    case 'enquadrar-tudo': mundo.enquadrar(mundo.caixaTudo()); break;
  }
}

/* -------------------------------------------------------------- outliner */

function desenharOutliner () {
  const el = $('outliner');
  el.textContent = '';
  $('cnt-obj').textContent = `${estado.objetos.length}`;
  if (!estado.objetos.length) { el.append(h('p.nota', {}, 'Empty. Click an asset on the left.')); return; }
  for (const d of estado.objetos) {
    const linha = h('div.linha', {
      onclick: e => {
        if (e.target.tagName === 'BUTTON') return;
        if (e.shiftKey || e.metaKey || e.ctrlKey) editor.alternar(d.id); else editor.selecionar([d.id]);
      },
    },
      h('span.tag', {}, d.tipo === 'aeronave' ? 'AC' : 'PR'),
      h('span.rot', { title: d.slug }, d.nome),
      h('button.mini', { title: d.visivel ? 'hide' : 'show', onclick: () => editor.ocultar(d.id, d.visivel) }, d.visivel ? '👁' : '⃠'),
      h('button.mini', { title: d.travado ? 'unlock' : 'lock', onclick: () => editor.travar(d.id, !d.travado) }, d.travado ? '🔒' : '🔓'));
    if (editor.selecao.includes(d.id)) linha.classList.add('sel');
    el.append(linha);
  }
}

/* ------------------------------------------------------------- transform */

function sincronizarTransform () {
  const sel = editor.selecionados;
  const campos = $('campos-transform'), vazio = $('sem-selecao');
  if (sel.length !== 1) {
    campos.hidden = true;
    vazio.hidden = false;
    vazio.textContent = sel.length
      ? `${sel.length} objects selected — drag the gizmo, or select one to type numbers.`
      : 'Nothing selected. Click an object in the viewport, or a row in the outliner.';
    return;
  }
  const d = sel[0];
  campos.hidden = false; vazio.hidden = true;
  const set = (id, v) => { const e = $(id); if (document.activeElement !== e) e.value = +v.toFixed(3); };
  set('tx', d.pos[0]); set('ty', d.pos[1]); set('tz', d.pos[2]);
  set('rx', d.rot[0]); set('ry', d.rot[1]); set('rz', d.rot[2]);
  set('sx', d.esc[0]); set('sy', d.esc[1]); set('sz', d.esc[2]);

  const o = mundo.objetos.get(d.id);
  if (o) {
    const b = new THREE.Box3().setFromObject(o), s = b.getSize(new THREE.Vector3());
    const a = d.tipo === 'aeronave' ? acharAsset(d.slug) : null;
    $('medidas-sel').textContent =
      `${s.x.toFixed(2)} × ${s.y.toFixed(2)} × ${s.z.toFixed(2)} m (world bbox)`
      + (a ? `\n${a.matricula} · ${a.triangulos.toLocaleString()} tris · ${a.materiais} materials` : '')
      + `\nlowest point y = ${b.min.y.toFixed(3)} m`;
  }
}

function ligarTransform () {
  const ids = ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz'];
  for (const id of ids) {
    const e = $(id);
    e.addEventListener('input', () => {
      const d = editor.selecionados[0];
      if (!d) return;
      const v = parseFloat(e.value);
      if (!isFinite(v)) return;
      const k = id[0] === 't' ? 'pos' : id[0] === 'r' ? 'rot' : 'esc';
      const i = { x: 0, y: 1, z: 2 }[id[1]];
      d[k][i] = v;
      mundo.aplicarTransformacoes(estado);
      editor.atualizarGizmo();
    });
    // One entry per committed edit: typing digits fires many `input` events
    // and exactly one `change` when the field is left or Enter is pressed.
    e.addEventListener('change', () => {
      historico.registrar('edit transform', estado);
      sincronizarTransform();
    });
  }
  const snap = () => editor.snap(+$('snap-mov').value, +$('snap-rot').value);
  $('snap-mov').addEventListener('change', snap);
  $('snap-rot').addEventListener('change', snap);
}

/* ------------------------------------------------------------- inspector */

function ligarInspetor () {
  document.querySelectorAll('.bloco h3').forEach(t =>
    t.addEventListener('click', () => {
      const b = t.parentElement;
      b.dataset.aberto = b.dataset.aberto === '1' ? '0' : '1';
    }));

  ligarTransform();

  $('btn-dup').addEventListener('click', duplicar);
  $('btn-del').addEventListener('click', apagar);
  $('btn-chao').addEventListener('click', () => editor.aoChao());

  /* camera */
  $('fov').addEventListener('input', e => {
    const v = +e.target.value;
    $('fov-out').textContent = v;
    estado.camera.fov = v;
    mundo.camP.fov = v; mundo.camP.updateProjectionMatrix(); mundo.atualizarOrto();
  });
  $('orto').addEventListener('change', e => { estado.camera.orto = e.target.checked; mundo.usarOrto(e.target.checked); editor.gizmo.camera = mundo.cam; });
  $('btn-pose-a').addEventListener('click', () => guardarPose('A'));
  $('btn-pose-b').addEventListener('click', () => guardarPose('B'));

  /* sun & sky */
  const amb = (id, cam, saida, transformar = v => v) => {
    const e = $(id);
    const aplicar = () => {
      const v = transformar(e.type === 'checkbox' ? e.checked : (e.type === 'color' ? e.value : (isNaN(+e.value) ? e.value : +e.value)));
      cam(v);
      if (saida) $(saida).textContent = typeof v === 'number' ? (v % 1 ? v.toFixed(2) : v) : v;
      mundo.aplicarAmbiente(estado.ambiente);
    };
    e.addEventListener('input', aplicar);
    e.addEventListener('change', aplicar);
  };
  amb('sol-elev', v => (estado.ambiente.sol.elev = v), 'sol-elev-out');
  amb('sol-azim', v => (estado.ambiente.sol.azim = v), 'sol-azim-out');
  amb('sol-int', v => (estado.ambiente.sol.intensidade = v), 'sol-int-out');
  amb('sol-cor', v => (estado.ambiente.sol.cor = v));
  amb('env-preset', v => (estado.ambiente.envPreset = v));
  amb('env-int', v => (estado.ambiente.envIntensidade = v), 'env-int-out');
  amb('fundo', v => (estado.ambiente.fundo = v));
  amb('fundo-cor', v => (estado.ambiente.fundoCor = v));
  amb('neblina', v => (estado.ambiente.neblina.ligado = v));
  amb('neblina-d', v => (estado.ambiente.neblina.densidade = v), 'neblina-d-out');
  amb('chao-on', v => (estado.ambiente.chao.ligado = v));
  amb('chao-tipo', v => (estado.ambiente.chao.tipo = v));
  amb('chao-tam', v => (estado.ambiente.chao.tamanho = v), 'chao-tam-out');
  amb('grade-on', v => (estado.ambiente.grade = v));

  /* render */
  const ren = (id, cam, saida) => {
    const e = $(id);
    const aplicar = () => {
      const v = e.type === 'checkbox' ? e.checked : (isNaN(+e.value) ? e.value : +e.value);
      cam(v);
      if (saida) $(saida).textContent = typeof v === 'number' ? v.toFixed(v % 1 ? 2 : 1) : v;
      mundo.aplicarRender(estado.render);
    };
    e.addEventListener('input', aplicar);
    e.addEventListener('change', aplicar);
  };
  ren('tone', v => (estado.render.tone = v));
  ren('exposicao', v => (estado.render.exposicao = v), 'exposicao-out');
  ren('sombras', v => (estado.render.sombras = v));
  ren('sombra-px', v => (estado.render.sombraPx = v));
  ren('aa', v => (estado.render.aa = v));
  ren('pr', v => (estado.render.pixelRatioMax = v), 'pr-out');

  /* One undo step per committed setting. A slider drag fires a stream of
     `input` events and a single `change` when the thumb is released, so the
     whole drag collapses into one entry — which is what a user expects. */
  document.querySelectorAll('#inspetor input, #inspetor select').forEach(e => {
    if (e.closest('#campos-transform')) return;
    e.addEventListener('change', () => historico.registrar('scene setting', estado));
  });
}

function guardarPose (qual) {
  estado.poses[qual] = mundo.poseAtual(mundo.camP.fov, mundo.cam === mundo.camO);
  $('poses-info').innerHTML =
    `A ${estado.poses.A ? '<b>stored</b>' : '—'} · B ${estado.poses.B ? '<b>stored</b>' : '—'} — `
    + 'the endpoints of the “camera path” GIF.';
}

function sincronizarInspetor () {
  const a = estado.ambiente, r = estado.render;
  const p = (id, v) => { const e = $(id); if (e.type === 'checkbox') e.checked = !!v; else e.value = v; };
  p('sol-elev', a.sol.elev); $('sol-elev-out').textContent = a.sol.elev;
  p('sol-azim', a.sol.azim); $('sol-azim-out').textContent = a.sol.azim;
  p('sol-int', a.sol.intensidade); $('sol-int-out').textContent = a.sol.intensidade;
  p('sol-cor', a.sol.cor);
  p('env-preset', a.envPreset);
  p('env-int', a.envIntensidade); $('env-int-out').textContent = (+a.envIntensidade).toFixed(2);
  p('fundo', a.fundo); p('fundo-cor', a.fundoCor);
  p('neblina', a.neblina.ligado);
  p('neblina-d', a.neblina.densidade); $('neblina-d-out').textContent = a.neblina.densidade;
  p('chao-on', a.chao.ligado); p('chao-tipo', a.chao.tipo);
  p('chao-tam', a.chao.tamanho); $('chao-tam-out').textContent = a.chao.tamanho;
  p('grade-on', a.grade);
  p('tone', r.tone);
  p('exposicao', r.exposicao); $('exposicao-out').textContent = (+r.exposicao).toFixed(2);
  p('sombras', r.sombras); p('sombra-px', r.sombraPx); p('aa', r.aa);
  p('pr', r.pixelRatioMax); $('pr-out').textContent = (+r.pixelRatioMax).toFixed(1);
  p('fov', estado.camera.fov); $('fov-out').textContent = estado.camera.fov;
  p('orto', estado.camera.orto);
  guardarPoseTexto();
}
function guardarPoseTexto () {
  $('poses-info').innerHTML =
    `A ${estado.poses.A ? '<b>stored</b>' : '—'} · B ${estado.poses.B ? '<b>stored</b>' : '—'} — `
    + 'the endpoints of the “camera path” GIF.';
}

/* ------------------------------------------------------------------- bar */

function atualizarBotoesHistorico () {
  const u = $('btn-undo'), r = $('btn-redo');
  u.disabled = !historico.podeDesfazer;
  r.disabled = !historico.podeRefazer;
  u.title = historico.podeDesfazer ? `Undo ${historico.rotuloDesfazer} (Ctrl+Z)` : 'Nothing to undo';
  r.title = historico.podeRefazer ? `Redo ${historico.rotuloRefazer} (Ctrl+Shift+Z)` : 'Nothing to redo';
}

function ligarBarra () {
  $('btn-undo').addEventListener('click', () => atalho('desfazer'));
  $('btn-redo').addEventListener('click', () => atalho('refazer'));
  $('nome-cena').addEventListener('change', e => { estado.nome = e.target.value.trim() || 'untitled scene'; });
  $('btn-salvar').addEventListener('click', () => {
    estado.nome = $('nome-cena').value.trim() || 'untitled scene';
    Object.assign(estado.camera, {
      pos: mundo.camP.position.toArray().map(n => +n.toFixed(3)),
      alvo: mundo.controles.target.toArray().map(n => +n.toFixed(3)),
      fov: mundo.camP.fov, orto: mundo.cam === mundo.camO,
    });
    const n = salvarCena(estado);
    desenharCenas();
    document.querySelector('#abas-lateral .aba:nth-child(2)').click();
    if (!n) alert('Could not save — the browser refused localStorage (private window?).');
  });
  $('btn-exportar').addEventListener('click', () =>
    dlgExportar({ mundo, estado, editor, carregarDocumento }));
  $('btn-sobre').addEventListener('click', dlgLicenca);
  $('modal-fechar').addEventListener('click', fecharModal);

  document.querySelectorAll('#abas-lateral .aba').forEach(b =>
    b.addEventListener('click', () => {
      document.querySelectorAll('#abas-lateral .aba').forEach(x => x.classList.toggle('ativa', x === b));
      document.querySelectorAll('#lateral .painel').forEach(p => p.classList.toggle('ativo', p.id === b.dataset.alvo));
    }));

  $('btn-cena-nova').addEventListener('click', () => carregarDocumento(estadoPadrao()));
  $('btn-cena-importar').addEventListener('click', () =>
    dlgExportar({ mundo, estado, editor, carregarDocumento }, 'JSON'));
}

function ligarHud () {
  document.querySelectorAll('#hud-cameras button').forEach(b =>
    b.addEventListener('click', () => {
      if (b.dataset.vista) {
        const alvo = editor.selecao.length ? mundo.caixaDe(editor.selecao) : null;
        mundo.vista(b.dataset.vista, alvo || mundo.caixaTudo());
      } else atalho(b.dataset.acao);
    }));

  document.querySelectorAll('#hud-gizmo button[data-modo]').forEach(b =>
    b.addEventListener('click', () => {
      editor.modo(b.dataset.modo);
      document.querySelectorAll('#hud-gizmo button[data-modo]').forEach(x => x.classList.toggle('ativo', x === b));
    }));
  const bEspaco = document.querySelector('#hud-gizmo button[data-espaco]');
  bEspaco.addEventListener('click', () => {
    const novo = editor.gizmo.space === 'world' ? 'local' : 'world';
    editor.espaco(novo);
    bEspaco.textContent = novo;
  });
}

/* ------------------------------------------------------------ drag & drop */

function ligarArrastar () {
  const el = $('palco');
  el.addEventListener('dragover', e => { e.preventDefault(); e.dataTransfer.dropEffect = 'copy'; });
  el.addEventListener('drop', e => {
    e.preventDefault();
    const dados = e.dataTransfer.getData('text/plain');
    if (!dados) return;
    const [tipo, slug, ...resto] = dados.split(':');
    const r = mundo.renderer.domElement.getBoundingClientRect();
    const p = new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    const ray = new THREE.Raycaster();
    ray.setFromCamera(p, mundo.cam);
    const ponto = new THREE.Vector3();
    const acertou = ray.ray.intersectPlane(new THREE.Plane(new THREE.Vector3(0, 1, 0), 0), ponto);
    adicionar(tipo, slug, resto.join(':'), acertou ? ponto : null);
  });
}

/* ----------------------------------------------------------- status line */

let quadros = 0, t0 = performance.now();
function contarQuadro () {
  quadros++;
  const agora = performance.now();
  if (agora - t0 < 500) return;
  const fps = quadros * 1000 / (agora - t0);
  quadros = 0; t0 = agora;
  const s = mundo.estatisticas();
  $('status').textContent =
    `${fps.toFixed(0)} fps · ${estado.objetos.length} objects · `
    + `${s.triangulos.toLocaleString()} tris · ${s.chamadas} draw calls · `
    + `${formatarBytes(bytesCarregados())} of GLB loaded`
    + (falhas.length ? `\n${falhas.length} asset(s) failed — see the console` : '');
}

addEventListener('error', e => { falhas.push(e.message); });

iniciar().catch(e => {
  console.error(e);
  document.getElementById('status').textContent = 'boot failed: ' + e.message;
});
