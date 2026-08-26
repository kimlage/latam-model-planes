# SBGR — photographic and documentary survey of LATAM's hub at Guarulhos

Phase 1 of the third base. Sibling of `../scenario_sdsc/sdsc_references.md`,
same rules: every photograph is cited with URL, author and licence in
`refs/manifest.json` and **never committed**; every measurement states its
method; and §6 lists what could **not** be established, which is the part a
build phase must read before inventing anything.

The target is **LATAM's maintenance base and hub operation at Aeroporto
Internacional de São Paulo/Guarulhos (SBGR / GRU)** — the airline's largest
hub, and the place where the **Boeing 777-300ER fleet is maintained** (CNN
Brasil, recorded during the São Carlos survey: 777 maintenance is done at
Guarulhos, *not* São Carlos). The 777 is the one type in this repository with
no scenery presence; its home base is this folder.

---

## 1. Reference frame adopted

Origin = the **published threshold of RWY 10L** (S 23 26 03 / W 046 28 57,
AISWEB/ROTAER + ADC), z = 0 at the published 750 m aerodrome elevation.
x = East, y = North, metres. `lib/frame.py` is the single source; every number
below is in that frame. **The published thresholds are whole seconds (±30 m)**
— see `sbgr_aip_survey.json → divergences` for how the OSM tracing reconciles.

### What goes past on a RWY 10L departure

From `sbgr_osm.json → departure_10L_landmarks` (the roll physically starts at
−90 m; a heavy 777 rotates ~2 200–2 900 m in):

| along roll | offset | side | what |
|---|---|---|---|
| 325 m | 770 m | left | Terminal 2 |
| ~500 m | ~1 000 m | left | Terminal de Cargas (TECA) behind it |
| 983 m | 763 m | left | Terminal 3 |
| ~1 320 m | ~890 m | left | the TWR (ADC georef, see §4) |
| **2 575 m** | **654 m** | **left** | **the LATAM hangar** — abeam at rotation |
| 2 3xx m | ~600 m | left | the American Airlines hangar, just before it |
| ~1 900–2 900 m | 300–900 m | right | the BASP (air base) hangars and Pátio 13 |

The SDSC geometry — the base coming abeam exactly at rotation — **repeats
here without being asked for**, mirrored to the left.

---

## 2. Photograph table

13 photographs fetched + 1 citation-only, all CC BY / CC BY-SA / PD, all in
`refs/manifest.json`. **MARCO AURÉLIO ESPARZ**, who carried the São Carlos
survey with 8 of its 13 frames, turns out to have photographed Guarulhos too:
five of the frames here are his, all from **30 November 2013**, all 4000×3000.

### 2.1 The maintenance corner — the point of this base

| file | date | what it shows |
|---|---|---|
| `refs/ne_apron_tam_widebodies_dome_2013.jpg` | 2013 | **the NE corner before the hangar existed**: the new remote apron with painted stand numbers **901–912**, five TAM/American widebodies parked, an **inflatable white dome** on the spot where the permanent hangar now stands, a building under construction at frame left, the Baquirivu green belt and Guarulhos climbing the hills behind |
| `refs/latam_cargo_767_north_rwy_cantareira_2023.jpg` | 2023 | a **LATAM Cargo 767 rolling on the north runway** seen from the south runway, approach-light masts, and the **whole Cabuçu/Cantareira green wall behind it** — current colours, and the phase-3 composition in one photographed frame |
| `refs/latam_777_tam_livery_taxiing_2017.jpg` | 2017 | the group's 777-300ER **PT-MUH taxiing at GRU — in TAM livery**, past signs reading **09L / 27**: the old designators. Ground furniture and grass line |

### 2.2 Runways and thresholds

| file | date | what it shows |
|---|---|---|
| `refs/thr_09l_lineup_dawn_2012.jpg` | 2012 | cockpit view **lined up on today's 10L at dawn**, fog, sun dead ahead — the departure clip's opening frame; threshold stripes and displaced-threshold arrows |
| `refs/rwy28l_rollout_terminals_tower_2023.jpg` | 2023 | 28L rollout in rain: grooved pavement, the parallel runway, the terminal frontage + TWR silhouette on the flat horizon |
| `refs/west_taxi_queue_hills_2013.jpg` | 2013 | the west-end taxi queue (TAM A321, GOL 737), T2 tails, northern hills over everything. **Its own caption is wrong** (calls 09L "3000 x 45" *and* "the longest") — captions are not survey data |

