---
name: livery-latam
description: Apply the LATAM identity to the model with fleet-level fidelity — brand from the official SVGs (never a lookalike font), paint rasterized as a UV (x,θ) texture instead of a 3D decal, per-side fin sash, rear écharpe, registration, and the material recipe that makes paint look like paint. Use ALWAYS when the subject is paint, brand, logo, colours, tail, registration, titles, white windows, or render appearance: "the tail logo isn't right", "apply the livery", "the windows are white", "paint the registration", "make it more realistic", "the colours are wrong". Brings the official palette, the rasterization pipeline and the shader traps that have already rendered the whole aircraft in blue glass.
---

# LATAM livery

Three rules the project owner repeated until they became law:

0. **Look at the photo of the registration before painting anything.** Paint is
   a visual fact: no textual description — not the one in this spec, not the one
   from a research pass — outweighs the photo. If you do not have one, go find it
   (`WebSearch` for the registration, JetPhotos, Planespotters, Wikimedia)
   before opening the texture.
1. **Exact brand, never an approximation.** Import the official SVG. A lookalike
   font is an automatic rejection — the eye recognizes the letterforms.
2. **Application identical to the fleet's.** This is not a "LATAM-inspired
   livery": it is the paint scheme of that registration, measured on its own
   photo.

**The post-2016 LATAM livery, in practice: the fuselage is white except for a
triangular indigo wedge at the tail**, continuous with the indigo mass at the fin
root and carrying the registration. There is no cheatline running the length of
the hull.

This paragraph was wrong twice, in opposite directions, and both are worth
keeping. First the spec described an indigo sash running from the fin all the
way to the tailcone; it was refined for hours — limit by z, then by angle, then
with a local dip — against paint that did not exist in that shape. Then, on
removing it, **too much was removed**: the whole fuselage was declared white,
when the photo plainly shows the wedge.

The lesson is not "the photo wins" — that is already rule 4. It is that
**correcting an error in the opposite direction is still an error.** When the
owner says there is too much of something, measure how much to take away instead
of zeroing it. The wedge's exact geometry is in *The hull écharpe* below.

The official vectors are at the root: `latam_logo_indigo.svg` (full lockup) and
`airbus_a320neo_logo.svg` (type title).

## Palette

| Colour | Hex | Where |
|---|---|---|
| Indigo | `#2A0088` | wordmark, tail mass, écharpe |
| Coral | `#ED1651` | symbol, sash bands |
| Hull white | `#E6E7EA` | fuselage — **never pure white** |
| Title navy | `#1C2E63` | secondary lettering |
| Airbus grey | `#9FA4A9` (FS16515) | belly fairing, lower surfaces |
| Boeing flight gray | `#C8CACC` | 787 wings |

Photogrammetric measurements give slightly different values depending on photo
and lighting (on CC-BGK they came out as `#1B0088`/`#E8114B`). The brand values
above come from the official SVG and are the ones that go into the model; keep
the measured ones in the spec as an observation, not as a source.

## The architectural decision: paint is texture, not geometry

The first attempt was a 3D decal — a logo mesh stuck to the hull by shrinkwrap.
It failed in several ways at once: creasing under double curvature, z-fighting,
and `shrinkwrap` in PROJECT mode uses the object's **local** axis, so rotated
logos never projected — they hung at y=±3, z=−3.4, and their shadows showed up
on the hull as a "ghost LATAM".

The definitive architecture is to **rasterize everything into the hull's UV
(x,θ) texture**:

1. Model the brand marks as a flat mesh (imported from the SVG, or
   `TextCurve`→mesh for the registration).
2. Rasterize those meshes' triangles into (x,θ) space, writing an **integer
   colour code** per pixel into a `uint8` buffer of 8192×2048.
3. Downsample 2× (supersample) to 4096×1024, converting coverage into colour and
   into a mask.
4. Write **two images**: `LiveryTex` (colour, sRGB) and `LiveryFac` (mask,
   Non-Color).
