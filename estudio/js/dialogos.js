/* dialogos.js — the modal dialogs: Export (GIF / embed / PNG / JSON) and Licence.
 *
 * Kept apart from main.js because these are the only screens with real forms,
 * and because the export dialog is where the studio has to be honest: it states
 * the GIF's frame delay in centiseconds, the estimate before and the measured
 * size after, and exactly which files an embed needs alongside it.
 */

import {
  FPS_LEGAIS, estimarGif, formatarBytes, exportarGif, exportarPng,
  construirEmbed, documentoParaJson, baixar, nomeArquivo,
  licencasDaCena, textoAtribuicao, exportarSequencia,
} from './exportar.js';
import { acharAsset } from './frota.js';
import { RECEITAS_VOO, RECEITAS_MOV, aplicarVoo, escreverMovimento, perfilPara } from './presets.js';
import { temAnimacao, quadros as quadrosDaLinha, amostrarVoo, tabelaDe, invalidarVoo } from './tempo.js';

/* Tiny DOM helper: h('div.classe', {attr}, ...filhos) */
export function h (spec, props = {}, ...filhos) {
  const [tag, ...cls] = spec.split('.');
  const el = document.createElement(tag || 'div');
  if (cls.length) el.className = cls.join(' ');
  for (const [k, v] of Object.entries(props || {})) {
    if (k === 'html') el.innerHTML = v;
    else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
    else if (v !== null && v !== undefined && v !== false) el.setAttribute(k, v === true ? '' : v);
  }
  for (const f of filhos.flat()) if (f !== null && f !== undefined) el.append(f.nodeType ? f : document.createTextNode(f));
  return el;
}

const sel = (id, opcoes, valor) =>
  h('select', { id }, opcoes.map(o => {
    const op = h('option', { value: o.v }, o.r);
    if (String(o.v) === String(valor)) op.selected = true;
    return op;
  }));

const campo = (rotulo, controle) => h('label.uma', {}, h('span', {}, rotulo), controle);

/* --------------------------------------------------------------- modal --- */

let fecharAtual = null;

export function abrirModal (titulo, corpo) {
  const m = document.getElementById('modal');
  document.getElementById('modal-titulo').textContent = titulo;
  const c = document.getElementById('modal-corpo');
  c.textContent = '';
  c.append(corpo);
  m.hidden = false;
  fecharAtual = () => { m.hidden = true; c.textContent = ''; fecharAtual = null; };
  return fecharAtual;
}
export function fecharModal () { fecharAtual && fecharAtual(); }

document.addEventListener('keydown', e => { if (e.key === 'Escape') fecharModal(); });

/* -------------------------------------------------------------- licence --- */

/* The Licence panel answers "what does THIS scene oblige me to do", so it is
 * built from the assets that are actually in the open scene. A blanket claim
 * about the page would be wrong in both directions: wrong when the scene is
 * pure fleet (it would over-claim), and wrong when a GRU hangar is in it (it
 * would hide the share-alike). */

const escapar = t => String(t).replace(/[<>&]/g, c =>
  ({ '<': '&lt;', '>': '&gt;', '&': '&amp;' }[c]));

export function dlgLicenca (ctx) {
  const estado = ctx && ctx.estado;
  const lics = estado ? licencasDaCena(estado) : [];
  const compartilha = lics.some(l => l.share_alike);

  const usados = estado
    ? [...new Set(estado.objetos.map(o => o.slug))]
        .map(s => acharAsset(s)).filter(Boolean)
    : [];
  const campos = [...new Set(usados.map(a => a.campo).filter(Boolean))];

  const linhasCena = lics.map(l => `
    <tr><th style="white-space:nowrap">${escapar(l.nome)}${l.share_alike
        ? ' <span style="color:#d8b263">share-alike</span>' : ''}</th>
        <td><code>${escapar(l.atribuicao)}</code><br>
            <a href="${l.url}" target="_blank" rel="noopener">${l.url}</a>
            ${l.nota ? `<br><span style="opacity:.8">${escapar(l.nota)}</span>` : ''}</td></tr>`).join('');

  const corpo = h('div', { html: `
    <h4>This scene</h4>
    <p>${estado ? `<b>${escapar(estado.nome || 'untitled')}</b> — ${estado.objetos.length}
       object(s)${campos.length ? `, using geometry from ${campos.map(c => c.toUpperCase()).join(', ')}` : ''}.`
       : 'Open a scene to see what it carries.'}</p>
    <table>${linhasCena || '<tr><td>nothing placed yet</td></tr>'}</table>
    <p>Everything this scene exports — GIF, PNG, embed, JSON — carries
       <b>every</b> line above. The exported embed writes them into the page and
       the scene JSON records them in a <code>licencas</code> field.</p>
    ${compartilha ? `<div class="aviso"><b>Share-alike is in play.</b> This scene
       contains airport geometry derived from OpenStreetMap. ODbL 1.0 lets you
       redistribute it — that is why it is here — but a <i>derived database</i>
       you publish from it must be offered under ODbL as well, and the
       attribution has to travel with the file. Renders and animations are
       Produced Works: attribute them, and you are done.</div>` : ''}

    <h4>The two tiers, and why both may ship</h4>
    <p>The <b>eleven aircraft</b> are original geometry built in this repository
       from the manufacturers' published dimensional documents. <b>CC BY 4.0.</b></p>
    <p>The <b>airport pieces</b> under <code>export/cenarios/</code> are cut out of
       <code>scenario/</code> (SCL), <code>scenario_sdsc/</code> and
       <code>scenario_sbgr/</code>, which are generated from
       <b>OpenStreetMap</b>. A mesh built from an ODbL database is a derived
       database, so it is <b>ODbL 1.0, share-alike</b> — and ODbL <i>permits</i>
       that redistribution as long as the attribution travels and share-alike is
       honoured. That is what the per-asset <code>licenca</code> field, the
       <code>copyright</code> written into every <code>.glb</code>, and this
       panel are for. See <code>NOTICE.md</code> §"The airport mesh is an OSM
       derivative".</p>
    <p>The <b>grounds, the sky and the massing blocks</b> are authored in
       <code>estudio/js/props.js</code> from primitives and canvas painting, with
       no survey data in them. They ride with the fleet under CC BY 4.0.</p>
    <p><b>Copernicus terrain is not exported at all.</b> The height fields under
       <code>scenario*/</code> are 3.7 M faces at SBGR alone and would carry two
       further notices; no asset in this studio references them.</p>

    <h4>What is lost on the way out</h4>
    <p>The airport materials are procedural node trees — noise, range maps, a
       haze group — that glTF cannot carry. The exporter flattens each one to a
       representative colour taken from the material's own
       <code>diffuse_color</code>, and records that substitution material by
       material in <code>export/cenarios/manifest.json</code> under
       <code>materiais_achatados</code>. The pavement is the right grey; it is
       not the pavement you see in a Cycles render of the field.</p>

    <h4>Trademarks</h4>
    <p><b>LATAM</b>, <b>Airbus</b> and <b>Boeing</b> are trademarks of their owners.
       This is an independent, non-commercial project with no affiliation or
       endorsement. Neither licence above grants any right over the marks.</p>

    <h4>Third-party code, vendored under <code>estudio/vendor/</code></h4>
    <table>
      <tr><th>three.js r169</th><td>MIT</td></tr>
      <tr><th>Draco decoder</th><td>Apache-2.0 (Google)</td></tr>
      <tr><th>gifenc 1.0.3</th><td>MIT (Matt DesLauriers)</td></tr>
    </table>
    <p>Nothing is loaded from a CDN: the studio runs with no internet.</p>
  ` });

  const btn = h('button', {
    onclick: () => {
      navigator.clipboard?.writeText(estado ? textoAtribuicao(estado) : '');
      btn.textContent = 'copied';
    },
  }, 'Copy this scene\'s attribution');
  corpo.append(h('div.rodape', {},
    h('span.estimativa', {}, `${lics.length} licence(s) in play`), btn));
  abrirModal('Licence and attribution', corpo);
}

