# SCL / SCEL scenery — a shared asset

The Santiago base is built once and **linked** into every aircraft file. Fixing the
airport here fixes it for the A320neo, the 787-9 and everything that comes after.

```
scenario/
  scl_field.blend      the aerodrome     collections SCL_Field, SCL_Light, SCL_Anchors
  scl_terrain.blend    the Andes         collection  SCL_Terrain          (not committed)
  build_scenery.py     rebuilds both from the data in this folder
  place_aircraft.py    puts an aircraft rig on RWY 17R and links the scenery
  render_checks.py     the visual checks (plan / ground / andes)
  blender_assets.cats.txt   Asset Browser catalogues
```

`scl_terrain.blend` is 130 MB of mesh and is **git-ignored**. It regenerates in about
six seconds from the heightfields, which *are* committed:

```bash
blender -b --factory-startup -P scenario/build_scenery.py -- --terrain
blender -b --factory-startup -P scenario/build_scenery.py -- --field     # ~2 s
```

---

## 1. The reference frame

Everything in `scenario/` — OSM geometry, heightfields, both .blend files — lives in
one frame. Blender units are metres, 1:1, no scaling.

| | |
|---|---|
| Type | local **ENU** tangent plane on WGS84 |
| Origin | lat **−33.3760915**, lon **−70.7867106** — the **RWY 17L** threshold (OSM node 2451905265; the AIP threshold falls 1.2 m from it) |
| Axes | x = East, y = North, z = Up, metres |
| Vertical datum | **z = 0 at 474.0 m AMSL**, the published SCEL aerodrome elevation |
| Runway pavement | z = **+0.09 m** (see the z-stack in §5) |

Earth curvature is baked into the terrain z, on purpose: a point 90 km out sits about
630 m below the tangent plane. Drop the heightfield on a flat plane and the far
cordillera stands hundreds of metres too tall.

### Anchors — the only two things a new aircraft needs

`SCL_Anchors` carries Empties whose **+Y axis points down the take-off track**, so an
aircraft can simply be parented to one:

| Empty | position (x, y, z) | track |
|---|---|---|
| **`SCL_17R_Threshold`** | (−1582.57, 459.21, 0) | 177.424° true — **departures** |
| `SCL_17L_Threshold` | (0.21, 1.21, 0) | 177.416° true — arrivals |
| `SCL_35L_Threshold` | (−1411.15, −3337.32, 0) | 357.424° true |
| `SCL_LATAM_Base` | (−620, −1290, 0) | — |

**Departures are from 17R, not 17L.** AIP-CHILE AD 2 SCEL §1.2 runs segregated mode,
17L arrivals / 17R departures; the 17L departure is only the 00:00–07:00 noise-abatement
exception. On a 17R departure **every named feature on the field is on the LEFT**; the
right-hand side is empty grass. Build it the other way round and an employee sees their
own base mirrored. See `RECOGNITION.md` §1.

The OSM cluster tagged **"Hangar A…G" is FACh/ENAER**, ~1.2 km north — *not* LATAM.
The LATAM base is the block around (−660, −1310).

---

## 2. Linking the scenery into a new aircraft

```python
import bpy, math, os

SCEN = os.path.join(os.path.dirname(bpy.data.filepath), "..", "scenario")

def link(blend, coll):
    with bpy.data.libraries.load(os.path.join(SCEN, blend), link=True) as (src, dst):
        dst.collections = [coll]
    ob = bpy.data.objects.new(coll + "_Link", None)
    ob.instance_type = "COLLECTION"
    ob.instance_collection = dst.collections[0]
    bpy.context.scene.collection.objects.link(ob)

link("scl_field.blend",   "SCL_Field")     # the aerodrome
link("scl_field.blend",   "SCL_Light")     # sun
link("scl_field.blend",   "SCL_Anchors")   # threshold Empties
link("scl_terrain.blend", "SCL_Terrain")   # the Andes

with bpy.data.libraries.load(os.path.join(SCEN, "scl_field.blend"), link=True) as (s, d):
    d.worlds = ["SCL_World"]               # the sky
bpy.context.scene.world = d.worlds[0]

for cam in bpy.data.cameras:
    cam.clip_end = 250_000                 # the scene is 130 km wide
```

Then place the aircraft. `place_aircraft.py` does this for the A320neo and is the
worked example: it builds an Empty `SCL_Placement` at

```
psi   = atan2(-cos(track), -sin(track))          # the model's nose is local -X
O.xy  = THR_17R + track_unit * roll_at_frame_1  -  R(psi) @ pivot.xy_at_frame_1
O.z   = 0.09 - pivot.z_at_frame_1                # wheels on the pavement
```