5. Mix them in the hull shader.

Advantages that are not obvious until you hit them: zero z-fighting, free
anti-aliasing from the supersample, and the paint follows any rebuild of the
hull without repositioning anything.

For the belly, rasterize over θ∈0..2π with no seam and then `np.roll(H/2)` —
that way the belly mark is not cut by the UV seam.

**Marks with their own artwork** (logo, registration, titles) come from a
rasterized mesh as above. **Anything that is a rectangle or a stripe** —
antennas, drains, bay doors, operational markings, wear stains — is cheaper via
`scripts/pintar_marcas.py`, which takes a list of items in aircraft coordinates
and composites over the existing livery without erasing anything:

```python
exec(open(".claude/skills/livery-latam/scripts/pintar_marcas.py").read())
pintar([{"nome":"dreno fwd","tipo":"dreno","x_m":[8.4,8.7],"z_m":[-2.9,-2.6],
         "cor_hex":"#2A2C2E","lados":"ambos","intensidade":1.0}],
       spec, comprimento_uv=63.5)
```

Weathering comes in through the same door with a fractional `intensidade`
(0.08–0.35): the colour tints without covering, which is how dirt behaves.

## Four shader traps that cost hours

**Float-image alpha does not survive pack/reload.** The coverage mask was stored
in the alpha channel of a float image; after saving and reopening the `.blend`,
the alpha became 1.0 everywhere and the entire hull rendered as navy-blue glass.
The defence: the mask lives in a **separate, Non-Color image** (`LiveryFac`).
Never depend on alpha.

**`ShaderNodeMix` sockets are ambiguous by name.** The node has ten inputs —
`Factor_Float`, `Factor_Vector`, `A_Float`, `B_Float`, `A_Vector`, `B_Vector`,
`A_Color`, `B_Color`, `A_Rotation`, `B_Rotation` — and several share the same
*name* ("A", "B", "Factor"). You need the **identifier**, but
`node.inputs['A_Color']` **does not work**: bpy's key lookup uses the name, not
the identifier, and raises `KeyError`. Iterate:

```python
def sock(node, ident, saida=False):
    for s in (node.outputs if saida else node.inputs):
        if s.identifier == ident:
            return s
    raise KeyError(f"{ident} does not exist: " +
                   ", ".join(s.identifier for s in (node.outputs if saida else node.inputs)))
```

Use `sock(mix, "A_Color")`, `sock(mix, "Factor_Float")`,
`sock(mix, "Result_Color", saida=True)`. The error message listing the available
identifiers pays for itself the first time a Blender version renames something.

**A hidden object has a stale `matrix_world` after reopening the `.blend`.**
Before rasterizing decals that are set to `hide_viewport`, reveal them
temporarily and call `bpy.context.view_layer.update()`. Without that the matrix
comes back as identity, the titles vanish from the texture and the only symptom
is the painted pixel count dropping — with no error at all.

**A BYTE image with sRGB values.** Write to a byte image (sRGB by default) with
sRGB values. A `float_buffer` without getting the colorspace right washes the
colours out.

## The tail

The fin sash is the hardest part to get right and the one the owner pushed back
on most.

**The two sides are not mirrored in the naive sense.** Work in normalized height
`h` and chord `c` coordinates and generate **separate textures per side**
(`FinSashE`/`FinSashD`), assigned by the sign of the face centre. On the A320 the
starboard side is the same artwork in (x,z) — the band does not wrap around the
leading edge, as was assumed at the start.

**The white leading-edge fillet does exist, but it is thin** — a constant 0.30 m,
not 11.5% of the chord. That wrong width was exactly what the owner pointed out.

**The rear "band" is not a circumferential wrap.** It is a **diagonal écharpe**
at roughly 45°, coming down from the crown towards the front and closing in a
sharp point underneath (on PT-TMN, at x≈27.6, z≈−1.2). Belly and tailcone stay
**white**; the APU exhaust ring is bare metal. Modelling it as a circular wrap
leaves the tail visibly wrong.