### 2.3 Terminals, tower, aprons

| file | date | what it shows |
|---|---|---|
| `refs/tower_closeup_2024.jpg` | 2024 | **the TWR close up**: bare concrete shaft, two-ring gallery, glazed cab, white radome ball — LATAM tails at the pier behind |
| `refs/t2_tower_t3_construction_2013.jpg` | 2013 | T2's frontage, the TWR among the terminals (agrees with the ADC georef), T3 under construction, floodlight-mast forest |
| `refs/t3_apron_747_a330_masts_2023.jpg` | 2023 | T3 apron at dawn: 747-8 + A330, marshaller, pink-edged lanes, mast head close up |
| `refs/remote_stands_masts_city_2026.jpg` | **2026-07** | the newest frame found: remote stands, **two floodlight-mast designs side by side**, north-fence sheds, the city on the hill — what the field looks like *now* |

### 2.4 The surround — the anti-São-Carlos

| file | date | what it shows |
|---|---|---|
| `refs/ramp_heavies_cantareira_2013.jpg` | 2013 | the ramp line of heavies with **the Serra da Cantareira as the whole backdrop** (the caption names the Serra) |
| `refs/climbout_north_city_2013.jpg` | 2013 | seconds after a 09L/10L departure: **city wall-to-wall**, hills under cloud, red-soil lots at the fence |
| `refs/city_fence_taxiway_2023.jpg` | 2023 | TAP A330neo holding short with houses and sheds **pressed against the fence** — the middle distance at GRU is city, not farmland |

Citation-only: `AeroportoGuarulhos Torre2.jpg` (PD, 2007) — the tower in 2007,
not fetched, not verified.

---

## 3. What the photographs establish

- **The maintenance corner's history**: numbered remote stands 901–912 and an
  inflatable dome in 2013; the permanent hangar absent. Together with the DSM
  (flat under the footprint, 2011–14 epoch) and the OSM way ids (~2020), the
  LATAM hangar is bracketed **built between 2014 and 2020**. The ADC and AGMC
  charts label it HANGAR LATAM today.
- **The composition answer photographed**: from the south side, an aircraft on
  the north runway stands against the Cabuçu/Cantareira ridge
  (`latam_cargo_767_north_rwy_cantareira_2023.jpg`). The horizon profile says
  the same thing in numbers (N sector 1.8–3.2°).
- **The tower's appearance and position**: concrete shaft + radome ball, among
  the terminals — three frames agree with the ADC label georef at ENU
  (301, 1323).
- **The field is flat** — no crest, no platform steps; every ground-level
  frame confirms what four published THR elevations within 6 ft say.
- **The furniture**: two floodlight-mast designs, pink-edged apron lanes,
  grooved runway, ILS approach-light lattices — all photographed close enough
  to model from.
- **The surround is city**: Guarulhos to the fence on the north and east, the
  BASP and more city south, the green Baquirivu belt the only gap.

### And what they do **not** establish

- **No photograph of the LATAM hangar itself was found** — not its facade, not
  its doors, not its branding. The 2013 dome frame shows the site *before* it;
  the 2023 frames graze past it. Its appearance is **phase-2 inference** until
  a photograph or street-level source is found.
- No frame shows the current **LATAM livery on a 777 at GRU** (the 2017 one is
  TAM livery; the 2023 Cargo 767 is current but a 767). The fleet masters in
  this repository carry the current livery; the scenery must not copy the 2017
  photo's colours.
- Nothing establishes **which gates/stands are LATAM's** on a given day.

---

## 4. What I measured, and how

- **Chart georeferencing.** The ADC and AGMC DEP 10L PDFs carry lat/lon
  graticules in their text layers. Affine-fitting the graticule label
  positions (6 lat + 6 lon points, residuals ≲2 px) turns every chart label
  into WGS84: HANGAR LATAM → (−23.4203, −46.4580) on the ADC and
  (−23.4201, −46.4598) on the AGMC; TWR + AIS/MET → (−23.4222, −46.4795);
  SCI/RFFS → (−23.4348, −46.4606). Label positions, ±~100 m — the OSM
  footprint under the HANGAR LATAM label is the geometry to build.
