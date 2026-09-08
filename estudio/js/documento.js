/* Validate before replacing the open scene. Older /1 documents receive defaults. */
import { SCHEMA, estadoPadrao, novoObjeto } from './estado.js';
import { CANAIS, FPS_LEGAIS_T, linhaPadrao } from './tempo.js';

const registro = v => v !== null && typeof v === 'object' && !Array.isArray(v);
const exigir = (ok, campo) => { if (!ok) throw new Error(`Invalid scene: ${campo}.`); };
const numero = (v, campo, min = -1e7, max = 1e7) =>
  exigir(typeof v === 'number' && Number.isFinite(v) && v >= min && v <= max, campo);
const vetor = (v, campo, n = 3) => {
  exigir(Array.isArray(v) && v.length === n, campo);
  v.forEach(x => numero(x, campo));
};

export function normalizarDocumento (doc) {
  exigir(registro(doc) && doc.schema === SCHEMA, `expected ${SCHEMA}`);
  exigir(Array.isArray(doc.objetos) && doc.objetos.length <= 2000, 'objects (maximum 2000)');
  // Reject non-JSON values and dangerous dictionary keys before merging anything.
  const visitar = (v, profundidade = 0) => {
    exigir(profundidade < 32, 'document nesting');
    // Asset byte counts can exceed the coordinate limit (for example 20 MB).
    // Check finiteness here; vectors and editable fields apply their own bounds.
    if (typeof v === 'number') exigir(Number.isFinite(v), 'finite numeric values');
    if (v && typeof v === 'object') for (const [k, x] of Object.entries(v)) {
      exigir(!['__proto__', 'prototype', 'constructor'].includes(k), 'reserved property');
      visitar(x, profundidade + 1);
    }
  };
  visitar(doc);
  for (const k of ['ambiente', 'render', 'camera', 'poses', 'linha']) {
    if (doc[k] !== undefined) exigir(registro(doc[k]), k);
  }
  for (const k of ['sol', 'chao', 'neblina']) {
    if (doc.ambiente?.[k] !== undefined) exigir(registro(doc.ambiente[k]), `environment ${k}`);
  }
  if (doc.render?.correcao !== undefined) exigir(registro(doc.render.correcao), 'colour grade');
  const b = estadoPadrao();
  const novo = {
    ...b, ...doc,
    nome: typeof doc.nome === 'string' ? doc.nome.trim().slice(0, 200) || b.nome : b.nome,
    ambiente: { ...b.ambiente, ...doc.ambiente,
      sol: { ...b.ambiente.sol, ...doc.ambiente?.sol },
      chao: { ...b.ambiente.chao, ...doc.ambiente?.chao },
      neblina: { ...b.ambiente.neblina, ...doc.ambiente?.neblina } },
    render: { ...b.render, ...doc.render,
      correcao: { ...b.render.correcao, ...doc.render?.correcao } },
    camera: { ...b.camera, ...doc.camera,
      ...(doc.vista && doc.camera?.pos === null && doc.camera?.alvo === null
        ? { pos: b.camera.pos, alvo: b.camera.alvo } : {}) },
    poses: { ...b.poses, ...doc.poses },
    linha: { ...linhaPadrao(), ...doc.linha },
    objetos: doc.objetos.map(o => {
      exigir(registro(o), 'object record');
      exigir(['aeronave', 'cenario', 'prop'].includes(o.tipo), 'object type');
      exigir(typeof o.slug === 'string' && /^[\w-]+$/.test(o.slug), 'asset slug');
      const d = { ...novoObjeto(o.tipo, o.slug, o.slug), ...o };
      exigir(typeof d.id === 'string' && d.id.length > 0, 'object id');
      exigir(typeof d.nome === 'string', 'object name');
      for (const k of ['pos', 'rot', 'esc']) vetor(d[k], `${d.nome}: ${k}`);
      exigir(d.esc.every(x => Math.abs(x) >= 0.0001 && Math.abs(x) <= 10000), 'non-zero scale');
      if (d.nivel !== undefined) exigir(['web', 'heroi', 'alta'].includes(d.nivel), 'detail tier');
      for (const k of ['visivel', 'travado']) exigir(typeof d[k] === 'boolean', k);
      return d;
    }),
  };
  const ids = new Set(novo.objetos.map(o => o.id));
  exigir(ids.size === novo.objetos.length, 'duplicate object ids');
  for (const p of [novo.camera, ...Object.values(novo.poses).filter(Boolean)]) {
    exigir(registro(p), 'camera pose');
    vetor(p.pos, 'camera position'); vetor(p.alvo, 'camera target');
    numero(p.fov, 'camera FOV', 1, 179);
  }
  const l = novo.linha;
  numero(l.duracao, 'timeline length', 0.04, 600);
  exigir(FPS_LEGAIS_T.includes(l.fps), 'timeline frame rate');
  exigir(Array.isArray(l.trilhas) && l.trilhas.length <= 10000, 'tracks');
  exigir(Array.isArray(l.voos) && l.voos.length <= 2000, 'flights');
  exigir(Array.isArray(l.planos) && l.planos.length <= 500, 'camera shots');
  const planos = [...l.planos].sort((a,b) => a.inicio-b.inicio);
  const planosIds = new Set();
  let fimPlano = 0;
  for (const p of planos) {
    exigir(registro(p) && typeof p.id === 'string' && !planosIds.has(p.id), 'unique shot id');
    planosIds.add(p.id);
    exigir(typeof p.nome === 'string' && p.nome.length > 0, 'shot name');
    numero(p.inicio, 'shot start', 0, l.duracao);
    numero(p.fim, 'shot end', 0, l.duracao);
    exigir(p.fim > p.inicio && p.inicio >= fimPlano, 'shots must not overlap');
    fimPlano = p.fim;
    exigir(['linear','suave','fixa'].includes(p.curva), 'shot interpolation');
    exigir(!p.seguir || ids.has(p.seguir), 'shot follow target');
    if (p.caminho !== undefined) {
      exigir(Array.isArray(p.caminho) && p.caminho.length >= 2 && p.caminho.length <= 15000,'shot camera path');
      let anterior = -1;
      for(const q of p.caminho) {
        exigir(registro(q),'shot path sample'); numero(q.u,'shot path progress',0,1);
        exigir(q.u > anterior,'shot path must advance'); anterior = q.u;
      }
      exigir(p.caminho[0].u === 0 && p.caminho.at(-1).u === 1,'shot path endpoints');
    }
    for (const pose of [p.cameraInicio,p.cameraFim,...(p.caminho||[])]) {
      exigir(registro(pose), 'shot camera pose');
      vetor(pose.pos, 'shot position'); vetor(pose.alvo, 'shot target');
      numero(pose.fov, 'shot FOV', 1, 179);
      exigir(pose.pos.some((v,i) => Math.abs(v-pose.alvo[i]) > 0.001), 'shot camera must have a direction');
    }
  }
  l.planos = planos;
  for (const conjunto of [l.trilhas, l.voos]) {
    exigir(conjunto.every(x => registro(x) && typeof x.id === 'string' && x.id.length > 0), 'animation id');
    exigir(new Set(conjunto.map(x => x.id)).size === conjunto.length, 'duplicate animation ids');
  }
  exigir(new Set(l.voos.map(v => v.ref)).size === l.voos.length, 'one flight per aircraft');
  for (const t of l.trilhas) {
    exigir(registro(t) && Object.hasOwn(CANAIS, t.canal), 'track channel');
    const c = CANAIS[t.canal];
    if (c.alvo === 'objeto') exigir(ids.has(t.ref), 'track object');
    exigir(Array.isArray(t.chaves) && t.chaves.length <= 20000, 'keyframes');
    let anterior = -Infinity;
    for (const k of t.chaves) {
      exigir(registro(k), 'keyframe'); numero(k.t, 'key time', 0, 600);
      exigir(k.t > anterior, 'key times must be unique and increasing'); anterior = k.t;
      if (c.dim === 3) vetor(k.v, 'key value');
      else if (c.discreto) exigir([true, false, 0, 1].includes(k.v), 'boolean key value');
      else numero(k.v, 'key value');
    }
  }
  for (const v of l.voos) {
    exigir(registro(v) && novo.objetos.some(o => o.id === v.ref && o.tipo === 'aeronave'), 'flight aircraft');
    exigir(Array.isArray(v.rota) && v.rota.length >= 2 && v.rota.length <= 2000, 'flight waypoints');
    numero(v.t0, 'flight start', 0, 600);
    for (const p of v.rota) {
      exigir(registro(p), 'waypoint');
      for (const k of ['x', 'z', 'alt']) numero(p[k], `waypoint ${k}`);
      numero(p.v, 'waypoint speed', 0.1, 1000);
    }
  }
  numero(novo.render.pixelRatioMax, 'pixel ratio', 0.5, 3);
  exigir([512, 1024, 2048, 4096].includes(novo.render.sombraPx), 'shadow map size');
  numero(novo.render.aa, 'export sampling', 1, 3);
  numero(novo.ambiente.chao.tamanho, 'ground size', 1, 20000);
  const a = novo.ambiente, r = novo.render;
  for (const [v, nome, min, max] of [
    [r.exposicao, 'exposure', 0, 20], [a.envIntensidade, 'environment intensity', 0, 10],
    [a.sol.elev, 'sun elevation', -90, 90], [a.sol.azim, 'sun azimuth', -360, 720],
    [a.sol.intensidade, 'sun intensity', 0, 20], [a.neblina.densidade, 'fog density', 0, 1000],
    [r.correcao.contraste, 'contrast', 0, 5], [r.correcao.saturacao, 'saturation', 0, 5],
    [r.correcao.elevar, 'lift', -1, 1], [r.correcao.temperatura, 'temperature', -1, 1],
    [r.correcao.vinheta, 'vignette', 0, 1],
  ]) numero(v, nome, min, max);
  for (const v of [a.grade, a.chao.ligado, a.neblina.ligado, r.sombras, novo.camera.orto, l.loop, l.autochave])
    exigir(typeof v === 'boolean', 'boolean setting');
  for (const [v, opcoes] of [
    [r.tone, ['aces', 'agx', 'neutral', 'reinhard', 'linear']],
    [a.envPreset, ['ceu', 'sala', 'nenhum']], [a.fundo, ['ceu', 'cor', 'transparente']],
    [a.chao.tipo, ['apron', 'concreto', 'pista', 'grama', 'estudio', 'sombra']],
  ]) exigir(opcoes.includes(v), 'unknown environment/render setting');
  for (const cor of [novo.ambiente.sol.cor, novo.ambiente.fundoCor])
    exigir(typeof cor === 'string' && /^#[0-9a-f]{6}$/i.test(cor), 'colour');
  return novo;
}
