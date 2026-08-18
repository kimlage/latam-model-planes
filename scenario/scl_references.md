# SCL — photographic validation of the LATAM base in Santiago

Photographic and dimensional survey of **Aeropuerto Internacional Comodoro Arturo
Merino Benítez (SCL / SCEL)**, Pudahuel, Santiago de Chile, for building the take-off
scene. The yardstick the owner set is that a LATAM employee who works there every day
should recognise the place — so every claim below is tied to a photograph I opened and
looked at, or to a geographic datum, and whatever I could **not** confirm is marked as
such.

Survey date: 2026-08-18.

> **Runway warning, added after the sceptic's review.** Section 1 below asserts that the
> departure is from **17L**. **That is wrong** — AIP-CHILE AD 2 SCEL §1.2 assigns
> 17L to arrivals and **17R to departures**; the 17L departure is only the 00:00–07:00
> noise-abatement exception. Everything in §1 that says "on the right" is therefore
> mirrored: on a 17R departure every named feature is on the **LEFT**. See
> `RECOGNITION.md` §1 and `scl_operations.md` §1. The rest of this document — shapes,
> colours, materials, positions in the local frame — is unaffected, because it is
> expressed in the frame, not relative to the aircraft.

---

## 1. Reference frame adopted

| item | value |
|---|---|
| origin | **lat −33.3760915, lon −70.7867106** — the threshold of runway **17L**, i.e. the point where the take-off roll starts |
| axes | x = east, y = north, z = up, in metres |
| local scale (computed, not approximated) | 1° lat = **110 911.1 m**; 1° lon = **93 054.7 m** at the origin latitude |
| aerodrome elevation | **474 m** AMSL (SRTM at the point gives 482 m) |

Why 17L and not 17R: at SCL the operation is predominantly southbound (southerly wind),
and runways 17L/17R are the preferred ones for departure. The OPSGROUP operational
briefing further records that, because of the night noise restriction,
**departures use 17L, not 17R**. Since 17L is the *eastern* runway and the whole complex
(maintenance base, tower, T1, T2) sits **between the two runways**, on a 17L departure the
entire base parades past on the **right** of the aircraft. That is what makes the scene work.

*(Superseded — see the warning at the top of this file. The departure is from 17R and
everything passes on the left.)*

### What goes past on the right during the roll

Projected onto the 17L axis (track **177.40°**), measured from the threshold. "Offset" is the
perpendicular distance from the axis. **Everything is on the right** — confirmed by
calculation, not by impression.

| point in the roll | feature | lateral offset |
|---|---|---|
| 58 m | Hangar A of the FACh base | 578 m to the right |
| 159 m | Torre de Control FACh (15 m tall) | 578 m to the right |
| 1 222 m | **LATAM** hangar | 683 m to the right |
| 1 245 m | **Plataforma LATAM** (centre) | 618 m to the right |
| 1 282 m | **Base de Operaciones y Mantenimiento LATAM Airlines** | 719 m to the right |
| 1 746 m | **DGAC control tower** (65 m) | 756 m to the right |
| 2 243 m | Terminal 1 Nacional | 771 m to the right |
| 2 770 m | Terminal 2 Internacional | 762 m to the right |
| 3 204 m | threshold 35R (usable end in the opposite direction) | — |

An A320 typically rotates between 1 600 and 2 000 m of roll: **the aircraft leaves the
ground practically abeam the control tower**, with the LATAM base already behind and
Terminal 1 starting to appear. Worth using in the animation.

---

## 2. Photograph table

All the images below are in `refs/`, all under a free licence (CC0 / CC BY / CC BY-SA),
**all redistributable** provided attribution is kept. `refs/manifest.json` carries the
machine-readable record (page URL, original file URL, author, licence, date, dimensions).

> No restrictively licensed photograph (JetPhotos, Planespotters, LATAM press) was
> downloaded into the repository. Where I needed to look at material like that, it is
> cited as a consultation in §6 and was **not** copied here.

### 2.1 Hangars and maintenance base

