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

## State of these files — a re-run is required after the QA fixes

**The pipeline is the deliverable; these binaries are not.** They were generated
on 2026-08-21 from the masters as they stood that morning, while
[`QA-BACKLOG.md`](../QA-BACKLOG.md) still listed open defects on most of the
fleet — the A320-family windshields, the 787 radome joint, the A321 wordmark's
broken "M", the A320ceo ghost door. **Every one of those defects is baked into
the exports here.** When a fix lands, re-run the aircraft:

```bash
python3 export_frota.py A321neo          # one aircraft, both LODs
python3 export_frota.py                  # or the whole fleet
```

Nine of the ten aircraft in the table exported and verified clean. The tenth,
the **Boeing 767-300F**, has no master yet — it is being built in
`boeing 767-300F/`, its row is already in `FROTA`, and it will export on the
next run without anyone editing anything.

One measurement worth passing back to the model side rather than the export
side: the exported bounding boxes agree with each aircraft's own
`spec_*.json` to within a few centimetres on all four Boeings, and are **2.4–2.8
m wide on all five Airbus** — 38.23 m of span read out of the A320/A321 files
against 35.80 m declared in their specs, 36.92 m on the A319 against 34.10 m.
That is a property of the masters, not of the export (Blender measures the same
figure directly), and it is not in the QA backlog.

## Measured, per aircraft

Every number below was read back **out of the finished file**, not predicted.
Sizes in MB; `tris` is the triangle count parsed from the index accessors;
`MP` is the total megapixels of embedded texture; X/Y/Z are the glTF bounding
box in metres — length, height, span.

| Aircraft | Reg. | `web` tris | `web` .glb | `web` MP | `alta` tris | `alta` .glb | .usdz | .fbx | .obj+tex | X | Y | Z |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Airbus A319 (ceo) | PT-TMT | 57,250 | 0.5 | 9.4 | 308,386 | 8.3 | 3.0 | 6.5 | 26.4 | 33.98 | 11.71 | 36.92 |
| Airbus A320ceo | CC-BFO | 62,954 | 0.5 | 9.4 | 328,490 | 8.8 | 3.3 | 6.8 | 28.1 | 37.71 | 11.71 | 38.23 |
| Airbus A320neo | PT-TMN | 61,474 | 0.6 | 9.4 | 327,010 | 8.8 | 3.2 | 6.9 | 28.0 | 37.71 | 11.71 | 38.23 |
| Airbus A321-231 (ceo) | PT-MXP | 65,746 | 0.6 | 9.4 | 342,802 | 9.2 | 3.4 | 7.1 | 29.2 | 44.65 | 11.71 | 38.23 |
| Airbus A321neo (ACF) | PS-LBA | 66,734 | 0.6 | 9.4 | 343,790 | 9.3 | 3.5 | 7.1 | 29.3 | 44.65 | 11.71 | 38.23 |
| Boeing 767-300ER | CC-CWY | 60,428 | 0.6 | 13.6 | 326,960 | 8.9 | 3.2 | 7.4 | 28.8 | 54.75 | 15.75 | 50.89 |
| Boeing 777-300ER | PT-MUG | 46,908 | 0.4 | 9.4 | 325,344 | 8.6 | 2.5 | 7.1 | 28.3 | 73.93 | 18.51 | 64.74 |
| Boeing 787-8 | CC-BBF | 59,256 | 0.6 | 13.6 | 346,008 | 8.6 | 3.3 | 7.3 | 29.4 | 56.74 | 16.48 | 60.11 |
| Boeing 787-9 | CC-BGK | 61,768 | 0.6 | 13.6 | 356,200 | 8.9 | 3.4 | 7.4 | 30.2 | 62.83 | 16.48 | 60.11 |
| Boeing 767-300F | — | *exported 2026-08-26* | | | | | | | | | | |

**Whole fleet: 5.0 MB of `web` GLB** (committed), 28.6 MB of USDZ and 400.8 MB
of `alta` (both regenerated on demand). An export takes 6–10 s per aircraft per
LOD, 26–40 s for the 767 whose bake is the largest.

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