**On the tailcone, limit the écharpe by ANGLE, never by z.** The cone tapers, so
a fixed height corresponds to an ever larger angle as the radius shrinks — and
the indigo ends up wrapping around the belly without any number in metres giving
it away. On the 787-9 that produced 50–54% of the circumference painted between
x=51 and 60, reaching down to 107–116° from the crown; the owner called it *"azul
a mais"* [too much blue] looking from behind and below. The right shape is a
decreasing `θ_max`: about 110° where the band crosses the fuselage, falling to
about 30° at the tip of the cone. Measure in **percentage of the
circumference** when checking — that is the metric that exposes the defect.

**The registration may be asymmetric.** On CC-BGK (787-9) it is white inside the
indigo to port and indigo over white to starboard. And it varies with the age of
the paint: PT-TMN left the factory with a white registration on the indigo and
today flies with indigo over white. Follow the owner's reference photo and
document the variation in the spec.

All of these outlines are tabulated in `spec_a320.json → cauda_livery` and
`spec_b789.json → livery_cc_bgk`. Reuse the `h`/`c` convention when measuring a
new aircraft.

### The fin artwork: edge-to-edge bands

The sash is a set of **parallel bands crossing the entire fin, from leading edge
to trailing edge**, over an **indigo** field. Each band is a parallelogram that
is **flight grey at both ends and coral in the middle**. Above the top band, the
tip is flight grey.

What it is **not**: a white fin with thick bands dying at mid-chord. That was
the reading of the inherited `F1..F7` polylines, and the owner rejected it —
*"o design da faixa lateral tem que ir de ponta a ponta, a espessura das faixas
tb esta errado"* [the side band design has to go end to end, the band thickness
is wrong too]. `F1..F7` are obsolete; do not use them.

The canonical geometry is now measured, in two linear coordinates:

```
c = z − 0.372·x    across the bands (20.4°)
e = z + 0.21·x     along the bands (cuts descend ~12°)

lower band:  c ∈ [−16.49, −15.46]   coral where e ∈ [16.35, 18.49]
upper band:  c ∈ [−12.88, −11.86]   coral where e ∈ [20.83, 23.05]
above the upper band → flight grey (tip cap)  ·  everything else → indigo
```

(787-9 reference frame; `spec_b789.json → cauda_livery.fin_bandas_2026-08-17`.
An earlier 13.5° model, `b = z − 0.24·x`, was wrong by dozens of sigmas —
if you find those constants anywhere, they are stale.)

**The brand artwork does NOT transfer between types — the placement is
type-specific.** The `(h,c)`-normalized transfer of the 787 bands to the A320
family was believed for three days and was exactly what the owner rejected as
*"as marcas nas caudas estão distorcidas"*: it put the lower band ~1.5 m too
high at the TE, made both bands ~half their real proportional thickness, and
left the aft tip indigo where the real cap is grey. Measured on PS-LBO
delivery photos (2026-08-20): on the A320 family the lower band enters through
the fin **root** (not the LE), the tip cap **widens** aft (on the 787 it
narrows), and the band thickness is the same **absolute** 0.96 m on both types
— LATAM paints one physical band width fleet-wide, so it cannot scale with the
fin. What generalizes: the internal angles (bands climb ~20.4°, coral cuts
descend ~12°) and the grey–coral–grey structure. What must be measured per
type, on a photo of that type: where each band edge crosses each fin edge.
Anchor the edges by those crossings — fractions of the exposed fin along
LE/TE/root — and the artwork lands right even if the model's planform taper is
imperfect (`spec_*.json → fin_bandas_2026-08-20`).

**Check the crossings in an elevation, not in the gate.** A crossing is a length
measured *along* a fin edge, so it can only be read in an orthographic view of
the fin, in the same `(x,z)` domain the texture is rasterized in. The seven gate
cameras are perspective at 90–250 m and CamCauda still foreshortens the root.
The panel is `render_fin_ortho.py` in the repository root:

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b "<aircraft>/<MASTER>.blend" \
    --python render_fin_ortho.py -- 1300 96
