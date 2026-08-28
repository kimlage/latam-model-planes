# SBGR / Guarulhos — LATAM's hub, and the 777's home

**Phase 1: data only.** Nothing here is modelled. This folder is the survey,
the geometry, the climatology and the reference material a build phase will
consume — the same contents `../scenario_sdsc/` carries for São Carlos,
produced the same way, named the same way, so anyone who knows one knows the
other.

The target is **Aeroporto Internacional de São Paulo/Guarulhos — Governador
André Franco Montoro (SBGR / GRU)**: LATAM's largest hub, South America's
busiest international airport, and **the base where LATAM's Boeing 777-300ER
fleet is maintained** (CNN Brasil, recorded during the São Carlos survey —
777 maintenance is done at Guarulhos, *not* São Carlos). The 777 is the one
type in this repository with no scenery presence. Its hangar is on this
field, the ADC prints **HANGAR LATAM** over it, and on the dominant-flow
departure the aeroplane rotates abeam its own base.

```
scenario_sbgr/
  sbgr_aip_survey.json     the survey constants, every value with its source   <- read first
  sbgr_osm.json            aerodrome + LATAM-base geometry in the local frame (ODbL)
  sbgr_osm_plan.png        the plan, drawn                    <- the build's check image
  sbgr_osm_plan_latam.png  the maintenance corner, drawn
  sbgr_operations_wind.json  which flow the wind offers (ERA5 2021-2025)
  sbgr_operations_sun.json   solar geometry, computed here
  sbgr_references.md       what each photograph proves, and what I could NOT establish
  RECOGNITION.md           what makes the place recognisable, and the traps
  TERRAIN.md               the heightfields, and a horizon that is a RING
  terrain/                 3 heightfield tiers + horizon profiles + silhouette
  refs/manifest.json       the reference photographs, cited - never committed
  lib/frame.py             the ENU frame. Single source of truth.
  build_osm.py  build_terrain.py  prepare_dem.py  fetch_dem.sh
  horizon.py    silhouette.py     verify.py       plot_osm_plan.py
  --- phase 2, the build ---
  build_scenery.py         builds sbgr_field.blend and sbgr_terrain.blend
  load_terrain.py          the three heightfield tiers as meshes
  fleet_placement.py       the eleven masters, linked and instanced on stand
  render_checks.py         the visual gate: plan / latam / ground / horizon /
                           tour / fleet, output in checks/ (git-ignored)
  sbgr_field.blend         the aerodrome + city ring (committed)
  sbgr_terrain.blend       the terrain (git-ignored; rebuilds in ~2 min)
```

Reproduce the whole thing:

```bash
./fetch_dem.sh              # ~950 MB of DEM tiles, not committed
python3 build_terrain.py    # ~3 min
python3 horizon.py          # ~1 min
python3 silhouette.py
python3 verify.py           # the checks in TERRAIN.md §4
python3 build_osm.py        # re-queries Overpass; --offline reuses sbgr_osm_raw.json
python3 plot_osm_plan.py && python3 plot_osm_plan.py --latam
cd .. && python3 refs_fetch.py scenario_sbgr     # the photographs
```

---

## 1. The reference frame

One frame, `lib/frame.py`, used by every file here. Blender units are metres, 1:1.

| | |
|---|---|
| Type | local **ENU** tangent plane on WGS84 |
| Origin | lat **−23.4341667**, lon **−46.4825000** — the published threshold of **RWY 10L** |
| Origin source | AISWEB/ROTAER declared-distance table + SBGR ADC, `S 23 26 03 / W 046 28 57` |
| Axes | x = East, y = North, z = Up, metres |
| Vertical datum | **z = 0 at 750.0 m AMSL**, the published SBGR aerodrome elevation (2461 ft) |
| Runway true track | **073.65°** adopted (OSM tracing; published whole-second thresholds give 073.41/073.28) — 095/275 MAG with VAR 22 W |

**Why THR 10L.** Same choice as Santiago and São Carlos: the threshold where
the departure lines up. RWY 10L is the departure end of the departure runway
in the dominant flow (§ the runway answer, below), and the origin makes
`distance_along_roll_m` in `sbgr_osm.json` directly usable. Note the roll
physically starts at −90 m: the threshold is displaced and TORA is the full
pavement.