- **Frame closure.** The four published thresholds, converted exactly, close
  their own declared-distance arithmetic to +4.6 / −6.4 m — inside the
  whole-second rounding. The OSM centrelines close 3700/3000 m to ≤1.5 m and
  are parallel to 0.015°; bearing adopted 073.65 true.
- **DSM building probes** (Copernicus GLO-30, 2011–14 epoch, 12×12 in-polygon
  grids vs a 250 m surround ring): T2 **+14.1 m** (floor), T1 +10.8, TECA
  +8–10, American hangar **+7.2** (floor), **Terminal 3 +0.9 and the LATAM
  hangar +0.9 — i.e. absent: both postdate the DSM.** The one DSM number that
  matters here is a *date*, not a height.
- **Horizon**: ray-scan over both DEMs, refraction k=0.13, observer on the
  published THR 10L elevation + 5 m; scan start 1 500 m except 5 000 m in the
  aerodrome sector 050–120°. Copernicus vs SRTM: 0.033° rms.
- **Wind**: ERA5 2021–2025 hourly, headwind component on track 073.65.

---

## 5. Sources consulted

Primary (all AISWEB/DECEA, quoted as fact, charts not redistributed):
ROTAER SBGR (D-AMDT 26/26); SBGR ADC (SBGR_ADC_02U, AMDT 2605A1); IAC ILS N
10L / ILS M 28R / ILS Q 10R / ILS Y 28L (THR elevations, VAR 22 W); AGMC
DEP 10L/10R/28L/28R + 3ARR 10R; AOC A/B; PDC 1/2/3. URLs in
`sbgr_aip_survey.json`.

Data: OpenStreetMap via Overpass (ODbL); Copernicus GLO-30 + SRTM v3;
ERA5 via Open-Meteo (CC BY 4.0).

Context carried over from the SDSC survey: CNN Brasil's feature on the São
Carlos MRO (777 maintenance at Guarulhos) — recorded in
`../scenario_sdsc/sdsc_aip_survey.json`, not re-fetched here.

---

## 6. What I could **not** establish

1. **The LATAM hangar's appearance, height, door span and exact construction
   year.** No published dimension, no free photograph, no DSM return (it
   postdates the 2011–14 acquisition). Bracketed 2014–2020 by dome photo +
   DSM + OSM way age. Anything phase 2 builds above its OSM footprint is
   declared inference; a 777-300ER is 18.5 m tall and must fit through the
   door.
2. **The eAIP AD 2 SBGR text.** Script-rendered index, not retrievable
   non-interactively this session. It likely carries centisecond thresholds
   and possibly a declared preferential-runway paragraph — both would upgrade
   this survey. The whole-second strings and the chart-set inference stand in
   their place, recorded as such.
3. **The control tower's height and exact footprint.** Not in OSM, no
   published height found. ADC label georef ±100 m + three photographs is all
   phase 2 gets.
4. **Stand/gate allocation** (which stands are LATAM's, where the 777s park
   overnight). The PDCs publish geometry, not airlines.
5. **Whether the '3ARR 10R' AGMC chart means arrivals are 10R-only in east
   flow.** The chart-set asymmetry plus CAT III on 10R plus the
   intersection-departure notes make the north-runway-departs reading strong,
   but no single published sentence states it.
6. **Heights of everything built after 2014** — T3, the LATAM hangar, the
   newest cargo sheds. The DSM predates them; OSM carries 10 height/levels
   tags over 140 buildings.
7. **The 'Pátio 7' duplication** in OSM (south GA block vs east cargo block) —
   left to the PDCs if it ever matters.

---

## 7. Licences and what may be published

Same regime as SDSC: OSM extract and derived meshes **ODbL share-alike**;
Copernicus DEM with the required DLR/Airbus/ESA attribution (full text in
`TERRAIN.md`); SRTM public domain; DECEA data quoted as fact, charts linked
never redistributed; photographs cited in `refs/manifest.json`, fetched on
demand, **never committed** (CC BY-SA share-alike conflicts with the repo's
CC BY 4.0 asset licence). `python3 refs_fetch.py --verificar` is the gate and
exits 0 today.
