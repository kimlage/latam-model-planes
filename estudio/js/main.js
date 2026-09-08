/* main.js — boot and wiring.
 *
 * Reads the fleet manifest, builds the world, binds every control in the two
 * side columns to the scene document, and owns the render loop. Anything with
 * real logic lives in its own module; this file is the switchboard.
 */

import * as THREE from 'three';
import { estadoPadrao, novoObjeto, clonar, Historico, lerBiblioteca, salvarCena, apagarCena, renomearCena, nomeLivre, lerSessao, salvarSessao, arquivarSessao } from './estado.js';
import { carregarManifesto, carregarCenarios, catalogo, miniatura, bytesCarregados,
         acharAsset, LICENCAS, CATEGORIAS, ORDEM_CATEGORIAS, CAMPOS,
         ORDEM_NIVEIS, NIVEL_PADRAO, ROTULOS_NIVEL } from './frota.js';
import { PROPS, RIGS } from './props.js';
import { Mundo } from './mundo.js';
import { Editor } from './editor.js';
import { CENAS_BASE, ROTULOS_BASE, cenaBase } from './cenas.js';
import { PRODUCOES, carregarProducao } from './producoes.js';
import { dlgDiretor, gravarEnquadramento } from './diretor.js';
import { h, dlgExportar, dlgLicenca, dlgMovimento, dlgVoo, fecharModal } from './dialogos.js';
import { formatarBytes } from './exportar.js';
import { linhaPadrao, avaliar, temAnimacao, podar, porChave, acharTrilha, encaixar } from './tempo.js';
import { Dock } from './tempoui.js';
import { normalizarDocumento } from './documento.js';
import { ligarInterface, atalhoBloqueado, avisarUsuario } from './interface.js';

const $ = id => document.getElementById(id);

let estado = estadoPadrao();
const historico = new Historico();
let mundo, editor, dock;
let falhas = [];
let carregando = false, pronto = false, timerSessao, ultimaSessao = '', protegido = true;
let permitirSessao = true;

function preservarSessao () {
  if (!pronto || carregando) return true;
  const doc = clonar(estado);
  // A timeline camera is an evaluated frame, never the saved rest camera.
  if (!estado.linha.trilhas.some(t => t.canal.startsWith('camera.') && t.chaves.length && !t.mudo))
    doc.camera = mundo.poseAtual(mundo.camP.fov, mundo.cam === mundo.camO);
  delete doc.vista; delete doc.quadro; delete doc.assentar;
  const texto = JSON.stringify(doc);
  if (texto === ultimaSessao) return protegido;
  protegido = permitirSessao && salvarSessao(doc);
  const el = $('estado-salvo');
  el.textContent = protegido ? 'Session saved' : 'Session not saved';
  el.classList.toggle('erro', !protegido);
  el.title = protegido ? 'Recovered automatically on this browser. Save scene creates a named library copy.' : 'Browser storage unavailable. Export a JSON backup.';
  if (protegido) ultimaSessao = texto;
  return protegido;
}
function agendarSessao () {
  if (!pronto || carregando) return;
  $('estado-salvo').textContent = 'Saving…';
  clearTimeout(timerSessao);
  timerSessao = setTimeout(preservarSessao, 500);
}
function registrarCamera (rotulo) {
  estado.camera = mundo.poseAtual(mundo.camP.fov, mundo.cam === mundo.camO);
  historico.registrar(rotulo, estado);
}

/* ------------------------------------------------------------------ boot */

