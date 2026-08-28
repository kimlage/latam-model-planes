/* props.js — everything in a scene that is NOT an aircraft.
 *
 * LICENCE, and the reason this file exists at all:
 * the airport scenery in scenario/, scenario_sdsc/ and scenario_sbgr/ is
 * generated from OpenStreetMap and is therefore an ODbL derived database.
 * ODbL is share-alike; the models are CC BY 4.0. Those terms conflict, so the
 * scenery is NEVER exported and NEVER reaches this studio. Every ground, sky,
 * marking and block below is original geometry authored here, from primitives
 * and canvas painting, with no survey data of any real airport in it. Runway
 * markings follow the generic published pattern (centreline 30 m on / 20 m off,
 * edge stripes); they are not a survey of any specific runway.
 *
 * Conventions shared with the aircraft: +Y up, metres, every prop's origin at
 * its X/Z centre with y = 0 at its base, so "snap to ground" is pos.y = 0.
 */

import * as THREE from 'three';

/* ------------------------------------------------------------- utilities */

const canvas = (w, h) => {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  return c;
};

/** Value noise splattered as soft dots — cheap, seamless enough at tiling size. */
function ruido (ctx, w, h, n, raio, alpha) {
  for (let i = 0; i < n; i++) {
    const x = Math.random() * w, y = Math.random() * h;
    const r = raio * (0.4 + Math.random());
    const g = ctx.createRadialGradient(x, y, 0, x, y, r);
    const v = Math.random() < 0.5 ? 0 : 255;
    g.addColorStop(0, `rgba(${v},${v},${v},${alpha})`);
    g.addColorStop(1, `rgba(${v},${v},${v},0)`);
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.fill();
  }
}

function textura (c, repete = 1) {
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(repete, repete);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  return t;
}

/* ---------------------------------------------------------- ground types */
/* Each returns { material, metrosPorTile } — the caller sets texture.repeat
 * from the plane size so that one tile is always the same number of metres. */

const chaoCache = new Map();

export function materialChao (tipo) {
  if (chaoCache.has(tipo)) return chaoCache.get(tipo);
  let out;
  switch (tipo) {
    case 'concreto': out = chaoConcreto(); break;
    case 'grama':    out = chaoGrama();    break;
    case 'estudio':  out = chaoEstudio();  break;
    case 'sombra':   out = { material: new THREE.ShadowMaterial({ opacity: 0.35 }), metros: 60 }; break;
    case 'pista':    out = chaoAsfalto();  break;   // base under the runway strip
    case 'apron':
    default:         out = chaoAsfalto();  break;
  }
  chaoCache.set(tipo, out);
  return out;
}

function chaoAsfalto () {
  const c = canvas(512, 512), x = c.getContext('2d');
  x.fillStyle = '#3a3d42'; x.fillRect(0, 0, 512, 512);
  ruido(x, 512, 512, 2600, 5, 0.06);
  ruido(x, 512, 512, 400, 22, 0.025);
  // Faint paving seams every half tile: 30 m of a 60 m tile.
  x.strokeStyle = 'rgba(0,0,0,.20)'; x.lineWidth = 2;
  for (const p of [0, 256]) {
    x.beginPath(); x.moveTo(p, 0); x.lineTo(p, 512); x.moveTo(0, p); x.lineTo(512, p); x.stroke();
  }
  const map = textura(c);
  return { material: new THREE.MeshStandardMaterial({ map, roughness: 0.92, metalness: 0.0 }), metros: 60 };
}

