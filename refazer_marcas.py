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
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import latam_livery_kit as kit  # noqa: E402

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


# ======================================================== legado A320-familia
# build_a319_livery.py / build_a320ceo_livery.py pintavam matricula, titulo e
# a marca do ventre numa grade supersampled 2x em (x, z) sobre a tabela de
# aneis (que e a tabela da malha serializada — conferido zc/rz/ry identicos).
# Movido para ca verbatim; o compositor por cobertura reproduz o downsample do
# builder texel a texel onde o fundo e uniforme dentro do texel.
#
# A MATRICULA do A319 e o caso especial documentado no QA-BACKLOG: o mesh
# Reg_E guarda o PT-TMN do master, entao pintar "a malha inteira" escreveria a
# matricula errada. A op abaixo usa a RECOMBINACAO do proprio builder
# (ilhas P,T,-,T,M,T do mesmo mesh) — que produz PT-TMT — e a pinta na caixa
# FINAL da rodada 2026-08-22 (fix_matricula_a319.py: porta 4 + 0.60..+2.40 m,
# |theta| 56.5..67.7, medida na propria foto), em BRANCO_MARCA, como o fix
# deixou. fix_matricula_a319.py fica como registro historico; a reconstrucao
# nao precisa mais dele.


class CascoA320:
    """Grades SS2 dos builders A319/A320ceo + compositor de cobertura."""

    def __init__(self, rings_rel, luv):
        import os as _os
        raiz = _os.path.dirname(_os.path.abspath(__file__))
        rings = json.load(open(_os.path.join(raiz, rings_rel)))
        self.rx = np.array([r["x"] for r in rings])
        self.rzc = np.array([r["zc"] for r in rings])
        self.rrz = np.array([r["rz"] for r in rings])
        self.rry = np.array([r["ry"] for r in rings])
        self.LUV = luv
        imT = bpy.data.images["LiveryTex"]
        imF = bpy.data.images["LiveryFac"]
        self.imT, self.imF = imT, imF
        W, H = imT.size
        self.W, self.H = W, H
        SS2 = 2
        self.SS2 = SS2
        Ws, Hs = W * SS2, H * SS2
        u = (np.arange(Ws) + 0.5) / Ws
        v = (np.arange(Hs) + 0.5) / Hs
        X = u * luv
        TH = v * 2 * math.pi - math.pi
        self.Xg = np.broadcast_to(X, (Hs, Ws))
        self.THg = np.broadcast_to(TH[:, None], (Hs, Ws))
        ZCg = np.interp(X, self.rx, self.rzc)[None, :]
        RZg = np.interp(X, self.rx, self.rrz)[None, :]
        RYg = np.interp(X, self.rx, self.rry)[None, :]
        self.Zg = ZCg + RZg * np.cos(self.THg)
        self.Yg = RYg * np.sin(self.THg)
        self.THdeg = np.degrees(np.abs(self.THg))
        buf = np.empty(W * H * 4, np.float32)
        imT.pixels.foreach_get(buf)
        self.t4 = buf.reshape(H, W, 4)
        buf = np.empty(W * H * 4, np.float32)
        imF.pixels.foreach_get(buf)
        self.f4 = buf.reshape(H, W, 4)

    # --- machinery dos builders, verbatim -------------------------------
    @staticmethod
    def tri_mask_2d(tris, x0, x1, y0, y1, res=600):
        nx = max(int((x1 - x0) * res), 4)
        ny = max(int((y1 - y0) * res), 4)
        m = np.zeros((ny, nx), bool)
        gx, gy = np.meshgrid(np.arange(nx) + 0.5, np.arange(ny) + 0.5)
        gx = x0 + gx * (x1 - x0) / nx
        gy = y0 + gy * (y1 - y0) / ny
        for (ax, ay), (bx, by), (cx, cy) in tris:
            lo_x = min(ax, bx, cx); hi_x = max(ax, bx, cx)
            lo_y = min(ay, by, cy); hi_y = max(ay, by, cy)
            i0 = max(int((lo_x - x0) / (x1 - x0) * nx) - 1, 0)
            i1 = min(int((hi_x - x0) / (x1 - x0) * nx) + 2, nx)
            j0 = max(int((lo_y - y0) / (y1 - y0) * ny) - 1, 0)
            j1 = min(int((hi_y - y0) / (y1 - y0) * ny) + 2, ny)
            if i1 <= i0 or j1 <= j0:
                continue
            sx = gx[j0:j1, i0:i1]; sy = gy[j0:j1, i0:i1]
            d1 = (sx - bx) * (ay - by) - (ax - bx) * (sy - by)
            d2 = (sx - cx) * (by - cy) - (bx - cx) * (sy - cy)
            d3 = (sx - ax) * (cy - ay) - (cx - ax) * (sy - ay)
            m[j0:j1, i0:i1] |= ~(((d1 < 0) | (d2 < 0) | (d3 < 0)) &
                                 ((d1 > 0) | (d2 > 0) | (d3 > 0)))
        return m, (x0, x1, y0, y1)

    @staticmethod
    def sample_mask(mask_info, px, py):
        m, (x0, x1, y0, y1) = mask_info
        ny, nx = m.shape
        ii = ((px - x0) / (x1 - x0) * nx).astype(int)
        jj = ((py - y0) / (y1 - y0) * ny).astype(int)
        ok = (ii >= 0) & (ii < nx) & (jj >= 0) & (jj < ny)
        out = np.zeros(px.shape, bool)
        out[ok] = m[jj[ok], ii[ok]]
        return out

    @staticmethod
    def mesh_islands(me):
        import collections
        adj = collections.defaultdict(set)
        for e in me.edges:
            a, b = e.vertices
            adj[a].add(b); adj[b].add(a)
        seen = set(); islands = []
        for v0 in range(len(me.vertices)):
            if v0 in seen:
                continue
            stack = [v0]; comp = set()
            while stack:
                v1 = stack.pop()
                if v1 in comp:
                    continue
                comp.add(v1)
                stack.extend(adj[v1] - comp)
            seen |= comp
            islands.append(comp)
        return islands

    @staticmethod
    def mesh_tris_world(name):
        import mathutils
        ob = bpy.data.objects[name]
        me = ob.data
        mw = mathutils.Matrix.LocRotScale(ob.location, ob.rotation_euler,
                                          ob.scale)
        vs = [mw @ v.co for v in me.vertices]
        me.calc_loop_triangles()
        return [[vs[i] for i in t.vertices] for t in me.loop_triangles]

    def compor(self, selSS, cor, nome=""):
        """Cobertura do texel = media dos 4 subsamples (o downsample SS2 do
        builder); tinta e fac compostos com essa cobertura."""
        H, W, SS2 = self.H, self.W, self.SS2
        cov = selSS.reshape(H, SS2, W, SS2).mean(axis=(1, 3)).astype(np.float32)
        m = cov > 0
        a = cov[m][:, None]
        self.t4[..., :3][m] = (self.t4[..., :3][m] * (1 - a) +
                               np.asarray(cor, np.float32)[None, :] * a)
        self.t4[..., 3][m] = 1.0
        for k in range(3):
            self.f4[..., k][m] = self.f4[..., k][m] * (1 - a[:, 0]) + a[:, 0]
        print(f"   [pintar]  {nome:24} {int(m.sum())} texels (SS2)")
        return int(m.sum())

    def salvar(self):
        self.imT.pixels.foreach_set(self.t4.ravel())
        self.imT.update()
        self.imF.pixels.foreach_set(self.f4.ravel())
        self.imF.update()
        for im in (self.imT, self.imF):
            if im.packed_file:
                im.pack()
        print("   [salvar] LiveryTex + LiveryFac atualizadas (SS2)")