/* --------------------------------------------------------------- motion ---
 * Everything that WRITES a timeline lives behind this one button, and that is
 * the point: a preset here is not a mode the exporter runs, it is a handful of
 * keys you can then drag. */

export function dlgMovimento (ctx) {
  /* NOT named `sel`: that is the <select> helper at the top of this file, and
     shadowing it here turns every dropdown below into a TypeError. */
  const selId = ctx.editor.selecao[0] || null;
  const d = selId ? ctx.estado.objetos.find(o => o.id === selId) : null;
  const inst = selId ? ctx.mundo.objetos.get(selId) : null;
  const ehAero = d && d.tipo === 'aeronave';
  const comp = inst ? inst.userData.tamanho.x : 0;
  const trem = inst ? inst.userData.trem : null;

  /* --- flight --- */
  const receita = sel('voo-tipo', Object.entries(RECEITAS_VOO).map(([v, r]) => ({ v, r: r.rot })), 'decolagem');
  const dur = h('input', { type: 'number', min: 2, max: 60, step: 0.5, value: ctx.estado.linha.duracao });
  const altP = h('input', { type: 'number', min: 15, max: 900, step: 5, value: 90 });
  const velP = h('input', { type: 'number', min: 40, max: 250, step: 5, value: 100 });
  const giroP = h('input', { type: 'number', min: 0, max: 60, step: 5, value: 20 });
  const camOn = h('input', { type: 'checkbox', checked: true });
  const linhaAlt = campo('pass altitude (m)', altP);
  const linhaVel = campo('pass speed (m/s)', velP);
  const linhaGiro = campo('turn through the pass (°)', giroP);
  const msgVoo = h('div.nota');
  const perfil = ehAero ? perfilPara(comp) : null;

  const atualizarVoo = () => {
    const p = receita.value === 'passagem';
    linhaAlt.style.display = linhaVel.style.display = linhaGiro.style.display = p ? '' : 'none';
  };
  receita.addEventListener('change', atualizarVoo);

  const btnVoo = h('button.primaria', {
    onclick: () => {
      try {
        const r = aplicarVoo(ctx.estado, ctx.mundo, selId, receita.value, {
          duracao: +dur.value, camera: camOn.checked,
          altitude: +altP.value, velocidade: +velP.value, giro: +giroP.value,
        });
        ctx.registrar(`flight: ${receita.value}`);
        ctx.dock.t = 0;
        ctx.redesenhar();
        msgVoo.innerHTML = `<b>done.</b> ${r.resumo}`
          + (r.camera ? ' · camera keyed to follow it' : '');
      } catch (e) { msgVoo.innerHTML = `<span style="color:#ff8f8f">${e.message}</span>`; console.error(e); }
    },
  }, 'Build the flight');
  btnVoo.disabled = !ehAero;

  /* --- the four canned motions --- */
  const modo = sel('mov-modo', Object.entries(RECEITAS_MOV).map(([v, r]) => ({ v, r })), 'turntable-cena');
  const sentido = sel('mov-sentido', [{ v: 'horario', r: 'clockwise' }, { v: 'anti', r: 'anticlockwise' }], 'horario');
  const pingpong = h('input', { type: 'checkbox', checked: true });
  const distancia = h('input', { type: 'number', step: 5, value: 60 });
  const subida = h('input', { type: 'number', step: 1, value: 0 });
  const direcao = sel('mov-dir', [
    { v: 'nariz', r: 'along the nose (local −X)' }, { v: 'x', r: 'world +X' }, { v: 'z', r: 'world +Z' },
  ], 'nariz');
  const linhaSentido = campo('direction', sentido);
  const linhaPP = h('label.check', {}, pingpong, ' ping-pong (A→B→A, so the loop does not cut)');
  const linhaDist = campo('travel (m)', distancia);
  const linhaSobe = campo('climb (m)', subida);
  const linhaDir = campo('direction', direcao);
  const msgMov = h('div.nota');
  const atualizarMov = () => {
    const m = modo.value;
    linhaSentido.style.display = m.startsWith('turntable') ? '' : 'none';
    linhaPP.style.display = m === 'caminho-camera' ? '' : 'none';
    linhaDist.style.display = linhaSobe.style.display = linhaDir.style.display = m === 'objeto-movel' ? '' : 'none';
  };
  modo.addEventListener('change', atualizarMov);

  const btnMov = h('button', {
    onclick: () => {
      try {
        const r = escreverMovimento(ctx.estado, ctx.mundo, modo.value, {
          sentido: sentido.value, pingpong: pingpong.checked,
          distancia: +distancia.value, subida: +subida.value, direcao: direcao.value,
        }, selId);
        ctx.registrar(`motion: ${modo.value}`);
        ctx.dock.t = 0;
        ctx.redesenhar();
        msgMov.innerHTML = `<b>written.</b> ${r} — every key is now draggable.`;
      } catch (e) { msgMov.innerHTML = `<span style="color:#ff8f8f">${e.message}</span>`; console.error(e); }
    },
  }, 'Write the keys');

  atualizarVoo(); atualizarMov();

  const corpo = h('div', {},
    h('h4', {}, 'Flight'),
    ehAero
      ? h('p.nota', { html:
          `<b>${d.nome}</b> — ${comp.toFixed(1)} m, which puts it on the `
          + `<b>${perfil === undefined ? '?' : (perfil.rot.split(' —')[0])}</b> profile. `
          + (trem ? `Main gear measured at x = ${trem.x.toFixed(2)} m, ${trem.nos} meshes: `
                  + 'the aeroplane rotates about the wheels, not about its own origin.'
                  : 'No gear meshes found in this GLB — it will rotate about its origin.') })
      : h('div.aviso', { html: 'Select an <b>aircraft</b> in the viewport or the outliner. '
          + 'A flight derives heading, pitch and bank from a path, which only means '
          + 'anything for something with wings.' }),
    campo('recipe', receita), campo('clip length (s)', dur),
    linhaAlt, linhaVel, linhaGiro,
    h('label.check', {}, camOn, ' also key the camera to follow it'),
    h('p.nota', { html:
      'The route starts where the aeroplane stands, along the heading it is '
      + 'already facing. Attitude is <b>derived</b>: bank from tan φ = v·ψ̇/g, '
      + 'pitch from the flight path angle plus an angle of attack that scales as '
      + '1/v², both rate-limited. See <code>js/tempo.js</code> §flight for where '
      + 'every number was measured.' }),
    msgVoo,
    h('div.rodape', {}, h('span.estimativa', {}, 'writes one flight + a gear key'), btnVoo),

    h('h4', {}, 'The four motions the GIF dialog used to own'),
    h('p.nota', {}, 'They are not gone — they are now timeline writers. Pick one, '
      + 'get keys, drag them.'),
    campo('motion', modo), linhaSentido, linhaPP, linhaDir, linhaDist, linhaSobe,
    msgMov,
    h('div.rodape', {}, h('span.estimativa', {},
      `clip is ${ctx.estado.linha.duracao} s at ${ctx.estado.linha.fps} fps`), btnMov));

  abrirModal('Motion — write the timeline', corpo);
}

