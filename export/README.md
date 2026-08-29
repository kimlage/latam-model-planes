# Portable exports — GLB, USDZ, FBX, OBJ

The repository's deliverable is a `.blend` per aircraft. This folder is the same
fleet in formats that open **outside Blender** — primarily **glTF 2.0 binary
(`.glb`) for three.js**, plus USDZ, FBX and OBJ for everything else.

```bash
python3 export_frota.py                    # whole fleet, both LODs  (~4 min)
python3 export_frota.py B77W A320neo       # just these
python3 export_frota.py --lod web          # just the light level
python3 export_frota.py --verificar        # do not export: read back what exists
python3 export_frota.py --verificar --reimportar   # …and re-open every format
```

Everything here is generated. Nothing in an aircraft folder is written, and no
`.blend` is ever saved — the export can run while another session edits a master.

## State of these files

**The pipeline is the deliverable; these binaries are not.** They were
regenerated on **2026-08-27**, from the masters as they stood after that day's
geometry and surface-print rounds: eleven aircraft at both LODs, 22 exports,
every one verified with no errors. Whatever [`QA-BACKLOG.md`](../QA-BACKLOG.md)
still listed open on that date is baked in here — an export is a photograph of
a master, never a fix for one. When a fix lands, re-run the aircraft:

```bash
python3 export_frota.py A321neo          # one aircraft, both LODs
python3 export_frota.py                  # or the whole fleet
```

The fleet reached eleven on 2026-08-26, when the two freighters — the
**767-300F** (N536LA) and the **767-300BCF** (CC-CXE) — were exported for the
first time. Neither needed a line of export code: they arrived as one row each
in `FROTA`, which is what that table is for.

The exported bounding boxes now agree with each aircraft's own `spec_*.json`,
**span to within 1 cm on all eleven**. This README used to report the opposite —
38.23 m of span read out of the A320/A321 files against 35.80 m declared, 36.92
m on the A319 against 34.10 m — and that was true when it was written and fixed
on the model side hours later, in `7aedc29`, without the prose following. Of
the other two axes: length agrees to within 2 cm on the 767s and the 787s and
reads 0.17–0.21 m long on the 777 and the five Airbus; height is within 0.10 m
on the Boeings and 0.23–0.26 m over on the Airbus. All of it sits inside the
±0.6 m the axis check allows. One residual belongs to the export rather than to
the masters: the GLB box comes out 0.13 m shorter than Blender measures on the
Airbus, 0.02–0.03 m on the Boeings, which is the `comprimento … medido no
Blender` note each `verificacao` block carries.

## Measured, per aircraft

Every number below was read back **out of the finished file**, not predicted.
Sizes in MB; `tris` is the triangle count parsed from the index accessors;
`MP` is the total megapixels of embedded texture; X/Y/Z are the glTF bounding
box in metres — length, height, span.

| Aircraft | Reg. | `web` tris | `web` .glb | `web` MP | `alta` tris | `alta` .glb | .usdz | .fbx | .obj+tex | X | Y | Z |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Airbus A319 (ceo) | PT-TMT | 58,232 | 1.2 | 34.6 | 314,168 | 10.4 | 3.7 | 8.5 | 29.3 | 34.05 | 11.99 | 34.10 |
| Airbus A320ceo | CC-BFO | 63,936 | 1.2 | 34.6 | 334,272 | 10.9 | 4.0 | 9.0 | 31.3 | 37.78 | 11.99 | 35.80 |
| Airbus A320neo | PT-TMN | 62,456 | 1.2 | 34.6 | 332,792 | 11.0 | 3.9 | 9.1 | 31.3 | 37.78 | 11.99 | 35.80 |
| Airbus A321-231 (ceo) | PT-MXP | 66,728 | 1.2 | 34.6 | 348,584 | 11.4 | 4.1 | 9.2 | 32.4 | 44.72 | 12.02 | 35.80 |
| Airbus A321neo (ACF) | PS-LBA | 67,716 | 1.3 | 34.6 | 349,572 | 11.5 | 4.2 | 9.3 | 32.6 | 44.72 | 12.02 | 35.80 |
| Boeing 767-300ER | CC-CWY | 61,673 | 0.6 | 13.6 | 333,005 | 9.1 | 3.3 | 7.7 | 29.4 | 54.96 | 15.75 | 50.89 |
| Boeing 777-300ER | PT-MUG | 47,805 | 0.6 | 17.8 | 326,241 | 9.1 | 2.7 | 7.6 | 29.4 | 74.03 | 18.51 | 64.74 |
| Boeing 787-8 Dreamliner | CC-BBF | 60,423 | 0.7 | 13.6 | 351,975 | 9.5 | 3.3 | 8.1 | 30.6 | 56.74 | 16.92 | 60.11 |
| Boeing 787-9 Dreamliner | CC-BGK | 62,935 | 0.7 | 13.6 | 362,167 | 9.7 | 3.5 | 8.2 | 31.4 | 62.83 | 17.02 | 60.11 |
| Boeing 767-300F | N536LA | 51,061 | 0.6 | 13.6 | 322,393 | 8.8 | 2.9 | 7.4 | 28.5 | 54.96 | 15.75 | 50.89 |
| Boeing 767-300BCF | CC-CXE | 51,061 | 0.6 | 13.6 | 322,393 | 8.8 | 2.9 | 7.5 | 28.6 | 54.96 | 15.75 | 50.89 |

