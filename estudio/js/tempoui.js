/* tempoui.js — the timeline dock.
 *
 * A track list, a ruler and a playhead. It edits `estado.linha` and nothing
 * else; every mutation goes back through main.js so that one history entry is
 * written for one user action, and SCRUBBING WRITES NOTHING — moving the
 * playhead is not an edit, and a timeline that filled the undo stack with
 * playhead positions would make undo useless exactly when you need it.
 */

import * as THREE from 'three';
import { h } from './dialogos.js';
import {
  CANAIS, EASINGS, FPS_LEGAIS_T, quadros, encaixar, apagarChave, porChave,
  temAnimacao, amostrarTrilha, tabelaDe,
} from './tempo.js';

const fmtTempo = (t, fps) => {
  const q = Math.round(t * fps);
  return `${t.toFixed(2)} s · f${q}`;
};

export class Dock {
  /**
   * @param el   the dock element
   * @param ctx  { estado, mundo, editor, aoMudar(rot), aoTempo(), aoPreset(),
   *               aoVooPainel(voo) }
   */
  constructor (el, ctx) {
    this.el = el;
    this.ctx = ctx;
    this.t = 0;          // the playhead, SNAPPED to the frame grid
    this.tBruto = 0;     // the unsnapped clock the snapping is derived from
    this.tocando = false;
    this.chaveSel = null;          // { trilhaId, t }
    this.aberto = true;
    this.construir();
  }

  get linha () { return this.ctx.estado.linha; }

  /* ------------------------------------------------------------ chrome --- */

  construir () {
    const l = this.linha;
    this.btnTocar = h('button.tocar', { title: 'Play / pause (space)', onclick: () => this.alternarTocar() }, '▶');
    this.btnInicio = h('button', { title: 'Go to start', onclick: () => this.irPara(0) }, '⏮');
    this.btnFim = h('button', { title: 'Go to end', onclick: () => this.irPara(this.linha.duracao) }, '⏭');
    this.btnLoop = h('button', { title: 'Loop', onclick: () => { this.linha.loop = !this.linha.loop; this.ctx.aoMudar('timeline loop'); this.desenhar(); } }, '⟲');

    this.campoDur = h('input.num', { type: 'number', min: 0.4, max: 120, step: 0.5, value: l.duracao, title: 'clip length, seconds' });
    this.campoDur.addEventListener('change', () => {
      const v = THREE.MathUtils.clamp(+this.campoDur.value || 8, 0.4, 120);
      this.linha.duracao = +v.toFixed(3);
      this.t = Math.min(this.t, this.linha.duracao);
      this.ctx.aoMudar('clip length');
      this.desenhar();
    });

    this.campoFps = h('select', { title: 'frame rate — only rates whose GIF delay is a whole centisecond' },
      FPS_LEGAIS_T.map(f => {
        const o = h('option', { value: f }, `${f} fps`);
        if (f === l.fps) o.selected = true;
        return o;
      }));
    this.campoFps.addEventListener('change', () => {
      this.linha.fps = +this.campoFps.value;
      this.ctx.aoMudar('frame rate');
      this.desenhar();
    });

    this.btnAuto = h('button', {
      title: 'Auto-key: moving anything at the playhead writes a key there',
      onclick: () => { this.linha.autochave = !this.linha.autochave; this.ctx.aoMudar('auto-key'); this.desenhar(); },
    }, 'auto-key');
    this.btnChave = h('button', { title: 'Key the selection\'s position, rotation and scale here (K)', onclick: () => this.ctx.aoChavear() }, '◆ key');
    this.btnPreset = h('button.primaria', { title: 'Flight and motion presets — they write keys you can then edit', onclick: () => this.ctx.aoPreset() }, 'Motion…');
    this.btnLimpar = h('button', { title: 'Remove every track and flight', onclick: () => this.limpar() }, 'clear');

    this.leitura = h('span.leitura');
    this.marcaTempo = h('span.tmp');

    this.barra = h('div.tempo-barra', {},
      this.btnInicio, this.btnTocar, this.btnFim, this.btnLoop,
      h('span.hud-sep'),
      h('label.mini-campo', {}, h('span', {}, 'length'), this.campoDur, h('i', {}, 's')),
      this.campoFps,
      h('span.hud-sep'),
      this.btnAuto, this.btnChave, this.btnPreset, this.btnLimpar,
      h('span.hud-sep'),
      this.marcaTempo, this.leitura);

    this.regua = h('div.tempo-regua');
    this.cabeca = h('div.tempo-cabeca');
    this.regua.append(this.cabeca);
    this.trilhas = h('div.tempo-trilhas');
    this.pistas = h('div.tempo-pistas', {}, this.regua, this.trilhas);

    this.el.textContent = '';
    this.el.append(this.barra, this.pistas);
    this.ligarArrastoRegua();
    this.desenhar();
  }

