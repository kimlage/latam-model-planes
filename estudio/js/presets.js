/* presets.js — recipes that WRITE a timeline.
 *
 * Two families, and they exist for the same reason: nothing in this studio
 * should be a motion you cannot then edit. The four canned GIF motions the
 * studio shipped before the timeline existed are still here, but they are now
 * timeline WRITERS — pick "turntable", get thirty-three camera keys you can drag.
 * Nothing is lost and everything becomes editable.
 *
 * The flight recipes are the other family, and they are the point of the
 * exercise: two clicks and a 777 rolls, rotates about its main gear, and
 * climbs at an eleven per cent gradient with the bank and pitch derived from
 * where it is going. See tempo.js §flight for the maths and for where every
 * number below was measured.
 */

import * as THREE from 'three';
import {
  novoVoo, porChave, garantirTrilha, encaixar, amostrarVoo, quadros, tabelaDe,
} from './tempo.js';

/* ------------------------------------------------------------- helpers --- */

/** Forward unit vector for a heading in degrees. The nose is local −X, so a
 *  rotation of ry about +Y sends (−1,0,0) to (−cos ry, 0, sin ry). Verified
 *  against cenas.js, where GRU's 10L track (16.354° off +X) is written 196.354. */
export function frente (ryGraus) {
  const r = THREE.MathUtils.degToRad(ryGraus);
  return new THREE.Vector3(-Math.cos(r), 0, Math.sin(r));
}

const ponto = (o, f, d, alt, v) => ({
  x: +(o.x + f.x * d).toFixed(3), z: +(o.z + f.z * d).toFixed(3),
  alt: +alt.toFixed(3), v: +v.toFixed(2),
});

/* -------------------------------------------------------------- flight --- */

/* Two calibrations, measured off the two clips this repository has shipped.
 * The chooser is the aircraft's own measured length, so an A319 is light and a
 * 777 is heavy without a table of type names anywhere — and a twelfth aircraft
 * exported tomorrow lands on the right side of the line on its own. */
export const PERFIS = {
  pesado: {
    rot: 'heavy — measured off the GRU 777-300ER departure',
    vLift: 83, accel: 1.4, taxaRot: 3.1, pitchDec: 12.0,
    gradiente: 0.11, vSubida: 86, alfaRef: 6.6, vRef: 86,
    rampa: 240,                 // m over which the climb rate reaches 95 %
    vApp: 71, vTouch: 68, desacel: 1.6,
    fonte: 'scenario_sbgr/place_777.py — 3.1 °/s to 12°, 9.5 m/s against 86 m/s',
  },
  leve: {
    rot: 'light — measured off the São Carlos A320 ferry departure',
    vLift: 58, accel: 1.6, taxaRot: 3.5, pitchDec: 13.0,
    gradiente: 0.21, vSubida: 75, alfaRef: 7.0, vRef: 75,
    rampa: 150,
    vApp: 62, vTouch: 59, desacel: 1.8,
    fonte: 'scenario_sdsc/place_aircraft.py — airborne 1150 m into a 1672 m TORA, 21 %',
  },
};

export const perfilPara = comprimento => (comprimento >= 55 ? PERFIS.pesado : PERFIS.leve);

/**
 * The climb profile, as height above the runway a distance x past lift-off.
 *
 *   alt(x) = G·(x − Lₑ(1 − e^{−x/Lₑ}))     so   tan γ(x) = G·(1 − e^{−x/Lₑ})
 *
 * i.e. the gradient approaches G exponentially, which means the climb rate has
 * its MAXIMUM DERIVATIVE at lift-off. That is the whole point, and it is the
 * fix commit 96a2371 made in Blender for exactly the same reason: the previous
 * curve was a smoothstep, whose derivative at lift-off is zero, and the 777
 * left the ground at 0.006 m/s and appeared to stick to the pavement.
 *
 * The knots below are DENSE for the first 120 m for a second, subtler reason:
 * the interpolator is monotone (PCHIP), and at a knot where a flat segment
 * meets a climbing one the Fritsch–Carlson limiter sets the tangent to zero —
 * the same dead knot, reintroduced by the interpolation rather than by the
 * profile. Sampling the exponential every 25 m through the transition keeps the
 * curve honest between the knots the limiter flattens.
 */
const altClimb = (x, G, Le) => G * (x - Le * (1 - Math.exp(-x / Le)));
const ESTACOES_SUBIDA = [0, 25, 60, 120, 240, 420, 650, 950, 1300, 1800, 2400];