C_A320 = {1: (0.969, 0.976, 0.980), 2: (0.165, 0.000, 0.533),
          3: (0.929, 0.086, 0.318)}


def _ventre_a320(ca):
    """paint_belly_decal dos builders, verbatim: LogoBarriga sobre o ventre."""
    for nomes, c in ((["LogoBarriga_Coral"], 3), (["LogoBarriga"], 2)):
        tris3 = []
        for n in nomes:
            tris3 += ca.mesh_tris_world(n)
        t2 = [[(p.x, p.y) for p in t] for t in tris3]
        xs = [p[0] for t in t2 for p in t]; ys = [p[1] for t in t2 for p in t]
        mi = ca.tri_mask_2d(t2, min(xs) - 0.05, max(xs) + 0.05,
                            min(ys) - 0.05, max(ys) + 0.05)
        sel = ca.sample_mask(mi, ca.Xg, ca.Yg)
        sel &= (np.cos(ca.THg) < -0.35)
        ca.compor(sel, C_A320[c], nome=f"ventre {nomes[0]}")


def _marcas_a319(ca):
    """Marcas do A319 (PT-TMT): ventre, matricula recombinada, titulo."""
    _ventre_a320(ca)
    # --- matricula: glifos P,T,-,T,M,T recombinados de Reg_E (build_a319_livery,
    # verbatim), pintados na caixa FINAL de fix_matricula_a319.py.
    reg = bpy.data.objects["Reg_E"]
    me = reg.data
    me.calc_loop_triangles()
    isl = ca.mesh_islands(me)

    def isl_bbox(comp):
        xs = [me.vertices[i].co.x for i in comp]
        zs = [me.vertices[i].co.z for i in comp]
        return min(xs), max(xs), min(zs), max(zs)

    isl.sort(key=lambda c: isl_bbox(c)[0])
    vert_isl = {}
    for k, comp in enumerate(isl):
        for i in comp:
            vert_isl[i] = k
    tris_by_isl = {k: [] for k in range(len(isl))}
    for t in me.loop_triangles:
        k = vert_isl[t.vertices[0]]
        tris_by_isl[k].append([(me.vertices[i].co.x, me.vertices[i].co.z)
                               for i in t.vertices])
    seq = [0, 1, 2, 3, 4, 1]            # P T - T M N -> P T - T M T
    bb = [isl_bbox(c) for c in isl]
    tris2 = []
    for pos, k in enumerate(seq):
        src = tris_by_isl[k]
        tgt_slot = bb[pos] if pos < len(bb) else bb[-1]
        dx = (0.5 * (tgt_slot[0] + tgt_slot[1])) - (0.5 * (bb[k][0] + bb[k][1]))
        tris2 += [[(px + dx, pz) for px, pz in t] for t in src]
    xs = [p[0] for t in tris2 for p in t]; zs = [p[1] for t in tris2 for p in t]
    lx0, lx1, lz0, lz1 = min(xs), max(xs), min(zs), max(zs)
    mi = ca.tri_mask_2d(tris2, lx0 - 0.02, lx1 + 0.02, lz0 - 0.02, lz1 + 0.02,
                        res=800)
    # caixa FINAL (fix_matricula_a319.py): porta 4 (25.81) + 0.60..+2.40 m,
    # |theta| 56.5..67.7; esticada para preencher a caixa, como o fix fez.
    RX0, RX1, RT0, RT1 = 25.81 + 0.60, 25.81 + 2.40, 56.5, 67.7
    dentro = ((ca.Xg >= RX0) & (ca.Xg <= RX1) &
              (ca.THdeg >= RT0) & (ca.THdeg <= RT1))
    u = np.clip((ca.Xg - RX0) / (RX1 - RX0), 0.0, 1.0)
    vfr = np.clip((ca.THdeg - RT0) / (RT1 - RT0), 0.0, 1.0)
    gzs = lz1 - vfr * (lz1 - lz0)
    cor = tuple(np.array(BRANCO_MARCA, np.float32) / 255.0)
    for lado in (-1, 1):
        uu = u if lado < 0 else (1.0 - u)
        gxs = lx0 + uu * (lx1 - lx0)
        sel = dentro & ca.sample_mask(mi, gxs, gzs)
        sel &= ((ca.Yg < 0) if lado < 0 else (ca.Yg > 0)) & \
            (np.abs(np.sin(ca.THg)) > 0.30)
        ca.compor(sel, cor,
                  nome=f"matricula PT-TMT {'port' if lado < 0 else 'stbd'}")
    # --- titulo 'AIRBUS A319' (build_a319_livery, verbatim: ilhas do
    # MarkAirbusNeo_E + '1' da haste do I + '9' reconstruido). A cunha velha
    # destruiu '1','9' e o swirl NA TEXTURA (QA-BACKLOG "AIRBUS A3"); esta op
    # repinta a arte completa do builder — a unica fonte que resta.
    mk = bpy.data.objects["MarkAirbusNeo_E"]
    mm = mk.data
    mm.calc_loop_triangles()
    isl = ca.mesh_islands(mm)

    def mbox(comp):
        xs = [mm.vertices[i].co.x for i in comp]
        ys = [mm.vertices[i].co.y for i in comp]
        return min(xs), max(xs), min(ys), max(ys)

    isl.sort(key=lambda c: mbox(c)[0])
    vert_isl = {}
    for k, comp in enumerate(isl):
        for i in comp:
            vert_isl[i] = k
    mtris = {k: [] for k in range(len(isl))}
    for t in mm.loop_triangles:
        k = vert_isl[t.vertices[0]]
        mtris[k].append([(mm.vertices[i].co.x, mm.vertices[i].co.y)
                         for i in t.vertices])
    n = len(isl)
    keep = list(range(0, n - 2))
    tris2 = []
    for k in keep:
        tris2 += mtris[k]
    b3 = mbox(isl[keep[-1]])
    gw = b3[1] - b3[0]
    gap = 0.15 * gw
    capz0, capz1 = b3[2], b3[3]
    widths = [(mbox(isl[k])[1] - mbox(isl[k])[0], k) for k in keep[1:]]
    wI, kI = sorted(widths)[0]
    dx = (b3[1] + gap) - mbox(isl[kI])[0]
    one_tris = [[(px + dx, py) for px, py in t] for t in mtris[kI]]
    tris2 += one_tris
    one_x1 = mbox(isl[kI])[1] + dx
    bx0 = one_x1 + gap
    bw = gw * 0.92
    bh = (capz1 - capz0)
    cx = bx0 + 0.5 * bw * 0.92
    cyb = capz0 + bh * 0.62
    r_out_x = 0.46 * bw; r_out_y = 0.40 * bh
    r_in_x = 0.24 * bw; r_in_y = 0.20 * bh
    NSEG = 24
    for i in range(NSEG):
        a0 = 2 * math.pi * i / NSEG; a1 = 2 * math.pi * (i + 1) / NSEG
        o0 = (cx + r_out_x * math.cos(a0), cyb + r_out_y * math.sin(a0))
        o1 = (cx + r_out_x * math.cos(a1), cyb + r_out_y * math.sin(a1))
        i0 = (cx + r_in_x * math.cos(a0), cyb + r_in_y * math.sin(a0))
        i1 = (cx + r_in_x * math.cos(a1), cyb + r_in_y * math.sin(a1))
        tris2.append([o0, o1, i1]); tris2.append([o0, i1, i0])
    sw = wI
    sx0 = cx + r_out_x - sw
    tris2.append([(sx0, capz0), (sx0 + sw, capz0), (sx0 + sw, cyb + 0.1 * bh)])
    tris2.append([(sx0, capz0), (sx0 + sw, cyb + 0.1 * bh), (sx0, cyb + 0.1 * bh)])
    xs = [p[0] for t in tris2 for p in t]; ys = [p[1] for t in tris2 for p in t]
    lx0, lx1, ly0, ly1 = min(xs), max(xs), min(ys), max(ys)
    TX0, TX1, TZ0, TZ1 = 23.45, 25.20, 1.040, 1.210
    s = min((TX1 - TX0) / (lx1 - lx0), (TZ1 - TZ0) / (ly1 - ly0))
    tris2 = [[(TX0 + (px - lx0) * s, TZ0 + (py - ly0) * s) for px, py in t]
             for t in tris2]
    mi = ca.tri_mask_2d(tris2, TX0 - 0.03, TX1 + 0.03, TZ0 - 0.03, TZ1 + 0.03,
                        res=1500)
    selp = ca.sample_mask(mi, ca.Xg, ca.Zg) & (ca.Yg < 0) & \
        (np.abs(np.sin(ca.THg)) > 0.25)
    XMIR = TX0 + TX1
    sels = ca.sample_mask(mi, XMIR - ca.Xg, ca.Zg) & (ca.Yg > 0) & \
        (np.abs(np.sin(ca.THg)) > 0.25)
    ca.compor(selp | sels, C_A320[2], nome="titulo AIRBUS A319")


