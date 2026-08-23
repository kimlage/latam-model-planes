# The terrain — SDSC / São Carlos

What makes Santiago unmistakable is the Cordillera. What makes São Carlos
unmistakable is that **there is nothing on the horizon at all**.

That is not an impression, it is a measurement. The entire horizon band around
SDSC — all 360° of it — spans **−0.32° to +1.30°**. At SCL the eastern wall alone
occupies 3.2° to 4.9°. `terrain/horizon_silhouette.png` plots SDSC on the same
vertical scale Santiago uses, and the top panel is the point: the band where the
Andes live is empty.

Everything here is derived from open elevation data. Nothing is modelled by hand.

---

## 1. The frame

| | |
|---|---|
| **Origin** | lat **−21.8818417**, lon **−47.9039639** (WGS84) |
| **What that point is** | the published landing threshold of **RWY 02** — where a 02 take-off roll lines up |
| **Axes** | x = East, y = North, z = Up. Metres. WGS84 local **ENU** tangent frame |
| **Vertical datum** | **z = 0 at 807.0 m AMSL**, the published SDSC aerodrome elevation (2648 ft) |

Same frame as `sdsc_osm.json` and `lib/frame.py`. Unlike the Santiago pair, which
ended up 1.51 m apart and had to be reconciled, **there is one origin here and both
deliverables were built from `lib/frame.py` directly.**

### Earth curvature is baked into z — and here it matters *more*, not less

The scene is 240 km wide. Each grid node's z is the height of the terrain along the
local vertical through that node, so the curvature drop is already in the data:
a point 60 km out sits **~282 m** below the tangent plane.

At Santiago the reason was that a flat plane makes the far cordillera stand hundreds
of metres too tall. At São Carlos the reason is sharper: **on a plateau with no relief,
the curvature drop IS the horizon.** Every negative number in the profile below —
which is most of them — is curvature, not topography. Drop this heightfield on a flat
plane and the ground 60 km away becomes a wall at eye level, and the field acquires a
horizon it does not have.

### Reference points in the frame

| point | x (m) | y (m) | z (m) | source |
|---|---|---|---|---|
| **THR 02** (origin) | 0.00 | 0.00 | **−2.33** | published 2640 ft |
| **THR 20** | 29.00 | 1 619.72 | **−12.39** | published 2607 ft |
| south pavement end | −0.93 | −51.99 | — | derived (THR 02 − 52 m) |
| north pavement end | 29.86 | 1 667.71 | — | derived (THR 20 + 48 m) |
| ARP | 65.20 | 603.77 | +0.11 | ROTAER, whole seconds |
| aerodrome beacon | −509.0 | 511.5 | — | ROTAER note [1] |

**z = 0 is the aerodrome elevation, not the runway surface.** The runway is not
level: it falls **10.06 m over the 1 620 m between thresholds**, 0.62%, downhill
toward 20. Copernicus independently reads a 12.0 m fall. Build it flat and the far
threshold is wrong by roughly the height of an A320's tail.

THR 02 → THR 20 measures **1 619.98 m** in this frame against a published
1720 − 52 − 48 = **1 620 m**. 2 cm. The frame checks out.

---

## 2. The heightfields

Regular grids, **float32 `.npy`**, z in metres above the 807 m datum.
`row 0 = y_min (south)`, `column 0 = x_min (west)`.

| file | size (cols × rows) | step | extent (km) | z range (m) |
|---|---|---|---|---|
| `terrain/terrain_sdsc_near_30m.npy` | 1001 × 1001 | **30 m** | ±15.0 | −308 .. +110 |
| `terrain/terrain_sdsc_60m.npy` | 1668 × 1668 | **60 m** | ±50.0 | −640 .. +165 |
| `terrain/terrain_sdsc_far_180m.npy` | 1334 × 1334 | **180 m** | ±120.0 | −2 586 .. +164 |