/* --- flight parameters --------------------------------------------------- */

export function dlgVoo (ctx, voo) {
  const d = ctx.estado.objetos.find(o => o.id === voo.ref);
  const cx = ctx.mundo.contextoVoo(voo.ref, ctx.estado);
  amostrarVoo(voo, 0, cx);                       // makes sure the table exists
  const tab = tabelaDe(voo);

  const num = (rot, k, min, max, passo, nota) => {
    const i = h('input', { type: 'number', min, max, step: passo, value: voo[k] });
    i.addEventListener('change', () => {
      voo[k] = +i.value;
      invalidarVoo(voo);                         // force the table to rebuild
      ctx.registrar(`flight ${k}`);
      ctx.redesenhar();
      medir();
    });
    return h('div', {}, campo(rot, i), nota ? h('p.nota', {}, nota) : null);
  };

  const saida = h('div.nota');
  function medir () {
    amostrarVoo(voo, 0, ctx.mundo.contextoVoo(voo.ref, ctx.estado));
    const t = tabelaDe(voo);
    if (!t) { saida.textContent = 'route not built'; return; }
    const vsMax = Math.max(...t.VS), bMax = Math.max(...t.BANCO.map(Math.abs));
    const pMax = Math.max(...t.PITCH);
    /* Everything below is READ BACK from the built table. Nothing here is the
       number that was asked for; it is the number that came out. */
    saida.innerHTML =
      `<table>
        <tr><th>path</th><td>${t.comprimento.toFixed(0)} m in ${t.dur.toFixed(2)} s,
            ${voo.rota.length} waypoints</td></tr>
        <tr><th>speed</th><td>${Math.min(...t.V).toFixed(1)} → ${Math.max(...t.V).toFixed(1)} m/s</td></tr>
        <tr><th>wheels off</th><td>${t.tLift !== null
            ? `${t.tLift.toFixed(2)} s, ${t.S[t.SOLO.indexOf(false)].toFixed(0)} m into the roll`
            : 'never — this flight does not leave the ground'}</td></tr>
        <tr><th>peak climb</th><td>${vsMax.toFixed(2)} m/s
            ${vsMax > 0.05 ? `(${(100 * vsMax / Math.max(...t.V)).toFixed(1)} % gradient)` : ''}</td></tr>
        <tr><th>peak pitch</th><td>${pMax.toFixed(1)}°</td></tr>
        <tr><th>peak bank</th><td>${bMax.toFixed(1)}°</td></tr>
        <tr><th>main gear</th><td>${cx && cx.temTrem
            ? `x = ${cx.xg.toFixed(3)} m, y = ${cx.yg.toFixed(3)} m — measured off the GLB`
            : 'not found; rotating about the object origin'}</td></tr>
      </table>`;
  }
  medir();

  const btnRefazer = h('button', {
    onclick: () => {
      try {
        const r = aplicarVoo(ctx.estado, ctx.mundo, voo.ref,
          voo.rotulo === 'landing' ? 'pouso' : voo.rotulo === 'flypast' ? 'passagem' : 'decolagem',
          { duracao: ctx.estado.linha.duracao, camera: false });
        ctx.registrar('rebuild flight');
        ctx.redesenhar();
        saida.innerHTML = `<b>rebuilt.</b> ${r.resumo}`;
      } catch (e) { saida.innerHTML = `<span style="color:#ff8f8f">${e.message}</span>`; }
    },
  }, 'Rebuild from where the aircraft stands now');

  abrirModal(`Flight — ${d ? d.nome : '?'} · ${voo.rotulo}`, h('div', {},
    h('p.nota', { html:
      'The <b>path</b> is the data. Heading, pitch and bank are consequences of '
      + 'it — change a number here and the whole attitude re-derives. '
      + 'Everything in the table is measured off the rebuilt curve, not copied '
      + 'from the field above it.' }),
    num('pitch rate (°/s)', 'taxaRot', 0.5, 12, 0.1,
      'The rate limiter that does the rotation, the flare and the de-rotation. '
      + '3.1 °/s is the loaded 777; 3.5 is the ferry A320. Raise it and the '
      + 'aeroplane reads light.'),
    num('take-off attitude (°)', 'pitchDec', 4, 20, 0.5),
    num('α at reference speed (°)', 'alfaRef', 0, 15, 0.1,
      'The angle of attack the model scales as 1/v². Pitch is the flight path '
      + 'angle plus this.'),
    num('reference speed (m/s)', 'vRef', 30, 260, 1),
    num('roll rate (°/s)', 'taxaBanco', 1, 30, 0.5),
    num('bank limit (°)', 'bancoMax', 0, 45, 1),
    num('rotation distance (m)', 'rotacao', 0, 900, 10,
      'How far before lift-off the nose starts coming up. The recipe sets it to '
      + 'pitch ÷ rate × speed, so the attitude is reached exactly AT lift-off.'),
    h('h4', {}, 'Measured'), saida,
    h('div.rodape', {}, h('span.estimativa', {}, tab ? `${tab.N} samples` : ''), btnRefazer)));
}