| file | author / licence | date | what it validates exactly |
|---|---|---|---|
| `hangar_sky_2021.jpg` | Corsario CL, CC BY-SA 4.0 | 2021-07-21 | Interior of a hangar at SCL seen from inside with the door open: **exposed dark steel truss structure**, chords and diagonals, high-bay luminaires hung from the trusses, very shallow gable roof profile. And, across the ramp, **the illuminated LATAM sign at night** (enlarged crop in `refs/_detalhe_letreiro_latam_noite.jpg`, same author and licence). |
| `hangar_sky_2021_b.jpg` | Corsario CL, CC BY-SA 4.0 | 2021-07-21 | Same hangar, A320 inside: gives the **bay × aircraft scale** — an A320 (37.6 m) occupies a bay with comfortable clearance. |
| `latam_a320neo_landing_scel_2025.jpg` | Robert Motecinos Holda, **CC0** | 2025-08-31 | LATAM A320 CC-BAC landing at SCEL with **a hangar right behind it**: roof in a **shallow arch (a continuous curve, not a gable)**, cladding in light grey ribbed metal sheet, white fascia/flashing following the curve of the roof. It also gives the palette of the range behind. *I could not identify which building it is* — see §7. |
| `fach_base_2010_phillipc.jpg` | Phillip Capper, CC BY 2.0 | 2010-12-28 | The FACh base at the far north end of the field: **gable hangars in dark navy sheet metal**, light fascias, red-ochre earth in front, low brown range behind. This is OSM's "Hangar A…G" cluster — **it is not LATAM**, it is the Air Force. Useful for not picking the wrong block. |
| `refs/_map_mro_overlay.png` | derived (see §6) | — | Plan of the maintenance block with the OSM footprints overlaid on satellite imagery, with a local metric grid every 100 m. |

### 2.2 Terminal

| file | author / licence | date | what it validates exactly |
|---|---|---|---|
| `t2_panorama_anfiteatro.jpg` | Ivotoledo45, CC BY-SA 4.0 | 2022-07-19 | **The best photograph of the set.** A 10754×2745 panorama of Terminal 2 from the landside: continuous **undulating roof** in dark grey metal with a long cantilevered eave; facade in **light green (sage/mint) panels** alternating with **orange-copper brise-soleil** and glass; walkways and ramps in concrete and white steel. Snow-capped mountains behind (July = winter). |
| `t2_exterior_2022.jpg` | Corsario CL, CC BY-SA 4.0 | 2022-09-01 | T2 at dusk from the access viaduct: shows how the facade reads in the dark. |
| `t1_landside_spaceframe.jpg` | Nanosmile, CC BY-SA 2.0 de | — | Terminal 1 from the landside: **tubular space-frame structure with V-shaped struts**, glass curtain wall, flat eave with an exposed white duct. Blue Centropuerto buses. |
| `apron_2022_sky_latam.jpg` | Aeveraal, CC BY-SA 4.0 | 2022-02-11 | Terminal 1 **from the airside**: glass curtain wall with grey mullions, light metal fascia, flat roof with exposed condensers, jet bridge. **Tall white light masts with a helical/fluted shaft** — a very characteristic detail. AKE containers marked "LA" (LATAM). February = summer, the hill behind is brown with no snow. |
| `spotting_2012_otherside.jpg` | Aeroprints.com, CC BY-SA 3.0 | 2012-10-19 | View of the terminal **across the field**, from the far side of the runways: this is literally the framing of the scene. It shows the terminal as a low, long volume, the row of white masts, the aircraft lined up — and **how much haze there is**: at 1–1.5 km the terminal has already lost contrast and is barely saturated. |
| `takeoff_scl_a320.jpg` | Ralphito, CC BY-SA 3.0 | — | A LAN A320 rotating with the terminal and the apron behind. The target composition for the animation. |
| `scl01`…`scl10.jpg` | Vmzp85, CC BY-SA 4.0 | 2022-09 | Interiors of T2 and T1. Only useful for T2: **branching V-columns made of bundles of steel tubes on a truncated-cone concrete base**, ceiling of metal slats. They do not appear in an exterior scene, but they record the building's language. `scl03.jpg` shows the landside from outside. |

### 2.3 Control tower

| file | author / licence | date | what it validates exactly |
|---|---|---|---|
| `apron_panoramio_2011.jpg` | Nelson Pérez, CC BY-SA 3.0 | 2011-03-05 | **The only good photograph of the tower.** Shaft in **exposed concrete**, rectangular section with chamfered corners, tapering slightly upward; **open lower gallery with a handrail**, then the **glazed cab with the glass raked outward**, then a **roof slab with a handrail** carrying the **horizontal-bar radar** and whip antennas. A striking detail: **an external steel lattice frame (X plus raking posts) leaning against one face of the shaft**, painted light grey. Aged grey concrete with dark streaking. |

### 2.4 Apron, jet bridges and ground equipment