function chaoConcreto () {
  const c = canvas(512, 512), x = c.getContext('2d');
  x.fillStyle = '#6d6f71'; x.fillRect(0, 0, 512, 512);
  // 4×4 slabs per tile, each slightly different, with expansion joints.
  for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) {
    const v = 104 + Math.random() * 16;
    x.fillStyle = `rgb(${v},${v + 1},${v + 2})`;
    x.fillRect(i * 128 + 2, j * 128 + 2, 124, 124);
  }
  ruido(x, 512, 512, 1800, 6, 0.05);
  x.strokeStyle = 'rgba(40,42,45,.85)'; x.lineWidth = 3;
  for (let i = 0; i <= 4; i++) {
    x.beginPath(); x.moveTo(i * 128, 0); x.lineTo(i * 128, 512);
    x.moveTo(0, i * 128); x.lineTo(512, i * 128); x.stroke();
  }
  const map = textura(c);
  return { material: new THREE.MeshStandardMaterial({ map, roughness: 0.85 }), metros: 40 };
}

function chaoGrama () {
  const c = canvas(512, 512), x = c.getContext('2d');
  x.fillStyle = '#4a5c38'; x.fillRect(0, 0, 512, 512);
  ruido(x, 512, 512, 5000, 4, 0.10);
  ruido(x, 512, 512, 300, 30, 0.05);
  const map = textura(c);
  return { material: new THREE.MeshStandardMaterial({ map, roughness: 1.0 }), metros: 30 };
}

function chaoEstudio () {
  return { material: new THREE.MeshStandardMaterial({ color: 0xb9bcc2, roughness: 0.55, metalness: 0.0 }), metros: 60 };
}

/** The runway strip laid over the ground for the "runway" ground type.
 *  45 m wide (generic code-E runway), `comprimento` long, centred on origin,
 *  running along X — the same axis the aircraft's fuselage runs along. */
export function faixaPista (comprimento = 600) {
  const larg = 45;
  const c = canvas(1024, 128);                       // U = along the runway
  const x = c.getContext('2d');
  x.fillStyle = '#2f3237'; x.fillRect(0, 0, 1024, 128);
  ruido(x, 1024, 128, 1400, 5, 0.05);
  // Edge stripes: 0.9 m white, set 0.3 m inside the 45 m edge.
  const m2px = 128 / larg;
  x.fillStyle = '#d8d8d4';
  x.fillRect(0, 0.3 * m2px, 1024, 0.9 * m2px);
  x.fillRect(0, 128 - 1.2 * m2px, 1024, 0.9 * m2px);
  // Centreline: 30 m painted, 20 m gap, 0.9 m wide. One tile of U = 50 m.
  const tile = 50;
  x.fillRect(0, 64 - 0.45 * m2px, 1024 * (30 / tile), 0.9 * m2px);
  const t = new THREE.CanvasTexture(c);
  t.wrapS = THREE.RepeatWrapping; t.wrapT = THREE.ClampToEdgeWrapping;
  t.repeat.set(comprimento / tile, 1);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  const g = new THREE.PlaneGeometry(comprimento, larg);
  const malha = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ map: t, roughness: 0.9 }));
  malha.rotation.x = -Math.PI / 2;
  malha.position.y = 0.02;                            // above the ground, no z-fighting
  malha.receiveShadow = true;
  malha.name = 'pista';
  return malha;
}

/* --------------------------------------------------------------- the sky -
 * An equirectangular gradient painted from the sun's own elevation/azimuth, so
 * the background, the image-based lighting and the key light always agree.
 *
 * Sampling convention (three.js): u = atan2(z, -x)/2π + 0.5, v = asin(y)/π + 0.5,
 * and a CanvasTexture is flipY by default, so canvas row j carries v = 1 - j/H.
 */