```

It writes `render_fin_ortho.png` beside the master, framed on the `Deriva`
bounding box, so it re-centres itself when the fin moves. **Re-run it in any
round that moves the empennage or repaints the fin** — the 2026-08-20 panels
were shot from a scratchpad, and the ACAP empennage round of 2026-08-21 left
three of them showing a fin the fleet no longer had, with nothing committed to
refresh them.

### Rectifying the photo is what unlocks the measurement

The fin is **flat**, so a photo of it is a homography — and for a telephoto
lens, an affine one. Reproject the photo onto the fin's `(x,z)` plane before
measuring: suddenly the artwork becomes rectangles and what was illegible
becomes obvious. That was the step that solved it after several frustrated
attempts at reading angles and thicknesses off the raw photo.

Determine the affine transform from two known directions (leading edge and tip
chord) plus a scale. Then **fit the parameters by coordinate descent** against
the photo classified into coral/indigo/grey: on CC-BGP that took the pixel-wise
agreement from 91.4% to **92.6%**. An agreement number is what lets you say "it
is right" without arguing about whether it "looks" right.

To find the band slope without guessing: sweep the slope `m`, group the pixels
by `b = z − m·x` and pick the `m` that **minimizes colour impurity per band**.
The correct band is the one that comes out a single colour.

**But the APPLICATION on the hull is type-specific — never extrapolate.** The
brand artwork on the fin repeats; what it does when it meets the fuselage does
not. Verified on photos of both registrations:

| | A320neo PT-TMN | 787-9 CC-BGK / CC-BGP |
|---|---|---|
| Rear fuselage | indigo comes down from the fin and **covers door 2** | indigo **triangular wedge**, straight forward boundary cutting across the rear door; crown and belly white |
| Registration | **white inside the indigo** | **white inside the indigo**, over the wedge |

In both cases the indigo comes down onto the fuselage — but with a **different
shape**, and that is what has to be measured per type. The rule is a photo of
**that type and that registration**.

This point had **two corrections in opposite directions**, and both are worth
keeping as a warning. First the spec described a sash that did not exist and
hours were spent refining its shape; then, on removing it, **too much** was
removed — the fuselage went entirely white, when the photo clearly shows the
wedge. The lesson is not "the photo wins" (that is already rule 4); it is that
**correcting an error in the opposite direction is also getting it wrong**. When
the owner points at an excess, measure how much to take off instead of zeroing
it.

## The hull écharpe — the model, and the five ways to get it wrong

The indigo patch on the rear fuselage is the **same mass** as the indigo at the
fin root, coming down onto the hull. Two boundaries define it, and **they live
in different spaces** — failing to see that is what cost four rounds.

```
indigo ⟺ x ≥ x0 + k·z              (FORWARD boundary — a straight line in the (x,z) plane)
       AND θ ≤ θ0 − r·(x − xr)      (LOWER boundary — a straight line in the (x,θ) plane)
       AND x ≤ x_tras