async function iniciar () {
  ligarInterface();
  mundo = new Mundo($('viewport'));
  editor = new Editor(mundo, estado, historico);

  editor.aoMudarSelecao = () => { desenharOutliner(); sincronizarTransform(); };
  editor.aoMudarTransformacao = () => sincronizarTransform();
  editor.aoMudarDoc = () => atualizarBotoesHistorico();
  editor.aoAtalho = atalho;
  editor.aoAutoChave = autoChave;
  editor.aoAutoChaveCanal = autoChaveCanal;
  historico.aoMudar = () => { atualizarBotoesHistorico(); agendarSessao(); };

  ligarTempo();
  ligarInspetor();
  ligarBarra();
  ligarHud();
  ligarArrastar();

  let nAero = 0, nCen = 0;
  try {
    nAero = (await carregarManifesto()).n;
  } catch (e) {
    $('lista-assets').innerHTML =
      `<p class="nota" style="color:#ff8f8f">${e.message}<br><br>Run
       <code>python3 -m http.server 8000</code> in the repository root and open
       <code>/estudio/</code>.</p>`;
    console.error(e);
  }
  /* The airport tier is optional on purpose: a checkout without
     export/cenarios/ still runs, it just has no airports. It never throws. */
  nCen = (await carregarCenarios()).n;
  nCen += (await carregarCenarios('ambientes')).n;
  $('cnt-frota').textContent =
    `${nAero} aircraft · ${nCen} airport assets · ${Object.keys(PROPS).length} authored props`;
  construirBiblioteca();

  mundo.aplicarRender(estado.render);
  mundo.aplicarAmbiente(estado.ambiente);
  sincronizarInspetor();
  historico.iniciar(estado);

  let relogio = performance.now();
  mundo.iniciarLoop(() => {
    const agora = performance.now();
    const dt = Math.min(0.25, (agora - relogio) / 1000);
    relogio = agora;
    if (dock.avancar(dt)) sincronizarTransform();
    const ov = aplicarTempo();
    /* OrbitControls.update() recomputes the camera from its own spherical
       state and would overwrite whatever the camera track just set — the same
       collision the GIF exporter avoids by pausing the loop. While the
       timeline owns the camera, the controls do not get a turn. */
    if (!(ov && ov.camera)) mundo.controles.update();
    mundo.render();
    contarQuadro();
  });

  /* Debug handle. Deliberate: it is how this page was driven and verified from
     the console, and it is the only way to script the studio from outside.
     `estado` is a GETTER because carregarDocumento REPLACES the object — a
     plain reference here went stale the moment a scene was opened, which made
     every console measurement read the scene before last. */
  window.__estudio = {
    get estado () { return estado; },
    mundo, editor, historico, get dock () { return dock; },
    carregarDocumento, adicionar, atalho, aplicarTempo,
    registrar: r => historico.registrar(r, estado),

    /* MEASUREMENT, not control. Two questions about the hero tier cannot be
       answered by hand at all: how long a GLB takes to arrive, and what the
       renderer really costs per frame with a 6 km field plate on screen. Both
       had to be measured in a browser rather than argued about, and the numbers
       in export/README.md come from here.

       `medirRender` counts real milliseconds around N draws with a gl.finish()
       at each end, which is the honest way to time WebGL — and, unlike counting
       requestAnimationFrame callbacks, it still works when the tab is in the
       background, where the browser throttles rAF to about 1 Hz. */
    medirRender: (n = 60) => {
      const gl = mundo.renderer.getContext();
      mundo.render(); gl.finish();
      const t0 = performance.now();
      for (let i = 0; i < n; i++) mundo.render();
      gl.finish();
      const ms = (performance.now() - t0) / n;
      return { ms: +ms.toFixed(2), fps: +(1000 / ms).toFixed(1),
               px: [mundo.largura, mundo.altura],
               tri: mundo.renderer.info.render.triangles,
               draws: mundo.renderer.info.render.calls };
    },
  };

  // Open on something worth looking at rather than an empty grid.
  const sessao = lerSessao();
  if (sessao) {
    try { await carregarDocumento(sessao); avisarUsuario('Your previous session was restored.'); }
    catch (e) {
      permitirSessao = arquivarSessao();
      avisarUsuario(`Recovery failed: ${e.message} ${permitirSessao ? 'Original session preserved in browser recovery storage.' : 'Original session kept; automatic saving is paused.'}`, true);
      await carregarDocumento(cenaBase('heroi'));
    }
  } else await carregarDocumento(cenaBase('heroi'));
  pronto = true;
  preservarSessao();
  const producaoInicial = new URLSearchParams(location.search).get('producao');
  if (PRODUCOES.some(p=>p.id===producaoInicial)) {
    await abrirCena(await carregarProducao(producaoInicial));
    document.querySelector('[data-alvo="pnl-scenes"]')?.click();
  }
  if (new URLSearchParams(location.search).get('loading') === 'cinema') {
    try {
      const { criarCenaCinema } = await import('../loading/cenas-cinema.js');
      const { lerParametros } = await import('../loading/catalogo.js');
      await abrirCena(await criarCenaCinema(lerParametros()));
      document.querySelector('[data-alvo="pnl-scenes"]')?.click();
    } catch(e) { avisarUsuario(e.message, true); }
  }
  // Pointer-up captures camera drags, including the final damped pose.
  mundo.controles.addEventListener('end', () => {
    if (!temAnimacao(estado.linha)) {
      estado.camera = mundo.poseAtual(mundo.camP.fov, mundo.cam === mundo.camO);
      historico.registrar('camera orbit', estado);
    }
    agendarSessao();
  });
  addEventListener('pagehide', preservarSessao);
  document.addEventListener('visibilitychange', () => { if (document.hidden) preservarSessao(); });
  addEventListener('beforeunload', e => {
    if (!preservarSessao()) { e.preventDefault(); e.returnValue = ''; }
  });
  document.addEventListener('input', agendarSessao);
}

/* ------------------------------------------------------------- timeline --
 *
 * The dock edits `estado.linha`; this file owns everything that has to happen
 * around an edit — one history entry per action, a re-evaluation after it, and
 * the rule that SCRUBBING IS NOT AN EDIT. */

function ligarTempo () {
  dock = new Dock($('tempo'), {
    estado, mundo, editor,
    aoMudar: rot => { historico.registrar(rot, estado); },
    aoTempo: () => { aplicarTempo(); sincronizarTransform(); },
    aoParar: () => mundo.controles.update(),      // resync the orbit state
    aoChavear: () => chavearSelecao(),
    aoChavearCamera: () => chavearCamera(),
    aoPreset: () => dlgMovimento(ctxDialogo()),
    aoDiretor: () => dlgDiretor(ctxDialogo()),
    aoVooPainel: v => dlgVoo(ctxDialogo(), v),
  });

  const alt = $('tempo-alternar');
  alt.addEventListener('click', () => alternarDock());
  addEventListener('keydown', e => {
    if (atalhoBloqueado(e)) return;
    const a = e.target;
    if (a && (a.tagName === 'INPUT' || a.tagName === 'SELECT' || a.tagName === 'TEXTAREA')) return;
    if (e.metaKey || e.ctrlKey) return;
    if (e.key === ' ') { e.preventDefault(); dock.alternarTocar(); }
    else if (e.key === 'ArrowRight') { e.preventDefault(); dock.parar(); dock.passo(e.shiftKey ? 10 : 1); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); dock.parar(); dock.passo(e.shiftKey ? -10 : -1); }
    else if (e.key === 'Home') { dock.parar(); dock.irPara(0); }
    else if (e.key === 'End') { dock.parar(); dock.irPara(estado.linha.duracao); }
    else if (e.key.toLowerCase() === 'k') { e.shiftKey ? chavearCamera() : chavearSelecao(); }
    else if (e.key.toLowerCase() === 't') { alternarDock(); }
    else if (e.key === 'Delete' || e.key === 'Backspace') {
      /* A selected KEY wins over a selected object: you just clicked the key. */
      if (dock.chaveSel && dock.apagarSelecionada()) { e.preventDefault(); e.stopImmediatePropagation(); }
    }
  }, true);
}

function alternarDock () {
  const p = $('palco');
  p.classList.toggle('sem-tempo');
  $('tempo-alternar').textContent = p.classList.contains('sem-tempo') ? '▴ timeline' : '▾ timeline';
}

const ctxDialogo = () => ({ mundo, estado, editor, dock, carregarDocumento,
  registrar: rot => historico.registrar(rot, estado),
  redesenhar: () => { podar(estado); dock.desenhar(); aplicarTempo(); desenharOutliner(); } });

/** Evaluate the timeline onto the world. Returns the overlay, or null when the
 *  scene has no animation — in which case nothing here costs anything. */