def _marcas_a320ceo(ca):
    """Marcas do A320ceo (CC-BFO): ventre, matricula, titulo (verbatim)."""
    _ventre_a320(ca)
    # --- matricula CC-BFO em Arial Bold (a fonte do master), branca no indigo
    D = bpy.data
    cu = D.curves.new("RegCeoTmp", type='FONT')
    cu.body = "CC-BFO"
    cu.font = D.fonts["Arial Bold"]
    cu.size = 1.0
    ob = D.objects.new("RegCeoTmp", cu)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = ob.evaluated_get(dg).to_mesh()
    me.calc_loop_triangles()
    tris2 = [[(me.vertices[i].co.x, me.vertices[i].co.y) for i in t.vertices]
             for t in me.loop_triangles]
    xs = [p[0] for t in tris2 for p in t]; ys = [p[1] for t in tris2 for p in t]
    lx0, lx1, ly0, ly1 = min(xs), max(xs), min(ys), max(ys)
    TX0, TZ0, TZ1 = 30.29, 1.04, 1.335
    s = (TZ1 - TZ0) / (ly1 - ly0)
    tris2 = [[(TX0 + (px - lx0) * s, TZ0 + (py - ly0) * s) for px, py in t]
             for t in tris2]
    TX1 = TX0 + (lx1 - lx0) * s
    mi = ca.tri_mask_2d(tris2, TX0 - 0.05, TX1 + 0.05, TZ0 - 0.05, TZ1 + 0.05,
                        res=900)
    selp = ca.sample_mask(mi, ca.Xg, ca.Zg) & (ca.Yg < 0) & \
        (np.abs(np.sin(ca.THg)) > 0.30)
    XMIR = TX0 + TX1
    sels = ca.sample_mask(mi, XMIR - ca.Xg, ca.Zg) & (ca.Yg > 0) & \
        (np.abs(np.sin(ca.THg)) > 0.30)
    ca.compor(selp | sels, C_A320[1], nome="matricula CC-BFO")
    ob.evaluated_get(dg).to_mesh_clear()
    D.objects.remove(ob, do_unlink=True)
    D.curves.remove(cu)
    # --- titulo 'AIRBUS A320': ilhas do MarkAirbusNeo_E menos a ultima ('neo')
    mk = D.objects["MarkAirbusNeo_E"]
    mm = mk.data
    mm.calc_loop_triangles()
    isl = ca.mesh_islands(mm)

    def mbox(comp):
        xs = [mm.vertices[i].co.x for i in comp]
        ys = [mm.vertices[i].co.y for i in comp]
        return min(xs), max(xs), min(ys), max(ys)

    isl.sort(key=lambda c: mbox(c)[0])
    vert_isl = {}
    for k, comp in enumerate(isl):
        for i in comp:
            vert_isl[i] = k
    mtris = {k: [] for k in range(len(isl))}
    for t in mm.loop_triangles:
        k = vert_isl[t.vertices[0]]
        mtris[k].append([(mm.vertices[i].co.x, mm.vertices[i].co.y)
                         for i in t.vertices])
    n = len(isl)
    keep = list(range(0, n - 1))
    tris2 = []
    for k in keep:
        tris2 += mtris[k]
    xs = [p[0] for t in tris2 for p in t]; ys = [p[1] for t in tris2 for p in t]
    lx0, lx1, ly0, ly1 = min(xs), max(xs), min(ys), max(ys)
    TX0, TX1, TZ0, TZ1 = 26.21, 27.94, 1.040, 1.240
    s = min((TX1 - TX0) / (lx1 - lx0), (TZ1 - TZ0) / (ly1 - ly0))
    tris2 = [[(TX0 + (px - lx0) * s, TZ0 + (py - ly0) * s) for px, py in t]
             for t in tris2]
    mi = ca.tri_mask_2d(tris2, TX0 - 0.03, TX1 + 0.03, TZ0 - 0.03, TZ1 + 0.03,
                        res=1500)
    selp = ca.sample_mask(mi, ca.Xg, ca.Zg) & (ca.Yg < 0) & \
        (np.abs(np.sin(ca.THg)) > 0.25)
    XMIR = TX0 + TX1
    sels = ca.sample_mask(mi, XMIR - ca.Xg, ca.Zg) & (ca.Yg > 0) & \
        (np.abs(np.sin(ca.THg)) > 0.25)
    ca.compor(selp | sels, C_A320[2], nome="titulo AIRBUS A320")


