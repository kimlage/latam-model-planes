/* tempo.js — the timeline: the document, the interpolation and the flight model.
 *
 * The studio's rule is that the scene is a document and the world is a
 * projection of it (estado.js, mundo.js). The timeline obeys the same rule and
 * gets undo, save, embed and export for free: `estado.linha` is plain JSON,
 * `avaliar()` turns it into an OVERLAY at a time t, and `mundo.aplicarLinha()`
 * writes that overlay onto the world. Nothing here touches the DOM and nothing
 * here mutates the scene document — scrubbing must never write history.
 *
 * ---------------------------------------------------------------------------
 * WHY PCHIP AND NOT SMOOTHSTEP — the one piece of received wisdom in this file
 *
 * A smoothstep has ZERO derivative at both ends. Chain them and every knot is a
 * dead stop; this repository has paid for that lesson twice and written it down
 * both times:
 *
 *   scenario_sbgr/shot_common.py::_slopes  — a chain of smoothstepped camera
 *      segments produced a 107 m/s² acceleration spike (recorded in the São
 *      Carlos module it was ported from).
 *   scenario_sbgr/place_777.py::_subida (commit 96a2371, 2026-08-28) — the
 *      SAME curve was still in the aeroplane's own climb. At the lift-off frame
 *      the vertical speed was 0.006 m/s and took nearly a second to reach 0.6:
 *      on screen the 777 clung to the runway after its wheels were off. The fix
 *      was an exponential approach, which has its MAXIMUM derivative at t = 0.
 *
 * So the default interpolation here is monotone cubic Hermite with
 * Fritsch–Carlson tangents (PCHIP): C¹, no overshoot, and a real derivative at
 * every interior knot. `suave` (smoothstep) is offered per key because it is
 * the right answer for a single deliberate ease, and the UI says what it costs.
 *
 * TWO END CONDITIONS, and the difference matters:
 *
 *   'zero'    m₀ = mₙ₋₁ = 0 — the clip starts and ends AT REST. This is what
 *             you want for a camera move, and it is what shot_common._slopes
 *             ships (it initialises the slope array to zero and only fills the
 *             interior). Keyframe tracks use it.
 *   'secante' m₀ = first secant, mₙ₋₁ = last — no ease at the ends, and a
 *             straight line stays a straight line at constant speed. A flight
 *             path uses it: with 'zero' an aeroplane would ease into and out of
 *             its own take-off roll, which is the runway-sticking bug again,
 *             wearing a different hat.
 * --------------------------------------------------------------------------- */

import * as THREE from 'three';

/* Only frame rates whose GIF delay is a whole number of centiseconds — the
 * project's law, stated once in exportar.js and obeyed here so that a timeline
 * always exports without a rounding stutter. */
export const FPS_LEGAIS_T = [25, 20, 12.5, 10, 5];

export const G = 9.80665;                 // m/s², for the coordinated-turn bank

/* ------------------------------------------------------------- document --- */

/** id -> { alvo, canal, dim, rot, passo, discreto } */
export const CANAIS = {
  'objeto.pos':      { alvo: 'objeto', dim: 3, rot: 'position',   unidade: 'm' },
  'objeto.rot':      { alvo: 'objeto', dim: 3, rot: 'rotation',   unidade: '°' },
  'objeto.esc':      { alvo: 'objeto', dim: 3, rot: 'scale',      unidade: '×' },
  'objeto.visivel':  { alvo: 'objeto', dim: 1, rot: 'visible',    discreto: true },
  'objeto.trem':     { alvo: 'objeto', dim: 1, rot: 'gear down',  discreto: true },
  'camera.pos':      { alvo: 'camera', dim: 3, rot: 'cam position', unidade: 'm' },
  'camera.alvo':     { alvo: 'camera', dim: 3, rot: 'cam target',   unidade: 'm' },
  'camera.fov':      { alvo: 'camera', dim: 1, rot: 'cam FOV',      unidade: '°' },
  'sol.elev':        { alvo: 'sol',    dim: 1, rot: 'sun elevation', unidade: '°' },
  'sol.azim':        { alvo: 'sol',    dim: 1, rot: 'sun azimuth',   unidade: '°' },
  'sol.intensidade': { alvo: 'sol',    dim: 1, rot: 'sun intensity' },
  'render.exposicao':{ alvo: 'render', dim: 1, rot: 'exposure' },
};