function aplicarTempo () {
  if (!dock) return null;
  /* Not while a gizmo is being dragged: the overlay would put the object back
     where the keys say it is on every frame and the drag would do nothing at
     all, which is a bug that looks exactly like a broken mouse. */
  if (editor && editor.gizmo && editor.gizmo.dragging) return null;
  if (!temAnimacao(estado.linha)) { dock.mostrarVoo(null); return null; }
  const ov = avaliar(estado, dock.t, id => mundo.contextoVoo(id, estado));
  if (dock.cameraLivre) ov.camera = null;
  mundo.aplicarTransformacoes(estado);
  mundo.aplicarLinha(estado, ov);
  let info = null;
  for (const [, v] of ov.objetos) if (v.voo) info = v.voo;
  dock.mostrarVoo(info);
  editor.atualizarCaixa && editor.atualizarCaixa();
  /* The overlay writes the camera directly, which does NOT fire OrbitControls'
     change event — without this the numeric camera rows would freeze at the
     last hand-driven pose while the clip flew past behind them. */
  if (ov.camera) sincronizarCamera();
  return ov;
}

/* Which channels a drag on an object touches. */
const CANAIS_OBJ = [['objeto.pos', 'pos'], ['objeto.rot', 'rot'], ['objeto.esc', 'esc']];

/**
 * Auto-key, and the one rule that is not the DCC default:
 *
 *   auto-key ON  — a move writes keys on position, rotation and scale, starting
 *                  the tracks if they do not exist.
 *   auto-key OFF — a move on a channel that is ALREADY animated still writes a
 *                  key, because otherwise the next frame re-evaluates the track
 *                  and the drag is silently thrown away. A channel with no keys
 *                  is left alone and just edits the rest pose.
 *
 * Blender discards that drag. This studio does not, because there is no
 * F-curve editor here to explain what happened to it.
 */
function autoChave (ids) {
  const l = estado.linha;
  if (!l) return;
  let escreveu = 0;
  for (const id of ids || []) {
    const d = estado.objetos.find(o => o.id === id);
    if (!d) continue;
    for (const [canal, campo] of CANAIS_OBJ) {
      const jaTem = !!acharTrilha(l, canal, id);
      if (!l.autochave && !jaTem) continue;
      porChave(l, canal, id, dock.t, d[campo].slice());
      escreveu++;
    }
  }
  if (escreveu) { dock.desenhar(); aplicarTempo(); }
  return escreveu;
}

/** The camera, keyed from the viewport at the playhead.
 *
 *  Position and target always; FOV only if a `camera.fov` track already exists,
 *  because writing one silently pins the FOV for the whole clip and the FOV
 *  slider would then appear to do nothing.
 *
 *  This is the counterpart of `chavearSelecao` and it exists because a recipe's
 *  framing is a STARTING POINT. `cameraParaVoo` puts the lens 1.75 aircraft
 *  lengths abeam the lift-off point, which is a good guess and was the wrong
 *  one for the GRU field clip — the shot wanted to be closer and lower, with
 *  the hangar behind. Without this button the only way to change it was to
 *  edit the JSON. */
function chavearCamera () {
  if (gravarEnquadramento(ctxDialogo())) { avisar('Enquadramento gravado no plano.'); return; }
  if (estado.linha.planos?.length) { avisar('Abra Câmeras e escolha Enquadrar início ou fim.'); return; }
  const l = estado.linha;
  const t = dock.t;
  porChave(l, 'camera.pos', null, encaixar(l, t),
    mundo.camP.position.toArray().map(n => +n.toFixed(3)));
  porChave(l, 'camera.alvo', null, encaixar(l, t),
    mundo.controles.target.toArray().map(n => +n.toFixed(3)));
  if (acharTrilha(l, 'camera.fov', null)) {
    porChave(l, 'camera.fov', null, encaixar(l, t), +mundo.camP.fov.toFixed(2));
  }
  historico.registrar(`key camera @ ${t.toFixed(2)} s`, estado);
  dock.desenhar();
  aplicarTempo();
  avisar(`camera keyed at ${t.toFixed(2)} s`);
}

/** One channel, same rule: start a track only with auto-key on, but keep an
 *  already-animated channel honest. */
function autoChaveCanal (id, canal, valor) {
  const l = estado.linha;
  if (!l) return 0;
  if (!l.autochave && !acharTrilha(l, canal, id)) return 0;
  porChave(l, canal, id, dock.t, valor, 'segurar');
  dock.desenhar();
  aplicarTempo();
  return 1;
}

/** The explicit key button: position, rotation and scale of the selection. */
function chavearSelecao () {
  const sel = editor.selecionados;
  if (!sel.length) { avisar('Select something first — “key” writes the selection’s transform.'); return; }
  for (const d of sel) for (const [canal, campo] of CANAIS_OBJ) {
    porChave(estado.linha, canal, d.id, dock.t, d[campo].slice());
  }
  historico.registrar(`key ${sel.length} object(s)`, estado);
  dock.desenhar();
  aplicarTempo();
}

let avisoT = null;
function avisar (txt) {
  const s = $('status');
  s.dataset.aviso = txt;
  clearTimeout(avisoT);
  avisoT = setTimeout(() => { delete s.dataset.aviso; }, 4000);
}

/* -------------------------------------------------------------- sidebar */

/* The sidebar is built from the manifests, in this order:
 *
 *   catalogo   every GLB — the 11 aircraft (export/manifest.json) and the 46
 *              airport pieces (export/cenarios/manifest.json), each carrying
 *              its own `categoria` and `licenca`
 *   PROPS      the authored boxes and slabs in js/props.js, tagged with the
 *              same category vocabulary so both sets land in the same sections
 *
 * Nothing about the sections is written here except their order. A category the
 * scenery manifest invents tomorrow appears at the end of the list rather than
 * silently dropping its assets on the floor. */

function rotuloCategoria (c) {
  return CATEGORIAS[c] || c;
}

/** A share-alike badge, or nothing. It is the licence fact a composer needs to
 *  see BEFORE placing a piece, not after exporting. */
function selo (licId) {
  const l = LICENCAS[licId];
  if (!l || !l.share_alike) return null;
  return h('span.lic', { title: `${l.nome} — ${l.atribuicao}` }, 'ODbL');
}

