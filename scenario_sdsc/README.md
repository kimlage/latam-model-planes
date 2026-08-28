# SDSC / São Carlos — the LATAM MRO base

The São Carlos base is built once and **linked** into every aircraft file, exactly
the way `../scenario/` works for Santiago. Fixing the aerodrome here fixes it for
the A320neo, the 787-9 and everything after.

The target is **LATAM MRO São Carlos**, on **Aeroporto Estadual Mário Pereira Lopes
(SDSC / QSC)**, Água Vermelha, São Carlos/SP: LATAM's heavy-maintenance base, nine
hangars, 22 workshops, ~2 000 people, ~270 aircraft a year, and **hangar 9**,
inaugurated 26 September 2025 for Boeing 787 heavy maintenance.

```
scenario_sdsc/
  sdsc_field.blend         the aerodrome    collections SDSC_Field, SDSC_Light, SDSC_Anchors
  sdsc_terrain.blend       the plateau      collection  SDSC_Terrain        (not committed)
  build_scenery.py         rebuilds both from the data in this folder
  render_checks.py         the visual checks
                           (plan / mro / ground / horizon / tour / ops)
  load_terrain.py          heightfield -> mesh
  blender_assets.cats.txt  Asset Browser catalogues

  --- the three clips (section 8) -------------------------------------------
  shot_common.py           the RWY 02 frame, the graded ground and the curve
                           helpers, all three clips share them, and NO bpy so
                           every shot can be solved offline in a second
  place_aircraft.py        A320neo take-off rig onto THR 02, riding the grade
  takeoff_camera.py        clip 1, the RWY 02 departure   -> a320_sdsc_v1.gif
  hangar_tow.py            clip 2, the 787-9 into hangar 9 -> b789_hangar9_v1.gif
  base_flyover.py          clip 3, the aerial tour        -> sdsc_base_v1.gif
  render_clip.py           frames on the GPU, shared by all three
  verify_gifs.py           the GIF timing gate - a real parser, not a byte scan
  sdsc_takeoff.blend       the placed A320neo, 140 frames, no camera yet
  sdsc_takeoff_v1.blend    clip 1's scene
  sdsc_hangar_tow.blend    clip 2's scene
  sdsc_base_flyover.blend  clip 3's scene
  ac_curve_sdsc.json       the graded aircraft track, for offline tuning

  sdsc_aip_survey.json     the survey constants, every value with its source     <- read first
  sdsc_osm.json            aerodrome + MRO geometry in the local frame (ODbL)
  sdsc_osm_plan.png        the plan, drawn                    <- the build's check image
  sdsc_osm_plan_mro.png    the MRO block, drawn
                           (roads / water / landuse are in BOTH from phase 4)
  sdsc_operations_wind.json  which runway the wind favours (ERA5 2021-2025)
  sdsc_operations_sun.json   solar geometry, computed here
  sdsc_references.md       what each photograph proves, and what I could NOT establish
  RECOGNITION.md           what makes the place recognisable, and the traps
  TERRAIN.md               the heightfields, the horizon, and why there isn't one
  terrain/                 3 heightfield tiers + horizon profiles + silhouette
  refs/manifest.json       the reference photographs, cited - never committed
  lib/frame.py             the ENU frame. Single source of truth.
  build_osm.py  build_terrain.py  prepare_dem.py  fetch_dem.sh
  horizon.py    silhouette.py     verify.py       plot_osm_plan.py
```

`sdsc_terrain.blend` is 108 MB of mesh and is **git-ignored**. It regenerates in
about ninety seconds from the heightfields, which *are* committed:

```bash
blender -b --factory-startup -P scenario_sdsc/build_scenery.py -- --field     # ~10 s
blender -b --factory-startup -P scenario_sdsc/build_scenery.py -- --terrain   # ~90 s
```

Rebuild the survey data underneath it:

```bash
./fetch_dem.sh              # ~770 MB of DEM tiles, not committed
python3 build_terrain.py    # ~2 min
python3 horizon.py          # ~40 s
python3 silhouette.py
python3 verify.py           # the checks in TERRAIN.md §4 and below
python3 build_osm.py        # re-queries Overpass; --offline reuses sdsc_osm_raw.json
python3 plot_osm_plan.py && python3 plot_osm_plan.py --mro
cd .. && python3 refs_fetch.py scenario_sdsc     # the photographs
```

---

## 1. The reference frame

One frame, `lib/frame.py`, used by every file here. Blender units are metres, 1:1.

| | |
|---|---|
| Type | local **ENU** tangent plane on WGS84 |
| Origin | lat **−21.8818417**, lon **−47.9039639** — the published landing threshold of **RWY 02** |
| Origin source | AISWEB/ROTAER declared-distance table, `S 21 52 54.63 / W 047 54 14.27` |
| Axes | x = East, y = North, z = Up, metres |
| Vertical datum | **z = 0 at 807.0 m AMSL**, the published SDSC aerodrome elevation (2648 ft) |
| Runway true track | **001.026°** — computed, and confirmed by 023° magnetic with VAR 22° W |

**Why THR 02.** Santiago's origin is the threshold where the take-off roll starts;
this is the same choice. RWY 02 is the departure end (`RECOGNITION.md` §1), it is the
uphill/southern end, and putting the origin there makes `distance_along_roll_m` in
`sdsc_osm.json` directly usable.

> Santiago ended up with **two** origins 1.51 m apart — the OSM task and the terrain
> task each picked their own — and had to reconcile them afterwards. That does not
> happen here: `build_osm.py` and `build_terrain.py` both import `lib/frame.py`.

### The runway is not level

| point | x, y (m) | z (m) | AMSL |
|---|---|---|---|
| **THR 02** (origin) | 0.00, 0.00 | **−2.33** | 2640 ft = 804.67 m |
| **THR 20** | 29.00, 1 619.72 | **−12.39** | 2607 ft = 794.61 m |
| south pavement end (derived) | −0.93, −51.99 | — | — |
| north pavement end (derived) | 29.86, 1 667.71 | — | — |
| ARP | 65.20, 603.77 | +0.11 | 2648 ft |

It falls **10.06 m over the 1 620 m between thresholds** — 0.62%, downhill toward 20.
Copernicus GLO-30 independently reads 12.0 m. **z = 0 is the aerodrome elevation, not
the runway surface.** Build the strip flat and the far end is wrong by an aircraft
tail's height.

### Anchors — the only thing a new aircraft needs

`SDSC_Anchors` carries Empties whose **+Y axis points down the take-off track**, so
an aircraft can be parented to one. **Their z is the runway surface at that
station**, not zero — this runway is not level.

| Empty | position (x, y, z) | track |
|---|---|---|
| **`SDSC_02_Threshold`** | (0.00, 0.00, **−2.33**) | 001.026° true — **departures** |
| `SDSC_20_Threshold` | (29.00, 1619.72, **−12.39**) | 181.026° true |
| `SDSC_LATAM_MRO` | (912.5, 1608.9, **−37.10**) | — |
| `SDSC_Hangar9` | (750.0, 1637.5, **−37.10**) | — |

**Departures are from RWY 02 — northbound, true track 001.026°, and downhill.**
On a 02 departure the LATAM MRO is on the **RIGHT**, abeam between 1 602 m and
1 937 m into the roll (at or just after rotation) and 797–1 287 m out. The only
thing on the **LEFT** is the Aeroclube, in the first 500 m at 180–280 m out. Build
it mirrored and a mechanic sees their own base on the wrong side —
`RECOGNITION.md` §1.

---

## 1b. Linking the scenery into an aircraft file

```python
import bpy, os

SCEN = os.path.join(os.path.dirname(bpy.data.filepath), "..", "scenario_sdsc")

def link(blend, coll):
    with bpy.data.libraries.load(os.path.join(SCEN, blend), link=True) as (src, dst):
        dst.collections = [coll]
    ob = bpy.data.objects.new(coll + "_Link", None)
    ob.instance_type = "COLLECTION"
    ob.instance_collection = dst.collections[0]
    bpy.context.scene.collection.objects.link(ob)

link("sdsc_field.blend",   "SDSC_Field")     # the aerodrome
link("sdsc_field.blend",   "SDSC_Light")     # sun
link("sdsc_field.blend",   "SDSC_Anchors")   # threshold Empties
link("sdsc_terrain.blend", "SDSC_Terrain")   # the plateau

with bpy.data.libraries.load(os.path.join(SCEN, "sdsc_field.blend"), link=True) as (s, d):
    d.worlds = ["SDSC_World"]                # the sky
bpy.context.scene.world = d.worlds[0]

for cam in bpy.data.cameras:
    cam.clip_end = 250_000                   # the scene is 240 km wide
```

`../scenario/place_aircraft.py` is the worked example for Santiago and the same
maths applies here, with **one change**: the threshold z is **−2.33**, not 0, and
the wheels must ride the grade all the way down the roll —

```
O.z  =  rwy_z(roll) + 0.09  -  pivot.z_at_frame_1        rwy_z(a) = -2.33 - 0.006210*a
```

Collections and the reusable pieces are also **marked as assets** with catalogues
under *SDSC Scenery*.

---

## 2. What is in `sdsc_osm.json`

OpenStreetMap via Overpass, **2026-08-23**, converted to the frame above. Counts:

| | |
|---|---|
| runways | **1** (way/35448784, `02/20`) |
| taxiways | 8 |
| aprons | **6** — 4 at the Aeroclube, 1 mid-field, 1 at the MRO (35 729 m²) |
| hangars (`aeroway=hangar` or `building=hangar`) | **9** — but **5 are the Aeroclube's**, not LATAM's |
| terminals | 1 |
| buildings | **95** |
| parking positions | 3 (all Aeroclube; **none at the MRO**) |
| holding positions | 2 |
| navaids / windsocks | 1 / 1 |
| landuse polygons | 35, including the `TAM MRO` site |
| roads / water | 330 / 80 |
| aerodrome boundary | 1 ring, 124 points, stitched from 18 member ways |

Plus two derived blocks: `latam_mro` (the site, its members, its projection onto the
02 roll) and `departure_02_landmarks` (77 features projected onto the take-off roll).

**All of it is now built.** Phases 2 and 3 used the runway, taxiways, aprons,
hangars, terminals, buildings and the boundary ring, and left the 330 roads, 80
water features and 35 landuse polygons in the plan only. §3 has what each of
them became and which side of the honesty line it lands on. The one thing in
this file that is still not built is `other` — 102 `man_made` nodes, of which 94
are untagged and 6 are water towers.

**Multipolygon rings are stitched.** The aerodrome boundary is cut into 18 separate
ways and the MRO site into 6. Taking the longest member — the obvious shortcut —
gives a fragment, and the aerodrome then measures 1.0 × 0.85 km instead of its real
1.72 × 2.16 km. `build_osm.py:stitch()` joins them end to end.

### The MRO block

**Hangar 9 is not in this data and is added by the build.** Everything below is the
2017 tracing.

| | |
|---|---|
| site polygon | 684 088 m², bbox x 380…1 445, y 1 148…2 069, extent 1 064 × 921 m |
| mapped building footprint | 78 527 m² across 28 features |
| mapped apron | 35 729 m² |
| largest building | `relation/7422965` — **471.5 × 137.3 m**, 43 140 m², long axis 001.1°, tagged only `building=yes`, unnamed |
| projection on the 02 roll | site 1 155–2 095 m along, 360–1 407 m right; **buildings 1 602–1 937 m along, 797–1 287 m right** |

**Every MRO building and apron in OSM is version 1 from one tracing session on
2017-07-27** (except way/708700156, 2019, and way/510750642, 2021). **Hangar 9 is not
in this data.** See `sdsc_references.md` §6.

---

## 3. What is measured, and what I estimated

The honesty contract. Read this before quoting any number out of this folder.

### Measured / published — safe to quote