```

`θ` is measured from the crown; `z = centro_z(x) + raio(x)·cos θ`.

**787-9:** `x ≥ 48.77 + 0.992·z` ; `θ ≤ 117.0 − 5.2·(x − 48.70)` ; `x ≤ 57.14 + 0.3858·z`
**A320neo (PT-TMN, re-solved 2026-08-20):** `x ≥ 28.51 + 0.63·z` ; lower `z ≥ −1.2` and
`θ ≤ 145` (white keel, tip at 27.75) ; rear piecewise `z:[−1.2,1.6,1.8,2.05] →
x:[27.75, 32.80, 33.36, 33.85]` (meets the fin at the corrected ACAP station).

Warning from that re-solve: the previous A320neo line here (`27.39 + 0.8393·z`)
had been constructed parallel to the **mis-placed** fin LE of the old master and
sat ~1.1 m too far forward; the competing spec table (crown crossing at 31.3) was
crown-wrap projection bias from a from-below photo. Both were refuted by a
door-anchored measurement on the registration photo (residuals < 0.02 m over
z 0.4–1.6), cross-checked by the current-era registration and title positions
clearing the line by 0.04–0.09 m — the fleet's almost-touching style. Never
anchor a paint boundary to model geometry that has not itself passed the gate.

The rear limit is the **fin trailing-edge line itself**: the indigo stops at the
projection of the TE, and from there aft come the TE root fairing and the
tailcone, both white. Cutting at a constant `x` leaves indigo over the fairing —
that was the defect the owner pointed out with everything else already approved.

### Error 1 — modelling the lower boundary as a straight line in (x,z)

It was tried three times: a horizontal cut, 16° measured on a photo, and the
stabilizer line. **All three give a wedge that is too small.** The lower boundary
is a straight line in **(x, θ)**, not in (x, z). At the forward edge it comes
down to about 117° from the crown — well below the half-width, almost at the
keel — and narrows aft. Any straight line in (x,z) stops around 90° and the wedge
comes out stunted.

How to measure it: sweep the photo **column by column**; in each column find the
hull silhouette (top and bottom) and the lower edge of the indigo; convert to
`u = (y_ind − y_top)/(y_base − y_top)` and from there `θ = acos(1 − 2u)`. Fit
`θ(x)`. It comes out as a clean straight line. Calibrate `x` against the **window
pitch**, never against the nose-to-tail span.

### Error 2 — the forward boundary is not the leading edge

It is **parallel** to the fin's straight LE, offset about 0.10·H aft (0.86 m on
the 787, 0.62 m on the A320). And the 787's straight LE is **45.2°**, not the
40.5° the spec carried — 40.5° is the chord of the curved dorsal fairing. See
`extrair-cotas`.

### Error 3 — drawing the boundary as a straight line in the (x,θ) texture

A planar cut `x = x0 + k·z` **is not a straight line** in UV. Drawing a straight
line there is off by as much as 0.9 m at the waist. And **do not resolve the
boundary's `x` once per texture row**: that jags the edge and creates loose
islands of indigo, because the whole row is accepted or discarded. Each texel
already knows its own `x` and `θ`, hence its own `z` — the test is direct and
vectorized, with no iteration at all.

### Error 4 — painting "only where it was already white"

That leaves a hole at every panel line and door outline. `LiveryTex` mixes two
layers: **base** (white/indigo) and **markings** (registration, doors, panels).
When moving the boundary, apply the base colour **only to the flat texels** (pure
white or pure indigo) and leave the markings layer untouched — the outlines then
read on top of the indigo, as on the real aircraft.

Do not try to reconstruct by relative modulation (`orig / base`): it amplifies
the texture noise and duplicates markings that were nearly invisible. Tried, made
it worse.

**Registration:** white letters over the indigo. If the boundary moves and the
registration falls outside the patch, paint it **indigo over white** — a
legitimate LATAM variant — instead of trying to cut it out and paste it back.
Threshold-based cutting always breaks the glyph or drags a panel line along with
it.

### Error 5 — cutting the wedge at a constant `x` at the rear

The indigo does not end at a station; it ends at the **fin trailing-edge line**.
Behind it there is the light fairing at the TE root, which continues into the
tailcone. With a constant-`x` cut the indigo invades that fairing and the fin ×
stabilizer × tailcone junction comes out wrong — that was the last defect pointed
out, with the rest of the tail already approved. Check that corner zoomed in,
always.

### Error 6 — editing the wedge instead of rasterizing it

The one that produced holes, splinters and dotted boundaries on three different
types at once, and the reason `latam_livery_kit` now carries **one** écharpe
implementation (`secoes_do_casco`, `cobertura_echarpe`, `reparar_echarpe`) with
`reparar_echarpe.py` driving it.

Every builder painted its wedge once, and then every later script that touched
the tail changed it **conditionally**. Each condition has a complement, and the
complement keeps the old paint:

| condition | complement | what the owner sees |
|---|---|---|
| `nova & ~velha & flat_w` (A321) | any anti-aliased edge texel inside the band that changed | **dotted boundary** |
| `velha & ~nova & flat_i` (A321) | any old-wedge texel that was not exactly flat indigo | **detached splinter** |
| `np.abs(np.sin(THg)) > 0.10` (787-8) | `\|theta\| <= 5.74°` | **rectangular block across the crown** |
| `fac[m] = 0` as "erase" (fleet) | the base restored is hull white **whatever was underneath** | **white rectangle inside the indigo** |

So: **paint the wedge absolutely, from its rule, over the whole tail zone, with
supersampling; never as a difference of two rules and never gated on the texel
already being flat.** If a repair has to leave marks alone, protect them by
COLOUR — a texel is safe to write only if its effective colour lies on the
white→indigo segment — not by a geometric guard like `|sin θ|`. And an erase
inside the wedge must state its base (`refazer_marcas.Casco._basemap`,
`base="indigo"` / `"fronteira"`), never write `Fac = 0`.

Underneath all four sits the bridge: the rule lives in `(x, z)` and the texture
in `(x, θ)`, joined by `z(x, θ) = zc(x) + rz(x)·cos θ`. **Build that table from
the mesh, in world coordinates, one entry per station.** A hand-spliced table is
discontinuous at the splice and a discontinuity in `z(x)` is a step in any
boundary written as `x >= x0 + k·z`: the 767's `zc_rz()` joins the constant
mid-section to `cauda_estacoes` at `x = 41.0` with `Δzc = +0.117 m` and
`Δrz = −0.117 m`, and its wedge's lower edge jumps from `|θ| 114.02` to `117.04`
right there.

## The paint lives on the DEVELOPED surface — measure in (x, θ), never in (x, z)

This is the single error that had propagated furthest through the fleet. It was
found on the 767 build and then confirmed on every Airbus master and the 787-8.

A mark is painted onto the skin, so **its proportion is width / ARC**, not
width / Δz. The side projection foreshortens: for anything that climbs the
shoulder the flattening is about **25%**. The brand symbol crosses θ 38–95°, so
it is the worst affected; a registration sitting near θ 60–70° barely notices.

```
metres along x    = Δcolumns · fuselage_length / texture_width
metres along arc  = ∫ ds along the section between the two θ  (NOT R·Δθ if the
                    section is a double bubble, and NOT Δz ever)
