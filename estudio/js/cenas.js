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

const aero = (slug, nome, x, z, ry = 0, y = 0) => {
  const o = novoObjeto('aeronave', slug, nome);
  o.pos = [x, y, z]; o.rot = [0, ry, 0];
  return o;
};
const prop = (slug, nome, x, z, ry = 0) => {
  const o = novoObjeto('prop', slug, nome);
  o.pos = [x, 0, z]; o.rot = [0, ry, 0];
  return o;
};
/* An airport piece out of export/cenarios/. Same pivot rule as an aircraft —
   origin at the X/Z bbox centre, base on y = 0 — so placement is the same
   arithmetic; `y` exists only because a zero-thickness apron slab has to sit a
   few centimetres above the studio's own ground plane or the two z-fight. */
const cen = (slug, nome, x, z, ry = 0, y = 0) => {
  const o = novoObjeto('cenario', slug, nome);
  o.pos = [x, y, z]; o.rot = [0, ry, 0];
  return o;
};

/* GRU's runways lie at 16.354° to +X in the field's own metric frame (measured
   from the threshold empties in scenario_sbgr/sbgr_field.blend, not assumed:
   10L at (-2.42, 11.21) to 28R at (3402.95, 1009.57)). An aircraft faces −X, so
   pointing one down the take-off track is 180° + that. */
const RWY_GRU = 196.354;
/* Where the 10L threshold sits inside sbgr_placa_campo's own frame, from the
   plate's recorded origin in the field: (1713.47, -403.26). Blender +Y is glTF
   −Z, which is why the second term flips sign. */
const LIM_10L = [-1715.9, -414.5];
const aoLongo = (m, x0 = LIM_10L[0], z0 = LIM_10L[1]) =>
  [x0 + m * Math.cos(16.354 * Math.PI / 180),
   z0 - m * Math.sin(16.354 * Math.PI / 180)];

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
  /* 'aeronaves' (default) frames the jets, so a 210 m backdrop card cannot
     decide the shot. 'tudo' frames everything, which is the only sane choice
     for a scene whose subject IS a 6 km field plate. */
  e.quadro = patch.quadro || 'aeronaves';
  e.assentar = !!patch.assentar;
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

/* ------------------------------------------------------- the real bases --
 * The four scenes below are the ones that prove the airport tier: they are
 * composed from measured pieces of GRU and Sao Carlos, not from boxes. Placement
 * inside a scene is still eyeballed — a stand is a stand — with one exception
 * that is not: in `campo-gru` the aircraft and the tower sit at their TRUE
 * positions on the field, computed from each asset's recorded origin. That is
 * the arithmetic check on the whole export, done where you can see it. */

