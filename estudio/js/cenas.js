/* cenas.js — the starter scenes.
 *
 * Authored compositions, shipped with the studio. They are ordinary scene
 * documents: loading one and saving it puts a copy in the user's own library,
 * and the starters themselves are never overwritten.
 *
 * Placement note: an instance's origin is its X/Z bounding-box centre with the
 * wheels on y = 0 (see frota.js), so a line-up is a list of Z offsets and every
 * aircraft lands on the ground with pos = [x, 0, z]. Spacings below are chosen
 * against the measured spans in export/README.md — 38.2 m for the A320 family,
 * 50.9 m for the 767, 64.7 m for the 777, 60.1 m for the 787.
 */

import { estadoPadrao, novoObjeto, clonar } from './estado.js';

const aero = (slug, nome, x, z, ry = 0) => {
  const o = novoObjeto('aeronave', slug, nome);
  o.pos = [x, 0, z]; o.rot = [0, ry, 0];
  return o;
};
const prop = (slug, nome, x, z, ry = 0) => {
  const o = novoObjeto('prop', slug, nome);
  o.pos = [x, 0, z]; o.rot = [0, ry, 0];
  return o;
};

function base (patch) {
  const e = estadoPadrao();
  Object.assign(e.ambiente, patch.ambiente || {});
  if (patch.ambiente?.sol) e.ambiente.sol = { ...e.ambiente.sol, ...patch.ambiente.sol };
  if (patch.ambiente?.chao) e.ambiente.chao = { ...e.ambiente.chao, ...patch.ambiente.chao };
  if (patch.ambiente?.neblina) e.ambiente.neblina = { ...e.ambiente.neblina, ...patch.ambiente.neblina };
  Object.assign(e.render, patch.render || {});
  e.nome = patch.nome;
  e.objetos = patch.objetos;
  /* No camera position: a starter is FRAMED on open, from the measured bounding
     box of whatever it contains. Hard-coding a camera would mean re-tuning five
     scenes every time an aircraft's span changes. `vista` picks the direction. */
  e.camera = { pos: null, alvo: null, fov: patch.fov || 35, orto: false };
  e.vista = patch.vista || 'tres-quartos';
  return e;
}

export const CENAS_BASE = {
  'heroi': () => base({
    nome: 'Single hero — 777-300ER',
    vista: 'heroi',
    ambiente: {
      sol: { elev: 11, azim: 104, intensidade: 3.6, cor: '#ffd7a6' },
      chao: { ligado: true, tipo: 'apron', tamanho: 800 },
      grade: false, envIntensidade: 1.0,
    },
    render: { exposicao: 1.05, tone: 'aces', sombraPx: 2048 },
    objetos: [aero('B77W', 'Boeing 777-300ER', 0, 0)],
  }),

  'familia': () => base({
    nome: 'Line-up of the family — A320 family',
    vista: 'tres-quartos',
    ambiente: {
      sol: { elev: 38, azim: 150, intensidade: 3.2, cor: '#fff2df' },
      chao: { ligado: true, tipo: 'concreto', tamanho: 900 },
      grade: false,
    },
    objetos: [
      aero('A319',    'A319',    0, -92),
      aero('A320ceo', 'A320ceo', 0, -46),
      aero('A320neo', 'A320neo', 0, 0),
      aero('A321ceo', 'A321ceo', 0, 46),
      aero('A321neo', 'A321neo', 0, 92),
    ],
  }),

  'rampa-carga': () => base({
    nome: 'Cargo ramp — the two 767 freighters',
    vista: 'tres-quartos',
    ambiente: {
      sol: { elev: 24, azim: 205, intensidade: 3.0, cor: '#ffeccd' },
      chao: { ligado: true, tipo: 'concreto', tamanho: 700 },
      grade: false,
    },
    objetos: [
      aero('B763F',   'Boeing 767-300F',   0, 0),
      aero('B763BCF', 'Boeing 767-300BCF', 0, -78),
      prop('escada', 'stairs — fwd door', -19, 5),
      prop('mastro', 'light mast', 40, -40),
      prop('cone', 'cone', -30, 8),
      prop('cone', 'cone', -30, -8),
      prop('cone', 'cone', 26, 0),
      prop('hangar', 'hangar', 120, 40, 90),
    ],
  }),

  'vitrine': () => base({
    nome: 'Turntable showcase — 787-9',
    vista: 'tres-quartos',
    ambiente: {
      sol: { elev: 46, azim: 132, intensidade: 1.7, cor: '#ffffff' },
      envPreset: 'sala', envIntensidade: 1.45,
      fundo: 'cor', fundoCor: '#0d0f14',
      chao: { ligado: true, tipo: 'estudio', tamanho: 300 },
      grade: false,
    },
    render: { exposicao: 1.0, tone: 'aces', sombraPx: 4096 },
    // The backdrop card is what makes a sweep read as a sweep: without it the
    // ground plane simply ends and the background shows through behind it.
    objetos: [aero('B789', 'Boeing 787-9', 0, 0), prop('cartao', 'backdrop', 0, 0)],
  }),

  'noite': () => base({
    nome: 'Night ramp — A320neo at the stand',
    vista: 'heroi',
    ambiente: {
      sol: { elev: -3, azim: 300, intensidade: 0.4, cor: '#8fa6ff' },
      envIntensidade: 0.55,
      chao: { ligado: true, tipo: 'apron', tamanho: 700 },
      neblina: { ligado: true, densidade: 6 },
      grade: false,
    },
    render: { exposicao: 1.55, tone: 'agx' },
    objetos: [
      aero('A320neo', 'A320neo', 0, 0),
      prop('ponte', 'boarding bridge', -14, 26, 90),
      prop('mastro', 'light mast', 30, 55),
      prop('mastro', 'light mast', -50, 55),
      prop('terminal', 'terminal', 0, 105),
    ],
  }),
};

export const ROTULOS_BASE = {
  'heroi': 'Single hero',
  'familia': 'Line-up of the family',
  'rampa-carga': 'Cargo ramp',
  'vitrine': 'Turntable showcase',
  'noite': 'Night ramp',
};

/** Fresh copy — starters are templates, never handed out by reference. */
export const cenaBase = chave => clonar(CENAS_BASE[chave]());