Three tiers, mirroring Santiago's structure so the two projects read the same way —
but doing a different job. The 30 m tier is the aerodrome and its surround (the only
part with any visible shape). The 60 m tier carries the ground texture out to where
haze takes over. The 180 m tier exists to carry the plate **down and away**, not to
carry a skyline.

Each `.npy` has a **16-bit PNG twin** for displacement workflows, row-flipped
(row 0 = north), with its decode scale in `terrain/terrain_meta.json`.

Total committed: **21 MB** of `.npy` plus **8 MB** of PNG. The raw tiles
(~770 MB downloaded, ~1.4 GB once normalised) are git-ignored; `fetch_dem.sh`
reproduces them.

---

## 3. The horizon profile

`terrain/horizon_5deg.json` — elevation angle of the horizon at every **5°** of
azimuth (72 entries), each with distance, summit height, lat/lon, the no-refraction
variant, the SRTM control value, **and two extra columns Santiago does not have**:
`near_field_elev_deg` and `near_field_dist_km`.

`terrain/horizon_fine_0p1deg.csv` — the same at 0.1° (3600 entries).
`terrain/horizon_silhouette.png` — the profile drawn. **Check it against a photograph.**

Method: spherical Earth, Gaussian radius at the origin latitude, standard refraction
k = 0.13, radial step 20 m out to 130 km.

### The observer height is published, not DEM-derived — and that is a change from Santiago

Santiago took the observer height from the median DEM height over a 1.5 km disc,
because the field there is graded flat over that whole disc. **SDSC is not.** The
runway itself falls 10 m, and the ground keeps falling east and north; a 1.5 km
median lands **12 m below the threshold** and would lift the entire horizon by
0.1–0.3°. On a field whose whole horizon band is 1.6° wide, that is not a rounding
error — it is 20% of the answer. So the observer stands on the **published THR 02
elevation, 804.7 m, plus 5 m of eye height**. Both DEMs read within 2.5 m of the
published value *at* the threshold, so the same height is used for both and the
Copernicus-vs-SRTM comparison stays about profile shape rather than datum.

### The scan starts at 1 500 m, and here that split is not cosmetic

1 500 m clears the aerodrome boundary. But at Santiago the excluded near field
"exceeds the mountain horizon at **0** of 72 azimuths" — it never mattered. Here the
near field (60 m – 1.5 km) peaks at **1.455°** and **exceeds the terrain horizon at
24 of 72 azimuths**. A third of this field's visible horizon is hangars, tree lines
and masts, not terrain. Read that number before deciding the far terrain matters.

### What the profile says

| direction | character |
|---|---|
| **N, 330–030°** | the ground **falls away** steadily — 806 m at the threshold, 763 m at 4 km, 662 m at 12 km, 580 m at 23 km. Horizon **−0.32° to −0.10°** — below eye level. This is the direction a RWY 02 departure climbs into: nothing but sky and falling ground. |
| **E, 060–105°** | flat to barely rising, **−0.17° to +0.19°**. The MRO is in this sector, and you look slightly **down** at it. |
| **S, 120–210°** | the only sustained *positive* sector: **−0.02° to +0.48°**, summits 860–945 m at 9–21 km. This is the land rising toward **São Carlos city** (~856 m, 12 km south). |
| **W, 245–300°** | **+0.03° to +1.30°** — **the one real feature**: a low rise **1.0–3.0 km west of the runway, reaching ~845 m** — about 40 m above the threshold — subtending up to **1.30°**. Beyond it the ground collapses to 670–720 m by 5–11 km: the plateau edge falling into the **Córrego da Matinha ou da Aparecida** (nearest point 1.77 km WSW) and beyond it the **Rio Chibarro** valley (5.5 km WSW). |

**The western rise is the only relief a camera will ever notice at SDSC**, and it is
behind an aircraft departing 02 as seen from the east. Both DEMs agree on it
(Copernicus 845.0 m, SRTM 848.1 m at 1.4 km due west). Note that both are *surface*
models, so part of that 40 m may be eucalyptus or cane canopy rather than ground —
they cannot be separated at 30 m.