**Whole fleet: 9.8 MB of `web` GLB** (committed), 38.5 MB of USDZ and 536.5 MB
of `alta` (both regenerated on demand). An export takes 6–10 s per aircraft per
LOD, 26–40 s for the 767 whose bake is the largest — that pair of figures was
timed on the 2026-08-21 run. `manifest.json` carries no timings by design (it is
what keeps re-runs byte-identical), so it is the only number in this section not
read back out of the current files.

## See it now

```bash
cd export && python3 -m http.server 8000
open http://localhost:8000/viewer.html
```

[`viewer.html`](viewer.html) is a single self-contained page: three.js from a CDN
import map, orbit controls, image-based lighting, a picker for the whole fleet,
and DRACO decoding wired up. It reports the triangle count, material count and
measured dimensions of whatever it loaded, so it doubles as a second opinion on
the export.

It **must be served over HTTP**. Opening `viewer.html` from disk gives a blank
model and a CORS error in the console: a `file://` page is not allowed to fetch
the `.glb` next to it. That is a browser rule, not a fault in the export. The
CDN import map also means the page needs internet on first load.

## The two levels of detail

|  | `web` | `alta` |
|---|---|---|
| Subdivision | Catmull-Clark capped at **level 1** | as authored (**level 2–3**) |
| Textures | capped at **2048 px** | native (up to 8192 px) |
| Mesh compression | **Draco** | none |
| Roughness | one baked scalar per material | baked **map** |
| Formats | `.glb`, `.usdz` | `.glb`, `.fbx`, `.obj`+`.mtl` |
| For | three.js, web, mobile AR | desktop, DCC, Unity/Unreal, offline |

### Why those two numbers, measured on the 777-300ER

Everything below is a measurement on `B77W_LATAM.blend`, not a preference. The
visual column is the mean absolute pixel difference against the reference
variant, over Cycles renders at two canonical gate angles, 1280×720, 64 samples.

The study was run on 2026-08-21 and has not been repeated. The master has gained
paint since — the 777's `web` LOD measures 17.8 MP in the table above, against
the 9.44 below — so read these columns as the comparison that fixed the two
knobs, not as today's file sizes.

**Subdivision cap** — textures held at 2048, Draco on:

| cap | triangles | `.glb` | vs. as-authored |
|---|---|---|---|
| as authored (2–3) | 325,344 | 725 kB | — |
| 2 | 170,208 | 605 kB | 0.004 % / 0.013 % |
| **1** | **46,908** | **412 kB** | **0.051 % / 0.054 %** |
| 0 | 16,364 | 334 kB | 0.175 % / 0.200 % |

Level 1 is 7× lighter than the authored mesh and the rendered difference is
**0.05 %** — invisible even in the nose close-up, which is the angle that broke
two windshields in this project's history. Level 0 is where faceting starts:
the difference quadruples and the nose silhouette visibly flattens. The subsurf
level is the right LOD knob here precisely because the hull is a sparse
Catmull-Clark cage — dropping a level preserves UVs, materials and silhouette
in a way no decimator does.