export const EASINGS = [
  { v: 'pchip',    r: 'monotone (PCHIP) — the default, and why' },
  { v: 'linear',   r: 'linear — constant rate, exact' },
  { v: 'suave',    r: 'smooth — eases in AND out (dead stop at both knots)' },
  { v: 'segurar',  r: 'hold — step, no motion until the next key' },
];

let seq = 0;
const novoIdT = p => `${p}${(++seq).toString(36)}${Date.now().toString(36).slice(-3)}`;

export function linhaPadrao () {
  return {
    duracao: 8,          // seconds
    fps: 25,             // must divide 100 evenly — see FPS_LEGAIS_T
    loop: true,
    autochave: false,    // auto-key: a move at the playhead writes a key
    trilhas: [],         // keyframe tracks
    voos: [],            // flight behaviours (see §flight)
  };
}

export function novaTrilha (canal, ref = null) {
  return { id: novoIdT('t'), canal, ref, chaves: [], mudo: false };
}

/** A key. `v` is a number or an array; `e` governs the segment LEAVING it —
 *  the Blender convention, and the reason the last key's easing is inert. */
export const novaChave = (t, v, e = 'pchip') => ({ t: +(+t).toFixed(4), v, e });

export const quadros = l => Math.max(1, Math.round(l.duracao * l.fps));
export const paraQuadro = (l, t) => Math.round(t * l.fps);
export const deQuadro = (l, q) => q / l.fps;
/** Snap a time to the frame grid — every key lands on a frame that exists. */
export const encaixar = (l, t) =>
  THREE.MathUtils.clamp(Math.round(t * l.fps), 0, quadros(l)) / l.fps;

export const temAnimacao = l =>
  !!l && ((l.trilhas || []).some(t => t.chaves.length > 0) || (l.voos || []).length > 0);

/* -------------------------------------------------------- interpolation --- */

/** Fritsch–Carlson tangents. C¹, monotone, no overshoot.
 *  @param extremos 'zero' (rest at both ends) or 'secante' (no end ease). */
export function tangentes (ts, vs, extremos = 'zero') {
  const n = ts.length;
  if (n < 2) return { h: [], m: [0] };
  const h = [], dl = [];
  for (let i = 0; i < n - 1; i++) {
    h.push(Math.max(1e-9, ts[i + 1] - ts[i]));
    dl.push((vs[i + 1] - vs[i]) / h[i]);
  }
  const m = new Array(n).fill(0);
  for (let i = 1; i < n - 1; i++) {
    if (dl[i - 1] * dl[i] <= 0) { m[i] = 0; continue; }
    const w1 = 2 * h[i] + h[i - 1], w2 = h[i] + 2 * h[i - 1];
    m[i] = (w1 + w2) / (w1 / dl[i - 1] + w2 / dl[i]);
  }
  if (extremos === 'secante' && n >= 2) { m[0] = dl[0]; m[n - 1] = dl[n - 2]; }
  return { h, m };
}

const hermite = (v0, v1, m0, m1, hh, u) => {
  const u2 = u * u, u3 = u2 * u;
  return (2 * u3 - 3 * u2 + 1) * v0 + (u3 - 2 * u2 + u) * hh * m0
       + (-2 * u3 + 3 * u2) * v1 + (u3 - u2) * hh * m1;
};
const suavizar = u => u * u * (3 - 2 * u);

/**
 * Evaluate one component of one channel at time t.
 * @param chaves sorted keys
 * @param i      component index (0 for scalars)
 */
