# `estudio/` — the scene studio

A browser page that loads the exported fleet **and the three airports**, lets
you **compose a scene** from them, and gets the result back out four ways: an
**animated GIF**, a **navigable 3D embed** you can drop into another web page, a
**scene JSON** that round-trips, and a **PNG still**.

57 GLB assets: 11 aircraft (CC BY 4.0) and 46 pieces of Guarulhos, São Carlos
and Santiago (ODbL 1.0, share-alike), plus 9 authored massing props.

It is a sibling of [`export/viewer.html`](../export/viewer.html), not a
replacement: the viewer answers *did the GLB export correctly*, the studio
answers *what does a scene made of them look like, and how do I ship it*.

```bash
# from the repository ROOT, not from estudio/
python3 -m http.server 8000
open http://localhost:8000/estudio/
```

**It must be served over HTTP, and the server must be rooted at the repository**,
because the page reads `../export/manifest.json`, `../export/web/*.glb` and
`../export/cenarios/`. A
`file://` page is not allowed to fetch them; that is a browser rule, the same
one documented in [`export/README.md`](../export/README.md). There is no build
step: three.js, the Draco decoder and the GIF encoder are **vendored** under
`vendor/`, so the page also needs no internet.

There is a `.claude/launch.json` at the repository root with the same server
under the name `estudio`, for tools that read it.

---

## Licence — read this before you export anything

**Two tiers, two licences, and the studio computes which ones YOUR scene
carries.** The Licence button in the top bar does not make a blanket claim about
the page; it lists the licences of the assets actually placed in the open scene,
and the export dialogs, the generated embed and the scene JSON carry the same
list.

| | what it is | licence | attribution |
|---|---|---|---|
| the 11 **aircraft** | original geometry built here from the manufacturers' published dimensional documents | CC BY 4.0 | *LATAM fleet 3D replicas — Kim Lage — CC BY 4.0* |
| the 46 **airport pieces** | cut out of `scenario/` (SCL), `scenario_sdsc/`, `scenario_sbgr/`, which are generated from **OpenStreetMap** | **ODbL 1.0, share-alike** | *Airport geometry © OpenStreetMap contributors, ODbL 1.0* |
| the **grounds, sky and massing blocks** | authored in [`js/props.js`](js/props.js) from primitives and canvas painting | CC BY 4.0 | as the aircraft |

A mesh built from an ODbL database is a derived database, so the airport pieces
carry share-alike — and ODbL *permits* that redistribution as long as the
attribution travels and share-alike is honoured. See
[`../NOTICE.md`](../NOTICE.md) §"The airport mesh is an OSM derivative". An
earlier round of this studio refused to load any of it on the belief that ODbL
and CC BY "conflict"; they do not, and the fix was not to hide the geometry but
to **license per asset**. Every scenery row in
`../export/cenarios/manifest.json` carries a `licenca` field, every scenery
`.glb` carries the attribution in its own `asset.copyright`, and cards for
share-alike assets show an **ODbL** badge in the sidebar — before you place one,
not after you export.

**Copernicus terrain is not exported at all.** The height fields under
`scenario*/` are 3.7 M faces at SBGR alone; no asset here references them. The
manifest still carries the Copernicus row so the panel can show it the day one
does.

**What the airport pieces lose on the way out.** Their materials are procedural
node trees — noise, range maps, a haze group — that glTF cannot carry. The
exporter flattens each to a representative colour read from the material's own
`diffuse_color`, which the scenery builders set deliberately; all 93 resolved
that way, none needed a fallback. The pavement is the right grey. It is not the
pavement a Cycles render of the field gives you, and
`materiais_achatados` in the manifest records the substitution material by
material.

**Trademarks.** LATAM, Airbus and Boeing are their owners'. This is an
independent, non-commercial project. See [`../NOTICE.md`](../NOTICE.md).

The same text is in the studio, behind the **Licence** button in the top bar.

