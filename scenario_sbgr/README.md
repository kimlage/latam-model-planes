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

### Anchors phase 2 will want

Not built yet — no `.blend` exists. When it is, mirror `SDSC_Anchors`:
Empties whose **+Y points down the take-off track**.

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