export function amostrar (chaves, t, i = 0, extremos = 'zero') {
  const n = chaves.length;
  if (!n) return null;
  const val = k => (Array.isArray(k.v) ? k.v[i] : k.v);
  if (n === 1 || t <= chaves[0].t) return val(chaves[0]);
  if (t >= chaves[n - 1].t) return val(chaves[n - 1]);

  let k = 0;
  while (k < n - 2 && t > chaves[k + 1].t) k++;
  const t0 = chaves[k].t, t1 = chaves[k + 1].t;
  const hh = Math.max(1e-9, t1 - t0);
  const u = (t - t0) / hh;
  const v0 = val(chaves[k]), v1 = val(chaves[k + 1]);

  switch (chaves[k].e) {
    case 'segurar': return v0;
    case 'linear':  return v0 + (v1 - v0) * u;
    case 'suave':   return v0 + (v1 - v0) * suavizar(u);
    default: {
      /* PCHIP over the WHOLE key list, so a key three segments away still
         shapes the tangent here — that is what makes a chain of moves read as
         one move rather than as a series of arrivals. */
      const ts = chaves.map(c => c.t), vs = chaves.map(val);
      const { m } = tangentes(ts, vs, extremos);
      return hermite(v0, v1, m[k], m[k + 1], hh, u);
    }
  }
}

/** A whole channel: a number for dim 1, an array for dim 3. */
export function amostrarTrilha (tr, t) {
  const def = CANAIS[tr.canal];
  if (!def || !tr.chaves.length) return null;
  if (def.discreto) {
    /* Booleans never interpolate: the value is the last key at or before t. */
    let v = tr.chaves[0].v;
    for (const c of tr.chaves) { if (c.t <= t + 1e-6) v = c.v; else break; }
    return !!v;
  }
  if (def.dim === 1) return amostrar(tr.chaves, t, 0);
  return [0, 1, 2].map(i => amostrar(tr.chaves, t, i));
}

/* ------------------------------------------------------------- flight ------
 *
 * A flight is a PATH plus a SPEED SCHEDULE. The attitude is not keyed: it is
 * derived, because an aeroplane's attitude is a consequence of where it is
 * going and how fast.
 *
 *   heading ψ   the horizontal tangent of the path.
 *   bank    φ   tan φ = v·ψ̇ / g — the coordinated-turn relation, i.e. the bank
 *               at which the lift vector's horizontal component supplies
 *               exactly the centripetal acceleration the turn needs. Rate
 *               limited (a transport rolls at 5–10 °/s, not instantly) and
 *               capped.
 *   pitch   θ   θ = γ + α, where γ = atan(vs / v) is the FLIGHT PATH angle read
 *               off the path, and α is the angle of attack. α is not free: at
 *               a given weight and configuration lift = ½ρv²S·C_L must equal
 *               the weight, and C_L ≈ C_Lα·α, so α ∝ 1/v². The model carries
 *               one number, `alfaRef` at `vRef`, and scales it.
 *
 *               θ is then RATE LIMITED at `taxaRot` °/s, and that single limiter
 *               does three jobs: it is the rotation on take-off (the target
 *               jumps to `pitchDec` at the rotation point and the limiter walks
 *               the nose up at 3.1 °/s, which is what makes a loaded 777 look
 *               loaded), the flare and the de-rotation on landing.
 *
 * THE CALIBRATION IS MEASURED, from the two Blender clips this repository has
 * already shipped, and the two are deliberately different aeroplanes:
 *
 *   loaded 777-300ER, GRU 10L (scenario_sbgr/place_777.py)
 *      74 m/s at frame 1, +1.4 m/s², rotation at 81 m/s at 3.1 °/s to 12.0°,
 *      main gear off at ~83 m/s, climb 9.5 m/s against 86 m/s — an 11 %
 *      gradient — pitch settling at 13°.
 *   ferry A320, SDSC (scenario_sdsc/place_aircraft.py)
 *      airborne 1150 m into a 1672 m TORA at 58 m/s, 21 % gradient — twice the
 *      777's, on a runway half the length. Same physics, different aeroplane.
 *
 * The take-off preset picks between them on the aircraft's measured length, so
 * a 777 is heavy and an A319 is not, without a table of types anywhere.
 *
 * WHAT IS DELIBERATELY NOT MODELLED: thrust, drag, weight, wind, ground effect,
 * flap schedule. This is authoring, not a simulator — every number above is a
 * profile chosen to read right, and the derivations above are what keep the
 * profile self-consistent once you drag a waypoint.
 */

