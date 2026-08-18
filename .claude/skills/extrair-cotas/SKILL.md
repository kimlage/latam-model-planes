---
name: extrair-cotas
description: Turn dimensioned drawings (ACAP/APR) and photos into usable numbers — rasterize the PDF, calibrate against a printed dimension, extract hull crown/keel/half-width, measure windshield/doors/livery by photogrammetry, and write curves.json + spec_<type>.json. Use ALWAYS when you need real coordinates for any part of an aircraft: "measure the 767 nose", "extract the curves from the drawing", "where is door 2", "what shape is the windshield", "the proportions are wrong", "calibrate this against the photo". Use it as well when the model does not match the reference and the cause may be a wrong dimension. Brings the ready-made script and the calibration traps that have already produced deformed hulls.
---

# Extracting dimensions from drawings and photos

The goal is always the same: start from a PDF or a photo and end up with
coordinates in metres, in the aircraft's reference frame, written to JSON. Once
written, the number never has to be measured again — and the model can be
rebuilt from scratch without losing fidelity.

## Reference frame — fix it before measuring anything

The whole repository uses the same one, and mixing reference frames is the
easiest way to produce a crooked aircraft:

- **x = 0 at the nose tip**, growing aft, in metres;
- **z = 0 at the mid-height of the constant section**, positive up;
- **y = 0 on the plane of symmetry**, positive to starboard.

Watch out for manufacturer data. Airbus *stations* (STA) are measured from an
X0 that sits **2540 mm ahead of the nose tip** — so `x = STA − 2540`. And the
same family mixes units: the SRM gives STA in cm, the AMM gives it in mm. The
static attitude is not zero either (the 787-9 sits with −0.52° nose down); the
model is built in the aircraft's frame, not the ground's.

## From PDF to numbers

### 1. Rasterize
```bash
pdftoppm -f 21 -l 21 -r 600 -png "B787_APR_boeing.pdf" apr600_p21
```
600 dpi resolves everything that matters; 1200 dpi is only worth it for fine
detail such as the windshield. A stupid trap that has already cost time: **the
`pdftoppm` page index is neither the printed number nor what Read shows you** —
in the A320 ACAP the 3-views were on raw pages 44–45, not 6–7. Confirm by
opening the PNG.

### 2. Anchor by hand, on enlarged crops
This is the one step that cannot be automated, and it determines whether
everything else is any good. Crop and enlarge the anchor regions and **look**
to find the exact pixels:

```python
from PIL import Image
im = Image.open("apr600_p21-021.png")
im.crop((825, 3960, 1320, 4488)).resize((990, 1056)).save("insp_nariz.png")
im.crop((3630, 3960, 4257, 4488)).resize((1254, 1056)).save("insp_cauda.png")
im.crop((2310, 5082, 2904, 5610)).resize((1188, 1056)).save("insp_frontal.png")
```

Keep those `insp_*.png` in the aircraft's folder — they document where each
anchor came from.

### 3. Extract
Use the ready-made script:
```bash
python3 .claude/skills/extrair-cotas/scripts/extrair_contorno.py config.json
```
`scripts/exemplo_config.json` is the real 787-9 config, annotated. It already
carries the whole recipe: mask, median cleanup, bridging over occlusions,
monotonicity, normalization and the sanity dimensions. Run against the 787-9
drawing it reproduces the project's validated spec to within a few centimetres.

Two masks, because the two manufacturers draw differently:

- **`amarelo`** — Airbus ACAP, filled silhouette. It picks up the interior
  (`R−B > 15 & R > 170`) instead of the stroke, which avoids capturing dimension
  lines.
- **`linhas`** — Boeing APR, line art. A dark pixel (`< 128`) is outline.

### 4. Check sanity — and understand what the error means
The script prints measured height and width against the ones in the document.
The size of the error tells you what to do:

| Error | Cause | What to do |
|---|---|---|
| < 3% | reading bias (stroke thickness inflates the height; the dimension halo bites into the width) | normalize each axis by `doc/measured` — the script already does it |
| > 4% | a genuinely wrong anchor | go back to the crops |

The >4% case has happened: the 787 side band picked up fuselage and stabilizer
together and the "tail" came out at 79 m. No filter tweak fixes that — only
re-anchoring.

## The three traps that produced a wrong hull

**A white dimension halo becomes a phantom waist.** Dimension arrows have a
light halo that bites into the filled silhouette. On the A320 that produced a
"waist" of 0.22 m half-width at x≈6 — the hull was strangled there and the
decals passed straight through it. The defence is to impose monotonicity: the
width only grows going aft in the nose and only shrinks going aft in the tail
(`np.maximum.accumulate`).

**Another part touching the outline.** Wing, nacelle, gear and stabilizer cross
the fuselage band. Interpolate over the gap instead of trusting the pixel — on
the 787 the gaps were `keel` at 4–8 m (nose gear) and 16.5–34 m (nacelle + wing
+ main gear), and `crown` at 20–30 m.

**The top view lying about the tail.** The horizontal stabilizer crosses the
band and the half-width extracted there is garbage. Do not try to salvage it:
derive the width from the lateral radius. On the 787, `w = 0.96·rz`; on the
A320, `w = 0.954·r`.

## Calibrating against the right dimension