There are **no named peaks**. Santiago's `peaks.py` / `peaks.json` have no analogue
here and none was built: matching gazetteer names to a horizon that is 1.6° tall
would be theatre.

---

## 4. Checks — `python3 verify.py`

**Aerodrome elevation.** Copernicus reads **806.0 m** and SRTM **807.2 m** at
THR 02, against a published **804.7 m** threshold / 807.0 m aerodrome elevation.
A 2.5 m spread. The datum is confirmed. ✔

**The runway slope, independently.** Copernicus reads 806.0 at THR 02 and 794.0 at
THR 20 — a 12.0 m fall against a published 10.06 m. Same sign, same order, from a
completely different source. SRTM is the outlier at THR 20 (783.2 m, 11.4 m low).

**The delivered grid, not just the source data.** Ray-casting the actual heightfields
reproduces the DEM-derived horizon to:

| | mean | rms | max |
|---|---|---|---|
| 60 m grid alone | −0.011° | 0.030° | 0.126° |
| 30 + 60 + 180 m stack | −0.004° | **0.011°** | **0.043°** |

**Two independent DEMs.** Copernicus vs SRTM: **0.091° rms, 0.266° max** over all 72
azimuths. Santiago's equivalent was 0.013° rms. **Do not read that as this survey
being ten times worse** — it is the same absolute noise floor measured against a
horizon that is 3° tall instead of 5°, and it comes almost entirely from the sectors
where the "horizon" is vegetation at 1.5–3 km rather than terrain at 30–60 km. But it
does mean the honest statement is: **at SDSC the horizon is not well determined by
DEM, because it is not made of terrain.**

**No despiking was needed.** Prepare_dem removed **0** spike pixels across all 12
SRTM tiles. Santiago needed 198 removed, all over water; there is no water here.

---

## 5. Reproducing

```bash
./fetch_dem.sh            # downloads both DEMs (~770 MB), normalises
python3 build_terrain.py  # heightfields + metadata     (~2 min)
python3 horizon.py        # horizon profiles, both DEMs (~40 s)
python3 silhouette.py     # the silhouette drawing
python3 verify.py         # the checks in §4
```

Raw DEM tiles are **not committed**; `fetch_dem.sh` reproduces them byte for byte.

**`prepare_dem.py` here uses `tifffile`, not `rasterio`.** Santiago's version needs
rasterio to read the Copernicus COGs, and rasterio is not installed in this
environment — installing it forces a numpy major-version upgrade across the whole
project, which the Santiago README already warns about. A GLO-30 tile is a plain
tiled, deflate-compressed float32 GeoTIFF; `tifffile` reads it directly, and the
georeference is read off `ModelTiepointTag` / `ModelPixelScaleTag` rather than
trusted from the file name (and asserted against the name, which caught nothing but
would have).

Tiles: **S21–S23 × W047–W050**, twelve of each DEM, covering ~120 km around the field.

---

## 6. The MRO platform — a terrain result, not a scenery one

Sampling the 30 m grid over the MRO block gives something that changes the scene:

| point | m AMSL |
|---|---|
| runway centreline, y = 0 (THR 02) | 806.0 |
| runway centreline, y = 1600 | 793.0 |
| MRO apron centroid (916, 1882) | **770.2** |
| MRO block, east edge (x ≈ 1400) | **~745–760** |

The ground falls roughly **40 m per kilometre eastward** from the runway into the
córrego valley, and the base sits on the low ground — **~35 m below THR 02 and ~25 m
below THR 20**. From the runway you look slightly **down** at the hangars.

This is measured and both DEMs agree, but it is **unconfirmed against a photograph or
a levelling survey**, and it is exactly the kind of thing a 30 m DSM can get wrong
over a graded industrial platform. Phase 2 should check it before building.