| thing | value | source |
|---|---|---|
| Runway 02/20 | **1 720 × 45 m ASPH, PCN 47/F/A/X/T** | AISWEB/ROTAER |
| Thresholds | 02 `S 21 52 54.63 / W 047 54 14.27`, 20 `S 21 52 01.97 / W 047 54 13.26` | ROTAER declared-distance table |
| Threshold displacements | 52 m at 02, 48 m at 20 | ROTAER |
| Declared distances | **TORA 1672/1668, TODA 1672/1668, ASDA 1720/1720, LDA 1668/1672** | ROTAER |
| Threshold elevations | **2640 ft / 2607 ft** | SDSC IAC charts |
| Aerodrome elevation | **807 m / 2648 ft** | ROTAER and both IAC charts |
| Magnetic variation | **22° W**, annual change 04′ W | both IAC charts, AIRAC AMDT 2512A1 |
| Magnetic final courses | 023° / 203° | IAC charts |
| True track | **001.026°** | computed from the published thresholds; +22° = 023.03° vs a published 023° |
| Geoid undulation at the thresholds | −6.381 m / −6.398 m | ROTAER |
| AFIS / ATIS | 128.125 "RÁDIO SÃO CARLOS" / 127.70 | ROTAER, IAC |
| Hours, lighting-on-request, the international-ops restriction | as published | ROTAER remarks |
| Every footprint, taxiway, apron polygon | as mapped | OpenStreetMap, `sdsc_osm.json` |
| Terrain | Copernicus GLO-30 + SRTM control, 30/60/180 m tiers | `TERRAIN.md` |
| Horizon band, all 360° | **−0.32° to +1.30°** | `terrain/horizon_5deg.json` |
| Largest MRO building's height | **+12.9 m** above its platform (a floor, not the ridge) | Copernicus DSM, 54 grid cells |
| MRO platform | **769.9 m AMSL**, 34.8 m below THR 02 | Copernicus median over 348 samples inside the apron polygon, p10–p90 769.3–771.3; SRTM agrees ±4 m |
| mid-field apron | **795.9 m AMSL** | idem, 121 samples |
| Aeroclube apron | **804.9 m AMSL** | idem, 25 samples |
| `relation/7422966` roof | **+14.0 m** above its platform | Copernicus DSM, 784.8 over the footprint against 770.8 around it |
| Wind favouring RWY 02 | 53.4% all hours, **63.2%** in AD opening hours | ERA5 2021–2025 |
| Solar geometry | see `sdsc_operations_sun.json` | computed here (NOAA algorithm) |

**Zero of the 95 building footprints carries a `height` tag, and none carries
`building:levels`.** Santiago had 4 heights and 42 level counts out of 748. Here there
is nothing. **Two** heights are measured — the two DSM rows above — and every other
height in `sdsc_field.blend` is an estimate.

### The MRO platform: the phase-1 check-before-build, answered

Phase 1 flagged "the MRO reads ~35 m below THR 02 in both DEMs" as scene-defining
and unconfirmed. Phase 2 checked it three ways and **it stands**:

1. **The grid, properly sampled.** Median 769.9 m over 348 points inside the apron
   polygon, p10–p90 769.3–771.3 — a 2 m spread over 35 729 m², which is a graded
   platform, not DEM noise. 34.8 m below the published THR 02.
2. **`refs/mro_centro_tecnologico_2009.jpg` agrees.** That camera is at (498, 2094),
   where the grid reads 762.4 m, and the photograph shows the hangar line standing
   on an embankment **above** the cane field with the buildings' feet cut off behind
   the bank — which is what an 8 m rise looks like.
3. **`refs/sdsc_field_from_sp318_2013.jpg` does NOT disagree, because it is not of
   the MRO.** See `sdsc_references.md` §2.1: the sight line from the SP-318 to the
   base is blocked by the runway crest, and the frame is of the mid-field apron.
   `render_checks.py ground` renders that blocked sight line on purpose as
   `ground_sp318_from_west.png` — **the MRO must not be visible in it.**

### Estimated by me — do NOT quote these as data

Two lists. The first was already in phase 1 and is about the *survey*; the second
is new and is about the *model*.

#### Inference in the survey

- **The reading of the declared distances.** LDA = 1720 − own displacement; TORA =
  1720 − *far* end's displacement; ASDA = 1720. That pattern is what you get if the
  end 48/52 m count as stopway as well as displacement. **DECEA publishes no
  stopway/clearway declaration for SDSC.** The arithmetic is published; the reading
  is mine. Either way the usable take-off run is **1 672 m**.
- **The pavement ends.** Derived by walking the published thresholds back along the
  measured track by the published displacements.
- **The western rise.** ~845 m at 1–3 km west, ~40 m above the field. Both DEMs are
  *surface* models, so part of that may be eucalyptus or cane canopy.
- **RWY 02 as the departure end.** Nothing forces it — SDSC is VFR with AFIS, not an
  ATC flow. Wind (63.2% in opening hours), slope (downhill) and TORA (4 m longer)
  all lean the same way. A well-supported choice, not a published rule.

#### Inference in the model — every height, and the appearance

**Building heights.** There is no OSM `height` or `building:levels` tag anywhere on
this field, and no published height for any building on it. Two DSM measurements
exist, one photogrammetric measurement was made here, and **everything else in this
table is mine**.

| element | height | reasoning |
|---|---|---|
| `relation/7422965` — the 471 × 137 m workshop spine | **13.0 m eave / 15.2 m ridge** | the DSM measures **+12.9 m**, and phase 1 called that a **floor** because a 30 m DSM smears roof edges inward. A very shallow gable on top of that floor. |
| `relation/7422966` — the 101 × 57 m **widebody bay** | **17.5 m eave / 20.0 m ridge**, door 84 × 16.4 m | the DSM measures **+14.0 m** (784.8 over the footprint against 770.8 around it) — but the building is 57 m across, i.e. **two** 30 m cells, so that is a floor for the same reason +12.9 is. A 767-300ER's fin is 15.85 m and an A330-200's 17.4 m, and both types are documented at this base; neither clears 14 m. 17.5 m is the smallest eave that works. **This is the one place where an estimate deliberately overrides a measurement, and the reason is written into the source.** |
| `relation/7422968`, `way/708700156` — 50 × 46 m and 44 × 42 m hangars | 12.0 m | in scale with the two above |
| `relation/7422970` — the mid-field barrel vault | **12.7 m apex** | photogrammetry on `refs/sdsc_field_from_sp318_2013.jpg`: see below |
| **hangar 9** | **22 m eave / 26 m ridge, 130 × 95 m** | **declared inference, no source at all** — see the next block |
| MRO workshop strips, 105 × 25 m | 7 m | single-storey shop |
| the two ~80 m museum halls | 11 m | `refs/museu_tam_2011.jpg` shows a clerestory hall, not a hangar |
| the five **Aeroclube** hangars | 12 m | single-bay light-aircraft sheds, 18–30 m across; they are NOT LATAM's — `RECOGNITION.md` §5, and half of OSM's nine `hangar` polygons on this field belong to them |
| the 89 untyped `building=yes` footprints | 5 m | most are village houses and field sheds south of the aerodrome |
| the chequerboard tower | 21 m to the cab, 29 m to the antenna tip | horizon-ratio method, below |
| **apron floodlight masts** | **16 m** | horizon-ratio again: in the 2013 frame the lamp clusters sit within ~1 m of a 12.7 m apex beside them. **Santiago's 30 m is wrong here** and copying it is the obvious mistake. |
| the guyed lattice antenna mast | 30 m | the tallest thing in the 2013 frame, at about 2.3× the vault |
| the derelict concrete block | 9.5 m, three storeys | unidentified, `sdsc_references.md` §6.9 |

**The method behind the photogrammetric ones**, because it is checkable and
distance-free. For an object standing on a plane and a camera at height *h*, the
ratio (pixel height of the object) ÷ (pixel depression of its base below the
horizon) equals *H/h* — no focal length, no distance. Applied to the parked
widebody in `refs/sdsc_field_from_sp318_2013.jpg` it gives *h* ≈ 7.3 m; applied to
the arch beside it, 0.755 × the aeroplane's own 17.4 m fin = **12.7 m**. The
Copernicus DSM reads +13 to +15 m over three MRO footprints by a completely
different route. **The hangars on this field are low**, and that is the single
most useful number phase 2 produced.

**Hangar 9 — declared inference, and it must never be presented as data.**
Inaugurated 2025-09-26, R$40 M, ten months, for 787 heavy maintenance, painting of
large aircraft, and three A320s at once. **No published dimension, no published
position, and not in OpenStreetMap** — every MRO footprint there is version 1 from
a single tracing session on 2017-07-27, eight years before it existed.

*Size* comes from what it has to hold, not from a source: a 787-9 is 62.8 m long,
60.1 m in span and 17.0 m tall, so the door must clear ~68 m and ~20 m; three
A320s nose-in at 35.8 m span each need ≥115 m of usable width; and a paint bay has
to enclose the whole aeroplane, so ≥70 m deep. That gives **130 × 95 m, eave 22 m,
ridge 26 m, door 78 × 20.5 m**.

*Position* comes from the apron geometry: a search over the MRO site polygon for a
free 140 × 105 m rectangle clear of every mapped footprint, of the apron and of the
taxiway returns **(750, 1638)** as the candidate nearest the existing apron — 56 m
from it, on level platform ground, taxiway-served. **It is not from imagery.** If a
2025 image later puts it elsewhere, move the `HANGAR9` block at the top of
`build_scenery.py`: nothing else in the build depends on where it is.

**What the base looks like in LATAM colours — the largest gap, decided and declared.**
Every free-licence photograph of this site is 2006–2014, i.e. TAM: light-grey ribbed
cladding under a broad **dark red-maroon fascia band** carrying the TAM wordmark.
The base has been LATAM since 2016 and hangar 9 opened under LATAM in 2025. No
free-licence photograph of it in LATAM colours was found.

The build therefore keeps everything that *is* photographed — the barrel vault, the
shallow gable, the ribbed cladding, the fascia band's height and its position under
the eave, the nose-in line, the white-rendered wall with the black welded-mesh
fence, the **bright red space frame** inside the hangars — and repaints only the
**band colour** and the **mark**, because the date says so. The mark is the official
SVG lockup via `latam_livery_kit.importar_svg_2_camadas`, never a lookalike font,
the same rule the fleet livery follows.

**This is a decision, not a finding.** `build_scenery.py` carries it as one
constant:

```bash
SDSC_LIVERY=tam blender -b --factory-startup -P scenario_sdsc/build_scenery.py -- --field
```

rebuilds the base exactly as it is photographed, in TAM maroon. The mid-field
hangar's corner returns are left **oxide red** either way, because that building is
not identified as LATAM's.

**Other inference visible in the render**, all of it declared here and in the
source:

- **The runway markings.** SDSC has no ADC (`sdsc_references.md` §6.1), so threshold
  stripes, designator, aiming point, TDZ, centreline, side stripes and the
  displaced-threshold arrows are the **ICAO Annex 14 pattern for a 45 m code-C
  runway with LDA 1668/1672 m**, applied by me: 12 threshold stripes, aiming point
  at 300 m, four TDZ pairs at 150/450/600/750 m with the 300 m pair deleted by rule,
  30/30 m centreline. Nothing on this pavement is published.
- **Taxiway widths** (23 m on the MRO link, 12 m at the Aeroclube) and the two turn
  pads. OSM carries no width tag and there is no ADC.
- **Edge lights at 60 m, and a four-box PAPI 300 m in on the left at each end.**
  ROTAER's runway line carries a lighting code at each threshold and two more along
  it; the layout is the standard one, applied by me.
- **Which face the doors are on, and it is not the obvious one.** `relation/7422965`
  has a bbox of x 938…1080, but its ring is **C-shaped**: the west edge is at x = 938
  only for y 1569…1758, steps back to x = 988 for y 1758…1853 and to x = 1027 for
  y 1852…2039. The first build painted a band along "x = 938" for the whole length
  and hung it in mid-air for 280 m of it; the 135 mm ground check is what caught it.
  The face that actually stands on the apron — node for node, the apron polygon's own
  east edge runs along it — is **`relation/7422966`'s west wall at x = 931,
  y 1759…1859**, the polygon OSM tags `aeroway=hangar`. So the hangar is the block in
  front and the 471 m spine behind it is the workshop line. That reading is
  inference, but it is the one the two polygons and the apron agree on, and it
  answers `sdsc_references.md` §6.5 as far as the geometry can.
- **The door itself** — 84 × 16.4 m on that face — and the fascia band's three runs
  (that hangar's face, the 172 m of spine wall at x = 938 that looks at the runway,
  and the 164 m at x = 1027 that looks at the north apron) are mine.
- **The nose-in line.** OSM maps three parking positions and all three are at the
  **Aeroclube**; not one MRO stand is surveyed. Six aeroplanes: two nose-in on the
  hangar face at x = 931 with their tails toward the runway, four on the apron's four
  northern lobes, which run north–south and are what the mapped polygon offers. All
  six are clear of `way/708700156`, the 44 × 42 m hangar standing in the middle of
  that apron. Their positions follow the polygon; their spacing and fleet mix do not.
- **The perimeter wall's line.** The white wall and black mesh are photographed
  (`refs/mro_airbus_esquadrilha_2010.jpg`); where they run is drawn along the south
  and east edges of the MRO block by me.
- **The tree line.** At SDSC this is scenery, not detail — see §4b. The aerodrome
  boundary ring and the 80 mapped watercourses it follows are data; the species,
  spacing, rows and 8–20 m heights are not.