function cartaoAsset (a) {
  const img = h('img.thumb', { alt: '' });
  miniatura(a.slug).then(u => { if (u) img.src = u; }).catch(() => {});
  const grande = Math.max(a.L, a.env) >= 300;
  const dim = a.L ? `${a.L.toFixed(a.L < 100 ? 1 : 0)} × ${a.env.toFixed(a.env < 100 ? 1 : 0)} m` : '';
  const sub = a.tipo === 'aeronave'
    ? `${a.matricula} · ${a.L.toFixed(1)} m · ${(a.triangulos / 1000).toFixed(0)}k tris`
    : `${dim} · ${(a.triangulos / 1000).toFixed(a.triangulos < 1000 ? 2 : 0)}k tris`;
  const card = h('div.card', {
    draggable: 'true',
    title: [`${a.nome}${a.matricula && a.tipo === 'aeronave' ? ' · ' + a.matricula : ''}`,
            `${a.L.toFixed(2)} × ${a.H.toFixed(2)} × ${a.env.toFixed(2)} m (L × H × span)`,
            `${a.triangulos.toLocaleString()} triangles · ${formatarBytes(a.bytes)}`,
            a.campo ? `field ${a.campo.toUpperCase()} — ${(CAMPOS[a.campo] || {}).rotulo || ''}` : '',
            a.datum === 'campo' ? 'datum: runway threshold at y = 0 — the plate goes below zero on purpose' : '',
            LICENCAS[a.licenca] ? LICENCAS[a.licenca].atribuicao : '',
            a.nota || ''].filter(Boolean).join('\n'),
    onclick: () => adicionar(a.tipo, a.slug, a.nome),
    ondragstart: e => e.dataTransfer.setData('text/plain', `${a.tipo}:${a.slug}:${a.nome}`),
  },
    img,
    h('div', {},
      h('div.n', {}, a.nome),
      h('div.m', {}, sub, grande ? h('b.grande', { title: 'wider than 300 m — it is a backdrop, not a building block' }, ' ▮ large') : null),
      selo(a.licenca)));
  card.dataset.busca = [a.nome, a.slug, a.matricula, a.campo, a.categoria,
                        rotuloCategoria(a.categoria), a.licenca, a.nota]
    .filter(Boolean).join(' ').toLowerCase();
  return card;
}

function cartaoProp (slug, def) {
  const card = h('div.card', {
    draggable: 'true',
    title: `${def.rotulo} — ${def.medidas}\nAuthored in estudio/js/props.js. `
         + `CC BY 4.0, no survey data.`,
    onclick: () => adicionar('prop', slug, def.rotulo),
    ondragstart: e => e.dataTransfer.setData('text/plain', `prop:${slug}:${def.rotulo}`),
  },
    h('div.thumb', { style: 'display:grid;place-items:center;color:#5c6478;font-size:18px' }, '▦'),
    h('div', {}, h('div.n', {}, def.rotulo), h('div.m', {}, def.medidas)));
  card.dataset.busca = `${def.rotulo} ${slug} ${def.categoria} `
    + `${rotuloCategoria(def.categoria)} authored prop generic`.toLowerCase();
  return card;
}

function construirBiblioteca () {
  const grupos = new Map();
  const por = (c, n) => { if (!grupos.has(c)) grupos.set(c, []); grupos.get(c).push(n); };

  for (const a of catalogo) por(a.categoria || 'aeronave', cartaoAsset(a));
  for (const [slug, def] of Object.entries(PROPS)) por(def.categoria || 'adereco', cartaoProp(slug, def));

  const ordem = [...ORDEM_CATEGORIAS.filter(c => grupos.has(c)),
                 ...[...grupos.keys()].filter(c => !ORDEM_CATEGORIAS.includes(c))];

  const raiz = $('lista-assets');
  raiz.textContent = '';
  for (const c of ordem) {
    const cards = grupos.get(c);
    const lista = h('div.lista-cards', { 'data-cat': c }, cards);
    raiz.append(h('h3', { 'data-cat': c }, rotuloCategoria(c), h('small', {}, ` ${cards.length}`)), lista);
  }

  const lr = $('lista-rigs');
  lr.textContent = '';
  for (const [chave, r] of Object.entries(RIGS)) {
    const card = h('div.card', { title: r.desc, onclick: () => aplicarRig(chave) },
      h('div.thumb', { style: 'display:grid;place-items:center;color:#c9a24a;font-size:18px' }, '☀'),
      h('div', {}, h('div.n', {}, r.rotulo), h('div.m', {}, r.desc)));
    card.dataset.busca = `${r.rotulo} ${r.desc} light rig`;
    lr.append(card);
  }

  /* One filter box over every section. A heading whose whole section is hidden
     hides too, otherwise the sidebar fills with empty titles. */
  for (const c of ordem) $('filtro-categoria').append(h('option', { value: c }, rotuloCategoria(c)));
  const filtrar = () => {
    const q = $('busca').value.trim().toLowerCase();
    const categoria = $('filtro-categoria').value;
    document.querySelectorAll('.card').forEach(cd =>
      cd.classList.toggle('oculto', (!!q && !(cd.dataset.busca || '').includes(q)) || (!!categoria && cd.closest('[data-cat]')?.dataset.cat !== categoria)));
    document.querySelectorAll('#lista-assets .lista-cards').forEach(l => {
      const vivos = [...l.children].filter(cd => !cd.classList.contains('oculto')).length;
      l.classList.toggle('oculto', vivos === 0);
      const t = l.previousElementSibling;
      if (t && t.tagName === 'H3') {
        t.classList.toggle('oculto', vivos === 0);
        t.querySelector('small').textContent = ` ${vivos}`;
      }
    });
    $('busca-vazia').hidden = !!document.querySelector('#lista-assets .card:not(.oculto)');
    $('lista-rigs').previousElementSibling.hidden = !!categoria || !document.querySelector('#lista-rigs .card:not(.oculto)');
  };
  $('busca').addEventListener('input', filtrar);
  $('filtro-categoria').addEventListener('change', filtrar);

  desenharCenas();
}

