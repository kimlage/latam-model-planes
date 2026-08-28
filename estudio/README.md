# `estudio/` — the scene studio

A browser page that loads the exported fleet, lets you **compose a scene** from
it, and gets the result back out four ways: an **animated GIF**, a **navigable
3D embed** you can drop into another web page, a **scene JSON** that
round-trips, and a **PNG still**.

It is a sibling of [`export/viewer.html`](../export/viewer.html), not a
replacement: the viewer answers *did the GLB export correctly*, the studio
answers *what does a scene made of them look like, and how do I ship it*.

```bash
# from the repository ROOT, not from estudio/
python3 -m http.server 8000
open http://localhost:8000/estudio/
```

**It must be served over HTTP, and the server must be rooted at the repository**,
because the page reads `../export/manifest.json` and `../export/web/*.glb`. A
`file://` page is not allowed to fetch them; that is a browser rule, the same
one documented in [`export/README.md`](../export/README.md). There is no build
step: three.js, the Draco decoder and the GIF encoder are **vendored** under
`vendor/`, so the page also needs no internet.

There is a `.claude/launch.json` at the repository root with the same server
under the name `estudio`, for tools that read it.

---

## Licence — read this before you export anything

Two facts, and the second one is why half of this folder exists.

**The aircraft are CC BY 4.0.** They are original geometry, built in this
repository from the manufacturers' published dimensional documents. Everything
this page exports carries that licence, and the attribution it requires is:

> LATAM fleet 3D replicas — Kim Lage — CC BY 4.0
> https://creativecommons.org/licenses/by/4.0/

The exported embed writes that line into the page itself. The exported scene
JSON carries it in a `licenca` field.

**The airport scenery is not exportable, ever.** `scenario/` (SCL),
`scenario_sdsc/` and `scenario_sbgr/` are generated from **OpenStreetMap**;
a mesh built from an ODbL database is a derived database, so redistributing it
carries ODbL's **share-alike**. Share-alike and CC BY 4.0 conflict. So the
studio has no way to load that geometry at all — it is not a checkbox someone
can tick by mistake, there is simply no code path from `scenario*/` into this
page.

What you get instead is authored here, in
[`js/props.js`](js/props.js): ground materials painted on a `<canvas>` (asphalt,
concrete slabs, grass, a generic runway pattern, a plain studio sweep), a sky
built analytically from the sun's own elevation and azimuth, and box-and-cylinder
massing — hangar, terminal, apron slab, light mast, boarding bridge, stairs,
cone, block, backdrop card. None of it is a survey of any real airport. The
runway markings follow the generic published pattern (30 m stripe / 20 m gap
centreline, edge stripes on a 45 m strip); they are not a specific runway.

**Trademarks.** LATAM, Airbus and Boeing are their owners'. This is an
independent, non-commercial project. See [`../NOTICE.md`](../NOTICE.md).

The same text is in the studio, behind the **Licence** button in the top bar.

**Vendored third-party code** — `vendor/three` (three.js r169, MIT),
`vendor/three/draco` (Draco decoder, Apache-2.0, Google), `vendor/gifenc`
(gifenc 1.0.3, MIT, Matt DesLauriers). Licence files ship alongside each.

---

## The facts it relies on

Everything below is read out of `export/manifest.json` or measured from the
loaded geometry — nothing about the fleet is hard-coded in this folder.

| Fact | Where it comes from | Why the studio needs it |
|---|---|---|
| **+Y up, metres** | glTF convention; `export_frota.py` verifies it | the ground plane is `y = 0` |
| **wheels on `y = 0`** | the exporter moves the height datum, and checks it | "snap to ground" is `pos.y = 0`, nothing smarter |
| **nose at `x ≈ 0`, tail at `x ≈ +L`** | repository frame; the bbox proves it | the aircraft's forward direction is **−X**; the "front" camera preset looks along +X, and the GIF "travel along the nose" moves along local −X |
| **span along Z, straddling 0** | exporter's symmetry check | line-ups are Z offsets |
| **Draco-compressed** | `KHR_draco_mesh_compression` in every `web` GLB | `DRACOLoader` is wired, decoder vendored |
| **clearcoat paint** | `KHR_materials_clearcoat` on 12–28 materials | an environment map is not optional — with only direct light the livery reads as flat vinyl. Default environment is the generated sky; `RoomEnvironment` is offered as "studio" |
| name, registration, triangles, materials, bytes, bounding box | `manifest.json` `verificacao` block | the sidebar cards and the selection read-out |

**Instances are wrapped in a pivot group** whose origin sits at the model's X/Z
bounding-box centre with `y = 0` at the wheels — measured from the loaded
geometry, not from the manifest. Without it a turntable would spin the aircraft
about its nose tip and the gizmo would sit in front of the radome.