| file | author / licence | date | what it validates exactly |
|---|---|---|---|
| `ctj_5365.jpg` | Christer T Johansson, CC BY 3.0 | 2016-12-22 | **The jet bridges at SCL are royal blue with "Banco de Chile" in white cursive** on the side. That is *the* detail an employee recognises instantly. Also: **dark blue "ANDES" tugs** with a red/white stripe, white baggage carts with railings, orange cones, a white truck with a red chequer and the legend "MANTENGA EL FRENTE DE ESTE VEHÍCULO LIBRE". Apron surface in **light concrete slabs with visible joints**, yellow taxi lines and red restriction lines. |
| `ctj_5361.jpg`, `ctj_5369.jpg`, `ctj_5372.jpg` | Christer T Johansson, CC BY 3.0 | 2016-12-22 | More angles of the same blue "Banco de Chile" bridges and of the GSE. |
| `losa_carga_2015.jpg` | Omnespsx, CC BY-SA 4.0 | 2015-08-28 | Cargo apron with a Tampa Cargo 767F; stairs and ramp equipment. |
| `ramp_2010_phillipc.jpg` | Phillip Capper, CC BY 2.0 | 2010-12-28 | A row of tails on the apron with the tall light masts; gives the rhythm of the spacing between stands. |
| `apron_2010_phillipc.jpg`, `lan_a320_2012_ramp.jpg`, `lan_a320_2012_ramp_b.jpg`, `lan_767_2012_ramp.jpg` | see `manifest.json` | 2010/2012 | Aircraft on the apron and taxiing; background context. |
| `latam_787_scl_2017.jpg` | Sky KoreSCL, CC BY-SA 4.0 | 2017-02-22 | A LATAM 787-9 at SCL at dusk — reference for the colour of late-afternoon light on the field. |

### 2.5 The cordillera behind

| file | author / licence | date | what it validates exactly |
|---|---|---|---|
| `latam_a321_2022.jpg` | Maurice Becker, CC BY-SA 4.0 | **2022-06-12** (winter) | **The cordillera calibration photograph.** A321 CC-BEA on the runway with the high range behind: **snow on the upper part**, blue-grey rock below, and a **very strong horizontal haze layer** that lightens and desaturates the mountain from the base upward. Extremely low contrast — the range is almost a pale blue silhouette with a white top. |
| `latam_a321_2018.jpg` | Sky KoreSCL, CC BY-SA 4.0 | 2018-06-16 (winter) | The near range, brown, **with no snow** — shows that not every crest turns white in winter; the snow is only on the high ground. |
| `lan767_2010_phillipc.jpg` | Phillip Capper, CC BY 2.0 | 2010-12-28 (summer) | **Summer: no snow visible at all**, the range entirely brown-grey. |
| `aerial_2014.jpg` | Ivotoledo45, CC BY-SA 4.0 | 2014-11-30 | Aerial view of the field between clouds; useful for reading the general layout, but with heavy haze. |

---

## 3. What each element looks like — modelling summary

### 3.1 LATAM maintenance base

It sits **between the two runways**, west of 17L. OSM names the main building
**"Base de Operaciones y Mantenimiento LATAM Airlines"** (César Lavín Toro 2198,
Pudahuel) and a second volume simply **"LATAM"** (tagged `building=hangar`).

Measurements in the local frame (minimum oriented box, from OSM; checked against the
satellite image — see §5):

| building | centre (x, y) m | box m | area m² |
|---|---|---|---|
| Base de Operaciones y Mantenimiento LATAM Airlines | (−660, −1313) | 161.9 × 123.1 | 13 447 |
| "LATAM" hangar | (−627, −1252) | 88.5 × 81.7 | 5 381 |
| unnamed annex | (−635, −1142) | 78.2 × 51.2 | 2 845 |
| unnamed annex | (−648, −1058) | 50.3 × 46.9 | 2 358 |
| **Plataforma LATAM** (apron) | (−561, −1272) | 471.7 × 307.2 | **82 617** |

Appearance, from what can be seen:

- **Light roof** (off-white to very light grey) seen from above, with regular rows of dark
  monitors/extractors. The "LATAM" hangar has a **long central joint dividing the roof into
  two planes** → it reads as **two bays**, each of the order of **45–47 m**, which accepts an
  A320 (35.8 m span) per bay with clearance. I measured the volume on the satellite image at
  two independent zoom levels (z18 and z19) and got **90–94 m × 61–65 m**, different from the
  OSM polygon (88.5 × 81.7 m) — the OSM polygon appears to include an appendage to the south.
  **Use ≈ 92 × 63 m** and treat the OSM value as a known divergence.