/**
 * Build a take-off.
 * @param ctx { pos:[3], ry, comprimento, xg, yg }   the aircraft as it stands
 * @param opc { duracao }
 */
export function vooDecolagem (ctx, opc = {}) {
  const P = perfilPara(ctx.comprimento);
  const D = opc.duracao || 8;
  const f = frente(ctx.ry);
  /* The path is the track of the MAIN-GEAR CONTACT, so the route starts where
     the wheels are, not where the object's origin is. */
  const o = new THREE.Vector3(ctx.pos[0], 0, ctx.pos[2])
    .addScaledVector(new THREE.Vector3(Math.cos(THREE.MathUtils.degToRad(ctx.ry)), 0,
                                       -Math.sin(THREE.MathUtils.degToRad(ctx.ry))), ctx.xg);

  /* How long the aeroplane is on the runway. Solving backwards from the
     lift-off speed rather than forwards from a start speed is what makes the
     recipe scale: ask for 6 seconds and the aeroplane simply opens later in its
     own roll, which is exactly what the GRU Blender clip does — it opens 2 170 m
     into the take-off, because a loaded 777 spends 50 s on the runway and the
     clip has 9.6.
     The floor is the one that had to be found by looking: the rotation ITSELF
     takes pitchDec/taxaRot = 3.9 s for a 777, so a roll shorter than that plus a
     margin has the nose coming up in the first frame — which the flight panel
     reported as "rotation starts at −31 m", i.e. before the clip begins. A clip
     too short to hold both keeps the nosewheel down for 1.2 s and no less. */
  const tRot = P.pitchDec / P.taxaRot;
  const tRoll = Math.min(0.72 * D, Math.max(0.45 * D, tRot + 1.2));
  const v0 = Math.max(12, P.vLift - P.accel * tRoll);
  const dRoll = (P.vLift ** 2 - v0 ** 2) / (2 * P.accel);
  const rota = [];
  for (const g of [0, 0.25, 0.5, 0.75, 1]) {
    const d = dRoll * g;
    rota.push(ponto(o, f, d, 0, Math.sqrt(v0 * v0 + 2 * P.accel * d)));
  }
  const Le = P.rampa / 3;                    // tan γ is 95 % of G at x = rampa
  const dAr = (P.vSubida * 0.98) * (D - tRoll);
  for (const x of ESTACOES_SUBIDA) {
    if (x === 0) continue;                   // the lift-off knot is already there
    if (x > dAr * 1.25) break;
    rota.push(ponto(o, f, dRoll + x, altClimb(x, P.gradiente, Le),
                    P.vSubida + (P.vLift - P.vSubida) * Math.exp(-x / 300)));
  }

  const voo = novoVoo(ctx.id, {
    rotulo: 'take-off',
    rota,
    taxaRot: P.taxaRot, pitchDec: P.pitchDec,
    /* Rotate exactly long enough to reach the take-off attitude AT lift-off —
       capped at 90 % of the roll, so there is always some nosewheel-down
       pavement to see. The Blender profile picked 32 frames and then jumped the
       pitch from 4° to 12° in a single frame; a rate limiter cannot do that,
       and it should not. */
    rotacao: +Math.min(tRot * P.vLift, dRoll * 0.9).toFixed(1),
    alfaRef: P.alfaRef, vRef: P.vRef,
    taxaBanco: 6, bancoMax: 15,
  });
  return { voo, perfil: P, dRoll, v0 };
}

