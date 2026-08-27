"""SUPERADO 2026-08-27 (pintor unico): absorvido por refazer_marcas.py (tag b788).
Fica como registro historico do que pintou o estado embarcado. NAO rodar.

787-8 livery — STAGE 3: the two marks that stage 2 got wrong, measured on CC-BBF/CC-BBB.

Run headless:
  blender -b "boeing 787-8/B788_LATAM.blend" --python "boeing 787-8/build_788_livery2.py"

Both defects were found by measuring the photos and the texture in the same
(x, z) frame and comparing numbers, not by eye:

1. REGISTRATION was 60% too long and 67% too tall, and 0.4 m too low.
   Stage 2 rebuilt CC-BBF from the -9's CC-BGK glyph slots at cap 0.50 m, which
   is the -9's painted size; the -8's is smaller.  Measured twice, on two
   photos, two sides, each anchored on a local ruler rather than on the
   nose-to-tail span:
     CC-BBB port  (ref_bbb_mia23, scale = window pitch 0.61 m, x anchored on
                   door 4 = 43.56):  x 44.42..46.04, z 1.17..1.47, cap 0.30
     CC-BBF stbd  (ref_bbf_mia23, projective fit on nose tip + doors 1/2/4):
                   x 44.36..46.02, cap 0.28..0.30
   Target adopted: x 44.40..46.03 (1.63 m), z 1.17..1.47, cap 0.30 m, both
   sides white-inside-the-indigo (confirmed on CC-BBB port AND CC-BBF stbd).
   The glyphs are NOT redrawn - the ink already painted is resampled with area
   averaging into the smaller box, so the letterforms (and the constructed F)
   survive exactly.

2. LOCKUP sat 0.12 m too low and its letters clipped the top 0.08 m of the
   window row.  Measured on CC-BBB (window-pitch scale): letters z 1.06..1.83,
   window top z 1.02 - i.e. a ~0.10 m gap on the real aircraft, an overlap in
   the model.  Raised +0.12 m; artwork and proportions untouched (the mesh
   reproduces the official SVG ink ratio 4.30 exactly - checked).

3. STARBOARD LOCKUP WAS MIRRORED THE WRONG WAY - the symbol sat at the TAIL end.
   Stage 2 painted the starboard side from B789_LogoLATAM_D, which is the whole
   lockup rotated 180 deg about z; that reverses the composition as a block, so
   the symbol ends up aft.  Both reference photos show the symbol on the NOSE
   side of BOTH flanks (CC-BBB port: symbol, L, A, T, A, M going aft; CC-BBF
   stbd: symbol, M, A, T, A, L going aft).  The 787-9's painted texture is
   correct while its D mesh has the same fault, so the -9's paint was not made
   from that mesh either.  Fixed by mirroring the symbol about its own centre
   and the wordmark about its own centre, from the port (E) meshes.
"""
import bpy
import json
import math
import os
import numpy as np
import mathutils

D = bpy.data
BASE = os.path.dirname(os.path.abspath(__file__))
log = lambda *a: print("[B788L2]", *a)

L_UV = 57.5
W, H = 4096, 1024
WHITE = np.array([0.969, 0.976, 0.980], np.float32)
INDIGO = np.array([0.165, 0.000, 0.533], np.float32)
CORAL = np.array([0.929, 0.086, 0.318], np.float32)

DZ_LOCKUP = 0.12
REG_X0, REG_X1 = 44.40, 46.03
REG_Z0, REG_Z1 = 1.17, 1.47

rings = json.load(open(os.path.join(BASE, "b788_rings.json")))
rx = np.array([r["x"] for r in rings])
rzc = np.array([r["zc"] for r in rings])
rrz = np.array([r["rz"] for r in rings])
rry = np.array([r["ry"] for r in rings])


def read_img(name):
    img = D.images[name]
    w, h = img.size
    buf = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(buf)
    return img, buf.reshape(h, w, 4)


img_tex, tex = read_img("LiveryTex")
img_fac, fac = read_img("LiveryFac")

X = (np.arange(W) + 0.5) / W * L_UV
TH = (np.arange(H) + 0.5) / H * 2 * math.pi - math.pi
Xg = np.broadcast_to(X, (H, W))
THg = np.broadcast_to(TH[:, None], (H, W))
ZCg = np.interp(X, rx, rzc)[None, :]
RZg = np.interp(X, rx, rrz)[None, :]
RYg = np.interp(X, rx, rry)[None, :]
Zg = ZCg + RZg * np.cos(THg)
Yg = RYg * np.sin(THg)
THdeg = np.degrees(np.abs(THg))

PORT = Yg < 0
STBD = Yg > 0
FLANK = (np.abs(np.sin(THg)) > 0.30) & (THdeg < 120)