**Vendored third-party code** — `vendor/three` (three.js r169, MIT),
`vendor/three/draco` (Draco decoder, Apache-2.0, Google), `vendor/gifenc`
(gifenc 1.0.3, MIT, Matt DesLauriers). Licence files ship alongside each.

---

## The facts it relies on

Everything below is read out of `export/manifest.json`,
`export/cenarios/manifest.json` or measured from the loaded geometry — nothing
about the fleet or the airports is hard-coded in this folder, including the
sidebar's section names.

| Fact | Where it comes from | Why the studio needs it |
|---|---|---|
| **+Y up, metres** | glTF convention; `export_frota.py` verifies it | the ground plane is `y = 0` |
| **wheels on `y = 0`** | the exporter moves the height datum, and checks it | the ground datum; "snap to ground" starts from it |
| **nose at `x ≈ 0`, tail at `x ≈ +L`** | repository frame; the bbox proves it | the aircraft's forward direction is **−X**; the "front" camera preset looks along +X, and the GIF "travel along the nose" moves along local −X |
| **span along Z, straddling 0** | exporter's symmetry check | line-ups are Z offsets |
| **Draco-compressed** | `KHR_draco_mesh_compression` in every `web` GLB | `DRACOLoader` is wired, decoder vendored |
| **clearcoat paint** | `KHR_materials_clearcoat` on 12–28 materials | an environment map is not optional — with only direct light the livery reads as flat vinyl. Default environment is the generated sky; `RoomEnvironment` is offered as "studio" |
| name, registration, triangles, materials, bytes, bounding box | `manifest.json` `verificacao` block | the sidebar cards and the selection read-out |
| **`categoria` and `licenca` per asset** | both manifests | the five sidebar sections, the ODbL badge, the Licence panel, the embed's credit line |
| **airport pieces already centred** | `export_cenarios.py` measures and verifies it | the studio does **not** re-centre them — see below |
| **field plates datumed on the runway threshold** | `datum: "campo"` in the scenery manifest | part of the plate is below `y = 0` on purpose, and "snap to ground" must not clamp there |

**Aircraft instances are wrapped in a pivot group** whose origin sits at the
model's X/Z bounding-box centre with `y = 0` at the wheels — measured from the
loaded geometry, not from the manifest. Without it a turntable would spin the
aircraft about its nose tip and the gizmo would sit in front of the radome.

**Airport pieces are NOT re-centred here.** They arrive already centred, and in
three cases centred deliberately somewhere other than the box middle: a runway
section is centred on the *runway*, because a PAPI on one side alone pulls the
bounding box 21 m off the centreline. Re-measuring and re-centring them in the
browser silently undid that decision, and the 777 of the runway starter stood
with its gear on the shoulder until somebody looked at it from above.

A twelfth aircraft — or a forty-seventh hangar — needs no edit here: export it,
and it appears, under its own category, with its own licence.

---

## What is in the page

### Two libraries, deliberately separate

**Assets** — 66 cards in five sections, and the sections come from the
manifests rather than from this folder:

| section | count | what is in it |
|---|---:|---|
| aircraft | 11 | the fleet, with registration, measured length and triangle count |
| airport structures | 22 | hangars, terminals, towers, a jetbridge, a cargo shed, the MRO frontage |
| ground & surfaces | 7 | a runway threshold section, a taxiway section, apron slabs, three whole-field plates |
| vehicles & GSE | 14 | tug and towbar, GPU, air start, belt loader, catering, cargo loader, stairs, bus, bowsers, cherry picker, van, dolly train |
| props | 12 | masts, fences, maintenance docks, engine stands, containers, cones, massing blocks, the backdrop card |

The authored props from [`js/props.js`](js/props.js) carry the same category
vocabulary as the surveyed pieces, so both file into the same sections and one
filter box searches across everything — name, slug, field, category, licence and
the asset's own note. Cards for share-alike assets carry an **ODbL** badge, and
anything wider than 300 m is flagged **▮ large**: it is a backdrop, not a
building block. Click to add at the orbit target, or drag onto the viewport to
drop at that point on the ground. New objects are nudged clear of what is
already there — except pieces over 300 m across, which neither move nor push,
because you drop a jet *onto* a runway, not beside it.