/** Build a landing whose TOUCHDOWN is where the aircraft stands now. */
export function vooPouso (ctx, opc = {}) {
  const P = perfilPara(ctx.comprimento);
  const D = opc.duracao || 8;
  const f = frente(ctx.ry);
  const o = new THREE.Vector3(ctx.pos[0], 0, ctx.pos[2])
    .addScaledVector(new THREE.Vector3(Math.cos(THREE.MathUtils.degToRad(ctx.ry)), 0,
                                       -Math.sin(THREE.MathUtils.degToRad(ctx.ry))), ctx.xg);

  const tAr = 0.62 * D;
  const dApp = P.vApp * tAr;
  const dFlare = Math.min(260, dApp * 0.55);
  const gs = Math.tan(THREE.MathUtils.degToRad(3));      // the 3° glideslope

  /* THE FLARE, and the first version of it was wrong in a way only measuring
     found. It was an exponential in distance-to-go, `(e^{3d/dF} − 1)/(e³ − 1)`,
     which is flat near the wheels — a lovely soft touchdown — and therefore
     STEEP at the top, because all the height it had to lose was still there.
     The flight panel read −9.63 m/s peak descent on what is meant to be a 3°
     approach at 71 m/s, i.e. 3.7. The aeroplane dived into its own flare.
     What a flare actually is, is the descent rate bleeding off: the path's
     SLOPE goes linearly from the glideslope to almost nothing over the last
     dFlare metres, so integrating it gives a quadratic —
        h(d) = s₀·d + (gs − s₀)·d²/(2·dF),  s₀ = 0.6 m/s worth of slope
     which is continuous in BOTH height and slope at the top of the flare, and
     therefore has no dive anywhere. The straight glideslope above it starts
     from the height the flare integral actually reaches, not from gs·dF —
     getting that wrong is what puts a 5 m step in the approach. */
  const sToque = 0.6 / P.vApp;                    // ≈0.6 m/s at the wheels
  const hFlare = dFlare * (sToque + gs) / 2;
  const altDe = d => (d >= dFlare
    ? hFlare + gs * (d - dFlare)
    : sToque * d + (gs - sToque) * d * d / (2 * dFlare));

  const rota = [];
  const estacoes = [...new Set([dApp, dApp * 0.75, dFlare * 1.5, dFlare,
                                dFlare * 0.72, dFlare * 0.5, dFlare * 0.32,
                                dFlare * 0.18, dFlare * 0.08, dFlare * 0.03, 0]
    .filter(d => d <= dApp).map(d => +d.toFixed(2)))].sort((a, b) => b - a);
  for (const d of estacoes) rota.push(ponto(o, f, dApp - d, altDe(d), P.vApp));
  /* Rollout: decelerating, wheels down, the limiter de-rotates the nose. */
  let v = P.vTouch, d = 0;
  for (let k = 0; k < 6; k++) {
    const dt = (D - tAr) / 6;
    d += v * dt; v = Math.max(18, v - P.desacel * dt);
    rota.push(ponto(o, f, dApp + d, 0, v));
  }

  const voo = novoVoo(ctx.id, {
    rotulo: 'landing',
    rota,
    taxaRot: P.taxaRot, pitchDec: P.pitchDec, rotacao: 0,
    /* The approach attitude comes out of the same α law, referenced at the
       approach speed: pitch = γ + α = −3° + 7.5° ≈ 4.5° nose-up on the slope,
       rising through the flare as γ goes to zero. */
    alfaRef: 7.5, vRef: P.vApp,
    taxaBanco: 5, bancoMax: 8,
  });
  return { voo, perfil: P, dApp };
}

/** A flypast: no ground contact, and a turn through the pass so the bank the
 *  model derives is actually visible. Bank is not keyed anywhere — it comes out
 *  of tan φ = v ψ̇ / g and the roll-rate limiter. */
export function vooPassagem (ctx, opc = {}) {
  const D = opc.duracao || 8;
  const alt = opc.altitude ?? 90;
  const v = opc.velocidade ?? 100;
  const giro = opc.giro ?? 20;                    // ° of heading change over the pass
  const o = new THREE.Vector3(ctx.pos[0], 0, ctx.pos[2]);
  /* Integrate the heading along the pass rather than lay a circle out by
     trigonometry: the waypoints then sit on the arc the aeroplane actually
     flies, and the derived bank is the bank that arc demands. */
  const NP = 60, Lp = v * D, passo = Lp / NP;
  const bruto = [new THREE.Vector3()];
  for (let i = 1; i <= NP; i++) {
    const psi = ctx.ry - giro / 2 + giro * ((i - 0.5) / NP);
    bruto.push(bruto[i - 1].clone().addScaledVector(frente(psi), passo));
  }
  /* Shift so the aeroplane passes through where it stands now, at half time. */
  const desloc = o.clone().sub(bruto[Math.round(NP / 2)]);
  const rota = [];
  for (let k = 0; k <= 10; k++) {
    const p = bruto[Math.round(NP * k / 10)].clone().add(desloc);
    rota.push({ x: +p.x.toFixed(3), z: +p.z.toFixed(3), alt: +alt.toFixed(2), v });
  }
  const voo = novoVoo(ctx.id, {
    rotulo: 'flypast', rota,
    taxaRot: 4, pitchDec: 10, rotacao: 0,
    alfaRef: 6.6, vRef: 86, taxaBanco: 9, bancoMax: 30,
  });
  return { voo, perfil: null };
}