The cause is structural. `FuselagemPaint` — the paint on all nine aircraft — is
not a Principled BSDF: it is three of them mixed by channels of an 8192×2048
nose mask, with the base colour coming from a `Mix` of `LiveryFac` over
`LiveryTex`. glTF can represent exactly one Principled per material. The
exporter does not warn; it writes grey and moves on.

So the pipeline finds those materials by a **structural test** — the Output's
Surface must come straight from a Principled, and that Principled's scalar
inputs may only come from an Image Texture or a Normal Map — and Cycles-bakes
each failing material into a texture glTF *can* carry. On the current fleet the
test catches exactly two materials (`FuselagemPaint` on all nine, `CinzaAsa` on
the four Boeings) and it will catch whatever the 767-300F brings without anyone
editing a list of names.

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
tree. On the fleet this is only the Boeing wing/stabiliser group: those meshes
have no UV layer, so the wing texture already renders as a single texel and the
flat colour is exact rather than approximate. The manifest records which method
each material got.

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
Y and the height in Z. Across the fleet all 45 artefacts return **identical
object, triangle, material and texture counts and an identical bounding box** to
their GLB sibling, wheels on `z = 0`.

This is not a formality. It is what caught the FBX exporter silently dropping
`RegPortaTrem` — the gear-door registration, which is a **`FONT`** object on the
five Airbus and therefore outside the default FBX `object_types`. The GLB and
the OBJ carried it; the FBX came back 800 triangles and one material short, and
nothing in the export log said so. Reading the file was the only way to know.

## What is in git, and what is not

**Committed:** this README, the three scripts, `viewer.html`, `manifest.json`,
and **`web/*.glb`** — about 0.5 MB per aircraft, so a fresh clone can serve the
folder and see the fleet immediately.

**Not committed** (see the repository [`.gitignore`](../.gitignore)): `alta/`
in full and the `.usdz` files. Together they are roughly 400 MB of derived
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

### The airports ship too, in their own folder, under their own licence

For a while this section said the scenery was excluded because ODbL's
share-alike "conflicts" with CC BY 4.0. That was over-cautious and it is now
corrected. ODbL does not forbid redistribution; it requires **attribution** and
**share-alike on the derived database**. [`../NOTICE.md`](../NOTICE.md)
§"The airport mesh is an OSM derivative" says exactly that, and the repository
has always published renders of the fields anyway.

So there are **two tiers with two licences**, kept in separate folders:

| | built by | licence | attribution |
|---|---|---|---|
| [`web/`](web/), [`alta/`](alta/) | `export_frota.py` | CC BY 4.0 | LATAM fleet 3D replicas — Kim Lage |
| [`cenarios/`](cenarios/) | `export_cenarios.py` | **ODbL 1.0, share-alike** | Airport geometry © OpenStreetMap contributors |

An **aircraft** `.glb` still contains nothing but the aeroplane: the exporter
drops linked-library objects and the `Pista` ground plane before writing, which
is why that file carries one licence and no share-alike. Mixing the two inside
one file is what would be careless; shipping them as separate assets, each
carrying its own `licenca` in the manifest and its own `asset.copyright` inside
the `.glb`, is not.

**Copernicus terrain is still excluded**, and that one is a size decision as
much as a licensing one: the SBGR height field alone is 3.7 M faces. Build it
with `scenario*/build_terrain.py` if you need it, and carry the two Copernicus
notices from NOTICE.md with whatever you make.

## `cenarios/` — the airport tier

```bash
python3 export_cenarios.py              # 46 assets from three fields, ~90 s
python3 export_cenarios.py --listar     # the catalogue, without opening Blender
python3 export_cenarios.py --campo sbgr # just Guarulhos
python3 export_cenarios.py --verificar  # read every .glb back and check it
python3 export_cenarios.py --tier leve  # half-size atlases, where they pay
```

