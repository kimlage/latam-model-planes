# The terrain and the Andes — SCL / SCEL

What makes Santiago unmistakable is the **Cordillera de los Andes**: very high and
very close, filling the eastern sky. This directory carries the real elevation of
that ground, in the scene's metric frame, plus the horizon profile that makes the
silhouette recognisable.

Everything here is derived from open elevation data. Nothing is modelled by hand or
estimated by eye.

---

## 1. The frame

| | |
|---|---|
| **Origin** | lat **-33.376099**, lon **-70.786697** (WGS84) |
| **What that point is** | threshold of **RWY 17L** at SCEL — the start of the takeoff roll |
| **Axes** | x = East, y = North, z = Up. Metres. WGS84 local **ENU** tangent frame |
| **Vertical datum** | **z = 0 at 474.0 m AMSL**, the published SCEL aerodrome elevation (1555 ft) |

Departures at SCL run **south on 17/17R** (prevailing southerly wind), so the roll
starts at the north end and the Andes sit off the **left** wing.

### Earth curvature is baked into z — on purpose

The scene is 130 km wide. Over that distance the Earth's curvature is not a rounding
error: a point 90 km away sits **~630 m lower** than a flat plane would put it. Each
grid node's z is the height of the terrain along the local vertical through that
node, so the drop is already in the data. Verified against `d²/2R` to within 1 m.

Drop this terrain on a flat plane instead and the far cordillera stands hundreds of
metres too tall.

### Reference points in the frame

| point | x (m) | y (m) | z (m) |
|---|---|---|---|
| RWY 17L threshold (origin) | 0.0 | 0.0 | -1.6 |
| RWY 35R threshold | 139.1 | -3749.3 | 0.0 |
| RWY 17R threshold | -1582.7 | 465.8 | -1.3 |
| RWY 35L threshold | -1414.6 | -3416.4 | -1.6 |
| Aerodrome reference point | 83.7 | -1874.8 | 0.0 |

17L→35R measures **3751.9 m** in this frame against a published 12,303 ft
(3749.9 m) — 2 m, which is the frame checking out.

> **Note on the shared origin.** `refs/_medidas_osm_local.json`, produced by the
> airport-layout work, uses the same 17L threshold from OSM geometry:
> -33.3760915, -70.7867106. That is **1.4 m** from the origin used here (mine comes
> from the AIP via OurAirports). Both use the same 474 m datum. 1.4 m is 20× below
> the finest terrain grid step, so the terrain is unaffected; anyone needing exact
> agreement should shift by (+1.27 m east, +0.83 m north).

---

## 2. The heightfields

Regular grids, **float32 `.npy`**, z in metres above the 474 m datum.
`row 0 = y_min (south)`, `column 0 = x_min (west)`.

| file | size (cols × rows) | step | extent (km) | z range (m) |
|---|---|---|---|---|
| `terreno/terreno_scl_perto_30m.npy` | 1001 × 1001 | **30 m** | x -15.0..15.0, y -15.0..15.0 | -150 .. 1327 |
| `terreno/terreno_scl_60m.npy` | 2185 × 1671 | **60 m** | x -38.7..92.3, y -47.5..52.7 | -655 .. 5148 |
| `terreno/terreno_scl_longe_180m.npy` | 1445 × 1668 | **180 m** | x -110.0..149.9, y -150.0..150.1 | -3194 .. 5477 |

Three tiers because one grid cannot do both jobs. The 60 m grid covers the
requested box and carries the Andes wall. The 180 m tier exists because **the
southern skyline sits 70–150 km out, far beyond the requested box** — without it the
horizon south of the field is simply missing (see §5). The 30 m tier is the
aerodrome's immediate surroundings.

Each `.npy` has a **16-bit PNG twin** for displacement workflows. The PNG is
row-flipped (row 0 = north) and its decode scale is in `terreno_meta.json`:
`z_m = png/65535 × (z_max − z_min) + z_min`.