LEGADO_A320 = {
    "a319": ("airbus A319/a319_rings.json", 34.2, _marcas_a319),
    "a320ceo": ("airbus A320ceo/a320ceo_rings.json", 38.0, _marcas_a320ceo),
}


# ========================================================== legado A321s
# As marcas FINAIS dos dois A321 foram pintadas por
#   airbus A321neo/build_a321_fase2_livery.py + build_a321_fase2b_espelho.py
#   airbus A321ceo/fix_reg_ghosts.py + fix_titulo_a321.py
# — todos com o mesmo `raster_side` (ss=2, ponte circular lida da malha).
# Movidos para ca verbatim; os quatro arquivos ficam como registro historico.


class CascoA321:
    """Ponte circular (z-only) e rasterizador raster_side dos scripts A321."""

    def __init__(self, luv):
        D = bpy.data
        self.LUV = luv
        fus = D.objects["Fuselagem"]
        rings = {}
        for v in fus.data.vertices:
            rings.setdefault(round(v.co.x, 3), []).append(v.co)
        rx, rzc, rr = [], [], []
        for k in sorted(rings):
            vs = rings[k]
            if len(vs) < 8:
                continue
            zmax = max(p.z for p in vs); zmin = min(p.z for p in vs)
            rx.append(k); rzc.append((zmax + zmin) / 2)
            rr.append((zmax - zmin) / 2)
        self._rx = np.array(rx); self._rzc = np.array(rzc)
        self._rr = np.array(rr)
        self._aneis = None            # tabela (x,zc,rz,ry) p/ exclusao de anel
        imT = D.images["LiveryTex"]; imF = D.images["LiveryFac"]
        self.imT, self.imF = imT, imF
        W, H = imT.size
        self.W, self.H = W, H
        ux = (np.arange(W) + 0.5) / W * luv
        vv = (np.arange(H) + 0.5) / H
        TH = vv * 2 * math.pi - math.pi
        self.XG = np.broadcast_to(ux, (H, W))
        self.THG = np.broadcast_to(TH[:, None], (H, W))
        self.ZG = (np.broadcast_to(self.zc_of(ux), (H, W)) +
                   np.broadcast_to(self.r_of(ux), (H, W)) * np.cos(self.THG))
        self.SIDE = np.abs(np.sin(self.THG)) > 0.25
        buf = np.empty(W * H * 4, np.float32)
        imT.pixels.foreach_get(buf)
        self.tex = buf.reshape(H, W, 4)
        buf = np.empty(W * H * 4, np.float32)
        imF.pixels.foreach_get(buf)
        self.fac = buf.reshape(H, W, 4)

    def anel_excluir(self, rings_rel, nomes):
        """Mascara (H,W) do anel branco da porta (banda+sulco, dilatada 1
        texel): os erases dos ops de matricula NAO podem tocar o anel — na
        textura embarcada ele e o AA do portas_familia, pintado DEPOIS dos
        fixes de marca, e qualquer repintura binaria aqui o degradaria."""
        import os as _os
        raiz = _os.path.dirname(_os.path.abspath(__file__))
        rj = json.load(open(_os.path.join(raiz, rings_rel)))
        rx = np.array([r["x"] for r in rj]); rzc = np.array([r["zc"] for r in rj])
        rrz = np.array([r["rz"] for r in rj]); rry = np.array([r["ry"] for r in rj])
        W, H = self.W, self.H
        X = (np.arange(W) + 0.5) / W * self.LUV
        TH = ((np.arange(H) + 0.5) / H - 0.5) * 2 * math.pi
        WG = kit.grade_arco(rx, rrz, rry, X, TH)
        Xg = np.broadcast_to(X, (H, W))
        out = np.zeros((H, W), bool)
        for nome in nomes:
            ob = bpy.data.objects.get(nome)
            if ob is None:
                continue
            cx = kit.caixa_porta_xw(ob, rx, rzc, rrz, rry)
            banda, sulco = kit.anel_porta(Xg, WG, cx, 0.058, 0.010, 0.15)
            out |= banda | sulco
        per = out.copy()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                per |= np.roll(np.roll(out, dy, 0), dx, 1)
        return per

    def zc_of(self, x):
        return np.interp(x, self._rx, self._rzc)

    def r_of(self, x):
        return np.interp(x, self._rx, self._rr)

    def raster_side(self, tris, cor, lado, ss=2):
        W, H, L = self.W, self.H, self.LUV
        Ws, Hs = W * ss, H * ss
        cov = np.zeros((Hs, Ws), dtype=bool)
        for pts in tris:
            pix = []
            for (x, _, z) in pts:
                r = max(self.r_of(x), 1e-6)
                ct = float(np.clip((z - self.zc_of(x)) / r, -1, 1))
                th = math.acos(ct)
                if lado == "E":
                    th = -th
                pix.append((x / L * Ws, (th + math.pi) / (2 * math.pi) * Hs))
            xs = [p[0] for p in pix]; ys = [p[1] for p in pix]
            xlo, xhi = max(int(min(xs)), 0), min(int(max(xs)) + 1, Ws - 1)
            ylo, yhi = max(int(min(ys)), 0), min(int(max(ys)) + 1, Hs - 1)
            if xhi <= xlo or yhi <= ylo:
                continue
            gx, gy = np.meshgrid(np.arange(xlo, xhi + 1), np.arange(ylo, yhi + 1))
            (ax, ay), (bx, by), (cx, cy) = pix
            d1 = (gx - bx) * (ay - by) - (ax - bx) * (gy - by)
            d2 = (gx - cx) * (by - cy) - (bx - cx) * (gy - cy)
            d3 = (gx - ax) * (cy - ay) - (cx - ax) * (gy - ay)
            mm = ~((((d1 < 0) | (d2 < 0) | (d3 < 0)) &
                    ((d1 > 0) | (d2 > 0) | (d3 > 0))))
            cov[ylo:yhi + 1, xlo:xhi + 1] |= mm
        frac = cov.reshape(H, ss, W, ss).mean(axis=(1, 3))
        mm = frac > 0.02
        a = frac[mm][:, None]
        self.tex[mm, 0:3] = self.tex[mm, 0:3] * (1 - a) + np.asarray(cor)[None, :] * a
        self.fac[mm, 0:3] = np.maximum(self.fac[mm, 0:3], a)
        return int(mm.sum())

    @staticmethod
    def mirror(tris, x0, x1):
        return [[(x0 + x1 - x, y, z) for (x, y, z) in pts] for pts in tris]

    @staticmethod
    def text_tris(body, cap, x_at, z_at):
        D = bpy.data
        cu = D.curves.new("t", 'FONT')
        cu.body = body
        cu.font = D.fonts["Arial Bold"]
        cu.size = 1.0
        ob = D.objects.new("t", cu)
        bpy.context.scene.collection.objects.link(ob)
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]
        s = cap / (max(ys) - min(ys))
        x0b, y0b = min(xs), min(ys)
        me.calc_loop_triangles()
        tris = []
        for tri in me.loop_triangles:
            pts = [me.vertices[i].co for i in tri.vertices]
            tris.append([((p.x - x0b) * s + x_at, 0.0, (p.y - y0b) * s + z_at)
                         for p in pts])
        span = (max(xs) - min(xs)) * s
        bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.meshes.remove(me)
        return tris, span

    def malha_titulo_321(self):
        """AIRBUS do MarkAirbusNeo_E + glifos do SVG a321neo (fase2b, verbatim:
        importa o SVG se a malha temporaria nao existir no blend)."""
        D = bpy.data
        mark = D.objects["MarkAirbusNeo_E"]
        me = mark.data
        me.calc_loop_triangles()
        xs_loc = sorted(set(round(v.co.x, 4) for v in me.vertices))
        ga = max((b - a, a) for a, b in zip(xs_loc[:-1], xs_loc[1:]))[1]
        airbus_v = [v.co for v in me.vertices if v.co.x <= ga + 1e-5]
        ax0 = min(v.x for v in airbus_v); ax1 = max(v.x for v in airbus_v)
        ay0 = min(v.y for v in airbus_v); ay1 = max(v.y for v in airbus_v)
        s_air = 0.145 / (ay1 - ay0)
        me321 = D.meshes.get("a321neo_mark")
        if me321 is None:
            import os as _os
            svg = _os.path.abspath(_os.path.join(
                _os.path.dirname(_os.path.abspath(__file__)),
                "airbus_a321neo_logo.svg"))
            before = set(D.objects)
            bpy.ops.import_curve.svg(filepath=svg)
            imported = [o for o in D.objects if o not in before]
            bmn = bmesh.new()
            dg = bpy.context.evaluated_depsgraph_get()
            for o in imported:
                mev = o.evaluated_get(dg).to_mesh()
                vmap = {}
                for p in mev.polygons:
                    nv = []
                    for vi in p.vertices:
                        if vi not in vmap:
                            vmap[vi] = bmn.verts.new(o.matrix_world @
                                                     mev.vertices[vi].co)
                        nv.append(vmap[vi])
                    try:
                        bmn.faces.new(nv)
                    except ValueError:
                        pass
                o.evaluated_get(dg).to_mesh_clear()
            for o in imported:
                bpy.data.objects.remove(o, do_unlink=True)
            bmesh.ops.triangulate(bmn, faces=bmn.faces[:])
            me321 = D.meshes.new("a321neo_mark")
            bmn.to_mesh(me321)
            bmn.free()
        me321.calc_loop_triangles()
        return me, ga, ax0, ax1, ay0, ay1, s_air, me321


