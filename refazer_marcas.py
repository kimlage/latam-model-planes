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
    # --- titulo 'AIRBUS A319': DESDE 2026-08-27 pintado pela tarefa
    # `titulo` (fazer_titulo_a319, ponte moderna) com arte SVG real — ilhas
    # do MarkAirbusNeo_E + '1' do airbus_a321neo_logo.svg + '9' do bojo do
    # '0'. O bloco legado (ilhas + '1' da haste do I + '9' de aneis NSEG)
    # que vivia aqui pintava uma aproximacao em indigo e foi APOSENTADO —
    # rodar `-- a319 lockup marcas titulo` reproduz a textura embarcada.
    print("   [titulo] a319: pintado pela tarefa 'titulo' (arte SVG); "
          "bloco legado aposentado")


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


# ========================================== IMPRESSAO DE SUPERFICIE 2026-08-27
# A rodada da impressao: linhas de painel e cutlines de comandos em (x,theta),
# matricula sob a asa, linha do leme na deriva. TUDO por este arquivo (o pintor
# unico); os builders nao pintam nada disto.
#
# LEI DA SUTILEZA (medida, nao estimada): tres faixas limpas da fuselagem em
# refs/20251011_LATAM_PT-MUC_EGLL.jpg (6016 px, flanco ao sol) dao juntas
# circunferenciais lendo como quedas de luminancia de 0.8-3.8% (tipico 1-2.5%);
# so portas/recortes profundos passam de 5%. A tinta abaixo compoe
# ef' = ef*(1-a*cov) + cor*a*cov com a=ALPHA_*; com COR_PRINT sobre o branco
# do casco (#E6E7EA) a queda resultante e ~0.83*a — a tabela:
ALPHA_JUNTA = 0.032      # -> ~2.7% de queda (dentro do 1-3.8% medido)
ALPHA_RADOME = 0.055     # a junta do radome le mais forte (painel dieletrico)
ALPHA_CARENAGEM = 0.045  # costura da carenagem ventral no casco
ALPHA_APU = 0.045        # anel da parede de fogo do APU
ALPHA_LEME = 0.09        # linha do leme sobre a arte da deriva (multiplicativa)
COR_PRINT = (0x55, 0x57, 0x5B)


def _sock(node, ident, saida=False):
    for sk in (node.outputs if saida else node.inputs):
        if sk.identifier == ident:
            return sk
    raise KeyError(ident + " nao existe em " + node.name)


class Impressao:
    """Linhas de painel sobre a LiveryTex, pela ponte moderna (Casco).
    Marca NOVA e autorada na ponte da malha — a regra de REBUILD.md sobre
    pontes legadas vale para marcas que ja existiam, nao para estas."""

    def __init__(self, cs):
        self.cs = cs
        self.cor = np.array(COR_PRINT, np.float32) / 255.0

    def _compor(self, r0, r1, c0, c1, cov, alpha, nome):
        cs = self.cs
        ef = cs.efetiva(r0, r1, c0, c1)
        a = (cov * alpha)[..., None]
        novo = ef * (1 - a) + self.cor[None, None, :] * a
        cs.escrever(r0, r1, c0, c1, novo, cov > 0.02)
        n = int((cov > 0.02).sum())
        print(f"   [imprimir] {nome:28} {n:6d} texels  alpha {alpha:.3f}")
        return n

    def anel(self, x_m, alpha, larg_m, nome):
        """Junta circunferencial: coluna de texels na estacao x, todas as
        linhas. A junta real cruza tinta, janela e cunha — e na foto tambem."""
        cs = self.cs
        cc = float(cs.col_of_x(x_m))
        half = 0.5 * larg_m / (cs.L / cs.W)
        c0 = max(0, int(math.floor(cc - half - 1)))
        c1 = min(cs.W - 1, int(math.ceil(cc + half + 1)))
        cols = np.arange(c0, c1 + 1, dtype=float)
        cov1 = np.clip(half + 0.5 - np.abs(cols - cc), 0.0, 1.0)
        cov = np.broadcast_to(cov1[None, :], (cs.H, c1 - c0 + 1)).copy()
        return self._compor(0, cs.H - 1, c0, c1, cov, alpha, nome)

    def polilinha(self, xs, ths_deg, alpha, larg_m, nome, lados=(-1, 1)):
        """Linha em (x, theta): por coluna, theta(x) interpolado; cobertura
        vertical em queda linear sobre larg_m convertido a linhas locais."""
        cs = self.cs
        xs = np.asarray(xs, float)
        ths = np.radians(np.asarray(ths_deg, float))
        c0 = max(0, int(cs.col_of_x(xs.min())))
        c1 = min(cs.W - 1, int(cs.col_of_x(xs.max())))
        if c1 <= c0:
            return 0
        colx = cs.x_of_col(np.arange(c0, c1 + 1))
        thx = np.interp(colx, xs, ths)
        n = 0
        for lado in lados:
            rc = cs.row_of_th(lado * thx)
            # metros de arco por linha de texel, na estacao media
            xm = float(colx.mean())
            s1 = float(cs.arc(np.array([xm]), np.array([math.pi * 0.98]))[0])
            m_por_linha = abs(s1) * 2 / (cs.H * 0.98)
            half = 0.5 * larg_m / max(m_por_linha, 1e-6)
            r0 = max(0, int(np.floor(rc.min() - half - 1)))
            r1 = min(cs.H - 1, int(np.ceil(rc.max() + half + 1)))
            rows = np.arange(r0, r1 + 1, dtype=float)
            cov = np.clip(half + 0.5 - np.abs(rows[:, None] - rc[None, :]),
                          0.0, 1.0)
            n += self._compor(r0, r1, c0, c1, cov, alpha,
                              f"{nome} {'E' if lado < 0 else 'D'}")
        return n

    def costura_carenagem(self, alpha=None, nome="costura carenagem"):
        """A costura da carenagem ventral LIDA DA PROPRIA MALHA: por faixa de
        x, o vertice da carenagem mais proximo da crista (menor |theta| do
        lado) e a borda; a polilinha detectada e pintada no casco."""
        ob = bpy.data.objects.get("BellyFairing")
        if ob is None:
            print("   [imprimir] costura: sem BellyFairing, pulando")
            return 0
        cs = self.cs
        M = ob.matrix_world
        P = np.array([tuple(M @ v.co) for v in ob.data.vertices])
        # theta do vertice contra a secao local do casco
        i = cs._i(P[:, 0])
        th = np.empty(len(P))
        for k in range(len(P)):
            e = cs.est[i[k]]
            zz = e[3]; tt = e[1]
            # z(theta) monotono por metade; usar o lado do vertice
            m = tt >= 0 if P[k, 1] >= 0 else tt <= 0
            th[k] = abs(np.interp(P[k, 2], zz[m][np.argsort(zz[m])],
                                  np.abs(tt[m])[np.argsort(zz[m])]))
        xb = np.arange(math.floor(P[:, 0].min()), math.ceil(P[:, 0].max()), 0.5)
        xs, ts = [], []
        for a, b in zip(xb[:-1], xb[1:]):
            m = (P[:, 0] >= a) & (P[:, 0] < b)
            if m.sum() < 3:
                continue
            xs.append(0.5 * (a + b)); ts.append(np.degrees(th[m].min()))
        if len(xs) < 4:
            print("   [imprimir] costura: malha insuficiente")
            return 0
        return self.polilinha(xs, ts, alpha or ALPHA_CARENAGEM, 0.04, nome)