export function novoVoo (ref, patch = {}) {
  return {
    id: novoIdT('v'),
    ref,                       // scene object id — must be an aircraft
    t0: 0,                     // seconds: when the flight starts
    rotulo: 'flight',
    /* Waypoints. x/z are world metres, `alt` is height above the SURFACE under
       that point (so 0 means "wheels on whatever is there"), `v` is ground
       speed in m/s. */
    rota: [],
    taxaRot: 3.1,              // °/s — pitch rate limit
    pitchDec: 12.0,            // ° — the attitude rotation aims for
    rotacao: 120,              // m before lift-off at which rotation starts
    alfaRef: 6.6,              // ° angle of attack at vRef
    vRef: 86,                  // m/s
    taxaBanco: 8,              // °/s — roll rate limit
    bancoMax: 25,              // °
    ...patch,
  };
}

const AR_MIN = 0.02;           // m: below this the wheels are on the ground

/* The sampled table is a CACHE, and it lives in a WeakMap rather than on the
 * flight object. It was a `voo._tab` field for one afternoon, which put three
 * thousand samples of six arrays into every scene JSON (108 kB for a nine-point
 * route), into every localStorage save, and — worst — into all sixty undo
 * snapshots, because `clonar()` is a JSON round trip. A cache that survives
 * serialisation is not a cache. */
const CACHE_VOO = new WeakMap();

/** The built table for a flight, or null if it has not been built yet. */
export const tabelaDe = voo => (CACHE_VOO.get(voo) || {}).tab || null;
/** Force the next sample to rebuild — after a parameter edit. */
export const invalidarVoo = voo => CACHE_VOO.delete(voo);

/** Build the sampled table for one flight, or return the cached one.
 *  @param ctx { sondar(x,z)->y, xg, yg }  ground probe and main-gear offset */