Pick a printed dimension that is long and unambiguous. But **read what it
measures**: on the 787-9 the 62.00 m dimension is the distance on the **ground**
between the vertical projections of the nose and the tip of the tailcone — not
the length. The real length is 62.81 m, because the tailcone ends at z=+1.66,
well above the ground. Calibrating against it is correct; treating it as the
length is not. That error made it through an entire research workflow before
cross-validation caught it.

Hence the rule: **calibrate with one dimension and validate with at least two
others.** Fuselage height, width, wheelbase and stabilizer span are good
witnesses. If all three agree to within 1–2%, the calibration is good.

## From curves to spec

`curves.json` is raw, noisy data. `spec_<type>.json` is what the model consumes,
and it stores **discrete stations at the real frames**, not the pixel cloud —
because that is what makes the hull smooth (see `casco-parametrico`). Densify
with PCHIP (C² interpolation, monotone, no oscillation between points) to
generate the intermediate `<type>_hull_smooth.json`.

`spec_*.json` must contain, at minimum: overall dimensions, nose stations
`[x, crown, keel, meia_largura]`, tail stations `[x, centro_z, raio]`, master
section, windshield polygons, doors (pax/cargo/overwing), windows, wing,
empennage, engine, landing gear, and a `confianca` field saying what is an
official dimension and what is photogrammetry. See
[spec_b789.json](boeing%20787-9/spec_b789.json) and
[spec_a320.json](airbus%20A320neo/spec_a320.json) as templates.

## Photogrammetry on photos

What the document does not carry — livery application, shade, weathering,
variation by registration — is measured on a photo. The technique that worked:

**Calibrate against something of known size inside the photo itself.** The
cabin window pitch is excellent (0.515 m on the A320, 0.61 m on the 787)
because it repeats along the whole hull; the centre of a door with a known x
gives the second anchor. With both, a 1920 px side-profile photo gives about
51–52 px/m.

**Never calibrate against the aircraft's overall length in the photo.** It
looks like the most obvious dimension and it is the most treacherous: the
aircraft only has to be slightly yawed for the nose-to-tail span to shorten by
perspective. On a photo of CC-BGP, nose-to-tail calibration was off by **14%** —
and because the error is a scale factor, it displaces *every* measurement
plausibly, with nothing looking wrong. The window pitch is immune: it is a
repeated dimension, so perspective shows up as variation in the pitch and you
notice. Always validate by reprojecting: if the anchor predicts the nose tip at
x≈0 and the tail at the official length, the scale is good.

**A colour threshold does not separate same-coloured parts that overlap in
projection.** Measuring the 787's rear fuselage paint by "which pixels are
indigo" failed repeatedly because **the fin is also indigo** and covers the hull
in side view. The result was tables that changed on every attempt. When two
parts share a colour, enlarge the crop and **read the boundary by eye** — it is
more reliable than any threshold, and faster than discovering this after five
iterations.

**Two points do not define a curved leading edge.** The 787-9 spec gave the fin
as `raiz_le=(50.10; 2.97) → topo_le=(60.20; 11.60)`, i.e. 40.5°. Measured on the
official drawing at 600 dpi, the **straight run** of the LE is
`x = 47.91 + 0.9920·z`, i.e. **45.2°** — and below z≈5.5 the LE curves *forward*,
turning into the dorsal fairing. The spec's two points were the **chord** of
that curve. Everything derived from it (including transfer between types by
tangent ratio) comes out contaminated. When tabulating a surface, record the
**straight run as a straight line** and the fairing as a separate curve, never
both as one segment.

**Check camera ELEVATION, not just yaw.** Yaw is the known trap; elevation is
the forgotten one. With the camera off-axis by `e`, every point on the skin is
displaced by `w(z)·sin(e)`, where `w` is the local half-width — zero at the
crown, ~2.9 m at the waist. That **curves** the projection of any boundary on
the hull (but not on the fin, which sits at y=0) and shifts the measurement by
up to 0.44 m with only 8.5°. Cheap test: the crown-to-window-line distance has a
known value from the drawing; if it comes out shorter, the camera is below the
axis. Alternative: the vertical separation of the two main gear bogies (known
track).

**Choose the right space before fitting a line.** A paint boundary may be
straight in `(x,z)`, in `(x,θ)`, or in neither. The 787's rear wedge is straight
in `(x,θ)`, and three successive fits in `(x,z)` gave plausible results that
were all wrong. Before fitting, measure in **two spaces** and see which one
makes the residual collapse.

**Use a near-pure side profile.** At mid-fuselage the projection is nearly
orthographic. Near the nose and the tail, perspective already bites — declare a
larger uncertainty there.

**Cross-check photos.** Two independent photos agreeing to within 0.3 m is a
result; a single photo is a hypothesis. Record the uncertainty in the spec
(`±0.3 m` is typical) and the URL of every photo.

**Date the photo.** The livery changes. The 2016 PT-TMN has the registration in
white inside the indigo; today it is indigo over white. Note the variation in
the spec instead of silently choosing — and follow the photo the owner
supplied.

**Delegate to agents with a schema.** The most complete measurements in the
project (PT-TMN tail, CC-BGK livery, A320 windshield) came from workflows with
a structured schema asking for polygons and cross-validation. See
`fontes-aeronave` for how to build the schema.