export const RECEITAS_VOO = {
  decolagem: { rot: 'Take-off — roll, rotate, climb out', fn: vooDecolagem },
  pouso:     { rot: 'Landing — 3° approach, flare, rollout', fn: vooPouso },
  passagem:  { rot: 'Flypast — low pass with a banked turn', fn: vooPassagem },
};

/* -------------------------------------------------- the camera that sees it -
 * A flight preset that leaves the camera where it was gives you a beautiful
 * take-off happening off-screen. These write a camera track sampled FROM the
 * flight, so the shot is framed on the aeroplane's real path rather than on a
 * guess about it. */

export function cameraParaVoo (estado, voo, ctxVoo, tipo, D, escala = 60) {
  const l = estado.linha;
  const amostra = u => amostrarVoo(voo, (voo.t0 || 0) + u * D, ctxVoo);
  const a0 = amostra(0), a2 = amostra(1);
  if (!a0 || !a2) return false;
  const p0 = new THREE.Vector3().fromArray(a0.pos);
  const p2 = new THREE.Vector3().fromArray(a2.pos);
  const em = u => new THREE.Vector3().fromArray(amostra(u).pos);

  /* Sideways from the track, so the camera is never in the aeroplane's way. */
  const eixo = p2.clone().sub(p0).setY(0).normalize();
  const lado = new THREE.Vector3(-eixo.z, 0, eixo.x);
  const span = p0.distanceTo(p2);
  /* The stand-off is set by the SUBJECT, not by the path. The first version of
     this scaled it to 22 % of the path length, which for an 825 m take-off put
     the camera 181 m out and made a 74 m aeroplane a speck between two
     floodlight masts. 1.75 aircraft lengths puts the aeroplane across most of a
     35° frame as it passes, which is what a runway-side lens actually gives. */
  const fora = Math.max(80, escala * 1.75);
  const olho = escala * 0.09;                 // the fuselage centre, not the wheels

  let cam0, cam1;
  if (tipo === 'passagem') {
    /* Abeam the closest point, low, so the pass crosses the frame. */
    cam0 = em(0.5).clone().addScaledVector(lado, fora * 1.4); cam0.y = 12;
    cam1 = cam0.clone().addScaledVector(eixo, span * 0.05); cam1.y = 20;
  } else if (tipo === 'pouso') {
    /* Beyond the touchdown, off to one side, looking back up the approach: the
       aeroplane comes at the lens and settles onto the pavement in front of it. */
    cam0 = em(0.86).clone().addScaledVector(lado, fora); cam0.y = 11;
    cam1 = cam0.clone().addScaledVector(eixo, span * 0.03); cam1.y = 8;
  } else {
    /* Abeam the point the wheels leave, so the aeroplane rolls INTO the frame,
       rotates in it, and climbs out of it. */
    cam0 = em(0.66).clone().addScaledVector(lado, fora); cam0.y = 7.5;
    cam1 = cam0.clone().addScaledVector(eixo, span * 0.05); cam1.y = 16;
  }

  const camT = garantirTrilha(l, 'camera.pos');
  const alvT = garantirTrilha(l, 'camera.alvo');
  camT.chaves = []; alvT.chaves = [];
  porChave(l, 'camera.pos', null, 0, cam0.toArray().map(n => +n.toFixed(2)));
  porChave(l, 'camera.pos', null, D, cam1.toArray().map(n => +n.toFixed(2)));
  /* The target follows the aeroplane: seven samples of the flight itself, so
     the pan is exactly as fast as the aeroplane is, at every instant — and
     PCHIP through them does not overshoot, which a Catmull-Rom would, sending
     the framing past the aeroplane at every knot. */
  for (const u of [0, 1 / 6, 2 / 6, 0.5, 4 / 6, 5 / 6, 1]) {
    const a = amostra(u);
    if (!a) continue;
    porChave(l, 'camera.alvo', null, encaixar(l, u * D),
      [+(a.pos[0]).toFixed(2), +(a.pos[1] + olho).toFixed(2), +(a.pos[2]).toFixed(2)]);
  }
  return true;
}

/* ------------------------------------------------------------ applying --- */