export function tabelaVoo (voo, ctx) {
  const chave = JSON.stringify([voo.rota, voo.taxaRot, voo.pitchDec, voo.alfaRef,
                                voo.vRef, voo.taxaBanco, voo.bancoMax, voo.rotacao,
                                ctx.xg, ctx.yg, ctx.marca || 0]);
  const posto = CACHE_VOO.get(voo);
  if (posto && posto.chave === chave) return posto.tab;

  const R = voo.rota || [];
  if (R.length < 2) { CACHE_VOO.set(voo, { chave, tab: null }); return null; }

  /* 1 — knots, parameterised by chord length. */
  const u = [0];
  for (let i = 1; i < R.length; i++) {
    u.push(u[i - 1] + Math.max(0.01, Math.hypot(R[i].x - R[i - 1].x, R[i].z - R[i - 1].z)));
  }
  const canal = f => R.map(f);
  const tx = tangentes(u, canal(p => p.x), 'secante');
  const tz = tangentes(u, canal(p => p.z), 'secante');
  const ta = tangentes(u, canal(p => p.alt), 'secante');
  const tv = tangentes(u, canal(p => p.v), 'secante');
  const em = (tan, vals, q) => {
    if (q <= u[0]) return vals[0];
    if (q >= u[u.length - 1]) return vals[vals.length - 1];
    let k = 0; while (k < u.length - 2 && q > u[k + 1]) k++;
    const hh = u[k + 1] - u[k];
    return hermite(vals[k], vals[k + 1], tan.m[k], tan.m[k + 1], hh, (q - u[k]) / hh);
  };

  /* 2 — resample. The parameter is chord length, which is NOT arc length once
     the curve bends, so step 3 re-measures the real distance and drives time
     from that. Skip it and a curved path silently flies slower than its own
     speed schedule. */
  const L = u[u.length - 1];
  const N = THREE.MathUtils.clamp(Math.round(L / 2), 240, 3000);
  const X = [], Z = [], A = [], V = [], Y0 = [];
  for (let i = 0; i <= N; i++) {
    const q = L * i / N;
    X.push(em(tx, canal(p => p.x), q));
    Z.push(em(tz, canal(p => p.z), q));
    A.push(Math.max(0, em(ta, canal(p => p.alt), q)));
    V.push(Math.max(1, em(tv, canal(p => p.v), q)));
  }
  /* 3 — the ground under the path. Probed at 24 stations and interpolated, not
     raycast per frame: GRU's 10L is 0.39 m below the threshold datum and the
     10R section rises 24 cm over 490 m, so the relief is real but it is also
     smooth, and 24 samples over a 2 km roll is one every 80 m. */
  const M = 24, probe = [];
  for (let j = 0; j <= M; j++) {
    const i = Math.round(N * j / M);
    probe.push(ctx.sondar ? ctx.sondar(X[i], Z[i]) : 0);
  }
  for (let i = 0; i <= N; i++) {
    const f = (i / N) * M, j = Math.min(M - 1, Math.floor(f));
    Y0.push(probe[j] + (probe[j + 1] - probe[j]) * (f - j));
  }

  /* 3b — the datum an altitude is measured FROM.
     `alt` is height above the surface, which is exactly right while the wheels
     are near it and exactly wrong at height: a flypast at 90 m AGL crossing a
     26 m hangar would climb 26 m to keep its clearance, and the flight panel
     showed the milder version of that — ±0.7 m/s of phantom climb where the
     path leaves the runway slab and the probe drops 28 cm. So the datum is
     blended: at the pavement it IS the pavement, and by 50 m up it is the
     surface height where the route began. Aeroplanes do not hug terrain. */
  const Y0M = [];
  for (let i = 0; i <= N; i++) {
    const w = THREE.MathUtils.clamp(1 - A[i] / 50, 0, 1);
    Y0M.push(Y0[i] * w + Y0[0] * (1 - w));
  }
  for (let i = 0; i <= N; i++) Y0[i] = Y0M[i];

  /* 4 — true arc length, then time. dt = ds / v with s the REAL distance. */
  const S = [0], T = [0];
  for (let i = 1; i <= N; i++) {
    const ds = Math.hypot(X[i] - X[i - 1], Z[i] - Z[i - 1],
                          (Y0[i] + A[i]) - (Y0[i - 1] + A[i - 1]));
    S.push(S[i - 1] + ds);
    T.push(T[i - 1] + ds / (0.5 * (V[i] + V[i - 1])));
  }

  /* 5 — where the wheels leave and where they come back. Read off the route's
     own altitude, so a preset that never climbs is a taxi and a preset that
     starts high is a flypast, with no flag to keep in sync. */
  const SOLO = A.map(a => a <= AR_MIN);
  const iLift = SOLO.indexOf(false);                      // −1 if it never flies
  const iToca = SOLO.lastIndexOf(false) >= 0 && SOLO[N] ? SOLO.lastIndexOf(false) + 1 : -1;
  const sRot = iLift > 0 ? S[iLift] - (voo.rotacao ?? 120) : -Infinity;

  /* 6 — heading, climb rate, and the derived attitude, marched forward in time
     so the two rate limiters are honest integrations rather than clamps. */
  const PSI = [], PITCH = [], BANCO = [], VS = [];
  let pitch = 0, banco = 0, psiAnt = null;
  const alfa = v => THREE.MathUtils.clamp(voo.alfaRef * (voo.vRef / v) ** 2, 0, 25);
  const tLift = iLift > 0 ? T[iLift] : null;
  for (let i = 0; i <= N; i++) {
    const i0 = Math.max(0, i - 1), i1 = Math.min(N, i + 1);
    const dx = X[i1] - X[i0], dz = Z[i1] - Z[i0];
    /* Nose is local −X, so the heading that points forward along (dx, dz) is
       atan2(dz, −dx). Checked against cenas.js: GRU's 10L track bears 16.354°
       off +X and the starter parks the 777 at 196.354°, which is what this
       returns for that tangent. */
    let psi = Math.atan2(dz, -dx);
    if (psiAnt !== null) {            // unwrap, or a pass through ±180° banks hard
      while (psi - psiAnt > Math.PI) psi -= 2 * Math.PI;
      while (psi - psiAnt < -Math.PI) psi += 2 * Math.PI;
    }
    psiAnt = psi;
    PSI.push(psi);

    const dt = Math.max(1e-4, T[i1] - T[i0]);
    const dh = (Y0[i1] + A[i1]) - (Y0[i0] + A[i0]);
    const vs = dh / dt;
    VS.push(vs);
    const noSolo = SOLO[i];

    /* pitch target */
    let alvo;
    if (noSolo) {
      /* On the ground the nose is down until the rotation point. `rotacao` is
         the distance BEFORE lift-off at which rotation starts, which is how a
         profile is actually written: "rotate 120 m before the wheels leave".
         After touchdown the target is 0 again and the same limiter de-rotates
         the nose onto the runway at `taxaRot`. */
      alvo = (iLift > 0 && i < iLift && S[i] >= sRot) ? voo.pitchDec : 0;
      if (iToca > 0 && i >= iToca) alvo = 0;
    } else {
      const gama = THREE.MathUtils.radToDeg(Math.atan2(vs, Math.max(1, V[i])));
      alvo = gama + alfa(V[i]);
      /* Right after lift-off the aeroplane is NOT trimmed: it holds the attitude
         it rotated to while speed and climb build under it. Without this floor
         the derived target starts at α alone (6.6° for the 777) while the nose
         is already at 12°, and the limiter walks the nose DOWN for a second —
         a dip nobody asked for. */
      if (tLift !== null && T[i] - tLift < 6) alvo = Math.max(alvo, voo.pitchDec);
    }
    const passo = voo.taxaRot * dt;
    pitch += THREE.MathUtils.clamp(alvo - pitch, -passo, passo);
    PITCH.push(pitch);

    /* bank from the turn rate: tan φ = v ψ̇ / g.
       THE SIGN, worked out rather than guessed, because it was wrong first:
       forward(ψ) = (−cos ψ, 0, sin ψ), so d(forward)/dψ at ψ = 180° is
       (0, 0, −1) while starboard there is (0, 0, +1). Increasing ψ therefore
       swings the nose to PORT — a LEFT turn — and a coordinated left turn puts
       the PORT wing down, which is a negative bank in this file's convention
       (positive drops the starboard wing; see `atitude`). Without the minus the
       aeroplane banked away from every turn it made. */
    const dpsi = PSI[i] - PSI[i0];
    const psiPonto = dpsi / dt;
    let bAlvo = -THREE.MathUtils.radToDeg(Math.atan((V[i] * psiPonto) / G));
    bAlvo = THREE.MathUtils.clamp(bAlvo, -voo.bancoMax, voo.bancoMax);
    if (noSolo) bAlvo = 0;                       // wheels on the tarmac: wings level
    const pb = voo.taxaBanco * dt;
    banco += THREE.MathUtils.clamp(bAlvo - banco, -pb, pb);
    BANCO.push(banco);
  }

  const tab = {
    N, T, X, Z, A, V, Y0, S, PSI, PITCH, BANCO, VS, SOLO,
    dur: T[N], comprimento: S[N], tLift,
    xg: ctx.xg, yg: ctx.yg,
  };
  CACHE_VOO.set(voo, { chave, tab });
  return tab;
}