/* --------------------------------------------------------------- export --- */

export function dlgExportar (ctx, abaInicial = 'GIF') {
  const abas = h('div.abas-modal');
  const painel = h('div');
  const construtores = {
    GIF: () => abaGif(ctx),
    'PNG seq': () => abaSequencia(ctx),
    Embed: () => abaEmbed(ctx),
    PNG: () => abaPng(ctx),
    JSON: () => abaJson(ctx),
  };
  const trocar = nome => {
    painel.textContent = '';
    painel.append(construtores[nome]());
    [...abas.children].forEach(b => b.classList.toggle('ativa', b.textContent === nome));
  };
  for (const nome of Object.keys(construtores)) abas.append(h('button', { onclick: () => trocar(nome) }, nome));
  const raiz = h('div', {}, abas, painel);
  abrirModal('Export', raiz);
  trocar(construtores[abaInicial] ? abaInicial : 'GIF');
}

/* --- GIF ---------------------------------------------------------------- */

function abaGif (ctx) {
  const selecionado = ctx.editor.selecao[0] || null;
  const nomeSel = selecionado ? (ctx.estado.objetos.find(o => o.id === selecionado)?.nome || '?') : null;

  const temLinha = temAnimacao(ctx.estado.linha);
  const modo = sel('gif-modo', [
    { v: 'linha', r: `timeline — the clip you built${temLinha ? '' : ' (nothing on it yet)'}` },
    { v: 'turntable-cena', r: 'turntable — camera orbits the scene' },
    { v: 'turntable-objeto', r: `turntable — spin the selected object${nomeSel ? ` (${nomeSel})` : ' (none selected)'}` },
    { v: 'caminho-camera', r: 'camera path — pose A → pose B' },
    { v: 'objeto-movel', r: 'fixed camera — the selected object moves' },
  ], temLinha ? 'linha' : 'turntable-cena');

  const sentido = sel('gif-sentido', [{ v: 'horario', r: 'clockwise' }, { v: 'anti', r: 'anticlockwise' }], 'horario');
  const quadros = h('input', { type: 'number', id: 'gif-n', min: 2, max: 400, step: 1, value: 60 });
  const fps = sel('gif-fps', FPS_LEGAIS.map(f => ({ v: f.fps, r: f.rot })), 25);
  const larg = sel('gif-w', [320, 400, 480, 560, 640, 720, 800, 960].map(v => ({ v, r: `${v} px wide` })), 640);
  const proporcao = sel('gif-ar', [
    { v: '16:9', r: '16 : 9' }, { v: '4:3', r: '4 : 3' }, { v: '1:1', r: 'square' }, { v: 'vp', r: 'match the viewport' },
  ], '16:9');
  const cores = sel('gif-cores', [32, 64, 128, 256].map(v => ({ v, r: `${v} colours` })), 128);
  const loop = h('input', { type: 'checkbox', id: 'gif-loop', checked: true });
  // Default follows Render → export sampling, so the setting is not a decoration.
  const ss = h('input', { type: 'checkbox', id: 'gif-ss', checked: (ctx.estado.render.aa || 2) > 1 });
  const pingpong = h('input', { type: 'checkbox', id: 'gif-pp', checked: true });
  const distancia = h('input', { type: 'number', id: 'gif-dist', step: 5, value: 60 });
  const subida = h('input', { type: 'number', id: 'gif-sobe', step: 1, value: 0 });
  const direcao = sel('gif-dir', [
    { v: 'nariz', r: 'along the nose (local −X)' }, { v: 'x', r: 'world +X' }, { v: 'z', r: 'world +Z' },
  ], 'nariz');
  const matte = h('input', { type: 'color', id: 'gif-matte', value: ctx.estado.ambiente.fundoCor });

  const est = h('div.estimativa');
  const custo = h('div.aviso');
  const notaLinha = h('p.nota', { html:
    'The GIF is the timeline, frame for frame: same count, same rate, same '
    + 'interpolation, so what you scrubbed is what you get. Duration and frame '
    + 'rate are edited in the dock, not here.' });
  const aviso = h('div.aviso', { html:
    'A GIF frame delay is an integer number of <b>centiseconds</b>. Only rates that '
    + 'divide 100 evenly are offered: 24 fps would alternate 4 and 5 cs and visibly '
    + 'stutter. gifenc does not dither — the colour count is the only size/quality knob.' });

  const linhaSentido = campo('direction', sentido);
  const linhaPP = h('label.check', {}, pingpong, ' ping-pong (A→B→A, so the loop does not cut)');
  const linhaDist = campo('travel (m)', distancia);
  const linhaSobe = campo('climb (m)', subida);
  const linhaDir = campo('direction', direcao);
  const linhaMatte = campo('matte behind', matte);

  function dims () {
    const w = +larg.value;
    let h2;
    if (proporcao.value === '16:9') h2 = Math.round(w * 9 / 16);
    else if (proporcao.value === '4:3') h2 = Math.round(w * 3 / 4);
    else if (proporcao.value === '1:1') h2 = w;
    else h2 = Math.round(w * ctx.mundo.altura / ctx.mundo.largura);
    return [w, h2 - (h2 % 2)];
  }

  function atualizar () {
    const m = modo.value;
    const naLinha = m === 'linha';
    /* On the timeline the frame count and the rate are NOT the exporter's to
       choose: they are the clip's, and a GIF that renders a different number of
       frames than the playhead showed is a GIF you cannot direct. */
    if (naLinha) {
      quadros.value = quadrosDaLinha(ctx.estado.linha);
      fps.value = ctx.estado.linha.fps;
    }
    quadros.disabled = naLinha;
    fps.disabled = naLinha;
    linhaSentido.style.display = (!naLinha && m.startsWith('turntable')) ? '' : 'none';
    linhaPP.style.display = (!naLinha && m === 'caminho-camera') ? '' : 'none';
    linhaDist.style.display = linhaSobe.style.display = linhaDir.style.display =
      (!naLinha && m === 'objeto-movel') ? '' : 'none';
    notaLinha.style.display = naLinha ? '' : 'none';
    linhaMatte.style.display = ctx.estado.ambiente.fundo === 'transparente' ? '' : 'none';
    const [w, hh] = dims();
    const n = +quadros.value, f = +fps.value;
    const cs = (FPS_LEGAIS.find(x => x.fps === f) || FPS_LEGAIS[0]).cs;
    const bytes = estimarGif({ quadros: n, larg: w, alt: hh, cores: +cores.value });
    est.textContent = `${w}×${hh} · ${n} frames · ${cs} cs each · ${(n / f).toFixed(1)} s · ≈ ${formatarBytes(bytes)}`;
    /* The encoder is synchronous. Say so, with a number, BEFORE the click that
       freezes the page. The constant is MEASURED, not guessed: the shipped
       example — 159 frames of 640×360 at 2× supersample — rendered, quantised
       and encoded in 1.9 s, which is 19 million output pixels a second on this
       machine, GPU render included. A first attempt at this line used a made-up
       constant and overstated the wait by seventeen times, which is its own
       kind of dishonesty. */
    const seg = (n * w * hh * (ss.checked ? 1.7 : 1)) / 19e6;
    custo.innerHTML = `Encoding is <b>synchronous on the main thread</b> — there is no
      worker. This export will make the page unresponsive for roughly
      <b>${seg < 1 ? 'under a second' : `${seg.toFixed(0)} s`}</b> on a machine like the one
      that measurement came from, yielding only every second frame; a slower GPU
      will be several times worse. Nothing is lost if you wait; nothing works if
      you do not.`;
  }
  [modo, quadros, fps, larg, proporcao, cores].forEach(e => e.addEventListener('change', atualizar));
  quadros.addEventListener('input', atualizar);

  const prog = h('div.barra-carga', {}, h('i'));
  const progTxt = h('div.nota', {}, '');
  const caixaProg = h('div', { style: 'display:none' }, prog, progTxt);

  const btn = h('button.primaria', {
    onclick: async () => {
      const [w, hh] = dims();
      btn.disabled = true;
      caixaProg.style.display = '';
      const cfg = {
        modo: modo.value, quadros: +quadros.value, fps: +fps.value,
        larg: w, alt: hh, cores: +cores.value, loop: loop.checked,
        ss: ss.checked ? Math.max(2, ctx.estado.render.aa || 2) : 1,
        sentido: sentido.value, pingpong: pingpong.checked,
        distancia: +distancia.value, subida: +subida.value, direcao: direcao.value,
        matte: matte.value,
      };
      try {
        const t0 = performance.now();
        const r = await exportarGif(ctx.mundo, ctx.estado, cfg, ctx.editor.selecao[0] || null,
          (feito, total, fase) => {
            prog.firstChild.style.width = `${Math.round(100 * feito / total)}%`;
            progTxt.textContent = `${fase} — ${feito}/${total}`;
          });
        const seg = (performance.now() - t0) / 1000;
        baixar(r.blob, nomeArquivo(ctx.estado.nome, 'gif'));
        progTxt.innerHTML = `<b>done.</b> ${formatarBytes(r.bytes)} measured `
          + `(${(r.bytes / (r.quadros * w * hh)).toFixed(3)} bytes/pixel/frame), `
          + `${r.quadros} frames at ${r.cs} cs, encoded in ${seg.toFixed(1)} s. Downloaded.`;
      } catch (e) {
        progTxt.innerHTML = `<span style="color:#ff8f8f">${e.message}</span>`;
        console.error(e);
      } finally { btn.disabled = false; }
    },
  }, 'Render GIF');

  atualizar();
  return h('div', {},
    campo('motion', modo), linhaSentido, linhaPP, linhaDir, linhaDist, linhaSobe,
    h('hr', { style: 'border:none;border-top:1px solid var(--borda);margin:10px 0' }),
    campo('frames', quadros), campo('frame rate', fps),
    campo('width', larg), campo('aspect', proporcao), campo('colours', cores),
    linhaMatte,
    h('label.check', {}, loop, ' loop forever'),
    h('label.check', {}, ss, ' 2× supersample (slower, much cleaner edges)'),
    notaLinha, aviso, custo, caixaProg,
    h('div.rodape', {}, est, btn));
}