and parents the aircraft pivot and the camera to it. **Nothing in the aircraft's own
animation is edited** — the placement lives entirely in the parent transform, so the
take-off curves stay bit-identical.

Collections and the reusable pieces are also **marked as assets** with catalogues under
*SCL Scenery*, so the Asset Browser can drag them in instead.

---

## 3. What is measured, and what I estimated

This is the part to read before quoting any number out of the model.

### Measured / published — safe to quote

| Thing | Value | Source |
|---|---|---|
| RWY 17R/35L | 3 800 × **45** m, thresholds (−1582.57, 459.21) and (−1411.15, −3337.32) | AIP-Chile ADC + DGAC IFIS, via `scl_aip_corrections.json` |
| RWY 17L/35R | 3 750 × **55** m, 35R threshold displaced 548.8 m | idem |
| Parallel separation | 1 560.5 m | idem |
| True track | 177.424° / 177.416° | idem |
| Aerodrome elevation | 474.0 m AMSL | DGAC IFIS |
| Runway markings | threshold stripes 12 × 1.75 m from 6 m; aiming point from 385 m, 45.3 × 6.0 m, inner edges ±9.25 m; TDZ pattern B at 150/300/600/750/900 m (the 450 m pair deleted by rule); centre line 30 m stripe / 30 m gap; side stripe 1.0 m | measured on rectified imagery, `scl_operations.md` §3 |
| Every footprint, taxiway centreline, apron polygon, stand and jet-bridge position | as mapped | OpenStreetMap, `scl_osm.json` |
| Terrain | Copernicus GLO-30 + SRTM control, 30/60/180 m tiers | `TERRAIN.md` |
| Control tower height | **60 m** (OSM `height` tag) | see divergence below |
| Torre de Control FACh | 15 m (OSM tag) | |
| Metalúrgica Gaymer 9 m, PCA 5 5 m | OSM tags | |

**Only 4 of the 748 building footprints carry a height tag**, and 42 carry
`building:levels` (used at 3.2 m per level). Everything else below is mine.

### Estimated by me — do NOT quote these as data

Default by OSM building type:

| type | height | reasoning |
|---|---|---|
| `hangar` | 16 m | generic GA/airline hangar, ~12 m door |
| `warehouse` | 12 m | single tall cargo bay |
| `industrial` | 10 m | |
| `office` | 14 m | ≈ 4 floors at 3.2 m plus plant |
| `apartments` | 15 m | ≈ 5 floors |
| `hotel` | 18 m | |
| `commercial` | 9 m | |
| `house` | 4 m | single storey |
| `service` | 5 m | plant rooms, small sheds |
| `roof` | 6 m | canopies |
| `parking` | 10 m | |
| `carport` | 3 m | |
| `public` / `kindergarten` | 6 / 5 m | |
| `yes` (untyped, 431 of them) | 7 m | most are single-storey airport service blocks |

Named overrides:

| building | height | why |
|---|---|---|
| **LATAM hangar** | **23 m** ridge | `scl_references.md` §7.1: a ~45 m bay for an A320 usually has **18–25 m** of clear door height. 23 m is the middle of that declared range plus roof. **No source gives this number.** |
| **LATAM ops + maintenance** | **20 m** | inferred from the hangar next to it |
| Sky Airline maintenance base | 21 m | same reasoning |
| Terminal 2 Internacional | 28 m + 7 m roof wave | proportion from `t2_panorama_anfiteatro.jpg` |
| T1/T2 concourses (piers A–F) | 18 m (+3.5 m roof wave on C–F) | idem |
| Terminal 1 Nacional | 16 m | idem |
| DGAC building | 11 m | from `apron_panoramio_2011.jpg` against the tower |
| cargo terminals, Centro de Importación, TEISA | 12 m | |
| Holiday Inn | 20 m | |
| Estacionamiento Expreso 1/2 | 11 m | |
| **apron floodlight masts** | **30 m** | the usual band for apron high-mast lighting; the photographs show them clearly taller than the terminal. No published figure found. |
| perimeter tree line | 8.5–18.5 m, ~460 trees, 30 % gaps | `scl_operations.md` §7 records a poplar/eucalyptus line along the boundary. Species, spacing and exact rows are **not** surveyed. |

Other inferences, all visible in the render:

- **The LATAM sign.** The ops-building footprint and its **west** facade (x = −721,
  y −1397…−1320, the face that looks at RWY 17R) are data. That the sign is on *that*
  face, its 5.5 m cap height, and the dark upper-facade band it reads against are
  **inferred**. The only evidence is a small distant night crop showing a white LATAM
  wordmark with the coral brandmark to its left, high on a facade over 2–3 lit office
  floors. Facade colour and cladding remain unconfirmed — `scl_references.md` §7.2.
  The wordmark geometry here is a block stand-in, not the official SVG outline.