/* Scratch, so a 240-frame export does not allocate 240 × 6 objects. */
const _q = new THREE.Quaternion();
const _m = new THREE.Matrix4();
const _f = new THREE.Vector3(), _up = new THREE.Vector3(), _r = new THREE.Vector3();
const _ref = new THREE.Vector3();

/** Attitude → quaternion, in this project's frame: nose is local −X, up is +Y,
 *  and the STARBOARD wing is local −Z (forward × up with forward = −X gives
 *  (0,0,−1)). Built as a basis rather than as Euler angles, because Euler order
 *  is a trap and the document stores whatever `decompose` gives back anyway. */
export function atitude (psi, pitchDeg, bancoDeg, out = new THREE.Quaternion()) {
  const p = THREE.MathUtils.degToRad(pitchDeg), b = THREE.MathUtils.degToRad(bancoDeg);
  const cp = Math.cos(p), sp = Math.sin(p);
  _f.set(-Math.cos(psi) * cp, sp, Math.sin(psi) * cp).normalize();
  _up.set(0, 1, 0);
  _r.crossVectors(_f, _up);                        // starboard
  if (_r.lengthSq() < 1e-9) _r.set(0, 0, -1);
  _r.normalize();
  _up.crossVectors(_r, _f).normalize();            // re-orthogonalise
  /* Roll: positive bank drops the starboard wing, so "up" tips toward it. */
  const cb = Math.cos(b), sb = Math.sin(b);
  const ux = _up.x * cb + _r.x * sb, uy = _up.y * cb + _r.y * sb, uz = _up.z * cb + _r.z * sb;
  const rx = _r.x * cb - _up.x * sb, ry = _r.y * cb - _up.y * sb, rz = _r.z * cb - _up.z * sb;
  /* Columns are the images of local +X, +Y, +Z: −forward, up, −starboard. */
  _m.set(-_f.x, ux, -rx, 0,
         -_f.y, uy, -ry, 0,
         -_f.z, uz, -rz, 0,
         0, 0, 0, 1);
  return out.setFromRotationMatrix(_m);
}

