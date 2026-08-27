"""Re-rasterize the fuselage marks of a master in (x, theta) — the DEVELOPED
surface — instead of the (x, z) side projection.

    blender -b "<aircraft>/<MASTER>.blend" --python refazer_marcas.py -- <tag>

Why this exists (see .claude/skills/livery-latam/SKILL.md, "The paint lives on
the developed surface"): fuselage paint is applied to the skin, so a mark's
proportion is width / ARC, not width / dz.  Measuring or placing it in the side
projection flattens whatever climbs the shoulder — about 25% for the brand
symbol, which spans theta 39..93 deg.  Every Airbus master and the 787-8 had the
lockup pasted as ONE block whose ratio matched the official 4.303 in the (x,z)
projection; on the surface that block reads ~19% too tall, and the split between
symbol and wordmark is wrong as well.

The fleet constants below were measured on four aircraft, three types
(CC-BFO/A320ceo, PS-LBO/A321neo, PT-TMT/A319, CC-BGP/787-9) plus the two
already-correct builds (CC-CWY/767, CC-BBF/787-8).
"""
import bpy, bmesh, math, os, sys
import numpy as np

# ------------------------------------------------------------------ fleet law
RAZAO_SIMBOLO = 0.62230      # official ink bbox ratio, symbol alone
RAZAO_WORDMARK = 6.73080     # official ink bbox ratio, wordmark alone
DIVISAO = 0.260              # symbol width / wordmark width ON THE AIRCRAFT
                             # (print SVG says 0.18458; the aircraft symbol is
                             #  ~1.4x wider relative to the wordmark)
FOLGA = 0.065                # gap symbol->wordmark, as a fraction of wordmark width
SIMBOLO_ACIMA = 0.170        # symbol top above the wordmark cap line, in ARC metres
CORTE_ARTE_X = 1.12          # local x that splits symbol from wordmark in the art

INDIGO = (0x2A, 0x00, 0x88)
CORAL = (0xED, 0x16, 0x51)
TITULO = (0x1C, 0x2E, 0x63)
BRANCO_MARCA = (0xF2, 0xF3, 0xF5)

SS = 3                       # supersampling per texel, per axis


