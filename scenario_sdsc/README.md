# SDSC / São Carlos — the LATAM MRO base

**Phase 1: data only.** Nothing here is modelled. This folder is the survey, the
geometry and the reference material that a build phase will consume — the same
contents `../scenario/` carries for Santiago, produced the same way, named the same
way, so anyone who knows one knows the other.

The target is **LATAM MRO São Carlos**, on **Aeroporto Estadual Mário Pereira Lopes
(SDSC / QSC)**, Água Vermelha, São Carlos/SP: LATAM's heavy-maintenance base, nine
hangars, 22 workshops, ~2 000 people, ~270 aircraft a year, and **hangar 9**,
inaugurated 26 September 2025 for Boeing 787 heavy maintenance.

```
scenario_sdsc/
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

Reproduce the whole thing:

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

### Anchors phase 2 will want

Not built yet — no `.blend` exists. When it is, mirror
`../scenario/`'s `SCL_Anchors`: Empties whose **+Y points down the take-off track**.

| anchor | position (x, y, z) | track |
|---|---|---|
| `SDSC_02_Threshold` | (0.00, 0.00, −2.33) | 001.026° true — **departures** |
| `SDSC_20_Threshold` | (29.00, 1619.72, −12.39) | 181.026° true |
| `SDSC_LATAM_MRO` | (912.5, 1608.9, ~−37) | — |

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
| MRO platform | ~770 m AMSL, ~35 m below THR 02 | Copernicus, SRTM agrees ±4 m |
| Wind favouring RWY 02 | 53.4% all hours, **63.2%** in AD opening hours | ERA5 2021–2025 |
| Solar geometry | see `sdsc_operations_sun.json` | computed here (NOAA algorithm) |

**Zero of the 95 building footprints carries a `height` tag, and none carries
`building:levels`.** Santiago had 4 heights and 42 level counts out of 748. Here there
is nothing. Every building height in phase 2 will be an estimate except the one above.

### Estimated by me — do NOT quote these as data

Almost nothing is estimated here, because phase 1 deliberately did not model. What
**is** inference, and is flagged as such in the files:

- **The reading of the declared distances.** LDA = 1720 − own displacement; TORA =
  1720 − *far* end's displacement; ASDA = 1720. That pattern is what you get if the
  end 48/52 m count as stopway as well as displacement. **DECEA publishes no
  stopway/clearway declaration for SDSC.** The arithmetic is published; the reading
  is mine. Either way the usable take-off run is **1 672 m**.
- **The pavement ends.** Derived by walking the published thresholds back along the
  measured track by the published displacements. DECEA publishes thresholds and
  displacements, not ends.
- **That `relation/7422965` is the hangar line.** It is 471 × 137 m and tagged only
  `building=yes`. Whether it is the hangars, the workshop spine, or both, is not
  established.
- **The MRO platform level.** Measured from a 30 m DSM, agreed by two DEMs, but a
  graded industrial platform is exactly what a 30 m DSM can get wrong. Scene-defining
  and unconfirmed.
- **The western rise.** ~845 m at 1–3 km west, ~40 m above the field. Both DEMs are
  *surface* models, so part of that may be eucalyptus or cane canopy rather than
  ground; they cannot be separated at 30 m.
- **RWY 02 as the departure end.** Nothing forces it — SDSC is VFR with AFIS, not an
  ATC flow, and both ends have RNP approaches. Wind (63.2% in opening hours), slope
  (downhill) and TORA (4 m longer) all lean the same way. It is a well-supported
  choice, not a published rule.

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

## 4. The z-stack for phase 2

Not built yet, but the stack that stops coplanar surfaces z-fighting is the same one
Santiago proved, shifted onto this field's datum. **Note the runway is sloped**, so
these offsets are *relative to the runway surface at each station*, not absolute z:

```
 +0.12  runway markings
 +0.09  runway pavement       (surface: −2.33 at THR 02, −12.39 at THR 20)
 +0.07  runway shoulders
 +0.06  taxiways              (+0.09 for the yellow centrelines)
 +0.05  aprons, parked aircraft
  0.00  aerodrome ground
 -0.40  field surround
 -0.80  terrain, flattened over the aerodrome strip and blended back to the DEM
