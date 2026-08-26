# The terrain — SBGR / Guarulhos

Santiago is a wall, São Carlos is nothing, **Guarulhos is a ring**. The whole
360° horizon from THR 10L sits between **+0.12° and +3.23°** — never negative
(the field is in a shallow bowl), never Andean. The one low sector is
**exactly the departure direction**: ESE, 0.22–0.72°. An aircraft leaving 10L
climbs into the emptiest sky the site has, with the tallest ground —
the Cabuçu spur of the Serra da Cantareira, 3.2° at 5 km — standing directly
behind its own left wing.

Everything here is derived from open elevation data. Nothing is modelled by
hand.

---

## 1. The frame

| | |
|---|---|
| **Origin** | lat **−23.4341667**, lon **−46.4825000** (WGS84) |
| **What that point is** | the published landing threshold of **RWY 10L** — the departure runway's threshold (the roll starts 90 m before it) |
| **Precision warning** | DECEA publishes SBGR thresholds to **whole seconds** (±~30 m). The origin is the published string, exactly; relative geometry comes from the OSM tracing. `sbgr_aip_survey.json → divergences`. |
| **Axes** | x = East, y = North, z = Up. Metres. WGS84 local **ENU** tangent frame |
| **Vertical datum** | **z = 0 at 750.0 m AMSL**, the published SBGR aerodrome elevation (2461 ft) |

Same frame as `sbgr_osm.json` and `lib/frame.py`; `build_osm.py` and
`build_terrain.py` both import it — the SCL two-origins accident stays fixed.

### Earth curvature is baked into z

Grid z is sampled along the local vertical through each node, so a point
60 km out sits ~282 m below the tangent plane before any relief is counted.
New at SBGR: the far tier crosses the **Atlantic coastline** 55–75 km
south-east — the first ocean in this project, and the one surface whose only
shape IS the curvature drop.

### Reference points in the frame

| point | x (m) | y (m) | z (m) | source |
|---|---|---|---|---|
| **THR 10L** (origin) | 0.00 | 0.00 | **−4.76** | published 2445 ft |
| THR 28R | 3 407.02 | 1 014.94 | −5.98 | published 2441 ft |
| THR 10R | −454.22 | −523.05 | −2.94 | published 2451 ft |
| THR 28L | 2 413.20 | 338.25 | −4.46 | published 2446 ft |
| ARP | 965.24 | −153.87 | +0.11 | ROTAER, whole seconds |
| LATAM hangar centre | 2 281.21 | 1 361.74 | — | OSM way/778050745 |
| TWR (label georef) | ~301 | ~1 323 | — | ADC, ±100 m |

**GRU is flat.** Highest published point 2461 ft (the 10R TDZ), lowest
2441 ft (THR 28R): 6.1 m across a 5 km field, runway falls of 1.2 and 1.5 m.
Copernicus and SRTM agree within 1–4 m at all four thresholds. There is no
SDSC-style graded-platform machinery to build — but **z = 0 is the aerodrome
elevation, not the pavement**: the runways sit 3–6 m below it.

---

## 2. The heightfields

Regular grids, **float32 `.npy`**, z in metres above the 750 m datum.
`row 0 = y_min (south)`, `column 0 = x_min (west)`. 16-bit PNG twins,
row-flipped, decode scales in `terrain/terrain_meta.json`.

| file | size | step | extent (km) | z range (m) |
|---|---|---|---|---|
| `terrain/terrain_sbgr_near_30m.npy` | 1001 × 1001 | **30 m** | ±15.0 | −104 .. +604 |
| `terrain/terrain_sbgr_60m.npy` | 1668 × 1668 | **60 m** | ±50.0 | −1 143 .. +651 |
| `terrain/terrain_sbgr_far_180m.npy` | 1334 × 1334 | **180 m** | ±120.0 | −3 012 .. +837 |