function desenharCenas () {
  const producoes = $('lista-producoes');
  producoes.replaceChildren();
  for (const p of PRODUCOES) producoes.append(h('button.producao', {
    onclick: async () => {
      try { await abrirCena(await carregarProducao(p.id)); }
      catch(e) { avisarUsuario(e.message, true); }
    }}, h('strong',{},p.nome), h('span',{},p.descricao), h('small',{},p.uso)));
  const lb = $('lista-cenas-base');
  lb.textContent = '';
  for (const chave of Object.keys(CENAS_BASE)) {
    lb.append(h('div.linha', { onclick: () => abrirCena(cenaBase(chave)) },
      h('span.rot', {}, ROTULOS_BASE[chave]),
      h('span.tag', {}, 'starter')));
  }

  const lu = $('lista-cenas-user');
  lu.textContent = '';
  const bib = lerBiblioteca();
  const nomes = Object.keys(bib).sort();
  if (!nomes.length) lu.append(h('p.nota', {}, 'Nothing saved yet. “Save scene” puts the current composition here.'));
  for (const nome of nomes) {
    lu.append(h('div.linha', { onclick: e => { if (e.target.tagName !== 'BUTTON') abrirCena(clonar(bib[nome])); } },
      h('span.rot', { title: `saved ${bib[nome].salvo || '?'}` }, nome),
      h('button.mini', { title: 'duplicate', onclick: () => { const c = clonar(bib[nome]); c.nome = nomeLivre(`${nome} copy`); if (!salvarCena(c)) avisarUsuario('Could not duplicate scene.', true); desenharCenas(); } }, '⧉'),
      h('button.mini', { title: 'rename', onclick: () => {
        const n = prompt('New name', nome)?.trim();
        if (n && n !== nome) {
          if (!renomearCena(nome, n)) avisarUsuario('Rename failed: name already exists or storage unavailable.', true);
          desenharCenas();
        }
      } }, '✎'),
      h('button.mini', { title: 'delete', onclick: () => {
        if (confirm(`Delete scene “${nome}”?`)) {
          if (!apagarCena(nome)) avisarUsuario('Could not delete scene.', true);
          desenharCenas();
        }
      } }, '✕')));
  }
}

/* ------------------------------------------------------------- documents */

function substituirEstado (novo) {
  for (const k of Object.keys(estado)) delete estado[k];
  Object.assign(estado, novo);
}

function mostrarCarga (txt, frac) {
  const c = $('carga');
  document.body.dataset.carregando = 'true';
  c.hidden = false;
  c.querySelector('span').textContent = txt;
  c.querySelector('i').style.width = `${Math.round((frac || 0) * 100)}%`;
}
const esconderCarga = () => { $('carga').hidden = true; document.body.dataset.carregando = 'false'; };

async function abrirCena (doc) {
  if (pronto && !preservarSessao()) {
    avisarUsuario('Export a JSON backup before opening another scene: browser storage is unavailable.', true);
    return;
  }
  try { await carregarDocumento(doc); desenharCenas(); }
  catch (e) { avisarUsuario(e.message, true); }
}

async function carregarDocumento (doc) {
  const novo = normalizarDocumento(doc);
  for (const o of novo.objetos) {
    const asset = o.tipo === 'prop' ? PROPS[o.slug] : acharAsset(o.slug);
    if (!asset) throw new Error(`Asset unavailable: ${o.slug}. Your current scene has been kept.`);
    if (o.nivel && o.tipo !== 'prop' && !asset.niveis?.[o.nivel])
      throw new Error(`Detail unavailable: ${o.slug} / ${o.nivel}.`);
  }
  if (carregando) throw new Error('Please wait for the current scene to finish loading.');
  if (pronto && (!preservarSessao() || !salvarCena({ ...clonar(estado), nome: nomeLivre(`${estado.nome} — recovery`) })))
    throw new Error('Could not preserve your current scene. Export a JSON backup before switching.');
  const anterior = clonar(estado);
  carregando = true;
  mostrarCarga('loading assets…', 0);
  dock.parar();
  try {
    // Build all assets before replacing the document or closing the import dialog.
    await mundo.sincronizar(novo, (f, t, nome) => mostrarCarga(`${nome} — ${f}/${t}`, f / t));
    fecharModal();
    await aplicarDocumento(doc, novo);
  } catch (e) {
    substituirEstado(anterior);
    await mundo.sincronizar(estado);
    mundo.aplicarRender(estado.render); mundo.aplicarAmbiente(estado.ambiente);
    throw e;
  } finally {
    carregando = false; esconderCarga();
  }
  if (pronto) { preservarSessao(); desenharCenas(); }
}

async function aplicarDocumento (doc, novo) {
  substituirEstado(novo);
  podar(estado);
  editor.selecao = [];
  editor.atualizarGizmo();
  dock.parar();
  dock.t = 0;
  dock.cameraLivre = false;
  dock.planoEditado = null;

  mostrarCarga('loading assets…', 0);
  mundo.aplicarRender(estado.render);
  mundo.aplicarAmbiente(estado.ambiente);
  await mundo.sincronizar(estado, (f, t, nome) => mostrarCarga(`${nome} — ${f}/${t}`, f / t));
  mundo.aplicarAmbiente(estado.ambiente);      // the shadow camera needs the real scene radius
  esconderCarga();

  /* `assentar` — seat the aircraft on whatever is under them, once, on open.
     A field plate is a real surface with real relief: GRU's 10L runway sits
     0.39 m below the threshold datum where the starter puts the 777, so a
     hard-coded y would be a number that goes stale the day the plate is
     re-exported. Ask the studio instead; it is the same code the G key runs. */
  if (doc.assentar) {
    const guarda = editor.selecao;
    editor.selecao = estado.objetos
      .filter(o => o.tipo === 'aeronave' && !o.travado && o.visivel).map(o => o.id);
    editor.aoChao(false);
    editor.selecao = guarda;
    editor.atualizarGizmo();      // aoChao attached the gizmo to the temporary selection
  }

  mundo.usarOrto(false);
  editor.gizmo.camera = mundo.cam;
  mundo.camP.fov = estado.camera.fov || 35;
  mundo.camP.updateProjectionMatrix();
  if (doc.camera && doc.camera.pos) {
    mundo.aplicarPose(estado.camera);
    if (doc.camera.orto) { estado.camera.orto = true; mundo.usarOrto(true); }
  } else {
    /* A starter scene carries a direction, not a position: frame what is here.
       Frame the AIRCRAFT by default — a 240 m backdrop card, a 624 m terminal
       pier or a 6 km field plate would otherwise decide the shot and leave the
       jet a speck. A scene whose subject IS the field says `quadro: 'tudo'`.
       The "frame all" button still frames all of it either way. */
    const aeronaves = estado.objetos.filter(o => o.tipo === 'aeronave').map(o => o.id);
    const caixa = doc.quadro === 'tudo'
      ? mundo.caixaTudo()
      : (mundo.caixaDe(aeronaves) || mundo.caixaTudo());
    mundo.vista(doc.vista || 'tres-quartos', caixa);
  }
  editor.gizmo.camera = mundo.cam;
  estado.camera = mundo.poseAtual(mundo.camP.fov, mundo.cam === mundo.camO);
  $('nome-cena').value = estado.nome;
  mundo.invalidarTerreno();
  sincronizarInspetor();
  desenharOutliner();
  sincronizarTransform();
  dock.desenhar();
  /* A scene that carries a timeline opens ON its first frame, not on the rest
     pose: otherwise a take-off scene opens with the aeroplane at the origin and
     the camera somewhere else entirely, and looks broken until you press play. */
  aplicarTempo();
  historico.iniciar(estado);
  $('palco').classList.toggle('sem-tempo', !temAnimacao(estado.linha));
  $('tempo-alternar').textContent = temAnimacao(estado.linha) ? '▾ timeline' : '▴ timeline';
}