  /* --------------------------------------------------------- scrubbing --- */

  ligarArrastoRegua () {
    const puxar = e => {
      const r = this.regua.getBoundingClientRect();
      const u = THREE.MathUtils.clamp((e.clientX - r.left) / r.width, 0, 1);
      this.irPara(encaixar(this.linha, u * this.linha.duracao));
    };
    this.regua.addEventListener('pointerdown', e => {
      this.regua.setPointerCapture(e.pointerId);
      this.arrastando = true; this.parar(); puxar(e);
    });
    this.regua.addEventListener('pointermove', e => { if (this.arrastando) puxar(e); });
    const soltar = e => { this.arrastando = false; try { this.regua.releasePointerCapture(e.pointerId); } catch (x) { /* already gone */ } };
    this.regua.addEventListener('pointerup', soltar);
    this.regua.addEventListener('pointercancel', soltar);
  }

  irPara (t) {
    this.t = THREE.MathUtils.clamp(t, 0, this.linha.duracao);
    this.tBruto = this.t;
    this.atualizarCabeca();
    this.ctx.aoTempo();
  }

  passo (n) { this.irPara(this.t + n / this.linha.fps); }

  alternarTocar () { this.tocando ? this.parar() : this.tocar(); }
  tocar () {
    if (!temAnimacao(this.linha)) return;
    if (this.t >= this.linha.duracao - 1e-6) this.t = 0;
    this.tBruto = this.t;
    this.tocando = true; this.btnTocar.textContent = '⏸';
    this.btnTocar.classList.add('ativo');
  }
  parar () {
    if (!this.tocando) return;
    this.tocando = false; this.btnTocar.textContent = '▶';
    this.btnTocar.classList.remove('ativo');
    this.ctx.aoParar && this.ctx.aoParar();
  }

  /** Advance the clock. Called from main.js's render loop with real seconds.
   *
   *  The playhead is SNAPPED to the frame grid, so what you watch is what the
   *  GIF contains — a preview on wall-clock time shows in-between poses no
   *  exported frame will ever hold.
   *
   *  But the snapping must NOT feed back into the clock, and doing that is a
   *  bug that stops playback dead without an error: on a 120 Hz display each
   *  frame adds 1/120 s, which for a 20 fps timeline is 0.17 of a frame and
   *  rounds straight back to the frame it started on. The playhead sat at 0.20 s
   *  for as long as you cared to watch, with the render loop running at 240
   *  draw calls a second behind it. So the real clock accumulates in `tBruto`
   *  and `t` is derived from it — never the other way round. */
  avancar (dt) {
    if (!this.tocando) return false;
    const l = this.linha;
    this.tBruto += dt;
    if (this.tBruto >= l.duracao) {
      if (l.loop) this.tBruto = this.tBruto % l.duracao;
      else { this.tBruto = l.duracao; this.parar(); }
    }
    const antes = this.t;
    this.t = Math.min(l.duracao, Math.round(this.tBruto * l.fps) / l.fps);
    this.atualizarCabeca();
    return this.t !== antes;
  }

  atualizarCabeca () {
    const l = this.linha;
    const u = l.duracao > 0 ? this.t / l.duracao : 0;
    this.cabeca.style.left = `${(u * 100).toFixed(4)}%`;
    this.marcaTempo.textContent = `${fmtTempo(this.t, l.fps)} / ${l.duracao.toFixed(2)} s`;
    for (const el of this.el.querySelectorAll('.tempo-cabeca-linha')) {
      el.style.left = `${(u * 100).toFixed(4)}%`;
    }
  }

  /** The flight telemetry, so the derived model can be checked rather than
   *  believed. This is the whole reason it is on screen. */
  mostrarVoo (info) {
    if (!info) { this.leitura.textContent = ''; return; }
    this.leitura.textContent =
      `${info.v.toFixed(1)} m/s · vs ${info.vs >= 0 ? '+' : ''}${info.vs.toFixed(2)} m/s · `
      + `pitch ${info.pitch.toFixed(1)}° · bank ${info.banco.toFixed(1)}° · `
      + `agl ${info.alt.toFixed(1)} m`;
  }

  /* ------------------------------------------------------------- tracks --- */