The 30 m tier holds the Cantareira crest (+604 m over datum at its corner);
the 60 m tier carries all of Greater São Paulo and the Serra do Mar; the
180 m tier reaches the Mantiqueira (+837) and the Atlantic (−3 012 is the
curvature drop at the plate corner). Nine tiles per DEM (S23–S25 ×
W046–W048), ~950 MB raw, git-ignored; `fetch_dem.sh` reproduces them.

---

## 3. The horizon profile

`terrain/horizon_5deg.json` (72 azimuths), `horizon_fine_0p1deg.csv` (3600),
`horizon_silhouette.png` (drawn, on the SCL scale for comparison).

Method as at SDSC — spherical Earth, refraction k = 0.13, radial step 20 m to
130 km, observer on the **published THR 10L elevation + 5 m** — with **one
structural change**: the scan start is azimuth-dependent. From THR 10L the
aerodrome extends ~4.5 km ESE but <1 km every other way, and this DEM is a
*surface* model: at a uniform 1 500 m start it would report terminal and
hangar roofs as "terrain" precisely where the real terrain horizon (Serra do
Itapety, ~20 km E) is of similar apparent height. So: **1 500 m everywhere,
5 000 m in the 050–120° sector**, and the near-field audit reports what each
exclusion removed, per azimuth.

### What the profile says

| sector | band | what it is |
|---|---|---|
| **N, 325–020°** | **+1.76 .. +3.23°** | the **Cabuçu de Cima spur of the Serra da Cantareira**, 3.7–5 km out, summits 905–1 035 m. The fine profile peaks at **3.23° at az 006**. The tallest thing in any GRU frame. |
| NE, 025–045° | +0.93 .. +1.74° | the Cantareira east ranges toward Itaberaba, 12–18 km, to 1 307 m |
| **ESE, 050–120°** | **+0.22 .. +0.72°** | **the departure direction — the lowest sector.** Down the Baquirivu/Tietê valley; the Serra do Itapety at ~20 km never beats 0.72° |
| S–SSE, 130–185° | +1.49 .. +2.07° | a near ridge only 1.6–1.8 km out (50–60 m above field) — close city hills, not a serra |
| SW, 190–260° | +0.12 .. +0.73° | the second low sector, toward São Paulo proper (the fine minimum, 0.115°, is at az 217) |
| **W–NW, 265–320°** | **+0.80 .. +2.21°** | the **Cantareira main crest** (1 057–1 107 m at 13–14 km) and the Pico do Jaraguá sector |

Two things the numbers rule on:

- **The Mantiqueira is NOT on the horizon.** Its 2 000+ m summits at
  90–110 km NE lose to the near Cantareira ranges at every azimuth.
- **The Atlantic is NOT on the horizon.** The S–SSE near ridge and the Serra
  do Mar block it. The ocean exists only for a high aerial camera, in the far
  tier.

**Near field**: peaks at 2.21° (an object +50 m over the observer — terminal
structures), exceeds the terrain horizon at **16 of 72** azimuths, 10 of them
in the aerodrome sector where the "near field" is the airport itself —
scenery to model, not terrain to sample. Unlike São Carlos (24/72 with
nothing behind), the ring here beats the near field at most azimuths: **the
skyline of GRU is real terrain, and a terrain mesh alone will draw most of
it correctly.** The tree line owed at SDSC is owed here only inside the
050–120° sector and by the city fabric inside 1.5 km.

---

## 4. Checks — `python3 verify.py`

```
1. delivered grid vs full-resolution DEM horizon
   60 m grid alone          mean -0.015  rms 0.027  max|diff| 0.097 deg
   30 + 60 + 180 m stack    mean -0.005  rms 0.018  max|diff| 0.056 deg
2. the ring, sector by sector      (table as in section 3)
3. threshold elevations: published vs Copernicus vs SRTM, spreads 2-5 m,
   both runways' published falls 1.2 / 1.5 m - the field is level
4. geometry: published whole-second strings close their own declared
   distances to +4.6 / -6.4 m; OSM centrelines close 3700/3000 to 1.5 m and
   are parallel to 0.015 deg; true 73.4 + VAR 22 W = 95.4 vs published 095
```