**The precision inversion — GRU's version of the SDSC bearing lesson.**
DECEA publishes these thresholds to **whole seconds** (±30 m), the coarsest
of the three bases — while OSM's tracing closes the published pavement
lengths to 1.5 m and holds the two centrelines parallel to 0.015°. So: the
**origin position** is the published string, the **bearing and relative
geometry** are the tracing, and `sbgr_aip_survey.json → divergences` records
the whole reconciliation instead of averaging it.

### The runways are LEVEL — the anti-SDSC

| point | x, y (m) | z (m) | AMSL |
|---|---|---|---|
| **THR 10L** (origin) | 0.00, 0.00 | **−4.76** | 2445 ft |
| THR 28R | 3 407.02, 1 014.94 | −5.98 | 2441 ft |
| THR 10R | −454.22, −523.05 | **−2.94** | 2451 ft |
| THR 28L | 2 413.20, 338.25 | −4.46 | 2446 ft |
| ARP | 965.24, −153.87 | +0.11 | 2461 ft |

Total published relief across a 5 km field: **6 ft**. The falls are 1.2 m
(north runway) and 1.5 m (south) — invisible. The aerodrome high point is the
RWY 10R touchdown zone (TDZE = AD ELEV). **But z = 0 is the aerodrome
elevation, not the pavement**: build the runways at z = 0 and they float
3–6 m.

### Anchors — built (phase 2)

`SBGR_Anchors` exists in `sbgr_field.blend`: Empties whose **+Y points down
the take-off track**. One divergence from the table below, recorded here: the
anchors sit on the **built centrelines (the OSM tracing)** so a parented
aircraft rolls down the middle of the pavement — `SBGR_10L_Threshold` is at
(−2.7, 12.3, −4.76), 12.6 m from the published string this table quotes. The
gap is the whole-second rounding the survey records; the published strings
below stay the frame's definition.

| anchor | position (x, y, z) | track |
|---|---|---|
| `SBGR_10L_Threshold` | (0.00, 0.00, −4.76) | 073.65° true — **departures** |
| `SBGR_28R_Threshold` | (3407.02, 1014.94, −5.98) | 253.65° true |
| `SBGR_10R_Threshold` | (−454.22, −523.05, −2.94) | 073.65° true — landings, east flow |
| `SBGR_28L_Threshold` | (2413.20, 338.25, −4.46) | 253.65° true |
| `SBGR_LATAM_Hangar` | (2281.2, 1361.7, ~−5) | doors face SSE onto the apron |
| `SBGR_TWR` | (~301, ~1323, —) | ADC label georef, ±100 m |

---

## 2. What is in `sbgr_osm.json`

OpenStreetMap via Overpass, **2026-08-26**, converted to the frame above.
This is not SDSC's stale one-session tracing: the NE-corner hangars, aprons
and stands are recent, well-drawn work. Counts:

| | |
|---|---|
| runways | 7 ways → 2 centrelines (3 698.5 m + 3 000.0 m merged) |
| taxiways | 302 ways, 34.1 km |
| aprons | **25**, 677 272 m², named **Pátio 1–7** |
| hangars | **5** — LATAM, American Airlines, 2× BASP (4º ETA), Táxis Aéreos |
| terminals | 13 — T1, T2, T3, TECA ×3, people-mover stations |
| gates / parking positions | **171 / 215** |
| holding positions / navaids / windsocks | 76 / 145 / 2 |
| buildings (inside the fence) | 122 |
| landuse / roads / railways / water | 415 / 1 415 (269 km) / 39 (32 km) / 251 (77 km + bodies) |
| aerodrome boundary | 1 ring, 496 points |

Plus two derived blocks: `latam_maintenance` (the hangar, its evidence, its
apron, its projection onto the 10L roll) and `departure_10L_landmarks`.