- **The cane surround.** Blocks, rotation and palette are read qualitatively off
  `refs/mro_centro_tecnologico_2009.jpg` and the region's satellite impression.
  Field boundaries are procedural, not the mapped parcels.
- **Colours.** Read qualitatively off the photographs, never sampled
  photometrically — the same rule `../scenario/` follows.

#### Inference in the surround — phase 4

Phase 2 left "roads, water and landuse tint in the plan and not the build, as at
Santiago". At Santiago that was defensible: the city is 15 km out and the
farmland grid carried the middle distance. Here the field is 1.7 × 2.2 km and
the surroundings fill the frame of every aerial, so the same omission rendered
an aerodrome floating on coloured ground. **330 roads, 80 water features and 35
landuse polygons were already in `sdsc_osm.json` and are now built.**

| element | side | what it rests on |
|---|---|---|
| **158.5 km of road**, 287 ways | **data** | every centreline, class and `surface` tag from OSM. Includes the **SP-318**, whose two carriageways are mapped apart, 620–700 m west of the runway — the road `refs/sdsc_field_from_sp318_2013.jpg` was shot from |
| **paved vs unpaved** — 70.4 km against 88.1 km | **data** | OSM's own `surface` tag. Not cosmetic: 35 of the 101 `unclassified` ways are tagged unpaved, and an unpaved road in this soil is a bright red-orange line, not a black one |
| road **widths** (8.5 m motorway → 3.5 m track) | *estimated by me* | **not one way here carries a `width` or `lanes` tag.** An untagged `surface` is read as paved, which is the majority reading |
| **62.0 km of stream**, 7 water bodies, 1 wetland | **data** | every centreline and shoreline. Includes **way/154922934, a 71 772 m² reservoir at (1097, 1137)** — a kilometre south-west of the MRO, in frame for most of the tour, and simply not built before |
| stream **widths** (3.5 / 5 / 7 m) and water **levels** | *estimated by me* | no width tag; the level is the 40th percentile of the ground under each shoreline. The 30 m DEM does not resolve a channel, so the streams lie **on** the ground rather than in it |
| **19 km² of farmland parcels** — Fazenda São Roberto, Chile, Palmeiras, Santo Antônio, do Saltinho, Bela Vista | **data** | the mapped polygons, which replace `build_ground`'s **procedural** parcel pattern with surveyed boundaries. From 230–700 m up, that is the difference between a landscape and a texture |
| which **crop** each parcel carries | *estimated by me* | four-way palette (cane, cut cane, tilled, pasture) dealt by a hash of the OSM id. **Nothing in OSM says.** |
| **Água Vermelha**: 2 residential polygons (75 201 m²), the street grid, 14 footprints incl. the Capela de São Roque, the Unidade de Saúde da Família, the Assembleia de Deus | **data** | the mapped village |
| **300 infill houses** in it | *estimated by me* | 14 footprints in 7.5 ha is an under-mapping, not a hamlet. `refs/agua_vermelha_avenida.jpg` shows a continuous frontage of single-storey rendered houses under red pantile. One house per ~17 m of mapped frontage, jittered; `VILLAGE_INFILL = False` rebuilds with only the 14 surveyed footprints |
| **541 power poles + conductors** on the road verges | *estimated by me* — **presence photographed, route not** | a conductor is strung right across the top of `refs/sdsc_field_from_sp318_2013.jpg`, shot from the SP-318 verge, and `refs/agua_vermelha_avenida.jpg` shows the poles. **OSM's extract carries no `power` way at all**, so the line follows the motorway/secondary/tertiary verges inside 3 km, at the standard rural 52 m / 9.2 m |
| **3 cane-loading yards** | *declared inference, no source at all* | there is nothing in OSM. They are here because 19 km² of surveyed farmland with no sign that anyone works it is the less true of the two |
| **the gallery forest on the watercourses** | **data** (the courses) / *estimated by me* (the trees) | `build_trees` had a latent bug: it read `w["xy_m"]`, and a way-type water feature carries its polyline under `polygon_xy_m`. **The riparian loop never ran** — every tree in phase 3's scene came from the aerodrome boundary ring. Fixed; the count went 276 → 1 171 |

#### Inference in the operation — phase 4

This is a working MRO — **~2 000 people, 22 workshops, ~270 aircraft a year, 16
in work at once** — and phase 2 built none of it. Whole aeroplanes parked
nose-in on an empty slab is what a *model* of a base looks like.

| element | side | what it rests on |
|---|---|---|
| **the car parks' geometry**, 766 m of aisle in four grids | **data**, and it was a surprise | OSM has no `amenity=parking` here, but it maps the MRO's landside circulation as `service` ways — and four of those clusters are unmistakable **aisle grids**: parallel 60–120 m runs 18–46 m apart inside closed loops. `_aisles()` finds them by that geometric test, not by a hand-written list, so a future OSM refresh moves them by itself |
| that those aisles are **staff** parking; the 22 m slab; the 2.65 m bay pitch; **541 cars** at 72% of 560 bays | *estimated by me* | nothing published says how many of the 2 000 staff drive. **The mapped aisles hold ~560 cars, which is short of what 2 000 people need** — recorded below as still open, not silently filled with an invented overflow lot |
| **the maintenance kit is yellow, the tool trolleys red** | **photographed** | `refs/mro_centro_manutencao_2006.jpg` (a Fokker 100 in a bay on this site) and `refs/mro_centro_tecnologico_2010.jpg` (an A320 with the fan cowls open) are both full of yellow tubular access towers, yellow wing docks and yellow rolling stairs, with red trolleys between them |
| **aircraft apart** — 6 of 9 stands: cowls open, an engine off, an airframe on jacks, two in full dock | **photographed as a state**, *inferred as an allocation* | `refs/mro_centro_tecnologico_2010.jpg` is the cowls-open A320; `refs/mro_centro_tecnologico_2009.jpg` has a stripped fuselage inside a tall dock **out on the apron**. No photograph says which aeroplane is in what check on a given day. ROW0, ROW1 and H9 are deliberately left whole — `base_flyover.py` swaps those three for the real 767-300ER, A320neo and 787-9 this repository built, and a hero model with its engines missing would be a different lie |
| **71 pieces** of dock, tower, stair, jack, engine cradle and trolley | *estimated by me* | positions and counts. Nothing surveys a ramp's kit |
| **75 GSE units** — tugs with towbars, GPUs, air-start, belt loaders, stairs, vans, bowsers, cherry pickers | *estimated by me, all of it* | **no photograph of LATAM's São Carlos ground fleet was found** and OSM maps no vehicle. What is not inference is that an apron working 270 aircraft a year has these on it. `refs/mro_centro_tecnologico_2009.jpg` shows small dark vehicles clustered at the nose of every aeroplane in the line; that is the level this reproduces |
| **30 containers** in blocks against the hangar line | **photographed** (that they are there) / *inferred* (where) | white ISO boxes along the apron in the 2009 frame, a dark red skip on the hangar floor in the 2010 one. Placed by walking the **mapped apron polygon's own edge**, so none stands on grass |
| **the gate and guard house** | *estimated by me*, with the position constrained | the wall and its black mesh are photographed (`refs/mro_airbus_esquadrilha_2010.jpg`) and phase 2 drew its line. Four mapped service ways — way/510750444, /445, /446, /510750640 — cross that run at **x = 914–930**, which is where the landside road really enters the airside, so the wall opens there. The guard house, canopy and boom are mine |

**Every stand was checked against the mapped concrete.** A 21 m circle — a
narrowbody half-span — round each of the nine has to lie inside apron
`relation/7422967` and clear of every mapped MRO footprint. The first pass put
two aeroplanes on the grass west of the ramp and one on a building; the plan
check caught it. The same rule now places the containers and the GSE rows.

### Divergences left standing, not silently split

Full text in `sdsc_aip_survey.json` → `divergences_recorded_not_split`.

- **Runway length: 1 720 m (DECEA, today) vs "from 1 400 m to over 1 700 m" (Alckmin,
  2025, on the 2001 works) vs 1 460 × 30 m before 2001 (Wikipedia).** No conflict about
  today. Build 1 720 × 45 m.
- **A proposed extension to 3 000 × 60 m**, reported as pending DAESP and environmental
  approval. **Proposed, not built.** Recorded because a search will surface it.
- **MRO fleet share: ">60% of the group fleet" (LATAM, 2025) vs "~70% in Latin
  America" (CNN Brasil).** Different denominators, both LATAM's own. Not averaged.
- **MRO area: 95 000 m² (LATAM, built area) vs 684 088 m² (OSM site polygon) vs
  78 527 m² (OSM building footprints).** Three different things; none is wrong. Do not
  quote 95 000 m² as a site footprint.
- **OSM relation/7422930 is tagged both `TAM MRO` and `TAM Museum`/`Q3868501`.** The
  polygon is the MRO; the museum tags are wrong. The museum did share the site and
  closed in 2016.
- **OSM's runway geometry is 9.4 m shorter than its own `length=1720` tag.** Use the
  AIP thresholds for the runway; use OSM for taxiways, aprons and footprints.
- **SRTM reads 11.4 m low at THR 20** (783.2 m vs a published 794.6 m and Copernicus's
  794.0 m). Copernicus is primary; SRTM is the control and here it is the outlier.

---

## 4. Conventions inside the field file

### The z-stack — and here it is RELATIVE, not absolute

Santiago's stack is a set of constant heights, because Santiago's aerodrome is
graded flat. **This one is not.** Every offset below is measured from
`graded(x, y)`, the graded aerodrome surface `build_scenery.py` computes: the
published runway grade over the strip, the measured platform level over each of
the three aprons, and the raw Copernicus DEM everywhere else, with smooth blends
between them.

```
 +0.12  runway markings
 +0.09  runway pavement       (surface: -2.33 at THR 02, -12.39 at THR 20)
 +0.07  runway shoulders
 +0.06  taxiways              (+0.09 for the yellow centrelines)
 +0.05  aprons, parked aircraft
  0.00  graded(x, y)  <- the aerodrome ground
 -0.80  terrain, graded to the SAME function and blended back to the raw DEM
        between 500 m and 2 600 m outside the aerodrome bounding box
```

`graded(x, y)` forces the runway grade and three platform levels, and nothing else:

| region | level | source |
|---|---|---|
| runway strip, full weight to ±90 m, gone by ±260 m | `-2.33 - 0.006210·a` | published THR elevations |
| MRO platform, x 620–1100, y 1530–2060, 160 m fade | **−37.10** (769.9 m AMSL) | Copernicus median, 348 samples inside the apron polygon, p10–p90 769.3–771.3 |
| mid-field apron, 70 m fade | **−11.10** (795.9 m) | idem, 121 samples |
| Aeroclube apron, 60 m fade | **−2.10** (804.9 m) | idem, 25 samples |

`build_scenery.py` prints all of these back against the grid on every build.
**Do not flatten this aerodrome to one z**: it would put the MRO 35 m in the air
or the runway 35 m underground.

### Collections

`SDSC_Runway`, `SDSC_Taxiways`, `SDSC_Aprons`, `SDSC_Ground`, `SDSC_Buildings`,
`SDSC_LATAM_MRO`, `SDSC_Aeroclube`, `SDSC_Midfield`, `SDSC_Vegetation`,
`SDSC_Furniture`, `SDSC_ParkedAircraft`, **`SDSC_Roads`**, **`SDSC_Water`**,
**`SDSC_Operations`** under `SDSC_Field`; plus `SDSC_Light` and `SDSC_Anchors`
at the top level.

`SDSC_ParkedAircraft` now holds **only the five Aeroclube light aircraft**.
Phase 5 (§9) moved the ten airliner stands into `fleet_placement.py`, which
builds a top-level **`SDSC_Fleet`** collection of collection-instance empties in
each CLIP file rather than in the shared field. That is why a check frame
rendered off the bare `sdsc_field.blend` must call `populate()` first, and why
`render_checks.py` does.

Polygon budget: the field is **134 019** faces, the terrain **3.7 M** (180 m tier
decimated ×3, 60 m and 30 m tiers full). The field is deliberately cheap — it is
background, and the MRO is seen from 0.8–1.9 km in the departure and 0.4–1.0 km
in the tour.