- **Hangar doors** on the south face of the LATAM hangar, two ~45 m bays. The central
  roof joint visible on satellite supports two bays; the door face is inferred from
  where the apron is.
- **Window bands** on buildings ≥ 10 m. Generic realism, not survey.
- **Fleet mix and stand allocation** for the 86 parked aircraft. The AIP publishes stand
  *groups*, not which airline sits where. Nose-in directions on 108 of the stands come
  from the mapped guidance lines and are real; the rest are inferred from the pier they
  belong to.
- **Colours.** Read qualitatively off the reference photographs, never sampled
  numerically (`scl_operations.md` §9).

### Divergences left standing, not silently split

- **Control tower: 60 m (OSM tag) vs 65 m (DGAC's own history page).** Built at 60 m,
  as briefed. 8 % of the tallest object on the field.
- **RWY 17R length: 3 800 m (AIP, OSM) vs 4 000 m (DGAC history page).** Built at 3 800 m.
- **LATAM hangar plan: 88.5 × 81.7 m (OSM) vs 90–94 × 61–65 m (satellite, two zooms).**
  The OSM polygon is used, because everything else in the scene is keyed to OSM
  footprints and mixing sources would misalign the block.
- **17L threshold-stripe count.** The ICAO table is discrete and has no entry for a 55 m
  runway; the 45 m pattern is scaled. Not independently measured.

---

## 4. Light, sky and haze

**Sun: mid-February, ≈19:13 local, elevation 15.0°, azimuth 267.0°.**
`scl_operations.md` §5 tabulates 19:30 → 11.5° / 264.7° and 19:45 → 8.4° / 262.7°, i.e.
0.207°/min of elevation; 17 minutes earlier than 19:30 gives the values used. This is
still squarely inside the recommended band — sun in the west, behind a camera looking
east, lighting a southbound departure's starboard side — but 15° puts sin(elev) = 0.26
on the ground instead of 0.15, which is the difference between a readable airfield and a
black one. At 8.4° the whole field renders as silhouette.

Sun and sky are **balanced against each other numerically**, not by eye: a white
lambertian card was rendered under the rig and the horizontal irradiance split measured.
The shipped values (sun 13.0 W/m², world background 0.16) give roughly a 2:1
direct-to-diffuse split, which is what a 15° sun actually does. The first attempt had 90 %
of the light coming from the sky, and the symptom was pavement mirroring the sky at
grazing incidence while the soil went black.

**Haze is a number, not an adjective.** `RECOGNITION.md` §3 asked for an extinction
coefficient with a stated visibility. Every scenery material runs its shader through the
`SCL_Haze` node group, which mixes toward airlight with optical depth

```
tau(d, z) = beta0 * d * (H/z) * (1 - exp(-z/H))        beta0 = 3.912 / V
```

the exact integral of an `exp(-z/H)` aerosol layer along a straight ray from the ground
to a point at height *z*, distance *d* away. Shipped: **V = 14 km** surface visibility,
**H = 900 m** scale height. That gives

| target | distance | haze fraction |
|---|---|---|
| LATAM base | 1.1 km | 27 % |
| Terminal 2 | 2.5 km | 50 % |
| Cerro San Ramón crest | 34 km | 87 % |
| Cerro El Plomo | 55 km | 89 % |

which reproduces what the photographs show: the terminal already losing most of its
contrast at 1.5 km, and the cordillera a pale, very low-contrast wall. Airlight colour is
a scattering ramp on `dot(view, sun)` — warm gold looking west into the low sun, cool
pale blue-grey looking east at the Andes.

**Snow.** Mid-February is summer, and `scl_references.md` §3.5 records no snow on the
near ranges then. The terrain shader puts permanent snow only above ~4 300 m AMSL, so
El Plomo keeps its glaciers and the Sierra de Ramón stays brown.

---

## 5. Conventions inside the field file

z-stack, chosen so nothing z-fights:

```
 +0.12  runway markings
 +0.09  runway pavement
 +0.07  runway shoulders
 +0.06  taxiways        (+0.09 for the yellow centrelines)
 +0.05  aprons, parked aircraft
  0.00  aerodrome ground (bare ochre soil)
 -0.40  field surround
 -0.80  terrain, flattened over the field and blended back to the DEM between
        400 m and 2 600 m outside the aerodrome bounding box
```

The aerodrome is graded flat and a 30 m DEM there carries buildings and radar noise
rather than ground, so flattening is correct — but it must land **below** the built
surfaces. Leaving the terrain at exactly z = 0 was coplanar with the ground plane and
rendered as black bands across the whole infield.

Collections: `SCL_Runways`, `SCL_Taxiways`, `SCL_Aprons`, `SCL_Ground`, `SCL_Buildings`,
`SCL_LATAMBase`, `SCL_Terminals`, `SCL_Tower`, `SCL_Furniture`, `SCL_ParkedAircraft`
under `SCL_Field`; plus `SCL_Light` and `SCL_Anchors` at the top level.

Polygon budget: the field is **~42 000** faces, the terrain **4.6 M** (180 m tier
decimated ×3, 60 m tier full, 30 m tier full). The field is deliberately cheap — it is
background, and it is seen from 0.8–3 km away.

---

## 6. Licences — read this before publishing anything built from here

| Source | Covers | Obligation |
|---|---|---|
| **OpenStreetMap**, via Overpass | every footprint, taxiway, apron, stand, jet bridge, runway centreline in `scl_osm.json` — and therefore most of the mesh in `scl_field.blend` | **ODbL 1.0**. Attribution *"Airport geometry © OpenStreetMap contributors, ODbL 1.0"* **and share-alike**: a derived database, which includes a mesh generated straight from it, must be published under ODbL. |
| **Copernicus DEM GLO-30** (primary) and **SRTM v3** (control) | `terrain/*.npy`, and therefore `scl_terrain.blend` | Copernicus DEM: free use with attribution to © DLR e.V. 2010–2014 / © Airbus Defence and Space GmbH, ESA-funded. SRTM: public domain (NASA/USGS). |
| **AIP-Chile / DGAC** | runway survey, declared distances, lighting, marking spec, taxi routes | Chilean State aeronautical information, quoted as fact. Charts are **not** redistributed — only numbers and URLs. |
| **ICAO Annex 14** | the marking standard the geometry follows | ICAO ©. Used as a specification reference, quoted only in short fragments. |
| **Esri World Imagery** | used only to *measure* the runway markings and to check the OSM overlay | Restrictive. **No pixels from it are in this repository**; `refs/_map_*.png` are derived from it and are git-ignored — do not publish them. |
| **Wikimedia Commons photographs** in `refs/` | appearance of hangars, terminals, tower, apron, cordillera, haze | CC0 / CC BY / CC BY-SA per `refs/manifest.json`; git-ignored here because share-alike conflicts with this repo's asset licence. Christer T Johansson and Phillip Capper ask for named credit. |
| **LATAM brand** | the sign on the ops building, the livery on the parked proxies | Trademark. Depiction for a model of LATAM's own fleet; not a licence to reuse the marks. |

---

## 7. Checking it

```bash
blender -b --factory-startup scenario/scl_field.blend -P scenario/render_checks.py -- plan
blender -b --factory-startup scenario/scl_field.blend -P scenario/render_checks.py -- ground andes
```

`plan` renders an orthographic top-down framed to match `scl_osm_plan.png` — put the two
side by side; if the plan does not match, the build is wrong. `ground` and `andes` render
eye-level views from west of RWY 17R at the roll stations the take-off camera uses.
Output lands in `scenario/checks/`.

The angular scale of the cordillera is the thing to check hardest: the crest belongs in a
**2–5° band** above the horizon (4.63° at azimuth 75°, Cerro El Plomo, 5 425 m at 55 km).
The classic failure is modelling the range far too large.

---

## 8. Rendering the take-off animation

```bash
# 140 frames, 960x540, Cycles 64 samples, motion blur shutter 0.15
blender -b "airbus A320neo/A320neo_scl.blend" -P - <<'PY'
import bpy, os
scn = bpy.context.scene
out = "/tmp/frames_scl/"; os.makedirs(out, exist_ok=True)
scn.render.filepath = out
scn.render.image_settings.file_format = 'PNG'
bpy.ops.render.render(animation=True)
PY

# GIF: 800 px wide, 25 fps
ffmpeg -y -framerate 25 -start_number 1 -i /tmp/frames_scl/%04d.png \
  -vf "scale=800:-1:flags=lanczos,split[a][b];\
[a]palettegen=max_colors=200:stats_mode=diff[p];\
[b][p]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle" \
  -loop 0 "airbus A320neo/a320_scl.gif"
```

**Use 25 fps, not 24.** A GIF delay is an integer number of centiseconds. 25 fps is
exactly 4 cs for every frame; 24 fps is 4.1666… cs, and every encoder resolves that by
alternating 4 and 5 cs delays, which is visible as a stutter. Verify after encoding —
every Graphic Control Extension should carry the same delay:

```bash
python3 - <<'PY'
d = open("airbus A320neo/a320_scl.gif", "rb").read()
delays = {d[i+4] | (d[i+5] << 8) for i in range(len(d)-6)
          if d[i] == 0x21 and d[i+1] == 0xF9 and d[i+2] == 0x04}
print("delays (cs):", delays)      # must be a single value, {4}
PY
```
