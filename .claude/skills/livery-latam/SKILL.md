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
b = z − 0.24·x     across the bands
e = z + 0.25·x     along the bands

lower band:  b ∈ [−6.725, −5.99]   coral where e ∈ [22.006, 23.332]
upper band:  b ∈ [−4.208, −3.35]   coral where e ∈ [24.913, 26.192]
b ≥ −3.35 → flight grey (tip cap)   ·   everything else → indigo
```

(787-9 reference frame; `spec_b789.json → cauda_livery.fin_bandas_medidas_2026_08_17`)

**The brand artwork is the same on every aircraft — only the fin scale
changes.** Transfer it through normalized coordinates
`h = (z−z_root)/(z_tip−z_root)` and `c = (x−LE(z))/(TE(z)−LE(z))`: convert the
new aircraft's texel into `(h,c)`, take that `(h,c)` back into the 787 reference
frame and evaluate `b`/`e` there. That is how the A320 got the artwork without
re-measuring anything.

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
**A320neo:** `x ≥ 27.39 + 0.8393·z` ; `θ ≤ 101.4 − 7.58·(x − 29.11)` ; `x ≤ 34.52 + 0.0538·z`

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

## Check the PROPORTION of the lockup, not just the artwork

Rasterizing from the official SVG guarantees the shape of each glyph, but it
**does not guarantee that the result was pasted at the right proportion**. On the
787-9 the fuselage lockup was **28% stretched vertically**: 8.96 m long by 2.67 m
high, when the official vector has a ratio of **4.30**. The artwork was perfect
and the assembly was wrong — and the side effect was the brand encroaching on the
window row.

The check is arithmetic and takes seconds, but **there is a catch: the texels of
the (x,θ) texture are not square**. Convert to metres before dividing:

```
metres per column = fuselage_length / texture_width
metres per row    = 2π·radius       / texture_height
ratio = (n_columns · m_per_column) / (n_rows · m_per_row)
```

Compare against the ink bounding-box ratio of the SVG itself. If they differ,
fix whichever dimension is wrong and **anchor on the side that is already
right** — on the 787 the anchor was the top, which as a bonus lifted the brand
off the windows.

When rescaling already-rasterized ink, use **area averaging**, never nearest
neighbour: with nearest the letters come out jagged and the owner sees it. And
clean up the anti-aliasing fringe of the old version, otherwise a ghost remains
— but **restrict the cleanup to the mark's own bounding box**. Cleaning
"everything with saturation" over a wide band erased pieces of the door outlines,
which are also slightly tinted.

It is the same brand — so it must be literally the same geometry. Import it from
the finished `.blend` with `bpy.data.libraries.load` instead of re-importing the
SVG and risking a drift in scale or in the outlines.

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