def wedge_mask(margin=0.0):
    return ((Xg >= 42.68 + 0.992 * Zg - margin) &
            (THdeg <= 117.0 - 5.2 * (Xg - 42.61) + margin * 5) &
            (Xg <= 51.05 + 0.3858 * Zg + margin))


# ---------------------------------------------------------------- 1. registration
lum = tex[..., :3].mean(axis=2)
chroma = tex[..., :3].max(axis=2) - tex[..., :3].min(axis=2)
inw = wedge_mask(-0.12)
# stage 2 declared exactly this box for the CC-BBF glyphs; take it literally
# instead of scanning a bbox — a scan drags in the door-4 outline at x<=44.15
# and the resample then paints a white shard in front of the first C.
SRC_X0, SRC_X1, SRC_Z0, SRC_Z1 = 44.26, 46.90, 0.78, 1.28
lum_ind = float(INDIGO.mean())
lum_wht = float(WHITE.mean())
cov_src = np.clip((lum - lum_ind - 0.05) / (lum_wht - lum_ind - 0.05), 0.0, 1.0)
srcbox = ((Xg >= SRC_X0) & (Xg <= SRC_X1) & (Zg >= SRC_Z0) & (Zg <= SRC_Z1) & inw)
src = srcbox & (cov_src > 0.02)
log("registration source texels:", int(src.sum()))
# everything in this rectangle is flat indigo on the real aeroplane except the
# registration itself (door 4's outline ends at x 44.15, the wedge's forward
# boundary at this height is at x <= 44.07), so it is safe to flatten it whole
FLAT = (Xg >= 44.20) & (Xg <= 47.10) & (Zg >= 0.55) & (Zg <= 1.45) & inw

for tag, side in (("port", PORT), ("stbd", STBD)):
    m = src & side
    if m.sum() < 50:
        log("registration", tag, "NOT FOUND"); continue
    sx0, sx1, sz0, sz1 = SRC_X0, SRC_X1, SRC_Z0, SRC_Z1
    jj, ii = np.nonzero(m)
    log(f"registration {tag} source ink x {Xg[0,ii.min()]:.2f}..{Xg[0,ii.max()]:.2f} "
        f"z {Zg[jj,ii].min():.2f}..{Zg[jj,ii].max():.2f}, {int(m.sum())} texels "
        f"(box {sx1-sx0:.2f} x {sz1-sz0:.2f} m)")

    covS = np.where(m, cov_src, 0.0)
    # erase: flatten the whole rectangle back to indigo, fringe included
    f = FLAT & side
    tex[f, :3] = INDIGO
    fac[f, 0] = fac[f, 1] = fac[f, 2] = 1.0

    # target box, same side
    tgt = ((Xg >= REG_X0 - 0.06) & (Xg <= REG_X1 + 0.06) &
           (Zg >= REG_Z0 - 0.06) & (Zg <= REG_Z1 + 0.06) & side & inw)
    jt, it = np.nonzero(tgt)
    if len(it) == 0:
        log("registration", tag, "EMPTY TARGET"); continue
    kx = (sx1 - sx0) / (REG_X1 - REG_X0)
    kz = (sz1 - sz0) / (REG_Z1 - REG_Z0)
    # texel footprint for the supersample, in metres
    dx = L_UV / W
    acc = np.zeros(len(it), np.float32)
    SS = 4
    # source lookup grids (nearest texel in the source box, per side)
    src_rows = np.arange(H)
    for a in range(SS):
        for b in range(SS):
            xt = Xg[jt, it] + ((a + 0.5) / SS - 0.5) * dx
            zt = Zg[jt, it] + ((b + 0.5) / SS - 0.5) * 0.018
            xs = sx0 + (xt - REG_X0) * kx
            zs = sz0 + (zt - REG_Z0) * kz
            ci = np.clip((xs / L_UV * W - 0.5).astype(int), 0, W - 1)
            # theta of the source point on the same side
            zc = np.interp(xs, rx, rzc)
            rz = np.interp(xs, rx, rrz)
            c = np.clip((zs - zc) / rz, -1.0, 1.0)
            th = np.arccos(c) * (1.0 if tag == "stbd" else -1.0)
            rj = np.clip(((th + math.pi) / (2 * math.pi) * H - 0.5).astype(int), 0, H - 1)
            ok = (xs >= sx0 - 0.02) & (xs <= sx1 + 0.02) & (zs >= sz0 - 0.02) & (zs <= sz1 + 0.02)
            v = np.zeros(len(it), np.float32)
            v[ok] = covS[rj[ok], ci[ok]]
            acc += v
    acc /= SS * SS
    sel = acc > 0.02
    a = acc[sel][:, None]
    jj2, ii2 = jt[sel], it[sel]
    tex[jj2, ii2, :3] = tex[jj2, ii2, :3] * (1 - a) + WHITE[None, :] * a
    for ch in range(3):
        fac[jj2, ii2, ch] = np.maximum(fac[jj2, ii2, ch], acc[sel])
    log(f"registration {tag} repainted: {int(sel.sum())} texels into "
        f"x {REG_X0:.2f}..{REG_X1:.2f} z {REG_Z0:.2f}..{REG_Z1:.2f} (cap {REG_Z1-REG_Z0:.2f} m)")