| collection | faces | what dominates |
|---|---|---|
| `SDSC_Ground` | 51 378 | the cane sheet's 60 m inner ring (27 468, the price of the fix in §4b) and the 25 m aerodrome pad; then 4 931 crop cells |
| `SDSC_Vegetation` | 46 317 | 1 171 trees. **276 of them before phase 4** — the riparian rows had never run |
| `SDSC_Furniture` | 8 824 | 541 power poles and their conductors, floodlight masts, PAPI, windsock |
| `SDSC_Operations` | 7 151 | 541 cars, 75 GSE units, 71 dock pieces, 30 containers, the aisle slabs |
| `SDSC_LATAM_MRO` | 6 393 | hangar 9, the frontage, the perimeter wall, the gate |
| `SDSC_Roads` | 5 685 | 158.5 km of centreline, resampled to 30 m so it lies on the ground |
| `SDSC_Buildings` | 3 671 | 300 village houses and their roofs, the field sheds |
| `SDSC_Water` | 1 874 | 62 km of stream, 8 water bodies |
| everything else | 2 726 | runway, taxiways, aprons, parked aircraft, mid-field, Aeroclube |

The **fleet** is not in that budget and does not want to be: ten real masters
arrive as links, ~330 k triangles of *unique* geometry per type, instanced. §9.5
is what they cost.

Santiago's field is ~42 000 faces on purpose and this one was 66 455 after the
cane fix. Trebling it buys a village, 158 km of road, 62 km of watercourse, a
gallery forest that was missing entirely, and a ramp with an operation on it —
against a terrain mesh 28× larger that has always been affordable. The rule that
did not change for the *kit*: **simple proxies that read at 200–700 m**, not
detailed models nobody sees. Every car is ten faces; every GSE unit is two
boxes. The **aeroplanes** are the deliberate exception, and phase 5 (§9) is the
argument for it: a car at 400 m is a coloured box to anybody, but an airliner
has a silhouette people know, and the owner spotted the difference from a GIF.

---

## 4b. Light, sky and haze

**Sun: 26 September, 17:00 local (UTC−3), elevation 15.14°, azimuth 274.46°** —
straight out of `sdsc_operations_sun.json`, sample *"hangar 9 inauguration"*.

Why that instant, and not noon: São Carlos is at latitude −21.88, so the sun is
**87° at noon in December and never below 45° at noon even in June**
(`RECOGNITION.md` §4). A midday frame here is flat and top-lit — the opposite of
Santiago's problem, where the danger was the sun being too low. The only raking
light available is late afternoon, which is also the only light that puts the sun
**behind** a camera west of the runway looking east at the base and on the
**starboard** side of a northbound RWY 02 departure. 15.1° is where the September
equinox lands at 17:00, and it happens to be the same elevation Santiago had to be
argued up to: below ~10° the whole field renders as silhouette.

Sun and sky are balanced **numerically**, not by eye, the same way Santiago's are:
a white lambertian card is rendered under the rig and the horizontal irradiance
split measured.

| rig | direct : diffuse | symptom |
|---|---|---|
| first attempt — sun 13.0, world 0.18, air 1.7 / aerosol 3.2 | **1.53 : 1**, sky B/R = 2.2 | **the red latosol rendered grey-green.** Too much blue diffuse for a red ground |
| shipped — sun 15.0, world 0.15, air **1.05** / aerosol **4.6** | **2.45 : 1** | the ground reads red |

The Rayleigh/Mie swap is the important half of that fix, not the exposure: the end
of the dry season in the cane belt is *smoky*, not blue, and a milky sky's bounce
does not fight the ground colour. It is also what the photographs show — every
free-licence frame of this field has a white or hazy-blue sky, never a deep one.

**Haze is a number with a stated visibility**, through the same `SDSC_Haze` node
group Santiago uses:

```
tau(d, z) = beta0 * d * (H/z) * (1 - exp(-z/H))          beta0 = 3.912 / V
```

Shipped: **V = 18 km**, **H = 1 100 m** — thinner than Santiago's 14 km, because
this is an open plateau at 807 m rather than a basin, but not clean, because
September is the burning season. Two SDSC-specific changes to the node group, both forced by this scene rather
than chosen:

- **`z` is lifted by 60 m before the layer integral**, because much of this scene
  is *below* the datum — the MRO platform is at z = −37 — and a negative height
  makes the integral blow up.
- **the height that enters the integral is the HIGHER end of the ray, not the
  shaded point.** Santiago never needed this because its shots are ground-level;
  the aerial tour here flies at 400–700 m, where the ray spends most of its length
  in thin air, and using the ground point over-hazes an aerial by about a third.
  The camera height is recovered inside the shader as
  `z_cam = z + Incoming.z · ViewDistance`.

| target | distance | haze fraction |
|---|---|---|
| Aeroclube, from THR 02 | 0.3 km | 6 % |
| mid-field cluster | 0.9 km | 17 % |
| MRO hangar line, abeam at rotation | 1.15 km | 22 % |
| the western rise | 2.5 km | 41 % |
| São Carlos city | 12 km | 92 % |

Those are ground-level sight lines and they are what V = 18 km was calibrated
against — the base at 1 km reads with the contrast `refs/sdsc_field_from_sp318_2013.jpg`
shows. **An aerial is a different matter**: from 400–700 m the slant range to the
far half of the field is 3–8 km, so `checks/tour_field_south.png` is heavily hazed
even after the ray-height correction. That is the model behaving, not failing. If
phase 3 wants a crisper tour, `HAZE_VIS_KM` is the one knob — raise it and say so.

**No snow, no rock, no elevation ramp.** Santiago's terrain shader needs one
because the Andes climb 5 km; the whole 240 km plate here is farmland, so the
terrain material is a cane-and-pasture cell patchwork and the only ramp is haze.

**The cane surround and the terrain mesh are two samplings of the same DEM, and
they used to fight.** `build_ground` drapes a cane sheet from the aerodrome pad
out to 9 km; the terrain tiers sample the same Copernicus grid at 30 m. Wherever
the sheet's coarse chord dipped under the fine surface the TERRAIN material won,
so the far field rendered as a mottle of two different farmland shaders — in
patches up to a kilometre across, with hard straight edges. Phase 3's aerial tour
is the first camera to look out at 4–7 km at a shallow angle and it is plainly
visible there. Measured over 30 000 random points inside the inner ring:

| step | offset | terrain wins | worst |
|---|---|---|---|
| 120 m | −0.55 | **39.3%** | −13.80 m |
| 60 m | −0.55 | 21.0% | −5.99 m |
| 40 m | −0.55 | 10.6% | −3.67 m |
| **60 m** | **+0.45** | **2.6%** | −4.99 m |
| 40 m | +0.25 | 0.9% | −2.87 m |

Shipped at **60 m and +0.45** — the sheet sits 1.25 m clear of the terrain,
which at 1–9 km is 0.02°, and the ring costs 38 000 faces the field can afford.
Keeping 120 m and raising the sheet until it always wins needs +14 m, which is a
cliff at the aerodrome-pad boundary. The outer ring goes 400 m → 200 m for the
same reason.

The **terrain tiers used to interleave the same way, and phase 4 closed it.**
Same bug, one level up, and the arithmetic is worth writing down because
"`mask_inner` drops the coarse faces inside the fine tier's box" sounds like it
tiles and does not.

`load_terrain.build()` dropped coarse faces whose **centre** fell inside the fine
tier's box. The two lattices are not aligned — the near grid's nodes are at
`−15000 + 30i`, the mid grid's at `−50000 + 60k`, and **no node is shared** — so
the mid tier's last kept face ended at x = −15 020 where the near tier starts at
−15 000, and on the other side its first kept face started at 14 980 where the
near tier ends at 15 000. **A 20 m gap on one side and a 20 m overlap on the
other**, in both axes. Measured over 40 000 random points in a 200 m band inside
that boundary:

| seam | coarse − fine | mean | p99 | max | min |
|---|---|---|---|---|---|
| 30 m / 60 m at 15 km | 200 m band | −0.00 | +1.73 | **+6.35** | −6.67 m |
| 60 m / 180 m at 50 km | 600 m band | −0.03 | +7.18 | **+30.82** | −34.97 m |

±6.7 m of z-fight along a boundary at 15 km is exactly "a shallow ray past 12 km
alternates between Near and Mid". The fix is the cane fix's shape: make the
overlap **deliberate** — shrink the mask by two coarse cells so the coarse tier
always underlaps and never gaps — and then **bias the coarse tier down** by more
than the measured worst case, ramped back to zero outside so there is no cliff.
**7 m over 1 500 m** at the 30/60 seam, **32 m over 6 000 m** at the 60/180 one.
The residual is a 7 m step at a 15 km seam, which is 0.02° from anywhere a camera
stands in this project, under a haze term over 90%.

Like the cane, the tiers carry one material, so this always cost **shading and
never colour** — which is why it survived three phases.

---

## 5. Licences — read before publishing anything built from here

| source | covers | obligation |
|---|---|---|
| **OpenStreetMap**, via Overpass | every footprint, taxiway and apron in `sdsc_osm.json` — and therefore most of the mesh in **`sdsc_field.blend`** | **ODbL 1.0**. Attribution *"Airport geometry © OpenStreetMap contributors, ODbL 1.0"* **and share-alike**: a derived database, which includes a mesh generated straight from it, must be published under ODbL. |
| **Copernicus DEM GLO-30** (primary), **SRTM v3** (control) | `terrain/*.npy`, `terrain/*.png`, and therefore `sdsc_terrain.blend` **and the graded ground under `sdsc_field.blend`** | Copernicus: free use with attribution to © DLR e.V. 2010-2014 / © Airbus Defence and Space GmbH 2014-2018, ESA-funded — full text in `TERRAIN.md` §7. SRTM: public domain (NASA/USGS). |
| **AISWEB / DECEA (ICA)** | the runway survey, declared distances, magnetic variation, threshold elevations, frequencies, hours | Brazilian State aeronautical information, quoted as fact. **Charts are NOT redistributed** — only the numbers and the URLs. |
| **ERA5 via Open-Meteo** | `sdsc_operations_wind.json` | ERA5: Copernicus C3S / ECMWF, free use with attribution. Open-Meteo data: **CC BY 4.0**. |
| **Wikimedia Commons photographs** | the appearance of the hangars, the apron, the interiors, the ground | CC BY-SA 3.0 / 4.0 and **GFDL 1.2** per `refs/manifest.json`. **Git-ignored** — share-alike conflicts with this repo's asset licence. MARCO AURÉLIO ESPARZ (8 of 13) and Renato Spilimbergo Carvalho (3) carry this survey and deserve named credit. |
| **LATAM / Aeroflap / CNN Brasil / Rede Voa / aeroin press** | figures about the base and hangar 9 | All rights reserved. **Read for numbers only; nothing downloaded, nothing usable as an asset.** |
| **LATAM brand** | the wordmark and brandmark on the hangar line and on hangar 9, and the full livery of the ten real masters now parked on the ramp (§9) | Trademark. Depiction of LATAM's own base; not a licence to reuse the marks. The lockup comes from `../latam_logo_indigo.svg` via `latam_livery_kit`, the same official outlines the fleet livery uses. |
| **ICAO Annex 14** | the marking pattern the runway follows, since SDSC has no ADC | ICAO ©. Used as a specification reference, quoted only in short fragments. |

---

## 6. Checking it — `python3 verify.py`

```
1. delivered grid vs full-resolution DEM horizon
   60 m grid alone          mean -0.011  rms 0.030  max|diff| 0.126 deg
   30 + 60 + 180 m stack    mean -0.004  rms 0.011  max|diff| 0.043 deg
2. horizon band
   terrain horizon      : -0.319 .. +1.304 deg  (band 1.624 deg)
   near field exceeds the terrain horizon at 24 of 72 azimuths
3. aerodrome elevation
   THR 02  published 804.7  Copernicus 806.0  SRTM 807.2   (spread 2.5 m)
   THR 20  published 794.6  Copernicus 794.0  SRTM 783.2   (spread 11.4 m)
   runway slope: published 10.1 m / 0.62%;  Copernicus 12.0 m / 0.74%
4. threshold geometry
   THR 02 -> THR 20 measures 1619.98 m vs 1620 m published        delta -0.02 m
   true 1.026 deg + VAR 22 W = 23.0 deg vs published 023 MAG      delta  0.0 deg
   OSM centreline 1710.6 m vs published 1720 m pavement           OSM 9.4 m short
```

`python3 refs_fetch.py --verificar` must exit 0: every manifest entry carries URL,
author and licence, and no photograph is tracked by or exposed to git.

### The visual gate — `render_checks.py`

```bash
blender -b --factory-startup scenario_sdsc/sdsc_field.blend \
    -P scenario_sdsc/render_checks.py -- plan mro
blender -b --factory-startup scenario_sdsc/sdsc_field.blend \
    -P scenario_sdsc/render_checks.py -- ground horizon tour ops fleet
```

Output lands in `scenario_sdsc/checks/`. Every check populates the ramp from
`fleet_placement.py` first (§9), because the aeroplanes are no longer in the
field file.

