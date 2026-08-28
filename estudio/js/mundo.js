/* mundo.js — the three.js world.
 *
 * One rule: the scene is a projection of `estado`. `aplicar()` writes the
 * document onto the world and is idempotent; `sincronizar()` makes the object
 * list match. Nothing reads state back out of three.js except the editor, and
 * only while a gizmo is being dragged.
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { instanciar } from './frota.js';
import { instanciarProp, materialChao, faixaPista, texturaCeu, direcaoSol } from './props.js';

const TONE = {
  aces: THREE.ACESFilmicToneMapping,
  agx: THREE.AgXToneMapping,
  neutral: THREE.NeutralToneMapping,
  reinhard: THREE.ReinhardToneMapping,
  linear: THREE.LinearToneMapping,
};

export class Mundo {
  constructor (hospedeiro) {
    this.hospedeiro = hospedeiro;

    /* preserveDrawingBuffer: the GIF and PNG exports read the canvas back with
       drawImage after an explicit render. Without it the readback is a coin
       flip on some drivers — a black frame in the middle of a GIF. */
    this.renderer = new THREE.WebGLRenderer({
      antialias: true, alpha: true, preserveDrawingBuffer: true,
      powerPreference: 'high-performance',
    });
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    hospedeiro.append(this.renderer.domElement);

    this.cena = new THREE.Scene();

    this.raizObjetos = new THREE.Group();      // everything the user placed
    this.raizObjetos.name = 'objetos';
    this.cena.add(this.raizObjetos);

    this.raizAmbiente = new THREE.Group();     // ground, grid, runway strip
    this.raizAmbiente.name = 'ambiente';
    this.cena.add(this.raizAmbiente);

    /* lights */
    this.sol = new THREE.DirectionalLight(0xfff2df, 3);
    this.sol.castShadow = true;
    this.sol.shadow.mapSize.set(2048, 2048);
    this.sol.shadow.bias = -0.0006;
    this.sol.shadow.normalBias = 0.6;
    this.cena.add(this.sol, this.sol.target);
    this.preencher = new THREE.HemisphereLight(0xbfd4ff, 0x39312a, 0.25);
    this.cena.add(this.preencher);

    /* cameras */
    this.camP = new THREE.PerspectiveCamera(35, 1, 0.5, 20000);
    this.camP.position.set(-70, 26, 62);
    this.camO = new THREE.OrthographicCamera(-1, 1, 1, -1, -5000, 20000);
    this.cam = this.camP;

    this.controles = new OrbitControls(this.camP, this.renderer.domElement);
    this.controles.enableDamping = true;
    this.controles.dampingFactor = 0.08;
    this.controles.maxPolarAngle = Math.PI * 0.499;   // never under the tarmac
    this.controles.target.set(0, 4, 0);

    /* selection box */
    this.caixaSel = new THREE.Box3Helper(new THREE.Box3(), 0x8fa6ff);
    this.caixaSel.visible = false;
    this.caixaSel.material.depthTest = false;
    this.caixaSel.renderOrder = 999;
    this.cena.add(this.caixaSel);

    this.pmrem = new THREE.PMREMGenerator(this.renderer);
    this.pmrem.compileEquirectangularShader();

    this.objetos = new Map();        // id -> Object3D
    this.chao = null;
    this.pista = null;
    this.grade = null;
    this.texCeu = null;
    this.envAtual = null;
    this._envKey = '';
    this._raioCena = 200;

    this.aoRedimensionar = () => {};
    const ro = new ResizeObserver(() => this.redimensionar());
    ro.observe(hospedeiro);
    this.redimensionar();
  }

  /* ------------------------------------------------------------- sizing */
  get largura () { return Math.max(1, this.hospedeiro.clientWidth); }
  get altura  () { return Math.max(1, this.hospedeiro.clientHeight); }

  redimensionar () {
    const w = this.largura, h = this.altura;
    this.renderer.setSize(w, h, false);
    this.camP.aspect = w / h;
    this.camP.updateProjectionMatrix();
    this.atualizarOrto();
    this.aoRedimensionar(w, h);
  }

  /** The ortho frustum is derived from where the perspective camera is, so the
   *  toggle does not jump: same target, same apparent height. */
  atualizarOrto () {
    const d = this.camP.position.distanceTo(this.controles.target);
    const alt = 2 * d * Math.tan(THREE.MathUtils.degToRad(this.camP.fov) / 2);
    const asp = this.largura / this.altura;
    this.camO.top = alt / 2; this.camO.bottom = -alt / 2;
    this.camO.left = -alt * asp / 2; this.camO.right = alt * asp / 2;
    const r = Math.max(2000, (this._raioCena || 200) * 4);
    this.camO.near = -r; this.camO.far = r * 4;
    this.camO.position.copy(this.camP.position);
    this.camO.quaternion.copy(this.camP.quaternion);
    this.camO.updateProjectionMatrix();
  }

  usarOrto (v) {
    this.atualizarOrto();
    this.cam = v ? this.camO : this.camP;
    this.controles.object = this.cam;
    this.controles.update();
  }

  /* ---------------------------------------------------------- document → */

  aplicarRender (r) {
    this.renderer.toneMapping = TONE[r.tone] ?? THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = r.exposicao;
    this.renderer.shadowMap.enabled = !!r.sombras;
    this.sol.castShadow = !!r.sombras;
    if (this.sol.shadow.mapSize.x !== r.sombraPx) {
      this.sol.shadow.mapSize.set(r.sombraPx, r.sombraPx);
      this.sol.shadow.map?.dispose();
      this.sol.shadow.map = null;                   // force a rebuild at the new size
    }
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, r.pixelRatioMax));
  }

  aplicarAmbiente (a) {
    /* sun — aimed at the small objects, not at the whole scene */
    const dir = direcaoSol(a.sol.elev, a.sol.azim);
    const { centro, raio } = this.focoSombra();
    this.sol.position.copy(centro).addScaledVector(dir, raio * 2.4 + 400);
    this.sol.target.position.copy(centro);
    this.sol.target.updateMatrixWorld();
    this.sol.intensity = a.sol.intensidade;
    this.sol.color.set(a.sol.cor);
    const s = this.sol.shadow.camera;
    s.left = -raio * 1.3; s.right = raio * 1.3;
    s.top = raio * 1.3; s.bottom = -raio * 1.3;
    s.near = 1; s.far = raio * 6 + 900;
    s.updateProjectionMatrix();
    this._raioCena = this.raioCena();
    this.preencher.intensity = 0.18 * a.envIntensidade;

    /* environment + background. The sky texture is rebuilt only when the sun
       actually moved: PMREM of a 512×256 equirect is ~4 ms, but it is 4 ms on
       every drag frame if you are careless. */
    const chave = `${a.envPreset}|${a.sol.elev}|${a.sol.azim}|${a.sol.cor}`;
    if (chave !== this._envKey) {
      this._envKey = chave;
      this.envAtual?.dispose();
      this.texCeu?.dispose();
      this.texCeu = null; this.envAtual = null;
      if (a.envPreset === 'ceu') {
        this.texCeu = texturaCeu(a.sol.elev, a.sol.azim, a.sol.cor);
        this.envAtual = this.pmrem.fromEquirectangular(this.texCeu).texture;
      } else if (a.envPreset === 'sala') {
        this.envAtual = this.pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
      }
      this.cena.environment = this.envAtual;
    }
    // Even when the sun did not move the sky may be needed as a background.
    if (a.fundo === 'ceu' && !this.texCeu) {
      this.texCeu = texturaCeu(a.sol.elev, a.sol.azim, a.sol.cor);
    }
    this.cena.environmentIntensity = a.envIntensidade;

    if (a.fundo === 'ceu')            { this.cena.background = this.texCeu; this.renderer.setClearAlpha(1); }
    else if (a.fundo === 'cor')       { this.cena.background = new THREE.Color(a.fundoCor); this.renderer.setClearAlpha(1); }
    else                              { this.cena.background = null; this.renderer.setClearAlpha(0); }

    /* fog */
    if (a.neblina.ligado) {
      const cor = a.fundo === 'cor' ? new THREE.Color(a.fundoCor) : this.corHorizonte(a);
      this.cena.fog = new THREE.FogExp2(cor, a.neblina.densidade * 1e-4);
    } else this.cena.fog = null;

    this.aplicarChao(a);
    this.aplicarGrade(a);
  }

  corHorizonte (a) {
    const dia = THREE.MathUtils.clamp((a.sol.elev + 6) / 26, 0, 1);
    return new THREE.Color(0x2a2f3d).lerp(new THREE.Color(0xcfe0f2), dia);
  }

  aplicarChao (a) {
    if (this.chao) { this.raizAmbiente.remove(this.chao); this.chao.geometry.dispose(); this.chao = null; }
    if (this.pista) { this.raizAmbiente.remove(this.pista); this.pista.geometry.dispose(); this.pista = null; }
    if (!a.chao.ligado) return;

    const { material, metros } = materialChao(a.chao.tipo);
    const tam = a.chao.tamanho;
    if (material.map) material.map.repeat.set(tam / metros, tam / metros);
    const g = new THREE.PlaneGeometry(tam, tam);
    this.chao = new THREE.Mesh(g, material);
    this.chao.rotation.x = -Math.PI / 2;
    this.chao.receiveShadow = true;
    this.chao.name = 'chao';
    this.chao.userData.naoSelecionavel = true;
    this.raizAmbiente.add(this.chao);

    if (a.chao.tipo === 'pista') {
      this.pista = faixaPista(tam);
      this.pista.userData.naoSelecionavel = true;
      this.raizAmbiente.add(this.pista);
    }
  }

  aplicarGrade (a) {
    if (this.grade) { this.raizAmbiente.remove(this.grade); this.grade.geometry.dispose(); this.grade = null; }
    if (!a.grade) return;
    const tam = Math.max(200, a.chao.tamanho);
    const g = new THREE.GridHelper(tam, Math.round(tam / 20), 0x4b5468, 0x252a36);
    g.material.transparent = true;
    g.material.opacity = 0.45;
    g.position.y = 0.03;
    g.userData.naoSelecionavel = true;
    this.grade = g;
    this.raizAmbiente.add(g);
  }

  /** Add/remove three objects until they match estado.objetos. */
  async sincronizar (estado, aoProgresso) {
    const querem = new Set(estado.objetos.map(o => o.id));
    for (const [id, obj] of [...this.objetos]) {
      if (querem.has(id)) continue;
      this.raizObjetos.remove(obj);
      this.objetos.delete(id);
    }
    const faltando = estado.objetos.filter(o => !this.objetos.has(o.id));
    let feitos = 0;
    for (const d of faltando) {
      let obj;
      try {
        /* Anything that is not an authored prop comes from a GLB: 'aeronave'
           from export/manifest.json, 'cenario' from export/cenarios/. Both go
           through the same pivot wrapper, so a hangar and a 777 obey the same
           rule — origin at the X/Z bbox centre, base on y = 0. */
        obj = d.tipo === 'prop' ? instanciarProp(d.slug) : await instanciar(d.slug);
      } catch (e) {
        console.error('could not instantiate', d, e);
        continue;
      }
      obj.name = d.nome;
      obj.userData.id = d.id;
      this.objetos.set(d.id, obj);
      this.raizObjetos.add(obj);
      aoProgresso && aoProgresso(++feitos, faltando.length, d.nome);
    }
    this.aplicarTransformacoes(estado);
  }

  aplicarTransformacoes (estado) {
    for (const d of estado.objetos) {
      const o = this.objetos.get(d.id);
      if (!o) continue;
      o.position.fromArray(d.pos);
      o.rotation.set(...d.rot.map(THREE.MathUtils.degToRad));
      o.scale.fromArray(d.esc);
      o.visible = d.visivel;
      o.updateMatrixWorld(true);
    }
  }

  /** Copy one object's live transform back into the document row. */
  lerTransformacao (d) {
    const o = this.objetos.get(d.id);
    if (!o) return;
    d.pos = o.position.toArray().map(n => +n.toFixed(4));
    d.rot = [o.rotation.x, o.rotation.y, o.rotation.z]
      .map(r => +THREE.MathUtils.radToDeg(r).toFixed(3));
    d.esc = o.scale.toArray().map(n => +n.toFixed(4));
  }

  /* ------------------------------------------------------------ geometry */

  caixaDe (ids) {
    const b = new THREE.Box3();
    let algum = false;
    for (const id of ids) {
      const o = this.objetos.get(id);
      if (!o || !o.visible) continue;
      b.expandByObject(o); algum = true;
    }
    return algum ? b : null;
  }

  caixaTudo () {
    const b = this.caixaDe([...this.objetos.keys()]);
    return b || new THREE.Box3(new THREE.Vector3(-30, 0, -30), new THREE.Vector3(30, 12, 30));
  }

  /* A field plate is 6.1 km across. An aircraft is 60 m. Every quantity that
     used to be derived from "the scene radius" — the sun's distance, the shadow
     frustum, the spacing of a newly dropped object — becomes nonsense the
     moment one of those plates is in the scene: a 9.7 km shadow map at 2048 px
     is 4.8 m per texel, which is no shadow at all.
     So there are two radii. This one ignores anything whose footprint is wider
     than GRANDE, and it is the one the lighting uses. */
  static GRANDE = 300;

  caixaPequenos () {
    const b = new THREE.Box3();
    let algum = false;
    const t = new THREE.Vector3();
    for (const o of this.objetos.values()) {
      if (!o.visible) continue;
      const c = new THREE.Box3().setFromObject(o);
      c.getSize(t);
      if (Math.max(t.x, t.z) > Mundo.GRANDE) continue;
      b.union(c); algum = true;
    }
    return algum ? b : null;
  }

  raioCena () {
    const b = this.caixaTudo();
    return Math.max(40, b.getSize(new THREE.Vector3()).length() / 2);
  }

  /** Where the shadow map should spend its texels, and how wide. */
  focoSombra () {
    const b = this.caixaPequenos() || this.caixaTudo();
    const centro = b.getCenter(new THREE.Vector3());
    centro.y = 0;
    const raio = THREE.MathUtils.clamp(
      b.getSize(new THREE.Vector3()).length() / 2, 60, 800);
    return { centro, raio };
  }

  /** Distance at which `raio` fills the frame, honouring the tighter FOV.
   *  The margin is below 1 on purpose: an aircraft seen from three-quarters
   *  never fills its own bounding sphere, so fitting the sphere exactly leaves
   *  the subject small. 0.85 is the same trick export/viewer.html uses. */
  distanciaPara (raio, margem = 0.85) {
    const fovY = THREE.MathUtils.degToRad(this.camP.fov);
    const fovX = 2 * Math.atan(Math.tan(fovY / 2) * (this.camP.aspect || 1));
    return margem * raio / Math.sin(Math.min(fovY, fovX) / 2);
  }

  enquadrar (caixa, dir = null) {
    const centro = caixa.getCenter(new THREE.Vector3());
    const raio = Math.max(1, caixa.getSize(new THREE.Vector3()).length() / 2);
    const d = this.distanciaPara(raio);
    const v = (dir || new THREE.Vector3(-0.62, 0.30, 0.72)).clone().normalize();
    this.camP.position.copy(centro).addScaledVector(v, d);
    this.controles.target.copy(centro);
    this.ajustarProfundidade();
    this.controles.update();
    this.atualizarOrto();
  }

  /** Named views. The aircraft's nose points along −X, so "front" looks +X. */
  vista (nome, caixa) {
    const dirs = {
      frente: new THREE.Vector3(-1, 0.02, 0),
      lado: new THREE.Vector3(0, 0.03, 1),
      topo: new THREE.Vector3(0, 1, 0.001),
      'tres-quartos': new THREE.Vector3(-0.62, 0.30, 0.72),
      heroi: new THREE.Vector3(-0.86, 0.13, 0.50),
    };
    this.enquadrar(caixa, dirs[nome] || dirs['tres-quartos']);
  }

  poseAtual (fov, orto) {
    return {
      pos: this.camP.position.toArray().map(n => +n.toFixed(3)),
      alvo: this.controles.target.toArray().map(n => +n.toFixed(3)),
      fov, orto,
    };
  }

  aplicarPose (p) {
    if (!p) return;
    this.camP.position.fromArray(p.pos);
    this.controles.target.fromArray(p.alvo);
    if (p.fov) { this.camP.fov = p.fov; this.camP.updateProjectionMatrix(); }
    this.controles.update();
    this.atualizarOrto();
  }

  /* -------------------------------------------------------------- render */

  /** The interactive loop. Exports pause it so nothing fights the motion. */
  iniciarLoop (fn) { this._loop = fn; this.renderer.setAnimationLoop(fn); }
  pausar () { this.renderer.setAnimationLoop(null); }
  retomar () { if (this._loop) this.renderer.setAnimationLoop(this._loop); }

  /** near/far from where the camera actually IS.
   *
   *  Pinning them at "frame this box" was fine while every scene was aircraft.
   *  With a 6 km field plate, framing it gave near = 55 m and the next aircraft
   *  you flew up to vanished into the near plane. Deriving them from the orbit
   *  distance instead keeps the ratio near 5000:1 at every zoom level, which a
   *  24-bit depth buffer handles without fighting — and it survives the
   *  orthographic toggle, which a logarithmic depth buffer would not (ortho has
   *  w = 1, so the log-depth chunk flattens). */
  ajustarProfundidade () {
    const d = this.camP.position.distanceTo(this.controles.target);
    /* The RATIO is what a 24-bit depth buffer cares about, and it has to stay
       near 3000:1 at every zoom: a 3 cm gap between an apron slab and the
       ground plane z-fights visibly at 20000:1, which the first version of this
       function produced at 60 m out. near tracks the orbit distance (1%, so
       nothing you can be looking at is ever clipped) and far stays as tight as
       the scene allows. */
    const perto = THREE.MathUtils.clamp(d * 0.01, 0.2, 8);
    const longe = Math.max(1500, d * 3 + (this._raioCena || 200) * 3);
    if (Math.abs(perto - this.camP.near) > this.camP.near * 0.02 ||
        Math.abs(longe - this.camP.far) > this.camP.far * 0.02) {
      this.camP.near = perto;
      this.camP.far = longe;
      this.camP.updateProjectionMatrix();
    }
  }

  render () {
    this.ajustarProfundidade();
    if (this.cam === this.camO) this.atualizarOrto();
    this.renderer.render(this.cena, this.cam);
  }

  estatisticas () {
    const i = this.renderer.info;
    return { chamadas: i.render.calls, triangulos: i.render.triangles, geometrias: i.memory.geometries, texturas: i.memory.textures };
  }
}