ratio             = width_x / height_arc
```

The symptom, if you place in (x, z) instead: the mark's ratio comes out right in
the side render and ~20% squat on the aeroplane. On the 787-9 this is what once
made the lockup read *"28% stretched"*. On the five Airbus masters and the 787-8
the whole lockup had been pasted as **one block** whose ratio matched the
official 4.303 **in the (x,z) projection**; on the developed surface that reads
3.45, with the symbol 20% and the wordmark 14% off their own ratios.

### Symbol and wordmark are two marks, not one

Place them **separately**, each at its own official ink ratio, measured off the
lockup mesh:

| | official ratio (w/h) |
|---|---|
| symbol (indigo bars + coral) | **0.6223** |
| wordmark LATAM | **6.7308** |
| full lockup, print SVG | 4.3030 |

**And the aircraft does not use the print SVG's split.** In
`latam_logo_indigo.svg` the symbol is 0.18458 of the wordmark's width. On the
aeroplane it is **0.260** — the symbol is about 1.41× wider relative to the
wordmark. Measured on five registrations of five types, and they agree:

| CC-CWY 767 | PS-LBO A321neo | CC-BBF 787-8 | CC-BFO A320ceo | CC-BGP 787-9 |
|---|---|---|---|---|
| 0.2551 | 0.2598 | 0.253–0.259 | 0.2716 | 0.242 |

So the recipe, given the wordmark's measured x range (width `W`):

```
symbol width  S = 0.260 · W
gap           G = 0.065 · W          (symbol sits nose-side of the wordmark)
wordmark arc height = W / 6.7308
symbol   arc height = S / 0.6223
symbol top = wordmark cap line − 0.170 m of ARC
```

That reproduces the approved 767 build to within a few centimetres, which is how
it was validated.

**A corollary worth stating, because the older text here said the opposite:
checking the FULL lockup against 4.303 is checking the print sheet, not the
aeroplane.** With the aircraft's split and gap the full mark's ratio on the skin
is **≈3.15**. Check the two parts separately instead.

This also settles a question the 787-8 build raised: its photos gave the symbol
1.58–1.62 m wide against 1.16 m in the SVG "at the same height", and the overall
4.30 seemed to match. Both readings were right and there is no missing artwork —
it is the same art with a different split, and "the same height" had been
measured in z on a mark that crosses θ 29–76°.

### EVERY asymmetric mark is mirrored on starboard — count the mirrors

The hull texture is `(x, θ)` and **the same u serves both flanks**. Seen from
starboard the skin's `+x` runs to the **left** of frame (the nose is on the
right), so art painted with x increasing to the right comes out reversed there.
Registration, type title, lockup, country name, nose art — anything that is not
its own mirror image — has to be flipped for `lado = +1`.

It is not enough to *intend* the mirror; count how many the pixel actually gets.
Both failure modes have shipped in this repository:

- **Zero mirrors.** `for lado in (-1, 1)` with one set of triangles and no
  `espelha`. The 767-300ER, the 767-300F and the 777-300ER all read their
  registration backwards this way (`YWC-CC`, `AL635N`, `GUM-TP`), for as long as
  those aircraft existed. In the same files the *lockup* passed `espelha=True`
  correctly — the two calls sat a dozen lines apart.
- **Two mirrors.** `refazer_marcas.py` took a mesh **per side**,
  `("Reg_E", "Reg_D")`, *and* passed `espelha=(lado > 0)`. On the A319 and the
  A320neo, `Reg_D` is a separate datablock that is **already** the x-mirror of
  `Reg_E`, so the flip was applied twice and the A320neo read `NMT-TP`. The
  marks that survived — `MarkAirbusNeo`, `Reg787` — were exactly the ones whose
  `_D` object *shares* the `_E` mesh datablock.

The rule that removes the question: **state the art once, let the flank decide
the flip.** One canonical source mesh, `espelha=(lado > 0)`. Never infer the
mirror from which mesh you were handed.

Two things that follow, and are easy to get wrong on the way past:

- **The italic shear rides along.** `Xc = X + cis*(Y - ay)` is applied before
  the flip, so mirroring the box also mirrors the slant — which is correct: on
  the real aircraft the letters lean the same way *in reading order* on both
  flanks. Do not "fix" it by negating `cis`.
- **Read the effective colour, not `LiveryTex`.** The shader shows
  `mix(base, LiveryTex, LiveryFac)`. An erase that zeroes Fac leaves the dead
  ink sitting in Tex, so a raw dump of the texture shows ghosts and overlaps
  that no render has. Composite with Fac before you believe what you are
  looking at — the A321neo looks broken in Tex and is clean on the aeroplane.

The gate now has an eighth angle, `render_estibordo.png`, that is the exact
mirror of `render_perfil.png`; read the pair side by side. See skill
`verificacao-visual`.

### Starboard is mirrored PART BY PART, never as a block

The `_D` mesh in these blends is the whole lockup rotated 180°. Painting from it
inverts the composition and throws the symbol to the tail. **The symbol is
nose-side on both sides**; the wordmark is mirrored about its own centre so it
reads correctly from starboard (nose→tail it spells symbol, M, A, T, A, L). All
five Airbus masters had this defect; the 767 and 787-9 did not.

### Where (x,θ) and (x,z) agree, and where they do not

On the **cylindrical** section constant-z and constant-θ are the same line, so
the lockup can be placed either way there — the error above is purely one of
*proportion*, not of path. On the **tailcone** the radius shrinks and the two
diverge: a registration or a type title reads **horizontally** on the aeroplane,
which is a constant-**z** baseline, while its cap height is still measured along
the **arc**. Place those in "z mode": anchor the baseline in z, take the height
from width/ratio in arc. Placing them at constant arc tilts the text down the
cone.

### Erasing a mark without wrecking what is under it

Re-rasterizing means erasing the old ink first, and that has two traps.

**A "restore white" pass must not cross the wedge boundary.** Told to restore
white over a box that straddled it, the eraser cheerfully painted white letters
onto the indigo — the ghost was more visible than the mark had been. State which
side each erase box is on, and choose boxes that do not straddle.

**When a box must straddle, read the boundary back from the paint — do not
recompute it from the spec.** Rebuilding the A320neo's wedge edge from
`x ≥ 27.39 + 0.8393·z` left a visible step against the surrounding paint: the
painted wedge and that straight line are not the same curve. Instead take the
rows the mark does not touch, find the white→indigo transition on each, fit a
quadratic through them and carry it across the rows the mark hides. That lands
within 0.3 px and leaves no seam. (That `27.39 + 0.8393·z` has since been
re-solved — see the écharpe table above — which changes nothing here: the point
is that the paint, not the spec, is the boundary's own record.)

**And the read-back only works while the mark is not the wedge's colour.** The
same erase was run once with the type title repainted in indigo `#2A0088`
instead of its own navy `#1C2E63`: the row scan looks for the first indigo
column, found the title's left edge 2 m ahead of the wedge in the rows the
title occupies, and fitted a quadratic through two clusters — 92 px rms instead
of 0.35, and a white gash through the paint where it thought the boundary was.
If a mark inside the search window shares the boundary colour, either give the
mark its right colour first or move the box.