export function texturaCeu (elevGraus, azimGraus, corSol = '#fff2df', W = 512, H = 256) {
  const c = canvas(W, H), ctx = c.getContext('2d');
  const img = ctx.createImageData(W, H);
  const d = img.data;

  const el = THREE.MathUtils.degToRad(elevGraus);
  const az = THREE.MathUtils.degToRad(azimGraus);
  const sol = new THREE.Vector3(Math.cos(el) * Math.sin(az), Math.sin(el), Math.cos(el) * Math.cos(az));
  const cor = new THREE.Color(corSol);

  // Day factor: 1 with the sun high, 0 once it is below the horizon.
  const dia = THREE.MathUtils.clamp((elevGraus + 6) / 26, 0, 1);

  const zenite  = new THREE.Color(0x0b1526).lerp(new THREE.Color(0x2f6fc4), dia);
  const horiz   = new THREE.Color(0x2a2f3d).lerp(new THREE.Color(0xcfe0f2), dia);
  const quente  = new THREE.Color(0xff9a48);                 // low-sun horizon wash
  // Below the horizon the sky texture stands in for "distant ground seen through
  // haze". It is deliberately close to the apron grey: the ground plane is
  // finite, its edge is visible, and a matching band is what hides the seam.
  const solo    = new THREE.Color(0x191b1f).lerp(new THREE.Color(0x3b3d42), dia);
  const baixo   = 1 - THREE.MathUtils.clamp((elevGraus - 2) / 22, 0, 1); // 1 near sunset

  const dir = new THREE.Vector3(), tmp = new THREE.Color();
  for (let j = 0; j < H; j++) {
    const v = 1 - (j + 0.5) / H;
    const phi = (v - 0.5) * Math.PI;
    const y = Math.sin(phi), r = Math.cos(phi);
    for (let i = 0; i < W; i++) {
      const u = (i + 0.5) / W;
      const th = (u - 0.5) * 2 * Math.PI;
      dir.set(-r * Math.cos(th), y, r * Math.sin(th));

      if (y >= 0) {
        // Sky: zenith → horizon by height, warmed towards the sun near sunset.
        const t = Math.pow(1 - y, 2.2);
        tmp.copy(zenite).lerp(horiz, t);
        const alinha = Math.max(0, dir.dot(sol));
        tmp.lerp(quente, baixo * t * Math.pow(alinha, 1.5) * 0.55);
        // Sun glow and disc.
        const g = Math.pow(alinha, 220) * 1.0 + Math.pow(alinha, 14) * 0.16;
        tmp.lerp(cor, THREE.MathUtils.clamp(g, 0, 1));
        if (alinha > 0.99985) tmp.copy(cor).multiplyScalar(1.0);
      } else {
        // Below the horizon: haze fading into ground over ~25°, not a hard line.
        const t = THREE.MathUtils.clamp(-y * 2.4, 0, 1);
        tmp.copy(horiz).lerp(solo, Math.pow(t, 0.7));
      }
      const k = (j * W + i) * 4;
      d[k]     = Math.min(255, tmp.r * 255);
      d[k + 1] = Math.min(255, tmp.g * 255);
      d[k + 2] = Math.min(255, tmp.b * 255);
      d[k + 3] = 255;
    }
  }
  ctx.putImageData(img, 0, 0);
  const t = new THREE.CanvasTexture(c);
  t.mapping = THREE.EquirectangularReflectionMapping;
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

/** Unit vector pointing from the scene towards the sun. */
export function direcaoSol (elevGraus, azimGraus) {
  const el = THREE.MathUtils.degToRad(elevGraus), az = THREE.MathUtils.degToRad(azimGraus);
  return new THREE.Vector3(Math.cos(el) * Math.sin(az), Math.sin(el), Math.cos(el) * Math.cos(az));
}

/* ------------------------------------------------------------- the props */

const MAT = {
  claro:   () => new THREE.MeshStandardMaterial({ color: 0xd3d6da, roughness: 0.72 }),
  medio:   () => new THREE.MeshStandardMaterial({ color: 0x9aa0a8, roughness: 0.8 }),
  escuro:  () => new THREE.MeshStandardMaterial({ color: 0x3b4048, roughness: 0.75 }),
  vidro:   () => new THREE.MeshStandardMaterial({ color: 0x1b2431, roughness: 0.15, metalness: 0.6 }),
  metal:   () => new THREE.MeshStandardMaterial({ color: 0xb8bcc2, roughness: 0.35, metalness: 0.8 }),
  laranja: () => new THREE.MeshStandardMaterial({ color: 0xff6a1f, roughness: 0.7 }),
  lampada: () => new THREE.MeshStandardMaterial({ color: 0xfff3d0, emissive: 0xfff0c0, emissiveIntensity: 1.6, roughness: 0.4 }),
};

const caixa = (w, h, d, mat, x = 0, y = 0, z = 0) => {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
  m.position.set(x, y + h / 2, z);
  return m;
};

/** slug -> { rotulo, medidas, construir() }. Sidebar and loader both read this. */
export const PROPS = {
  hangar: {
    rotulo: 'Hangar block', medidas: '72 × 46 × 21 m',
    construir () {
      const g = new THREE.Group();
      g.add(caixa(72, 14, 46, MAT.claro()));
      const arco = new THREE.Mesh(
        new THREE.CylinderGeometry(23, 23, 72, 24, 1, false, 0, Math.PI),
        MAT.medio());
      arco.rotation.z = Math.PI / 2;
      arco.position.y = 14;
      arco.scale.set(1, 1, 0.30);            // flatten to a shallow vault
      g.add(arco);
      const porta = caixa(0.6, 12.5, 40, MAT.escuro(), -36, 0, 0);
      g.add(porta);
      return g;
    },
  },
  terminal: {
    rotulo: 'Terminal block', medidas: '160 × 28 × 14 m',
    construir () {
      const g = new THREE.Group();
      g.add(caixa(160, 13, 28, MAT.claro()));
      g.add(caixa(161, 1.2, 29, MAT.medio(), 0, 13, 0));
      const janela = caixa(160.4, 3.6, 28.4, MAT.vidro(), 0, 6.5, 0);
      g.add(janela);
      return g;
    },
  },
  laje: {
    rotulo: 'Apron slab', medidas: '80 × 80 m',
    construir () {
      const { material } = materialChao('concreto');
      const m = new THREE.Mesh(new THREE.BoxGeometry(80, 0.25, 80), material);
      m.position.y = 0.125;
      m.receiveShadow = true;
      return m;
    },
  },
  mastro: {
    rotulo: 'Light mast', medidas: '24 m',
    construir () {
      const g = new THREE.Group();
      const p = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.45, 22, 10), MAT.metal());
      p.position.y = 11; g.add(p);
      g.add(caixa(3.6, 0.5, 1.6, MAT.escuro(), 0, 22, 0));
      const l = caixa(3.2, 0.35, 1.2, MAT.lampada(), 0, 21.7, 0);
      g.add(l);
      return g;
    },
  },
  ponte: {
    rotulo: 'Boarding bridge', medidas: '28 m, generic',
    construir () {
      const g = new THREE.Group();
      const rot = new THREE.Mesh(new THREE.CylinderGeometry(3.2, 3.2, 6.5, 16), MAT.medio());
      rot.position.set(-13, 3.25, 0); g.add(rot);
      const tubo = caixa(24, 3.2, 3.0, MAT.claro(), 1, 4.2, 0);
      g.add(tubo);
      const cab = new THREE.Mesh(new THREE.CylinderGeometry(2.2, 2.2, 3.4, 14), MAT.claro());
      cab.position.set(13.5, 5.6, 0); g.add(cab);
      const perna = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 0.4, 4.2, 8), MAT.metal());
      perna.position.set(8, 2.1, 0); g.add(perna);
      return g;
    },
  },
  escada: {
    rotulo: 'Boarding stairs', medidas: '9 × 3 × 5 m',
    construir () {
      const g = new THREE.Group();
      g.add(caixa(6.5, 0.6, 2.6, MAT.medio(), 0, 0.5, 0));
      const rampa = caixa(7.4, 0.4, 2.2, MAT.claro(), 0.2, 2.6, 0);
      rampa.rotation.z = THREE.MathUtils.degToRad(26);
      g.add(rampa);
      g.add(caixa(2.0, 0.4, 2.4, MAT.claro(), 4.3, 4.5, 0));
      for (const x of [-2.4, 2.4]) for (const z of [-1.1, 1.1]) {
        const r = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.5, 0.35, 12), MAT.escuro());
        r.rotation.x = Math.PI / 2; r.position.set(x, 0.5, z); g.add(r);
      }
      return g;
    },
  },
  cone: {
    rotulo: 'Traffic cone', medidas: '0.75 m',
    construir () {
      const g = new THREE.Group();
      const c = new THREE.Mesh(new THREE.ConeGeometry(0.28, 0.7, 12), MAT.laranja());
      c.position.y = 0.36; g.add(c);
      g.add(caixa(0.62, 0.05, 0.62, MAT.laranja(), 0, 0, 0));
      return g;
    },
  },
  bloco: {
    rotulo: 'Massing block', medidas: '20 × 12 × 20 m — scale it',
    construir () { return caixa(20, 12, 20, MAT.medio()); },
  },
  cartao: {
    rotulo: 'Backdrop card', medidas: '240 × 90 m curved',
    construir () {
      const g = new THREE.CylinderGeometry(120, 120, 90, 40, 1, true, Math.PI * 0.62, Math.PI * 0.76);
      const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({
        color: 0xe8ecf2, roughness: 0.95, side: THREE.BackSide }));
      m.position.y = 45;
      return m;
    },
  },
};