Note what the file-size column also says: **Draco compresses so well that
geometry stops being the download cost.** The 325k-triangle mesh is only 313 kB
bigger than the 47k one. Level 1 is chosen for **runtime** cost — triangles,
GPU memory, draw time on a phone — not for bytes.

**Texture budget** — subdivision held at 1, Draco on:

| cap | megapixels | `.glb` | vs. 4096 |
|---|---|---|---|
| 4096 | 12.58 | 481 kB | — |
| **2048** | **9.44** | **412 kB** | **0.016 % / 0.024 %** |
| 1024 | 2.36 | 282 kB | 0.035 % / 0.058 % |
| 512 | 0.59 | 229 kB | 0.066 % / 0.104 % |

2048 matches 4096 to two hundredths of a percent. Below it the LATAM wordmark
softens and the fin sash edges go fuzzy — visible in a side-by-side crop, which
is why 1024 was not taken despite being 130 kB cheaper. If you want that trade,
it is one number: `textura_max` in `LODS` in
[`frota_portatil.py`](frota_portatil.py).

**Draco** — at subdivision 1: 1,165 kB → **412 kB**, 2.8× smaller. At the
authored subdivision: 8,052 kB → 725 kB, **11.1×**. Loading it in three.js needs
three lines (see below) and is worth it at every level.

**PNG, not JPEG.** Forcing JPEG q88 on the web LOD made the file **27 % bigger**
(512 kB against 404 kB): LATAM paint is flat vector-derived art, not photography,
and PNG's filters beat DCT on it. Measured, then reverted.

## What is actually in a `.glb`

A per-aircraft breakdown is in [`manifest.json`](manifest.json) — measured, not
declared: every number there was read back out of the finished file.

- **One root node** named for the aircraft (`B77W`, `A320neo`, …), with every
  part as its child. `scene.getObjectByName('B77W')` gets you the whole jet.
- **+Y up, metres, wheels on `y = 0`.** Blender is +Z up; the exporter converts,
  and this pipeline *verifies* the conversion instead of trusting the flag — see
  below. The repository's frame (x = 0 at the nose tip, y = 0 on the symmetry
  plane) survives; only the height datum moves, from mid-fuselage to the ground,
  because a viewer that assumes a ground plane at `y = 0` would otherwise bury
  the aircraft 5.7 m.
- **Textures embedded**, no side-car files. Materials are metallic-roughness
  with `KHR_materials_clearcoat` on the painted surfaces.
- **No cameras, no lights, no runway, no scenery.** See *Licensing*.

### The livery had to be baked, and why that matters

Exporting a master straight to glTF **silently loses the paint**. Measured on
the 777: 30 materials → 17, 8 textures → 3, and the fuselage came out flat grey.

The cause is structural. `FuselagemPaint` — the paint on all eleven aircraft — is
not a Principled BSDF: it is three of them mixed by channels of an 8192×2048
nose mask, with the base colour coming from a `Mix` of `LiveryFac` over
`LiveryTex`. glTF can represent exactly one Principled per material. The
exporter does not warn; it writes grey and moves on.

So the pipeline finds those materials by a **structural test** — the Output's
Surface must come straight from a Principled, and that Principled's scalar
inputs may only come from an Image Texture or a Normal Map — and Cycles-bakes
each failing material into a texture glTF *can* carry. On the current fleet the
test catches exactly two materials — `FuselagemPaint` and `CinzaAsa`, on all
eleven aircraft — and it caught both of them on the two freighters the first run
they appeared in, without anyone editing a list of names.

Proof that the bake is faithful: the same scene rendered before and after
remediation, three canonical angles, 1280×720/64 samples —

| angle | mean difference | 99th pct |
|---|---|---|
| profile | 0.19 % | 7/255 |
| nose close-up | 0.73 % | 10/255 |
| tail | 0.36 % | 12/255 |

The residual sits on specular highlight edges and the outlines of the windshield
panes; the wordmark, symbol, window row, titles, registration and rear écharpe
are unchanged.

