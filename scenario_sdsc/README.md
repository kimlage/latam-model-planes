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
  render_checks.py         the visual checks (plan / mro / ground / horizon / tour)
  load_terrain.py          heightfield -> mesh
  blender_assets.cats.txt  Asset Browser catalogues

  sdsc_aip_survey.json     the survey constants, every value with its source     <- read first
  sdsc_osm.json            aerodrome + MRO geometry in the local frame (ODbL)
  sdsc_osm_plan.png        the plan, drawn                    <- the build's check image
  sdsc_osm_plan_mro.png    the MRO block, drawn
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
`SDSC_Furniture`, `SDSC_ParkedAircraft` under `SDSC_Field`; plus `SDSC_Light` and
`SDSC_Anchors` at the top level.

Polygon budget: the field is **~37 000** faces, the terrain **3.7 M** (180 m tier
decimated ×3, 60 m and 30 m tiers full). The field is deliberately cheap — it is
background, and the MRO is seen from 0.8–1.9 km.

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
| **LATAM brand** | the wordmark and brandmark on the hangar line and on hangar 9, and the fins of the parked proxies | Trademark. Depiction of LATAM's own base; not a licence to reuse the marks. The lockup comes from `../latam_logo_indigo.svg` via `latam_livery_kit`, the same official outlines the fleet livery uses. |
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
    -P scenario_sdsc/render_checks.py -- ground horizon tour
```

Output lands in `scenario_sdsc/checks/`.

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
| roads, watercourses, landuse tint | in the plan, not in the build — `../scenario/` does not build them either |

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

---

## 7. What phase 3 needs — the three clips

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