46 composable pieces cut out of `scenario/scl_field.blend`,
`scenario_sdsc/sdsc_field.blend` and `scenario_sbgr/sbgr_field.blend`:
**53,797 faces and 1.64 MB of Draco GLB for the whole catalogue**, of which
1.06 MB is baked texture on the 15 assets that carry any (see
[The scenery materials are baked too](#the-scenery-materials-are-baked-too)
below); the heaviest single asset is the Santiago field plate at 324 kB, and
the Guarulhos one is 27,648 faces and 323 kB for 6.1 × 4.8 km of aerodrome.

The builders merge everything into a few large meshes per material —
`SBGR_Jetbridges` is *every* jetbridge at Guarulhos in one mesh spread over
1.7 km — so there is no "jetbridge object" to export. An asset is a **region of
the field**, cut one of two ways, chosen per piece:

- **islands** — whole connected components whose centre falls in the region.
  Right for buildings, vehicles and masts: nobody wants half a truck.
- **plane bisection** — right for pavement, paint and ground, which are carpets;
  cutting a quad in half is the wanted result, and filtering by centre would be
  all-or-nothing on a 3.7 km polygon.

Same conventions as the fleet: +Y up, metres, origin at the X/Z bounding-box
centre, base on y = 0, Draco, embedded textures, and every file read back and
verified — including that the images really are **embedded** and not external
URIs, that an asset the report says was baked came back with images at all, and
that its megapixels match what the bake claims to have written. Two
deliberate exceptions, both recorded in the manifest and both checked:

- **field plates** are datumed on the **runway threshold**, not on their lowest
  point, so an aircraft at y = 0 stands on the runway and the rest of the field
  goes below zero where the ground does;
- three surface sections carry `centrar_em`, which puts the origin on the named
  mesh instead of on the bounding box — a runway section is centred on the
  *runway*, because a PAPI on one side alone pulls the box 21 m off the
  centreline.

### The scenery materials are baked too

The scenery materials are procedural node trees that glTF cannot carry. They
used to be flattened to one representative colour each — all 93 of them — and a
runway plate with no rubber on it is not a runway. They are now **baked**, by
the same technique the livery uses two sections above, with three differences
that the scenery forces.

**1. The bake happens before the piece moves.** These materials read
`Geometry.Position`, which is a **world** coordinate, and the infield reads
`TexCoord.Object`. `montar()` rotates the piece (for an `obb` region) and drops
the datum. Baking after that would paint the pattern in the wrong place: the
rubber would run diagonally across the runway instead of along it. So the bake
runs immediately after the parts are joined and their matrices applied, while
vertex = world = object coordinates are still the frame the pattern was drawn
in. The proof is visible in the runway section: the rubber runs *along* the
centreline, which only happens if the ordering is right.

**2. The haze group is bypassed.** Every scenery material ends in a group that
mixes airlight by camera distance — correct for a render of the aerodrome, wrong
for an asset the studio will light itself. The bake relinks the Principled
straight to the output, otherwise each asset would ship with the fog of one
viewpoint painted into it permanently.

**3. One atlas per asset, UV by `smart_project`.** The scenery has no UVs at
all. A planar XY projection would be tighter on a carpet, but the **markings lie
on top of the pavement** — same XY, same texels, one would overwrite the other.
`smart_project` projects per coplanar island and packs without overlap, so
different materials land in different islands of the same atlas and one image
per asset is enough. Bake margin is 8 texels and the island margin is always
larger, so dilation never crosses from one island into its neighbour.

**Metres per texel** — the budget is set by the smallest feature each material
draws, and the manifest records the *achieved* figure per asset, not the target:

| class | target | achieved | why that number |
|---|---|---|---|
| `superficie_perto` | 0.30 m/texel | 0.24–0.32 | the lateral rubber streak is ~2.2 m wide; 0.30 gives it 7 texels |
| `superficie_campo` | 3.50 m/texel | 2.5–3.3 | the finest infield feature is ~21 m; 3.5 gives it 6 texels |
| `estrutura` | 0.12 m/texel | 0.09–0.46 | cladding ribs are pitched at 1 m; 0.12 gives 8 texels per rib |
| `adereco` | 0.05 m/texel | — | nothing in the catalogue triggers it yet |

Atlases are capped at **2048 for field plates and 1024 for everything else**.
4096 was never used: on a 6.1 km plate it would buy 1.6 m/texel, which is still
far too coarse to resolve a 2 m rubber streak, so it would cost four times the
pixels to change nothing you can see.

**What is baked and what is not.** The test is structural, not by name: a
material is baked when its Principled has a *linked* Base Color or Roughness.
**25 of the 93 materials** qualify, and the other **68 are constant colours** —
all the GSE, glass, steel and roofing. Flattening those is exact, not a loss:
there is nothing in them for a texture to carry. Both tables are in
`cenarios/manifest.json`, under `materiais_assados` and `materiais_achatados`.

**Roughness is a measured scalar, not a map.** Only the five runway materials
vary it, and the whole range is 0.59–0.84 — asphalt slightly smoothed where
rubber has been laid down, within ~15 m of the centreline. A map cost a second
512² image (+25% on the asset), came out of the exporter packed into the green
channel of a `metallicRoughness` texture whose colour-space conversion got the
value wrong once already, and changes nothing visible in a viewer without a
strong environment — the rubber is already in the *base colour*, which is the
signal the eye uses. So each runway material carries a mean measured from a
small bake instead: 0.812 for GRU's 10R/28L, 0.808 for São Carlos. Metallic is
constant everywhere and stays a scalar.

**Textures are JPEG q82, embedded.** The atlases are smooth noise with no alpha,
which is the case where PNG is expensive and JPEG is cheap, and the packing
leaves holes that are filled with the mean of what *was* baked — flat area that
JPEG pays almost nothing for. Filling those holes matters: left black they make
the asset darken as the mipmap blends hole with island.

**The bill.** The catalogue was 0.47 MB flat; it is now **1.64 MB**, of which
**1.06 MB (64%) is texture** across the 15 assets that have any. The heaviest
asset is the Santiago field plate at 324 kB. Texture memory is 20.1 MP for the
whole catalogue, and 4.19 MP for a single field plate.

A **low-texture tier** is available for the cases where that is too much:

```bash
python3 export_cenarios.py --tier leve    # <slug>.leve.glb, for the textured assets
```

`leve` halves every atlas side — a quarter of the pixels — and writes
`<slug>.leve.glb` beside the full one, recorded in the manifest under
`tier_leve`. Substituting them brings the catalogue to **0.94 MB and 5.0 MP**.

**14 of the 15 textured assets get a variant, not 15.** Assets with no texture
get none, because a second identical file is not a level of detail — and the
same rule is enforced by measurement, not by assumption: `scl_base_latam`'s
atlas was already small enough that halving the budget rounded back to the same
256², so its variant came out 12 bytes lighter and is deleted rather than
shipped. The exporter prints which slugs it dropped and why.

**What is still thin**, measured rather than guessed:

- On a **field plate**, runway markings lose 27.5% of their luminance, against
  the 14.9% that is genuine wear in the material (measured on the close-up
  section, where texels are 13× finer). The cause is geometric: a 0.15 m marking
  is well under one texel at 3.3 m/texel, so its UV island is a sliver and
  filtering mixes it with the fill. Raising the bake margin to 8 recovered 3.5
  of those points; the rest is inherent to the class. On a plate meant to be
  seen 6 km wide, a marking is one screen pixel, so this was not worth more.
- **Packing occupancy runs 0.09 to 0.92.** The bad end is long, thin, diagonal
  pieces — `sdsc_mro_oficinas` (a 470 m workshop spine) and `sbgr_taxi_secao`.
  They waste atlas *pixels*; they cost few *bytes*, because the fill is flat.
  A `uv.pack_islands(rotate=True)` pass was tried and made it worse, not better
  — it repacks the non-procedural faces too, whose UVs are degenerate.
- `sdsc_mro_oficinas` lands at 0.46 m/texel against a 0.12 target: it is capped
  at 1024 *and* packed badly, so its cladding ribs are not resolved.
- The apron reads as **aged patchwork, not as discrete slabs with joints** —
  because that is what `aged_pavement_material` draws. Slab joints would have to
  be added in `scenario*/`, which this round did not touch.