/**
 * Build a flight for one aircraft and write it into the timeline.
 *
 * The recipe reads the aeroplane WHERE IT STANDS — its position, its heading
 * and its own measured main-gear offset — so "put the 777 on the threshold and
 * ask for a take-off" is the whole interaction. Nothing about GRU, or about any
 * runway, is written into this file.
 *
 * @returns { voo, resumo }  resumo is a MEASURED line, not a promise: it is read
 *          back out of the built table.
 */
export function aplicarVoo (estado, mundo, objId, tipo, opc = {}) {
  const d = estado.objetos.find(o => o.id === objId);
  if (!d) throw new Error('no such object');
  if (d.tipo !== 'aeronave') throw new Error('a flight needs an aircraft, not a ' + d.tipo);
  const receita = RECEITAS_VOO[tipo];
  if (!receita) throw new Error(`unknown flight recipe "${tipo}"`);

  const inst = mundo.objetos.get(objId);
  const cx = mundo.contextoVoo(objId, estado);
  const tam = inst ? inst.userData.tamanho : null;
  const ctx = {
    id: objId, pos: d.pos, ry: d.rot[1],
    comprimento: tam ? tam.x : 40,
    xg: cx ? cx.xg : 0, yg: cx ? cx.yg : 0,
  };
  const D = opc.duracao || estado.linha.duracao || 8;
  const { voo, perfil } = receita.fn(ctx, { ...opc, duracao: D });

  const l = estado.linha;
  /* One flight per aircraft: a second one would fight the first for the same
     position every frame and the winner would be list order. */
  l.voos = (l.voos || []).filter(v => v.ref !== objId);
  l.voos.push(voo);
  /* The clip is as long as the flight, rounded to a whole frame — a timeline
     whose last frame lands mid-key is the one frame nobody looks at. */
  const tab = amostrarVoo(voo, 0, cx) ? tabelaDe(voo) : null;
  if (tab) l.duracao = +(Math.round(tab.dur * l.fps) / l.fps).toFixed(4);

  /* The gear is a KEY, not a derived quantity: it is a thing the pilot does,
     and you should be able to drag it. Down at the start; up six seconds after
     the wheels leave, if the clip is still running by then — on the GRU 777 it
     is not, which is why that clip keeps its gear down to the last frame. */
  const trT = garantirTrilha(l, 'objeto.trem', objId);
  trT.chaves = [];
  porChave(l, 'objeto.trem', objId, 0, tipo !== 'passagem', 'segurar');
  if (tipo === 'passagem') {
    // a flypast is already clean; nothing to retract
  } else if (tipo === 'decolagem' && tab && tab.tLift !== null && tab.tLift + 6 < l.duracao) {
    porChave(l, 'objeto.trem', objId, tab.tLift + 6, false, 'segurar');
  }

  let camera = false;
  if (opc.camera !== false) camera = cameraParaVoo(estado, voo, cx, tipo, l.duracao, ctx.comprimento);

  const resumo = tab
    ? `${tab.comprimento.toFixed(0)} m of path, ${tab.dur.toFixed(2)} s`
      + (tab.tLift !== null ? `, wheels off at ${tab.tLift.toFixed(2)} s` : '')
      + `, peak bank ${Math.max(...tab.BANCO.map(Math.abs)).toFixed(1)}°`
      + `, peak climb ${Math.max(...tab.VS).toFixed(2)} m/s`
      + (perfil ? ` — ${perfil.rot}` : '')
      + (cx && !cx.temTrem ? ' — no gear meshes found: rotating about the object origin' : '')
    : 'route built';
  return { voo, resumo, camera };
}

/* ------------------------------------------- the four canned motions -------
 * Everything the GIF dialog could do before the timeline existed, expressed as
 * keys. They are no longer a parallel code path that can disagree with the
 * timeline: they ARE the timeline. */

export const RECEITAS_MOV = {
  'turntable-cena': 'Turntable — camera orbits the scene',
  'turntable-objeto': 'Turntable — spin the selected object',
  'caminho-camera': 'Camera path — pose A → pose B',
  'objeto-movel': 'Fixed camera — the selected object moves',
};