/** Sample a flight at absolute timeline time `t`. */
export function amostrarVoo (voo, t, ctx) {
  const tab = tabelaVoo(voo, ctx);
  if (!tab) return null;
  const tt = THREE.MathUtils.clamp(t - (voo.t0 || 0), 0, tab.dur);
  /* binary search on T */
  let lo = 0, hi = tab.N;
  while (lo < hi) { const mid = (lo + hi) >> 1; if (tab.T[mid] < tt) lo = mid + 1; else hi = mid; }
  const i = Math.max(1, lo);
  const t0 = tab.T[i - 1], t1 = tab.T[i];
  const f = t1 > t0 ? (tt - t0) / (t1 - t0) : 0;
  const mix = (A) => A[i - 1] + (A[i] - A[i - 1]) * f;

  const x = mix(tab.X), z = mix(tab.Z), alt = mix(tab.A), y0 = mix(tab.Y0);
  const psi = mix(tab.PSI), pitch = mix(tab.PITCH), banco = mix(tab.BANCO);
  atitude(psi, pitch, banco, _q);

  /* The path describes the MAIN-GEAR CONTACT point, on the ground and in the
     air alike, so "rotate about the main gear" needs no special case: put the
     reference point where the path says it is and let the body hang off it. */
  _ref.set(tab.xg, tab.yg, 0).applyQuaternion(_q);
  return {
    pos: [x - _ref.x, y0 + alt - _ref.y, z - _ref.z],
    quat: [_q.x, _q.y, _q.z, _q.w],
    noSolo: alt <= AR_MIN,
    info: { v: mix(tab.V), vs: mix(tab.VS), alt, pitch, banco,
            psi: THREE.MathUtils.radToDeg(psi), s: mix(tab.S) },
  };
}