**The extract is scoped, and the cuts are decisions** (full list in
`build_osm.py`'s docstring). Kept: every aeroway feature; everything inside
the fence; motorway/trunk/primary/secondary (Hélio Smidt, Ayrton Senna,
Dutra, Rodoanel); the CPTM Line 13 rail into the airport; landuse and water
(the Rio Baquirivu-Guaçu). **Cut: ~2 756 city buildings and ~8 550 minor
street ways of Guarulhos** — the city is a landuse-tint-plus-procedural
problem for phase 2, not 2 756 footprints, and the cut is written down here
so it stays a decision and not an accident.

### The LATAM maintenance block

| | |
|---|---|
| the hangar | **way/778050745**, `building=hangar`, name `Latam Airlines` |
| footprint | **136.8 × 92.2 m**, 9 998 m², long axis 073.7° — parallel to the runways |
| its apron | way/778050217, 32 892 m², doors face SSE onto it |
| chart label | the ADC prints **HANGAR LATAM** at the georeferenced spot (±100 m); the AGMC DEP 10L repeats it |
| AIP-side evidence | ROTAER: **TAM Linhas Aéreas holds the 65–80 m-span recovery kit** at GRU |
| neighbour | American Airlines hangar, way/777394328, 178.6 × 95.0 m, long axis **perpendicular** — the older of the pair (DSM reads it; not the LATAM one) |
| on a 10L departure | **LEFT side, abeam at 2 575 m** — where a heavy 777 rotates — **654 m** out |
| on a 28R departure | right side, 975 m into the roll, aircraft still on the ground |
| height | **none measured.** The 2011–14 DSM reads flat ground under it (and under Terminal 3, opened 2014): the hangar postdates the data. Bracketed 2014–2020 by the 2013 dome photograph + DSM + OSM way age. |

---

## 3. What is measured, and what I estimated

The honesty contract. Read this before quoting any number out of this folder.

### Measured / published — safe to quote

| thing | value | source |
|---|---|---|
| RWY 10L/28R | **3 700 × 45 m ASPH, PCR 790/F/C/X/T** | ROTAER + ADC |
| RWY 10R/28L | **3 000 × 45 m ASPH, PCR 810/F/C/X/T** | ROTAER + ADC |
| Thresholds | the four whole-second strings in `sbgr_aip_survey.json` | ROTAER declared-distance table + ADC |
| Displacements | 90 m at 10L, 60 m at 28R; none on the south runway | ROTAER |
| Declared distances | 10L/28R TORA 3700 both ways, ASDA 3760, LDA 3610/3640; 10R TORA 3000 TODA **3300**, ASDA 3060 | ROTAER (identical on the ADC) |
| Stopways / clearway / strips | SWY 60×45 at all four ends; CWY 300×150 at the 28L end; strips 3940×300 / 3240×280 | **ADC — published, where SDSC had to infer** |
| THR elevations | 2445 / 2441 / 2451 / 2446 ft | the four IAC charts |
| TDZE, AD ELEV | 2446 / 2442 / 2461 / 2451; AD 2461 ft | ADC |
| Magnetic variation | **22 W** | IAC charts |
| Magnetic bearings | 095 / 275 | ADC + IAC final courses |
| True bearing | **073.65** adopted (OSM); 073.41/073.28 from published thresholds | recorded reconciliation |
| ILS | 10L IUC CAT II · 10R IGH **CAT III** · 28L IBC CAT I · 28R IGS CAT I | ROTAER + ADC |
| Approach lights | ALSF-2 on 10L and 10R, ALSF-1 on 28R and 28L; PAPI ×4 (MEHT 57/61.5/63/71 ft) | ADC |
| Frequencies, RFFS CAT 10, H24 | as published | ROTAER |
| Geoid undulation | −2.33 / −2.35 m | ROTAER |
| Every footprint, taxiway, apron, gate, stand | as mapped | OSM, `sbgr_osm.json` |
| Terrain | Copernicus GLO-30 + SRTM control, 30/60/180 m tiers | `TERRAIN.md` |
| Horizon | **+0.12° .. +3.23°**, a ring; departure sector 0.22–0.72° | `terrain/horizon_5deg.json` |
| Pre-2014 building heights (floors) | T2 +14.1, T1 +10.8, TECA +8–10, AA hangar +7.2 | Copernicus DSM |
| East flow availability | **67.4%** all hours; 78% mornings; 39–46% at 12–15 local | ERA5 2021–2025 |
| Solar geometry | Dec solstice noon = 89° — zenith | computed (NOAA algorithm) |

### Estimated by me — do NOT quote these as data

- **The runway answer's final step.** Every published sign points at the
  north runway for departures (ARR chart only for 10R, CAT III on 10R,
  intersection notes only on 10L/28R, TORA) — but no single DECEA sentence
  says "departures use 10L". Strong reading, declared as a reading. The eAIP
  AD 2 text might contain the sentence; it was not retrievable (see
  divergences).
- **The TWR position** — chart-label georef, ±100 m, no OSM object, no
  published height.
- **Heights of everything post-2014** — Terminal 3 and the LATAM hangar have
  *no* measured height; the DSM predates them. 10 of ~140 buildings carry
  any OSM height/levels tag.
- **The bearing choice** 073.65 — argued from parallelism and closure, not
  printed anywhere.
- **The south strip width 280 m** — read from a jumbled ADC table cell, low
  confidence.
- The `departure_10L_landmarks` distances inherit the origin's ±30 m.

### Divergences left standing, not silently split

Full text in `sbgr_aip_survey.json → divergences_recorded_not_split`:
threshold precision vs OSM tracing; true bearing 073.4 vs 073.65; VAR 22 W
(chart) vs ~21.4 (IGRF context) vs the 2019 renumbering; **PCR ≠ PCN** (790
is not a giant PCN); the south strip width; OSM's duplicated "Pátio 7"; the
hangar's day-to-day branding (charts say LATAM, no photograph confirms the
facade).