All extents, ranges and decode constants: **`terreno/terreno_meta.json`**.

### Building it in Blender

```python
import sys; sys.path.append(".../cenario")
import carregar_terreno as t
t.build_all()
```

Builds all three tiers, each masked so it rings the next without z-fighting, and
raises camera `clip_end` to 250 km — Blender's default 100 m clip hides the entire
scene.

---

## 3. The horizon profile

`terreno/horizonte_5deg.json` — elevation angle of the horizon at every **5° of
azimuth**, 0–355° (72 entries), as required. Each entry also carries the distance,
the summit height, its lat/lon, the no-refraction variant, and the SRTM control value.

`terreno/horizonte_fino_0p1deg.csv` — the same at **0.1°** (3600 entries), for
building the actual silhouette.

`terreno/horizonte_silhueta.png` — the profile drawn, with peaks labelled. **Check
this against a photograph.**

Method: spherical Earth, radius 6 375 397 m (Gaussian at the origin latitude), with
standard atmospheric refraction k = 0.13 (effective radius 7/6 R). Observer on the
runway, eye 5 m up. Radial step 20 m out to 160 km.

**The scan starts at 3 km.** The aerodrome is graded flat — terrain stays within
~20 m of field level out to 3 km, and a *surface* DEM there contains terminal
buildings and radar noise rather than terrain. The excluded near field peaks at
0.621° (its tallest object is +17.6 m above the observer) and **exceeds the mountain
horizon at 0 of 72 azimuths** — so cutting it removes nothing from the silhouette.
That audit is in the JSON, not just this sentence.

### What the profile says

| direction | character |
|---|---|
| **E, 45–125°** | the Andes. Horizon 3.2–4.9°, summits 2500–5400 m at 33–58 km |
| **highest point of the eastern wall** | **4.63° at azimuth 75°** — 5159 m, 55 km |
| **S, ~175°** | the low gap toward Rancagua — horizon drops to **0.50°** |
| **W, 240–320°** | Cordillera de la Costa. Angularly *comparable* to the Andes (up to 4.99° at 255°) because it is only 13–20 km away |

The western range being as angularly tall as the Andes is the non-obvious part, and
it is real: it is close, not high. The Andes read as Andes because they are a
**distant, snow-covered, 5000 m wall**, not because they subtend more sky.

---

## 4. Which peaks appear, and where

`terreno/picos.json` — 85 named summits matched along the skyline (55 confirmed,
11 probable, 19 uncertain), plus explicit line-of-sight tests on the notable ones.

Confidence is graded, not asserted: **confirmed** = gazetteer within 800 m of the
DEM summit and within 60 m in height; **probable** = within 1500 m / 150 m;
**uncertain** = the gazetteer's nearest name does not actually sit on the summit
forming the skyline. Treat *uncertain* names as unnamed summits.

### The eastern skyline, north to south

| azimuth | peak | height | distance |
|---|---|---|---|
| 53.8° | Cordón de los Españoles | 3331 m | 38 km |
| 63.0° | Cerro Negro | 4901 m | 58 km |
| 66.1° | Cerro La Paloma | 4909 m | 53 km |
| 67.5° | Cerro Altar | 5152 m | 55 km |
| 71.7° | Cerro Fickenscher | 5338 m | 56 km |
| **74.0°** | **Cerro El Plomo** | **5425 m** | **55 km** |
| 78.2° | Cerro Bismarck | 4635 m | 56 km |
| 85.0° | Cerro Klatt | 4188 m | 56 km |
| 99.8° | Cerro de la Provincia | 2733 m | 33 km |
| 104.4° | Morro Tambor | 2876 m | 34 km |
| **110.8°** | **Cerro San Ramón** | **3248 m** | **34 km** |
| 117.6° | Morro de las Bayas | 2657 m | 34 km |
| 121.3° | Cerro Tarapacá | 2482 m | 33 km |