export function escreverMovimento (estado, mundo, modo, cfg = {}, selId = null) {
  const l = estado.linha;
  const D = l.duracao;
  const sentido = cfg.sentido === 'anti' ? -1 : 1;
  /* `ref` is not optional here, and defaulting it to null was a real bug: an
     object channel cleared with ref null created a SECOND, empty, ownerless
     track beside the one the keys then went into, which showed in the dock as a
     ghost row labelled "(gone)". A track is identified by channel AND owner. */
  const limpar = (canal, ref = null) => { const t = garantirTrilha(l, canal, ref); t.chaves = []; return t; };

  switch (modo) {
    case 'turntable-cena': {
      const alvo = mundo.controles.target.clone();
      const rel = mundo.camP.position.clone().sub(alvo);
      const raio = Math.hypot(rel.x, rel.z), y = rel.y;
      const a0 = Math.atan2(rel.z, rel.x);
      limpar('camera.pos'); limpar('camera.alvo');
      /* Keys on a circle, LINEAR, which makes the angular rate exactly constant
         — measured at 45.0000 °/s across every probe, which is what a turntable
         is and what PCHIP would not give (its zero end tangents would make the
         loop stop dead at the seam).
         The cost is that the path is an N-gon, not a circle: the radius wobbles
         by 1 − cos(π/N). At the sixteen keys this was first written with that is
         1.94 % — measured, and enough to pulse the subject's apparent size eight
         times a revolution. At 32 it is 0.48 %, which is not. */
      const N = 32;
      for (let i = 0; i <= N; i++) {
        const a = a0 + sentido * (i / N) * Math.PI * 2;
        porChave(l, 'camera.pos', null, encaixar(l, D * i / N), [
          +(alvo.x + raio * Math.cos(a)).toFixed(3),
          +(alvo.y + y).toFixed(3),
          +(alvo.z + raio * Math.sin(a)).toFixed(3)],
          'linear');
      }
      porChave(l, 'camera.alvo', null, 0, alvo.toArray().map(n => +n.toFixed(3)));
      return `turntable: ${N + 1} camera keys over ${D} s`;
    }
    case 'turntable-objeto': {
      if (!selId) throw new Error('spinning an object needs a selection');
      const d = estado.objetos.find(o => o.id === selId);
      limpar('objeto.rot', selId);
      /* Linear easing on every key, because a spin at a CONSTANT rate is what a
         turntable is; PCHIP through four quarter-turns would ease at each. */
      for (let i = 0; i <= 4; i++) {
        porChave(l, 'objeto.rot', selId, encaixar(l, D * i / 4),
          [d.rot[0], +(d.rot[1] + sentido * 90 * i).toFixed(3), d.rot[2]], 'linear');
      }
      return `object turntable: 5 rotation keys, linear`;
    }
    case 'caminho-camera': {
      const A = estado.poses.A, B = estado.poses.B;
      if (!A || !B) throw new Error('a camera path needs both pose A and pose B stored');
      limpar('camera.pos'); limpar('camera.alvo'); limpar('camera.fov');
      const pontos = cfg.pingpong ? [[0, A], [D / 2, B], [D, A]] : [[0, A], [D, B]];
      for (const [t, p] of pontos) {
        porChave(l, 'camera.pos', null, encaixar(l, t), p.pos);
        porChave(l, 'camera.alvo', null, encaixar(l, t), p.alvo);
        if (p.fov) porChave(l, 'camera.fov', null, encaixar(l, t), p.fov);
      }
      return `camera path: ${pontos.length} keys${cfg.pingpong ? ', ping-pong' : ''}`;
    }
    case 'objeto-movel': {
      if (!selId) throw new Error('a moving object needs a selection');
      const d = estado.objetos.find(o => o.id === selId);
      const dist = cfg.distancia || 0, sobe = cfg.subida || 0;
      const dir = cfg.direcao === 'nariz' ? frente(d.rot[1])
        : cfg.direcao === 'x' ? new THREE.Vector3(1, 0, 0) : new THREE.Vector3(0, 0, 1);
      limpar('objeto.pos', selId);
      /* Linear keys, eight segments. The horizontal travel is exactly constant
         (which PCHIP would ease at both ends) and the quadratic climb is
         sampled finely enough that the piecewise-linear error is under
         `sobe`/256 — under 4 cm on a 10 m climb. */
      for (let i = 0; i <= 8; i++) {
        const u = i / 8;
        porChave(l, 'objeto.pos', selId, encaixar(l, D * u), [
          +(d.pos[0] + dir.x * dist * u).toFixed(3),
          +(d.pos[1] + sobe * u * u).toFixed(3),
          +(d.pos[2] + dir.z * dist * u).toFixed(3)], 'linear');
      }
      return `object move: 9 position keys over ${dist} m`;
    }
    default: throw new Error(`unknown motion "${modo}"`);
  }
}

/** Frames the timeline will render, for the dialogs. */
export const quadrosDe = l => quadros(l);