---

## 4. The z-stack plan — flat, for once

Phase 2's stack can be Santiago-simple: constant offsets on a level field.
The published pavement levels: north runway surface −4.76 → −5.98, south
−2.94 → −4.46, apron/terminal platform ≈ −4 to −6 (DEM), the whole spread
under 4 m. **No graded function needed** — the SDSC machinery stays home.
The two GRU-specific rules instead:

```
 z = 0 is the AD elevation (750 m), 3-6 m ABOVE every pavement
 the DSM outside the fence is city roofs and canopy, not ground - do not
 sit the fence line or the Baquirivu belt on raw DSM values without looking
```

Collections, when the build comes: `SBGR_Runways`, `SBGR_Taxiways`,
`SBGR_Aprons`, `SBGR_Terminals`, `SBGR_LATAM_Base`, `SBGR_BASP`,
`SBGR_Cargo`, `SBGR_Furniture` (the two mast designs, the ILS lattices),
`SBGR_Roads`, `SBGR_Rail`, `SBGR_Water`, `SBGR_City` — plus `SBGR_Light`
and `SBGR_Anchors`.

---

## 5. Licences — read before publishing anything built from here

| source | covers | obligation |
|---|---|---|
| **OpenStreetMap** | every footprint, taxiway, apron, stand in `sbgr_osm.json`, and any mesh generated from them | **ODbL 1.0** — attribution + share-alike |
| **Copernicus DEM GLO-30** | `terrain/*` | attribution © DLR 2010-2014 / © Airbus DS 2014-2018, ESA/EU — full text `TERRAIN.md` §7 |
| **SRTM v3** | control DEM | public domain |
| **AISWEB / DECEA** | the survey values | quoted as fact; **charts are NOT redistributed** — numbers and URLs only |
| **ERA5 via Open-Meteo** | `sbgr_operations_wind.json` | C3S/ECMWF; Open-Meteo CC BY 4.0 |
| **Wikimedia Commons photographs** | appearance | CC BY / CC BY-SA / PD per `refs/manifest.json`; **git-ignored**, fetched on demand. MARCO AURÉLIO ESPARZ carries this survey too (5 of 14) |
| **LATAM / American brands** | the hangar titles, aircraft liveries | trademark; depiction of the real place, not a licence to reuse marks |

---

## 6. Checking it — `python3 verify.py`

```
1. delivered grid vs DEM horizon: 30+60+180 stack  rms 0.018  max 0.056 deg
2. the ring: +0.144..+3.077 (5-deg grid; fine profile peaks 3.23 at az 006)
   N sector +1.76..+3.08, departure sector ESE +0.24..+0.66
   near field exceeds the terrain horizon at 16 of 72 azimuths
3. THR elevations: published vs Copernicus vs SRTM spread 2-5 m; falls 1.2/1.5 m
4. published thresholds close their own arithmetic to +4.6/-6.4 m;
   OSM centrelines close 3700/3000 to <=1.5 m, parallel to 0.015 deg
```

`python3 refs_fetch.py --verificar` exits 0: every entry carries URL, author
and licence; no photograph is tracked by or exposed to git.

---

## 7. What phase 2 needs — and must decide

The field data is here; these are the decisions the build owes the record:

1. **The LATAM hangar's body.** Footprint and orientation are data; height,
   doors, cladding and branding are not (no photograph, no DSM return, no
   published dimension). A 777-300ER is 18.5 m tall, 64.8 m long, 64.8 m in
   span; the door must clear it. Declare the inference the way SDSC declared
   hangar 9 — one constant block, movable if a photograph surfaces.
2. **The tower.** ADC georef (301, 1323) ±100 m, three photographs for shape,
   no height. Estimate from the photographs' proportions and say so.