**Cerro El Plomo at azimuth 74° is the anchor.** It is the highest point of the
eastern skyline in this computation — and Wikipedia describes it independently as
"the highest peak visible from Santiago". Two DEMs, a gazetteer and an encyclopaedia
agree. If a LATAM employee recognises one thing, it is this summit and the
**Sierra de Ramón** wall at 110°.

### Visible vs blocked

Line of sight tested over the DEM, summit coordinates snapped to the local DEM
maximum first (gazetteer coordinates are up to 700 m off).

**Visible:** Cerro El Plomo (5424 m, az 74°), Cerro Altar (5180 m, 67°),
Cerro Leonera (4954 m, 74°), Cerro La Paloma (4910 m, 66°),
Nevado El Plomo (4841 m, 73°), Cerro Bismarck (4650 m, 77°),
Cerro San Ramón (3253 m, 111°), Cerro El Roble (2222 m, 335°),
Cerro Manquehue (1635 m, 82°), Cerro Renca (905 m, 103°).

**Blocked by the front range** — do not put these on the horizon:
Aconcagua (6961 m), Tupungato (6570 m), Marmolejo (6109 m), Cerro Polleras (5993 m),
Nevado Juncal (5965 m), Volcán San José (5856 m), Tupungatito (5650 m),
Cerro Punta Negra (4548 m), Cerro Provincia (2751 m), Cerro San Cristóbal (880 m).

That the giants are hidden is a real feature of the view from Pudahuel, on the
**western** edge of the basin: the Cordón del Plomo and Sierra de Ramón stand in
front of them. Aconcagua misses by 0.175°, Tupungato by 0.120° — margins of 200–350 m
of intervening ridge, beyond DEM error. Changing the refraction coefficient from 0
to 0.25 (a strong Santiago inversion) moves these margins by only ~0.03°, so the
conclusion is not an artefact of the refraction assumption. Every margin and its
sensitivity is in `picos.json`.

---

## 5. Checks

Nothing above is asserted without a check. These are reproducible via `verificar.py`.

**The required sanity check.** Aerodrome reads **472.0 m** (Copernicus) and
**478.2 m** (SRTM) against a published **474.0 m** — a ±4 m spread, normal for a
surface model over a built-up airfield. Peaks east exceed 5000 m: highest node in
the required box is **6047.7 m** at 74 km. ✔

**Two independent DEMs.** The horizon computed from Copernicus GLO-30 and from
despiked SRTM v3 agree to **0.013° rms, 0.049° max** across all 72 azimuths.

**Known summits.** Aconcagua reads 6916 m (Cop) / 6940 m (SRTM) against an accepted
6961 m. Tupungato reads **6573 m in both** against an accepted 6570 m.

**The delivered grid, not just the source data.** Ray-casting the actual
heightfields reproduces the DEM-derived horizon to **0.028° rms, 0.062° max**
(east sector 0.027° rms). This check is what exposed the missing southern
skyline — the 60 m grid alone was wrong by up to **0.979°** at azimuth 165°,
because the horizon there is 147 km away and the requested box stops at 47 km.
The 180 m far tier fixed it.

**A third, independent skyline.** `refs/_skyline_leste_dem.csv`, computed separately
by the airport-layout work, agrees with this one over 40–140° to **0.096° rms**
(max 0.242°). This profile runs ~0.06° higher on average, consistent with its finer
radial sampling catching crests the coarser scan steps past.

### SRTM had to be despiked

Raw SRTM v3 carries isolated single-pixel spike/pit pairs over water — a **+5844 m**
pixel sitting on a **−6900 m** pixel, surrounded by 3–20 m sea level, 150 km NNW of
the field. Left in, they inject a fake alpine peak into the skyline. 198 such pixels
were removed across the 12 tiles (3×3 median, 200 m threshold); afterwards the
coastal maximum reads 2405 m against Copernicus's 2406 m. Copernicus is clean and is
therefore the primary source; SRTM is the control.

---

## 6. Reproducing