  rotuloTrilha (tr) {
    const def = CANAIS[tr.canal];
    if (!def) return tr.canal;
    if (def.alvo !== 'objeto') return def.rot;
    const d = this.ctx.estado.objetos.find(o => o.id === tr.ref);
    return `${d ? d.nome : '(gone)'} · ${def.rot}`;
  }

  desenhar () {
    const l = this.linha;
    this.btnLoop.classList.toggle('ativo', !!l.loop);
    this.btnAuto.classList.toggle('ativo', !!l.autochave);
    this.campoDur.value = l.duracao;
    this.campoFps.value = l.fps;

    /* ruler ticks — one per second, plus the frame count */
    this.regua.querySelectorAll('.tick').forEach(e => e.remove());
    const seg = Math.max(1, Math.ceil(l.duracao / 12));
    for (let s = 0; s <= l.duracao + 1e-6; s += seg) {
      const u = s / l.duracao;
      this.regua.append(h('span.tick', { style: `left:${(u * 100).toFixed(3)}%` }, `${s.toFixed(seg < 1 ? 1 : 0)}s`));
    }

    this.trilhas.textContent = '';
    const total = quadros(l);
    if (!temAnimacao(l)) {
      this.trilhas.append(h('p.nota.vazio', {},
        'No tracks yet. Move something with auto-key on, press ',
        h('b', {}, '◆ key'), ', or open ', h('b', {}, 'Motion…'),
        ' for a take-off, a landing, a flypast or one of the four old GIF motions — '
        + 'each of which now writes keys you can drag.'));
    }

    for (const v of l.voos || []) this.trilhas.append(this.linhaVoo(v));
    for (const tr of l.trilhas || []) this.trilhas.append(this.linhaTrilha(tr));

    if (temAnimacao(l)) {
      this.trilhas.append(h('p.nota', {},
        `${total} frames at ${l.fps} fps — ${(100 / l.fps).toFixed(0)} cs a frame, `
        + `which is why only these rates are offered.`));
    }
    this.atualizarCabeca();
  }

  linhaTrilha (tr) {
    const l = this.linha;
    const def = CANAIS[tr.canal] || {};
    const pista = h('div.pista');
    for (const c of tr.chaves) {
      const u = l.duracao > 0 ? c.t / l.duracao : 0;
      const k = h('i.chave', {
        style: `left:${(u * 100).toFixed(4)}%`,
        title: `${c.t.toFixed(2)} s — ${Array.isArray(c.v) ? c.v.map(n => (+n).toFixed(2)).join(', ') : c.v}\n`
             + `${c.e} · drag to retime, click to select`,
        'data-e': c.e,
      });
      if (this.chaveSel && this.chaveSel.trilhaId === tr.id && Math.abs(this.chaveSel.t - c.t) < 1e-6) {
        k.classList.add('sel');
      }
      this.ligarChave(k, tr, c);
      pista.append(k);
    }
    pista.append(h('i.tempo-cabeca-linha'));
    return h('div.trilha', {},
      h('span.rot', { title: tr.canal }, this.rotuloTrilha(tr)),
      h('button.mini', {
        title: tr.mudo ? 'unmute this track' : 'mute this track',
        onclick: () => { tr.mudo = !tr.mudo; this.ctx.aoMudar('mute track'); this.desenhar(); this.ctx.aoTempo(); },
      }, tr.mudo ? '⃠' : '●'),
      h('button.mini', {
        title: 'delete this track',
        onclick: () => {
          l.trilhas = l.trilhas.filter(x => x !== tr);
          this.ctx.aoMudar('delete track'); this.desenhar(); this.ctx.aoTempo();
        },
      }, '✕'),
      pista,
      h('span.unid', {}, def.unidade || ''));
  }

  /** Click selects, drag retimes. A key dragged onto another key's frame
   *  replaces it, which is what every DCC does and what people expect. */
  ligarChave (el, tr, c) {
    let arrastou = false;
    el.addEventListener('pointerdown', e => {
      e.stopPropagation();
      el.setPointerCapture(e.pointerId);
      arrastou = false;
      const pista = el.parentElement;
      const mover = ev => {
        const r = pista.getBoundingClientRect();
        const u = THREE.MathUtils.clamp((ev.clientX - r.left) / r.width, 0, 1);
        const t = encaixar(this.linha, u * this.linha.duracao);
        if (Math.abs(t - c.t) > 1e-6) {
          arrastou = true;
          tr.chaves = tr.chaves.filter(x => x === c || Math.abs(x.t - t) > 1e-6);
          c.t = t;
          tr.chaves.sort((a, b) => a.t - b.t);
          this.desenhar();
          this.irPara(t);
        }
      };
      const soltar = ev => {
        el.removeEventListener('pointermove', mover);
        try { el.releasePointerCapture(ev.pointerId); } catch (x) { /* gone */ }
        if (arrastou) this.ctx.aoMudar('retime key');
        else { this.chaveSel = { trilhaId: tr.id, t: c.t }; this.desenhar(); this.irPara(c.t); }
        this.mostrarEditorChave(tr, c);
      };
      el.addEventListener('pointermove', mover);
      el.addEventListener('pointerup', soltar, { once: true });
    });
  }