# ------------------------------------------------------------------- hull map
class Casco:
    """(x, theta) <-> texel, plus the true arc length along each section."""

    def __init__(self):
        for o in bpy.data.objects:
            o.hide_viewport = False
        bpy.context.view_layer.update()
        self.ob = bpy.data.objects.get("Fuselagem") or bpy.data.objects["Casco"]
        me = self.ob.data
        uvl = me.uv_layers.active.data
        M = self.ob.matrix_world
        X = []; U = []; T = []; Y = []; Z = []
        for poly in me.polygons:
            for li in poly.loop_indices:
                co = M @ me.vertices[me.loops[li].vertex_index].co
                u, v = uvl[li].uv
                X.append(co.x); U.append(u); Y.append(co.y); Z.append(co.z)
                T.append((v - 0.5) * 2 * math.pi)
        X = np.array(X); U = np.array(U); T = np.array(T)
        Y = np.array(Y); Z = np.array(Z)
        a = np.polyfit(U, X, 1)
        self.L = float(a[0]); self.x0 = float(a[1])
        self.tex = bpy.data.images["LiveryTex"]
        self.fac = bpy.data.images["LiveryFac"]
        self.W, self.H = self.tex.size
        # per-station theta -> cumulative arc from the crown
        self.est = []
        key = np.round(X, 4)
        for k in np.unique(key):
            m = key == k
            if m.sum() < 8:
                continue
            th = T[m]; yy = Y[m]; zz = Z[m]
            o = np.argsort(th); th = th[o]; yy = yy[o]; zz = zz[o]
            keep = np.concatenate([[True], np.diff(th) > 1e-9])
            th = th[keep]; yy = yy[keep]; zz = zz[keep]
            if len(th) < 8:
                continue
            s = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(yy), np.diff(zz)))])
            s -= np.interp(0.0, th, s)
            self.est.append((float(k), th, s, zz))
        self.est.sort(key=lambda t: t[0])
        self.ex = np.array([e[0] for e in self.est])
        # pixels, sRGB byte values / 255, row 0 = v 0
        buf = np.empty(self.W * self.H * 4, np.float32)
        self.tex.pixels.foreach_get(buf)
        self.T4 = buf.reshape(self.H, self.W, 4).copy()
        buf = np.empty(self.W * self.H * 4, np.float32)
        self.fac.pixels.foreach_get(buf)
        self.F4 = buf.reshape(self.H, self.W, 4).copy()

    # --- coordinates -----------------------------------------------------
    def x_of_col(self, c):
        return self.x0 + self.L * (np.asarray(c, float) + 0.5) / self.W

    def col_of_x(self, x):
        return (np.asarray(x, float) - self.x0) / self.L * self.W - 0.5

    def th_of_row(self, r):
        return ((np.asarray(r, float) + 0.5) / self.H - 0.5) * 2 * math.pi

    def row_of_th(self, th):
        return (np.asarray(th, float) / (2 * math.pi) + 0.5) * self.H - 0.5

    def _i(self, x):
        return np.clip(np.searchsorted(self.ex, x), 1, len(self.ex) - 1)

    def arc(self, x, th):
        """arc from the crown, metres, signed like theta. Interpolated in x."""
        x = np.atleast_1d(np.asarray(x, float))
        th = np.atleast_1d(np.asarray(th, float))
        i = self._i(x)
        x1 = self.ex[i]; x0 = self.ex[i - 1]
        w = np.where(x1 > x0, (x - x0) / np.maximum(x1 - x0, 1e-9), 0.0)
        out = np.empty_like(x, float)
        for k in range(len(x)):
            a = np.interp(th[k], self.est[i[k] - 1][1], self.est[i[k] - 1][2])
            b = np.interp(th[k], self.est[i[k]][1], self.est[i[k]][2])
            out[k] = a + (b - a) * w[k]
        return out

    def th_of_arc(self, x, s):
        """inverse of arc(): theta that reaches arc s at station x."""
        x = np.atleast_1d(np.asarray(x, float))
        s = np.atleast_1d(np.asarray(s, float))
        i = self._i(x)
        x1 = self.ex[i]; x0 = self.ex[i - 1]
        w = np.where(x1 > x0, (x - x0) / np.maximum(x1 - x0, 1e-9), 0.0)
        out = np.empty_like(x, float)
        for k in range(len(x)):
            e0 = self.est[i[k] - 1]; e1 = self.est[i[k]]
            a = np.interp(s[k], e0[2], e0[1])
            b = np.interp(s[k], e1[2], e1[1])
            out[k] = a + (b - a) * w[k]
        return out

    def z_of(self, x, th):
        i = int(self._i(np.array([x]))[0])
        return float(np.interp(th, self.est[i][1], self.est[i][3]))

    def z_grid(self, X, T):
        """z of the hull at every (x, theta) sample of a grid."""
        i = self._i(X.ravel())
        out = np.empty(X.size, float)
        th = T.ravel()
        for k in range(X.size):
            e = self.est[i[k]]
            out[k] = np.interp(th[k], e[1], e[3])
        return out.reshape(X.shape)

    # --- painting --------------------------------------------------------
    def _box(self, x0, x1, th_a, th_b):
        c0 = int(math.floor(self.col_of_x(x0))); c1 = int(math.ceil(self.col_of_x(x1)))
        r0 = int(math.floor(self.row_of_th(min(th_a, th_b))))
        r1 = int(math.ceil(self.row_of_th(max(th_a, th_b))))
        return (max(0, c0), min(self.W - 1, c1), max(0, r0), min(self.H - 1, r1))

    def efetiva(self, r0, r1, c0, c1):
        """current colour the shader actually shows: mix(base, Tex, Fac)."""
        base = np.array([0xE6, 0xE7, 0xEA], np.float32) / 255.0
        f = self.F4[r0:r1 + 1, c0:c1 + 1, 0:1]
        return base[None, None, :] * (1 - f) + self.T4[r0:r1 + 1, c0:c1 + 1, :3] * f

    def escrever(self, r0, r1, c0, c1, cor_ef, onde):
        """write an effective colour back as Fac=1 + Tex=colour."""
        sl_t = self.T4[r0:r1 + 1, c0:c1 + 1]
        sl_f = self.F4[r0:r1 + 1, c0:c1 + 1]
        sl_t[..., :3] = np.where(onde[..., None], cor_ef, sl_t[..., :3])
        sl_t[..., 3] = 1.0
        sl_f[..., 0] = np.where(onde, 1.0, sl_f[..., 0])
        sl_f[..., 1] = sl_f[..., 0]; sl_f[..., 2] = sl_f[..., 0]; sl_f[..., 3] = 1.0

    def _basemap(self, r0, r1, c0, c1, base="branco"):
        """The flat paint under a mark. The caller states which side the box is
        on: "branco" (white hull), "indigo" (inside the wedge), or the wedge's
        own forward-boundary rule ("cunha", x0, k) meaning indigo where
        x >= x0 + k*z. Stating it beats guessing — a wrong guess punches white
        letters into the indigo, which is exactly what happened once here.
        """
        bw = np.array([0xE6, 0xE7, 0xEA], np.float32) / 255.0
        bi = np.array(INDIGO, np.float32) / 255.0
        ef = self.efetiva(r0, r1, c0, c1)
        if base == "fronteira":
            # The wedge edge is READ BACK from the paint, not recomputed: rows
            # the mark does not touch give the true boundary, and a quadratic
            # through them carries it across the rows the mark hides. Rebuilding
            # it from the spec's rule instead left a visible step — the painted
            # wedge and the spec's straight line are not the same curve.
            marg = 200
            cA = max(0, c0 - marg); cB = min(self.W - 1, c1 + marg)
            efw = self.efetiva(r0, r1, cA, cB)
            w_ = np.abs(efw - bw).sum(2) < 0.02
            i_ = np.abs(efw - bi).sum(2) < 0.02
            rows = []; cols = []
            for j in range(efw.shape[0]):
                iw = np.where(w_[j])[0]; ii = np.where(i_[j])[0]
                if not len(iw) or not len(ii):
                    continue
                b = ii.min()
                a = iw[iw < b]
                if not len(a):
                    continue
                a = a.max()
                if b - a <= 6:
                    rows.append(j); cols.append(0.5 * (a + b) + cA)
            if len(rows) < 6:
                raise RuntimeError("could not read the wedge boundary back")
            rr = np.array(rows, float); cc = np.array(cols, float)
            for _ in range(2):
                q = np.polyfit(rr, cc, 2)
                res = np.polyval(q, rr) - cc
                keep = np.abs(res) < max(2.0, 2.5 * res.std())
                rr, cc = rr[keep], cc[keep]
                q = np.polyfit(rr, cc, 2)
            jj = np.arange(ef.shape[0])[:, None]
            cols_grid = np.arange(c0, c1 + 1)[None, :]
            lim = np.polyval(q, jj)
            t = np.clip((cols_grid - lim) / 1.6 + 0.5, 0.0, 1.0)[..., None]
            novo = bw[None, None, :] * (1 - t) + bi[None, None, :] * t
            print(f"   [fronteira] read back from the paint on {len(rr)} rows, "
                  f"rms {np.sqrt(np.mean((np.polyval(q, rr) - cc) ** 2)):.2f} px")
            return ef, novo, novo
        cor = bi if base == "indigo" else bw
        novo = np.broadcast_to(cor[None, None, :], ef.shape)
        return ef, novo, cor

    def apagar(self, x0, x1, th_a_deg, th_b_deg, nome="", alvos=None, tol=0.075,
               base="branco"):
        """Restore the flat base over a box, removing a mark and its
        anti-aliasing fringe. `alvos` limits the erase to ink lying on the blend
        line between the base and one of those colours, so windows, door
        outlines and panel lines survive."""
        th_a = math.radians(th_a_deg); th_b = math.radians(th_b_deg)
        c0, c1, r0, r1 = self._box(x0, x1, th_a, th_b)
        ef, novo, cor = self._basemap(r0, r1, c0, c1, base)
        bi = np.array(INDIGO, np.float32) / 255.0
        muda = np.abs(ef - novo).sum(2) > 0.008
        if alvos:
            perto = np.zeros(muda.shape, bool)
            for a in alvos:
                t = np.array(a, np.float32) / 255.0
                d = t[None, None, :] - novo
                dd = (d * d).sum(2)
                w = ((ef - novo) * d).sum(2) / np.maximum(dd, 1e-9)
                proj = novo + d * np.clip(w, 0, 1)[..., None]
                perto |= np.abs(ef - proj).sum(2) < tol
            muda &= perto
        self.escrever(r0, r1, c0, c1, np.broadcast_to(novo, ef.shape), muda)
        print(f"   [apagar]  {nome:24} x {x0:7.3f}..{x1:7.3f}  "
              f"{int(muda.sum()):7d} texels restored")
        return int(muda.sum())

    def pintar(self, tris, bb, x0, x1, s_topo, altura, cor, lado, espelha=False,
               nome="", modo="arco", z_topo=None):
        """Rasterize art onto the DEVELOPED surface. In mode "arco" the art
        occupies a true rectangle in (x, arc) — that is what keeps a mark's
        proportion right on the skin. In mode "z" the baseline is a constant-z
        line (how a registration or a type title actually reads on the
        aircraft) while the HEIGHT is still arc."""
        ax, bx, ay, by = bb
        sx = (x1 - x0) / max(bx - ax, 1e-9)
        xmid = 0.5 * (x0 + x1)
        if modo == "z":
            th_t = float(self.th_of_arc(np.array([xmid]), np.array([s_topo]))[0])
            zt = self.z_of(xmid, th_t) if z_topo is None else z_topo
            th_b_mid = float(self.th_of_arc(np.array([xmid]),
                                            np.array([s_topo + altura]))[0])
            zb = self.z_of(xmid, th_b_mid)
            sv = (zt - zb) / max(by - ay, 1e-9)
            polys = [[((x1 - (X - ax) * sx) if espelha else (x0 + (X - ax) * sx),
                       zb + (Y - ay) * sv) for X, Y in t] for t in tris]
            th_a, th_b = th_t, th_b_mid
        else:
            ss = altura / max(by - ay, 1e-9)
            polys = []
            for t in tris:
                p = []
                for X, Y in t:
                    xm = (x1 - (X - ax) * sx) if espelha else (x0 + (X - ax) * sx)
                    p.append((xm, s_topo + altura - (Y - ay) * ss))
                polys.append(p)
            s0, s1 = s_topo, s_topo + altura
            th_a = float(self.th_of_arc(np.array([x0, x1]), np.array([s0, s0])).min())
            th_b = float(self.th_of_arc(np.array([x0, x1]), np.array([s1, s1])).max())
        if lado < 0:
            th_a, th_b = -th_b, -th_a
        marg = 0.14 if modo == "z" else 0.02
        c0, c1, r0, r1 = self._box(x0 - 0.02, x1 + 0.02,
                                   min(th_a, th_b) - marg, max(th_a, th_b) + marg)
        nc, nr = c1 - c0 + 1, r1 - r0 + 1
        oc = (np.arange(nc * SS) + 0.5) / SS - 0.5
        orr = (np.arange(nr * SS) + 0.5) / SS - 0.5
        XX = self.x_of_col(c0 + oc)[None, :].repeat(nr * SS, 0)
        TT = self.th_of_row(r0 + orr)[:, None].repeat(nc * SS, 1)
        if modo == "z":
            VV = self.z_grid(XX, np.abs(TT))
        else:
            VV = self.arc(XX.ravel(), np.abs(TT).ravel()).reshape(XX.shape)
        lado_ok = (np.sign(TT) == np.sign(lado))
        cov = _raster(polys, XX, VV) & lado_ok
        cov = cov.reshape(nr, SS, nc, SS).mean((1, 3)).astype(np.float32)
        if cov.max() <= 0:
            print(f"   [pintar]  {nome:24} NOTHING painted")
            return 0
        ef = self.efetiva(r0, r1, c0, c1)
        c = np.array(cor, np.float32) / 255.0
        novo = ef * (1 - cov[..., None]) + c[None, None, :] * cov[..., None]
        self.escrever(r0, r1, c0, c1, novo, cov > 0)
        n = int((cov > 0).sum())
        print(f"   [pintar]  {nome:24} x {x0:7.3f}..{x1:7.3f}  "
              f"|th| {math.degrees(min(abs(th_a),abs(th_b))):6.2f}.."
              f"{math.degrees(max(abs(th_a),abs(th_b))):6.2f}  "
              f"arc {altura:5.3f}  ratio {(x1-x0)/altura:6.3f}  {n} texels")
        return n

    def _decompor(self, r0, r1, c0, c1, tinta, base="branco"):
        """Split the current paint into (local flat base, coverage of `tinta`)."""
        ef, out, _ = self._basemap(r0, r1, c0, c1, base)
        t = np.array(tinta, np.float32) / 255.0
        d = t[None, None, :] - out
        dd = (d * d).sum(2)
        a = ((ef - out) * d).sum(2) / np.maximum(dd, 1e-9)
        resid = np.abs(ef - (out + d * np.clip(a, 0, 1)[..., None])).sum(2)
        a = np.where(resid < 0.09, np.clip(a, 0, 1), 0.0)
        return out, a.astype(np.float32)

    def transladar(self, x0, x1, th_a, th_b, dcol, tinta, nome=""):
        """Move already-rasterized ink by a WHOLE number of texture columns —
        an exact copy, no resampling loss — and restore the base behind it."""
        c0, c1, r0, r1 = self._box(x0, x1, math.radians(th_a), math.radians(th_b))
        base_s, a = self._decompor(r0, r1, c0, c1, tinta)
        self.apagar(x0, x1, th_a, th_b, nome=nome + " (origem)", alvos=[tinta],
                    base="branco")
        d0, d1 = c0 + dcol, c1 + dcol
        base_d = self.efetiva(r0, r1, d0, d1)
        t = np.array(tinta, np.float32) / 255.0
        novo = base_d * (1 - a[..., None]) + t[None, None, :] * a[..., None]
        self.escrever(r0, r1, d0, d1, novo, a > 0)
        print(f"   [mover]   {nome:24} {dcol:+d} cols "
              f"({dcol * self.L / self.W:+.3f} m)  {int((a > 0).sum())} texels")

    def espelhar_faixa(self, x0, x1, th_a, th_b, tinta, nome=""):
        """Copy a band of ink from port to starboard at the same |theta|.
        Used to repair a damaged side from the intact one."""
        c0, c1, r0, r1 = self._box(x0, x1, math.radians(-abs(th_b)),
                                   math.radians(-abs(th_a)))
        base_s, a = self._decompor(r0, r1, c0, c1, tinta)
        d0, d1, q0, q1 = self._box(x0, x1, math.radians(abs(th_a)),
                                   math.radians(abs(th_b)))
        a2 = a[::-1]                      # port rows run the other way in theta
        n = min(q1 - q0 + 1, a2.shape[0])
        a2 = a2[:n]
        base_d = self.efetiva(q0, q0 + n - 1, d0, d0 + a2.shape[1] - 1)
        t = np.array(tinta, np.float32) / 255.0
        novo = base_d * (1 - a2[..., None]) + t[None, None, :] * a2[..., None]
        self.escrever(q0, q0 + n - 1, d0, d0 + a2.shape[1] - 1, novo, a2 > 0)
        print(f"   [espelhar]{nome:24} port -> stbd  {int((a2 > 0).sum())} texels")

    def salvar(self):
        for im, arr in ((self.tex, self.T4), (self.fac, self.F4)):
            im.pixels.foreach_set(arr.ravel())
            im.update()
            if im.packed_file:
                im.pack()
        print("   [salvar] LiveryTex + LiveryFac updated")