# juntas: estacoes citadas dos geradores de PanelBump por tipo (a mesma
# tabela que ja embarcou como BUMP vira agora impressao sutil de COR);
# a320ceo/neo: padrao do builder do A319 + deslocamento dos plugs do ACAP
# (a tabela do A319 e a unica da familia com builder proprio; o PanelBump
# dos dois A320 estava DESEMPACOTADO no master — regenerado nesta rodada).
_J_A320 = [1.55, 2.65, 4.4, 5.96, 6.96, 8.0, 10.0, 12.0, 14.0, 16.0, 18.0,
           20.0, 22.0, 24.0, 26.04, 29.04, 32.04, 35.04, 36.7]
_J_A321 = ([0.96, 1.79, 2.65, 3.51, 4.4, 5.3, 6.96] +
           [8.9 + 1.99 * k for k in range(12)] +
           [33.69, 35.6, 37.4, 39.2, 41.0, 42.5])
IMPRESSAO = {
    "a319": dict(juntas=[2.65, 4.4, 5.96, 6.96, 8.0, 10.0, 12.0, 14.0, 16.0,
                         18.0, 20.0, 22.27, 25.27, 28.27, 31.27, 33.0],
                 radome=1.55, apu=None, carenagem=True),
    "a320ceo": dict(juntas=_J_A320[1:], radome=1.55, apu=None, carenagem=True,
                    pb_regen=True),
    "a320neo": dict(juntas=_J_A320[1:], radome=1.55, apu=None, carenagem=True,
                    pb_regen=True),
    "a321ceo": dict(juntas=_J_A321[1:], radome=0.96, apu=None, carenagem=True),
    "a321neo": dict(juntas=_J_A321[1:], radome=0.96, apu=None, carenagem=True),
    "b763er": dict(juntas=[10.3, 16.8, 23.3, 29.8, 36.3, 42.8, 47.5],
                   radome=2.0, apu=51.8, carenagem=True),
    "b763f": dict(juntas=[10.3, 16.8, 23.3, 29.8, 36.3, 42.8, 47.5],
                  radome=2.0, apu=51.8, carenagem=True),
    "b763bcf": dict(juntas=[10.3, 16.8, 23.3, 29.8, 36.3, 42.8, 47.5],
                    radome=2.0, apu=51.8, carenagem=True),
    "b77w": dict(juntas=[10.0, 22.6, 33.5, 44.9, 51.5, 56.0, 62.0, 68.0],
                 radome=2.05, apu=71.5, carenagem=True),
    # 787: fuselagem composita — so as emendas de barril. As do -9 foram
    # MEDIDAS na foto da CC-BGG (MAD, 6000 px, tres faixas de luminancia
    # concordantes; candidatos coincidentes com portas do spec descartados):
    # fracoes 0.228/0.307/0.423/0.606 do nariz->cauda = x 14.3/19.3/26.6/38.1.
    # As do -8 sao a MESMA tabela deslocada pelos plugs da derivacao (-3.05
    # avante da asa, -3.05 atras), declarado. Radome JA PINTADO por nose_art.
    "b788": dict(juntas=[11.25, 16.25, 23.55, 35.05], radome=None,
                 apu=54.2, carenagem=True, alpha_juntas=0.022),
    "b789": dict(juntas=[14.3, 19.3, 26.6, 38.1], radome=None,
                 apu=60.5, carenagem=True, alpha_juntas=0.022),
}


def fazer_impressao(cs, tag):
    cfg = IMPRESSAO[tag]
    imp = Impressao(cs)
    a_j = cfg.get("alpha_juntas", ALPHA_JUNTA)
    for xj in cfg["juntas"]:
        imp.anel(xj, a_j, 0.030, f"junta x={xj:.2f}")
    if cfg.get("radome"):
        imp.anel(cfg["radome"], ALPHA_RADOME, 0.045, "junta do radome")
    if cfg.get("apu"):
        imp.anel(cfg["apu"], ALPHA_APU, 0.040, "anel do APU")
    if cfg.get("carenagem"):
        imp.costura_carenagem()
    if cfg.get("pb_regen"):
        _panelbump_a320()


def _panelbump_a320():
    """A320ceo/neo: o PanelBump do master estava sem pixels (packed=False).
    Regenerado no padrao do builder do A319 (juntas 0.42, lap joints 0.46
    sobre 0.5 neutro) com a tabela _J_A320, e EMPACOTADO."""
    pb = bpy.data.images["PanelBump"]
    wp, hp = pb.size
    fus = bpy.data.objects.get("Fuselagem")
    xs = [v.co.x for v in fus.data.vertices]
    L = max(xs) - min(xs)
    L = 38.0 if L > 36.0 else 34.2
    arr = np.full((hp, wp), 0.5, np.float32)
    xs_pb = (np.arange(wp) + 0.5) / wp * L
    for j in [1.55] + _J_A320[1:]:
        col = int(np.argmin(np.abs(xs_pb - j)))
        arr[:, max(col - 1, 0):col + 1] = 0.42
    for vv in (0.36, 0.30, 0.64, 0.70, 0.14, 0.86):
        row = int(vv * hp)
        arr[row:row + 1, :] = 0.46
    out = np.empty((hp, wp, 4), np.float32)
    out[..., 0] = arr; out[..., 1] = arr; out[..., 2] = arr; out[..., 3] = 1.0
    pb.pixels.foreach_set(out.ravel())
    pb.pack()
    print(f"   [imprimir] PanelBump regenerado e empacotado (L={L})")


# ------------------------------------------------------------------ asa
# Linhas de comando da asa + matricula sob a asa DIREITA.
#
# A LEI DA MATRICULA SOB A ASA (fotografada, nao suposta): quatro quadros de
# tres tipos mostram a mesma convencao — a matricula vive sob a asa DIREITA
# (estibordo), corre ao longo da envergadura lendo da raiz para a ponta, com o
# topo dos glifos para o bordo de ataque, logo a frente da linha do flap/
# aileron: PT-MUG (ref_PT-MUG_2022_FRA.jpg), CC-BGG (ref_bgg_mad23.jpg),
# N536LA (ref_N536LA_ldg26.jpg), CC-CXE (ref_CC-CXE_appr4.jpg). Vista de
# baixo com o BA para cima, a leitura raiz->ponta e da esquerda para a
# direita — pintar em (y, -x) SEM espelho reproduz isso (verificado no gate
# CamBarriga).
COR_REG_ASA = (0x24, 0x26, 0x2B)   # nas fotos a tinta le como grafite escuro