```bash
./fetch_dem.sh            # downloads both DEMs (~900 MB), normalises, despikes
python3 build_terreno.py  # heightfields + metadata
python3 horizonte.py      # horizon profiles, both DEMs
python3 picos.py          # peak identification + line-of-sight
python3 silhueta.py       # the silhouette drawing
python3 verificar.py      # checks in §5
```

Raw DEM tiles are **not committed** (~1.5 GB); `fetch_dem.sh` reproduces them byte
for byte. `prepare_copernicus()` needs `rasterio` — use a venv, do not install it
into the base environment (it forces a numpy major-version upgrade).

---

## 7. Sources and licences

**Copernicus DEM GLO-30 (WorldDEM-30)** — primary elevation source, 1 arcsec,
EGM2008 orthometric. Downloaded from the AWS Open Data registry,
`https://copernicus-dem-30m.s3.amazonaws.com/`.
Licence: *Licence for Copernicus DEM instance COP-DEM-GLO-30-F Global 30m Full,
Free & Open* — worldwide, unlimited in time, free of charge, and expressly granting
reproduction, distribution, communication to the public, and **adaptation or
modification**. The data here is modified (resampled and reprojected), so Article
6(b) applies:

> produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence
> and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA;
> all rights reserved

And Article 6(c), which must accompany any redistribution:

> The organisations in charge of the Copernicus programme by law or by delegation do
> not incur any liability for any use of the Copernicus WorldDEM-30

Licence text: https://docs.sentinel-hub.com/api/latest/static/files/data/dem/resources/license/License-COPDEM-30.pdf

**SRTM v3 1 arcsec (NASA / USGS)** — independent control DEM, EGM96 orthometric.
Downloaded from the AWS Terrain Tiles open dataset,
`https://s3.amazonaws.com/elevation-tiles-prod/skadi/`.
Licence: **public domain** — NASA/USGS SRTM data carries no use restrictions.

**OurAirports** — SCEL runway thresholds, headings, elevations, aerodrome reference
point. `https://davidmegginson.github.io/ourairports-data/`.
Licence: **public domain** (dedicated by the OurAirports project).

**GeoNames** — peak names and elevations (Chile and Argentina country dumps).
`https://download.geonames.org/export/dump/`.
Licence: **CC BY 4.0** — attribution: *"this product uses data from GeoNames
(https://www.geonames.org), licensed under CC BY 4.0"*.

**OpenStreetMap** — peak and volcano names, via the Overpass API.
Licence: **ODbL 1.0** — attribution: *"© OpenStreetMap contributors"*. Derived
outputs distributed from this data are subject to ODbL share-alike.

The merged gazetteer is `refs/gazetteer.json`, with a `src` field on every entry
recording which of the two it came from.

**Wikipedia** — used only to cross-check Cerro El Plomo's elevation and its standing
as the highest peak visible from Santiago. Not used as geometry.
Licence: CC BY-SA 4.0. https://en.wikipedia.org/wiki/Cerro_El_Plomo

---

## 8. Known limits

- The DEM is a **surface** model: over Santiago it includes buildings, and over the
  aerodrome it reads 472–478 m instead of a graded-flat 474 m. Whoever lays the
  runway and apron should **flatten the airport platform** rather than sit it on
  this terrain — the near-field grid is honest terrain data, not a graded aerodrome.
- No snow, rock, vegetation or atmosphere here — this is geometry only. The Andes
  read as the Andes largely through **snow line and aerial perspective**; that is a
  shading job on top of this mesh.
- 19 of the 85 skyline name matches are graded *uncertain* and should be treated as
  unnamed summits.
- The far tier is capped at 110 km to the west by DEM tile coverage; beyond that is
  the Pacific, filled at sea level. This is correct for the ocean and irrelevant to
  the silhouette.
- OurAirports gives 17R/35L as 12,303 ft, but its own threshold coordinates are
  3886 m apart — a ~136 m inconsistency in that record. It does not affect the
  terrain; flagged for whoever builds the runways.