3. **How to render the city.** The deliberate cut of 2 756 footprints must be
   answered with SOMETHING — landuse-tinted blocks, procedural massing along
   the mapped major roads, the Baquirivu green belt, the favela texture on
   the Cabuçu flank that two photographs show. An empty ring would be the
   floating-aerodrome mistake repeated at metropolitan scale.
4. **The ramp population.** 215 stands and 171 gates are mapped; allocation
   is not published. Whatever mix of LATAM narrowbodies/widebodies and the
   international heavies goes on stand is inference — the photographs give
   the flavour (747/A330/777 era by era).
5. **Which stands the 777s sleep on** — probably the 901–912 remote row by
   the hangar (the 2013 photograph shows exactly that), but that is a reading
   of one old frame, not data.
6. **The clip geometry** (for phase 3, but it constrains what phase 2 builds
   at detail): the 10L departure with a south-side camera puts the rotating
   777, its own hangar line, and the Cantareira wall in one frame —
   `refs/latam_cargo_767_north_rwy_cantareira_2023.jpg` is that composition,
   photographed. Build detail budget accordingly: the NE corner and the
   north-side frontage are foreground; the BASP side is background.
7. **Flow honesty in any animated scene**: morning = east flow (78%), early
   afternoon leans west, ~17:00 back to east. A single clip should pick a
   time of day and let the flow follow the wind table.

---

## 8. The phase-3 answer, stated once