Objects whose material fails the test **and that carry no UV map at all** cannot
receive a baked texture, so they get a flat base colour walked out of the node
tree. On the current fleet that fallback reaches `CinzaAsa` on the horizontal
stabiliser of the A320ceo, both A321s and the 777 (which carries it as two
halves), and on the twelve flap canoes of each of the three 767s — never on a
wing, which carries UVs and is baked on all eleven. Without a UV layer the
material's image inputs sample one texel anyway, so the flat colour is what
those meshes already rendered. `manifest.json` records, per object, which of the
two methods it got.

## Loading in three.js

```js
import { GLTFLoader }  from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';

const draco = new DRACOLoader().setDecoderPath(
  'https://unpkg.com/three@0.169.0/examples/jsm/libs/draco/gltf/');

new GLTFLoader().setDRACOLoader(draco).load('web/B77W_web.glb', gltf => {
  scene.add(gltf.scene);          // +Y up, metres, wheels at y = 0
});
```

Two things the models assume:

- `renderer.outputColorSpace = THREE.SRGBColorSpace` — the default in current
  three.js, but set it if you have touched it.
- **An environment map.** The paint carries clearcoat; with only direct lights
  it has nothing to reflect and reads as flat vinyl. `RoomEnvironment` through a
  `PMREMGenerator` is enough and costs nothing extra — `viewer.html` shows it.

The `alta` GLB is not Draco-compressed, so `DRACOLoader` is optional for it.

## What each format loses

| Format | Carries | Loses |
|---|---|---|
| **GLB** (primary) | full metallic-roughness PBR, clearcoat, embedded textures, node hierarchy, +Y up, Draco | the Blender shader trees — everything is the baked/derived approximation described above. No cameras, lights or scenery, deliberately |
| **USDZ** (iOS / AR Quick Look) | geometry, UVs, base-colour and roughness textures packed uncompressed into the archive, +Y up. Blender does write `clearcoat` onto the UsdPreviewSurface | renderer support for that clearcoat varies — on AR Quick Look expect the paint to read flatter than in the GLB. No mesh compression, so the archive is ~6× the `web` GLB. Subdivision is tessellated on export rather than left as a subdiv surface |
| **FBX** (Unity, Unreal) | geometry, UVs, embedded textures, +Y up, object hierarchy | PBR itself: FBX materials are Lambert/Phong, so metallic, roughness and clearcoat arrive as approximations. Expect to rebuild materials on the engine side and reuse the embedded texture maps |
| **OBJ + MTL** (universal) | geometry, UVs, per-object groups, `map_Kd`/`map_Ns` into `textures_<slug>/` | everything else: no PBR, no node hierarchy beyond groups, no vertex colours, textures are loose files next to the `.obj` rather than embedded. Materials with no texture arrive as flat `Kd` |

USDZ is produced from the `web` LOD (AR is a mobile target); FBX and OBJ from
`alta` (engine and DCC users want the faithful mesh).

## Verification — what is actually checked

A file that exists is not a file that loads.
[`verificar_glb.py`](verificar_glb.py) is a dependency-free GLB reader: it opens
the container at the byte level, validates the header and both chunks, walks the
node hierarchy, counts triangles from the index accessors, confirms every image
is embedded in a bufferView rather than referenced by URI, reads image
dimensions straight out of the PNG/JPEG/WebP headers, and reconstructs the world
bounding box from the accessor `min`/`max` propagated through the node matrices.

`export_frota.py` then confronts those numbers with the aircraft itself:

- **geometry** — triangles in the `.glb` equal the triangles Blender evaluated
- **axis** — X must be the length, Y the height, Z the span, and the length must
  match the published figure within 0.6 m. This is the only honest way to check
  the +Z→+Y conversion: a wrong flag produces a file that opens fine and lies
  down sideways
- **ground** — the smallest Y must be ≈ 0
- **symmetry** — the span must straddle Z = 0
- **NaN** — the position accessors are actually read and scanned (skipped where
  Draco compresses them, where the accessor `min`/`max` is the available check)

Run it standalone on anything:

```bash
python3 export/verificar_glb.py export/web/B77W_web.glb
```

### …and the other three formats, by going back through Blender

A byte-level reader only exists here for GLB. USDZ, FBX and OBJ get the one
check that needs no library and cannot be fooled: **re-open the file in an empty
Blender and measure what came back.**

