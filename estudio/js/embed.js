/* embed.js — the runtime an exported embed loads.
 *
 * The whole point of this file is that an embed is NOT a second renderer with
 * its own idea of what a scene looks like. It builds the same Mundo the studio
 * builds, from the same document, and simply never constructs the editor. If a
 * scene looks right in the studio it looks right in the embed, or one of them
 * is broken and both are wrong in the same place.
 *
 * The generated HTML supplies its own asset table (slug → GLB URL relative to
 * the embed page), so the embed does not need export/manifest.json.
 */

import { Mundo } from './mundo.js';
import { registrarAssets } from './frota.js';

/**
 * @param {HTMLElement} el   container; it is sized by CSS, the canvas fills it
 * @param {object} doc       a scene document (schema latam-estudio/1) + .assets
 * @param {object} opc       { autoGirar, velocidadeGiro, zoom, pan }
 */
export async function montar (el, doc, opc = {}) {
  if (!doc || doc.schema !== 'latam-estudio/1') {
    throw new Error('not a latam-estudio/1 scene document');
  }
  registrarAssets(doc.assets || {});

  const m = new Mundo(el);
  m.aplicarRender(doc.render);
  m.aplicarAmbiente(doc.ambiente);
  await m.sincronizar(doc);
  m.aplicarAmbiente(doc.ambiente);          // again: the shadow camera needs the real scene radius

  m.aplicarPose({ pos: doc.camera.pos, alvo: doc.camera.alvo, fov: doc.camera.fov });
  if (doc.camera.orto) m.usarOrto(true);

  const c = m.controles;
  c.enableZoom = opc.zoom !== false;
  c.enablePan = opc.pan !== false;
  c.autoRotate = !!opc.autoGirar;
  c.autoRotateSpeed = opc.velocidadeGiro ?? 0.4;
  c.minDistance = 2;
  c.maxDistance = 12000;

  m.iniciarLoop(() => { c.update(); m.render(); });
  return m;
}