/* ------------------------------------------------------------ operations */

const GRANDE = 150;      // half-width, metres: above this a piece is scenery

/** A spot on the ground that does not sit inside anything already placed. */
function posicaoLivre (raioNovo, perto) {
  const alvo = perto || mundo.controles.target;
  const base = new THREE.Vector3(alvo.x, 0, alvo.z);
  const ocupados = [...mundo.objetos.values()].map(o => {
    const b = new THREE.Box3().setFromObject(o);
    const c = b.getCenter(new THREE.Vector3()), s = b.getSize(new THREE.Vector3());
    return { c, r: Math.hypot(s.x, s.z) / 2, grande: Math.max(s.x, s.z) > GRANDE };
  }).filter(o => !o.grande);
  /* A field plate has a 3 km radius. Nudging it "clear of what is already
     there" would put it 5 km away, and nudging an aircraft clear of a plate is
     just as wrong — you drop a jet ONTO a runway, not beside it. So anything
     wider than GRANDE neither moves nor pushes. */
  if (raioNovo > GRANDE) return base;
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
  if (document.body.dataset.carregando === 'true') return;
  if (tipo === 'prop' ? !Object.hasOwn(PROPS, slug) : !acharAsset(slug)) return;
  const d = novoObjeto(tipo, slug, nome);
  estado.objetos.push(d);
  mostrarCarga(`loading ${nome}…`, 0.4);
  try { await mundo.sincronizar(estado); }
  catch (e) { estado.objetos = estado.objetos.filter(o => o.id !== d.id); avisarUsuario(e.message, true); return; }
  finally { esconderCarga(); }
  const o = mundo.objetos.get(d.id);
  if (o) {
    const b = new THREE.Box3().setFromObject(o);
    const s = b.getSize(new THREE.Vector3());
    const p = posicaoLivre(Math.hypot(s.x, s.z) / 2, ponto);
    d.pos = [+p.x.toFixed(3), 0, +p.z.toFixed(3)];
    mundo.aplicarTransformacoes(estado);
  }
  mundo.aplicarAmbiente(estado.ambiente);      // shadow frustum follows the scene
  mundo.invalidarTerreno();                    // a flight's ground profile is stale
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
  /* Tracks and flights that pointed at those objects go with them. Leaving
     orphans behind would put rows in the dock for aeroplanes that are not
     there, and `avaliar` would keep asking mundo for their instances. */
  podar(estado);
  await mundo.sincronizar(estado);
  mundo.invalidarTerreno();
  editor.atualizarGizmo();
  desenharOutliner();
  sincronizarTransform();
  dock.desenhar();
  aplicarTempo();
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
  dock.parar();
  substituirEstado(s);
  mundo.aplicarPose(estado.camera);
  mundo.usarOrto(!!estado.camera.orto);
  editor.gizmo.camera = mundo.cam;
  editor.selecao = editor.selecao.filter(id => estado.objetos.some(o => o.id === id));
  mundo.aplicarRender(estado.render);
  await mundo.sincronizar(estado);
  mundo.aplicarAmbiente(estado.ambiente);
  mundo.invalidarTerreno();
  editor.atualizarGizmo();
  sincronizarInspetor();
  desenharOutliner();
  sincronizarTransform();
  /* The timeline is part of the snapshot, so undo undoes a key exactly the way
     it undoes a move — one serialiser, one restorer, still no third path. */
  dock.t = Math.min(dock.t, estado.linha.duracao);
  dock.chaveSel = null;
  dock.desenhar();
  aplicarTempo();
  $('nome-cena').value = estado.nome;
}

function atalho (nome) {
  if (document.body.dataset.carregando === 'true') return;
  switch (nome) {
    case 'desfazer': return aplicarSnapshot(historico.desfazer());
    case 'refazer': return aplicarSnapshot(historico.refazer());
    case 'duplicar': duplicar(); break;
    case 'apagar': apagar(); break;
    case 'chao': editor.aoChao(); break;
    case 'enquadrar-sel': {
      const b = mundo.caixaDe(editor.selecao);
      mundo.enquadrar(b || mundo.caixaTudo());
      registrarCamera('frame selection');
      break;
    }
    case 'enquadrar-tudo': mundo.enquadrar(mundo.caixaTudo()); registrarCamera('frame all'); break;
  }
}

/* -------------------------------------------------------------- outliner */

function desenharOutliner () {
  for (const id of ['btn-dup', 'btn-del', 'btn-chao']) $(id).disabled = !editor.selecionados.length;
  document.querySelectorAll('#hud-gizmo button[data-modo]').forEach(b => b.classList.toggle('ativo', b.dataset.modo === editor.gizmo.mode));
  document.querySelector('#hud-gizmo button[data-espaco]').textContent = editor.gizmo.space;
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
      h('span.tag', {}, d.tipo === 'aeronave' ? 'AC' : d.tipo === 'prop' ? 'PR' : 'CE'),
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

  sincronizarNivel(d);

  const o = mundo.objetos.get(d.id);
  if (o) {
    const b = new THREE.Box3().setFromObject(o), s = b.getSize(new THREE.Vector3());
    const a = d.tipo === 'prop' ? null : acharAsset(d.slug);
    const lic = a && LICENCAS[a.licenca];
    const detalhe = a?.niveis?.[d.nivel || NIVEL_PADRAO] || a;
    $('medidas-sel').textContent =
      `${s.x.toFixed(2)} × ${s.y.toFixed(2)} × ${s.z.toFixed(2)} m (world bbox)`
      + (a ? `\n${a.tipo === 'aeronave' ? a.matricula : (a.campo || '').toUpperCase()} · `
           + `${detalhe.triangulos.toLocaleString()} tris · ${a.materiais} materials` : '')
      + `\nlowest point y = ${b.min.y.toFixed(3)} m`
      + (lic ? `\n${lic.nome}${lic.share_alike ? ' — share-alike' : ''}` : '')
      + (a && a.nota ? `\n${a.nota}` : '');
  }
}

