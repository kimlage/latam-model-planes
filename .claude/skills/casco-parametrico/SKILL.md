---
name: casco-parametrico
description: Build the aircraft geometry in Blender from the spec — fuselage from a sparse control cage + Catmull-Clark subsurf, ovoid sections in the nose, wings and empennage by NACA loft, belly fairing, engines, landing gear, doors and windows built analytically on the surface. Use ALWAYS when modelling, rebuilding or fixing aircraft geometry in this repository: "the nose is dented", "the hull came out deformed", "assemble the wings", "the parts are disconnected", "the landing gear is floating", "rebuild the fuselage", "the doors are gone". Brings the ready-made builder and, above all, the method errors that have already produced rippled hulls and detached parts.
---

# Parametric hull and structure

All the geometry comes from `spec_<type>.json`. The model is disposable; the
spec is not. If the hull has to be rebuilt, rebuild it — as long as you rebuild
it from the spec.

## The central lesson: the cage is not the surface

This was the error that cost the most time in the project, and it is
counter-intuitive.

The first attempt sampled the extracted outline into dense rings, every 10 cm.
It seemed right: more data, more fidelity. The result was a **dented** hull —
the micro-ripples of pixel-extracted data turned into visible waves under the
glossy paint, because automotive clearcoat amplifies normal variation that a
matte surface would hide. Densifying further made it worse.

What works is the opposite: **few rings, in the right places, and let
Catmull-Clark do the fairing.** The control cage sits only on the real frames
(tip + FR1–FR12 + the door stations + the barrel + the tail), typically ~33
rings of 32 segments, and subsurf at level 3 in the render delivers genuinely
continuous curvature. It is not an approximation: Catmull-Clark converges to a
G² surface, which is exactly what a fuselage is.

Three practical consequences:

- **Longitudinals by PCHIP on the official frames**, not from the pixel cloud.
  The extraction serves to discover the shape; the cage uses the manufacturer's
  stations.
- **The barrel takes identical, evenly spaced rings** (every 2–3 m). If you
  sample the barrel from the extracted data, it ripples. Constant section means
  literally identical rings.
- **Compensate for the shrinkage.** Catmull-Clark pulls the surface inside the
  cage. On a 32-sided ring the measured factor is **×1.0064**, applied radially
  about the centre of the section. Without it the aircraft comes out thin and
  the doors end up buried.

## The builder

`scripts/casco.py` carries the ready-made recipe: `aneis_de_spec()`,
`construir_casco()`, `uv_cilindrica()`, the NACA profiles and
`validar_por_raycast()`. Paste it into `execute_blender_code` or run it with
`blender file.blend --python`.

```python
aneis = aneis_de_spec(json.load(open("spec_b789.json")))
fus = construir_casco(aneis, nome="Fuselagem", material="LATAM_Branco",
                      ponta_frente=(0.0, 0.0, -1.16), ponta_tras=(62.85, 0.0, 1.66))
uv_cilindrica(fus.data, aneis, comprimento_uv=63.5)
```

`construir_casco` swaps the existing object's `mesh` instead of recreating the
object. That preserves modifiers, shrinkwrap targets and references by name —
several regressions came from recreating the object and silently breaking those
links.

## Sections: the nose is not an ellipse

This is the difference between a nose that reads as an A320 and one that reads
as a duck bill.

The nose sections are **ovoid**: a full lower lobe (plan-view width), an upper
lobe pinched in the cockpit zone. Model the half-width as
`y = w(x)·(1−t²)^e(x)`, with the exponent `e(x)` varying along x — on the A320,
0.5 up to x≈1.2, rising to 1.0 between 2.4 and 3.2, back to 0.5 from 5.5 on.

It is the exponent that makes the windshield "turn forward" without a manual
facet. Validation: in the ACAP front view the front glass panes reach y≈±0.05 at
the centre post and the outer edge reaches ±0.86 at z≈0.9 — with `e=1`,
`y(2.8; z=0.9)=0.89`, which closes.

The barrel's master section is not an ellipse either: shoulders ~14% wider,
maximum width 8–10 cm **above** mid-height, and a gentle tuck underneath.
Tabulate the half-width by depth below the crown from the front-view drawing.

The tail, on the other hand, is an ellipse: `w = 0.954·r` on the A320, `0.96·r`
on the 787. Applying the ovoid section to the tail breaks the livery wrap and
the registration markings — it has happened.

## Buried roots

A rule that came out of a whole cycle of "vários elementos desconectados da
carroceria" [several elements disconnected from the body]: **the root of a wing,
fin, stabilizer or pylon never starts at the hull surface — always 1 to 1.5 m
inside it.**