def _raster(polys, XX, SS_):
    """point-in-triangle over a (possibly non-uniform) sample grid."""
    out = np.zeros(XX.shape, bool)
    P = np.asarray(polys, np.float64)
    xmin, xmax = XX[0].min(), XX[0].max()
    smin, smax = SS_.min(), SS_.max()
    for k in range(P.shape[0]):
        a, b, c = P[k]
        if (max(a[0], b[0], c[0]) < xmin or min(a[0], b[0], c[0]) > xmax or
                max(a[1], b[1], c[1]) < smin or min(a[1], b[1], c[1]) > smax):
            continue
        j0 = int(np.searchsorted(XX[0], min(a[0], b[0], c[0])) - 1)
        j1 = int(np.searchsorted(XX[0], max(a[0], b[0], c[0])) + 1)
        j0 = max(0, j0); j1 = min(XX.shape[1], j1)
        if j1 <= j0:
            continue
        x = XX[:, j0:j1]; s = SS_[:, j0:j1]
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-12:
            continue
        l1 = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (s - c[1])) / d
        l2 = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (s - c[1])) / d
        out[:, j0:j1] |= (l1 >= -1e-9) & (l2 >= -1e-9) & (l1 + l2 <= 1 + 1e-9)
    return out


# --------------------------------------------------------------------- art
def tris_xy(nome, eixo=("x", "y")):
    """Triangles of a rasterization-source mesh, projected onto its own flat
    art plane (LOCAL coordinates — the object transform is not art)."""
    ob = bpy.data.objects.get(nome)
    if ob is None:
        return [], None
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    idx = {"x": 0, "y": 1, "z": 2}
    i, j = idx[eixo[0]], idx[eixo[1]]
    tris = [[(v.co[i], v.co[j]) for v in f.verts] for f in bm.faces]
    bm.free()
    if not tris:
        return [], None
    a = np.asarray(tris)
    return tris, (a[..., 0].min(), a[..., 0].max(), a[..., 1].min(), a[..., 1].max())


def bb_de(*conjuntos):
    a = np.concatenate([np.asarray(t) for t in conjuntos if len(t)])
    return (a[..., 0].min(), a[..., 0].max(), a[..., 1].min(), a[..., 1].max())