**`fleet` is phase 5's check** — `fleet_line`, `fleet_cowls`,
`fleet_engine_off`, `fleet_jacked`. It is where the claim in §9.4 is tested:
whether the heavy-check states survived the switch from proxies that were built
with them to masters that have none. All four stand at 55–95 m above the
platform on purpose; the first pass put the three close cameras on the ramp at
7–9 m and rendered three black frames, because the hangar line's west face is at
x = 931 and the free-standing 44 × 42 m hangar `way/708700156` sits in the middle
of the apron, so a station picked off a plan is inside a building more often than
not.

**`plan` is the check that matters.** It renders an orthographic top-down framed to
match `sdsc_osm_plan.png` exactly — x −500…1700, y −400…2300 — so the two go side by
side. It is what catches a build that is silently wrong: a mirrored base, a runway
laid on the designator instead of the true track, a footprint 200 m out. `mro` does
the same against `sdsc_osm_plan_mro.png`. What the pair shows today:

| feature | agreement |
|---|---|
| runway position, 1° tilt, length, both turn pads | matches |
| Aeroclube block and its link taxiway | matches |
| mid-field apron and its 35 m hangar | matches |
| MRO apron, the 471 × 137 m spine, the three hangars, the museum cluster | matches |
| the 1 163 m MRO taxiway diagonal | matches |
| the long farm sheds south-east of the field | matches |
| **hangar 9** | present in the build, absent from the plan — **correct**, it is 2025 and OSM was traced in 2017 |
| **roads, watercourses, landuse** | **now in both.** Phase 4: 287 ways / 158.5 km, 71 streams / 62 km, 8 water bodies, 35 landuse polygons. The line that used to read *"in the plan, not in the build"* is closed |
| **Água Vermelha** | in both — the mapped grid plus 300 declared-inference houses (§3) |
| **the staff car parks** | **the aisles match the plan** — they are OSM's own service ways. The cars are inference |
| the MRO ramp | now has an operation on it: 6 of 9 aeroplanes apart, 71 dock pieces, 75 GSE, 28 containers, a gate — and since phase 5 the aeroplanes are the **real masters**, ten of them, eight types (§9) |

**`ground` frames the departure clip's stations**, all of them looking RIGHT of a
RWY 02 roll because that is where the base is. Two of them are deliberate negative
checks:

- `ground_sp318_from_west.png` and `ground_sp318_midfield.png` stand on the **real
  ground** 620 m west of the centreline at eye height. **The MRO must NOT be visible
  in them** — the runway is a crest and the base is 35 m down behind it. If the MRO
  appears there, the platform level is wrong. It does not appear, and the mid-field
  cluster does, which is exactly the geometry that identified the 2013 photograph.

**`horizon` is the SDSC-specific one.** TERRAIN.md §3 says the whole 360° band spans
−0.32° to +1.30° and the near field beats the terrain at 24 of 72 azimuths, so there
are two opposite failures to look for: a horizon **too low and too clean**, meaning
the tree line is missing or too short, and a **skyline**, meaning something is
standing where nothing does. North is flat to the eye with the Aeroclube and the
mid-field cluster on the shoulders; west shows the one real feature, the low rise at
1–3 km, bleached by looking into a 15° sun through 20 km of smoky air.

`terrain/horizon_silhouette.png` remains the numerical horizon check, and the thing
to check about it is that it stays **empty**.

**`ops` is phase 4's check, and it is framed at the distances the tour flies.**
The aerial tour is 230–292 m above the plateau and 930–1 038 m from its aim, so
the MRO ramp goes past at 400–900 m slant. `check_ops` stands at exactly those
ranges:

| frame | what it is for |
|---|---|
| `ops_ramp_low.png` | the nose-in line from 240 m, 470 m out — the docks, the towers, the cowls, the loose engine, the GSE, the container blocks |
| `ops_carpark.png` | the landside from 260 m — the mapped aisle grids with cars in them |
| `ops_gate.png` | **eye level at the gate, 60 m out.** The one frame close enough to say whether the kit holds up at all, and the only frame in the project that looks at the perimeter wall from the landside |
| `ops_village.png` | Água Vermelha from 300 m, which is where the tour's south leg passes it |

Four things were only visible in these frames and each of them was a build
error, not a taste call:

- **a GSE row and a container row standing on the grass** west of the ramp.
  Both are now placed against the *mapped* apron polygon — `_on_concrete()` — and
  the containers walk its own edge rather than sitting at hand-picked spots.
- **black rectangles 200 m west of anything**: the car-park aisle test fired on
  pairs of 7 m kerb stubs at x = 470–583 and laid 22 m of asphalt over them. An
  aisle now has to be **25 m or longer at both ends of the parallel pair**.
- **yellow ironing boards.** The wing docks were built the length of a wing
  chord and stood *outboard* of the wing. 8 × 2.4 m at 0.24 span puts them under
  it, where a dock goes.
- **a 100 m single file of containers**, end-on, reading as a goods train. They
  are stacked in blocks now, long axis along the wall.

---

## 7. What phase 3 needs — the three clips

> **Phase 3 shot them.** This section is left exactly as phase 2 wrote it,
> because it is the brief the clips were built against and it is worth reading
> before §8, which is what they turned out to be. Where §8 disagrees with §7 it
> says so and gives the measurement.

Phase 2 built the field. Nothing is animated and no aircraft is placed: the three
clips are phase 3's.

### The departure

`SDSC_02_Threshold` is the anchor, +Y down the track. `../scenario/place_aircraft.py`
and `takeoff_camera.py` are the worked examples, with **three SDSC changes**:

1. **The threshold z is −2.33, not 0,** and the wheels ride a 0.62% downhill grade:
   `z = -2.33 - 0.006210·roll + 0.09 - pivot.z`. Over 1 672 m of TORA that is 10 m.
2. **TORA is 1 672 m, not 1 720**, and this is a **ferry flight** — no payload,
   minimum fuel. It must look like a very light aeroplane: early rotation, steep
   initial climb. A full transatlantic departure profile on this runway is wrong.
3. **The base is on the RIGHT and it comes abeam at 1 602–1 937 m** — at or just
   after rotation — at 797–1 287 m out. That is roughly twice Santiago's offset and
   the base is smaller, so it reads as a distant line of hangars, not a wall. The
   Aeroclube goes past on the **LEFT** in the first 500 m at 180–280 m, and the
   mid-field cluster on the **RIGHT** at 1 146 m and only 314 m out — that is the
   closest thing to the roll, and it is the one with the chequerboard tower and the
   floodlight masts in it.

Type: an **A320neo or A321neo** is the everyday choice and is already built here; a
**787-9** is the striking one and is the reason hangar 9 exists. **Not a 777-300ER**
— CNN Brasil states 777 maintenance is done at Guarulhos.

### The tow into a hangar

`SDSC_Hangar9` is the anchor, at (750, 1637.5, −37.10). Hangar 9's door is on its
**north** face, 78 × 20.5 m, centred (750, 1685), opening onto its own apron; the red space frame
and the pale floor are modelled behind it so a shot can look in. The tow path runs
south off the main apron and turns onto the door face. **Remember that everything on
the MRO platform is 35 m below the runway** — a camera at "runway eye height" over
there is 35 m in the air.

Note the honesty problem this clip carries: hangar 9's size and position are
inference (§3). A clip that makes it the hero should say so in its caption.

### The aerial tour

`render_checks.py tour` renders three sample frames. The things worth flying:
the fall from the runway crest into the córrego valley (40 m/km eastward, and it is
real terrain, not DEM error), the nose-in line along the hangar frontage, hangar 9
sitting apart from the 2017 buildings, the cane blocks running right up to the fence,
and the fact that there is **no horizon anywhere** — this is a field on a plate.

Camera comfort is measured, not judged: `../scenario/camera_metrics.py` applies here
unchanged. Below ~0.5 frame-widths/s reads as calm, above ~1.0 disorients.

One thing to decide before flying it: at 400–700 m the slant range across the field
is 3–8 km and the shipped haze (V = 18 km, calibrated on ground-level frames) makes
the far half soft. Either fly lower and closer, or raise `HAZE_VIS_KM` and record
that the tour was shot on a clearer day than the departure.

### Still open after phase 2

- **Hangar 9's real size and position.** Nothing found. It is declared inference.
- **The base's LATAM appearance.** Decided (§3), not confirmed. One constant flips it.
- **The identity of the chequerboard tower.** Still unresolved; phase 2 triangulated
  it to about (300, 1255) ±80 m from the 2013 frame, which matches neither OSM node.
- **Whether `relation/7422965` is the hangar line, the workshop spine, or both.**
  Phase 2 answers it as far as geometry can — the polygon that stands on the apron is
  `relation/7422966`, so the spine behind it is built as workshops — but no source
  says so.
- **Which OSM polygon is which of LATAM's nine hangars.** Not forced. Four
  hangar-tagged polygons on the site plus hangar 9 is five; the counts do not
  reconcile and should not be made to.
- **Stand numbering, taxiway designators, marking geometry.** No ADC exists.
- **A 767 or A330 entering a 13 m hangar.** The DSM floor and the door heights a
  widebody needs are in tension; the build resolves it with raised portal bays, and
  that resolution is inference.

---

### Which LATAM types can operate from this runway

Full evidence in `sdsc_aip_survey.json` → `which_latam_types_can_operate_here`.
The field is **short, hot and high at once**: TORA **1 672 m** (02) / 1 668 m (20),
elevation 2 648 ft, and a 30 °C afternoon is ISA+20 — a density altitude near 5 000 ft.

| type | operates here? | evidence |
|---|---|---|
| **A319 / A320 / A321, ceo and neo** | **yes, routine** | the base's core workload; hangar 9 alone takes three A320s at once |
| **767-300ER / 767-300F** | **yes, routine** | listed by LATAM among the types maintained here; a TAM widebody is parked on the mid-field apron in the 2013 reference photograph |
| **787-8 / 787-9** | **yes** | hangar 9 exists specifically for 787 heavy maintenance; first major 787-9 overhaul there Feb 2026 |
| **A330-200** | yes — the largest type before 2020 | reported as such |
| **A350-900** | yes, demonstrated but exceptional | PR-XTK, 14 Oct 2020, 11:51, from Confins; the shortest runway an A350 had used in Brazil; came for maintenance and pandemic storage |
| **777-300ER** | **no** | CNN Brasil states 777 maintenance is done at **Guarulhos**, not here. The one type with evidence *against*. |
| **E195-E2** | expected H2 2026 | reported as the reason for further expansion |

**For the departure clip:** an **A320neo or A321neo on RWY 02** is the safe, everyday
choice and is already built in this repository. A **787-9 on RWY 02** is the striking
one — it is why hangar 9 was built, it is true to 2026, and a Dreamliner rotating off
1 672 m is the whole story of this base in a single shot. Either way, **it is a ferry
flight**: no payload, minimum fuel. It must look like a very light aeroplane — early
rotation, steep initial climb — not a full transatlantic departure. **Do not put a
777-300ER on this runway.**

---

## 8. The three clips, as shot

> **Phase 5 re-shot all three again, and `_v3` is what the clips are now.**
> What changed is on the ramp: the nine airliners on the MRO stands and the
> widebody on the mid-field apron were low-poly proxies and are now ten of the
> eleven real masters, placed by `fleet_placement.py`. **§9 is the whole
> reckoning** — the type mapping, which heavy-check states survived the switch
> and which one had to be authored, why it links rather than appends, and what
> it costs per frame.
>
> Phase 4 had re-shot them for a different reason: the surround was built and
> the ramp got an operation on it (§3), so `_v1` became history and `_v2` was
> the clip. Nothing about the camera work has changed in either round — the
> paths, the lenses, the frame counts and the reasoning below are still
> phase 3's, re-rendered against a changing world. The measured metrics at the
> end of each clip's block are **re-measured every round**; §9.7 is phase 5's,
> beside phase 4's, because detailed models at the stands change what the
> nearest in-frame object is and that is exactly the class of defect that bit
> Santiago. (It did not recur: the near field is the same three objects at the
> same three distances.)

Three GIFs, all **25 fps exactly** — a GIF delay is an integer number of
centiseconds, so 25 fps is 4 cs every frame while 24 fps alternates 4 and 5 and
reads as stutter. Two are 800 px wide; the aerial tour is 720, because it is the
one clip in which every pixel changes every frame and 800 px will not fit the
~15 MB budget at any palette size.

```bash
python3 scenario_sdsc/verify_gifs.py scenario_sdsc/*.gif   # must exit 0
``` Every one is verified after encoding with a real
parser (`PIL.ImageSequence`), never with a byte scan for `0x21F904`: that
pattern occurs by chance inside LZW data and has reported a phantom 311-second
delay in this repository before. `verify_gifs.py` is that gate and it exits
non-zero on any frame whose delay is not 40 ms.