Copernicus vs SRTM horizon: **0.033° rms, 0.123° max** — between Santiago's
0.013 (all far rock) and São Carlos's 0.091 (all near vegetation), which is
what a mixed near-city/far-serra horizon should give.

`prepare_dem.py` despiked **4 px** across nine SRTM tiles (S24W046, in the
Serra do Mar coastal cliffs). Copernicus needed none.

---

## 5. Reproducing

```bash
./fetch_dem.sh            # ~950 MB, both DEMs, 9 tiles each
python3 build_terrain.py  # ~3 min
python3 horizon.py        # ~1 min
python3 silhouette.py
python3 verify.py
```

`prepare_dem.py` reads the Copernicus COGs with **tifffile** (not rasterio),
georef from the tags, asserted against the file name — the SDSC change,
carried over with the tile lists swapped to S23–S25 × W046–W048.

---

## 6. The DSM epoch — the finding that replaces SDSC's platform

At São Carlos the terrain result that changed the scene was the 35 m MRO
platform. Here it is a **date**: Copernicus GLO-30 was acquired 2011–2014,
and over this airport that is *before half of what matters existed*.

| footprint | DSM p90 minus surround | reading |
|---|---|---|
| Terminal 2 | **+14.1 m** | floor on the true height (30 m DSM smears roofs) |
| Terminal 1 | +10.8 m | floor |
| TECA cargo | +8..10 m | floor |
| American Airlines hangar | **+7.2 m** | floor — the OLDER hangar |
| **Terminal 3** (opened 2014) | **+0.9 m** | **absent — under construction during acquisition** |
| **LATAM hangar** | **+0.9 m** | **absent — the hangar postdates the DSM** |

So the DSM *dates* the LATAM hangar (post-2014; the 2013 photograph shows an
inflatable dome on the spot; the OSM ways are ~2020 work) and measures only
the pre-2014 airport. **No structure built after 2014 has any measured height
in this survey.** Phase 2 heights for T3 and the LATAM hangar are inference
and must be declared — the survey's honesty line runs straight through the
two most important buildings.

---

## 7. Sources and licences

**Copernicus DEM GLO-30 (WorldDEM-30)** — primary, 1 arcsec, EGM2008.
AWS Open Data, `https://copernicus-dem-30m.s3.amazonaws.com/`. Licence:
COP-DEM-GLO-30-F Free & Open; modified data, so Article 6(b) applies:

> produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus
> Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European
> Union and ESA; all rights reserved

and Article 6(c) must accompany redistribution:

> The organisations in charge of the Copernicus programme by law or by
> delegation do not incur any liability for any use of the Copernicus
> WorldDEM-30

**SRTM v3 1 arcsec** (NASA/USGS) — control, EGM96, AWS Terrain Tiles skadi
endpoint. Public domain.

**AISWEB / DECEA** — elevations, thresholds, declared distances, VAR. State
aeronautical information, quoted as fact; charts linked, never redistributed.

**ERA5 via Open-Meteo** — `sbgr_operations_wind.json` only. C3S/ECMWF;
Open-Meteo CC BY 4.0.

---

## 8. Known limits

- The DEM is a **surface** model over a metropolis: outside the fence its
  "ground" includes rooftops and trees everywhere. The near ridge SSE and
  parts of the Cabuçu profile carry urban canopy.
- **The DSM epoch (2011–14) predates Terminal 3 and the LATAM hangar** — §6.
  Do not use this terrain to measure anything built after 2014.
- The aerodrome interior in the 050–120° sector was excluded from the terrain
  horizon on purpose; its skyline there is the airport's own buildings.
- The far tier's ocean corner is bathymetry-free (GLO-30 sea surface ≈ 0),
  which is correct for rendering and wrong for anything else.
- `terrain/_fine_profile.npy` is an intermediate and is git-ignored.