Thumbnails are **rendered from the real GLB** in a throwaway 168×114 context,
one at a time, and cached in `localStorage` — so the second visit shows them
without fetching 10 MB again. They are a smoke test as much as a picture: a
thumbnail that never appears is a GLB that did not load. All 57 render.

**Scenes** — nine starter compositions plus your own, saved in `localStorage`
with load / save / duplicate / rename / delete.

Five are fleet-only: single hero, line-up of the family, cargo ramp, turntable
showcase, night ramp. **Four are built on the real bases** and are what the
airport tier is for:

| starter | what is in it |
|---|---|
| **Stand at GRU** | A320neo at the gate: apron slab, terminal block, a jetbridge docked at the L1 door, catering, cargo loader, tug and towbar, bowser, apron bus, two floodlight masts |
| **Hangar 9, São Carlos** | 787-9 nose-in on the door line, the MRO hangar bay behind, maintenance dock, engine stands, containers, GSE, perimeter fence |
| **Runway 10R at GRU** | 777-300ER lined up on the threshold, on the real 10R marking geometry, with two lattice masts |
| **The whole field — GRU** | the 27,648-face field plate, 6.1 × 4.8 km, with a 777 rolling 10L, an A320neo holding short, and the control tower |

Starters carry a camera *direction*, not a position: they are framed on open
from the measured bounding box of the **aircraft** in them, so a 210 m backdrop
card — or a 6 km field plate — cannot decide the shot. A scene whose subject
*is* the field says `quadro: 'tudo'` and gets framed on everything.

In *The whole field*, the three placed objects are **not eyeballed**: the
aircraft and the tower are positioned from each asset's recorded origin in the
field, so they stand where they stand at Guarulhos. That is the arithmetic check
on the whole export, done where you can see it.

Starters may also ask to be **seated** (`assentar`), which drops every aircraft
onto whatever is beneath it once, on open. Field plates and runway sections are
real surfaces with real relief — GRU's 10L is 0.39 m below the threshold datum
where the starter puts the 777 — and hard-coding those numbers would make them
go stale the day a plate is re-cut.

### Controls

| Group | What is there |
|---|---|
| **Camera** | orbit / pan / dolly (OrbitControls, damped, no going under the tarmac); presets front / side / top / 3-quarter / hero; frame selected (F) and frame all (A); FOV slider; orthographic toggle that keeps the same apparent height; store pose A / pose B |
| **Object** | click-select in the viewport and in the outliner; shift-click to add to the selection; move / rotate / scale gizmos (W / E / R) with X / Y / Z axis constraints; local/world space (Q); numeric position, rotation and scale fields; translation and rotation snap increments; snap to ground (G); duplicate (Ctrl+D); delete (Del); per-object lock and hide; undo / redo (Ctrl+Z, Ctrl+Shift+Z). The selection read-out adds the asset's field, its licence and its note |
| **Scene** | sun elevation / azimuth / intensity / colour; environment (generated sky, RoomEnvironment, none) and its intensity; background (sky, solid colour, transparent); exponential fog; ground on/off with six materials and a size; grid |
| **Render** | tone mapping (ACES Filmic, AgX, Khronos Neutral, Reinhard, Linear); exposure; shadows on/off; shadow map 512–4096; export sampling 1–3×; pixel-ratio cap |

The status line under the viewport reports fps, object count, triangles, draw
calls and how many bytes of GLB have been fetched.

**Multi-select** attaches the gizmo to a pivot at the selection centroid and
re-parents the selected objects under it **for the duration of the drag only**,
with `Object3D.attach()` so world transforms are preserved. Attaching after the
pivot has moved pins the objects where they already are and the drag silently
does nothing — that bug was in this file for an hour, which is why the
bracketing is spelled out in [`js/editor.js`](js/editor.js).

### Airport scale needed four things fixed, and each was found by looking