- **Sign:** the LATAM office building carries a **large illuminated sign with the word LATAM
  in white and the brandmark (the coral/red bundle of strokes) to its left**, mounted high on
  the facade, above a band of lit windows on 2–3 floors. Confirmed in the night photograph
  `hangar_sky_2021.jpg`.
- **Hangar structure at SCL** (from the photographed interior): **exposed dark steel truss**,
  portal frames with chords and diagonals, a very shallow gable roof, a wide sliding door,
  high-bay luminaires hung from the trusses.
- **Height: not confirmed.** See §7.

Neighbours in the same block that must not be confused with LATAM:
**Base de Mantenimiento Sky Airline** (−822, −1659), 95.5 × 93.1 m, with the **Sky "S" logo
painted on the roof in magenta/maroon** (visible on satellite); **Aerocardal**
(−766, −1240), 93.0 × 36.8 m, with a very characteristic roof of **light rectangular panels
in two columns × seven rows**; **American Airlines** (−1072, −1296); **Aviasur**, **Jetex**,
**Santiago FBO**, **ENAER**; and **two hangars with cobalt-blue roofs and white stripes** at
(−981, −968) and (−982, −1040).

### 3.2 Terminals

| terminal | centre (x, y) m | box m | opened |
|---|---|---|---|
| Terminal 2 Internacional (central processor) | (−636, −2802) | 367 × 309 | **2022-02-28** |
| Terminal 1 Nacional | (−669, −2276) | 480 × 97 | 1994-02-14 |
| Espigón C "Isla de Pascua" | (−942, −2645) | 296 × 103 | 2018-12-18 |
| Espigón E "Lagos" | (−926, −3000) | 296 × 101 | 2019-09-12 |
| Espigón D "Desierto de Atacama" | (−371, −2618) | 238 × 102 | 2021-07 |
| Espigón F "Patagonia" | (−357, −2974) | 240 × 102 | 2024 |
| Espigón B "Valle Central" | (−370, −2263) | 210 × 94 | 1994 |
| Espigón A "Costa" | (−1007, −2283) | 199 × 81 | 2024-09 |

Which is which: **T1 = domestic** (the 1994 building, tubular space frame, piers A and B);
**T2 = international** (2022, undulating green/orange roof, piers C, D, E, F).
The piers are lettered **A to F** and each carries the name of a Chilean region — an
employee calls them by name, not by letter.

Visual language of T2: **undulating roof in dark grey metal with a long eave**, facade in
**mint-green panels + orange-copper brise-soleil + glass**, and, inside, **branching V-columns
of bundled tubes on a concrete base**. From the airside, the piers are elongated boxes about
100 m wide with the same undulating roof.

Language of T1: **white/grey tubular space frame with V-shaped struts**, glass curtain wall,
flat eave, roof with exposed condensers.

### 3.3 Control tower

- **Height: 65 m**, inaugurated on **15 December 1999** — source: DGAC (the operator itself).
  OSM says 60 m and 10 floors; **keep the DGAC 65 m** and treat the OSM number as a known
  divergence.
- Position: **(−676.5, −1779)** in the local frame; footprint ~15.9 × 15.8 m.
- Shape (from the photograph): shaft in **exposed concrete**, rectangular section with
  chamfered corners, tapering slightly upward; **open gallery with a handrail** just below the
  cab; **glazed cab with the glass raked outward**, wider than the shaft, octagonal in plan;
  **roof slab with a handrail** carrying **a horizontal-bar radar**, a whip antenna and small
  equipment.
- The detail that gives it identity: **an external steel lattice frame (an X plus raking
  posts), light grey, leaning against one face of the shaft**, running down from the cab.
- Colour: medium grey concrete, weathered, with dark streaking; light steel; greenish glass
  with a bluish reflection.
- There is a second tower, **"Torre de Control FACh"**, at (−570, −185), only **15 m**,
  3 floors — at the far north end, next to the Air Force's blue hangars.

### 3.4 Apron, bridges and ground equipment

- **Royal-blue jet bridges with "Banco de Chile" in white cursive.** Without this the scene is
  not SCL.
- Surface: **light, almost greyish-white concrete slabs with strongly marked joints**;
  **yellow** taxi/stand lines, **red** restriction lines, white bands.
- GSE: dark blue **ANDES** tugs with a red and white stripe, white railed baggage carts, flat
  dollies, light **AKE** containers marked "LA", orange cones, jersey-type concrete blocks.