/* --- PNG sequence -------------------------------------------------------- */

function abaSequencia (ctx) {
  const l = ctx.estado.linha;
  const larg = sel('seq-w', [640, 800, 960, 1280, 1600, 1920].map(v => ({ v, r: `${v} px wide` })), 1280);
  const proporcao = sel('seq-ar', [
    { v: '16:9', r: '16 : 9' }, { v: '4:3', r: '4 : 3' }, { v: '1:1', r: 'square' }, { v: 'vp', r: 'match the viewport' },
  ], '16:9');
  const ss = sel('seq-ss', [{ v: 1, r: 'none' }, { v: 2, r: '2×' }, { v: 3, r: '3× (heavy)' }],
    ctx.estado.render.aa || 2);
  const est = h('div.estimativa');
  const prog = h('div.barra-carga', {}, h('i'));
  const progTxt = h('div.nota', {}, '');
  const caixaProg = h('div', { style: 'display:none' }, prog, progTxt);

  function dims () {
    const w = +larg.value;
    let hh;
    if (proporcao.value === '16:9') hh = Math.round(w * 9 / 16);
    else if (proporcao.value === '4:3') hh = Math.round(w * 3 / 4);
    else if (proporcao.value === '1:1') hh = w;
    else hh = Math.round(w * ctx.mundo.altura / ctx.mundo.largura);
    return [w, hh - (hh % 2)];
  }
  const atualizar = () => {
    const [w, hh] = dims();
    const n = quadrosDaLinha(l);
    /* Roughly 0.6 bytes per pixel for a PNG of a 3D render at this palette
       depth — measured on this studio's own stills, and stated as a range
       because a sky gradient and tiled concrete are not the same problem. */
    est.textContent = `${n} frames · ${w}×${hh} · ≈ ${formatarBytes(n * w * hh * 0.6)} zipped `
      + `(0.3–1.0 bytes/pixel depending on the scene)`;
  };
  [larg, proporcao, ss].forEach(e => e.addEventListener('change', atualizar));
  atualizar();

  const btn = h('button.primaria', {
    onclick: async () => {
      const [w, hh] = dims();
      btn.disabled = true; caixaProg.style.display = '';
      try {
        const t0 = performance.now();
        const r = await exportarSequencia(ctx.mundo, ctx.estado,
          { larg: w, alt: hh, ss: +ss.value, prefixo: 'quadro' },
          (feito, total, fase) => {
            prog.firstChild.style.width = `${Math.round(100 * feito / total)}%`;
            progTxt.textContent = `${fase} — ${feito}/${total}`;
          });
        baixar(r.blob, nomeArquivo(ctx.estado.nome, 'zip'));
        progTxt.innerHTML = `<b>done.</b> ${r.quadros} PNGs, ${formatarBytes(r.bytes)} `
          + `(${(r.bytes / (r.quadros * w * hh)).toFixed(2)} bytes/pixel/frame), `
          + `${((performance.now() - t0) / 1000).toFixed(1)} s. Downloaded.`;
      } catch (e) {
        progTxt.innerHTML = `<span style="color:#ff8f8f">${e.message}</span>`;
        console.error(e);
      } finally { btn.disabled = false; }
    },
  }, 'Render PNG sequence');
  btn.disabled = !temAnimacao(l);

  return h('div', {},
    temAnimacao(l)
      ? h('p.nota', {}, `${quadrosDaLinha(l)} frames over ${l.duracao} s at ${l.fps} fps — `
        + 'the timeline exactly, one PNG per frame, in one ZIP.')
      : h('div.aviso', { html: 'This scene has no timeline. Open <b>Motion…</b> in the dock '
        + 'and write one — a flight, or one of the four old motions.' }),
    campo('width', larg), campo('aspect', proporcao), campo('supersample', ss),
    h('div.aviso', { html:
      'A PNG sequence is the way out to a real video codec, which a browser '
      + 'does not have. Feed it to ffmpeg:<br>'
      + `<code>ffmpeg -framerate ${l.fps} -i quadro_%04d.png -c:v libx264 -pix_fmt yuv420p out.mp4</code>`
      + '<br>The ZIP is <b>stored, not compressed</b> — PNG is already deflated, so '
      + 'compressing it again buys nothing and costs a compressor.' }),
    h('p.nota', {}, 'A transparent background keeps its alpha, frame by frame — '
      + 'combined with the shadow-catcher ground that is an aeroplane and its '
      + 'shadow over nothing, which is what a composite wants.'),
    caixaProg,
    h('div.rodape', {}, est, btn));
}