/* ------------------------------------------------------------- detail tier -
 * The control is built from `asset.niveis`, which is built from the manifest.
 * Nothing here knows the word "hero" except as a label: add a fourth tier to
 * export_frota.py, re-export, and it appears in this dropdown with its own
 * measured triangles and bytes. An asset with a single tier hides the row
 * rather than offering a choice of one. */

function sincronizarNivel (d) {
  const linha = $('linha-nivel'), nota = $('nota-nivel'), s = $('nivel-obj');
  const a = d.tipo === 'prop' ? null : acharAsset(d.slug);
  const niveis = a && a.niveis ? ORDEM_NIVEIS.filter(n => a.niveis[n]) : [];
  if (niveis.length < 2) {
    linha.style.display = nota.style.display = 'none';
    return;
  }
  linha.style.display = nota.style.display = '';
  const atual = a.niveis[d.nivel] ? d.nivel : NIVEL_PADRAO;
  s.textContent = '';
  for (const n of niveis) {
    const v = a.niveis[n];
    s.append(h('option', { value: n, selected: n === atual ? 'selected' : undefined },
      `${n} — ${v.triangulos.toLocaleString()} tris, ${formatarBytes(v.bytes)}`));
  }
  s.value = atual;
  const v = a.niveis[atual], base = a.niveis[NIVEL_PADRAO];
  nota.textContent = (ROTULOS_NIVEL[atual] || atual)
    + (base && v !== base
        ? `\n${(v.triangulos / Math.max(1, base.triangulos)).toFixed(1)}× the triangles of `
          + `${NIVEL_PADRAO}, ${v.bytes > base.bytes ? '+' : '−'}`
          + `${formatarBytes(Math.abs(v.bytes - base.bytes))}`
        : '');
}

async function trocarNivel (nivel) {
  const d = editor.selecionados[0];
  if (!d) return;
  const antes = d.nivel || NIVEL_PADRAO;
  if (antes === nivel) return;
  if (nivel === NIVEL_PADRAO) delete d.nivel; else d.nivel = nivel;
  mostrarCarga(`loading ${d.nome} at ${nivel} detail…`, 0.4);
  const t0 = performance.now();
  try { await mundo.sincronizar(estado); }
  catch (e) {
    if (antes === NIVEL_PADRAO) delete d.nivel; else d.nivel = antes;
    sincronizarTransform(); avisarUsuario(e.message, true); return;
  } finally { esconderCarga(); }
  mundo.aplicarAmbiente(estado.ambiente);
  /* A hero mesh is a different mesh: the main-gear measurement, the bounding
     box and any flight table derived from them are all stale. */
  mundo.invalidarTerreno();
  editor.atualizarGizmo();
  sincronizarTransform();
  historico.registrar(`detail ${d.nome} → ${nivel}`, estado);
  avisar(`${d.nome}: ${nivel} tier in ${Math.round(performance.now() - t0)} ms`);
}