> **Phase 2 checked it, and it stands.** Sampled properly rather than at a point,
> the apron polygon gives a **median of 769.9 m over 348 grid points, p10–p90
> 769.3–771.3** — a 2 m spread over 35 729 m², which is a graded platform, not
> noise. 34.8 m below the published THR 02.
>
> `refs/mro_centro_tecnologico_2009.jpg` agrees independently: that camera sits at
> (498, 2094) where the grid reads 762.4 m, and the photograph shows the hangar line
> standing on an embankment **above** the cane field with the buildings' feet hidden
> behind the bank — which is what an 8 m rise looks like from there.
>
> And the one frame that appeared to contradict it does not, because it is not of
> the MRO: see `sdsc_references.md` §2.1. The sight line from the SP-318 to the base
> is **blocked by the runway crest** — the runway surface is 796 m where that line
> crosses it and the road is at 792.6 m — so from the west of this field the LATAM
> MRO cannot be seen at all. `render_checks.py ground` renders that as a deliberate
> negative check, `ground_sp318_from_west.png`.
>
> `build_scenery.py` therefore grades the aerodrome to a **function**, not a
> constant: the published runway slope over the strip, 769.9 m over the MRO,
> 795.9 m over the mid-field apron, 804.9 m at the Aeroclube, and the raw DEM
> between. The terrain mesh is pushed onto the same function before it is blended
> back out. Flattening this aerodrome to one z would put the MRO 35 m in the air.

One building *is* resolvable at 30 m: `relation/7422965`, 471 × 137 m, reads
**+12.9 m** above its platform (p90 +10.6 m) across 54 distinct grid cells. Because a
30 m DSM smears roof edges inward, that is a **floor** on the true ridge, not the
ridge. Every other building on the site is under ~90 m wide and returned 0.0–5.2 m,
which is smearing, not architecture.

---

## 7. Sources and licences

**Copernicus DEM GLO-30 (WorldDEM-30)** — primary elevation source, 1 arcsec,
EGM2008 orthometric. AWS Open Data registry,
`https://copernicus-dem-30m.s3.amazonaws.com/`.
Licence: *Licence for Copernicus DEM instance COP-DEM-GLO-30-F Global 30m Full, Free
& Open* — worldwide, unlimited in time, free of charge, expressly granting
reproduction, distribution, communication to the public and **adaptation**. The data
here is modified (resampled and reprojected), so Article 6(b) applies:

> produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence
> and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA;
> all rights reserved

and Article 6(c), which must accompany any redistribution:

> The organisations in charge of the Copernicus programme by law or by delegation do
> not incur any liability for any use of the Copernicus WorldDEM-30

**SRTM v3 1 arcsec (NASA / USGS)** — independent control DEM, EGM96 orthometric,
via the AWS Terrain Tiles `skadi` endpoint. **Public domain.**

**AISWEB / DECEA** — aerodrome elevation, threshold coordinates and elevations,
declared distances, magnetic variation. Brazilian State aeronautical information,
quoted as fact. Charts are **not** redistributed — only numbers and URLs.

**ERA5 via Open-Meteo** — used only in `sdsc_operations_wind.json`, not in the
terrain. ERA5: Copernicus Climate Change Service / ECMWF. Open-Meteo data: CC BY 4.0.

---

## 8. Known limits

- The DEM is a **surface** model. Over the MRO it includes the hangar roofs (which is
  how the one measured building height was obtained) and over the surround it includes
  eucalyptus and sugar cane. The western rise in §3 may be partly canopy.
- **No snow, rock, vegetation or atmosphere here** — geometry only.
- **The visible horizon at SDSC is vegetation and buildings, not terrain**, at a third
  of all azimuths. A terrain mesh alone will render a horizon that is *too low and too
  clean*. Whoever builds the scene owes it a tree line.
- The aerodrome platform is graded and this grid is **honest terrain data**, not a
  graded aerodrome: it carries the real 10 m runway slope and the fall into the
  córrego. Flatten the runway strip to the published threshold elevations rather than
  sitting it on the DEM, but do **not** flatten the MRO platform to runway level.
- The far tier stops at 120 km, well beyond anything visible on this plateau.
- `terrain/_fine_profile.npy` is an intermediate and is git-ignored.