class Asa:
    """Textura AsaLinhas (plan-form (x,y) -> UVAsa) + shader CinzaAsa.
    R = cutlines dos dois lados, G = spoilers (so extradorso),
    B = matricula (so intradorso). Cria a infraestrutura onde falta
    (familia A320) e repara onde ela morreu (ver cada master)."""

    W = H = 2048

    def __init__(self, nomes_asa, dominio=None):
        D = bpy.data
        self.obs = [D.objects[n] for n in nomes_asa if D.objects.get(n)]
        if not self.obs:
            raise SystemExit(f"asa nao encontrada: {nomes_asa}")
        # dominio planar: existente (ajuste por minimos quadrados da UV
        # embarcada) ou novo a partir da caixa do proprio conjunto
        uv_existente = all(o.data.uv_layers.get("UVAsa") for o in self.obs)
        if uv_existente and dominio is None:
            X, Y, U, V = [], [], [], []
            for o in self.obs:
                me = o.data
                uvl = me.uv_layers["UVAsa"].data
                M = o.matrix_world
                for poly in me.polygons:
                    for li in poly.loop_indices:
                        co = M @ me.vertices[me.loops[li].vertex_index].co
                        u, v = uvl[li].uv
                        X.append(co.x); Y.append(co.y); U.append(u); V.append(v)
            X = np.array(X); Y = np.array(Y)
            U = np.array(U); V = np.array(V)
            au = np.polyfit(X, U, 1); av = np.polyfit(Y, V, 1)
            self.X0 = -au[1] / au[0]; self.DX = 1.0 / au[0]
            self.Y0 = -av[1] / av[0]; self.DY = 1.0 / av[0]
            print(f"   [asa] dominio UVAsa embarcado: x {self.X0:.2f}+{self.DX:.2f}"
                  f"  y {self.Y0:.2f}+{self.DY:.2f}")
        else:
            if dominio is None:
                P = self._verts()
                x0 = math.floor(P[:, 0].min() - 1)
                x1 = math.ceil(P[:, 0].max() + 1)
                ym = math.ceil(np.abs(P[:, 1]).max() + 1)
                dominio = (x0, x1 - x0, -ym, 2 * ym)
            self.X0, self.DX, self.Y0, self.DY = dominio
            for o in self.obs:
                me = o.data
                uva = me.uv_layers.get("UVAsa") or me.uv_layers.new(name="UVAsa")
                M = o.matrix_world
                for loop in me.loops:
                    co = M @ me.vertices[loop.vertex_index].co
                    uva.data[loop.index].uv = ((co.x - self.X0) / self.DX,
                                               (co.y - self.Y0) / self.DY)
            print(f"   [asa] UVAsa criado: x {self.X0}+{self.DX}  "
                  f"y {self.Y0}+{self.DY}")
        img = D.images.get("AsaLinhas")
        if img is None:
            img = D.images.new("AsaLinhas", self.W, self.H, alpha=False,
                               float_buffer=False)
            img.colorspace_settings.name = "Non-Color"
            buf = np.zeros((self.H, self.W, 4), np.float32)
            buf[..., 3] = 1.0
            img.pixels.foreach_set(buf.ravel())
            print("   [asa] AsaLinhas criada (2048, zerada)")
        self.img = img
        self.W, self.H = img.size
        buf = np.empty(self.W * self.H * 4, np.float32)
        img.pixels.foreach_get(buf)
        self.arr = buf.reshape(self.H, self.W, 4)

    def _verts(self, so_cinza=False):
        out = []
        for o in self.obs:
            me = o.data
            M = o.matrix_world
            if so_cinza:
                idx = {i for i, ms in enumerate(o.material_slots)
                       if ms.material and ms.material.name.startswith("CinzaAsa")}
                vs = set()
                for p in me.polygons:
                    if p.material_index in idx:
                        vs.update(p.vertices)
                out += [tuple(M @ me.vertices[i].co) for i in vs]
            else:
                out += [tuple(M @ v.co) for v in me.vertices]
        return np.array(out)

    # --- bordos da propria malha ---------------------------------------
    def bordos(self):
        P = self._verts(so_cinza=True)
        ya = np.abs(P[:, 1])
        bins = np.arange(0, ya.max() + 0.4, 0.4)
        ys, le, te = [], [], []
        for a, b in zip(bins[:-1], bins[1:]):
            m = (ya >= a) & (ya < b)
            if m.sum() < 2:
                continue
            ys.append(0.5 * (a + b))
            le.append(P[m, 0].min())
            te.append(P[m, 0].max())
        self.ys = np.array(ys); self.le = np.array(le); self.te = np.array(te)
        self.y_ponta = float(self.ys.max())
        # raiz EXPOSTA: o mesh entra na fuselagem; a lei de fracao de
        # envergadura conta da lateral da carenagem (~0.12 da meia-envergadura)
        self.y_raiz = max(float(self.ys.min()), 0.12 * self.y_ponta)
        return self.ys, self.le, self.te

    def _le(self, y):
        return np.interp(np.abs(y), self.ys, self.le)

    def _te(self, y):
        return np.interp(np.abs(y), self.ys, self.te)

    # --- desenho ---------------------------------------------------------
    def _px(self, x, y):
        return ((x - self.X0) / self.DX * self.W,
                (y - self.Y0) / self.DY * self.H)

    def seg(self, x0, y0, x1, y1, canal, forca=1.0, esp_px=2):
        n = int(max(abs(x1 - x0), abs(y1 - y0)) * 30) + 2
        for i in range(n + 1):
            t = i / n
            px, py = self._px(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
            px, py = int(px), int(py)
            h = esp_px // 2
            if 0 <= px < self.W and 0 <= py < self.H:
                self.arr[max(0, py - h):py + h + 1,
                         max(0, px - h):px + h + 1, canal] = \
                    np.maximum(self.arr[max(0, py - h):py + h + 1,
                                        max(0, px - h):px + h + 1, canal], forca)

    def linhas_familia_a320(self):
        """Cutlines da familia A320, lidas do plano do ACAP p.45 (600 dpi)
        em FRACOES de envergadura (raiz da carenagem -> ponta), livres de
        calibracao: validadas pelos pods de flap-track (0.211/0.417/0.652 ->
        |y| 5.3/8.6/12.35 contra 4.95/8.48/12.21 lidos em vetor, QA-BACKLOG).
        flap A/B 0.265; flap/aileron 0.569; aileron ext 0.946; slats: raiz
        0.142, vao do pylon 0.304-0.324, cortes 0.436/0.588/0.740, fim 0.892."""
        self.bordos()
        yr, yp = self.y_raiz, self.y_ponta
        span = yp - yr

        def Y(eta):
            return yr + eta * span

        for sgn in (-1, 1):
            # bordo de fuga: linha do cove + cortes chordwise
            zonas = [(0.01, 0.265, 0.70), (0.265, 0.569, 0.70),
                     (0.569, 0.946, 0.68)]
            for (e0, e1, cf) in zonas:
                y0, y1 = sgn * Y(e0), sgn * Y(e1)
                xc0 = self._le(y0) + (self._te(y0) - self._le(y0)) * cf
                xc1 = self._le(y1) + (self._te(y1) - self._le(y1)) * cf
                self.seg(xc0, y0, xc1, y1, 0, 1.0, 2)
                for yy, xc in ((y0, xc0), (y1, xc1)):
                    self.seg(xc, yy, self._te(yy), yy, 0, 1.0, 3)
            # spoilers (so extradorso): 1 interno + 4 entre kink e aileron
            for (e0, e1) in ((0.05, 0.14), (0.30, 0.36), (0.36, 0.43),
                             (0.43, 0.50), (0.50, 0.565)):
                for cf in (0.57, 0.70):
                    self.seg(self._le(sgn * Y(e0)) + (self._te(sgn * Y(e0)) -
                             self._le(sgn * Y(e0))) * cf, sgn * Y(e0),
                             self._le(sgn * Y(e1)) + (self._te(sgn * Y(e1)) -
                             self._le(sgn * Y(e1))) * cf, sgn * Y(e1), 1, 1.0, 2)
                for ee in (e0, e1):
                    y = sgn * Y(ee)
                    xa = self._le(y) + (self._te(y) - self._le(y)) * 0.57
                    xb = self._le(y) + (self._te(y) - self._le(y)) * 0.70
                    self.seg(xa, y, xb, y, 1, 1.0, 2)
            # slats: linha da fenda a 0.45 m do BA + cortes
            cortes = [0.142, 0.304, 0.324, 0.436, 0.588, 0.740, 0.892]
            for (e0, e1) in ((0.142, 0.304), (0.324, 0.436), (0.436, 0.588),
                             (0.588, 0.740), (0.740, 0.892)):
                y0, y1 = sgn * Y(e0), sgn * Y(e1)
                self.seg(self._le(y0) + 0.45, y0, self._le(y1) + 0.45, y1,
                         0, 0.85, 2)
            for ee in cortes:
                y = sgn * Y(ee)
                self.seg(self._le(y), y, self._le(y) + 0.45, y, 0, 0.85, 2)
        print("   [asa] cutlines familia A320 desenhadas (R/G)")

    def linhas_777(self):
        """Cutlines do 777-300ER, medidas no intradorso da PT-MUG
        (ref_PT-MUG_2022_FRA.jpg) com as canoas do modelo como ancoras
        (y 9.0/14.5/19.5); declarado +-1 m. Flaperon atras do motor
        (y 8.0-11.0), flap interno 3.9-8.0, flap externo 11.0-24.6,
        aileron 24.6-29.6; slats com vao no pylon (7.5-11.7) e cortes a
        cada ~4 m. Spoilers deferidos (sem foto do extradorso)."""
        self.bordos()

        def cove(y, cf):
            return self._le(y) + (self._te(y) - self._le(y)) * cf

        for sgn in (-1, 1):
            zonas = [(3.9, 8.0, 0.72), (8.0, 11.0, 0.70), (11.0, 24.6, 0.72),
                     (24.6, 29.6, 0.68)]
            for (y0, y1, cf) in zonas:
                a, b = sgn * y0, sgn * y1
                self.seg(cove(a, cf), a, cove(b, cf), b, 0, 1.0, 2)
                for yy in (a, b):
                    self.seg(cove(yy, cf), yy, self._te(yy), yy, 0, 1.0, 3)
            for (y0, y1) in ((2.5, 7.5), (11.7, 15.7), (15.7, 19.7),
                             (19.7, 23.7), (23.7, 27.7), (27.7, 31.4)):
                a, b = sgn * y0, sgn * y1
                self.seg(self._le(a) + 0.65, a, self._le(b) + 0.65, b,
                         0, 0.85, 2)
                for yy in (y0, y1):
                    y = sgn * yy
                    self.seg(self._le(y), y, self._le(y) + 0.65, y, 0, 0.85, 2)
        print("   [asa] cutlines 777 desenhadas (R)")

    def matricula(self, tris, bb, y0, y1, folga_te=0.20):
        """Matricula sob a asa DIREITA: baseline paralela a linha do cove
        (te - folga), leitura raiz->ponta, topo dos glifos para o BA.
        O canal B pertence SO a matricula: zera-lo antes torna a op
        idempotente e re-posicionavel."""
        if not hasattr(self, "ys"):
            self.bordos()
        self.arr[..., 2] = 0.0
        ax, bx, ay, by = bb
        s = (y1 - y0) / max(bx - ax, 1e-9)
        cap = (by - ay) * s
        # baseline: reta entre os dois pontos do cove
        cove0 = self._te(y0) - folga_te
        cove1 = self._te(y1) - folga_te
        t = np.array([y1 - y0, cove1 - cove0]); t = t / np.hypot(*t)
        nrm = np.array([-t[1], t[0]])       # aponta para -x (BA)
        if nrm[1] > 0:
            nrm = -nrm
        P0 = np.array([y0, cove0])
        polys = []
        for tri in tris:
            p = []
            for X, Yv in tri:
                q = P0 + t * (X - ax) * s + nrm * (Yv - ay) * s
                p.append((q[0], q[1]))      # (y, x)
            polys.append(p)
        # rasterizar em (y, x) com SS2
        SS2 = 2
        ys_ = [p[0] for tri in polys for p in tri]
        xs_ = [p[1] for tri in polys for p in tri]
        u0 = int((min(ys_) - self.Y0) / self.DY * self.H) - 2
        u1 = int((max(ys_) - self.Y0) / self.DY * self.H) + 2
        v0 = int((min(xs_) - self.X0) / self.DX * self.W) - 2
        v1 = int((max(xs_) - self.X0) / self.DX * self.W) + 2
        nr, nc = u1 - u0 + 1, v1 - v0 + 1
        gy = self.Y0 + (u0 + (np.arange(nr * SS2) + 0.5) / SS2 - 0.5) * \
            (self.DY / self.H)
        gx = self.X0 + (v0 + (np.arange(nc * SS2) + 0.5) / SS2 - 0.5) * \
            (self.DX / self.W)
        GY = gy[:, None].repeat(nc * SS2, 1)
        GX = gx[None, :].repeat(nr * SS2, 0)
        cov = _raster([[(p[1], p[0]) for p in tri] for tri in polys], GX, GY)
        cov = cov.reshape(nr, SS2, nc, SS2).mean((1, 3)).astype(np.float32)
        m = cov > 0
        self.arr[u0:u1 + 1, v0:v1 + 1, 2] = np.maximum(
            self.arr[u0:u1 + 1, v0:v1 + 1, 2], cov)
        print(f"   [asa] matricula sob a asa D: y {y0:.2f}..{y1:.2f}  "
              f"cap {cap:.3f} m  {int(m.sum())} texels (canal B)")
        return cap

    # --- shader ----------------------------------------------------------
    def shader(self):
        """Garante o ramo AL_* em CinzaAsa (padrao do 777) + o ramo B da
        matricula (AL2_*, so intradorso). Idempotente: acha nos por nome."""
        D = bpy.data
        mats = [m for m in D.materials
                if m.name.startswith("CinzaAsa") and m.use_nodes and any(
                    ms.material == m for o in self.obs for ms in o.material_slots)]
        for mat in mats:
            nt = mat.node_tree
            nodes, links = nt.nodes, nt.links
            bsdf = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
            out = next(n for n in nodes if n.type == 'OUTPUT_MATERIAL')
            if not any(l.to_node == out for l in links):
                links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

            novos = set()

            def no(nome, tipo, **kw):
                n = nodes.get(nome)
                if n is None:
                    n = nodes.new(tipo)
                    n.name = nome
                    novos.add(nome)
                    for k, v in kw.items():
                        setattr(n, k, v)
                return n

            uv = no("AL_uv", "ShaderNodeUVMap")
            uv.uv_map = "UVAsa"
            tx = no("AL_tex", "ShaderNodeTexImage")
            tx.image = self.img
            tx.image.colorspace_settings.name = "Non-Color"
            tx.extension = 'EXTEND'
            sep = no("AL_sep", "ShaderNodeSeparateColor")
            geo = no("AL_geo", "ShaderNodeNewGeometry")
            sepn = no("AL_sepn", "ShaderNodeSeparateXYZ")
            mr = no("AL_mr", "ShaderNodeMapRange")
            mul = no("AL_mul", "ShaderNodeMath", operation='MULTIPLY')
            add = no("AL_add", "ShaderNodeMath", operation='ADD')
            mix = no("AL_mix", "ShaderNodeMix", data_type='RGBA')
            if "AL_mr" in novos:
                mr.inputs["From Min"].default_value = 0.1
                mr.inputs["From Max"].default_value = 0.4
            if "AL_mix" in novos:
                base = tuple(bsdf.inputs["Base Color"].default_value)
                _sock(mix, "A_Color").default_value = base
            # forca de linha da FROTA: nos Boeing embarcados o AL_mix leva
            # B = 0.42 x A (lido no proprio 767/777). So escrever quando o no
            # e novo ou carrega outra forca (a rodada chegou a criar 0.70x);
            # o B embarcado dos Boeing (0.329,0.333,0.36) fica intocado.
            aa = tuple(_sock(mix, "A_Color").default_value)
            bb_ = tuple(_sock(mix, "B_Color").default_value)
            if "AL_mix" in novos or abs(bb_[0] - aa[0] * 0.42) > 0.05:
                _sock(mix, "B_Color").default_value = (aa[0] * 0.42,
                                                       aa[1] * 0.42,
                                                       aa[2] * 0.42, 1.0)
            links.new(uv.outputs["UV"], tx.inputs["Vector"])
            links.new(tx.outputs["Color"], sep.inputs["Color"])
            links.new(geo.outputs["Normal"], sepn.inputs["Vector"])
            links.new(sepn.outputs["Z"], mr.inputs["Value"])
            links.new(sep.outputs["Green"], mul.inputs[0])
            links.new(mr.outputs["Result"], mul.inputs[1])
            links.new(sep.outputs["Red"], add.inputs[0])
            links.new(mul.outputs["Value"], add.inputs[1])
            links.new(add.outputs["Value"], _sock(mix, "Factor_Float"))
            # ramo B: matricula, so faces com normal para baixo
            lt = no("AL2_baixo", "ShaderNodeMath", operation='LESS_THAN')
            lt.inputs[1].default_value = -0.2
            m2 = no("AL2_mul", "ShaderNodeMath", operation='MULTIPLY')
            mix2 = no("AL2_mix", "ShaderNodeMix", data_type='RGBA')
            if "AL2_mix" in novos:
                lin = [(c / 255.0 / 12.92) if c / 255.0 <= 0.04045 else
                       (((c / 255.0 + 0.055) / 1.055) ** 2.4)
                       for c in COR_REG_ASA]
                _sock(mix2, "B_Color").default_value = (lin[0], lin[1],
                                                       lin[2], 1.0)
            links.new(sepn.outputs["Z"], lt.inputs[0])
            links.new(sep.outputs["Blue"], m2.inputs[0])
            links.new(lt.outputs["Value"], m2.inputs[1])
            links.new(_sock(mix, "Result_Color", saida=True), _sock(mix2, "A_Color"))
            links.new(m2.outputs["Value"], _sock(mix2, "Factor_Float"))
            links.new(_sock(mix2, "Result_Color", saida=True),
                      bsdf.inputs["Base Color"])
            print(f"   [asa] shader {mat.name}: ramo AL/AL2 garantido")

    def salvar(self):
        self.img.pixels.foreach_set(self.arr.ravel())
        self.img.update()
        self.img.pack()
        print("   [asa] AsaLinhas salva e empacotada")


# ------------------------------------------------------------------ deriva
class Deriva:
    """Linha do leme nas texturas FinSashE/D, pela UV da propria deriva."""

    def __init__(self):
        D = bpy.data
        self.ob = D.objects["Deriva"]
        me = self.ob.data
        uvl = me.uv_layers.active.data
        M = self.ob.matrix_world
        X, Z, U, V = [], [], [], []
        for poly in me.polygons:
            for li in poly.loop_indices:
                co = M @ me.vertices[me.loops[li].vertex_index].co
                u, v = uvl[li].uv
                X.append(co.x); Z.append(co.z); U.append(u); V.append(v)
        A = np.stack([X, Z, np.ones(len(X))], 1)
        self.cu, ru, *_ = np.linalg.lstsq(A, np.array(U), rcond=None)[:2]
        self.cv, rv, *_ = np.linalg.lstsq(A, np.array(V), rcond=None)[:2]
        P = np.array([tuple(M @ v.co) for v in me.vertices])
        zb = np.arange(P[:, 2].min(), P[:, 2].max(), 0.25)
        zs, le, te = [], [], []
        for a, b in zip(zb[:-1], zb[1:]):
            m = (P[:, 2] >= a) & (P[:, 2] < b)
            if m.sum() < 2:
                continue
            zs.append(0.5 * (a + b)); le.append(P[m, 0].min())
            te.append(P[m, 0].max())
        self.zs = np.array(zs); self.le = np.array(le); self.te = np.array(te)

    def leme(self, frac, z0f=0.04, z1f=0.97, alpha=ALPHA_LEME, esp_px=2):
        """Linha da charneira do leme: x = te - frac*(te-le), da raiz a ponta.
        frac lida na foto do proprio tipo (citada na tabela EMPENAGEM)."""
        D = bpy.data
        zr = self.zs.min() + z0f * (self.zs.max() - self.zs.min())
        zt = self.zs.min() + z1f * (self.zs.max() - self.zs.min())
        zz = np.linspace(zr, zt, 200)
        xle = np.interp(zz, self.zs, self.le)
        xte = np.interp(zz, self.zs, self.te)
        xh = xte - frac * (xte - xle)
        for nome in ("FinSashE", "FinSashD"):
            img = D.images.get(nome)
            if img is None:
                continue
            W, H = img.size
            buf = np.empty(W * H * 4, np.float32)
            img.pixels.foreach_get(buf)
            arr = buf.reshape(H, W, 4)
            n = 0
            for x, z in zip(xh, zz):
                u = self.cu[0] * x + self.cu[1] * z + self.cu[2]
                v = self.cv[0] * x + self.cv[1] * z + self.cv[2]
                px, py = int(u * W), int(v * H)
                h = esp_px // 2
                if 0 <= px < W and 0 <= py < H:
                    sl = arr[max(0, py - h):py + h + 1,
                             max(0, px - h):px + h + 1, :3]
                    sl *= (1.0 - alpha)
                    n += sl.shape[0] * sl.shape[1]
            img.pixels.foreach_set(arr.ravel())
            img.update()
            img.pack()
            print(f"   [deriva] leme em {nome}: frac {frac:.2f}, "
                  f"~{n} texels escurecidos x{1-alpha:.2f}")


# fracoes da charneira do leme, lidas na foto citada de cada familia
EMPENAGEM = {
    "a319": dict(leme=0.32, foto="airbus A320neo/refs/ref_PR-XBP_teresina.jpg"),
    "a320ceo": dict(leme=0.32, foto="ref_PR-XBP_teresina.jpg"),
    "a320neo": dict(leme=0.32, foto="ref_PR-XBP_teresina.jpg"),
    "a321ceo": dict(leme=0.32, foto="ref_PR-XBP_teresina.jpg (familia)"),
    "a321neo": dict(leme=0.32, foto="ref_PR-XBP_teresina.jpg (familia)"),
    "b763er": dict(leme=0.35, foto="ref_CC-CXE_appr4.jpg (familia 767)"),
    "b763f": dict(leme=0.35, foto="ref_CC-CXE_appr4.jpg (familia 767)"),
    "b763bcf": dict(leme=0.35, foto="ref_CC-CXE_appr4.jpg"),
    "b77w": dict(leme=0.30, foto="refs/20251011_LATAM_PT-MUC_EGLL.jpg"),
    "b788": dict(leme=0.33, foto="ref_bgg_mad23.jpg (familia 787)"),
    "b789": dict(leme=0.33, foto="ref_bgg_mad23.jpg"),
}


def fazer_empenagem(tag):
    cfg = EMPENAGEM[tag]
    dv = Deriva()
    dv.leme(cfg["leme"])


# tabela da asa: objetos, se as cutlines da familia A320 precisam ser
# desenhadas (os Boeing ja embarcam as suas), e a caixa da matricula.
# caixas: lidas nas fotos citadas na LEI acima; a familia A320 nao tem quadro
# de intradorso no repositorio — a caixa dela e a LEI DE FROTA aplicada a
# propria asa (banda do aileron, declarado; QA-BACKLOG registra a pendencia).
ASA = {
    "a319":    dict(objetos=["Asas"], linhas=True, reg="PT-TMT",
                    eta=(0.58, 0.905)),
    "a320ceo": dict(objetos=["Asas"], linhas=True, reg="CC-BFO",
                    eta=(0.58, 0.905)),
    "a320neo": dict(objetos=["Asas"], linhas=True, reg="PT-TMN",
                    eta=(0.58, 0.905)),
    "a321ceo": dict(objetos=["Asas"], linhas=True, reg="PT-MXP",
                    eta=(0.58, 0.905)),
    "a321neo": dict(objetos=["Asas"], linhas=True, reg="PS-LBA",
                    eta=(0.58, 0.905)),
    "b763er":  dict(objetos=["Asas"], linhas=False, reg="CC-CWY",
                    y=(16.5, 21.4)),
    "b763f":   dict(objetos=["Asas"], linhas=False, reg="N536LA",
                    y=(16.5, 21.4)),
    "b763bcf": dict(objetos=["Asas"], linhas=False, reg="CC-CXE",
                    y=(16.5, 21.4)),
    # 777: a arte embarcada de AsaLinhas NUNCA renderizou (AsaD/E sem camada
    # UV) e o frame dela e irrecuperavel (fit degenerado, sem gap de pylon);
    # esta rodada REPINTA as linhas num dominio declarado, medidas na foto do
    # intradorso da PROPRIA PT-MUG (ref_PT-MUG_2022_FRA.jpg) ancoradas nas
    # canoas do modelo (y 9.0/14.5/19.5). Spoilers DEFERIDOS (sem foto do
    # extradorso; QA-BACKLOG).
    "b77w":    dict(objetos=["AsaE", "AsaD"], linhas="b77w", reg="PT-MUG",
                    y=(13.2, 19.4), limpar=True),
    "b788":    dict(objetos=["Asas"], linhas=False, reg="CC-BBF",
                    eta=(0.66, 0.90)),
    "b789":    dict(objetos=["Asas"], linhas=False, reg="CC-BGK",
                    eta=(0.66, 0.90)),
}


def _texto_tris_arial(txt):
    """Glifos em Arial Bold — a fonte das matriculas dos A321/A320ceo."""
    D = bpy.data
    cu = D.curves.new("_txt_arial", 'FONT')
    cu.body = txt
    f = D.fonts.get("Arial Bold")
    if f:
        cu.font = f
    cu.size = 1.0
    ob = D.objects.new("_txt_arial", cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    tris = [[(v.co.x, v.co.y) for v in f2.verts] for f2 in bm.faces]
    bm.free()
    bpy.data.meshes.remove(me)
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    a = np.asarray(tris)
    return tris, (a[..., 0].min(), a[..., 0].max(),
                  a[..., 1].min(), a[..., 1].max())


def _tris_ilhas(nome, plano=("x", "z")):
    """Ilhas do mesh de matricula, ordenadas por x, como listas de tris 2D."""
    import collections
    ob = bpy.data.objects[nome]
    me = ob.data
    me.calc_loop_triangles()
    adj = collections.defaultdict(set)
    for e in me.edges:
        a, b = e.vertices
        adj[a].add(b); adj[b].add(a)
    seen, islands = set(), []
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
        islands.append(comp)
    idx = {"x": 0, "y": 1, "z": 2}
    i, j = idx[plano[0]], idx[plano[1]]

    def pt(vi):
        c = me.vertices[vi].co
        return (c[i], c[j])

    def bx(comp):
        ps = [pt(v) for v in comp]
        return (min(p[0] for p in ps), max(p[0] for p in ps),
                min(p[1] for p in ps), max(p[1] for p in ps))

    islands.sort(key=lambda c: bx(c)[0])
    vert_isl = {v: k for k, comp in enumerate(islands) for v in comp}
    tris_by = {k: [] for k in range(len(islands))}
    for t in me.loop_triangles:
        tris_by[vert_isl[t.vertices[0]]].append([pt(v) for v in t.vertices])
    return tris_by, [bx(c) for c in islands]


def _tris_reg(tag, texto):
    """A arte da matricula, a MESMA do casco de cada familia (REBUILD):
    mesh proprio quando existe, recombinacao quando o mesh guarda outra
    matricula, Arial Bold nos A321/A320ceo, fonte padrao nos Boeing legados."""
    if tag == "a320neo":
        return tris_xy("Reg_E", ("x", "z"))
    if tag == "b789":
        return tris_xy("Reg787_E", ("x", "y"))
    if tag == "a319":
        # P,T,-,T,M,T recombinado de Reg_E (que guarda PT-TMN)
        tris_by, bb = _tris_ilhas("Reg_E", ("x", "z"))
        seq = [0, 1, 2, 3, 4, 1]
        tris2 = []
        for pos, k in enumerate(seq):
            slot = bb[pos] if pos < len(bb) else bb[-1]
            dx = 0.5 * (slot[0] + slot[1]) - 0.5 * (bb[k][0] + bb[k][1])
            tris2 += [[(px + dx, pz) for px, pz in t] for t in tris_by[k]]
        return tris2, bb_de(tris2)
    if tag == "b788":
        # C,C,-,B,B + F construido (build_788_livery secao 6, como no casco)
        tris_by, bb = _tris_ilhas("Reg787_E", ("x", "y"))
        capH = max(b[3] for b in bb)
        hyph = min(range(len(bb)), key=lambda k: (bb[k][3] - bb[k][2]))
        tbar = bb[hyph][3] - bb[hyph][2]
        seq = [0, 1, 2, 3, 3]
        tris2 = []
        for pos, k in enumerate(seq):
            slot = bb[pos]
            dxg = 0.5 * (slot[0] + slot[1]) - 0.5 * (bb[k][0] + bb[k][1])
            tris2 += [[(px + dxg, py) for px, py in t] for t in tris_by[k]]
        s5 = bb[5]
        wF = (s5[1] - s5[0]) * 0.92
        fx0 = s5[0]
        sw = tbar * 1.10

        def rect(x0, x1, y0, y1):
            return [[(x0, y0), (x1, y0), (x1, y1)],
                    [(x0, y0), (x1, y1), (x0, y1)]]

        tris2 += rect(fx0, fx0 + sw, 0.0, capH)
        tris2 += rect(fx0, fx0 + wF, capH - tbar, capH)
        zm = 0.54 * capH
        tris2 += rect(fx0, fx0 + 0.82 * wF, zm - 0.5 * tbar, zm + 0.5 * tbar)
        return tris2, bb_de(tris2)
    if tag in ("a320ceo", "a321ceo", "a321neo"):
        return _texto_tris_arial(texto)
    return texto_tris(texto)          # boeing legados: fonte padrao do casco


def fazer_asa(tag):
    cfg = ASA[tag]
    asa = Asa(cfg["objetos"])
    asa.bordos()
    if cfg.get("limpar"):
        asa.arr[..., :3] = 0.0
        print("   [asa] AsaLinhas zerada (arte antiga sem UV, frame perdido)")
    if cfg["linhas"] == "b77w":
        asa.linhas_777()
    elif cfg["linhas"]:
        asa.linhas_familia_a320()
    tris, bb = _tris_reg(tag, cfg["reg"])
    if "y" in cfg:
        y0, y1 = cfg["y"]
    else:
        e0, e1 = cfg["eta"]
        y0 = asa.y_raiz + e0 * (asa.y_ponta - asa.y_raiz)
        y1 = asa.y_raiz + e1 * (asa.y_ponta - asa.y_raiz)
    asa.matricula(tris, bb, y0, y1)
    asa.shader()
    asa.salvar()


# ------------------------------------------------------- titulo do A319
def fazer_titulo_a319(cs):
    """Fecha a entrada 'AIRBUS A3' do QA-BACKLOG: o titulo inteiro re-
    rasterizado de ARTE REAL — as ilhas do proprio MarkAirbusNeo_E (swirl?/
    AIRBUS/A/3 + os SLOTS oficiais de '2' e '0' para o espacamento), o '1'
    importado de airbus_a321neo_logo.svg (mesma fonte de titulo), e o '9'
    reconstruido do bojo do proprio '0' + haste (unico glifo sem fonte SVG no
    repositorio — declarado; a proporcao conferida no crop da PT-TMT,
    ref_sdu_00). Caixa: a do builder (x 23.45..25.20, z 1.04..~1.21), que a
    sdu_01 confirma quase encostada na fronteira nova."""
    D = bpy.data
    mk = D.objects["MarkAirbusNeo_E"]
    me = mk.data
    me.calc_loop_triangles()
    # ilhas locais (x, y)
    import collections
    adj = collections.defaultdict(set)
    for e in me.edges:
        a, b = e.vertices
        adj[a].add(b); adj[b].add(a)
    seen, islands = set(), []
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
        islands.append(comp)

    def box(comp):
        xs = [me.vertices[i].co.x for i in comp]
        ys = [me.vertices[i].co.y for i in comp]
        return min(xs), max(xs), min(ys), max(ys)

    islands.sort(key=lambda c: box(c)[0])
    vert_isl = {i: k for k, comp in enumerate(islands) for i in comp}
    tris_by = {k: [] for k in range(len(islands))}
    for t in me.loop_triangles:
        tris_by[vert_isl[t.vertices[0]]].append(
            [(me.vertices[i].co.x, me.vertices[i].co.y) for i in t.vertices])
    bbs = [box(c) for c in islands]
    n = len(islands)
    caps = [b[3] - b[2] for b in bbs]
    # classificar por PALAVRAS: o maior vao em x separa 'AIRBUS' de 'A320neo'
    # (deterministico; o detector anterior de swirl confundiu o 'A' com um
    # swirl e deslocou todos os glifos — o 'neo' virou '9')
    gaps = [(bbs[k + 1][0] - bbs[k][1], k) for k in range(n - 1)]
    corte = max(gaps)[1]
    w1 = list(range(0, corte + 1))
    w2 = list(range(corte + 1, n))
    swirl = w1[0] if len(w1) == 7 else None
    letras1 = w1[1:] if swirl is not None else w1
    if len(letras1) != 6 or len(w2) < 5:
        raise SystemExit(f"titulo a319: particao inesperada {len(w1)}+{len(w2)}")
    seq = letras1 + w2[:2]                 # A I R B U S + A 3
    isl_2, isl_0 = w2[2], w2[3]            # slots do '2' e do '0'
    cap = max(caps[k] for k in letras1)
    print(f"   [titulo] {n} ilhas ({len(w1)}+{len(w2)}), "
          f"swirl={'sim' if swirl is not None else 'nao'}, cap {cap:.3f}")
    tris2 = []
    for k in ([swirl] if swirl is not None else []) + seq:
        tris2 += tris_by[k]
    # '1' real do SVG do a321neo, no SLOT do '2'
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
            D.objects.remove(o, do_unlink=True)
        bmesh.ops.triangulate(bmn, faces=bmn.faces[:])
        me321 = D.meshes.new("a321neo_mark")
        bmn.to_mesh(me321)
        bmn.free()
    me321.calc_loop_triangles()
    # ILHAS por conectividade (os glifos italicos se sobrepoem em x, entao
    # cluster por intervalo mistura '1' com 'n'/'e'): A 3 2 1 n e o
    adj2 = collections.defaultdict(set)
    for e in me321.edges:
        a2, b2 = e.vertices
        adj2[a2].add(b2); adj2[b2].add(a2)
    seen2, isl2 = set(), []
    for v0 in range(len(me321.vertices)):
        if v0 in seen2:
            continue
        st, comp = [v0], set()
        while st:
            v = st.pop()
            if v in comp:
                continue
            comp.add(v)
            st.extend(adj2[v] - comp)
        seen2 |= comp
        isl2.append(comp)
    isl2.sort(key=lambda c: min(me321.vertices[i].co.x for i in c))
    if len(isl2) < 5:
        raise SystemExit(f"a321neo_mark: {len(isl2)} ilhas (esperava >=5)")
    # o '1' e o mais ESTREITO dos quatro primeiros glifos (A,3,2,1);
    # com 'neo' ligado o mesh da 5 ilhas, com glifos soltos da 7

    def _w(comp):
        xs2 = [me321.vertices[i].co.x for i in comp]
        return max(xs2) - min(xs2)

    k1 = min(range(4), key=lambda k: _w(isl2[k]))
    vi2il = {v: k for k, comp in enumerate(isl2) for v in comp}
    tris_1 = [[(me321.vertices[i].co.x, me321.vertices[i].co.y)
               for i in t.vertices]
              for t in me321.loop_triangles
              if vi2il[t.vertices[0]] == k1]
    pts1 = [p for t in tris_1 for p in t]
    x1a = min(p[0] for p in pts1); x1b = max(p[0] for p in pts1)
    y1a = min(p[1] for p in pts1); y1b = max(p[1] for p in pts1)
    # os digitos do tipo sao MENORES que o cap do AIRBUS na arte oficial
    # (o 'A320' da marca mede 0.64 do cap); escalar pelo '3' real
    capd = bbs[seq[-1]][3] - bbs[seq[-1]][2]
    s1 = capd / (y1b - y1a)
    slot2 = bbs[isl_2]
    cx_slot2 = 0.5 * (slot2[0] + slot2[1])
    base_y = bbs[seq[-1]][2]                # baseline do '3'
    w1 = (x1b - x1a) * s1
    for t in tris_1:
        tris2.append([((px - x1a) * s1 + cx_slot2 - 0.5 * w1,
                       (py - y1a) * s1 + base_y) for px, py in t])
    # '9': bojo do '0' (0.72 do cap, alinhado ao topo) + haste a direita
    slot0 = bbs[isl_0]
    cx_slot0 = 0.5 * (slot0[0] + slot0[1])
    t0 = tris_by[isl_0]
    x0a, x0b, y0a, y0b = slot0
    esc = 0.72
    stroke = 0.19 * capd
    bojo = []
    for t in t0:
        bojo.append([(cx_slot0 + (px - cx_slot0) * esc,
                      (base_y + capd) - ((y0b - py) * esc)) for px, py in t])
    tris2 += bojo
    bj_x1 = cx_slot0 + (x0b - cx_slot0) * esc
    bj_ymid = (base_y + capd) - 0.5 * (y0b - y0a) * esc
    tris2.append([(bj_x1 - stroke, base_y), (bj_x1, base_y), (bj_x1, bj_ymid)])
    tris2.append([(bj_x1 - stroke, base_y), (bj_x1, bj_ymid),
                  (bj_x1 - stroke, bj_ymid)])
    # caixa final e rasterizacao (modo z, baseline constante)
    a = np.asarray([p for t in tris2 for p in t])
    bb = (a[:, 0].min(), a[:, 0].max(), a[:, 1].min(), a[:, 1].max())
    # caixa do spec (x 23.45-25.20, z 1.04-1.21): encaixe uniforme como o
    # builder fazia — a altura manda, a arte comeca em TX0
    razao = (bb[1] - bb[0]) / (bb[3] - bb[2])
    ZB, ZT = 1.040, 1.210
    TX0 = 23.45
    TX1 = min(TX0 + (ZT - ZB) * razao, 25.20)
    cs.apagar(23.30, 25.00, 50.0, 67.0, nome="titulo antigo (AIRBUS A3)",
              alvos=[INDIGO, TITULO], base="branco")
    cs.apagar(23.30, 25.00, -67.0, -50.0, nome="titulo antigo stbd",
              alvos=[INDIGO, TITULO], base="branco")
    xm = 0.5 * (TX0 + TX1)
    th_t = _th_de_z(cs, xm, ZT)
    th_b = _th_de_z(cs, xm, ZB)
    s_topo = float(cs.arc(np.array([xm]), np.array([th_t]))[0])
    altura = float(cs.arc(np.array([xm]), np.array([th_b]))[0]) - s_topo
    for lado, esp in ((-1, False), (1, True)):
        cs.pintar(tris2, bb, TX0, TX1, s_topo, altura, TITULO, lado, esp,
                  modo="z", z_topo=ZT,
                  nome=f"titulo AIRBUS A319 {'port' if lado < 0 else 'stbd'}")
    print(f"   [titulo] caixa x {TX0}..{TX1}  z {ZB:.3f}..{ZT:.3f} "
          f"(razao da arte {razao:.2f})")


def _th_de_z(cs, x, z):
    """theta (rad, >0) em que a secao local cruza z."""
    i = int(cs._i(np.array([x]))[0])
    e = cs.est[i]
    m = e[1] >= 0
    tt = e[1][m]; zz = e[3][m]
    o = np.argsort(zz)
    return float(np.interp(z, zz[o], tt[o]))


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
    if tag == "b788" or tag in LEGADO:
        tarefas = argv[1:]
        rodar_legado = (not tarefas) or ("marcas" in tarefas)
        for o in bpy.data.objects:
            o.hide_viewport = False
        bpy.context.view_layer.update()
        if rodar_legado:
            if tag == "b788":
                cb = CascoB788()
                print(f"[b788] legado 787-8  L={cb.L_UV}  tex {cb.W}x{cb.H}")
                _marcas_b788(cb)
                cb.salvar()
            else:
                cfg = LEGADO[tag]
                cl = CascoLegado(cfg["spec"], cfg["luv"], cfg["ponte"])
                print(f"[{tag}] legado  L={cl.LUV}  tex {cl.W}x{cl.H}")
                cfg["fn"](cl)
                cl.salvar()
        if "impressao" in tarefas:
            cs = Casco()
            print(f"[{tag}] impressao  L={cs.L:.3f}  tex {cs.W}x{cs.H}")
            fazer_impressao(cs, tag)
            cs.salvar()
        if "asa" in tarefas:
            fazer_asa(tag)
        if "empenagem" in tarefas:
            fazer_empenagem(tag)
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
    if "impressao" in tarefas:
        fazer_impressao(cs, tag)
    if "titulo" in tarefas and tag == "a319":
        fazer_titulo_a319(cs)
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
    if "asa" in tarefas:
        fazer_asa(tag)
    if "empenagem" in tarefas:
        fazer_empenagem(tag)
    bpy.ops.wm.save_mainfile()
    print(f"[{tag}] blend saved")


if __name__ == "__main__":
    main()