  /** The per-key easing control. It lives next to the key rather than in a
   *  panel because the choice is about THAT key's outgoing segment. */
  mostrarEditorChave (tr, c) {
    this.el.querySelectorAll('.editor-chave').forEach(e => e.remove());
    const s = h('select', {}, EASINGS.map(o => {
      const op = h('option', { value: o.v }, o.r);
      if (o.v === c.e) op.selected = true;
      return op;
    }));
    s.addEventListener('change', () => {
      c.e = s.value;
      this.ctx.aoMudar('key easing'); this.desenhar(); this.ctx.aoTempo();
    });
    const cx = h('div.editor-chave', {},
      h('b', {}, `key @ ${c.t.toFixed(2)} s`), s,
      h('button.mini', {
        title: 'delete this key (Del)',
        onclick: () => { this.apagarSelecionada(); },
      }, '✕ key'));
    this.barra.append(cx);
  }

  apagarSelecionada () {
    if (!this.chaveSel) return false;
    if (apagarChave(this.linha, this.chaveSel.trilhaId, this.chaveSel.t)) {
      this.chaveSel = null;
      this.el.querySelectorAll('.editor-chave').forEach(e => e.remove());
      this.ctx.aoMudar('delete key');
      this.desenhar(); this.ctx.aoTempo();
      return true;
    }
    return false;
  }

  linhaVoo (v) {
    const l = this.linha;
    const d = this.ctx.estado.objetos.find(o => o.id === v.ref);
    const tab = tabelaDe(v);
    const dur = tab ? tab.dur : l.duracao;
    const u0 = THREE.MathUtils.clamp((v.t0 || 0) / l.duracao, 0, 1);
    const u1 = THREE.MathUtils.clamp(((v.t0 || 0) + dur) / l.duracao, 0, 1);
    const barra = h('i.faixa-voo', {
      style: `left:${(u0 * 100).toFixed(3)}%;width:${((u1 - u0) * 100).toFixed(3)}%`,
      title: tab
        ? `${tab.comprimento.toFixed(0)} m of path, ${tab.dur.toFixed(2)} s`
          + (tab.tLift !== null ? `, wheels off at ${tab.tLift.toFixed(2)} s` : '')
        : 'route not built yet',
    }, v.rotulo);
    const pista = h('div.pista.voo', {}, barra, h('i.tempo-cabeca-linha'));
    return h('div.trilha.voo', {},
      h('span.rot', { title: 'a flight: the path is keyed, the attitude is derived' },
        `✈ ${d ? d.nome : '(gone)'} · ${v.rotulo}`),
      h('button.mini', { title: 'flight parameters', onclick: () => this.ctx.aoVooPainel(v) }, '⚙'),
      h('button.mini', {
        title: 'delete this flight',
        onclick: () => {
          l.voos = l.voos.filter(x => x !== v);
          this.ctx.aoMudar('delete flight'); this.desenhar(); this.ctx.aoTempo();
        },
      }, '✕'),
      pista);
  }

  limpar () {
    if (!temAnimacao(this.linha)) return;
    if (!confirm('Remove every track and every flight from this timeline?')) return;
    this.linha.trilhas = [];
    this.linha.voos = [];
    this.chaveSel = null;
    this.parar();
    this.ctx.aoMudar('clear timeline');
    this.desenhar();
    this.ctx.aoTempo();
  }

  /** Value of a channel at the playhead, for the inspector read-out. */
  valorEm (canal, ref) {
    const tr = (this.linha.trilhas || []).find(t => t.canal === canal && (t.ref || null) === (ref || null));
    return tr ? amostrarTrilha(tr, this.t) : null;
  }

  /** Write a key on every channel of a target at the playhead. */
  chavear (canal, ref, valor) {
    porChave(this.linha, canal, ref, this.t, valor);
  }
}