/* --- embed --------------------------------------------------------------- */

function abaEmbed (ctx) {
  const modo = sel('emb-modo', [
    { v: 'relativo', r: 'relative — save the file INSIDE estudio/' },
    { v: 'irmao', r: 'sibling — file next to the .glb files, estudio/ alongside' },
    { v: 'url', r: 'absolute URLs — hosted somewhere else' },
  ], 'relativo');
  const baseEstudio = h('input', { type: 'text', id: 'emb-be', value: 'https://example.com/estudio/' });
  const baseGlb = h('input', { type: 'text', id: 'emb-bg', value: 'https://example.com/export/web/' });
  const autoGirar = h('input', { type: 'checkbox', id: 'emb-ag' });
  const velocidade = h('input', { type: 'number', id: 'emb-vg', step: 0.1, value: 0.4 });
  const zoom = h('input', { type: 'checkbox', id: 'emb-z', checked: true });
  const pan = h('input', { type: 'checkbox', id: 'emb-p', checked: true });
  const tocar = h('input', { type: 'checkbox', id: 'emb-t', checked: true });
  const transporte = h('input', { type: 'checkbox', id: 'emb-tr', checked: true });

  const linhaU1 = campo('estudio/ base', baseEstudio);
  const linhaU2 = campo('GLB base', baseGlb);
  /* The embed plays the timeline with the studio's own evaluator, so these two
     boxes are the only decisions left: does it start playing, and does the
     viewer get a scrubber. */
  const linhaTempo = temAnimacao(ctx.estado.linha)
    ? h('div', {},
        h('label.check', {}, tocar, ' start the timeline playing'),
        h('label.check', {}, transporte, ' show a play / scrub bar'),
        h('p.nota', {}, `This scene carries ${quadrosDaLinha(ctx.estado.linha)} frames over `
          + `${ctx.estado.linha.duracao} s. While the camera track is running the orbit `
          + 'controls stand down; pause it and the viewer gets the scene back.'))
    : h('p.nota', {}, 'No timeline in this scene — the embed will be the still, orbitable scene.');
  const precisa = h('div', { style: 'margin-top:10px' });
  const saida = h('pre', { style: 'display:none;max-height:180px' });

  function cfg () {
    return {
      modo: modo.value, baseEstudio: baseEstudio.value, baseGlb: baseGlb.value,
      autoGirar: autoGirar.checked, velocidadeGiro: +velocidade.value,
      zoom: zoom.checked, pan: pan.checked,
      tocar: tocar.checked, transporte: transporte.checked,
    };
  }

  function atualizar () {
    const url = modo.value === 'url';
    linhaU1.style.display = linhaU2.style.display = url ? '' : 'none';
    const usados = [...new Set(ctx.estado.objetos.filter(o => o.tipo !== 'prop').map(o => o.slug))]
      .map(s => acharAsset(s)).filter(Boolean);
    const be = url ? baseEstudio.value.replace(/\/?$/, '/') : (modo.value === 'irmao' ? 'estudio/' : './');
    const bg = url ? baseGlb.value.replace(/\/?$/, '/') : (modo.value === 'irmao' ? './' : '../export/web/');
    const bc = url ? baseGlb.value.replace(/\/?$/, '/') : (modo.value === 'irmao' ? './' : '../export/cenarios/');
    const bytes = usados.reduce((n, a) => n + a.bytes, 0);
    const tris = usados.reduce((n, a) => n + a.triangulos, 0);
    const lics = licencasDaCena(ctx.estado);
    /* Honesty about weight, before the download and not after: 15 MB of GLB on
       a phone is a page that hangs, and the dialog has to say so. */
    const pesado = bytes > 12e6 || tris > 900e3;
    precisa.innerHTML =
      `<h4>What the embed needs alongside it</h4>
       <table>
         <tr><th>${be}vendor/three/</th><td>three.js r169 + Draco decoder (~2.1 MB, once)</td></tr>
         <tr><th>${be}js/</th><td>embed.js, mundo.js, props.js, frota.js, estado.js (~64 kB)</td></tr>
         ${usados.length
           ? usados.map(a => `<tr><th>${a.tipo === 'cenario' ? bc : bg}${a.arquivo.split('/').pop()}</th>`
               + `<td>${formatarBytes(a.bytes)} · ${a.triangulos.toLocaleString()} tris`
               + `${a.tipo === 'cenario' ? ' · <span style="color:#d8b263">ODbL</span>' : ''}</td></tr>`).join('')
           : '<tr><th>—</th><td>nothing but authored props in this scene</td></tr>'}
       </table>
       <p>Payload: <b>${formatarBytes(bytes)}</b>, ${tris.toLocaleString()} triangles.
          The embed does <b>not</b> need either manifest — the GLB paths are baked
          into the scene JSON inside the HTML. Nothing is fetched from a CDN.</p>
       ${pesado ? `<div class="aviso"><b>This is a heavy embed.</b>
          ${formatarBytes(bytes)} of GLB and ${tris.toLocaleString()} triangles will
          take several seconds to appear on a laptop and may not finish on a
          phone. Drop the biggest pieces, or serve the folder and link to it
          rather than putting it in an iframe on a busy page.</div>` : ''}
       <p class="nota">Licences written into the page:
          ${lics.map(l => l.nome).join(' · ')}.</p>`;
  }
  [modo, baseEstudio, baseGlb].forEach(e => e.addEventListener('input', atualizar));
  modo.addEventListener('change', atualizar);

  const btnBaixar = h('button.primaria', {
    onclick: () => {
      const html = construirEmbed(ctx.estado, ctx.mundo, cfg());
      baixar(new Blob([html], { type: 'text/html' }), nomeArquivo(ctx.estado.nome, 'html'));
    },
  }, 'Download embed .html');

  const btnSnippet = h('button', {
    onclick: () => {
      const arq = nomeArquivo(ctx.estado.nome, 'html');
      saida.style.display = '';
      saida.textContent =
        `<iframe src="${arq}" width="960" height="540" style="border:0;border-radius:8px"\n`
        + `        loading="lazy" title="${(ctx.estado.nome || 'scene').replace(/"/g, '')}"></iframe>`;
      navigator.clipboard?.writeText(saida.textContent).catch(() => {});
    },
  }, 'Copy <iframe> snippet');

  const btnVer = h('button', {
    onclick: () => {
      const html = construirEmbed(ctx.estado, ctx.mundo, cfg());
      const u = URL.createObjectURL(new Blob([html], { type: 'text/html' }));
      // A blob: page cannot resolve the relative module paths, so open the real
      // thing only in "absolute URLs" mode; otherwise just show the source.
      if (cfg().modo === 'url') open(u, '_blank');
      else { saida.style.display = ''; saida.textContent = html.slice(0, 4000) + '\n…'; }
    },
  }, 'Preview source');

  atualizar();
  return h('div', {},
    campo('paths', modo), linhaU1, linhaU2,
    h('label.check', {}, autoGirar, ' auto-rotate on load'),
    campo('rotate speed', velocidade),
    h('label.check', {}, zoom, ' allow zoom'),
    h('label.check', {}, pan, ' allow pan'),
    linhaTempo,
    precisa, saida,
    h('div.rodape', {}, h('span.estimativa', {}, 'iframe-able, self-hosted, no CDN'), btnVer, btnSnippet, btnBaixar));
}