Object.assign(CENAS_BASE, {

  'stand-gru': () => base({
    nome: 'Stand at GRU — A320neo at the gate',
    vista: 'tres-quartos', assentar: true,
    ambiente: {
      sol: { elev: 27, azim: 118, intensidade: 3.2, cor: '#fff0d8' },
      chao: { ligado: true, tipo: 'apron', tamanho: 1200 },
      grade: false,
    },
    render: { exposicao: 1.0, tone: 'aces', sombraPx: 2048 },
    objetos: [
      cen('sbgr_patio', 'apron slab — GRU', 0, 0, 0, 0.06),
      cen('sbgr_terminal_bloco', 'terminal block — GRU', -100, 0),
      /* The bridge's rotunda is its −X end and the cab its +X end (checked by
         eye, from above, against the aeroplane). Docked at the A320's L1 door,
         which is ~5 m aft of the nose on the port side — and port is +Z here,
         because the nose points −X and +Y is up. */
      cen('sbgr_ponte_embarque', 'jetbridge — GRU', -23, 4.2, 12),
      aero('A320neo', 'A320neo', 0, 0),
      cen('sbgr_gse_catering', 'catering', 2, -21),
      cen('sbgr_gse_loader', 'cargo loader', -7, -19),
      cen('sdsc_gse_reboque', 'tug + towbar', -27, 1, 90),
      cen('sbgr_gse_bowser', 'bowser', 12, 25, 20),
      cen('sbgr_gse_onibus', 'apron bus', 26, -30, 12),
      cen('sbgr_mastro', 'floodlight mast', 74, 84),
      cen('sbgr_mastro', 'floodlight mast', -34, -96),
    ],
  }),

  'hangar-sdsc': () => base({
    nome: 'Hangar 9 — 787-9 on the Sao Carlos MRO apron',
    vista: 'tres-quartos', assentar: true,
    ambiente: {
      /* The default framing looks in from +X,+Z, so the sun has to come from
         that side or the hangar face carrying the wordmark is the one face in
         shadow — which is exactly what azimuth 252 gave. */
      sol: { elev: 22, azim: 52, intensidade: 3.4, cor: '#ffdfb4' },
      chao: { ligado: true, tipo: 'concreto', tamanho: 1000 },
      grade: false,
    },
    render: { exposicao: 1.05, tone: 'aces', sombraPx: 2048 },
    /* Hangar 9's door faces −Z in the asset (it faces +Y in the field, and glTF
       flips that axis). The hangar is turned 180° so the door looks down +Z,
       because the three-quarter framing direction comes from +Z: leave it
       facing −Z and the hangar stands BETWEEN the camera and the aeroplane,
       which is what the first version of this scene did. The 787 is nose-in on
       that door line: −Z is −90°, and 41 m of it. */
    objetos: [
      cen('sdsc_hangar9', 'Hangar 9', 0, 0, 180),
      cen('sdsc_mro_hangar', 'MRO hangar bay', 152, 8, 180),
      aero('B789', 'Boeing 787-9', 0, 120, -90),
      cen('sdsc_doca_manutencao', 'maintenance dock', -74, 92),
      cen('sdsc_suporte_motor', 'engine stands', -72, 42),
      cen('sdsc_conteineres', 'container row', -98, -22, 90),
      cen('sdsc_gse_reboque', 'tug + towbar', 12, 104, 180),
      cen('sdsc_gse_gpu', 'GPU', -21, 108),
      cen('sdsc_gse_beltloader', 'belt loader', 27, 134),
      cen('sdsc_mastro', 'floodlight mast', 96, 136),
      cen('sdsc_mastro', 'floodlight mast', -96, 136),
      cen('sdsc_cerca', 'perimeter fence', -30, 205),
      cen('sdsc_cerca', 'perimeter fence', 30, 205),
      cen('sdsc_cerca', 'perimeter fence', 90, 205),
    ],
  }),

  'pista-gru': () => base({
    nome: 'Runway 10R at GRU — 777-300ER lined up',
    vista: 'heroi', assentar: true,
    ambiente: {
      sol: { elev: 9, azim: 96, intensidade: 3.6, cor: '#ffd39c' },
      chao: { ligado: true, tipo: 'grama', tamanho: 1800 },
      grade: false,
    },
    render: { exposicao: 1.05, tone: 'aces', sombraPx: 4096 },
    /* The section is cut 70 m before the threshold and 430 m after it, then
       rotated onto +X, so the threshold sits at local x = −175. The aeroplane
       is lined up 55 m beyond it, facing down the runway (+X = 180°). */
    objetos: [
      cen('sbgr_pista_secao', 'runway 10R threshold', 0, 0),
      /* No y here: `assentar` drops the aeroplane onto the pavement on open,
         and the pavement is 0.236 m above datum at x = −120. Hard-coding that
         number would go stale the day the section is re-cut. */
      aero('B77W', 'Boeing 777-300ER', -120, 0, 180),
      cen('sbgr_mastro_trelica', 'lattice mast', -60, 96),
      cen('sbgr_mastro_trelica', 'lattice mast', 140, -96),
    ],
  }),

  'campo-gru': () => base({
    nome: 'The whole field — GRU',
    vista: 'tres-quartos', fov: 42, quadro: 'tudo', assentar: true,
    ambiente: {
      sol: { elev: 48, azim: 140, intensidade: 3.1, cor: '#fff4e2' },
      chao: { ligado: false, tipo: 'apron', tamanho: 600 },
      /* No fog, and that is a measurement rather than a preference: framing a
         6.1 km plate puts the camera 9–18 km out, and FogExp2 at the studio's
         mildest setting (1e-4) is 70 % opaque over that path. The first version
         of this scene rendered Guarulhos as a white blob. */
      grade: false, neblina: { ligado: false, densidade: 1.2 },
    },
    render: { exposicao: 0.98, tone: 'aces', sombraPx: 2048 },
    /* 27,648 faces and 89 kB for 6.1 × 4.8 km of aerodrome. The three placed
       objects are NOT eyeballed: each sits where it sits at Guarulhos. */
    objetos: [
      cen('sbgr_placa_campo', 'GRU field plate', 0, 0),
      aero('B77W', '777-300ER rolling 10L', ...aoLongo(1400), RWY_GRU),
      aero('A320neo', 'A320neo holding short', ...aoLongo(240), RWY_GRU),
      cen('sbgr_torre', 'control tower', -1412.5, -1725.3),
    ],
  }),
});

export const ROTULOS_BASE = {
  'heroi': 'Single hero',
  'familia': 'Line-up of the family',
  'rampa-carga': 'Cargo ramp',
  'vitrine': 'Turntable showcase',
  'noite': 'Night ramp',
  'stand-gru': 'Stand at GRU',
  'hangar-sdsc': 'Hangar 9, Sao Carlos',
  'pista-gru': 'Runway 10R at GRU',
  'campo-gru': 'The whole field — GRU',
};

/** Fresh copy — starters are templates, never handed out by reference. */
export const cenaBase = chave => clonar(CENAS_BASE[chave]());