The reason is geometric. If the root starts exactly at the surface, any
difference between the wing's curvature and the hull's opens a gap, and the
subsurf pulls the surface further inward on top of that. Burying the root makes
the intersection happen inside the solid, where nobody sees it. On the 787: wing
at y=1.6 (the hull is at 2.885), fin base at z=1.9, pylon as a wedge entering
the wing, main gear legs rising up into the wing.

Same logic for the gear: the leg has to **enter** the bay, not stop at the
surface. A "floating" landing gear is almost always a leg that is too short, not
wrong positioning.

## Wings and empennage

Loft NACA profiles between stations with chord and offset interpolated from the
spec: `secao_aerofolio()` generates the closed outline (upper surface LE→TE,
lower surface TE→LE). Close it with a cap at the root and at the tip, otherwise
the render shows the interior.

Respect the real breaks: on the 787-9 the trailing edge has 11° up to y=10 m and
22.9° after that, and the raked tip runs from x=40.69 to 43.36 — the tip
silhouette is one of the things that identifies the type from a distance.
Dihedral is static in the model (7° on the 787), even though in real life it
depends on the load.

Subsurf 2 is enough for the wing; it is the hull that needs 3.

## Doors, windows and surface details

Build them analytically **on** the surface, evaluating the hull's `y_of(x, z)`
function and deriving the normal numerically — that way the detail follows the
double curvature instead of floating.

Two corrections that came from direct feedback:

**Compensate for the subsurf.** The shrinkage buries the doors. Push them ~22 mm
outward (`±0.022` in y depending on the side). Without that the door shows up
only half-there.

**A door outline that relies on shadow alone does not read.** A geometric groove
only appears where the light creates shadow — at the canonical angles that means
only the top and bottom arcs show up, and the door reads "half there". The
solution that worked was to **paint the outline into the livery texture**: a ring
of grey band (the FAR band) plus a dark groove ring, rasterized in (x,θ) space.
See `livery-latam`.

## Engines

The engine is visual identity, not decoration — getting the engine wrong makes
the aircraft read as a different type. Check which variant LATAM operates before
modelling: the LATAM A320neo is **PW1100G-GTF, not LEAP** (2013 order + 2023
agreement, exclusive in the fleet), which means a white fan cowl, polished lip,
no chevrons, and a nozzle with a long inconel tailcone. The 787-9 is Trent 1000,
with serrated chevrons on the trailing edge of the fan sleeve.

## Validate before rendering

After any rebuild, spend a few seconds on `validar_por_raycast()` with a handful
of probes at dimensions you know. A punctured hull, an inverted normal and a
wrong scale all show up there, before you spend minutes on a render and a round
of conversation.

`scripts/auditar_casco.py` does all three checks at once — run it after any
rebuild:

```python
exec(open(".claude/skills/casco-parametrico/scripts/auditar_casco.py").read())
auditar("boeing 787-9")
```

**Compare the cage with the spec station by station, not just the surface.**
Measure `max|y|` of each ring's vertices and divide by the spec's
`meia_largura`: the result has to be `COMP` (1.0064) over the whole length.
Where it is not, the error is in the cage, not in the subsurf — and that is the
only way to tell the two apart.

That is how a spurious taper in the nose of the 787-9 was found: the ratio came
out at 0.911 at the tip, rising linearly to 1.000 at x=5, while the barrel was
correct. Someone had applied a `1 − 0.105·(1 − x/5)` to the width and forgotten
about it. Crown and keel were right, so the hull looked plausible in every
render — no angle betrays 8% of narrowing in plan view. Once fixed, the median
error against the spec fell from 1.2 cm to 0.4 cm.

If you need to correct it, scale **only the wrong axis, ring by ring**, moving
the existing vertices. Rebuilding the mesh from scratch would throw away the UV
— and with it the whole registration of the painted livery.

Two traps when writing this kind of check, both discovered in practice: a ratio
against a near-zero value blows up with no defect at all (the crown crosses z=0
in the nose), so **judge by the error in metres**, with an absolute plus a
relative tolerance; and "a part's root is its highest vertices" is false for the
wing, whose top is the **tip** — declare which side the root is on for each part
instead of inferring it. A test that fires thirty false positives is worse than
no test, because it teaches you to ignore it.

Cross-check the three views against each other as well. That is how the A320's
"anamorphic top view" was found to be a false alarm (a fragmented run had
clipped an edge) — by validating against the stabilizer span: 6.012 measured
against 6.225 official, uniformly. One view on its own proves nothing.