# ---------------------------------------------------------------- 2. lockup +0.12 m
lockband = (Xg >= 7.20) & (Xg <= 16.20) & FLANK
m = lockband & (chroma > 0.10)
# the hull base in this texture is pure white with Fac=0 (the #E6E7EA tint comes
# from the shader), so erase to 1.0 — stage 2 wrote 0.975 here and left a patch
# that is invisible in the render but reads as a ghost when you open the texture
tex[m, :3] = 1.0
fac[m, 0] = fac[m, 1] = fac[m, 2] = 0.0
ghost = lockband & (chroma < 0.05) & (np.abs(lum - lum_wht) < 0.01) & (fac[..., 0] < 0.02)
tex[ghost, :3] = 1.0
log("lockup erased:", int(m.sum()), "texels; stage-2 white patch normalised:", int(ghost.sum()))

for nm in ("B789_LogoLATAM_E", "B789_LogoLATAM_E_Coral",
           "B789_LogoLATAM_D", "B789_LogoLATAM_D_Coral"):
    ob = D.objects[nm]
    ob.hide_viewport = False
    ob.location.z += DZ_LOCKUP
bpy.context.view_layer.update()


def tris_of(ob):
    me = ob.data
    me.calc_loop_triangles()
    mw = mathutils.Matrix.LocRotScale(ob.location, ob.rotation_euler, ob.scale)
    vs = [mw @ v.co for v in me.vertices]
    return [[vs[i] for i in t.vertices] for t in me.loop_triangles]


def coverage(tris2, PA, PB, gate, ss=3):
    xs = [p[0] for t in tris2 for p in t]
    ys = [p[1] for t in tris2 for p in t]
    x0, x1 = min(xs) - 0.05, max(xs) + 0.05
    y0, y1 = min(ys) - 0.05, max(ys) + 0.05
    res = max(int(3000 / max(x1 - x0, y1 - y0)), 400)
    nx = max(int((x1 - x0) * res), 8)
    ny = max(int((y1 - y0) * res), 8)
    grid = np.zeros((ny, nx), bool)
    gx, gy = np.meshgrid((np.arange(nx) + 0.5) / nx * (x1 - x0) + x0,
                         (np.arange(ny) + 0.5) / ny * (y1 - y0) + y0)
    for (ax, ay), (bx, by), (cx, cy) in tris2:
        i0 = max(int((min(ax, bx, cx) - x0) / (x1 - x0) * nx) - 1, 0)
        i1 = min(int((max(ax, bx, cx) - x0) / (x1 - x0) * nx) + 2, nx)
        j0 = max(int((min(ay, by, cy) - y0) / (y1 - y0) * ny) - 1, 0)
        j1 = min(int((max(ay, by, cy) - y0) / (y1 - y0) * ny) + 2, ny)
        if i1 <= i0 or j1 <= j0:
            continue
        sx = gx[j0:j1, i0:i1]
        sy = gy[j0:j1, i0:i1]
        d1 = (sx - bx) * (ay - by) - (ax - bx) * (sy - by)
        d2 = (sx - cx) * (by - cy) - (bx - cx) * (sy - cy)
        d3 = (sx - ax) * (cy - ay) - (cx - ax) * (sy - ay)
        inside = ~(((d1 < 0) | (d2 < 0) | (d3 < 0)) & ((d1 > 0) | (d2 > 0) | (d3 > 0)))
        grid[j0:j1, i0:i1] |= inside
    cov = np.zeros((H, W), np.float32)
    jj, ii = np.nonzero(gate)
    if len(ii) == 0:
        return cov
    pa = PA[jj, ii]
    pb = PB[jj, ii]
    acc = np.zeros(len(ii), np.float32)
    for oa in range(ss):
        for ob_ in range(ss):
            sa = pa + ((oa + 0.5) / ss - 0.5) * (L_UV / W)
            sb = pb + ((ob_ + 0.5) / ss - 0.5) * 0.018
            ci = ((sa - x0) / (x1 - x0) * nx).astype(int)
            cj = ((sb - y0) / (y1 - y0) * ny).astype(int)
            ok = (ci >= 0) & (ci < nx) & (cj >= 0) & (cj < ny)
            hit = np.zeros(len(ii), bool)
            hit[ok] = grid[cj[ok], ci[ok]]
            acc += hit
    cov[jj, ii] = acc / (ss * ss)
    return cov