/* --- PNG ----------------------------------------------------------------- */

function abaPng (ctx) {
  const larg = sel('png-w', [960, 1280, 1600, 1920, 2560, 3840].map(v => ({ v, r: `${v} px wide` })), 1920);
  const proporcao = sel('png-ar', [
    { v: '16:9', r: '16 : 9' }, { v: '4:3', r: '4 : 3' }, { v: '1:1', r: 'square' }, { v: 'vp', r: 'match the viewport' },
  ], '16:9');
  const ss = sel('png-ss', [{ v: 1, r: 'none' }, { v: 2, r: '2×' }, { v: 3, r: '3× (heavy)' }],
    ctx.estado.render.aa || 2);
  const est = h('div.estimativa');
  const msg = h('div.nota');

  function dims () {
    const w = +larg.value;
    let hh;
    if (proporcao.value === '16:9') hh = Math.round(w * 9 / 16);
    else if (proporcao.value === '4:3') hh = Math.round(w * 3 / 4);
    else if (proporcao.value === '1:1') hh = w;
    else hh = Math.round(w * ctx.mundo.altura / ctx.mundo.largura);
    return [w, hh];
  }
  const atualizar = () => {
    const [w, hh] = dims();
    est.textContent = `${w}×${hh}, rendered at ${w * +ss.value}×${hh * +ss.value}`
      + (ctx.estado.ambiente.fundo === 'transparente' ? ' · alpha kept' : '');
  };
  [larg, proporcao, ss].forEach(e => e.addEventListener('change', atualizar));
  atualizar();

  const btn = h('button.primaria', {
    onclick: async () => {
      const [w, hh] = dims();
      btn.disabled = true; msg.textContent = 'rendering…';
      try {
        const r = await exportarPng(ctx.mundo, { larg: w, alt: hh, ss: +ss.value });
        baixar(r.blob, nomeArquivo(ctx.estado.nome, 'png'));
        msg.innerHTML = `<b>done.</b> ${formatarBytes(r.bytes)} downloaded.`;
      } catch (e) { msg.innerHTML = `<span style="color:#ff8f8f">${e.message}</span>`; console.error(e); }
      finally { btn.disabled = false; }
    },
  }, 'Render PNG');

  return h('div', {},
    campo('width', larg), campo('aspect', proporcao), campo('supersample', ss),
    h('p.nota', {}, 'The still uses the viewport camera exactly as it stands. '
      + 'A transparent background produces a PNG with alpha; anything else is opaque.'),
    msg, h('div.rodape', {}, est, btn));
}