/** Build a prop instance, tagged and shadow-enabled like an aircraft. */
export function instanciarProp (slug) {
  const def = PROPS[slug];
  if (!def) throw new Error(`unknown prop "${slug}"`);
  const o = def.construir();
  const g = o.isGroup ? o : new THREE.Group().add(o);
  g.traverse(n => { if (n.isMesh) { n.castShadow = true; n.receiveShadow = true; } });
  return g;
}

/* -------------------------------------------------------------- rigs -----
 * A "light rig" is not an object: it is a named set of sun/sky/render values.
 * Clicking one in the sidebar patches estado.ambiente and estado.render. */
export const RIGS = {
  'hora-dourada': {
    rotulo: 'Golden hour', desc: 'low warm sun, long shadows',
    ambiente: { sol: { elev: 8, azim: 108, intensidade: 3.6, cor: '#ffd7a6' }, envPreset: 'ceu', envIntensidade: 1.0, fundo: 'ceu' },
    render: { exposicao: 1.05, tone: 'aces' },
  },
  'meio-dia': {
    rotulo: 'Midday', desc: 'high sun, hard shadow, clean sky',
    ambiente: { sol: { elev: 62, azim: 150, intensidade: 3.2, cor: '#fff6ea' }, envPreset: 'ceu', envIntensidade: 1.0, fundo: 'ceu' },
    render: { exposicao: 0.95, tone: 'aces' },
  },
  'encoberto': {
    rotulo: 'Overcast', desc: 'soft, no key, paint reads flat and honest',
    ambiente: { sol: { elev: 55, azim: 200, intensidade: 0.5, cor: '#eef2f6' }, envPreset: 'ceu', envIntensidade: 1.7, fundo: 'ceu' },
    render: { exposicao: 1.15, tone: 'agx' },
  },
  'noite': {
    rotulo: 'Night ramp', desc: 'sun below the horizon, mast light does the work',
    ambiente: { sol: { elev: -3, azim: 300, intensidade: 0.35, cor: '#8fa6ff' }, envPreset: 'ceu', envIntensidade: 0.5, fundo: 'ceu' },
    render: { exposicao: 1.5, tone: 'agx' },
  },
  'estudio': {
    rotulo: 'Studio', desc: 'RoomEnvironment, no sky — the clearcoat test',
    ambiente: { sol: { elev: 45, azim: 135, intensidade: 1.6, cor: '#ffffff' }, envPreset: 'sala', envIntensidade: 1.4, fundo: 'cor', fundoCor: '#0d0f14' },
    render: { exposicao: 1.0, tone: 'aces' },
  },
};