Composing at 6 km instead of 60 m broke assumptions the studio had been getting
away with. All four were visible on screen before they were understood:

- **Depth range.** `near`/`far` used to be pinned when a box was framed. Framing
  a field plate gave `near = 55 m`, which clipped every aircraft you then flew
  up to. They now track the **orbit distance** (`near = 1 % of it`, clamped),
  which holds the ratio near 3000:1 at every zoom — a first attempt at this
  reached 20000:1 and z-fought a 6 cm apron slab against the ground plane.
  Deriving from distance also survives the orthographic toggle, which a
  logarithmic depth buffer would not.
- **Surfaces do not cast shadows.** A zero-thickness apron 6 cm above the
  ground, casting into a shadow map whose texel is 26 cm at a 27° sun, shadows
  *itself* in stripes across the whole ramp. Assets in the *ground & surfaces*
  category receive shadows and are not occluders. No bias tweak fixes that; the
  surface simply should not be one.
- **The sun aims at the small objects.** Both the sun's position and the shadow
  frustum come from the bounding box of everything under 300 m wide. Using the
  whole scene put a 9.7 km shadow map at 2048 px — 4.8 m per texel, which is not
  a shadow.
- **Snap to ground means "onto what is below".** It raycasts down onto the other
  objects and lands on the highest surface under the footprint, with `y = 0` as
  the floor *only when there is a floor*: a field plate datumed on the threshold
  runs below zero over most of the aerodrome, and clamping there left the 777
  hovering. The five samples are the centre and a cross at ±15 % of the
  footprint — sampling the corners would let a wingtip over a container lift the
  whole aeroplane onto it.

**Undo is a snapshot stack, not a command stack.** One serialiser, one restorer,
no third code path that can disagree with them. The snapshot is taken *after*
each mutation and the cursor points at the current state; taking it before
gives you an undo that works and a redo that cannot, because the post-change
state was never written down. Restoring is cheap: GLB payloads are cached and
instances are `Object3D.clone()`s sharing geometry and materials.

---

## The four exports

### 1. Animated GIF

The **GIF law** of this project is arithmetic, not taste: a GIF frame delay is
an integer number of **centiseconds**. 25 fps is 4 cs exactly. 24 fps is
4.1666… cs, so every encoder alternates 4 and 5 and the motion visibly stutters
on a 12-frame cycle. The frame-rate menu therefore offers only rates that divide
100 evenly — 25, 20, 12.5, 10, 5 — and prints the delay it will write.

Encoder: **gifenc**, vendored. It does not dither at all; each pixel goes to the
nearest palette entry. That satisfies "no dithering by default" and it also
means the **colour count is the only quality/size knob**, which is why the
dialog puts it next to the resolution.

The palette is **global, built in a first pass** from four sampled frames (t =
0, ¼, ½, ¾) rather than per frame: a per-frame table looks marginally better on
a single frame and flickers across a loop. The second pass renders and encodes
frame by frame and keeps no buffers, so a 90-frame 960 px export does not need
200 MB of RAM.

Four motions:

- **turntable — camera orbits the scene**, at the current radius and height
- **turntable — spin the selected object** about its own centre, camera fixed
- **camera path — pose A → pose B**, smoothstepped, optionally ping-ponged so
  the loop does not cut
- **fixed camera — the selected object moves**, a distance along its own nose
  (local −X) or a world axis, with an optional quadratic climb

Every motion is bracketed by save/restore: an export leaves the scene, the
camera and the object exactly where they were. The interactive render loop is
paused for the duration, because `OrbitControls.update()` would otherwise
overwrite the camera the motion function just set — the classic "my GIF is 60
copies of one frame" bug.

**Sizes, measured.** Two 640×360 12-frame turntables at 2× supersampling (the
default), bytes per pixel per frame:

| colours | 32 | 64 | 128 | 256 |
|---|---:|---:|---:|---:|
| *Single hero* (smooth sky, one aircraft) | 0.035 | 0.050 | 0.063 | 0.082 |
| *Line-up of the family* (textured concrete, five) | 0.111 | 0.169 | 0.196 | 0.212 |