| clip | file | frames | subject | GIF | v2 | v1 |
|---|---|---|---|---|---|---|
| 1. departure | `a320_sdsc_v4.gif` | 240 (9.6 s) | **A320neo**, RWY 02, ferry | 12.31 MB / 800 px / 128 (v3: 13.06) | 12.96 / 800 / 128 | 14.09 / 800 / 128 |
| 2. the tow | `b789_hangar9_v3.gif` | 400 (16.0 s) | **787-9** into hangar 9 | 14.81 MB / **680 px** / 80 | 13.91 / 680 / 80 | 14.70 / 720 / 96 |
| 3. aerial tour | `sdsc_base_v3.gif` | 240 (9.6 s) | the whole base | 13.08 MB / **680 px** / 80 | 13.18 / 680 / 80 | 14.10 / 720 / 88 |

The v3 encodes use exactly the knobs v2 settled on; the busier ramp cost 0.1 MB
on the departure, 0.9 on the tow and 0.1 MB *less* on the tour, and all three
are inside the budget. The departure's **v4** (2026-08-27) re-renders the same
shot after the geometry-truth round — ACAP gear lengths, the drawn aft keel,
the capped nose — from a decolagem blend re-synced to the master (mesh
datablocks + hinge-space wheel deltas; the rig's own report seats wheel_agl at
0.000 through the roll and lifts off at frame 69). Same knobs, 12.31 MB; the
rotation at ~f68 now shows the tail clearing with the measured 12.6-degree
margin instead of the old 7.75. The
ladders, measured on these frames:

| clip | ladder |
|---|---|
| the tow | 680/80 = **14.81 MB**, 680/72 = 13.98, 660/80 = 13.65 |
| the tour | 680/80 = **13.08 MB**, 680/72 = 12.58, 660/80 = 12.41 |

Each script carries its full reasoning — what was tried, what was rejected and
the measurement that forced it — in its module docstring. That is the primary
documentation; this is the index.

### Why two different aeroplanes

The **787-9 gets the hangar**, because hangar 9 exists for 787 heavy maintenance
and phase 2 sized its 78 × 20.5 m door from a 787-9's 60.1 m span and 17 m fin.
Putting anything else through it would throw away the only reason the building
is in the model.

The **A320neo gets the departure**, for three reasons and one of them is
prudence: it is the base's core workload, it is the type this repository already
has a take-off rig for (`airbus A320neo/A320neo_decolagem.blend`, with the
tailstrike angle and the gear sequence already checked), and using the 787 for
both clips would have made the departure a repeat of the tow. Between them the
two clips say what the base is: widebodies come in for their checks, narrowbodies
go out after theirs.

**No 777-300ER anywhere.** CNN Brasil states 777 maintenance is done at
Guarulhos; it is the one type with positive evidence against
(`RECOGNITION.md` §5.6).

### The anchor this field offers

Santiago pins the Andes crest at a constant fraction of frame height and lets
everything move against it. Here the whole 360° terrain horizon spans **−0.35°
to +1.33°**, and across the NNE→ENE sector the departure looks through it
averages **−0.10°** and never leaves ±0.31° (`terrain/horizon_fine_0p1deg.csv`).

So the anchor is not a shape, it is a **level**. The horizon here is a
ruler-straight edge, which is a *stronger* thing to pin than a mountain,
because tilt and roll error show against a straight line instantly. All three
clips drive their tilt off it: the departure holds it at v 0.62 → 0.76, the
tour at v 0.81 → 0.84. The tow is the exception and it has a different anchor —
the 78 × 20.5 m door, held from u 0.45…0.77 at the start to u 0.28…0.80 at the
close.

### Clip 1 — the departure

```bash
blender -b "airbus A320neo/A320neo_decolagem.blend" \
    -P scenario_sdsc/place_aircraft.py -- --out scenario_sdsc/sdsc_takeoff.blend
blender -b scenario_sdsc/sdsc_takeoff.blend \
    -P scenario_sdsc/takeoff_camera.py -- --out scenario_sdsc/sdsc_takeoff_v1.blend
blender -b scenario_sdsc/sdsc_takeoff_v1.blend -P scenario/camera_metrics.py
blender -b scenario_sdsc/sdsc_takeoff_v1.blend -P scenario_sdsc/render_clip.py \
    -- --out /tmp/frames_sdsc_dep/
ffmpeg -y -framerate 25 -start_number 1 -i /tmp/frames_sdsc_dep/%04d.png \
  -vf "scale=800:-1:flags=lanczos,split[a][b];\
[a]palettegen=max_colors=128:stats_mode=diff[p];\
[b][p]paletteuse=dither=none:diff_mode=rectangle" \
  -loop 0 scenario_sdsc/a320_sdsc_v1.gif
```

`python3 scenario_sdsc/takeoff_camera.py` solves the same shot **offline in a
second** and prints every number below except the ray-cast ones. Use it to tune;
use `camera_metrics.py` to believe.

One orbit flown in the aeroplane's own coordinates from frame 1 to frame 240 —
no dolly, no hand-over, because Santiago's five rebuilds showed the stiffness
lived in the seam between coordinate frames. Camera on the port quarter,
psi 122° → 111°, 112 → 176 m out, 95 → 162 m west of the centreline, lens
50 → 42 mm, plus about a metre of slow sinusoidal sway because formation flight
is not a rail.

**Three things this runway imposed, all of them measured:**

- **The wheels ride downhill.** THR 02 is at z = −2.33 and the runway falls
  0.62%, so `place_aircraft.py` bakes the grade into the pivot's own z channel
  rather than into the parent Empty — one transform cannot express a slope. The
  wheels sit within 0.000 m of the pavement for every frame of the roll, and the
  offset is smoothstepped to a stop across lift-off so the 0.36 m/s of sink the
  grade is worth does not appear as a velocity step at rotation.
- **It is a ferry flight.** Lift-off at **1 150 m of a 1 672 m TORA** — 522 m,
  31%, still ahead of it — and the climb-out is extended at 16.0 m/s against
  76 m/s, a 21% gradient, holding 15.5° of pitch. A revenue departure profile on
  this runway would be wrong.
- **The camera cannot fly where it wants.** The RWY 20 PAPI stands at lateral
  +20…+68 m west at along ~1 320 m, exactly where a tight chase would be at
  exactly the frame it would be at eye height. This one stays 130 m clear at its
  closest. The other constraint is flow: a low broadside at 7 m measures 1.36
  frame-widths/s in the central band, which is parallax and no pan change
  touches it.

**The reveal is terrain, not camera work.** The MRO platform is 35 m below the
runway and the runway is a crest, so from the camera's opening position the
sight line to the MRO apron clears the ground by **−5.5 m** — it does not clear
it. The base is behind the hill; only the tallest roofs show. `mro_clr` in the
printed report goes positive at **frame 78**, nine frames after the wheels
leave, and reaches **+10.9 m** at the close, and by then the apron, the nose-in
line and hangar 9 are all open. This is phase 2's negative check
`checks/ground_sp318_from_west.png` seen from the other side.

Measured in the scene by `../scenario/camera_metrics.py`:

| | |
|---|---|
| screen flow, central band | median **0.050**, p90 0.069, max 0.073 w/s |
| frames above 0.5 / 1.0 w/s | **0 of 239** / 0 of 239 |
| screen flow, whole frame | median 0.076, p90 0.166, max 0.175 w/s |
| nearest scenery in frame | **67 m, `SDSC_AerodromeGround`** — grass, not a tree |
| worst foreground parallax | 47°/s (Santiago's tree-line disaster was 582°/s) |
| aeroplane edge margin | 24.87% |
| aeroplane in frame | 40.4% → 24.4% of frame width, v 0.35 → 0.46 |
| camera speed | 47 → 79 m/s |

The body max/min flow ratio is 8.7 against the skill's "keep it under ~5:1".
It is not a hitch: the range is 0.008 → 0.073 w/s, a monotonic ramp from a
camera locked to the aeroplane during the roll to one craning at the close. A
ratio between two numbers an order of magnitude below the comfort threshold is
not a speed change the eye can see.

### Clip 2 — the tow into hangar 9

```bash
blender -b --factory-startup scenario_sdsc/sdsc_field.blend \
    -P scenario_sdsc/hangar_tow.py -- --out scenario_sdsc/sdsc_hangar_tow.blend
blender -b scenario_sdsc/sdsc_hangar_tow.blend -P scenario/camera_metrics.py \
    -- --pivot B789_Tow
blender -b scenario_sdsc/sdsc_hangar_tow.blend -P scenario_sdsc/render_clip.py \
    -- --out /tmp/frames_sdsc_tow/
```

then the same `ffmpeg` line at **720 px / 96 colours**. This clip is 400
frames against the others' 240, so it pays 67% more before a single palette
decision is made; 800 px does not fit at any palette size. Measured on these
frames: 800/128 = 20.08 MB, 800/96 = 17.75, 800/80 = 15.20, 700/96 = 14.25,
**720/96 = 14.70**, 720/80 = 12.63. 720/96 keeps the colour depth the dark
hangar interior needs and still lands inside the budget.

**This clip opens `sdsc_field.blend` directly instead of linking it**, and that
is deliberate: it has to rebuild hangar 9's north wall, and it has to leave
hangar 9's stand empty because the towed aeroplane goes there. Since phase 5 the
second half is one argument — `F.populate(scn, skip=("H9",))` — rather than a
proxy deletion. Re-running the script is the propagation; the shared asset is
never edited.

**The towed 787-9 is still APPENDED, not instanced**, and it is the one place a
clip departs from `fleet_placement.py`: the tow re-parents `TremNariz*` to a
steering empty so the nose gear tracks the towbar, and you cannot re-parent
inside a collection instance. One aircraft's worth of unique geometry, for the
one aircraft the clip is about.

**What the shared scenery does not have, built locally in this file.**
At the 0.8–1.9 km the field file is designed for, hangar 9's door is correctly a
dark rectangle *painted on a solid wall* — `build_scenery.py` makes it as a
1.6 m thick box of `SDSC_HangarInterior`. An aeroplane cannot be towed through
that. So `hangar_tow.py` cuts a real 78 × 20.5 m opening, stacks the door leaves
in jamb pockets either side, widens the floor from door-width to the full
128 × 93 m bay, and hangs six high-bay light lines under phase 2's red space
frame. **The lamps are load-bearing, not decoration:** the door faces north and
the shipped sun is at azimuth 274.46°, so no direct sunlight enters it at any
hour of the shipped rig — without them the interior is a black slot and nothing
phase 2 built behind that door can be seen at all.

It also moves the fascia band and the LATAM lockup off the opening and onto the
two wall panels flanking it, for the same reason: a band drawn across a hole
hangs in mid-air.

**A defect this clip found in the shared build.** Hangar 9's wordmark was
rendering **mirrored**. `place_wordmark()` lays the lockup out along world
+X × `facing`, and a wall whose outward normal is north needs `facing = −1`
because an observer north of it sees +X on their left; the build passed +1. The
west-facing run on the hangar line has the opposite handedness and was right all
along, which is why the two disagreed and nobody noticed — no camera had ever
been close enough to read it. Fixed in `build_scenery.py`; **`sdsc_field.blend`
was rebuilt** and the fix is in the shared asset, not in the clip.

**The tow is a tractrix, and it is solved backwards.** What separates a tow from
an aeroplane sliding along a spline is that the aeroplane does not follow the
nose gear's path: the main gear cuts the corner and the tail swings the other
way. The first attempt drove that forward — a "turn then straight" nose-gear
path with the aeroplane trailing on a 25.83 m link — and it is **wrong**, for a
reason worth writing down: a trailer needs three or four wheelbases to settle,
and after the 19 m of straight this hangar allows, the fuselage was still 9.3°
off square with one wingtip at 4.0 m of clearance against the other's 14.7.

So the **aeroplane's heading** is the control curve, its main gear integrates
along it, and the nose gear is derived at `N = M + W·(sin h, cos h)`. The tug
then follows N. That guarantees square at the door and produces the nose-wheel
steering for free — it is `atan(W·dh/ds)`, so the wheels swing out to start the
turn and return to centre to stop it. The eight `TremNariz_*` parts are
re-parented to an empty on the strut axis so they can actually turn.

| | |
|---|---|
| path | 42 m, heading 197° → **180.0°** (hangar 9 is axis-aligned, not on the runway track) |
| speed | 3.4 m/s (12 km/h) on the apron → 1.0 m/s (3.6 km/h) at the threshold |
| off-tracking | main gear **3.65 m** inside the nose-gear line, tail **5.01 m** outside it |
| nose-wheel steer | 0 → **−18.84°** → 0 |
| square to the door | from frame 304 of 400 |
| tug across the door plane | frame 85 (21%) |
| nose across the door plane | frame 115 (29%) |
| wingtips at frame 400 | x 719.9 and 780.1 in an opening x 711…789 — **8.94 m each side** |
| fin | 17.02 m in a 20.5 m door, **3.48 m under the lintel** (re-measured 2026-08-27 on the geometry-truth legs: `WHEEL_Z` −4.88 → −5.42, the fin now rides at the published height) |

**Why this clip is 400 frames when the others are 240.** A 787 does not enter a
hangar in 9.6 seconds. At a real tow speed the aeroplane covers 42 m in 16 s,
and speeding it up is the one lie this shot cannot afford. What 42 m does not
buy is the fin passing under the lintel: the fin is 55 m behind the nose, which
is 22 more seconds of tow, and no framing recovers it. It is given as a number
instead — the row above.

**Slow shots fail differently.** The risk is not disorientation, it is stepping:
a gentle move shows every quantisation in the curves. So the camera path is
PCHIP rather than a chain of smoothsteps (zero derivative at every knot would
read as the camera stopping six times), every f-curve is baked per frame and set
LINEAR, and the report prints the *minimum* screen flow as well as the maximum.
The camera is one continuous push, 58 m in 16 s, 30 m down to 17 m above the
platform — **above the platform, which is 35 m below the runway; "runway eye
height" over here is 35 m in the air.**

Measured in the scene by `camera_metrics.py --pivot B789_Tow`:

| | |
|---|---|
| screen flow, central band | median **0.011**, p90 0.017, max 0.017 w/s |
| frames above 0.5 / 1.0 w/s | **0 of 399** / 0 of 399 |
| worst single probe in frame | 0.036 w/s |
| body max/min ratio | 2.0 |
| nearest scenery in frame | **59 m, `SDSC_FloodlightMasts`** — hangar 9's own apron mast |
| worst foreground parallax | 3.9°/s |
| aeroplane edge margin | 12.52% |
| camera speed | 3 → 4 m/s |

That mast is the one piece of thin geometry close enough to matter. It measures
12.1 px of shaft and steps **1.9 px per frame** at 3 m/s, so the coupling that
made Santiago's light masts strobe — thin geometry stepping 68 px behind a 10 px
shutter — cannot arise. It sits at u 0.93, clear of the doorway.

### Clip 3 — the aerial tour

```bash
blender -b --factory-startup scenario_sdsc/sdsc_field.blend \
    -P scenario_sdsc/base_flyover.py -- --out scenario_sdsc/sdsc_base_flyover.blend
blender -b scenario_sdsc/sdsc_base_flyover.blend -P scenario/camera_metrics.py \
    -- --pivot none
blender -b scenario_sdsc/sdsc_base_flyover.blend -P scenario_sdsc/render_clip.py \
    -- --out /tmp/frames_sdsc_tour/
```

then the same `ffmpeg` line — but at **720 px, not 800, and 88 colours**. This
is the clip in which every pixel changes every frame, so it quantises worst:
800 px lands at 17–20 MB whatever the palette. Santiago's flyover shipped at
720 px / 72 for exactly the same reason. The ladder, measured on these frames:

| width | colours | size |
|---|---|---|
| 800 | 128 | 20 MB |
| 800 | 72 | 17 MB |
| 760 | 80 | 14.96 MB |
| **720** | **88** | **14.10 MB** |
| 720 | 80 | 13.50 MB |
| 660 | 88 | 12.46 MB |

Santiago's flyover works for three reasons and all three transfer: **one
continuous move at constant rate** (a straight line, linear in every control
value), **a travelling aim** on a different line from the camera's, and **the
sun never in front of the lens**. Here the sun is 177° off the lens axis at
frame 1 and 163° at frame 240.

The aim runs Aeroclube → mid-field cluster → hangar 9 → hangar line, and those
are very nearly collinear on this field: the straight line from (−212, 456) to
(900, 1800) passes within 30 m of the mid-field apron. One lerp gives the whole
tour. The camera line **converges** on it by about 6°; a parallel line was tried
first and is the trap — it holds the bearing exactly constant, which sounds
ideal and makes the entire world slide sideways at 0.34 w/s with nothing growing
and nothing arriving.

**Phase 2's haze question, answered by not touching the knob.** §4b warns that
at 400–700 m the slant range across this field is 3–8 km and offers
`HAZE_VIS_KM`. This clip flies **lower and closer instead**: 230 → 292 m above
the plateau at 209 m/s, 930 → 1 038 m from the aim, so the haze term stays at
16% and the shared calibration is left alone. The cost is that the whole field
is never in one frame; that is what the travelling aim is for.

What is in frame, and for how long, of 240:

| | | | |
|---|---|---|---|
| Aeroclube | 1…32 | hangar 9 | 90…240 |
| runway, mid-point | 1…93 | MRO hangar bay | 127…240 |
| mid-field apron | 1…156 | hangar-line north end | 181…240 |
| chequerboard tower | 10…167 | Museu TAM block | 46…240 |

**This is also the shot that caught the cane/terrain fight.** It is the first
camera on the field to look OUT at 4–7 km at a shallow angle — every check frame
before it is either ground-level, where haze closes at 2 km, or steeply down —
and it rendered the far field as a mottle of two farmland shaders with hard
straight edges. Diagnosis, the measurement and the fix are in §4b. The general
lesson is worth keeping: **a new camera angle is a test the scenery has never
taken.**

Phase 3 shipped this clip with three of the nose-in proxies hand-swapped for
real masters, in `base_flyover.py` itself, and that tuple is what the owner's
complaint eventually landed on: everything outside those three entries was still
a proxy. **Phase 5 took the whole business out of this script.** The ramp is now
ten real masters of eight types, from `fleet_placement.py`, and this file's
entire contribution is `F.populate(scn)`. §9 is the reckoning. The apron here is
at z = −37.05 and the wheels are seated on it to 0.000 m, measured.

Measured in the scene by `camera_metrics.py --pivot none`:

| | |
|---|---|
| screen flow, central band | median **0.053**, p90 0.058, max 0.061 w/s |
| frames above 0.5 / 1.0 w/s | **0 of 239** / 0 of 239 |
| screen flow, whole frame | median 0.079, p90 0.081, max 0.082 w/s |
| worst single probe in frame | 0.384 w/s |
| body max/min ratio | **1.3** — the constant rate, measured |
| nearest scenery in frame | 571 m, `SDSC_AerodromeGround` |
| worst foreground parallax | 20.9°/s |
| camera speed | 209 m/s, constant |

A body ratio of 1.3 across 240 frames is what "one continuous move at constant
rate" looks like when it is measured rather than asserted. The whole-frame and
central-band numbers barely differ, which is the other signature: at 230 m there
is nothing near enough to streak at the bottom edge.

### Still open after phase 3

- **The fin has never been through the door.** Clip 2 stops with the wingspan in
  the opening; the 3.48 m of lintel clearance (on the 2026-08-27 legs) is
  arithmetic, not a frame.
- **The shared `sdsc_field.blend` still has a painted-on door.** Only
  `sdsc_hangar_tow.blend` has a real opening. If another clip ever needs to look
  into hangar 9, the opening should move into `build_scenery.py` — it is about
  forty lines and it would cost the field file nothing.
- **The tug is inference.** A towbar tractor of plausible size in plausible
  colours; no photograph of LATAM's São Carlos ground equipment was found.
- **The interior lighting is inference too.** Six high-bay lines at 17.6 m,
  tuned by render to about 2 W/m² on the floor, i.e. an interior clearly dimmer
  than the sunlit apron. No source says what hangar 9 is lit with.
- **The runway leaves the tour early** (frame 93). A camera that keeps both the
  1 720 m of pavement and the base would have to be much further out, and the
  haze answer above rules that out.
- ~~**The terrain tiers still interleave with each other.**~~ **Closed in phase
  4.** The mask was dropping coarse faces by their centre, and the lattices are
  not aligned, so it left a 20 m gap on one side and a 20 m overlap on the other
  — worth ±6.7 m of z at the 30/60 seam and ±35 m at the 60/180 one. Measured,
  then fixed the cane fix's way: a deliberate underlap plus a ramped 7 m / 32 m
  bias. §4b has the numbers.

---

## 9. Phase 5 — the real aeroplanes on the ramp

> The owner watched `b789_hangar9_v2.gif` and said the towed 787-9 is the real
> master but there is an undetailed aeroplane standing behind it. He was right,
> and the reason is worth naming: phase 4 parked **fifteen low-poly proxies** on
> this field and `base_flyover.py` then hand-swapped **three** of them — in its
> own file, as a tuple — for the models this repository had built. Everything
> outside those three entries was still a proxy, in every clip.
>
> Phase 5 replaced the three-entry special case with **one module**,
> [`fleet_placement.py`](fleet_placement.py), and gave every airliner stand on
> the field a real master.

### 9.1 What the module is

One table, four callers. The table says which of the eleven masters stands where;
the stand's **position, heading and state** stay in `build_scenery.MRO_STANDS`
and `OUTFIELD_STANDS`, which is also what the maintenance kit and the GSE are
laid out from, so there is exactly one set of coordinates in the repository.

```python
import fleet_placement as F
F.populate(scn)                     # takeoff_camera.py, base_flyover.py
F.populate(scn, skip=("H9",))       # hangar_tow.py — its 787 is being towed on
```

`render_checks.py` calls it too, and has to: the ramp aeroplanes are no longer
part of `sdsc_field.blend`, so a check frame rendered off the bare field would
show an empty apron and would have stopped being a check of what the clips see.

`build_scenery.py` reads the same table the other way round. `airliner_proxy()`
is **kept and still wired up** — a stand whose `FLEET` entry is `None` gets its
proxy back, and `proxy_stands()` reports which. Nothing uses it today; the
escape hatch is real, and §9.5 is the measurement that would justify pulling it.

### 9.2 Instance, do not duplicate — and why linking, not appending

A master at render subdivision is **307 000 – 356 000 triangles**, measured on
all eleven. Fifteen unique copies would be ~5 M and the tow clip is 400 frames.

Santiago's `../scenario/base_flyover.py` **appends** each master and duplicates
hierarchies with `ob.copy()`, which shares the mesh datablock. That is not an
instance as far as Cycles is concerned: **Cycles keys geometry on the OBJECT
whenever the object carries modifiers**, and every master mesh here has
SUBSURF / MIRROR / BEVEL, so two objects sharing one modified mesh still export
as two geometries. Appending also copies every mesh into the shot file, and the
three clip `.blend`s are committed.

So this module **links** the four sub-collections and puts an
`instance_type='COLLECTION'` empty at each stand. The depsgraph then hands
Cycles the *same evaluated object* with N matrices — one geometry, N instances —
and the file gains a library reference instead of mesh data:

| file | v2 (appended / proxies) | v3 (linked instances) |
|---|---|---|
| `sdsc_field.blend` | 3.30 MB | 3.37 MB |
| `sdsc_takeoff_v1.blend` | 3.22 MB | 3.55 MB |
| `sdsc_hangar_tow.blend` | 4.09 MB | 4.42 MB |
| `sdsc_base_flyover.blend` | 4.91 MB | **3.69 MB** |

The tour file got *smaller*: its three appended masters became three links.

**Linking the master's TOP collection is what does not work**, and Santiago's
docstring says why — the parts hang from parent empties that live outside the
sub-collections, so an instance disassembles into a fin on the apron. Linking
the four sub-collections is fine, and it was verified rather than assumed:
**every object in `01_Estrutura` / `02_Motores` / `03_Trem` / `04_Detalhes`, in
all eleven masters, is a world-coordinate root with no parent.**

The one deliberate exception is the towed 787-9 in `hangar_tow.py`, which is
still appended: the tow re-parents `TremNariz*` to a steering empty so the nose
gear tracks the towbar, and you cannot re-parent inside a collection instance.
One aircraft's worth of unique geometry, for the one aircraft the clip is about.

### 9.3 The type mapping, and the evidence for each

Ten stands, eight of the eleven masters. Everything below comes from the table
in §7 and `sdsc_aip_survey.json`.

| stand | state | type | why |
|---|---|---|---|
| `ROW0` | parked | **767-300ER** | the widebody LATAM lists among the types maintained here |
| `ROW1` | parked | **A320neo** | the everyday type, and the one the departure clip flies |
| `H9` | parked | **787-9** | hangar 9 exists for 787 heavy maintenance |
| `N0` | jacked | **767-300F**, LATAM Cargo | the freighter is an evidenced variant, and it puts the cargo livery on a ramp that would otherwise be all passenger white |
| `N1` | docked | **A321neo** | |
| `N2` | engine_off | **A320ceo** | |
| `N3` | cowls | **A320neo** | shares `ROW1`'s linked geometry |
| `N4` | cowls | **A319** | the shortest of the family — length is what reads at 300 m |
| `N5` | docked | **A321ceo** | |
| `MID` | parked | **767-300ER** | the mid-field apron, 26 m below the runway crest, where the 2013 reference photograph has a TAM widebody. Shares `ROW0`'s geometry |

Six of the ten are A320-family, ceo and neo, in three different lengths. That is
not decoration: *"the A320 family is the base's core workload; hangar 9 alone
takes three A320s at once."*

**Two gaps are declared, not papered over.**

* **No A330.** The A330-200 is recorded as the largest type here before 2020 and
  there is no A330 master in this repository. The "wide" stands are 767s, which
  is the type with *current* evidence.
* **No light aircraft.** The five Aeroclube GA aeroplanes stay `ga_proxy()` and
  are now **the only proxies on this field** — 180–280 m off a RWY 02 roll,
  which is close enough to be worth saying out loud.

**No 777-300ER anywhere**, and it is not in the module's `TYPES` table at all.
CNN Brasil states 777 maintenance is done at Guarulhos; it is the one type with
positive evidence *against*.

### 9.4 The states — this is a heavy-check base, not a terminal apron

`MRO_STANDS` deliberately shows aircraft **apart**. That is what distinguishes an
MRO from a gate row, the proxies were built with the states, and the masters have
none. What each one could honestly become:

| state | on a real master | verdict |
|---|---|---|
| `parked` | all four collections | trivial |
| `docked` | all four collections | **survives unchanged.** `docked` was never an airframe state — the nose dock, tail dock, wing docks and towers that make it read are `build_maintenance`'s kit and they are already standing round the stand |
| `jacked` | all four, lifted `JACK_LIFT` = 0.55 m | **survives.** Gear stays DOWN and the tyres hang clear of the concrete over the jacks, which is a jacking for a weighing or a strut change. Gear *retracted* on jacks would be a gear swing, and that is not what the kit under it shows |
| `engine_off` | **`02_Motores` is a separate collection, and that is the opening.** This stand does not instance it: it appends a local copy, bakes it at render subdivision, and deletes every face on the **port** side except the pylon's | **survives exactly.** One engine, one bare pylon — the proxy's own semantics — and `build_maintenance` already has the removed engine on its cradle and the dolly beside the wing. Port is local −Y: the nose is local −X and up is +Z, so left = up × forward |
| `cowls` | **the one state the masters cannot hold** | see below |

**`cowls` could not be taken off the shelf, and it is not silently dropped.**
There is no fan-cowl door in any master's geometry to hinge — `Motor_Nacelle`
(Airbus, mirrored) and `Nacelle_E` / `Nacelle_D` (Boeing) are single lofted,
subsurfed skins. Hiding the skin was tried on paper and rejected: it gives
"engine stripped to the core", a real state but a *different* one, and at 300 m
it reads as a thinner engine rather than an opened one.

So **the doors are authored by the module** and that has to be said plainly: two
panels per engine, hinged on the nacelle crown at 55°, are new geometry that is
not part of any master. What is *not* invented is their size and position — the
nacelle's crown line, centre, radius and length are **measured off the evaluated
master** and the panels are built in the master's own local frame, so they sit on
the real nacelle and scale with the type. It is the same construction
`airliner_proxy(engines="open")` uses, moved onto a real aeroplane, and the state
it reproduces is photographed on this site: `refs/mro_centro_tecnologico_2010.jpg`,
an A320 with the fan cowls open and the core exposed.

`checks/fleet_cowls.png` is the frame that says whether the doors sit on the
nacelle or float beside it. Look at it before believing this paragraph.

### 9.5 What it costs, measured

Whole-scene triangles, and the marginal cost of one frame at 960 × 540 on the
M3 Max — *marginal*, not the first frame, because a 240-frame job pays the sync
and BVH build once. Measured as `(t(6 frames) − t(1 frame)) / 5` on the same
frame range before and after.

| clip | triangles v2 → v3 | s/frame v2 → v3 | v3 whole clip, wall clock |
|---|---|---|---|
| departure, f118–123 | 7.86 M → 9.69 M | 2.22 → 20.77 | 240 frames in **54.5 min** (13.6 s/frame) |
| the tow, f200–205 | 7.84 M → 9.50 M | 7.52 → 19.40 | 400 frames in 175 min (26.2 s/frame) |
| the tour, f200–205 | 8.22 M → 9.50 M | 5.09 → 13.48 | 240 frames in 101 min (25.3 s/frame) |

**The wall-clock column is not a clean measurement and is here for planning
only.** The machine was shared while these ran — another GPU application, and
then a memory wall: 82 MB free, 42 GB in the compressor, Blender paged down from
8.4 GB resident to 1.1 and taking five minutes a frame. The departure ran
essentially unimpeded and is the honest one. The tow's second half was re-run
through a **chunked, resumable driver** — 30 frames per Blender process,
skipping whatever is already on disk — which is worth keeping whatever the
machine is doing: it turns a lost long run into a lost chunk. The middle column,
measured as `(t(6 frames) − t(1 frame)) / 5` on the same frame range before and
after, is the controlled comparison.

**Where the cost is, and it is not where it looks.** Two controlled experiments
on the tour, which is the clip with no hero aircraft:

| tour, marginal s/frame | |
|---|---|
| no aircraft at all | 5.09 |
| 10 aircraft, **3** types | 9.79 |
| 10 aircraft, **8** types | 13.48 |
| 10 aircraft, 8 types, **subdivision capped at level 1** | 15.28 |

So ~0.47 s/frame per *aeroplane* and ~0.74 s/frame per *type*, and **capping the
subdivision made it slower, not faster** — the geometry LOD idea is dead, the
cost is the number of distinct materials and texture sets, not the triangles.
Collapsing the six A320-family aircraft onto one type would buy back 3.7 s/frame
on the tour, about 15 minutes; it was not taken, because ceo/neo and
A319/A320/A321 are the evidenced workload of this base and 8 % of one render is
what that truth costs.

**Nothing stayed a proxy for cost reasons.** The honest answer here was that all
ten stands could carry a real master and the clips still render in one sitting —
about 4 hours for all three against about 2.5 for v2. The only proxies left on
this field are the five Aeroclube light aircraft, and they are proxies because
**no light-aircraft master exists**, not because of render time.

### 9.6 The placement verifies itself, and it caught something

Santiago's rule, generalised: nothing trusts a convention about where a master's
origin is or how big it is. Each aircraft is rotated nose-to-heading, its
**evaluated** envelope is measured through the depsgraph — collection instances
included — and the root is moved so the centre lands on the stand and the lowest
point, the tyres, lands on the apron. Then it is measured again and printed.
**Wheels seated to 0.000 m on all ten.**

On top of that `populate()` runs two checks the proxy table could not, because
the proxies were nominal boxes and the real spans are not. **Both found
something.**

**A pairwise 2-D overlap check.** The phase-4 `wide` proxy was 47.6 m of span
and a real 767-300ER is **51.2**, which put its starboard wingtip **1.6 m
inside** the A320 parked next door on the hangar frontage. Overlaps now: **0**.

**A ray-cast down at the centre and at the nose, tail and both wingtips**,
stepping past the aeroplane, its gear and the kit round it — a naive cast from
above answers `Fuselagem` for all ten and says nothing. Stand `N0` came back
`SDSC_AerodromeGround`: **the jacked LATAM Cargo 767-300F was standing on
dirt.** It sits in a notch of the mapped apron polygon, 5 cm below the concrete
and the same pale grey in a render, which is why it had shipped in `_v2`
unnoticed. Five more aeroplanes had a wingtip over the edge.

Phase 4's test had been a 21 m circle — a narrowbody half-span — against
`relation/7422967`, and it stopped being enough the moment real models went on
the stands. Ray-cast at 2 m over the whole MRO block, `SDSC_ApronConcrete` is
**10 632 cells of 38 409**: a deep frontage block from y 1770 to 1920, and above
it only three fingers, 10 to 50 m wide, at x ≈ 880, 920–930 and 970–1020.

So the nine stands were **re-solved against that map**, with the criterion a
ramp actually has — the **fuselage strip on pavement**, 13 m wide, which covers
the belly and the main-gear track of every type here (A320 7.6 m, 767 9.3 m,
787 10.8 m) — envelopes 8 m clear of each other and clear of every mapped
building, each stand taking the **nearest** solution to where phase 4 had put
it, so the composition is phase 4's and only the error is gone:

| stand | moved | |
|---|---|---|
| `H9`, `N2`, `N4` | 0 m | already right |
| `ROW0`, `ROW1`, `N1`, `N5` | 1–3 m | wingtip clearance and the strip |
| `N0` | **7 m** | off the dirt and onto the concrete |
| `N3` | **13 m** | onto its finger |

**A wingtip may overhang, and four still do.** Real ramps end somewhere and a
bounding box is mostly empty air; the check reports it every run rather than
pretending otherwise. Aircraft not standing on concrete: **0**.

### 9.7 The camera metrics, re-measured

Detailed models at the stands change what the nearest in-frame object is, which
is exactly the class of defect that bit Santiago. Re-measured on all three v3
files with `../scenario/camera_metrics.py`:

| | departure | the tow | the tour |
|---|---|---|---|
| nearest scenery in frame | 67 m, `SDSC_MownGrass` | **59 m, `SDSC_FloodlightMasts`** | 571 m, `SDSC_AerodromeGround` |
| phase 4 said | 67 m, `SDSC_AerodromeGround` | 59 m, `SDSC_FloodlightMasts` | 571 m, `SDSC_AerodromeGround` |
| worst foreground parallax | 47.5°/s (was 47) | 3.9°/s (unchanged) | 20.9°/s (unchanged) |
| aeroplane edge margin | 24.87% (unchanged) | 12.52% (unchanged) | — |
| body max/min flow ratio | 9.0 (was 8.7) | 2.0 (unchanged) | 1.3 (unchanged) |
| central-band frames > 0.5 w/s | 0 of 239 | 0 of 399 | 0 of 239 |

**No detailed model became the nearest object in any clip.** The near field is
grass at 67 m in the departure, hangar 9's own apron mast at 59 m in the tow, and
the aerodrome ground at 571 m in the tour — the same three as phase 4, at the
same three distances. The departure's nearest hit changes *name* only, from the
aerodrome pad to the mown-grass sheet, which are adjacent surfaces at the same
station; the body ratio moves 8.7 → 9.0 because some of the flow probes now land
on an aeroplane instead of on the apron behind it, and both numbers are an order
of magnitude below the comfort threshold.

### 9.8 Still open after phase 5

- **The open fan-cowl doors are authored geometry.** Their *position and size*
  are measured off each master's nacelle, but the doors themselves are two
  quads per engine that no master contains and no drawing in this repository
  specifies. They reproduce the state
  `refs/mro_centro_tecnologico_2010.jpg` photographs on this site; the panel
  angle (55°) and the fraction of the nacelle they cover (the forward 6–58%)
  are chosen to read at 300 m, not measured off that photograph.
- **No A330 and no light aircraft.** The A330-200 is recorded as the largest
  type here before 2020 and there is no master for it; the five Aeroclube GA
  aeroplanes are the only proxies left on this field, 180–280 m off a RWY 02
  roll, because there is no light-aircraft master either.
- **Four wingtips overhang the mapped concrete** — `N0`, `N1`, `N2` and `MID`.
  The criterion applied is the fuselage strip, and the check reports the
  wingtips every run. Whether the real apron is bigger than
  `relation/7422967` is not knowable from OSM; it was traced in 2017 and
  hangar 9 was not there either.
- **The mid-field stand was not re-solved.** `MID` is the only stand off the
  MRO platform and the concrete solver was run over the MRO block only; its
  767 keeps phase 4's position, with a wingtip over the edge.
- **The tow clip still appends its 787-9.** It is the one aircraft in the three
  clips that is not an instance, because the tow re-parents the nose gear to a
  steering empty and you cannot re-parent inside a collection instance.
- **The 787-8 is in the type table and unplaced.** There is one widebody stand
  at hangar 9 and it belongs to the -9. A second dream stand is one line.
- **`build_scenery` still keys the maintenance kit off `AC_TYPES`**, the
  nominal proxy dimensions, not off the real master the stand now carries. The
  docks and towers are sized from a 37.6 m "narrow" and a 54.9 m "wide"; the
  A319 at `N4` is 34.0 m and the 787-9 at `H9` is 62.9 m. Nothing looks wrong
  at the ranges these clips fly, and it is the obvious next thing to tighten.