function ligarTransform () {
  $('nivel-obj').addEventListener('change', e => trocarNivel(e.target.value));

  const ids = ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz'];
  for (const id of ids) {
    const e = $(id);
    e.addEventListener('input', () => {
      const d = editor.selecionados[0];
      if (!d) return;
      const v = parseFloat(e.value);
      if (!isFinite(v) || (id[0] === 's' && Math.abs(v) < 0.0001)) return;
      const k = id[0] === 't' ? 'pos' : id[0] === 'r' ? 'rot' : 'esc';
      const i = { x: 0, y: 1, z: 2 }[id[1]];
      d[k][i] = v;
      mundo.aplicarTransformacoes(estado);
      editor.atualizarGizmo();
    });
    // One entry per committed edit: typing digits fires many `input` events
    // and exactly one `change` when the field is left or Enter is pressed.
    e.addEventListener('change', () => {
      autoChave(editor.selecao);
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

  /* camera — the numeric fields, and the live read-back that keeps them
     honest while the mouse is driving. */
  const camIds = ['cx', 'cy', 'cz', 'ax', 'ay', 'az'];
  for (const id of camIds) {
    $(id).addEventListener('input', () => {
      const v = camIds.map(k => parseFloat($(k).value));
      if (v.some(n => !isFinite(n))) return;
      mundo.camP.position.set(v[0], v[1], v[2]);
      mundo.controles.target.set(v[3], v[4], v[5]);
      mundo.camP.lookAt(mundo.controles.target);
      /* NOT controles.update(), and this cost an hour. OrbitControls clamps the
         polar angle at maxPolarAngle = 0.499π — "never under the tarmac" — and
         that clamp is expressed relative to the TARGET, not to the ground. A
         climbing aeroplane puts the target 24 m up, so a lens typed in at 16 m
         is "below the target", and update() silently lifted it to 24.99 m: the
         camera key came back nine metres higher than the number typed.
         The timeline's own projection (mundo.aplicarLinha) sets the camera and
         calls lookAt without ever going through the controls, so it has never
         had this limit — which is why a keyed low camera plays back correctly
         and only the numeric fields disagreed with it. The next mouse drag
         re-derives the orbit state from the camera, and re-applies the clamp
         then, which is the control's own business. */
      mundo.atualizarOrto();
    });
  }
  mundo.controles.addEventListener('change', sincronizarCamera);
  sincronizarCamera();

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

  /* grade — see js/mundo.js §grade */
  ren('g-contraste', v => (estado.render.correcao.contraste = v), 'g-contraste-out');
  ren('g-saturacao', v => (estado.render.correcao.saturacao = v), 'g-saturacao-out');
  ren('g-elevar', v => (estado.render.correcao.elevar = v), 'g-elevar-out');
  ren('g-temperatura', v => (estado.render.correcao.temperatura = v), 'g-temperatura-out');
  ren('g-vinheta', v => (estado.render.correcao.vinheta = v), 'g-vinheta-out');
  $('g-reset').addEventListener('click', () => {
    estado.render.correcao = { contraste: 1, saturacao: 1, elevar: 0, temperatura: 0, vinheta: 0 };
    mundo.aplicarRender(estado.render);
    sincronizarInspetor();
    historico.registrar('reset colour grade', estado);
  });

  /* One undo step per committed setting. A slider drag fires a stream of
     `input` events and a single `change` when the thumb is released, so the
     whole drag collapses into one entry — which is what a user expects. */
  document.querySelectorAll('#inspetor input, #inspetor select').forEach(e => {
    if (e.closest('#campos-transform')) return;
    e.addEventListener('change', () => {
      if (['cx', 'cy', 'cz', 'ax', 'ay', 'az', 'fov', 'orto'].includes(e.id))
        estado.camera = mundo.poseAtual(mundo.camP.fov, mundo.cam === mundo.camO);
      historico.registrar('scene setting', estado);
    });
  });
}

function guardarPose (qual) {
  estado.poses[qual] = mundo.poseAtual(mundo.camP.fov, mundo.cam === mundo.camO);
  historico.registrar(`store pose ${qual}`, estado);
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
  const g = r.correcao || {};
  for (const [id, k] of [['g-contraste', 'contraste'], ['g-saturacao', 'saturacao'],
                         ['g-elevar', 'elevar'], ['g-temperatura', 'temperatura'],
                         ['g-vinheta', 'vinheta']]) {
    p(id, g[k] ?? (k === 'contraste' || k === 'saturacao' ? 1 : 0));
    $(`${id}-out`).textContent = (+$(id).value).toFixed(2);
  }
  p('fov', estado.camera.fov); $('fov-out').textContent = estado.camera.fov;
  p('orto', estado.camera.orto);
  guardarPoseTexto();
}
/** Write the live camera into the two numeric rows. Skips whichever field the
 *  user is typing in, the same rule the transform fields use. */
function sincronizarCamera () {
  if (document.activeElement !== $('fov')) {
    $('fov').value = mundo.camP.fov;
    $('fov-out').textContent = mundo.camP.fov.toFixed(1);
  }
  const p = mundo.camP.position, a = mundo.controles.target;
  const v = { cx: p.x, cy: p.y, cz: p.z, ax: a.x, ay: a.y, az: a.z };
  for (const [id, n] of Object.entries(v)) {
    const e = $(id);
    if (!e || document.activeElement === e) continue;
    e.value = +n.toFixed(2);
  }
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
  $('nome-cena').addEventListener('change', e => { estado.nome = e.target.value.trim() || 'untitled scene'; historico.registrar('rename scene', estado); });
  $('btn-salvar').addEventListener('click', () => {
    estado.nome = $('nome-cena').value.trim() || 'untitled scene';
    Object.assign(estado.camera, {
      pos: mundo.camP.position.toArray().map(n => +n.toFixed(3)),
      alvo: mundo.controles.target.toArray().map(n => +n.toFixed(3)),
      fov: mundo.camP.fov, orto: mundo.cam === mundo.camO,
    });
    const existe = Object.hasOwn(lerBiblioteca(), estado.nome);
    if (existe && !confirm(`Replace saved scene “${estado.nome}”?`)) return;
    const n = salvarCena(estado, { substituir: existe });
    if (n) { preservarSessao(); avisarUsuario('Scene saved to your library.'); }
    desenharCenas();
    document.querySelector('#abas-lateral .aba:nth-child(2)').click();
    if (!n) avisarUsuario('Could not save scene. Export a JSON backup.', true);
  });
  $('btn-exportar').addEventListener('click', () => { dock.parar(); dlgExportar({ mundo, estado, editor, carregarDocumento }); });
  /* The licence panel is built FROM the open scene, so it needs the scene. */
  $('btn-sobre').addEventListener('click', () => dlgLicenca({ estado }));
  $('modal-fechar').addEventListener('click', fecharModal);

  document.querySelectorAll('#abas-lateral .aba').forEach(b =>
    b.addEventListener('click', () => {
      document.querySelectorAll('#abas-lateral .aba').forEach(x => x.classList.toggle('ativa', x === b));
      document.querySelectorAll('#lateral .painel').forEach(p => p.classList.toggle('ativo', p.id === b.dataset.alvo));
    }));

  $('btn-cena-nova').addEventListener('click', () => abrirCena(estadoPadrao()));
  addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's' && $('modal').hidden) {
      e.preventDefault(); $('nome-cena').blur(); $('btn-salvar').click();
    }
  });
  $('btn-cena-importar').addEventListener('click', () =>
    dlgExportar({ mundo, estado, editor, carregarDocumento }, 'JSON'));
}

function ligarHud () {
  document.querySelectorAll('#hud-cameras button').forEach(b =>
    b.addEventListener('click', () => {
      if (b.dataset.vista) {
        const alvo = editor.selecao.length ? mundo.caixaDe(editor.selecao) : null;
        mundo.vista(b.dataset.vista, alvo || mundo.caixaTudo());
        registrarCamera(`camera ${b.dataset.vista}`);
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
  const el = $('status');
  el.textContent =
    `${fps.toFixed(0)} fps · ${estado.objetos.length} objects · `
    + `${s.triangulos.toLocaleString()} tris · ${s.chamadas} draw calls · `
    + `${formatarBytes(bytesCarregados())} of GLB loaded`
    + (temAnimacao(estado.linha) ? ` · timeline ${estado.linha.duracao}s @ ${estado.linha.fps} fps` : '')
    + (el.dataset.aviso ? `\n${el.dataset.aviso}` : '')
    + (falhas.length ? `\n${falhas.length} asset(s) failed — see the console` : '');
}

addEventListener('error', e => { falhas.push(e.message); avisarUsuario(e.message, true); });
addEventListener('unhandledrejection', e => { avisarUsuario(e.reason?.message || 'Operation failed.', true); esconderCarga(); });

iniciar().catch(e => {
  console.error(e);
  document.getElementById('status').textContent = 'boot failed: ' + e.message;
});