```

Two SDSC-specific warnings:

- **Do not flatten the runway strip to a single z.** Flatten it to the *published
  threshold elevations interpolated along the centreline*, and blend out from there.
- **Do not flatten the MRO platform to runway level.** It is 25–35 m lower and the
  ground genuinely falls ~40 m/km eastward. That fall is real terrain, not DEM error.

---

## 5. Licences — read before publishing anything built from here

| source | covers | obligation |
|---|---|---|
| **OpenStreetMap**, via Overpass | every footprint, taxiway, apron and the runway centreline in `sdsc_osm.json`, and therefore most of any mesh built from it | **ODbL 1.0**. Attribution *"Airport geometry © OpenStreetMap contributors, ODbL 1.0"* **and share-alike**: a derived database, which includes a mesh generated straight from it, must be published under ODbL. |
| **Copernicus DEM GLO-30** (primary), **SRTM v3** (control) | `terrain/*.npy`, `terrain/*.png` | Copernicus: free use with attribution to © DLR e.V. 2010-2014 / © Airbus Defence and Space GmbH 2014-2018, ESA-funded — full text in `TERRAIN.md` §7. SRTM: public domain (NASA/USGS). |
| **AISWEB / DECEA (ICA)** | the runway survey, declared distances, magnetic variation, threshold elevations, frequencies, hours | Brazilian State aeronautical information, quoted as fact. **Charts are NOT redistributed** — only the numbers and the URLs. |
| **ERA5 via Open-Meteo** | `sdsc_operations_wind.json` | ERA5: Copernicus C3S / ECMWF, free use with attribution. Open-Meteo data: **CC BY 4.0**. |
| **Wikimedia Commons photographs** | the appearance of the hangars, the apron, the interiors, the ground | CC BY-SA 3.0 / 4.0 and **GFDL 1.2** per `refs/manifest.json`. **Git-ignored** — share-alike conflicts with this repo's asset licence. MARCO AURÉLIO ESPARZ (8 of 13) and Renato Spilimbergo Carvalho (3) carry this survey and deserve named credit. |
| **LATAM / Aeroflap / CNN Brasil / Rede Voa / aeroin press** | figures about the base and hangar 9 | All rights reserved. **Read for numbers only; nothing downloaded, nothing usable as an asset.** |
| **LATAM brand** | anything the buildings carry | Trademark. Depiction of LATAM's own base; not a licence to reuse the marks. |

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

`sdsc_osm_plan.png` is the plan check: when phase 2 renders an orthographic top-down
of the built field, put the two side by side. If the plan does not match, the build is
wrong. `terrain/horizon_silhouette.png` is the horizon check — and the thing to check
about it is that it stays **empty**.

`python3 refs_fetch.py --verificar` must exit 0: every manifest entry carries URL,
author and licence, and no photograph is tracked by or exposed to git.

---

## 7. What phase 2 will need to decide

Ordered by how much damage getting it wrong does.

1. **Where hangar 9 is, and how big.** The whole 2025 story is a building with **no
   published dimension and no OSM footprint** (`sdsc_references.md` §6.2). It must be
   located and sized from imagery, or the scene must honestly show the pre-2025 base.
   **It cannot be invented.**
2. **What the base looks like in LATAM colours.** Every free-licence photograph is
   TAM-era (2006–2014). Indigo/coral, the current wordmark, or nothing — unconfirmed.
3. **Which OSM polygon is which hangar**, and how to reconcile LATAM's nine with OSM's
   four-on-site. Do not force the counts.
4. **Whether the MRO platform really is ~35 m below the runway.** Measured, agreed by
   two DEMs, unconfirmed by photograph.
5. **Every building height.** There is exactly one measurement (+12.9 m, a floor) and
   zero published or tagged heights. Santiago's estimate table is the model: declare a
   range, name the reasoning, and mark it *estimated*.
6. **The runway markings.** SDSC has no ADC, so threshold stripes, aiming point, TDZ,
   centreline and side stripe are all unpublished. Either measure them off imagery or
   apply the ICAO Annex 14 pattern for a 45 m code-C/D runway and label it an estimate.
7. **The aircraft type for the clip.** See below — this is decided, but the *weight*
   is not: a widebody leaving SDSC is a ferry flight and must look like one.
8. **A tree line.** At a third of all azimuths the real horizon is vegetation inside
   1.5 km. A terrain mesh alone will render a horizon that is too low and too clean.

### Which LATAM types can operate from this runway

Full evidence in `sdsc_aip_survey.json` → `which_latam_types_can_operate_here`.
The field is **short, hot and high at once**: TORA **1 672 m** (02) / 1 668 m (20),
elevation 2 648 ft, and a 30 °C afternoon is ISA+20 — a density altitude near 5 000 ft.

| type | operates here? | evidence |
|---|---|---|
| **A319 / A320 / A321, ceo and neo** | **yes, routine** | the base's core workload; hangar 9 alone takes three A320s at once |
| **767-300ER / 767-300F** | **yes, routine** | listed by LATAM among the types maintained here; a TAM widebody is in the 2013 reference photograph |
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