A factor of three between two perfectly ordinary scenes — LZW on a smooth sky
gradient and LZW on tiled concrete are not the same problem. Supersampling
*helps* the smooth scene (0.092 → 0.063 at 128 colours, cleaner edges compress
better) and slightly hurts the busy one (0.175 → 0.196). The live estimate uses
the geometric mean of those two columns, so it is honest to **about a factor of
2 either way**; it exists to make the trade visible, not to be precise. The line
the dialog prints *after* the encode is the real file size and the real
bytes-per-pixel.

A representative export, verified with PIL rather than by eye:

```
640×360, 60 frames, 2× supersample, 128 colours   →  917 kB in 1.1 s
PIL: frames 60, unique durations {40 ms}, loop 0
```

### 2. Navigable 3D embed

An `<iframe>`-able HTML file. It does **not** re-implement the renderer: it
imports [`js/embed.js`](js/embed.js), which builds the *same* `Mundo` the studio
builds from the *same* scene document and simply never constructs the editor. If
a scene looks right in the studio it looks right in the embed, or both are
broken in the same place.

The dialog states, before you download, exactly what the file needs beside it:
every GLB with its real byte size and triangle count, an ODbL tag on the ones
that carry share-alike, the total payload, and the licence lines that will be
written into the page. If the payload passes 12 MB or 900 k triangles it says
so, in as many words, rather than shipping a page that hangs.

Three path modes:

| mode | `estudio/` at | GLBs at | use when |
|---|---|---|---|
| **relative** (default) | `./` | `../export/web/` and `../export/cenarios/` | you save the HTML **inside `estudio/`** — works the moment the repository folder is copied anywhere |
| **sibling** | `estudio/` | `./` | the HTML sits next to the `.glb` files |
| **absolute URLs** | typed | typed | hosted somewhere else |

Options: auto-rotate and its speed, allow zoom, allow pan. The dialog also
copies a ready `<iframe>` snippet.

The generated page carries **both licence lines** — in the HTML comment at the
top, in the visible credit bar, and in the `licencas` block of the scene JSON
baked into the file.

[`exemplo_embed.html`](exemplo_embed.html) in this folder is a real one,
generated by the page and committed as the worked example — the GRU stand
scene. Open `http://localhost:8000/estudio/exemplo_embed.html`. Measured on it:
**10 GLBs, 1.26 MB, the last one in at 495 ms, 62,410 triangles, 150 draw
calls, 33 fps** at 1788 × 2088 physical pixels.

**The embed rendered at 2× on every HiDPI screen until 2026-08-28**, and it took
generating one and *looking at it* to notice. `mundo.js` calls
`renderer.setSize(w, h, false)` — `updateStyle` off — so the canvas carries its
physical size in its `width`/`height` attributes and something else has to give
it a CSS size. `css/estudio.css` does; the generated embed did not, so the
canvas laid out at twice the window and the page showed the top-left quarter of
the frame. On a 1× display it looked correct, which is exactly why it survived.

**The limit, stated plainly:** this is *linked*, not *inlined*. One HTML file
plus `estudio/vendor/` (2.1 MB, once, shared by every embed), `estudio/js/`
(~60 kB) and one GLB per aircraft type (0.4–1.3 MB). Nothing comes from a CDN.
A true single-file embed would have to inline three.js, the Draco decoder *and*
the GLBs as base64 — roughly 6 MB of HTML for a three-aircraft scene — and it is
**not built**. If you need one, the honest route is to serve the folder.

### 3. Scene JSON

Schema `latam-estudio/1`. Objects and their transforms, the sun and sky, the
render settings, the live camera, the two stored poses, and an `assets` table
mapping each slug to its GLB path. Download, copy to clipboard, or import a file
back. A save/load round trip was verified to return the same object count,
ground type, environment preset and camera position to 0.1 m.

### 4. PNG still

