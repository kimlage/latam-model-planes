#!/usr/bin/env python3
"""Put each aeroplane's WEDGE RULE on trial against its own photograph.

    python3 conferir_echarpe.py                 # the whole fleet, one sheet
    python3 conferir_echarpe.py a319 b77w       # only these

Writes `comparacao_echarpe_frota.png` next to this file: one tile per aircraft,
the model's rear fuselage with every straddle sample drawn on it.

------------------------------------------------------------------------------
WHY THIS EXISTS
------------------------------------------------------------------------------
`reparar_echarpe.py` repairs the PAINT so that it agrees with the RULE each
aircraft publishes. It cannot tell whether the rule is right, and the audit that
preceded it measured only that agreement — "against the neo's own published rule
the paint agrees to 1.31%" says nothing about the aeroplane. This file asks the
other question, and it asks it of the photograph.

THE TEST. Rectify the registration's photograph onto the model's own (x, z) by a
homography, then, for every height z, compute the x at which the rule's forward
boundary sits and sample the photographed skin 0.35 m each side of it. If the
rule is right the outer sample is white and the inner one is paint. The same for
the lower boundary, 7 degrees each side in theta. Nothing is fitted; the answer
is a count of agreements and disagreements, and the samples are drawn so the
disagreements can be looked at rather than believed.

WHY A HOMOGRAPHY, AND WHAT CONTROLS IT. The fuselage silhouette alone does NOT
pin x: the mid-fuselage is a cylinder, and the tail-cone tip is buried under the
stabiliser — a first fit here took the stabiliser tip for the tail cone and put
the A319's aft door two metres out. The homographies in `conferir_echarpe.json`
were fitted to the model's own orthographic silhouette (fin, stabiliser and tail
cone together are unmistakable) and are CONTROLLED on the fin: on the A319, the
fin's leading and trailing edges land within 0.07 m and 0.17 m of the model's
over z 2.5..7.0. Where a control like that is not available the tile says so.

WHAT THE COLOURS MEAN.
    green   the photograph agrees: white outside the boundary, paint inside
    red     the photograph disagrees
    grey    the sample lands on a door outline, a placard, or skin in shadow,
            where the colour test has no opinion

WHAT IT FOUND, 2026-08-22. Ten of the eleven rules put white outside and paint
inside. The A319's did not — it swept the forward boundary the wrong way and let
the paint down to |theta| 150 — and was replaced; the tile below is the
corrected rule. The photographs are NOT committed (see NOTICE.md); fetch them
with `python3 refs_fetch.py` before running this.

------------------------------------------------------------------------------
2026-08-26 — THE FLANK PARALLAX, AND WHAT IT HAD BEEN CHARGING
------------------------------------------------------------------------------
The fin control proves the homography maps the y = 0 PLANE correctly — and the
paint does not live in that plane. A skin point at lateral offset y projects
displaced by y * v, where v is the image projection of the aircraft's y axis;
on a telephoto near-profile v is negligible, but on a climbing or close frame
it reaches tens of px per metre, ALL of it in the direction that slides flank
features forward or aft. v is measurable inside the frame itself: the two
stabiliser tips sit at known (x, z) and +-y_tip, so the offset between the far
tip's image position and its y = 0 projection gives v directly.

Entries may therefore carry:
    "v":    [vx, vy] px per metre of +y (starboard), measured from the frame's
            own stabiliser; missing means 0, the old behaviour
    "lado": +1 when the photograph shows the starboard flank, -1 for port
    "rry":  the hull's half-width table, for y = lado * ry(x) * sin(theta)
    "nota": printed with the verdict; "sem_veredito" replaces OK/REVER for a
            frame that cannot answer (declared, not guessed)
A key like "b763er@cxc" is a SECOND frame of the same aircraft: the rule tested
is FROTA["b763er"]'s, and independent frames agreeing is what makes a verdict
safe to act on.

What the correction found: the four ~+-0.5..0.8 m "suspect wedges" of 08-22
were flank parallax, not paint — the 767-300ER reads +0.05/+0.18 m over two
frames, the A320ceo -0.03, the A321neo +0.25/+0.18 over two flanks. The A319's
08-22 re-measure had CARRIED the parallax whole (its frame is a climbing shot,
v = 57 px/m): door 4 was never off the ACAP station, and the wedge was moved
back +0.76 m aft. The A320neo's PT-TMN frame is delivery-era paint at 1024 px
and cannot be fin-anchored to better than +-0.3 m; the current fleet (PR-XBP)
wears the boundary ~+0.95 m aft of PT-TMN's — an era variant, recorded, not a
defect of the modelled registration.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

RAIZ = os.path.dirname(os.path.abspath(__file__))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import reparar_echarpe as rep  # noqa: E402

DADOS = os.path.join(RAIZ, "conferir_echarpe.json")
SAIDA = os.path.join(RAIZ, "comparacao_echarpe_frota.png")
BUSCA = 1.5         # metres searched each side of the forward boundary
BUSCA_TH = 25.0     # degrees searched each side of the lower boundary
TOL_X = 0.45        # a rule this close to the paint is called right
TOL_TH = 9.0


# ------------------------------------------------------------------ geometry
class Casco:
    def __init__(self, d):
        self.rx = np.array(d["rx"]); self.zc = np.array(d["rzc"])
        self.rz = np.array(d["rrz"])

    def zc_of(self, x): return np.interp(x, self.rx, self.zc)
    def rz_of(self, x): return np.interp(x, self.rx, self.rz)
    def crown(self, x): return self.zc_of(x) + self.rz_of(x)
    def keel(self, x): return self.zc_of(x) - self.rz_of(x)

    def theta(self, x, z):
        c = np.clip((z - self.zc_of(x)) / np.maximum(self.rz_of(x), 1e-6), -1, 1)
        return np.degrees(np.arccos(c))

    def z_of_theta(self, x, th):
        return self.zc_of(x) + self.rz_of(x) * np.cos(np.radians(th))


def aplicar(H, x, z):
    q = np.array([x, z, 1.0], float)
    p = H @ q
    return p[0] / p[2], p[1] / p[2]


def classe(A, H, x, z, sh=(0.0, 0.0)):
    """'_' white, '#' paint, 'o' neither (shadow, ink, a placard), '?' off frame.

    `sh` is the flank-parallax shift in pixels for THIS skin point, y * v."""
    px, py = aplicar(H, x, z)
    px += sh[0]; py += sh[1]
    ix, iy = int(round(px)), int(round(py))
    if not (3 <= ix < A.shape[1] - 3 and 3 <= iy < A.shape[0] - 3):
        return "?"
    p = A[iy - 3:iy + 4, ix - 3:ix + 4].reshape(-1, 3).mean(0)
    if p[2] - p[0] > 18 and p.max() < 150:
        return "#"
    if p.max() > 150:
        return "_"
    return "o"


def x_da_regra(regra, casco, z, x0, x1):
    xs = np.arange(x0, x1, 0.005)
    zz = np.full_like(xs, z)
    m = regra(xs, zz, casco.theta(xs, zz))
    k = np.nonzero(m)[0]
    return float(xs[k[0]]) if len(k) else float("nan")


def th_da_regra(regra, casco, x, ths):
    zz = casco.z_of_theta(x, ths)
    m = regra(np.full_like(ths, x), zz, ths)
    k = np.nonzero(m)[0]
    return float(ths[k[-1]]) if len(k) else float("nan")


# --------------------------------------------------------------------- test
def _transicao(cls, i0, passo):
    """Signed distance from the rule's boundary to the photograph's own.

    `cls` is the strip of classes sampled outward-to-inward across the rule's
    boundary, `i0` the index the rule sits at. The boundary is the last white
    sample before the first run of paint that then holds. Returns None when the
    strip never makes that transition — a door outline, a placard, or skin in
    shadow, where the colour test has no opinion.
    """
    n = len(cls)
    for i in range(n - 3):
        if cls[i] == "_" and cls[i + 1] == "#" and cls[i + 2] == "#" \
                and cls[i + 3] == "#":
            return (i + 0.5 - i0) * passo
    return None


def testar(tag, cfg):
    """(samples, forward residual, lower residual) — the photograph's answer.

    Each sample is (x, z, residual or None). A residual is signed: POSITIVE
    means the photographed boundary is AFT of / BELOW the rule's, i.e. the rule
    claims paint the aeroplane does not carry there.
    """
    casco = Casco(cfg)
    H = np.array(cfg["H"], float)
    A = np.asarray(Image.open(os.path.join(RAIZ, cfg["foto"])).convert("RGB")).astype(float)
    regra = rep.FROTA[tag.split("@")[0]]["regra"]
    v = np.array(cfg.get("v", (0.0, 0.0)), float)
    lado = float(cfg.get("lado", -1))
    rry = np.array(cfg.get("rry", cfg["rrz"]), float)

    def shift(x, z):
        th = casco.theta(np.asarray([x], float), np.asarray([z], float))[0]
        y = lado * np.interp(x, cfg["rx"], rry) * math.sin(math.radians(th))
        return (y * v[0], y * v[1])
    b = cfg["banda"]
    x0j = cfg["jan"][0]
    pontos = []
    dfw = []
    for z in np.arange(b["z"][0], b["z"][1] + 1e-9, 0.10):
        xr = x_da_regra(regra, casco, z, x0j - 10.0, b["xhi"])
        if not np.isfinite(xr) or z > casco.crown(xr) - 0.10 or z < casco.keel(xr) + 0.10:
            continue
        passo = 0.05
        off = np.arange(-BUSCA, BUSCA + 1e-9, passo)
        cls = [classe(A, H, xr + o, z, shift(xr + o, z)) for o in off]
        d = _transicao(cls, len(off) // 2, passo)
        pontos.append((xr, z, d))
        if d is not None:
            dfw.append(d)
    ths = np.arange(0.0, 180.01, 0.25)
    dlo = []
    for x in np.arange(b["x"][0], b["x"][1] + 1e-9, 0.20):
        tr = th_da_regra(regra, casco, x, ths)
        if not np.isfinite(tr) or tr > 175:
            continue
        passo = 1.0
        off = np.arange(-BUSCA_TH, BUSCA_TH + 1e-9, passo)
        zz = casco.z_of_theta(x, tr - off)          # outward = larger theta
        ok = zz > casco.keel(x) + 0.08
        if ok.sum() < 8:
            continue
        cls = [classe(A, H, x, z, shift(x, z)) if k else "?"
               for z, k in zip(zz, ok)]
        d = _transicao(cls, len(off) // 2, passo)
        pontos.append((x, casco.z_of_theta(x, tr), d))
        if d is not None:
            dlo.append(d)
    return pontos, _rob(dfw), _rob(dlo)


def _rob(v):
    """(median, robust spread, n) with the outliers trimmed."""
    if not v:
        return (float("nan"), float("nan"), 0)
    a = np.array(v, float)
    m = np.median(a)
    s = np.median(np.abs(a - m))
    k = np.abs(a - m) < max(3 * s, 0.15 if abs(m) < 10 else 3.0)
    return (float(np.median(a[k])), float(np.std(a[k])), int(k.sum()))


# -------------------------------------------------------------------- sheet
def tile(tag, cfg, pontos, sa, sb, larg=780):
    """The RULE's own shape, with the photograph's verdict drawn on it.

    Not a render and not a photograph: the reference images are third-party
    works and stay out of git (NOTICE.md), and a render would only show the
    paint agreeing with the rule it was made from. What is drawn is the region
    the rule claims, in the aircraft's own (x, z), and on it every place the
    photograph was asked whether that claim is true.
    """
    x0, x1, z0, z1, ppm = cfg["jan"]
    casco = Casco(cfg)
    regra = rep.FROTA[tag.split("@")[0]]["regra"]
    ppm = max(28.0, 760.0 / (x1 - x0))
    W = int((x1 - x0) * ppm); Hh = int((z1 - z0) * ppm)
    im = Image.new("RGB", (W, Hh), (26, 26, 30))
    dr = ImageDraw.Draw(im)
    U = lambda x: (x - x0) * ppm
    V = lambda z: (z1 - z) * ppm
    # hull, then the rule's region inside it
    up = [(U(x), V(casco.crown(x))) for x in np.arange(x0, x1, 0.1)]
    dn = [(U(x), V(casco.keel(x))) for x in np.arange(x1 - 0.1, x0, -0.1)]
    dr.polygon(up + dn, fill=(232, 233, 236))
    ths = np.arange(0.0, 180.01, 0.5)
    for x in np.arange(x0, x1, 1.0 / ppm):
        zz = casco.z_of_theta(x, ths)
        m = regra(np.full_like(ths, x), zz, ths)
        if not m.any():
            continue
        k = np.nonzero(m)[0]
        dr.line([(U(x), V(zz[k[0]])), (U(x), V(zz[k[-1]]))],
                fill=(0x2A, 0x00, 0x88), width=1)
    for x in np.arange(x0, x1, 0.05):
        for zt in (casco.crown(x), casco.keel(x)):
            dr.point((U(x), V(zt)), fill=(120, 120, 124))
    for x in np.arange(math.ceil(x0), x1, 2.0):
        dr.line([(U(x), 0), (U(x), Hh)], fill=(70, 70, 76), width=1)
        dr.text((U(x) + 2, Hh - 13), "%d" % x, fill=(120, 120, 128))
    for x, z, d in pontos:
        if d is None:
            c = (140, 140, 145)
        elif abs(d) < (TOL_X if abs(d) < 5 else TOL_TH):
            c = (40, 230, 60)
        else:
            c = (255, 40, 40)
        dr.ellipse([U(x) - 4, V(z) - 4, U(x) + 4, V(z) + 4], fill=c,
                   outline=(0, 0, 0))
    im = im.resize((larg, int(im.height * larg / im.width)))
    dr = ImageDraw.Draw(im)
    txt = ("%-9s  dianteira %+.2f +-%.2f m (n=%d)    inferior %+.1f +-%.1f deg "
           "(n=%d)   foto menos regra"
           % (tag, sa[0], sa[1], sa[2], sb[0], sb[1], sb[2]))
    dr.rectangle([0, 0, larg, 18], fill=(0, 0, 0))
    dr.text((5, 4), txt, fill=(255, 255, 0))
    return im


def main():
    cfgs = json.load(open(DADOS, encoding="utf-8"))
    alvos = [a for a in sys.argv[1:]] or list(cfgs)
    tiles = []
    print("%-9s %-22s %-24s" % ("tag", "dianteira (foto-regra)",
                                "inferior (foto-regra)"))
    for tag in alvos:
        cfg = cfgs[tag]
        if not os.path.exists(os.path.join(RAIZ, cfg["foto"])):
            print("%-9s  photograph missing — run refs_fetch.py" % tag)
            continue
        pontos, sa, sb = testar(tag, cfg)
        if cfg.get("sem_veredito"):
            verdito = "SEM VEREDITO"
        elif abs(sa[0]) < TOL_X and (np.isnan(sb[0]) or abs(sb[0]) < TOL_TH):
            verdito = "OK"
        else:
            verdito = "REVER"
        print("%-12s %+7.2f +-%.2f m  n=%-3d   %+7.1f +-%.1f deg  n=%-3d  %s"
              % (tag, sa[0], sa[1], sa[2], sb[0], sb[1], sb[2], verdito))
        if cfg.get("nota"):
            print("             %s" % cfg["nota"])
        tiles.append(tile(tag, cfg, pontos, sa, sb))
    if not tiles:
        return
    W = max(t.width for t in tiles)
    cv = Image.new("RGB", (W, sum(t.height + 4 for t in tiles)), (10, 10, 12))
    y = 0
    for t in tiles:
        cv.paste(t, (0, y)); y += t.height + 4
    cv.save(SAIDA)
    print("wrote", os.path.basename(SAIDA), cv.size)


if __name__ == "__main__":
    main()