def _marcas_a321neo(cn):
    """PS-LBA: matricula + titulo, port do fase2 e stbd do fase2b, verbatim."""
    NAVY = np.array([0.110, 0.180, 0.388])
    INDIGO_F = np.array([0.165, 0.000, 0.533])
    # erases (base declarada). O anel branco da porta 2 e EXCLUIDO: na textura
    # embarcada ele e o AA do portas_familia (pintado depois dos fixes) e o
    # erase nao pode toca-lo.
    anel = cn.anel_excluir("airbus A321neo/a321_rings.json",
                           ("Porta2_E", "Porta2_D"))
    D_side = cn.THG > 0
    E_side = cn.THG < 0
    for side in (E_side, D_side):
        m = side & (cn.XG > 36.6) & (cn.XG < 39.3) & (cn.ZG > 0.62) & \
            (cn.ZG < 1.18) & (cn.tex[..., 0] > 0.5) & (cn.tex[..., 1] > 0.5) & ~anel
        cn.tex[m, 0:3] = INDIGO_F
        cn.fac[m, 0:3] = 1.0
        m = side & (cn.XG > 33.35) & (cn.XG < 35.62) & (cn.ZG > 0.82) & \
            (cn.ZG < 1.12) & (cn.tex[..., 2] - cn.tex[..., 0] > 0.05)
        cn.fac[m, 0:3] = 0.0
    # registration: x 37.15 e a POSICAO EMBARCADA (spec_a321.json ->
    # cauda_livery_ps_lba: "x 37.15-39.12"; o 36.78 do fase2 foi re-assentado
    # por uma rodada posterior). Port reta, stbd espelhada (fase2b).
    tris, span = cn.text_tris("PS-LBA", 0.40, 37.15, 0.70)
    n = cn.raster_side(tris, (1.0, 1.0, 1.0), "E")
    print(f"   [pintar]  matricula PS-LBA port    {n} texels")
    n = cn.raster_side(cn.mirror(tris, 37.15, 37.15 + span), (1.0, 1.0, 1.0), "D")
    print(f"   [pintar]  matricula PS-LBA stbd    {n} texels")
    # title: AIRBUS + A321neo (cap 0.145, z 0.88, X0 33.55)
    me, ga, ax0, ax1, ay0, ay1, s_air, me321 = cn.malha_titulo_321()
    X0 = 33.55
    tris_air = []
    for tri in me.loop_triangles:
        pts = [me.vertices[i].co for i in tri.vertices]
        if max(p.x for p in pts) <= ga + 1e-5:
            tris_air.append([((p.x - ax0) * s_air + X0, 0.0,
                              (p.y - ay0) * s_air + 0.88) for p in pts])
    xs = [v.co.x for v in me321.vertices]; ys = [v.co.y for v in me321.vertices]
    n0, m0, m1 = min(xs), min(ys), max(ys)
    s321 = 0.145 / ((m1 - m0) / 1.12)
    XA = X0 + (ax1 - ax0) * s_air + 0.10
    tris321 = []
    for tri in me321.loop_triangles:
        pts = [me321.vertices[i].co for i in tri.vertices]
        tris321.append([((p.x - n0) * s321 + XA, 0.0,
                         (p.y - m0) * s321 + 0.88) for p in pts])
    xend = XA + (max(xs) - n0) * s321
    n = cn.raster_side(tris_air + tris321, NAVY, "E")
    print(f"   [pintar]  titulo A321neo port      {n} texels")
    n = cn.raster_side(cn.mirror(tris_air + tris321, X0, xend), NAVY, "D")
    print(f"   [pintar]  titulo A321neo stbd      {n} texels")