```bash
python3 export_frota.py --verificar --reimportar
```

[`reimportar.py`](reimportar.py) imports each artefact into a factory-fresh
scene and prints objects, triangles, materials, textures and the bounding box —
back in Blender's own +Z-up frame, where the length must land in X, the span in
Y and the height in Z. Across the fleet the artefacts return **identical
object, triangle, material and texture counts and an identical bounding box** to
their GLB sibling, wheels on `z = 0`.

That reading was taken on the 45 artefacts of the 2026-08-21 fleet. The fleet is
55 artefacts now — 11 aircraft × 5 formats — and no re-import pass has been
committed since, so the FBX, OBJ and USDZ of the current run are the one tier
this README does not vouch for. The GLBs are re-read on every export.

This is not a formality. It is what caught the FBX exporter silently dropping
`RegPortaTrem` — the gear-door registration, which is a **`FONT`** object on the
five Airbus and therefore outside the default FBX `object_types`. The GLB and
the OBJ carried it; the FBX came back 800 triangles and one material short, and
nothing in the export log said so. Reading the file was the only way to know.

## What is in git, and what is not

**Committed:** this README, the three scripts, `viewer.html`, `manifest.json`,
and **`web/*.glb`** — about 0.9 MB per aircraft, so a fresh clone can serve the
folder and see the fleet immediately.

**Not committed** (see the repository [`.gitignore`](../.gitignore)): `alta/`
in full and the `.usdz` files. Together they are roughly 575 MB of derived
binaries that one command regenerates:

```bash
python3 export_frota.py             # everything
python3 export_frota.py --lod alta  # just the heavy variants
```

Same rule the repository already applies to `scenario/scl_terrain.blend`: large,
derived, one command away.

Re-running is safe to do at any time: **the `.glb` files come out byte-identical
between runs** on an unchanged master (verified with `shasum`), so a re-export
that changed nothing shows up as no diff. `manifest.json` is written without the
per-run timings for the same reason. The one field that does move is the `.usdz`
byte count — a zip stores modification times, so its padding shifts by a few
dozen bytes each run. That is also why the `.usdz` files stay out of git.

## Licensing — the same notices as the rest of the repository

These files are exports of the repository's models. They inherit exactly the
licences in [`../NOTICE.md`](../NOTICE.md), and nothing here grants more:

- **3D models — [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).**
  Attribution: *LATAM fleet 3D replicas — Kim Lage — CC BY 4.0*. That string is
  written into every `.glb` as `asset.copyright`, so it travels inside the file.
- **The scripts in this folder — [MIT](../LICENSE)**, like the rest of the code.
- **Trademarks.** The models depict **LATAM**'s livery and carry **Airbus**,
  **Boeing** and **Dreamliner** titles. Those marks belong to their owners. This
  is an independent, non-commercial project with **no affiliation, sponsorship
  or endorsement**. CC BY 4.0 covers this project's own authorship — the mesh,
  the measurements, the scripts — and **grants no rights over the marks**.
  Commercial use of the livery needs permission from the owners.
- **Geometry provenance.** The hulls were built from dimensions in the
  manufacturers' public documents (Airbus ACAP, Boeing *Airplane
  Characteristics*). No third-party mesh was used. Those documents are free to
  download but not free to redistribute, and they are not in this repository.

### `scenario/` is deliberately excluded

The SCL airport under [`../scenario/`](../scenario/) is **not exported, in any
format, at any LOD** — the exporter drops linked-library objects and any ground
plane before writing.

The reason is a different and stricter obligation. `scenario/scl_field.blend` is
generated directly from OpenStreetMap data, which makes the mesh a **derived
database under ODbL 1.0 — share-alike**. Redistributing it, or a render of it,
or an aircraft file that links it, would drag that share-alike requirement onto
the exported asset and put it in conflict with the CC BY 4.0 the models carry.
The aircraft alone have no such entanglement. The `Pista` ground plane that the
visual gate uses is dropped for the same reason it exists — it is the gate's
floor, not part of the aeroplane.

If you want the scenery, build it from the repository with
`scenario/build_scenery.py` and keep the ODbL notice with whatever you make.