Restrict the erase to ink that lies on the blend line between the base and the
mark's own colour. That removes the mark and its anti-aliasing fringe while
window glass, door outlines and panel lines survive untouched.

The tool that does all of this is `refazer_marcas.py` at the project root.

## Material: making paint look like paint

The recipe the owner approved, in order of impact:

- **White `#E6E7EA`, never `#FFFFFF`.** Pure white blows out and kills the form.
- **Coat 1.0 with Coat Roughness 0.05** — the clearcoat is what reads as a new
  aircraft.
- **Roughness break-up**: `TexNoise` (scale 5, detail 6) → `MapRange` to
  0.32–0.48 → Roughness. A surface with constant roughness reads as plastic.
- **Orange peel on the Coat Normal**: `TexNoise` scale 1000 → `Bump` strength
  0.08, distance 0.0005. It is subtle and it is what sells the real scale.
- **Sun with a physical angle of 0.53°** (the real solar disc) — shadows with the
  correct penumbra.
- **Cloud card**: a large rectangular area light (60×20) as fill, imitating sky.
- **AgX Punchy with exposure ≈ −0.35**, keeping the whites around 0.8.

Window glass: **dark, not reflective**. The "the windows are white" feedback came
from glass that was too reflective. Base `#0B0F13`, roughness 0.28, coat 0.12,
specular 0.35. Door groove `#191B1D`, roughness 0.75, specular 0.1.

The windshield is a UV mask in the hull shader (`NoseMask`: R = matte frame,
G = glossy glass), never a 3D decal. The exact glass polygons are in the spec.

## Belly

Nobody looks until they look from below, and then the error jumps out. The real
thing: fuselage **all white** underneath; belly fairing and the lower surfaces of
wings/stabilizers in Airbus grey; a map of antennas, drains, beacon, outflow
valve and APU exhaust tabulated in `spec_a320.json → ventre_real`. A young fleet
has light weathering — a spray fan behind the nose gear and tan streaks 1 to 3 m
below the drains, painted into `LiveryTex/Fac` itself with a fractional factor.