The viewport camera as it stands, at a chosen width and aspect, with 1–3×
supersampling. A transparent background produces a PNG **with alpha** — combined
with the *shadow catcher* ground you get an aircraft and its shadow on nothing,
which is what a composite needs. Verified: 84,257 fully transparent pixels,
1,870 fully opaque, 3,873 partial (the antialiased edges and the soft shadow).

---

## Files

```
estudio/
  index.html            the page: panels, the two columns, the modal
  css/estudio.css       dark, dense, three columns; narrows below 1180 px
  js/
    main.js             boot and wiring — the switchboard, no logic of its own
    estado.js           the scene document, the history stack, the scene library
    frota.js            BOTH manifests → one catalogue, GLB cache, instancing,
                        thumbnails, the licence table
    props.js            the AUTHORED environment: grounds, sky, massing, rigs
    mundo.js            the three.js world; the document's only projection
    editor.js           selection, gizmos, snapping, lock/hide
    cenas.js            the nine starter scenes, four of them on real bases
    exportar.js         GIF, PNG, embed HTML, scene JSON
    dialogos.js         the export and licence modals
    embed.js            the runtime an exported embed loads
  vendor/               three.js r169 + Draco + gifenc, with their licences
  exemplo_embed.html    a real generated embed, as the worked example
```

`window.__estudio` exposes `{ mundo, editor, estado, historico,
carregarDocumento, adicionar, atalho }`. That is deliberate: it is how the page
was driven and verified, and it is the only way to script it from outside.

---

## Known limits

- **Needs a server, rooted at the repository.** `file://` cannot fetch the GLBs;
  serving `estudio/` alone breaks `../export/`.
- **The embed is linked, not inlined** — see above.
- **Undo covers the document, not the camera.** Orbiting is not undoable, which
  matches how 3D editors behave, but it does mean Ctrl+Z will not put a camera
  back. Store a pose if you want one kept.
- **No object-level material editing.** Instances share geometry *and*
  materials with every other instance of the same aircraft, which is what makes
  eleven of them cheap; per-instance paint would mean cloning materials.
- **Scaling a multi-selection non-uniformly while it is rotated** goes through
  a matrix decompose that cannot represent shear, so the result may not be what
  a DCC package would give. Single objects are exact.
- **Scenes live in this browser's `localStorage`.** Clearing site data clears
  them. Export the JSON to move a scene between machines.
- **GIF is 8-bit and never dithers.** Skies band. That is the format, and the
  colour-count control is how you trade against it.
- **The GIF encode is synchronous on the main thread**, yielding every second
  frame. A 400-frame 960 px export will make the page unresponsive for tens of
  seconds. There is no worker.
- **"export sampling" only affects exports.** The interactive viewport's
  antialiasing is the WebGL context's own MSAA plus the pixel-ratio cap, and
  changing that would mean rebuilding the renderer and every compiled program.
- **Fog colour** follows the horizon, or the background colour when the
  background is solid; it is not independently settable.
- **The starter scenes' prop placement is eyeballed**, not surveyed — they are
  compositions to start from, not a claim about where anything stands. The one
  exception is *The whole field — GRU*, where the aircraft and the tower are
  placed from the assets' recorded field origins.
- **Airport materials are flat colours.** glTF cannot carry the procedural node
  trees the scenery builders use, and this exporter does not bake. Pavement,
  paint and cladding are each one representative colour. See §Licence.
- **The frame rate is the aircraft's, not the airport's.** A 27,648-face field
  plate runs at 118 fps; five aircraft in the *line-up* starter run at 22, on
  320 k triangles and 695 draw calls. The jets are 60 k triangles and a few
  dozen materials each; the airport pieces are 10–1000 faces and two or three.
  If a scene is slow, it is the fleet in it.
- **Scenery pieces are single-sided and hollow.** Cropping a batched mesh by
  plane bisection leaves an open cut, so a terminal block seen from the wrong
  side shows through. Compose with the cut faces away from the camera.
- **No collision, no snapping to another object's face.** "Snap to ground" is
  vertical only; a jetbridge is docked by eye.
