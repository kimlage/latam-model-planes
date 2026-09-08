/* Run in a freshly opened Studio: await (await import('./tests/regression.js')).run().
   No network dependencies or test framework. Restores the document and storage. */
import { normalizarDocumento } from '../js/documento.js';
import { estadoPadrao, novoObjeto, clonar, salvarCena, renomearCena, lerBiblioteca, nomeLivre } from '../js/estado.js';
import { CENAS_BASE, cenaBase } from '../js/cenas.js';
import { novaTrilha } from '../js/tempo.js';
import { documentoParaJson, construirEmbed, exportarGif, exportarPng, exportarSequencia } from '../js/exportar.js';
import { abrirModal, fecharModal, h } from '../js/dialogos.js';

export async function run () {
  const out = [], app = window.__estudio;
  const assert = (ok, message) => { if (!ok) throw new Error(message); };
  const test = async (name, fn) => {
    try { await fn(); out.push({ name, ok: true }); }
    catch (e) { out.push({ name, ok: false, error: e.message }); }
  };
  const rejects = fn => { let error; try { fn(); } catch (e) { error = e; } assert(error, 'Must reject'); };
  const baseline = clonar(app.estado);
  const keys = ['latam-estudio/cenas/1', 'latam-estudio/sessao/1'];
  const saved = keys.map(k => localStorage.getItem(k));
  try {
    await test('All nine legacy starters normalize', () => {
      for (const key of Object.keys(CENAS_BASE)) normalizarDocumento(cenaBase(key));
    });
    await test('Both shipped clip documents normalize', async () => {
      for (const f of ['exemplo_clipe.json', 'clipe_gru_777_v1.json'])
        normalizarDocumento(await (await fetch(new URL('../' + f, import.meta.url))).json());
    });
    await test('Older /1 documents receive defaults', () => {
      const d = normalizarDocumento({schema:'latam-estudio/1', objetos:[]});
      assert(d.camera.fov === 35 && d.linha.fps === 25, 'Defaults missing');
    });
    await test('Wrong schema, duplicate IDs, invalid vectors, unsafe sizes rejected', () => {
      rejects(() => normalizarDocumento({objetos:[]}));
      for (const mutate of [d => d.objetos.push(clonar(d.objetos[0])), d => d.objetos[0].pos = [0, null, 2],
        d => d.objetos[0].esc = [0, 1, 1], d => d.linha.fps = 0,
        d => d.render.sombraPx = 100000, d => d.ambiente.chao.tamanho = 1e7,
        d => d.render.exposicao = 'bad', d => d.ambiente.sol.elev = {}, d => d.camera.pos = [NaN, 0, 1]]) {
        const d = estadoPadrao(); d.objetos = [novoObjeto('aeronave','B77W','Test')]; mutate(d);
        rejects(() => normalizarDocumento(d));
      }
    });
    await test('Invalid import keeps document and rendered objects', async () => {
      const before = JSON.stringify(app.estado), objs = app.mundo.objetos.size;
      let error; try { await app.carregarDocumento({schema:'wrong', objetos:[]}); } catch (e) { error = e; }
      assert(error && JSON.stringify(app.estado) === before && app.mundo.objetos.size === objs, 'Scene changed');
    });
    await test('Unavailable asset keeps the open scene', async () => {
      const d = estadoPadrao(); d.objetos = [novoObjeto('aeronave','missing_model','Missing')];
      const before = JSON.stringify(app.estado); let error;
      try { await app.carregarDocumento(d); } catch(e) { error = e; }
      assert(error && before === JSON.stringify(app.estado), 'Missing model replaced scene');
    });
    await test('Failed asset build keeps the previous rendered world', async () => {
      const before = [...app.mundo.objetos.values()];
      const d = estadoPadrao(); d.objetos = [novoObjeto('prop','missing_prop','Missing')];
      let error; try { await app.mundo.sincronizar(d); } catch(e) { error = e; }
      assert(error && [...app.mundo.objetos.values()].every((obj,i)=>obj===before[i]), 'World replaced on failure');
    });
    await test('Scene rename never overwrites a collision', () => {
      const a = {...estadoPadrao(), nome:'__qa_a'}, b = {...estadoPadrao(), nome:'__qa_b'};
      assert(salvarCena(a) && salvarCena(b), 'Setup save failed');
      assert(!renomearCena('__qa_a','__qa_b') && Object.hasOwn(lerBiblioteca(), '__qa_a'), 'Source lost');
      assert(renomearCena('__qa_a','__qa_c'), 'Atomic rename failed');
      assert(nomeLivre('__qa_b') !== '__qa_b', 'Copy collision');
    });
    await test('Corrupt library is preserved on save failure', () => {
      const key = keys[0], before = localStorage.getItem(key);
      try { localStorage.setItem(key, '{broken'); assert(salvarCena(estadoPadrao()) === null, 'Accepted corrupt storage');
        assert(localStorage.getItem(key) === '{broken', 'Corrupt bytes overwritten'); }
      finally { if(before === null) localStorage.removeItem(key); else localStorage.setItem(key,before); }
    });
    await test('All nine scenes load with matching object counts', async () => {
      for (const key of Object.keys(CENAS_BASE)) {
        await app.carregarDocumento(cenaBase(key));
        assert(app.estado.objetos.length === app.mundo.objetos.size, `Incomplete ${key}`);
      }
    });
    await app.carregarDocumento(cenaBase('heroi'));
    await test('Unchanged ground and grid are reused across lighting updates', () => {
      const ground = app.mundo.chao, grid = app.mundo.grade;
      app.mundo.aplicarAmbiente(app.estado.ambiente);
      assert(app.mundo.chao===ground && app.mundo.grade===grid, 'Unnecessary geometry allocation');
    });
    await test('Camera framing undo and redo restore the actual camera', async () => {
      const before = clonar(app.estado.camera);
      app.atalho('enquadrar-tudo');
      const after = clonar(app.estado.camera);
      await app.atalho('desfazer');
      assert(app.mundo.camP.position.toArray().every((v,i)=>Math.abs(v-before.pos[i])<.02), 'Camera undo failed');
      await app.atalho('refazer');
      assert(app.mundo.camP.position.toArray().every((v,i)=>Math.abs(v-after.pos[i])<.02), 'Camera redo failed');
    });
    await test('Orthographic navigation keeps a persistent driving camera', () => {
      app.mundo.usarOrto(true);
      assert(app.mundo.controles.object === app.mundo.camP, 'Wrong camera controlled');
      app.mundo.usarOrto(false);
    });
    await test('Loading a perspective scene resets orthographic mode and gizmo', async () => {
      const d = clonar(app.estado); d.camera.orto = true; await app.carregarDocumento(d);
      await app.carregarDocumento(cenaBase('heroi'));
      assert(app.mundo.cam === app.mundo.camP && app.editor.gizmo.camera === app.mundo.camP, 'Camera remained orthographic');
    });
    await test('Modal keyboard never deletes the selected aircraft', () => {
      app.editor.selecionar([app.estado.objetos[0].id]);
      abrirModal('QA dialog', h('button', {}, 'Test'));
      const n = app.estado.objetos.length;
      document.querySelector('#modal-fechar').dispatchEvent(new KeyboardEvent('keydown',{key:'Delete',bubbles:true,cancelable:true}));
      assert(app.estado.objetos.length === n, 'Object deleted behind modal');
      fecharModal();
    });
    await test('Delete selected key keeps selected object and can undo', async () => {
      const id = app.estado.objetos[0].id;
      app.editor.selecionar([id]);
      const tr = novaTrilha('objeto.pos',id);
      tr.chaves = [{t:0,v:[0,0,0],e:'linear'},{t:1,v:[4,0,0],e:'linear'}];
      app.estado.linha.trilhas.push(tr); app.registrar('qa keys');
      app.dock.chaveSel = {trilhaId:tr.id,t:1};
      document.body.dispatchEvent(new KeyboardEvent('keydown',{key:'Delete',bubbles:true,cancelable:true}));
      assert(app.estado.objetos.length === 1 && tr.chaves.length === 1, 'Key or object deletion wrong');
      const s = app.historico.desfazer();
      assert(s.linha.trilhas[0].chaves.length === 2, 'Key cannot undo');
      await app.carregarDocumento(s);
    });
    await test('Locked object cannot join a multi-selection', () => {
      const id = app.estado.objetos[0].id;
      app.editor.travar(id,true); app.editor.alternar(id);
      assert(!app.editor.selecao.includes(id), 'Locked object selected'); app.editor.travar(id,false);
    });
    await test('JSON asset URLs resolve for aircraft, hero tier and airport', async () => {
      const d = cenaBase('pista-gru'); d.objetos.find(o=>o.tipo==='aeronave').nivel='heroi';
      await app.carregarDocumento(d);
      const doc = documentoParaJson(app.estado,app.mundo,{comAssets:true,baseGlb:'../export/'});
      const paths = new Set(Object.values(doc.assets).flatMap(a=>[a.arquivo,...Object.values(a.niveis).map(n=>n.arquivo)]));
      for (const path of paths) assert((await fetch(new URL(path,location.href),{method:'HEAD'})).ok, `Broken URL ${path}`);
      normalizarDocumento(doc);
    });
    await test('Embed escapes scene text and rejects executable URLs', () => {
      const d = clonar(app.estado); d.objetos[0].nome = '</script><script>window.BAD=1</script>';
      const html = construirEmbed(d,app.mundo,{modo:'relativo'});
      assert(!html.includes('</script><script>window.BAD'), 'Executable scene text');
      assert(html.includes('\\u003c/script>'), 'JSON not escaped');
      rejects(()=>construirEmbed(d,app.mundo,{modo:'url',baseEstudio:'javascript:alert(1)',baseGlb:'https://example.com/'}));
    });
    await test('PNG renders real pixels and restores renderer size', async () => {
      const canvas = app.mundo.renderer.domElement, size = [canvas.width,canvas.height];
      const r = await exportarPng(app.mundo,{larg:480,alt:270,ss:1});
      const bitmap = await createImageBitmap(r.blob);
      assert(bitmap.width===480 && bitmap.height===270 && r.bytes>1000,'Invalid PNG'); bitmap.close();
      assert(canvas.width===size[0] && canvas.height===size[1], 'Renderer not restored');
    });
    await test('GIF produces an animated file and restores object/camera state', async () => {
      const before = JSON.stringify(app.estado);
      const pose = app.mundo.poseAtual();
      const r = await exportarGif(app.mundo,app.estado,{modo:'turntable-cena',quadros:8,fps:10,larg:320,alt:180,ss:1,cores:64,loop:true});
      assert(new TextDecoder().decode((await r.blob.arrayBuffer()).slice(0,6))==='GIF89a' && r.quadros===8,'Invalid GIF');
      assert(before===JSON.stringify(app.estado),'Export mutated document');
      const after = app.mundo.poseAtual();
      assert(after.pos.every((v,i)=>Math.abs(v-pose.pos[i])<.01),'Camera not restored');
    });
    await test('PNG sequence ZIP contains all requested frames', async () => {
      const d = clonar(app.estado), tr = novaTrilha('objeto.pos',d.objetos[0].id);
      const p = d.objetos[0].pos;
      tr.chaves = [{t:0,v:[...p],e:'linear'},{t:1,v:[p[0]+10,p[1],p[2]],e:'linear'}];
      d.linha.trilhas = [tr]; d.linha.voos = []; await app.carregarDocumento(d);
      const r = await exportarSequencia(app.mundo,app.estado,{larg:160,alt:90,ss:1,quadros:4});
      const raw = await r.blob.arrayBuffer(), view = new DataView(raw);
      assert(view.getUint32(0,true)===0x04034b50 && view.getUint16(raw.byteLength-12,true)===6,'Expected four PNGs plus attribution and sequence metadata');
      assert(r.quadros===4 && r.bytes>1000,'Empty sequence');
    });
  } finally {
    fecharModal();
    await app.carregarDocumento(baseline);
    keys.forEach((k,i)=> saved[i] === null ? localStorage.removeItem(k) : localStorage.setItem(k,saved[i]));
  }
  window.__qaResults = out;
  return out;
}
