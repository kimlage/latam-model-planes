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


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    tag = argv[0]
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