def texto_tris(txt, negrito=True):
    cu = bpy.data.curves.new(type="FONT", name="_txt")
    cu.body = txt
    ob = bpy.data.objects.new("_txt", cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.triangulate(bm, faces=bm.faces[:])
    tris = [[(v.co.x, v.co.y) for v in f.verts] for f in bm.faces]
    bm.free()
    bpy.data.meshes.remove(me); bpy.data.objects.remove(ob); bpy.data.curves.remove(cu)
    a = np.asarray(tris)
    return tris, (a[..., 0].min(), a[..., 0].max(), a[..., 1].min(), a[..., 1].max())


# ------------------------------------------------------------- the fleet
# wm_x  : wordmark ink box in x, metres (measured on the type's own photos)
# th_cap: theta of the wordmark cap line, degrees from the crown
# arte  : (indigo mesh, coral mesh) of the official lockup
A_FAMILIA = dict(wm_x=(7.680, 12.440), th_cap=43.1,
                 arte=("LogoLATAM_E", "LogoLATAM_E_Coral"),
                 apagar_lockup=(5.62, 16.45, 15.0, 105.0))
FROTA = {
    "a319":    dict(A_FAMILIA),
    "a320ceo": dict(A_FAMILIA),
    "a320neo": dict(A_FAMILIA),
    "a321ceo": dict(A_FAMILIA),
    "a321neo": dict(A_FAMILIA),
    "b789":    dict(wm_x=(9.480, 16.549), th_cap=43.07,
                    arte=("B789_LogoLATAM_E", "B789_LogoLATAM_E_Coral"),
                    apagar_lockup=(7.05, 16.75, 18.0, 69.5)),
}


def fazer_lockup(cs, cfg):
    """Symbol and wordmark placed SEPARATELY, each at its own official ratio,
    on the developed surface. The symbol sits nose-side on BOTH sides."""
    ind_nome, cor_nome = cfg["arte"]
    tri_all, _ = tris_xy(ind_nome)
    tri_cor, _ = tris_xy(cor_nome)
    if not tri_all or not tri_cor:
        raise SystemExit(f"lockup art not found: {ind_nome}/{cor_nome}")
    tri_sim = [t for t in tri_all if max(p[0] for p in t) <= CORTE_ARTE_X]
    tri_wm = [t for t in tri_all if min(p[0] for p in t) >= CORTE_ARTE_X]
    bb_s = bb_de(tri_sim, tri_cor)
    bb_w = bb_de(tri_wm)
    rs = (bb_s[1] - bb_s[0]) / (bb_s[3] - bb_s[2])
    rw = (bb_w[1] - bb_w[0]) / (bb_w[3] - bb_w[2])
    print(f"   art ratios: symbol {rs:.5f} (law {RAZAO_SIMBOLO}), "
          f"wordmark {rw:.5f} (law {RAZAO_WORDMARK})")

    wx0, wx1 = cfg["wm_x"]
    Wm = wx1 - wx0
    S = DIVISAO * Wm
    G = FOLGA * Wm
    sx1 = wx0 - G
    sx0 = sx1 - S
    alt_wm = Wm / rw
    alt_sim = S / rs
    xm_w = 0.5 * (wx0 + wx1)
    s_cap = float(cs.arc(np.array([xm_w]), np.array([math.radians(cfg["th_cap"])]))[0])
    s_sim = s_cap - SIMBOLO_ACIMA
    print(f"   wordmark {wx0:.3f}..{wx1:.3f} ({Wm:.3f} m)  arc {alt_wm:.3f} m  "
          f"cap arc {s_cap:.3f}")
    print(f"   symbol   {sx0:.3f}..{sx1:.3f} ({S:.3f} m)  arc {alt_sim:.3f} m  "
          f"top arc {s_sim:.3f}  gap {G:.3f}")

    ax0, ax1, ta, tb = cfg["apagar_lockup"]
    for lado in (-1, 1):
        cs.apagar(ax0, ax1, lado * ta, lado * tb,
                  nome=f"lockup {'port' if lado < 0 else 'stbd'}",
                  alvos=[INDIGO, CORAL], base="branco")
    for lado, esp in ((-1, False), (1, True)):
        tag = "port" if lado < 0 else "stbd"
        cs.pintar(tri_sim, bb_s, sx0, sx1, s_sim, alt_sim, INDIGO, lado, esp,
                  nome=f"symbol indigo {tag}")
        cs.pintar(tri_cor, bb_s, sx0, sx1, s_sim, alt_sim, CORAL, lado, esp,
                  nome=f"symbol coral {tag}")
        cs.pintar(tri_wm, bb_w, wx0, wx1, s_cap, alt_wm, INDIGO, lado, esp,
                  nome=f"wordmark {tag}")
    return dict(simbolo_x=[round(sx0, 3), round(sx1, 3)],
                simbolo_arco=round(alt_sim, 4),
                wordmark_x=[round(wx0, 3), round(wx1, 3)],
                wordmark_arco=round(alt_wm, 4),
                folga=round(G, 3), divisao=DIVISAO,
                theta_cap=cfg["th_cap"])



# ---------------------------------------------------------- the other marks
# Every entry is measured; see spec_*.json -> marcas_2026-08-20 for the source.
MARCAS = {
    "a319": [
        dict(op="apagar", x=(5.62, 6.125), th=(35, 62), base="branco",
             nome="fio do simbolo antigo"),
        # type title: the source art no longer exists in the blend (only
        # "AIRBUS A3" survived; the wedge was painted over the rest), so it is
        # left alone and reported instead of being moved half-complete.
        #
        # NOTE 2026-08-22: the A319's `Reg_E` mesh does NOT hold PT-TMT — it
        # still holds the master A320neo's PT-TMN, which is why the registration
        # cannot be repainted from art here. The 2026-08-22 wedge round moves the
        # painted glyphs instead; see `airbus A319/fix_matricula_a319.py`.
    ],
    "a320ceo": [
        dict(op="apagar", x=(5.62, 6.125), th=(35, 62), base="branco",
             nome="fio do simbolo antigo"),
    ],
    "a320neo": [
        dict(op="apagar", x=(5.62, 6.125), th=(35, 62), base="branco",
             nome="fio do simbolo antigo"),
        # the old title straddles the wedge edge, so the erase is given the
        # wedge's own forward-boundary rule (spec_a320.json -> echarpe_casco)
        dict(op="apagar", x=(26.80, 29.15), th=(36, 58),
             base="fronteira", nome="titulo antigo"),
        dict(op="pintar", malha="MarkAirbusNeo_E",
             plano=("x", "y"), x=(26.42, 28.72), th_topo=43.1, cor=TITULO,
             nome="titulo AIRBUS A320neo"),
        # The starboard registration left by the FIRST run of this file was
        # mirrored twice (see the note in `fazer_marcas`) and read 'NMT-TP'.
        # Erase before repainting, on BOTH sides so the new ink lands on clean
        # paint. Box measured on the texture itself: the white ink spans
        # x 30.137..31.752, theta 56.4..71.9, and the box below is 68% indigo,
        # 0.1% white hull -- so "indigo" is the base to restore, not "branco".
        dict(op="apagar", x=(30.05, 31.85), th=(54, 74), base="indigo",
             alvos=[BRANCO_MARCA], nome="matricula anterior"),
        dict(op="pintar", malha="Reg_E", plano=("x", "z"),
             x=(30.14, 31.76), th_topo=57.0, cor=BRANCO_MARCA,
             nome="matricula PT-TMN"),
    ],
    "a321ceo": [
        dict(op="apagar", x=(5.62, 6.125), th=(35, 62), base="branco",
             nome="fio do simbolo antigo"),
        dict(op="apagar", x=(33.90, 35.30), th=(39, 47), base="branco",
             alvos=[TITULO], nome="fantasma AIRBUS A320neo"),
    ],
    "a321neo": [
        dict(op="apagar", x=(5.62, 6.125), th=(35, 62), base="branco",
             nome="fio do simbolo antigo"),
        dict(op="apagar", x=(33.90, 35.30), th=(39, 47), base="branco",
             alvos=[TITULO], nome="fantasma AIRBUS A320neo"),
    ],
    "b789": [
        dict(op="apagar", x=(6.95, 7.18), th=(40, 67), base="branco",
             nome="fio do simbolo antigo"),
        dict(op="apagar", x=(54.10, 57.20), th=(92, 109), base="branco",
             alvos=[INDIGO], nome="matricula fantasma"),
        dict(op="apagar", x=(43.90, 48.40), th=(79, 88), base="branco",
             alvos=[(0xB7, 0xBC, 0xC1)], nome="fantasma DREAMLINER"),
        dict(op="pintar", malha="Reg787_E", plano=("x", "y"),
             # photo (CC-BGP) puts it 0.85..2.62 m aft of door 4 = x 50.51..52.28;
             # nudged 0.35 m aft so it clears the MODEL's wedge edge (x 50.76 at
             # theta 62), whose forward boundary sits slightly aft of the real one
             x=(50.86, 52.63), th_topo=62.5, cor=BRANCO_MARCA,
             nome="matricula CC-BGK"),
        dict(op="espelhar", x=(6.80, 48.20), th=(64, 84), tinta=(0x0E, 0x11, 0x13),
             nome="fileira de janelas"),
    ],
}


def fazer_marcas(cs, tag):
    for m in MARCAS.get(tag, []):
        if m["op"] == "apagar":
            for lado in (-1, 1):
                cs.apagar(m["x"][0], m["x"][1], lado * m["th"][0], lado * m["th"][1],
                          nome=f"{m['nome']} {'port' if lado < 0 else 'stbd'}",
                          alvos=m.get("alvos"), base=m.get("base", "auto"))
        elif m["op"] == "espelhar":
            cs.espelhar_faixa(m["x"][0], m["x"][1], m["th"][0], m["th"][1],
                              m["tinta"], nome=m["nome"])
        elif m["op"] == "pintar":
            # ONE art source for both flanks; the flank decides the mirror.
            # This used to read a mesh PER SIDE -- ("Reg_E", "Reg_D") -- and
            # still pass espelha=(lado > 0), which silently assumes the two
            # meshes hold the SAME artwork. They do not: on the A319 and the
            # A320neo, Reg_D is a separate datablock that is ALREADY the
            # x-mirror of Reg_E (rasterized and compared: 0.9% disagreement
            # mirrored against 93% straight). Mirroring it again put the
            # A320neo's registration back to front on the starboard side, where
            # it read 'NMT-TP'; the A319 escaped only because its registration
            # is painted by build_a319_livery.py and never came through here.
            # The marks that came out right -- MarkAirbusNeo and Reg787 -- are
            # exactly the ones whose _D object SHARES the _E mesh datablock, so
            # they were only mirrored once, and that coincidence hid the fault.
            # Stating the art once removes the question.
            tris, bb = tris_xy(m["malha"], m["plano"])
            if not tris:
                print(f"   [pintar]  {m['nome']}: mesh {m['malha']} missing"); continue
            razao = (bb[1] - bb[0]) / (bb[3] - bb[2])
            larg = m["x"][1] - m["x"][0]
            alt = m.get("altura") or larg / razao
            xm = 0.5 * (m["x"][0] + m["x"][1])
            s_topo = float(cs.arc(np.array([xm]),
                                  np.array([math.radians(m["th_topo"])]))[0])
            for lado in (-1, 1):
                cs.pintar(tris, bb, m["x"][0], m["x"][1], s_topo, alt, m["cor"],
                          lado, espelha=(lado > 0), modo=m.get("modo", "z"),
                          nome=f"{m['nome']} {'port' if lado < 0 else 'stbd'}")


# ============================================================ legado 767 / 777
# CONSOLIDACAO DO PINTOR UNICO (2026-08-27, QA-BACKLOG "The wedge rasterizer is
# shared now; the eleven builders are not"): os builders Boeing agora pintam so
# livery plana, e as marcas deles moram AQUI — rasterizador e constantes
# movidos TEXTUALMENTE de:
#     boeing 767-300ER/b5_livery.py   secoes 5-7   (CC-CWY)
#     boeing 767-300F/b5f_livery.py   secoes 5-7   (N536LA)
#     boeing 767-300BCF/b5b_livery.py secoes 5-7   (CC-CXE)
#     boeing 777-300ER/build_77w_fase2_livery.py secoes 5-7 (PT-MUG)
#
# A PONTE z(x, theta) destas marcas e o zc_rz() DO PROPRIO BUILDER (tabelas do
# spec, com a emenda em x = 41.0 e tudo): as marcas foram AUTORADAS nela, e
# troca-la pela ponte da malha as moveria ate ~1 grau de theta — mover marca e
# rodada de textura com gate, nao de encanamento. A cunha, essa sim, saiu da
# ponte emendada (ver os builders e reparar_echarpe).
#
# O rasterizador e o dos builders, BINARIO e uint8, de proposito: reproduz a
# textura embarcada byte a byte. Reaplicar a mesma marca no mesmo lugar e
# idempotente; se um dia uma marca MUDAR de lugar, apague a antiga com
# Casco.apagar (base declarada) antes de pintar a nova.
import json


class CascoLegado:
    """Grades (x, theta, z) e leitura uint8 da LiveryTex, como nos builders."""

    def __init__(self, spec_rel, luv, ponte):
        import os as _os
        raiz = _os.path.dirname(_os.path.abspath(__file__))
        spec = json.load(open(_os.path.join(raiz, spec_rel)))
        self.spec = spec
        self.LUV = luv
        imT = bpy.data.images["LiveryTex"]
        imF = bpy.data.images["LiveryFac"]
        self.imT, self.imF = imT, imF
        W, H = imT.size
        self.W, self.H = W, H
        nose = spec["nariz_estacoes"]
        self._nx = np.array([s[0] for s in nose])
        self._nc = np.array([s[1] for s in nose])
        self._nk = np.array([s[2] for s in nose])
        if ponte == "b763":
            tail = spec["cauda_estacoes"]
            self._tx = np.array([s[0] for s in tail])
            self._tzc = np.array([s[1] for s in tail])
            self._trz = np.array([s[2] for s in tail])

            def zc_rz(x):           # b5_livery.py, verbatim
                x = np.asarray(x, float)
                zc = np.zeros_like(x)
                rz = np.full_like(x, 2.705)
                m = x <= 7.5
                if m.any():
                    c = np.interp(x[m], self._nx, self._nc)
                    k = np.interp(x[m], self._nx, self._nk)
                    zc[m] = (c + k) / 2.0
                    rz[m] = (c - k) / 2.0
                m = x >= 41.0
                if m.any():
                    zc[m] = np.interp(x[m], self._tx, self._tzc)
                    rz[m] = np.interp(x[m], self._tx, self._trz)
                return zc, rz
        else:                        # "b77w": build_77w_fase2_livery.py, verbatim
            self._nw = np.array([s[3] for s in nose])
            tail = spec["cauda"]
            self._tx = np.array([s[0] for s in tail])
            self._tzc = np.array([s[1] for s in tail])
            self._trz = np.array([s[2] for s in tail])
            XC0, XC1 = spec["secao_constante_x"]

            def zc_rz(x):
                x = np.asarray(x, float)
                zc = np.zeros_like(x)
                rz = np.full_like(x, 3.10)
                m = x <= XC0
                if m.any():
                    c = np.interp(x[m], self._nx, self._nc)
                    k = np.interp(x[m], self._nx, self._nk)
                    zc[m] = (c + k) / 2.0
                    rz[m] = (c - k) / 2.0
                m = x >= XC1
                if m.any():
                    zc[m] = np.interp(x[m], self._tx, self._tzc)
                    rz[m] = np.interp(x[m], self._tx, self._trz)
                return zc, rz
        self.zc_rz = zc_rz
        uu = (np.arange(W) + 0.5) / W
        vv = (np.arange(H) + 0.5) / H
        UX = uu * luv
        VT = vv * 2 * math.pi - math.pi
        self.GX = np.repeat(UX[None, :], H, axis=0)
        GT = np.repeat(VT[:, None], W, axis=1)
        _zc, _rz = zc_rz(UX)
        self.GZ = _zc[None, :] + _rz[None, :] * np.cos(GT)
        self.GABS = np.abs(GT)
        self.LADO = np.where(GT < 0, -1, 1)
        buf = np.empty(W * H * 4, np.float32)
        imT.pixels.foreach_get(buf)
        self._t4 = buf.reshape(H, W, 4)
        self.tex = np.round(self._t4[..., :3] * 255.0).astype(np.uint8)
        buf = np.empty(W * H * 4, np.float32)
        imF.pixels.foreach_get(buf)
        self._f4 = buf.reshape(H, W, 4)
        self.pintado = np.zeros((H, W), bool)

    # --- rasterizador dos builders (fill_tris/leque/marca/marca_th), verbatim
    def fill_tris(self, tris, x0, x1, z0, z1, nx, nz):
        out = np.zeros((nz, nx), bool)
        if not tris:
            return out
        sx = (x1 - x0) / nx
        sz = (z1 - z0) / nz
        T = np.asarray(tris, np.float64)
        P = np.empty_like(T)
        P[..., 0] = (T[..., 0] - x0) / sx - 0.5
        P[..., 1] = (T[..., 1] - z0) / sz - 0.5
        for k in range(P.shape[0]):
            a, b, c = P[k]
            i0 = max(0, int(math.floor(min(a[0], b[0], c[0]))))
            i1 = min(nx - 1, int(math.ceil(max(a[0], b[0], c[0]))))
            j0 = max(0, int(math.floor(min(a[1], b[1], c[1]))))
            j1 = min(nz - 1, int(math.ceil(max(a[1], b[1], c[1]))))
            if i1 < i0 or j1 < j0:
                continue
            d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
            if abs(d) < 1e-12:
                continue
            ii = np.arange(i0, i1 + 1)[None, :]
            jj = np.arange(j0, j1 + 1)[:, None]
            l1 = ((b[1] - c[1]) * (ii - c[0]) + (c[0] - b[0]) * (jj - c[1])) / d
            l2 = ((c[1] - a[1]) * (ii - c[0]) + (a[0] - c[0]) * (jj - c[1])) / d
            l3 = 1.0 - l1 - l2
            m = (l1 >= -1e-9) & (l2 >= -1e-9) & (l3 >= -1e-9)
            out[j0:j1 + 1, i0:i1 + 1] |= m
        return out

    @staticmethod
    def leque(poly):
        return [[poly[0], poly[i], poly[i + 1]] for i in range(1, len(poly) - 1)]

    def marca(self, tris, x0, x1, z0, z1, cor, lado, ppm=460):
        nx = max(8, int(round((x1 - x0) * ppm)))
        nz = max(8, int(round((z1 - z0) * ppm)))
        arr = self.fill_tris(tris, x0, x1, z0, z1, nx, nz)
        if not arr.any():
            return 0
        sel = (self.GX >= x0) & (self.GX <= x1) & (self.GZ >= z0) & (self.GZ <= z1)
        if lado:
            sel &= (self.LADO == lado)
        if not sel.any():
            return 0
        ix = np.clip(((self.GX[sel] - x0) / (x1 - x0) * nx).astype(int), 0, nx - 1)
        jz = np.clip(((self.GZ[sel] - z0) / (z1 - z0) * nz).astype(int), 0, nz - 1)
        hit = arr[jz, ix]
        r, c = np.where(sel)
        r, c = r[hit], c[hit]
        self.tex[r, c] = cor
        self.pintado[r, c] = True
        return int(hit.sum())

    def marca_th(self, tris, bb, x0, x1, th_topo, th_base, cor, lado,
                 espelha=False, ppm=460, raio=2.50):
        """b5: raio 2.50 (767); build_77w: raio 3.10 (777)."""
        ax, bx, ay, by = bb
        sx = (x1 - x0) / max(bx - ax, 1e-9)
        st = (th_base - th_topo) / max(by - ay, 1e-9)
        polys = []
        for t in tris:
            p = []
            for X, Y in t:
                xm = (x1 - (X - ax) * sx) if espelha else (x0 + (X - ax) * sx)
                p.append((xm, th_base - (Y - ay) * st))
            polys.append(p)
        nx = max(8, int(round((x1 - x0) * ppm)))
        nt = max(8, int(round(math.radians(th_base - th_topo) * raio * ppm)))
        arr = self.fill_tris(polys, x0, x1, th_topo, th_base, nx, nt)
        if not arr.any():
            return 0
        GD = np.degrees(self.GABS)
        sel = (self.GX >= x0) & (self.GX <= x1) & (GD >= th_topo) & (GD <= th_base)
        if lado:
            sel &= (self.LADO == lado)
        if not sel.any():
            return 0
        ix = np.clip(((self.GX[sel] - x0) / (x1 - x0) * nx).astype(int), 0, nx - 1)
        jt = np.clip(((GD[sel] - th_topo) / (th_base - th_topo) * nt).astype(int),
                     0, nt - 1)
        hit = arr[jt, ix]
        r, c = np.where(sel)
        self.tex[r[hit], c[hit]] = cor
        self.pintado[r[hit], c[hit]] = True
        return int(hit.sum())

    def tris_do_objeto(self, nome):
        ob = bpy.data.objects.get(nome)
        if ob is None:
            return [], None
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        tris = [[(v.co.x, v.co.y) for v in f.verts] for f in bm.faces]
        bm.free()
        if not tris:
            return [], None
        a = np.asarray(tris)
        return tris, (a[..., 0].min(), a[..., 0].max(),
                      a[..., 1].min(), a[..., 1].max())

    def texto_tris_b(self, txt):
        """texto_tris() dos builders Boeing: fonte padrao do Blender."""
        cu = bpy.data.curves.new(type="FONT", name="_tmp_txt")
        cu.body = txt
        ob = bpy.data.objects.new("_tmp_txt", cu)
        bpy.context.scene.collection.objects.link(ob)
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        tris = [[(v.co.x, v.co.y) for v in f.verts] for f in bm.faces]
        bm.free()
        bpy.data.meshes.remove(me)
        bpy.data.objects.remove(ob)
        bpy.data.curves.remove(cu)
        a = np.asarray(tris)
        return tris, (a[..., 0].min(), a[..., 0].max(),
                      a[..., 1].min(), a[..., 1].max())

    @staticmethod
    def encaixa(tris, bb, x0, x1, z0, z1, espelha=False, cis=0.0):
        ax, bx, ay, by = bb
        sx = (x1 - x0) / max(bx - ax, 1e-9)
        sz = (z1 - z0) / max(by - ay, 1e-9)
        out = []
        for t in tris:
            p = []
            for X, Y in t:
                Xc = X + cis * (Y - ay)
                xm = (x1 - (Xc - ax) * sx) if espelha else (x0 + (Xc - ax) * sx)
                p.append((xm, z0 + (Y - ay) * sz))
            out.append(p)
        return out

    def resuja(self, caixas):
        """Reaplica o desgaste dos builders SO sobre a tinta pintada aqui.
        O builder aplica as mesmas caixas sobre a base; a ordem original
        (marca antes, sujeira por cima) fica preservada texel a texel."""
        for x0, x1, t0, t1, cor, inten in caixas:
            m = ((self.GX >= x0) & (self.GX <= x1) &
                 (self.GABS >= math.radians(t0)) &
                 (self.GABS <= math.radians(t1)) & self.pintado)
            if m.any():
                self.tex[m] = (self.tex[m] * (1 - inten) +
                               np.array(cor) * inten).astype(np.uint8)

    def salvar(self):
        self._t4[..., :3] = self.tex.astype(np.float32) / 255.0
        self._t4[..., 3] = 1.0
        f = self._f4
        f[..., 0][self.pintado] = 1.0
        f[..., 1][self.pintado] = 1.0
        f[..., 2][self.pintado] = 1.0
        self.imT.pixels.foreach_set(self._t4.ravel())
        self.imT.update()
        self.imF.pixels.foreach_set(f.ravel())
        self.imF.update()
        for im in (self.imT, self.imF):
            if im.packed_file:
                im.pack()
        print("   [salvar] LiveryTex + LiveryFac atualizadas "
              f"({int(self.pintado.sum())} texels de marca)")


SUJA_763 = [(5.2, 12.5, 156, 180, (0x9A, 0x93, 0x88), 0.09),
            (12.5, 17.5, 150, 172, (0xA8, 0xA2, 0x99), 0.05),
            (27.5, 34.0, 150, 180, (0x9E, 0x98, 0x8E), 0.07)]
BRANCO_763 = (0xF2, 0xF3, 0xF5)


def _marcas_b763er(cl):
    """boeing 767-300ER/b5_livery.py secoes 5-7, verbatim (CC-CWY)."""
    tri_all, bb_all = cl.tris_do_objeto("B789_LogoLATAM_E")
    tri_c, bb_c = cl.tris_do_objeto("B789_LogoLATAM_E_Coral")
    if not tri_all or not tri_c:
        raise SystemExit("[logo] malhas do lockup nao encontradas")
    tri_sim = [t for t in tri_all if max(p[0] for p in t) < 1.10]
    tri_wm = [t for t in tri_all if min(p[0] for p in t) >= 1.10]
    a = np.asarray(tri_sim + tri_c)
    bb_s = (a[..., 0].min(), a[..., 0].max(), a[..., 1].min(), a[..., 1].max())
    a = np.asarray(tri_wm)
    bb_w = (a[..., 0].min(), a[..., 0].max(), a[..., 1].min(), a[..., 1].max())
    rs = (bb_s[1] - bb_s[0]) / (bb_s[3] - bb_s[2])
    rw = (bb_w[1] - bb_w[0]) / (bb_w[3] - bb_w[2])
    # medido em CC-CWY (bombordo, 2026-08-20):
    SX0, SX1, S_TH = 6.98, 8.68, 34.26
    WX0, WX1, W_TH = 9.15, 15.80, 37.21
    S_TB = S_TH + math.degrees((SX1 - SX0) / rs / 2.50)
    W_TB = W_TH + math.degrees((WX1 - WX0) / rw / 2.50)
    print(f"   [logo] simbolo {rs:.3f} th {S_TH:.1f}..{S_TB:.1f} | "
          f"wordmark {rw:.3f} th {W_TH:.1f}..{W_TB:.1f}")
    INDIGO_T, CORAL_T = tuple(INDIGO), tuple(CORAL)
    for lado, esp in ((-1, False), (1, True)):
        cl.marca_th(tri_sim, bb_s, SX0, SX1, S_TH, S_TB, INDIGO_T, lado, esp)
        cl.marca_th(tri_c, bb_s, SX0, SX1, S_TH, S_TB, CORAL_T, lado, esp)
        cl.marca_th(tri_wm, bb_w, WX0, WX1, W_TH, W_TB, INDIGO_T, lado, esp)
    # matricula BRANCA dentro do indigo: x 44.12..45.92, z 1.044..1.343
    tr, bbr = cl.texto_tris_b("CC-CWY")
    for lado, esp in ((-1, False), (1, True)):
        cl.marca(cl.encaixa(tr, bbr, 44.12, 45.92, 1.044, 1.343, espelha=esp),
                 44.12, 45.92, 1.044, 1.343, BRANCO_763, lado, ppm=760)
    # titulo de tipo, obliquo: x 37.41..40.68, z 1.083..1.269
    tt, bbt = cl.texto_tris_b("BOEING 767-300ER")
    for lado, esp in ((-1, False), (1, True)):
        cl.marca(cl.encaixa(tt, bbt, 37.41, 40.68, 1.083, 1.269, espelha=esp,
                            cis=0.20),
                 37.41, 40.68, 1.083, 1.269, TITULO, lado, ppm=760)
    # barriga: wordmark x 24..31 + simbolo, arco lateral raio 2.466
    lat = (np.pi - cl.GABS) * 2.466 * cl.LADO
    BX0, BX1 = 24.0, 31.0
    BH = (BX1 - BX0) / rw
    nx, nz = int((BX1 - BX0) * 300), max(8, int(BH * 300))
    arr = cl.fill_tris(cl.encaixa(tri_wm, bb_w, BX0, BX1, -BH / 2, BH / 2),
                       BX0, BX1, -BH / 2, BH / 2, nx, nz)
    SBH = BH * 2.0
    SBX1 = BX0 - 0.45
    SBX0 = SBX1 - SBH * rs
    nsx, nsz = max(8, int((SBX1 - SBX0) * 300)), max(8, int(SBH * 300))
    arrS = cl.fill_tris(cl.encaixa(tri_sim, bb_s, SBX0, SBX1, -SBH / 2, SBH / 2),
                        SBX0, SBX1, -SBH / 2, SBH / 2, nsx, nsz)
    arrC = cl.fill_tris(cl.encaixa(tri_c, bb_s, SBX0, SBX1, -SBH / 2, SBH / 2),
                        SBX0, SBX1, -SBH / 2, SBH / 2, nsx, nsz)
    for (a0, X0b, X1b, Hb, nX, nZ, cor) in (
            (arr, BX0, BX1, BH, nx, nz, INDIGO_T),
            (arrS, SBX0, SBX1, SBH, nsx, nsz, INDIGO_T),
            (arrC, SBX0, SBX1, SBH, nsx, nsz, CORAL_T)):
        sel = (cl.GX >= X0b) & (cl.GX <= X1b) & (np.abs(lat) <= Hb / 2)
        if not sel.any():
            continue
        ix = np.clip(((cl.GX[sel] - X0b) / (X1b - X0b) * nX).astype(int),
                     0, nX - 1)
        jz = np.clip(((lat[sel] + Hb / 2) / Hb * nZ).astype(int), 0, nZ - 1)
        r, c = np.where(sel)
        h = a0[jz, ix]
        cl.tex[r[h], c[h]] = cor
        cl.pintado[r[h], c[h]] = True
    cl.resuja(SUJA_763)


def _marcas_carga(cl, spec_key, bandeira, texto_pais):
    """b5f_livery.py / b5b_livery.py secoes 5-7, verbatim.
    bandeira: "colombia" (N536LA) ou "chile" (CC-CXE)."""
    INDIGO_T, CORAL_T = tuple(INDIGO), tuple(CORAL)
    RU_S, CU_S = 2.521, 0.191
    RL_S, CL_S = 2.5075, -0.1985

    def _hw_sec(z):
        if z >= CU_S:
            h = RU_S * RU_S - (z - CU_S) ** 2
        elif z <= CL_S:
            h = RL_S * RL_S - (z - CL_S) ** 2
        else:
            return 2.515
        return math.sqrt(h) if h > 0 else 0.0

    def _arco(z0, z1, n=2001):
        zs = np.linspace(z0, z1, n)
        ys = np.array([_hw_sec(z) for z in zs])
        return float(np.sum(np.hypot(np.diff(ys), np.diff(zs))))

    def theta_base(th_topo_g, arco_alvo):
        z_t = 2.705 * math.cos(math.radians(th_topo_g))
        lo, hi = th_topo_g, 179.0
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            z_m = 2.705 * math.cos(math.radians(mid))
            if _arco(z_m, z_t) < arco_alvo:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    tri_si, bb_si = cl.tris_do_objeto("CargoLockup_Simbolo_Indigo")
    tri_sc, bb_sc = cl.tris_do_objeto("CargoLockup_Simbolo_Coral")
    tri_tx, bb_tx = cl.tris_do_objeto("CargoLockup_Texto")
    if not (tri_si and tri_sc and tri_tx):
        raise SystemExit("[logo] malhas do lockup CARGO nao encontradas")
    a = np.asarray(tri_si + tri_sc)
    bb_s = (a[..., 0].min(), a[..., 0].max(), a[..., 1].min(), a[..., 1].max())
    rs = (bb_s[1] - bb_s[0]) / (bb_s[3] - bb_s[2])
    rt = (bb_tx[1] - bb_tx[0]) / (bb_tx[3] - bb_tx[2])
    SX0, SX1, S_TH = 7.02, 8.72, 39.2
    TX0, TX1, T_TH = 9.36, 15.95, 52.6
    S_TB = theta_base(S_TH, (SX1 - SX0) / rs)
    T_TB = theta_base(T_TH, (TX1 - TX0) / rt)
    print(f"   [logo] CARGO simbolo th {S_TH:.1f}..{S_TB:.1f} | "
          f"texto th {T_TH:.1f}..{T_TB:.1f}")
    for lado, esp in ((-1, False), (1, True)):
        cl.marca_th(tri_si, bb_s, SX0, SX1, S_TH, S_TB, INDIGO_T, lado, esp)
        cl.marca_th(tri_sc, bb_s, SX0, SX1, S_TH, S_TB, CORAL_T, lado, esp)
        cl.marca_th(tri_tx, bb_tx, TX0, TX1, T_TH, T_TB, INDIGO_T, lado, esp)

    GD_ = np.degrees(cl.GABS)
    BF_T0, BF_T1 = 63.3, 75.3
    if bandeira == "colombia":
        BF_X0, BF_X1 = 3.94, 4.53
        _sel = ((cl.GX >= BF_X0) & (cl.GX <= BF_X1) &
                (GD_ >= BF_T0) & (GD_ <= BF_T1))
        if _sel.any():
            f = (GD_ - BF_T0) / (BF_T1 - BF_T0)
            for lo, hi, cor in ((0.0, 0.50, (0xFC, 0xD1, 0x16)),
                                (0.50, 0.75, (0x00, 0x33, 0x8D)),
                                (0.75, 1.00, (0xC8, 0x10, 0x2E))):
                m = _sel & (f >= lo) & (f < hi)
                cl.tex[m] = cor
            cl.pintado[_sel] = True
        _tp, _bbp = cl.texto_tris_b(texto_pais)
        for _lado, _esp in ((-1, False), (1, True)):
            cl.marca_th(_tp, _bbp, BF_X0 - 0.02, BF_X1 + 0.02, 76.4, 78.8,
                        (0x3A, 0x3C, 0x42), _lado, _esp, ppm=760)
    else:                                     # chile (b5b_livery.py, verbatim)
        _rz_bf = float(cl.zc_rz(np.array([4.23]))[1][0])
        BF_ARCO = math.radians(BF_T1 - BF_T0) * _rz_bf
        BF_X0 = 3.94
        BF_X1 = BF_X0 + 1.5 * BF_ARCO
        _sel = ((cl.GX >= BF_X0) & (cl.GX <= BF_X1) &
                (GD_ >= BF_T0) & (GD_ <= BF_T1))
        if _sel.any():
            fx = (cl.GX - BF_X0) / (BF_X1 - BF_X0)
            ft = (GD_ - BF_T0) / (BF_T1 - BF_T0)
            cl.tex[_sel & (ft < 0.5)] = (0xF2, 0xF3, 0xF5)
            cl.tex[_sel & (ft >= 0.5)] = (0xD5, 0x2B, 0x1E)
            cl.tex[_sel & (ft < 0.5) & (fx < 1.0 / 3.0)] = (0x0A, 0x39, 0x81)
            _lado_c = (BF_X1 - BF_X0) / 3.0
            _cxs = BF_X0 + _lado_c / 2.0
            _cts = BF_T0 + (BF_T1 - BF_T0) * 0.25
            _R = 0.30 * _lado_c
            _u = (cl.GX - _cxs) / _R
            _v = np.radians(GD_ - _cts) * _rz_bf / _R
            _ang = np.arctan2(_u, -_v)
            _rr = np.hypot(_u, _v)
            _BETA = math.radians(18.0)
            _aa = np.abs(np.mod(_ang + np.pi / 5.0, 2 * np.pi / 5.0) - np.pi / 5.0)
            _lim = math.sin(_BETA) / np.sin(_aa + _BETA)
            cl.tex[_sel & (_rr <= _lim)] = (0xF2, 0xF3, 0xF5)
            cl.pintado[_sel] = True
        _tp, _bbp = cl.texto_tris_b(texto_pais)
        for _lado, _esp in ((-1, False), (1, True)):
            cl.marca_th(_tp, _bbp, BF_X0 + 0.10, BF_X1 - 0.10, 76.4, 78.8,
                        (0x3A, 0x3C, 0x42), _lado, _esp, ppm=760)

    mr = cl.spec[spec_key]["marcas"]["matricula"]
    tr, bbr = cl.texto_tris_b(mr["texto"])
    for lado, esp in ((-1, False), (1, True)):
        cl.marca(cl.encaixa(tr, bbr, mr["x"][0], mr["x"][1], mr["z"][0],
                            mr["z"][1], espelha=esp),
                 mr["x"][0], mr["x"][1], mr["z"][0], mr["z"][1],
                 BRANCO_763, lado, ppm=760)
    tt_ = cl.spec[spec_key]["marcas"]["titulo"]
    tt, bbt = cl.texto_tris_b(tt_["texto"])
    for lado, esp in ((-1, False), (1, True)):
        cl.marca(cl.encaixa(tt, bbt, tt_["x"][0], tt_["x"][1], tt_["z"][0],
                            tt_["z"][1], espelha=esp, cis=0.20),
                 tt_["x"][0], tt_["x"][1], tt_["z"][0], tt_["z"][1],
                 TITULO, lado, ppm=760)
    # ventre: SO o simbolo, x 10.40..12.50
    lat = (np.pi - cl.GABS) * 2.466 * cl.LADO
    BX0, BX1 = 10.40, 12.50
    BH = (BX1 - BX0) / rs
    nx, nz = max(8, int((BX1 - BX0) * 300)), max(8, int(BH * 300))
    arrI = cl.fill_tris(cl.encaixa(tri_si, bb_s, BX0, BX1, -BH / 2, BH / 2),
                        BX0, BX1, -BH / 2, BH / 2, nx, nz)
    arrC = cl.fill_tris(cl.encaixa(tri_sc, bb_s, BX0, BX1, -BH / 2, BH / 2),
                        BX0, BX1, -BH / 2, BH / 2, nx, nz)
    for (a0, cor) in ((arrI, INDIGO_T), (arrC, CORAL_T)):
        sel = (cl.GX >= BX0) & (cl.GX <= BX1) & (np.abs(lat) <= BH / 2)
        if not sel.any():
            continue
        ix = np.clip(((cl.GX[sel] - BX0) / (BX1 - BX0) * nx).astype(int),
                     0, nx - 1)
        jz = np.clip(((lat[sel] + BH / 2) / BH * nz).astype(int), 0, nz - 1)
        r, c = np.where(sel)
        h = a0[jz, ix]
        cl.tex[r[h], c[h]] = cor
        cl.pintado[r[h], c[h]] = True
    cl.resuja(SUJA_763)


def _marcas_b77w(cl):
    """boeing 777-300ER/build_77w_fase2_livery.py secoes 5-7, verbatim (PT-MUG)."""
    INDIGO_T, CORAL_T = tuple(INDIGO), tuple(CORAL)
    tri_all, bb_all = cl.tris_do_objeto("B77W_LogoLATAM_E")
    tri_c, bb_c = cl.tris_do_objeto("B77W_LogoLATAM_E_Coral")
    if not tri_all or not tri_c:
        raise SystemExit("[logo] malhas do lockup nao encontradas")
    corte = bb_all[0] + 0.18 * (bb_all[1] - bb_all[0])
    tri_sim = [t for t in tri_all if max(p[0] for p in t) < corte]
    tri_wm = [t for t in tri_all if min(p[0] for p in t) >= corte]
    a = np.asarray(tri_sim + tri_c)
    bb_s = (a[..., 0].min(), a[..., 0].max(), a[..., 1].min(), a[..., 1].max())
    a = np.asarray(tri_wm)
    bb_w = (a[..., 0].min(), a[..., 0].max(), a[..., 1].min(), a[..., 1].max())
    rs = (bb_s[1] - bb_s[0]) / (bb_s[3] - bb_s[2])
    rw = (bb_w[1] - bb_w[0]) / (bb_w[3] - bb_w[2])
    SX0, SX1, S_TH = 7.91, 9.64, 46.8
    WX0, WX1, W_TH = 10.34, 17.26, 51.6
    S_TB = S_TH + math.degrees((SX1 - SX0) / rs / 3.10)
    W_TB = W_TH + math.degrees((WX1 - WX0) / rw / 3.10)
    print(f"   [logo] simbolo {rs:.3f} th {S_TH:.1f}..{S_TB:.1f} | "
          f"wordmark {rw:.3f} th {W_TH:.1f}..{W_TB:.1f}")
    for lado, esp in ((-1, False), (1, True)):
        cl.marca_th(tri_sim, bb_s, SX0, SX1, S_TH, S_TB, INDIGO_T, lado, esp,
                    raio=3.10)
        cl.marca_th(tri_c, bb_s, SX0, SX1, S_TH, S_TB, CORAL_T, lado, esp,
                    raio=3.10)
        cl.marca_th(tri_wm, bb_w, WX0, WX1, W_TH, W_TB, INDIGO_T, lado, esp,
                    raio=3.10)
    tr, bbr = cl.texto_tris_b("PT-MUG")
    for lado, esp in ((-1, False), (1, True)):
        cl.marca(cl.encaixa(tr, bbr, 60.64, 62.37, 0.80, 1.35, espelha=esp),
                 60.64, 62.37, 0.80, 1.35, BRANCO_763, lado, ppm=760)
    tt, bbt = cl.texto_tris_b("BOEING 777-300")
    for lado, esp in ((-1, False), (1, True)):
        cl.marca(cl.encaixa(tt, bbt, 55.84, 58.55, 0.78, 1.12, espelha=esp,
                            cis=0.18),
                 55.84, 58.55, 0.78, 1.12, INDIGO_T, lado, ppm=760)
    # ventre do PT-MUG: SO o simbolo, x 11.1..14.1
    lat = (np.pi - cl.GABS) * 3.10 * cl.LADO
    SBX0, SBX1 = 11.1, 14.1
    SBH = (SBX1 - SBX0) / rs
    nsx, nsz = max(8, int((SBX1 - SBX0) * 300)), max(8, int(SBH * 300))
    arrS = cl.fill_tris(cl.encaixa(tri_sim, bb_s, SBX0, SBX1, -SBH / 2, SBH / 2),
                        SBX0, SBX1, -SBH / 2, SBH / 2, nsx, nsz)
    arrC = cl.fill_tris(cl.encaixa(tri_c, bb_s, SBX0, SBX1, -SBH / 2, SBH / 2),
                        SBX0, SBX1, -SBH / 2, SBH / 2, nsx, nsz)
    for (a0, cor) in ((arrS, INDIGO_T), (arrC, CORAL_T)):
        sel = (cl.GX >= SBX0) & (cl.GX <= SBX1) & (np.abs(lat) <= SBH / 2)
        if not sel.any():
            continue
        ix = np.clip(((cl.GX[sel] - SBX0) / (SBX1 - SBX0) * nsx).astype(int),
                     0, nsx - 1)
        jz = np.clip(((lat[sel] + SBH / 2) / SBH * nsz).astype(int), 0, nsz - 1)
        r, c = np.where(sel)
        h = a0[jz, ix]
        cl.tex[r[h], c[h]] = cor
        cl.pintado[r[h], c[h]] = True
    cl.resuja([(6.5, 14.0, 156, 180, (0x9A, 0x93, 0x88), 0.08),
               (38.0, 46.0, 150, 180, (0x9E, 0x98, 0x8E), 0.06),
               (69.0, 74.0, 120, 180, (0x8E, 0x88, 0x82), 0.10)])


LEGADO = {
    "b763er": dict(spec="boeing 767-300ER/spec_763.json", luv=55.5,
                   ponte="b763", fn=_marcas_b763er),
    "b763f": dict(spec="boeing 767-300F/spec_763f.json", luv=55.5,
                  ponte="b763",
                  fn=lambda cl: _marcas_carga(cl, "livery_n536la",
                                              "colombia", "COLOMBIA")),
    "b763bcf": dict(spec="boeing 767-300BCF/spec_763bcf.json", luv=55.5,
                    ponte="b763",
                    fn=lambda cl: _marcas_carga(cl, "livery_cc_cxe",
                                                "chile", "CHILE")),
    "b77w": dict(spec="boeing 777-300ER/spec_77w.json", luv=74.5,
                 ponte="b77w", fn=_marcas_b77w),
}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    tag = argv[0]
    if tag in LEGADO:
        cfg = LEGADO[tag]
        for o in bpy.data.objects:
            o.hide_viewport = False
        bpy.context.view_layer.update()
        cl = CascoLegado(cfg["spec"], cfg["luv"], cfg["ponte"])
        print(f"[{tag}] legado  L={cl.LUV}  tex {cl.W}x{cl.H}")
        cfg["fn"](cl)
        cl.salvar()
        bpy.ops.wm.save_mainfile()
        print(f"[{tag}] blend saved")
        return
    tarefas = argv[1:] or ["lockup"]
    cfg = FROTA[tag]
    cs = Casco()
    print(f"[{tag}] hull {cs.ob.name}  L={cs.L:.3f}  tex {cs.W}x{cs.H}")
    if "lockup" in tarefas:
        fazer_lockup(cs, cfg)
    if "marcas" in tarefas:
        fazer_marcas(cs, tag)
    cs.salvar()
    bpy.ops.wm.save_mainfile()
    print(f"[{tag}] blend saved")


if __name__ == "__main__":
    main()