A twelfth aircraft needs no edit here: export it, and it appears.

---

## What is in the page

### Two libraries, deliberately separate

**Assets** — the 11 aircraft (thumbnail, name, registration, measured length,
triangle count), the environment props, and the light rigs. Click to add at the
orbit target, or drag onto the viewport to drop at that point on the ground.
New objects are nudged along Z until they are clear of what is already there.

Thumbnails are **rendered from the real GLB** in a throwaway 168×114 context,
one at a time, and cached in `localStorage` — so the second visit shows them
without fetching 9 MB again. They are a smoke test as much as a picture: a
thumbnail that never appears is a GLB that did not load.

**Scenes** — five starter compositions (single hero, line-up of the family,
cargo ramp, turntable showcase, night ramp) plus your own, saved in
`localStorage` with load / save / duplicate / rename / delete. Starters carry a
camera *direction*, not a position: they are framed on open from the measured
bounding box of the **aircraft** in them, so a 210 m backdrop card cannot decide
the shot.

### Controls

| Group | What is there |
|---|---|
| **Camera** | orbit / pan / dolly (OrbitControls, damped, no going under the tarmac); presets front / side / top / 3-quarter / hero; frame selected (F) and frame all (A); FOV slider; orthographic toggle that keeps the same apparent height; store pose A / pose B |
| **Object** | click-select in the viewport and in the outliner; shift-click to add to the selection; move / rotate / scale gizmos (W / E / R) with X / Y / Z axis constraints; local/world space (Q); numeric position, rotation and scale fields; translation and rotation snap increments; snap to ground (G); duplicate (Ctrl+D); delete (Del); per-object lock and hide; undo / redo (Ctrl+Z, Ctrl+Shift+Z) |
| **Scene** | sun elevation / azimuth / intensity / colour; environment (generated sky, RoomEnvironment, none) and its intensity; background (sky, solid colour, transparent); exponential fog; ground on/off with six materials and a size; grid |
| **Render** | tone mapping (ACES Filmic, AgX, Khronos Neutral, Reinhard, Linear); exposure; shadows on/off; shadow map 512–4096; antialias; pixel-ratio cap |

The status line under the viewport reports fps, object count, triangles, draw
calls and how many bytes of GLB have been fetched.

**Multi-select** attaches the gizmo to a pivot at the selection centroid and
re-parents the selected objects under it **for the duration of the drag only**,
with `Object3D.attach()` so world transforms are preserved. Attaching after the
pivot has moved pins the objects where they already are and the drag silently
does nothing — that bug was in this file for an hour, which is why the
bracketing is spelled out in [`js/editor.js`](js/editor.js).

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

**Sizes, measured.** Two 640×360 12-frame turntables, no supersampling, bytes
per pixel per frame:

| colours | 32 | 64 | 128 | 256 |
|---|---:|---:|---:|---:|
| *Single hero* (smooth sky, one aircraft) | 0.051 | 0.073 | 0.092 | 0.120 |
| *Line-up of the family* (textured concrete, five) | 0.103 | 0.145 | 0.175 | 0.200 |

With the default 2× supersampling the hero scene drops to **0.068** at 128
colours — cleaner edges compress better. The live estimate in the dialog uses
constants between those cases and is good to roughly **±50 %**; it exists to
make the trade visible, not to be precise. The line the dialog prints *after*
the encode is the real file size and the real bytes-per-pixel.

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

The dialog states, before you download, exactly what the file needs beside it,
with the real byte sizes. Three path modes:

| mode | `estudio/` at | GLBs at | use when |
|---|---|---|---|
| **relative** (default) | `./` | `../export/web/` | you save the HTML **inside `estudio/`** — works the moment the repository folder is copied anywhere |
| **sibling** | `estudio/` | `./` | the HTML sits next to the `.glb` files |
| **absolute URLs** | typed | typed | hosted somewhere else |

Options: auto-rotate and its speed, allow zoom, allow pan. The dialog also
copies a ready `<iframe>` snippet.

[`exemplo_embed.html`](exemplo_embed.html) in this folder is a real one,
generated by the page and committed as the worked example — open
`http://localhost:8000/estudio/exemplo_embed.html`.

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
    frota.js            manifest → catalogue, GLB cache, instancing, thumbnails
    props.js            ALL original environment: grounds, sky, props, rigs
    mundo.js            the three.js world; the document's only projection
    editor.js           selection, gizmos, snapping, lock/hide
    cenas.js            the five starter scenes
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
- **`aa: MSAA + 2× supersample`** only affects exports; the interactive viewport
  uses the context's own MSAA and the pixel-ratio cap.
- **Fog colour** follows the horizon, or the background colour when the
  background is solid; it is not independently settable.
- **The starter scenes' prop placement is eyeballed**, not surveyed — they are
  compositions to start from, not a claim about where anything stands.