def _marcas_a321ceo(cn):
    """PT-MXP: fix_reg_ghosts.py + fix_titulo_a321.py, verbatim."""
    D = bpy.data
    INDIGO_F = np.array([0.165, 0.000, 0.533])
    NAVY = np.array([0.110, 0.180, 0.388])
    WHITE = np.array([1.0, 1.0, 1.0])
    # refill indigo da zona da matricula (fix_reg_ghosts), MAS excluindo o anel
    # D4: na textura embarcada ele e o AA do portas_familia, pintado depois dos
    # fixes, e o refill+anel binario do fix o degradaria a cada rodada.
    anel = cn.anel_excluir("airbus A321ceo/a321ceo_rings.json",
                           ("Porta4_E", "Porta4_D"))
    m = (cn.XG > 36.55) & (cn.XG < 39.30) & (cn.ZG > 0.52) & (cn.ZG < 1.28) & \
        cn.SIDE & ~anel
    cn.tex[m, 0:3] = INDIGO_F
    cn.fac[m, 0:3] = 1.0
    print(f"   [apagar]  zona da matricula -> indigo  {int(m.sum())} texels")
    tris, span = cn.text_tris("PT-MXP", 0.40, 37.15, 0.70)
    n = cn.raster_side(tris, (1.0, 1.0, 1.0), "E")
    print(f"   [pintar]  matricula PT-MXP port    {n} texels")
    n = cn.raster_side(cn.mirror(tris, 37.15, 37.15 + span), (1.0, 1.0, 1.0), "D")
    print(f"   [pintar]  matricula PT-MXP stbd    {n} texels")
    # titulo AIRBUS A321 (fix_titulo_a321.py): erase box + clusters <= cap
    m = (cn.XG > 32.80) & (cn.XG < 34.95) & (cn.ZG > 0.78) & (cn.ZG < 1.18) & cn.SIDE
    cn.fac[m, 0:3] = 0.0
    me, ga, ax0, ax1, ay0, ay1, s_air, me321 = cn.malha_titulo_321()
    L_air = (ax1 - ax0) * s_air
    ivs = []
    for tri in me321.loop_triangles:
        pts = [me321.vertices[i].co for i in tri.vertices]
        ivs.append((min(p.x for p in pts), max(p.x for p in pts), tri))
    ivs.sort(key=lambda t: t[0])
    clusters = []
    for lo, hi, tri in ivs:
        if clusters and lo <= clusters[-1][1] + 1e-6:
            clusters[-1][1] = max(clusters[-1][1], hi)
            clusters[-1][2].append(tri)
        else:
            clusters.append([lo, hi, [tri]])
    span_ = clusters[-1][1]
    keep = [c for c in clusters if c[1] <= 0.62 * span_]
    tris321_raw = [t for c in keep for t in c[2]]
    k0 = min(c[0] for c in keep); k1 = max(c[1] for c in keep)
    kys = [me321.vertices[i].co.y for c in keep for t in c[2] for i in t.vertices]
    cap321 = max(kys) - min(kys)
    s321 = 0.145 / cap321
    L_321 = (k1 - k0) * s321
    ky0 = min(kys)
    GAP = 0.10
    X_END = 34.75
    X0 = X_END - (L_air + GAP + L_321)
    tris_air = []
    for tri in me.loop_triangles:
        pts = [me.vertices[i].co for i in tri.vertices]
        if max(p.x for p in pts) <= ga + 1e-5:
            tris_air.append([((p.x - ax0) * s_air + X0, 0.0,
                              (p.y - ay0) * s_air + 0.88) for p in pts])
    XA = X0 + L_air + GAP
    tris_321 = []
    for tri in tris321_raw:
        pts = [me321.vertices[i].co for i in tri.vertices]
        tris_321.append([((p.x - k0) * s321 + XA, 0.0,
                          (p.y - ky0) * s321 + 0.88) for p in pts])
    allt = tris_air + tris_321
    n = cn.raster_side(allt, NAVY, "E")
    print(f"   [pintar]  titulo AIRBUS A321 port  {n} texels")
    n = cn.raster_side(cn.mirror(allt, X0, X_END), NAVY, "D")
    print(f"   [pintar]  titulo AIRBUS A321 stbd  {n} texels")


LEGADO_A321 = {
    "a321neo": (45.0, _marcas_a321neo),
    "a321ceo": (45.0, _marcas_a321ceo),
}


# ============================================================== legado 787-8
# As marcas FINAIS do CC-BBF foram pintadas por build_788_livery2.py (lockup
# subido +0.12 m e espelhado parte a parte; matricula cap 0.30 na caixa medida
# nas fotos) e o simbolo do ventre por build_788_livery.py. Movidos para ca:
# o lockup e o ventre verbatim; a matricula e RECONSTRUIDA da mesma arte
# (ilhas C,C,-,B,B de Reg787_E + o F construido das metricas da propria fonte,
# build_788_livery.py secao 6) e pintada direto na caixa FINAL do livery2
# (x 44.40..46.03, z 1.17..1.47, cap 0.30) — o livery2 reamostrava a tinta ja
# pintada, o que nao e re-executavel; pintar da arte e, e cai na mesma caixa.
# NOTA: livery2 somou +0.12 m ao z dos objetos do lockup e SALVOU o blend; os
# objetos ja estao na posicao final — nao somar de novo.


class CascoB788:
    """Grades e rasterizador dos scripts do 787-8 (rings json, ss=3)."""

    def __init__(self):
        import os as _os
        raiz = _os.path.dirname(_os.path.abspath(__file__))
        rings = json.load(open(_os.path.join(raiz, "boeing 787-8/b788_rings.json")))
        self.L_UV = 57.5
        rx = np.array([r["x"] for r in rings])
        self.rx = rx
        self.rzc = np.array([r["zc"] for r in rings])
        self.rrz = np.array([r["rz"] for r in rings])
        self.rry = np.array([r["ry"] for r in rings])
        D = bpy.data
        imT = D.images["LiveryTex"]; imF = D.images["LiveryFac"]
        self.imT, self.imF = imT, imF
        W, H = imT.size
        self.W, self.H = W, H
        X = (np.arange(W) + 0.5) / W * self.L_UV
        TH = (np.arange(H) + 0.5) / H * 2 * math.pi - math.pi
        self.Xg = np.broadcast_to(X, (H, W))
        self.THg = np.broadcast_to(TH[:, None], (H, W))
        ZCg = np.interp(X, rx, self.rzc)[None, :]
        RZg = np.interp(X, rx, self.rrz)[None, :]
        RYg = np.interp(X, rx, self.rry)[None, :]
        self.Zg = ZCg + RZg * np.cos(self.THg)
        self.Yg = RYg * np.sin(self.THg)
        self.THdeg = np.degrees(np.abs(self.THg))
        buf = np.empty(W * H * 4, np.float32)
        imT.pixels.foreach_get(buf)
        self.tex = buf.reshape(H, W, 4)
        buf = np.empty(W * H * 4, np.float32)
        imF.pixels.foreach_get(buf)
        self.fac = buf.reshape(H, W, 4)

    def wedge_mask(self, margin=0.0):
        # a regra do -8 (reparar_echarpe._r_788), com a margem dos scripts
        return ((self.Xg >= 42.68 + 0.992 * self.Zg - margin) &
                (self.THdeg <= 117.0 - 5.2 * (self.Xg - 42.61) + margin * 5) &
                (self.Xg <= 51.05 + 0.3858 * self.Zg + margin))

    def coverage(self, tris2, PA, PB, gate, ss=3):
        H, W = self.H, self.W
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
            grid[j0:j1, i0:i1] |= ~(((d1 < 0) | (d2 < 0) | (d3 < 0)) &
                                    ((d1 > 0) | (d2 > 0) | (d3 > 0)))
        cov = np.zeros((H, W), np.float32)
        jj, ii = np.nonzero(gate)
        if len(ii) == 0:
            return cov
        pa = PA[jj, ii]
        pb = PB[jj, ii]
        acc = np.zeros(len(ii), np.float32)
        for oa in range(ss):
            for ob_ in range(ss):
                sa = pa + ((oa + 0.5) / ss - 0.5) * (self.L_UV / W)
                sb = pb + ((ob_ + 0.5) / ss - 0.5) * 0.018
                ci = ((sa - x0) / (x1 - x0) * nx).astype(int)
                cj = ((sb - y0) / (y1 - y0) * ny).astype(int)
                ok = (ci >= 0) & (ci < nx) & (cj >= 0) & (cj < ny)
                hit = np.zeros(len(ii), bool)
                hit[ok] = grid[cj[ok], ci[ok]]
                acc += hit
        cov[jj, ii] = acc / (ss * ss)
        return cov

    def composite(self, cov, color):
        m = cov > 0.003
        a = cov[m][:, None]
        self.tex[m, :3] = self.tex[m, :3] * (1 - a) + np.asarray(color)[None, :] * a
        for ch in range(3):
            self.fac[m, ch] = np.maximum(self.fac[m, ch], cov[m])
        return int(m.sum())

    @staticmethod
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

    def salvar(self):
        H, W = self.H, self.W
        self.imT.pixels.foreach_set(np.concatenate(
            [self.tex[..., :3], np.ones((H, W, 1), np.float32)],
            axis=2).astype(np.float32).ravel())
        self.imT.update()
        self.imF.pixels.foreach_set(np.concatenate(
            [self.fac[..., :1].repeat(3, axis=2),
             np.ones((H, W, 1), np.float32)], axis=2).astype(np.float32).ravel())
        self.imF.update()
        for im in (self.imT, self.imF):
            if im.packed_file:
                im.pack()
        print("   [salvar] LiveryTex + LiveryFac atualizadas (787-8)")