/* ---------------------------------------------------------- evaluation --- */

/**
 * The overlay at time t. Returns null when there is nothing animated, so a
 * scene with no timeline costs exactly nothing.
 * @param ctxVoo (id) -> { sondar, xg, yg }  supplied by mundo.js
 */
export function avaliar (estado, t, ctxVoo = null) {
  const l = estado.linha;
  if (!temAnimacao(l)) return null;
  const ov = { objetos: new Map(), camera: null, sol: null, render: null };
  const obj = id => {
    if (!ov.objetos.has(id)) ov.objetos.set(id, {});
    return ov.objetos.get(id);
  };

  for (const tr of l.trilhas || []) {
    if (tr.mudo || !tr.chaves.length) continue;
    const v = amostrarTrilha(tr, t);
    if (v === null) continue;
    const [alvo, campo] = tr.canal.split('.');
    if (alvo === 'objeto') { if (tr.ref) obj(tr.ref)[campo] = v; }
    else if (alvo === 'camera') { ov.camera = ov.camera || {}; ov.camera[campo] = v; }
    else if (alvo === 'sol') { ov.sol = ov.sol || {}; ov.sol[campo] = v; }
    else if (alvo === 'render') { ov.render = ov.render || {}; ov.render[campo] = v; }
  }

  /* Flights come after the tracks and win on pos/rot for their aircraft: an
     aeroplane's attitude is derived from its path, and letting a stale rotation
     key fight it would produce exactly the sideways-flying nonsense the derived
     model exists to prevent. The gear channel is left alone — that IS a key. */
  for (const v of l.voos || []) {
    if (!v.ref || !v.rota || v.rota.length < 2) continue;
    const ctx = ctxVoo ? ctxVoo(v.ref) : null;
    if (!ctx) continue;
    const a = amostrarVoo(v, t, ctx);
    if (!a) continue;
    const o = obj(v.ref);
    o.pos = a.pos; o.quat = a.quat;
    delete o.rot;
    o.voo = a.info;
  }
  return ov;
}

/* ------------------------------------------------------------- editing --- */

export function acharTrilha (l, canal, ref = null) {
  return (l.trilhas || []).find(t => t.canal === canal && (t.ref || null) === (ref || null));
}

export function garantirTrilha (l, canal, ref = null) {
  let tr = acharTrilha(l, canal, ref);
  if (!tr) { tr = novaTrilha(canal, ref); l.trilhas.push(tr); }
  return tr;
}

/** Write a key, replacing any key already on that frame. Returns the key. */
export function porChave (l, canal, ref, t, v, e = 'pchip') {
  const tr = garantirTrilha(l, canal, ref);
  const tq = encaixar(l, t);
  const i = tr.chaves.findIndex(c => Math.abs(c.t - tq) < 1e-6);
  const k = novaChave(tq, v, i >= 0 ? tr.chaves[i].e : e);
  if (i >= 0) tr.chaves[i] = k; else { tr.chaves.push(k); tr.chaves.sort((a, b) => a.t - b.t); }
  return k;
}

export function apagarChave (l, trilhaId, t) {
  const tr = (l.trilhas || []).find(x => x.id === trilhaId);
  if (!tr) return false;
  const n = tr.chaves.length;
  tr.chaves = tr.chaves.filter(c => Math.abs(c.t - t) > 1e-6);
  if (!tr.chaves.length) l.trilhas = l.trilhas.filter(x => x !== tr);
  return tr.chaves.length !== n;
}

/** Drop every track and flight that points at an object that no longer exists. */
export function podar (estado) {
  const l = estado.linha;
  if (!l) return;
  const vivos = new Set(estado.objetos.map(o => o.id));
  l.trilhas = (l.trilhas || []).filter(t => !t.ref || vivos.has(t.ref));
  l.voos = (l.voos || []).filter(v => vivos.has(v.ref));
}