- **Tall white light masts with a fluted/helical shaft** — they appear in a row along the
  apron and are very visible in the silhouette.
- 208 parking positions and 65 jet bridges are mapped in OSM
  (`refs/_osm_local_measurements.json`), with the real designators (A01…A16, B01…B09, C1…C11,
  D1…D10, E1…E12, F1…F9, W1…W9).

### 3.5 Cordillera

Two independent methods, and they agree:

**(a) Computation from the DEM.** Horizon profile traced from SRTM 30 m
(OpenTopoData) from the origin, over the azimuth sector 40°–140°, 2° step, range
3–109 km, with Earth-curvature and refraction correction (k = 0.13). Result in
`refs/_east_skyline_dem.csv`:

| | value |
|---|---|
| crest elevation angle, minimum | **1.95°** (az 132°) |
| crest elevation angle, maximum | **4.89°** (az 74°, at 55.5 km, summit 5 432 m — **Cerro El Plomo**, 5 424 m on the charts) |
| mean over the eastern sector | **3.46°** |
| first crest (near range, Sierra de Ramón) | 2–4°, at **33–40 km** |

**(b) Measurement on the photograph** `latam_a321_2022.jpg`, using the A321 (44.51 m long)
as the scale: the snowy crest sits **≈ 4.8°** above the horizon. It matches the DEM.

> A trap that cost me time: if you use the EXIF focal length (117 mm 35 mm-equivalent) as
> though the image were full frame, you get **6.0°** — wrong, because the photograph was
> cropped before publication. The ratio between angles inside the same photograph is
> reliable; the absolute value taken from EXIF is not. **Anchor on the DEM.**

Appearance:

- **Angular scale: the cordillera occupies a band only 2° to 5° above the horizon.**
  It is low. The classic error is modelling the mountain far too large.
- **Distance: 33–55 km.** The near range (Sierra de Ramón, Cerro Provincia,
  Cerro San Ramón) at 33–40 km; the big ones (El Plomo) at 55 km.
- **Colour: pale blue-grey, very desaturated.** Aerial perspective in Santiago is strong —
  there is a horizontal haze layer that lightens the mountain from the base upward and kills
  the contrast. Even the terminal at 1.5 km already loses saturation
  (`spotting_2012_otherside.jpg`).
- **Snow — it depends on the season, and this has to be an explicit decision for the scene:**
  - **winter (Jun–Sep)**: snow on the upper third. In `latam_a321_2022.jpg` (12 June) the snow
    starts around **3.5–3.6°** of elevation and runs to the crest at ~4.8° — that is,
    **white only on the top ~25% of the range's angular height**.
  - **summer (Dec–Mar)**: **no visible snow** (`lan767_2010_phillipc.jpg`, 28 December).
  - not every crest goes white in winter: the low ranges stay brown
    (`latam_a321_2018.jpg`, June).
- Ground around the field: **dry brown-ochre earth with sparse grass**, olive-green strips
  beside the runways; in winter the grass gets greener.

---

## 4. Runways

| runway | from (x,y) m | to (x,y) m | track | length |
|---|---|---|---|---|
| **17L/35R** | threshold 17L **(0, 0)** | threshold 35R **(145.1, −3200.7)** | **177.40°** | 3 204 m between thresholds; plus **542 m** of pavement mapped south of threshold 35R (total ≈ 3 746 m, matching the OSM `length=3748` tag) |
| **17R/35L** | (−1583.5, +458.6) | (−1413.1, −3337.6) | 177.43° | 3 800 m (OSM) |

The two runways are practically parallel and **separated by ~1 560 m**, with the whole
terminal and maintenance complex between them.

Recorded divergence: DGAC describes the second runway (17R) as **4 000 m**, completed in
2005; OSM gives 3 800 m. I did not resolve which is the currently certified figure.

Visual aids in the local frame: **PAPI 17L** at **(74.5, −397.6)**; PAPI 35R at
(69.0, −2801.5); windsocks at (−31.7, −1899.8), (−950.7, −1438.3) and (−877.0, −1499.9).

---

## 5. Cross-check of geometry against imagery

I overlaid the OpenStreetMap footprints on Esri World Imagery and checked the alignment:
`refs/_map_mro_overlay.png` (maintenance block, 100 m grid) and
`refs/_map_field_overlay.png` (whole field, 500 m grid, with the 17L take-off roll marked
every 500 m). The alignment is good — the polygons land on top of the buildings.

