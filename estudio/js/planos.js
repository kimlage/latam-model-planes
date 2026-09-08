/* Editorial camera cuts, evaluated identically by viewport, GIF and embed.
 * Following shots store WORLD-axis offsets from a moving object's position.
 * A cut belongs to the incoming shot at its exact boundary. Gaps use the
 * existing camera key tracks (or document camera), so old clips keep working.
 */
export function planoEm(linha, t) {
  const ps = linha?.planos || [];
  return ps.find(p => t >= p.inicio && t < p.fim)
    || (t >= linha?.duracao ? ps.find(p => p.fim === linha.duracao) : null);
}

export function cameraDoPlano(p, t, origem = [0, 0, 0]) {
  let u = Math.max(0, Math.min(1, (t-p.inicio)/(p.fim-p.inicio)));
  if (p.curva === 'suave') u = u*u*(3-2*u);
  if (p.curva === 'fixa') u = 0;
  const a = p.cameraInicio, b = p.cameraFim;
  let camera = {pos:a.pos.map((v,i)=>v+(b.pos[i]-v)*u),
    alvo:a.alvo.map((v,i)=>v+(b.alvo[i]-v)*u), fov:a.fov+(b.fov-a.fov)*u};
  if (p.caminho?.length >= 2) {
    const path = p.caminho;
    let i = 0;
    while(i < path.length-2 && path[i+1].u < u) i++;
    const c = path[i], d = path[i+1];
    const v = Math.max(0,Math.min(1,(u-c.u)/(d.u-c.u)));
    // Endpoint edits smoothly offset the imported motion instead of erasing it.
    const first = path[0], last = path.at(-1);
    for (const k of ['pos','alvo']) camera[k] = camera[k].map((x,j)=>
      x + c[k][j]+(d[k][j]-c[k][j])*v - (first[k][j]+(last[k][j]-first[k][j])*u));
    camera.fov += c.fov+(d.fov-c.fov)*v-(first.fov+(last.fov-first.fov)*u);
  }
  if(p.seguir) for(const k of ['pos','alvo']) camera[k]=camera[k].map((v,i)=>v+origem[i]);
  return camera;
}

export function aplicarPlanos(estado, t, ov) {
  const p = planoEm(estado.linha, t);
  if (!p) return;
  const origem = p.seguir ? ov.objetos.get(p.seguir)?.pos
    || estado.objetos.find(o => o.id === p.seguir)?.pos || [0,0,0] : [0,0,0];
  ov.camera = cameraDoPlano(p, t, origem);
  ov.plano = {id:p.id, nome:p.nome};
}

export function poseRelativa(pose, origem, seguir) {
  return {pos:pose.pos.map((v,i) => v-(seguir ? origem[i] : 0)),
    alvo:pose.alvo.map((v,i) => v-(seguir ? origem[i] : 0)), fov:pose.fov};
}