def composite(cov, color):
    m = cov > 0.003
    a = cov[m][:, None]
    tex[m, :3] = tex[m, :3] * (1 - a) + np.asarray(color)[None, :] * a
    for ch in range(3):
        fac[m, ch] = np.maximum(fac[m, ch], cov[m])
    return int(m.sum())


def islands_of(me):
    import collections
    adj = collections.defaultdict(set)
    for e in me.edges:
        a, b = e.vertices
        adj[a].add(b)
        adj[b].add(a)
    seen, out = set(), []
    for v0 in range(len(me.vertices)):
        if v0 in seen:
            continue
        st, comp = [v0], set()
        while st:
            v = st.pop()
            if v in comp:
                continue
            comp.add(v)
            st.extend(adj[v] - comp)
        seen |= comp
        out.append(comp)
    return out


def split_symbol_letters(ob, cut=9.0):
    """triangles of ob in world (x,z), split into the symbol group and the wordmark"""
    me = ob.data
    me.calc_loop_triangles()
    mw = mathutils.Matrix.LocRotScale(ob.location, ob.rotation_euler, ob.scale)
    vs = [mw @ v.co for v in me.vertices]
    which = {}
    for comp in islands_of(me):
        xs = [vs[i].x for i in comp]
        g = 0 if max(xs) <= cut else 1
        for i in comp:
            which[i] = g
    out = ([], [])
    for t in me.loop_triangles:
        out[which[t.vertices[0]]].append([(vs[i].x, vs[i].z) for i in t.vertices])
    return out


def mirror(tris, axis):
    return [[(2 * axis - x, z) for x, z in t] for t in tris]


# port: the E meshes as they are
for nm, color in (("B789_LogoLATAM_E_Coral", CORAL), ("B789_LogoLATAM_E", INDIGO)):
    tris2 = [[(p.x, p.z) for p in t] for t in tris_of(D.objects[nm])]
    cov = coverage(tris2, Xg, Zg, PORT & FLANK)
    log("lockup repaint port", nm, "->", composite(cov, color), "texels")

# starboard: NOT the D meshes.  The D objects are the whole lockup rotated 180 deg
# about z, which puts the symbol at the TAIL end — and both reference photos
# (CC-BBF stbd, CC-BBB port) show the symbol on the NOSE side on BOTH sides.
# The 787-9's painted texture has it right; its D mesh has the same fault, so the
# -9's paint was evidently not made from that mesh either.
# Correct construction: mirror the symbol about its own centre and the wordmark
# about its own centre, so the symbol keeps its forward station and the letter
# sequence reverses (stbd reads, nose to tail: symbol, M, A, T, A, L).
sym_i, let_i = split_symbol_letters(D.objects["B789_LogoLATAM_E"])
sym_c, let_c = split_symbol_letters(D.objects["B789_LogoLATAM_E_Coral"])
sx = [x for t in sym_i + sym_c for x, _ in t]
lx = [x for t in let_i for x, _ in t]
AX_SYM = 0.5 * (min(sx) + max(sx))
AX_LET = 0.5 * (min(lx) + max(lx))
log("stbd mirror axes: symbol %.3f (x %.2f..%.2f), wordmark %.3f (x %.2f..%.2f)"
    % (AX_SYM, min(sx), max(sx), AX_LET, min(lx), max(lx)))
cov = coverage(mirror(sym_c, AX_SYM), Xg, Zg, STBD & FLANK)
log("lockup repaint stbd symbol coral ->", composite(cov, CORAL), "texels")
cov = coverage(mirror(sym_i, AX_SYM), Xg, Zg, STBD & FLANK)
log("lockup repaint stbd symbol indigo ->", composite(cov, INDIGO), "texels")
cov = coverage(mirror(let_i, AX_LET), Xg, Zg, STBD & FLANK)
log("lockup repaint stbd wordmark ->", composite(cov, INDIGO), "texels")

for nm in ("B789_LogoLATAM_E", "B789_LogoLATAM_E_Coral",
           "B789_LogoLATAM_D", "B789_LogoLATAM_D_Coral"):
    ob = D.objects[nm]
    ob.hide_viewport = True
    ob.hide_render = True

# ---------------------------------------------------------------- 3. write
img_tex.pixels.foreach_set(np.concatenate(
    [tex[..., :3], np.ones((H, W, 1), np.float32)], axis=2).astype(np.float32).ravel())
img_tex.pack()
img_fac.pixels.foreach_set(np.concatenate(
    [fac[..., :1].repeat(3, axis=2), np.ones((H, W, 1), np.float32)], axis=2).astype(np.float32).ravel())
img_fac.pack()
log("LiveryTex/LiveryFac written")

bpy.ops.wm.save_mainfile()
log("SAVED", bpy.data.filepath)