**Protagonist**: the Boeing 777-300ER — maintained here, absent from all
scenery so far. **Runway**: 10L, full 3 700 m, east flow. **Geometry**: the
terminal frontage plays past the first kilometre of the roll on the left;
the American hangar, then the LATAM hangar come abeam at 2.3–2.6 km — the
777 lifts its nose next to its own base — 654 m out. **Composition, not
terrain — but the terrain composes**: GRU is flat along the track, and the
climb-out points into the lowest horizon sector (0.2–0.7°, sky like São
Carlos's); the drama stands BEHIND the aircraft — the Cabuçu/Cantareira
wall, 1.8–3.2°, 4–14 km, permanently in frame from any south-side camera.
The SDSC terrain-reveal, inverted: there the mountains appeared as the
aircraft climbed; here the ridge is the backdrop from brake release, and the
photographed proof is in `refs/`.

---

## 9. The build — phase 2

Everything below is in `build_scenery.py`, `fleet_placement.py` and
`render_checks.py`; this section is the decisions, so they stay decisions.

```bash
blender -b --factory-startup -P scenario_sbgr/build_scenery.py -- --terrain   # ~2 min
blender -b --factory-startup -P scenario_sbgr/build_scenery.py -- --field    # ~1 min
blender -b --factory-startup scenario_sbgr/sbgr_field.blend \
    -P scenario_sbgr/render_checks.py -- plan latam ground horizon tour fleet
```

### 9.1 The z reconciliation — flat field, one number

Copernicus reads the four thresholds 1.2–2.8 m below their published
elevations (EGM2008 vs the −2.33 m geoid undulation is most of it).
`DEM_TO_PUB = +1.84` — the mean of the four offsets — shifts the DEM onto the
published datum; the runway strips are then forced to the published threshold
lines exactly, and each apron zone is held flat at (its own DEM median
+ 1.84). `verify_levels()` reprints the residuals every build: the four
graded thresholds land on the published values to 0.00 m.

Zone plateaus (measured medians, in-build probe 2026-08-26): terminal
frontage + TECA **−9.20**, Pátio 9 / 901 row / hangars **−8.70**, east cargo
−8.50, Sideral −7.00, VIP −0.20, BASP **−2.00 (clamped — the DSM reads +1.3
there, but that is hangar roofs in a 2011–14 surface model)**. The terminal
platform really is ~4 m below the north runway: the field falls north, as the
ADC's "high point = RWY 10R TDZ" says.

**The NE corner is ONE towable plateau (−8.70) — declared inference.** The
DEM reads −6.93 under the hangar apron, but that epoch (2011–14) predates the
hangar: it is pre-construction ground. A 3.6 m step against the touching
Pátio 9 would make the hangar unreachable by a towed 777; continuity with the
ramp is the constraint. The first build used the raw DEM figure and the fleet
placement's own ray-cast caught the cliff.

### 9.2 Runways

Built ON the OSM centrelines (survey `divergences` resolution: origin =
published string, relative geometry = the tracing): north pavement
(−88.4, −14.0)→(3460.7, 1026.5) at 073.66 true, south (−462.6, −513.0)→
(2415.9, 331.7) at 073.65, centrelines 373 m apart. Published displacements
(90/60 m), stopways (60 × 45 at all four ends, ADC), the 28L clearway,
Annex 14 marking set for LDA ≥ 2400 (12 threshold stripes, letter-then-number
**10L/28R/10R/28L designators — the 2019 renumbering, not the 09/27 of the
old photographs**, 400 m aiming point, six TDZ pairs, displaced-threshold
arrows), ALSF-2/ALSF-1 approach-light skeletons per the ADC, PAPI ×4,
localizer arrays, edge lights, 76 holding boards, 2 windsocks.

### 9.3 The invented verticals — every one a movable constant

| thing | built | basis |
|---|---|---|
| **LATAM hangar** | eave 26 m, ridge 30 m, door 100 × 20.5 m on the SSE face, one 30 m bay open; indigo fascia band + official-SVG lockup | **NO photograph, NO DSM return exists.** Sized so a 777-300ER (18.5 m tail) clears the door; branding on the charts' authority (ADC/AGMC print HANGAR LATAM). `LATAM_HANGAR` constant; flip when a photograph surfaces |
| American hangar | eave 24 m, ridge 27.5 m, unbranded grey, door band on the apron end | DSM floor +7.2 m is smeared; a widebody door band needs ~24 m. `AA_HANGAR` |
| TWR | concrete shaft, two-ring gallery at 42/47 m, glazed cab to 55 m, white radome ball top ≈ 61 m | shape from `tower_closeup_2024.jpg`; height from proportion vs T2 in the 2013 frame (~3.5–4× a 20 m roofline); position = ADC label georef ±100 m. `TOWER` |
| Terminal 3 | 20 m, same band as T2 | opened 2014 — absent from the DSM. Built as T2's sibling |
| Terminal 2 / 1 / TECA | 20 / 14 / 11 m | DSM floors +14.1 / +10.8 / +8..10 plus roof plant |
| floodlight masts | 30 m, two designs (ring-head + lattice-rack) | the two designs are photographed side by side (2026 frame); 30 m is the international-apron band, no published figure |
| jetbridges | **two tiers since the scene-detail round (2026-08-27)**: 9 ARTICULATED bridges docked at the parked fleet's door-1 stations on the T2/T3 frontage — rotunda drum, sloped tunnel, elbow, fatter telescoping barrel, cab on a support portal with a wheel bogie — plus 6 parked articulated ones at free frontage gates (barrel drawn back, cab swung 35°), and 77 massing tubes at every other gate | the frontage is what the tour and the 10L departure actually see. The cab is aimed with real per-type door geometry (`DOCK_TYPES`, declared inference) **plus a measured +2.0 m nose correction**: `fleet_placement` centres the world AABB, not the fuselage — probed +1.9/+2.1 m on G403/G402 — and the cab face is held 0.4 m off the skin to absorb the residual. Gates the cameras never approach keep the massing per the LOD rule |

### 9.4 The city ring — the answer to phase 1's cut

Three layers, all cheap, all clipped to the fence RING by a signed-distance
field (the first build clipped to the boundary BBOX and buried the metropolis
under 25 km² of infield grass — caught by the plan check, which exists for
exactly that):

1. **Landuse tint** — 47 669 cells, 30 m, snapped to the near terrain tier's
   own lattice and sampled from the same DEM, so tint and terrain are
   parallel by construction and cannot interleave (the SDSC cane-sheet lesson
   applied before the fact). Residential polygons on the north hills render
   as the tighter, redder hillside fabric the photographs show climbing the
   Cabuçu flank. **Plus, since the surround round, 72 733 street-mask fabric
   cells**: `surround_osm.py` re-queried the ~8 550 minor streets and ~2 756
   footprints phase 1 deliberately cut (wider bbox, documented in the file —
   the owner's verdict on the first tour was *"o entorno está todo muito
   vazio"*), and every 30 m cell within ~50–100 m of a mapped street that no
   landuse polygon covers gets the residential tint. Brazilian OSM maps
   streets far more completely than landuse — Bonsucesso and Água Chata
   across the Baquirivu valley exist in the render because their streets are
   mapped, even though their landuse mostly is not.
2. **Massing** — 22 000 structures, three sources in order of honesty:
   7 743 **real footprints** (min-area boxes, height from `building:levels`
   where tagged); procedural boxes inside the mapped polygons within 4.2 km
   — and the big industrial polygons south of the field build as the
   **Cumbica logistics belt**, 45–110 m warehouses, not houses (835 of
   them); fabric houses on urban street-mask cells nothing else covered,
   nearest-first to 6.5 km. All of it stands on the DSM, which already
   contains roofs — a storey of double-counting, declared, invisible under
   haze at 1.5+ km.
3. **The mapped lines** — 255 km of major roads **plus 1 303 km of the minor
   streets themselves**, the CPTM Line 13 viaduct on piers (13.5 km), the
   Rio Baquirivu-Guaçu and 77 km of watercourses, and 2 344 trees: gallery
   rows on the watercourses, verge rows along the avenidas, park crowns on
   the green landuse.
4. **The serra** — 23 222 closed-canopy crowns (14 verts each, ONE material)
   on every high (+30 m, closing by +46) or steep (slope > 0.13) unbuilt
   cell, north first so the Cantareira wall that backs every clip can never
   lose out to the cap. The terrain material underneath was re-cut in the
   same round: forest from +18 m (full by +52 — the old 25→90 band rendered
   the whole visible flank as half-mixed bare tan), near-black-green matching
   the crowns, 45 m canopy noise instead of the 420 m city hash. The **"tint
   sawtooth"** phase 2's checks recorded stepping down the NE knoll turned
   out to be `build_ground`'s pad skirt climbing the flank in 25 m grass
   steps — the skirt now clips to flat ground and the knoll carries scrub
   crowns instead.

Beyond the tint reach the terrain's own material carries the fabric: a
block-hash city grey on the flats going closed-canopy green on height, so
the Cabuçu and Cantareira read as the forested wall of the photographs, and
the far tier's Atlantic corner reads as sea. Render cost of the whole
surround, measured on tour frame 120 (960×540, 96 samples, Metal): 13.6 →
16.4 s/frame, **+2.8 s (+21 %) for ~0.9 M added faces and two new
materials** — the material count, not the triangles, is what renders pay
for, and the round added only `SBGR_SerraCanopy` and `SBGR_WarehouseShed`.

### 9.5 Population — the ramp is not empty

`fleet_placement.py` instances **all eleven masters** (the only base where
that is honest) at sixteen stands: seven narrowbodies on the T2/T3 frontage,
787-8/787-9 at T3, the two Cargo 767s at TECA III, four widebodies on the
901 row, and **the 777-300ER at its own hangar** — plus a second 777 at
R901. Same link-and-instance machinery as SDSC (Cycles keys geometry on the
object; collection-instance empties share one evaluated geometry per TYPE,
so sixteen aircraft cost eleven geometries). Stand allocation is UNPUBLISHED:
the 901-row reading comes from the 2013 widebody photograph, the terminal
split from the airline's public T2/T3 operation. Placement self-verifies:
evaluated-envelope seating (wheels to 0.000 m), pairwise overlap check (it
re-picked the T3 and 901-row stands to widebody pitch), and a ray-cast
concrete check (it caught the NE-plateau cliff).

**Non-LATAM traffic is four neutral white proxies at distant gates** — GRU's
ramp is half other airlines' metal and this repository has no non-LATAM
model; an anonymous white airliner 600+ m from every camera is the honest
rendering.

GSE at every occupied stand (tug + towbar, GPU, loaders, catering, stairs
and bus at the remote row, dolly trains + ULDs at cargo, bowsers at the fuel
tanks) — 84 clusters, positions inferred, presence not.

### 9.6 Light, and the flow-honest render hour

**21 December, 17:30 local: sun 16.46° up at 251.1° true**
(`sbgr_operations_sun.json`). The raking light on the hangar frontage with
the Cantareira behind — and the honest flow hour: 12–15 local is when west
flow peaks (39–46 % east), by 17:00 east flow is back to 62 % (ERA5), so a
17:30 10L departure does not fight the wind table. Sun/sky balance MEASURED
by the white-card method: 2.3 : 1 direct:diffuse. Haze V = 19 km, H = 1200 m
(humid metropolitan summer, between SCL's 14 and SDSC's 18 — inferred).

### 9.7 The budget

| piece | faces |
|---|---|
| field (everything in `sbgr_field.blend`) | **1 071 825** (177 117 before the surround round) |
| of which: city tint + massing + serra crowns | ~970 000 |
| terrain, three tiers | 3 697 248 |
| fleet | 11 unique master geometries, instanced 16× |

LOD by camera reach (§8: the clips fly the 10L roll and an aerial tour):
the NE corner, the 901 row and the north frontage are foreground and carry
door/band/lockup detail; gates the camera never approaches get
pier-and-jetbridge massing; the BASP side and the city are background tint
and boxes.

**The fleet's marginal render cost, measured** (960×540, 64 samples,
Cycles/Metal, the south-side composition frame — the heaviest ramp view):
empty ramp 9.2 s, populated 15.8 s — **+6.6 s (+71 %) for sixteen aircraft**,
+2.8 M instanced triangles over 11 shared geometries. The instancing is what
makes that affordable: appended copies would have cost sixteen geometries.

### 9.8 The gate

`render_checks.py` renders: `plan` / `latam` (orthographic, framed to match
`sbgr_osm_plan.png` / `sbgr_osm_plan_latam.png` EXACTLY — the checks that
catch a silently-wrong build), `ground` (the 10L roll stations, including
abeam-the-hangar-at-rotation and the south-side composition the 2023 LATAM
Cargo photograph proves), `horizon` (N/E/S/W against the phase-1 ring table),
`tour`, `fleet`. Every check populates the ramp first, exactly as the clip
files will. `python3 refs_fetch.py --verificar` exits 0.

## 10. The three clips — phase 3, and the surround round

### 10.1 The clips, and how to re-render each

All three render at 960×540, Cycles/Metal, 96 samples, AgX Medium High
Contrast, motion blur OFF (its second BVH build is what blew the 9.7 GB
Metal ceiling — `takeoff_camera.py` documents it), through the chunked
resumable driver (frames land inside the repo, git-ignored, and survive a
reboot — one did):

    bash scenario_sbgr/render_drive.sh <scene.blend> <frames_dir> <end>
    python3 scenario_sbgr/encode_gif.py --dir <frames_dir> --out <gif> \
        --width <W> --colors <C>

| clip | scene | frames | GIF knobs | rebuild the scene with |
|---|---|---|---|---|
| departure, 777 off 10L | `sbgr_takeoff_v1.blend` | 240 → `frames_tk/` | 800 px / 112 colours | `blender -b sbgr_takeoff.blend -P takeoff_camera.py -- --out sbgr_takeoff_v1.blend` |
| hangar roll-out, tail first | `sbgr_rollout.blend` | 400 → `frames_roll/` | 680 px / 84 colours | `blender -b --factory-startup -P hangar_rollout.py -- --out sbgr_rollout.blend` |
| aerial tour | `sbgr_base_tour.blend` | 240 → `frames_tour/` | 640 px / 64 colours | `blender -b --factory-startup -P base_tour.py -- --out sbgr_base_tour.blend` |

Every GIF is verified with PIL frame-by-frame (40 ms on every frame, count
against the directory, ≤ 15 MB) — `encode_gif.py` does it and exits nonzero
otherwise; never trust the byte scan. The takeoff and tour scenes LINK the
field and terrain, so a scenery rebuild reaches them at render time with no
scene rebuild; **the roll-out APPENDS the LATAM base locally** (it re-cuts
the 76 m door opening into the wall) **and must be re-run through
`hangar_rollout.py` after any scenery change**, or it renders the old base.

### 10.2 The surround round (2026-08-26, after the first three GIFs)

The owner's verdict on the first tour was *"o entorno está todo muito
vazio"* — and the render evidence agreed: bare tan hills where the
Cantareira's closed canopy should be, nothing across the Baquirivu valley,
a sparse ring even where fabric existed, ~800 trees for a subtropical
metropolis edge. The round that answered it is §9.4 as it now reads:
the `surround_osm.py` re-query (streets are the urbanization truth where
landuse is thin), 120 402 tint cells, 22 000 structures with 7 743 real
footprints, the Cumbica warehouse belt, 1 303 km of minor streets, 23 222
serra crowns over a terrain material re-cut to closed-canopy dark, and the
"tint sawtooth" diagnosed to `build_ground`'s pad skirt climbing the NE
knoll — never tint at all. Cost discipline held from the fleet round's
measurement (render cost scales with DISTINCT MATERIALS, not triangles):
two new materials, +2.8 s/frame (+21 %) on the tour beat. The before/after
pairs live in `checks/before_surround/` against the current `checks/`
frames; the clips were re-rendered as v2 GIFs afterwards, keeping v1 in git
history per the per-round GIF rule.