def _marcas_b788(cb):
    import mathutils
    D = bpy.data
    WHITE = np.array([0.969, 0.976, 0.980], np.float32)
    INDIGO_F = np.array([0.165, 0.000, 0.533], np.float32)
    CORAL_F = np.array([0.929, 0.086, 0.318], np.float32)
    FLANK = (np.abs(np.sin(cb.THg)) > 0.30) & (cb.THdeg < 120)
    PORT = cb.Yg < 0
    STBD = cb.Yg > 0

    def tris_of(ob):
        me = ob.data
        me.calc_loop_triangles()
        mw = mathutils.Matrix.LocRotScale(ob.location, ob.rotation_euler, ob.scale)
        vs = [mw @ v.co for v in me.vertices]
        return [[vs[i] for i in t.vertices] for t in me.loop_triangles]

    # ------------------------------------------- lockup (livery2, verbatim)
    chroma = cb.tex[..., :3].max(axis=2) - cb.tex[..., :3].min(axis=2)
    lum = cb.tex[..., :3].mean(axis=2)
    lum_wht = float(WHITE.mean())
    lockband = (cb.Xg >= 7.20) & (cb.Xg <= 16.20) & FLANK
    m = lockband & (chroma > 0.10)
    cb.tex[m, :3] = 1.0
    cb.fac[m, 0] = cb.fac[m, 1] = cb.fac[m, 2] = 0.0
    ghost = lockband & (chroma < 0.05) & (np.abs(lum - lum_wht) < 0.01) & \
        (cb.fac[..., 0] < 0.02)
    cb.tex[ghost, :3] = 1.0
    print(f"   [apagar]  lockup {int(m.sum())} + ghost {int(ghost.sum())} texels")
    for nm in ("B789_LogoLATAM_E", "B789_LogoLATAM_E_Coral"):
        D.objects[nm].hide_viewport = False
    bpy.context.view_layer.update()
    for nm, color in (("B789_LogoLATAM_E_Coral", CORAL_F), ("B789_LogoLATAM_E", INDIGO_F)):
        tris2 = [[(p.x, p.z) for p in t] for t in tris_of(D.objects[nm])]
        cov = cb.coverage(tris2, cb.Xg, cb.Zg, PORT & FLANK)
        print(f"   [pintar]  lockup port {nm}  {cb.composite(cov, color)} texels")

    def split_symbol_letters(ob, cut=9.0):
        me = ob.data
        me.calc_loop_triangles()
        mw = mathutils.Matrix.LocRotScale(ob.location, ob.rotation_euler, ob.scale)
        vs = [mw @ v.co for v in me.vertices]
        which = {}
        for comp in cb.islands_of(me):
            xs = [vs[i].x for i in comp]
            g = 0 if max(xs) <= cut else 1
            for i in comp:
                which[i] = g
        out = ([], [])
        for t in me.loop_triangles:
            out[which[t.vertices[0]]].append([(vs[i].x, vs[i].z)
                                              for i in t.vertices])
        return out

    def mirror2(tris, axis):
        return [[(2 * axis - x, z) for x, z in t] for t in tris]

    sym_i, let_i = split_symbol_letters(D.objects["B789_LogoLATAM_E"])
    sym_c, let_c = split_symbol_letters(D.objects["B789_LogoLATAM_E_Coral"])
    sx = [x for t in sym_i + sym_c for x, _ in t]
    lx = [x for t in let_i for x, _ in t]
    AX_SYM = 0.5 * (min(sx) + max(sx))
    AX_LET = 0.5 * (min(lx) + max(lx))
    cov = cb.coverage(mirror2(sym_c, AX_SYM), cb.Xg, cb.Zg, STBD & FLANK)
    print(f"   [pintar]  lockup stbd simbolo coral  {cb.composite(cov, CORAL_F)}")
    cov = cb.coverage(mirror2(sym_i, AX_SYM), cb.Xg, cb.Zg, STBD & FLANK)
    print(f"   [pintar]  lockup stbd simbolo indigo {cb.composite(cov, INDIGO_F)}")
    cov = cb.coverage(mirror2(let_i, AX_LET), cb.Xg, cb.Zg, STBD & FLANK)
    print(f"   [pintar]  lockup stbd wordmark       {cb.composite(cov, INDIGO_F)}")
    for nm in ("B789_LogoLATAM_E", "B789_LogoLATAM_E_Coral",
               "B789_LogoLATAM_D", "B789_LogoLATAM_D_Coral"):
        D.objects[nm].hide_viewport = True
        D.objects[nm].hide_render = True

    # -------------------------------- ventre (build_788_livery, verbatim)
    ob = D.objects["LogoBarriga"]
    me = ob.data
    isl = cb.islands_of(me)
    sym_isl = []
    for comp in isl:
        xs = [me.vertices[i].co.x for i in comp]
        if max(xs) < 1.35:
            sym_isl.append(comp)
    keep = set()
    for comp in sym_isl:
        keep |= comp
    me.calc_loop_triangles()
    tris_sym = [[(me.vertices[i].co.x, me.vertices[i].co.y)
                 for i in t.vertices] for t in me.loop_triangles
                if t.vertices[0] in keep]
    obc = D.objects["LogoBarriga_Coral"]
    mec = obc.data
    mec.calc_loop_triangles()
    tris_cor = [[(mec.vertices[i].co.x, mec.vertices[i].co.y)
                 for i in t.vertices] for t in mec.loop_triangles]
    allpts = [p for t in tris_sym + tris_cor for p in t]
    lx0 = min(p[0] for p in allpts); lx1 = max(p[0] for p in allpts)
    ly0 = min(p[1] for p in allpts); ly1 = max(p[1] for p in allpts)
    sW = 3.12 / (lx1 - lx0)
    TX0 = 11.45 - 0.5 * 3.12
    TY0 = -0.5 * (ly1 - ly0) * sW

    def to_belly(tris):
        return [[(TX0 + (px - lx0) * sW, TY0 + (py - ly0) * sW)
                 for px, py in t] for t in tris]

    gate_belly = (np.cos(cb.THg) < -0.35)
    cov = cb.coverage(to_belly(tris_cor), cb.Xg, cb.Yg, gate_belly)
    n1 = cb.composite(cov, CORAL_F)
    cov = cb.coverage(to_belly(tris_sym), cb.Xg, cb.Yg, gate_belly)
    n2 = cb.composite(cov, INDIGO_F)
    print(f"   [pintar]  ventre simbolo  {n1} + {n2} texels")

    # ------------- matricula CC-BBF: arte do stage 2, caixa final do livery2
    reg = D.objects["Reg787_E"]
    me = reg.data
    isl = cb.islands_of(me)

    def ibox(comp):
        xs = [me.vertices[i].co.x for i in comp]
        zs = [me.vertices[i].co.y for i in comp]
        return min(xs), max(xs), min(zs), max(zs)

    isl.sort(key=lambda c: ibox(c)[0])
    vert_isl = {}
    for k, comp in enumerate(isl):
        for i in comp:
            vert_isl[i] = k
    me.calc_loop_triangles()
    tris_by = {k: [] for k in range(len(isl))}
    for t in me.loop_triangles:
        k = vert_isl[t.vertices[0]]
        tris_by[k].append([(me.vertices[i].co.x, me.vertices[i].co.y)
                           for i in t.vertices])
    bb = [ibox(c) for c in isl]
    capH = max(b[3] for b in bb)
    hyph = min(range(len(isl)), key=lambda k: (bb[k][3] - bb[k][2]))
    tbar = bb[hyph][3] - bb[hyph][2]
    seq = [0, 1, 2, 3, 3]                       # C C - B B
    tris2 = []
    for pos, k in enumerate(seq):
        slot = bb[pos]
        dxg = 0.5 * (slot[0] + slot[1]) - 0.5 * (bb[k][0] + bb[k][1])
        tris2 += [[(px + dxg, py) for px, py in t] for t in tris_by[k]]
    s5 = bb[5]
    wF = (s5[1] - s5[0]) * 0.92
    fx0 = s5[0]
    sw = tbar * 1.10
    z0g, z1g = 0.0, capH

    def rect(x0, x1, y0, y1):
        return [[(x0, y0), (x1, y0), (x1, y1)], [(x0, y0), (x1, y1), (x0, y1)]]

    tris2 += rect(fx0, fx0 + sw, z0g, z1g)
    tris2 += rect(fx0, fx0 + wF, z1g - tbar, z1g)
    zm = 0.54 * capH
    tris2 += rect(fx0, fx0 + 0.82 * wF, zm - 0.5 * tbar, zm + 0.5 * tbar)
    xs_l = [p[0] for t in tris2 for p in t]
    ys_l = [p[1] for t in tris2 for p in t]
    glx0, glx1 = min(xs_l), max(xs_l)
    gly0, gly1 = min(ys_l), max(ys_l)
    # caixa FINAL do livery2: x 44.40..46.03, z 1.17..1.47 (cap 0.30, fotos
    # CC-BBB port / CC-BBF stbd) — esticada para preencher, como o resample fez
    REG_X0, REG_X1, REG_Z0, REG_Z1 = 44.40, 46.03, 1.17, 1.47
    kx = (REG_X1 - REG_X0) / (glx1 - glx0)
    kz = (REG_Z1 - REG_Z0) / (gly1 - gly0)
    tris2w = [[(REG_X0 + (px - glx0) * kx, REG_Z0 + (py - gly0) * kz)
               for px, py in t] for t in tris2]
    inw = cb.wedge_mask(-0.12)
    # erase: o retangulo inteiro volta a indigo chapado (livery2 FLAT box)
    FLAT = (cb.Xg >= 44.20) & (cb.Xg <= 47.10) & (cb.Zg >= 0.55) & \
        (cb.Zg <= 1.45) & inw
    for tag2, side in (("port", PORT), ("stbd", STBD)):
        f = FLAT & side
        cb.tex[f, :3] = INDIGO_F
        cb.fac[f, 0] = cb.fac[f, 1] = cb.fac[f, 2] = 1.0
        gate = side & (np.abs(np.sin(cb.THg)) > 0.25)
        t2 = tris2w if tag2 == "port" else \
            [[(REG_X0 + REG_X1 - px, pz) for px, pz in t] for t in tris2w]
        cov = cb.coverage(t2, cb.Xg, cb.Zg, gate)
        n = cb.composite(cov, WHITE)
        print(f"   [pintar]  matricula CC-BBF {tag2}  {n} texels")


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
    if tag == "b788":
        for o in bpy.data.objects:
            o.hide_viewport = False
        bpy.context.view_layer.update()
        cb = CascoB788()
        print(f"[b788] legado 787-8  L={cb.L_UV}  tex {cb.W}x{cb.H}")
        _marcas_b788(cb)
        cb.salvar()
        bpy.ops.wm.save_mainfile()
        print("[b788] blend saved")
        return
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
    if "marcas" in tarefas and tag in LEGADO_A320:
        # as marcas legadas SS2 (ventre, matricula, titulo) leem as imagens ja
        # salvas pelo Casco e compoem por cima — segunda passada, mesma corrida
        rings_rel, luv, fn = LEGADO_A320[tag]
        ca = CascoA320(rings_rel, luv)
        print(f"[{tag}] legado A320  L={luv}  tex {ca.W}x{ca.H}")
        fn(ca)
        ca.salvar()
    if "marcas" in tarefas and tag in LEGADO_A321:
        luv, fn = LEGADO_A321[tag]
        cn = CascoA321(luv)
        print(f"[{tag}] legado A321  L={luv}  tex {cn.W}x{cn.H}")
        fn(cn)
        cn.imT.pixels.foreach_set(cn.tex.astype(np.float32).ravel())
        cn.imT.update()
        cn.imF.pixels.foreach_set(cn.fac.astype(np.float32).ravel())
        cn.imF.update()
        for im in (cn.imT, cn.imF):
            if im.packed_file:
                im.pack()
        print("   [salvar] LiveryTex + LiveryFac atualizadas (A321)")
    bpy.ops.wm.save_mainfile()
    print(f"[{tag}] blend saved")


if __name__ == "__main__":
    main()