**Important caveat:** the Esri mosaic is of mixed dates and, in the Terminal 2 area, appears
to predate the 2022 opening — construction work is visible. For T2, trust the photographs
(`t2_panorama_anfiteatro.jpg`, `t2_exterior_2022.jpg`), not the satellite.

Those two PNGs are **derived from Esri World Imagery, which is not free**. They are here as
working support. **Do not publish those two files** — see §8.

---

## 6. Sources consulted

**Geographic data**
- OpenStreetMap via the Overpass API, extracted 2026-08-18 — runways, hangars, terminals,
  towers, aprons, parking positions, bridges. Licence **ODbL**.
- SRTM 30 m via **OpenTopoData** (`api.opentopodata.org`) — 9 333 points sampled for the
  horizon profile. SRTM is **public domain** (NASA/USGS).
- Esri World Imagery (`server.arcgisonline.com`) — satellite imagery, **only as visual
  verification**. Restrictive terms, not redistributable.

**Text**
- DGAC (Dirección General de Aeronáutica Civil, Chile), "La historia del Aeropuerto
  Arturo Merino Benítez" — https://www.dgac.gob.cl/la-historia-del-aeropuerto-arturo-merino-benitez/
  → 65 m tower inaugurated 15/12/1999; second runway of 4 000 m completed in 2005;
  international terminal of 25 000 m² inaugurated 14/02/1994.
- OPSGROUP, "Santiago, Chile – Temporary Runway Changes" — https://ops.group/blog/santiago-chile-temporary-runway-changes/
  → because of the night noise restriction, departures use 17L and not 17R.
  **Read wrongly here** — it describes the 00:00–07:00 exception, not the general rule.
- LATAM Airlines, "Centro de Mantenimiento en Santiago: 30 años" —
  https://www.latamairlines.com/cl/es/vamos/volar/aviacion/centro-mantenimiento-santiago
  → **I could not open it** (HTTP 403). Left as a pending item.

**Photographs** — all from Wikimedia Commons, detailed in `refs/manifest.json`.

---

## 7. What I could not do

1. **Height of the LATAM base buildings.** No source carries it. I tried to calibrate from
   the satellite shadows using the 65 m tower as a reference, but the Esri mosaic is of mixed
   dates and I could not pin down the solar elevation with confidence — the number would come
   out invented, so **I am not giving a number**. Suggestion for whoever models it: a hangar
   with a ~45 m bay for an A320 usually has **18–25 m** of clear door height; use that as a
   declared range, not as a measurement.
2. **The LATAM base facade in daylight.** I only got the sign at night. Wall colour, cladding
   material and the exact number of hangar doors remain photographically unconfirmed.
   **This is the biggest gap** and it is precisely what the employee recognises most.
3. **Identity of the arch-roofed hangar** that appears behind CC-BAC in
   `latam_a320neo_landing_scel_2025.jpg`. The shape is documented; which building it is, is not.
4. **The currently certified length of 17R** (3 800 vs 4 000 m).
5. **No free-licence photograph of the airside of Terminal 2.** Everything I found of T2 is
   landside or interior. For the scene, what you see from the runway is exactly the airside of
   piers C/D/E/F — it is inferred from the plan shape and the landside language,
   **not validated by photograph**.
6. Wikimedia Commons has **no photograph** with the LATAM maintenance base as its subject.
   I searched by category and by free text.

---

## 8. Licences and what may be published

| file | may it be redistributed? | condition |
|---|---|---|
| all **40 `.jpg`** in `refs/` | **yes** | attribute author + licence per `refs/manifest.json`; CC BY-SA requires sharing derivatives under the same licence |
| `refs/manifest.json`, `refs/_osm_local_measurements.json` | yes | OSM data → **ODbL**, cite "© OpenStreetMap contributors" |
| `refs/_east_skyline_dem.csv` | yes | derived from SRTM (public domain) |
| `refs/_map_field_overlay.png`, `refs/_map_mro_overlay.png` | **NO** | they contain **Esri World Imagery**, restrictive licence. Internal verification use. If the repository is public, **delete them or replace them with a version carrying only the OSM vectors over a plain background.** |

Per-photograph licence detail (`CC0` / `CC BY 2.0` / `CC BY 3.0` / `CC BY-SA 2.0 de` /
`CC BY-SA 3.0` / `CC BY-SA 4.0`), with the Commons page URL and the original file URL, is in
`refs/manifest.json`. Two photographs are by photographers who explicitly ask for a named
credit: **Christer T Johansson** (the four `ctj_*`) and **Phillip Capper**
(the four `*_phillipc`).