/* --- JSON ---------------------------------------------------------------- */

function abaJson (ctx) {
  const msg = h('div.nota');
  const arquivo = h('input', { type: 'file', accept: '.json,application/json' });
  arquivo.addEventListener('change', async () => {
    const f = arquivo.files[0];
    if (!f) return;
    try {
      const doc = JSON.parse(await f.text());
      await ctx.carregarDocumento(doc);
      msg.innerHTML = `<b>loaded</b> “${doc.nome || f.name}”.`;
    } catch (e) { msg.innerHTML = `<span style="color:#ff8f8f">${e.message}</span>`; }
  });

  const btn = h('button.primaria', {
    onclick: () => {
      const doc = documentoParaJson(ctx.estado, ctx.mundo,
        { comAssets: true, baseGlb: '../export/web/', baseCen: '../export/cenarios/' });
      baixar(new Blob([JSON.stringify(doc, null, 2)], { type: 'application/json' }),
        nomeArquivo(ctx.estado.nome, 'json'));
    },
  }, 'Download scene JSON');

  const btnCopiar = h('button', {
    onclick: () => {
      const doc = documentoParaJson(ctx.estado, ctx.mundo,
        { comAssets: true, baseGlb: '../export/web/', baseCen: '../export/cenarios/' });
      navigator.clipboard?.writeText(JSON.stringify(doc, null, 2));
      msg.textContent = 'copied to the clipboard.';
    },
  }, 'Copy to clipboard');

  return h('div', {},
    h('p.nota', {}, 'Schema latam-estudio/1. Carries the objects, their transforms, '
      + 'the sun and sky, the render settings, the camera and the two stored poses, '
      + 'an asset table mapping each slug to its GLB path and its licence, and a '
      + '`licencas` block listing what this particular scene obliges you to.'),
    h('h4', {}, 'Import'), arquivo, msg,
    h('div.rodape', {}, h('span.estimativa', {}, `${ctx.estado.objetos.length} objects`), btnCopiar, btn));
}
