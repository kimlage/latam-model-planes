# SDSC — photographic and documentary survey of the LATAM MRO at São Carlos

Survey of **Aeroporto Estadual Mário Pereira Lopes (SDSC / QSC)**, Água Vermelha,
São Carlos/SP, and of the **LATAM MRO** on the field, for building the scenery and a
departure clip. Every claim below is tied to a photograph I opened and looked at, to a
published aeronautical document I fetched, or to a measurement I made in this
repository — and whatever I could **not** establish is marked as such.

Survey date: **2026-08-23**. Sibling of `../scenario/scl_references.md`; same rules.

> **The one-line difference from Santiago.** At SCL the hard part was the Andes.
> Here there is no skyline at all — the entire horizon band is **1.6° wide**
> (`TERRAIN.md` §3). The hard part at SDSC is the opposite: the base is
> **eight years stale in OpenStreetMap**, the aerodrome has **no published
> aerodrome chart**, and the building that the whole 2025 story is about —
> **hangar 9** — has no published dimension anywhere and is not mapped.

---

## 1. Reference frame adopted

| item | value |
|---|---|
| origin | **lat −21.8818417, lon −47.9039639** — the published landing threshold of **RWY 02**, where a 02 take-off roll lines up |
| axes | x = east, y = north, z = up, metres, exact WGS84 ENU |
| vertical datum | **z = 0 at 807.0 m AMSL**, the published aerodrome elevation (2648 ft) |
| runway true track | **001.026°** — computed from the two published thresholds, confirmed by the charts' 023° magnetic and VAR 22° W |

`lib/frame.py` is the single source of truth. Everything in this folder is in that frame.

### What goes past on a RWY 02 departure

Projected onto the 02 track, measured from THR 02. Full table in
`sdsc_osm.json` → `departure_02_landmarks`.

| point in the roll | feature | offset | side |
|---|---|---|---|
| 69 m | navaid | 57 m | right |
| 223–470 m | **Aeroclube de São Carlos** — GA apron, five small hangars, windsock, terminal | 177–282 m | **left** |
| 1 146 m | isolated hangar + apron + fuel tanks | 314 m | right |
| **1 602–1 940 m** | **the LATAM MRO buildings and apron** | **797–1 287 m** | **right** |
| 2 008 m | MRO grass | 1 140 m | right |

**TORA on RWY 02 is 1 672 m.** A light A320 rotates well before that, so the base
comes abeam **at or just after rotation** and stays in frame through the initial
climb. Departing **20** mirrors all of it *and* puts the base behind the aircraft
from the very start of the roll — see `RECOGNITION.md` §1.

Note the scale against Santiago: there the LATAM base is 620–720 m off the
centreline; here it is **800–1 290 m**, roughly twice as far, and smaller. It will
read as a distant line of hangars, not as a wall.

---

## 2. Photograph table

All the images below are on Wikimedia Commons under a free licence, **none of them is
committed**. `refs/manifest.json` carries the machine-readable record (page URL, file
URL, author, licence, date, resolution, GPS). Re-download with
`python3 refs_fetch.py scenario_sdsc` from the repository root.

> Restrictively licensed material — LATAM's own press photographs, Aeroflap,
> Panrotas, CNN Brasil, Rede Voa, aeroin — was **read** for the figures and is cited in
> §5. Nothing from it was copied here.

### 2.1 The field, from outside

| file | author / licence | date | what it proves |
|---|---|---|---|
| `refs/sdsc_field_from_sp318_2013.jpg` | MARCO AURÉLIO ESPARZ, CC BY-SA 3.0 | 2013-12-12 | **The best photograph of the set, and it is nearly the framing of the clip.** Taken from the SP-318 at (x −482, y +1156) in this frame — 480 m *west* of the runway centreline — looking east across the field at the MRO 1.3 km away. It gives: a **shallow-arched, light-grey barrel-vault hangar** with a **dark red / maroon** volume beside it; a **TAM widebody** parked in front, tail-on to the camera; **four tall floodlight masts** with lamp clusters, clearly the tallest built objects on the field; a slim **orange-and-white chequerboard tower** (the Brazilian obstruction-marking pattern) with whip antennas; a **guyed lattice antenna mast**; a derelict multi-storey concrete building at the far left; a **wire fence on square concrete posts**; and the horizon, which is **flat** — a low, distant tree and field line, nothing more. December = wet season: the grass is vivid green and the sky is solid overcast. |

> **CORRECTION, made in phase 2 while building from this photograph.** The row
> above reads `sdsc_field_from_sp318_2013.jpg` as the LATAM MRO at 1.3 km. It is
> not. It is the **mid-field apron and the isolated 35 m hangar** at (335, 1141),
> about 1.1 km from the road. Three independent reasons, all re-measurable:
>
> 1. **The sight line to the MRO is blocked.** The runway is a local crest — its
>    surface is 796 m where the line from the recorded camera point crosses it —
>    and the Copernicus grid puts that camera point at 792.6 m. Anything beyond
>    the crest has to stand above ~800 m to be seen. The MRO platform is 770 m and
>    its roofs reach 784 m. `render_checks.py ground` renders this deliberately as
>    `ground_sp318_from_west.png`: from the real ground west of the runway the MRO
>    is invisible, which is the correct behaviour and the check for it.
> 2. **The parked widebody's fin top stands ABOVE the horizon in the frame.** That
>    is distance-free and focal-length-free: it bounds the camera at less than the
>    aeroplane's own height (17.4 m) above the plane it stands on. The MRO apron is
>    ~23 m below the SP-318; the mid-field apron is 1.7 m below the runway and
>    ~7 m below the road, which is exactly what the frame measures.
> 3. **The arch is the wrong size for the MRO and the right size for the mid-field
>    hangar.** By the horizon-ratio method the vault is 12.7 m to the apex and
>    ~32 m across at the distance that implies. `relation/7422970` is 35.4 × 35.4 m.
>
> So the chequerboard tower, the guyed lattice mast, the cylindrical tank, the
> derelict concrete block and the four floodlight masts in that frame are all at
> the **mid-field**, 314 m right of a RWY 02 roll at 1 146 m along it — which is
> where a departure passes closest to anything on the right. `build_scenery.py`
> builds them there, in `SDSC_Midfield`. What the frame still proves about the
> *base* is unchanged: nothing in it was ever the source for the hangar line.

| `refs/mro_centro_tecnologico_2009.jpg` | MARCO AURÉLIO ESPARZ, CC BY-SA 3.0 | 2009-11-19 | **The best exterior of the hangar line.** From (x +490, y +2120) — north-west of the base — across a **sugar-cane field**. Two large hangars side by side: light-grey ribbed metal walls, very shallow roof pitch, each carrying a **broad dark-red/maroon fascia band under the eave with a large "TAM" wordmark**, one in red on white and one in white on maroon. **Five or six TAM aircraft parked nose-in in a line along the frontage**, which is what an MRO ramp looks like. Low white buildings behind. Horizon dead flat. Hazy white sky. |
| `refs/mro_centro_manutencao_2007.jpg` | MARCO AURÉLIO ESPARZ, CC BY-SA 3.0 | 2007-08-22 | Interior looking out of an **open hangar door**, TAM A319 PR-MBE inside. Gives the door proportion, the light spilling in, and the pale polished floor. |
| `refs/agua_vermelha_avenida.jpg` | Niels A. Sørensen, CC BY-SA 3.0 | — | The **Água Vermelha** district beside the field: large-crowned tropical trees, low houses with red pantile roofs, a tarmac avenue, deep blue dry-season sky. This is the surround. |

### 2.2 Inside the hangars

| file | author / licence | date | what it proves |
|---|---|---|---|
| `refs/mro_centro_tecnologico_2010.jpg` | MARCO AURÉLIO ESPARZ, CC BY-SA 3.0 | 2010-07-07 | A TAM A320 on jacks with the cowls open. The roof is a deep **steel space frame painted bright RED**, white profiled metal deck above it, high-bay luminaires hung between the chords. Floor pale polished concrete. **Yellow tubular docking stands and access ladders, red tool trolleys, mechanics in red shirts.** If a hangar interior is ever visible through an open door, this is the palette. |
| `refs/mro_centro_manutencao_2006.jpg` | MARCO AURÉLIO ESPARZ, CC BY-SA 3.0 | 2006-12-27 | The same hangar seen **through the museum's viewing window** into the maintenance bay — the museum literally looked into the MRO. Red trusses again, aircraft under a full dock, workers on the wing. |
| `refs/mro_airbus_esquadrilha_2010.jpg` | MARCO AURÉLIO ESPARZ, CC BY-SA 3.0 | 2010-07-07 | The MRO **apron** with the Esquadrilha da Fumaça lined up and a TAM A320 behind. Gives the perimeter, which is **a white-rendered concrete wall topped by a black welded-mesh fence** — a very recognisable boundary — plus the apron surface, the grass margin and the **red-brown latosol** soil in front of it. |

### 2.3 The GA side and the ground

| file | author / licence | date | what it proves |
|---|---|---|---|
| `refs/ga_cessna150_2007.jpg` | Renato Spilimbergo Carvalho, GFDL 1.2 | 2007-03-25 | The **Aeroclube apron**: dark asphalt, **red-brown bare earth** beyond it, coarse green grass, a low distant tree line, tall summer cumulus. The soil colour is the single most important thing here and it is nothing like Santiago's pale ochre. |
| `refs/ga_cessna170_2007.jpg`, `refs/ga_taylorcraft_2007.jpg` | idem | 2007-03-25 | Same session, two more angles of the same apron and the light aircraft that live on it. |

### 2.4 The Museu TAM (on the site, and a trap)

| file | author / licence | date | what it proves |
|---|---|---|---|
| `refs/museu_entrada_2014.jpg` | JCMA, CC BY-SA 4.0 | 2014-07-31 | 4320×3240. The museum entrance: **white render with strong crimson banding and pilasters**, a maroon curved canopy and a blue arc. Behind it on the right, a **long pale hangar with an aircraft tail showing over it** — the MRO. |
| `refs/museu_tam_2011.jpg` | MARCO AURÉLIO ESPARZ, CC BY-SA 3.0 | 2011-08-12 | 4000×3000. The museum hall interior: **silver-grey** space frame and clerestory glazing — deliberately *not* the MRO's red. Useful only for not confusing the two buildings. |
| `refs/museu_entrada_2010.jpg` | MARCO AURÉLIO ESPARZ, CC BY-SA 3.0 | 2010-07-07 | The entrance from further out, with the site access road. |

**The trap.** OSM relation `7422930` is tagged `name=TAM MRO` **and**
`name:en=TAM Museum`, `wikidata=Q3868501`, `wikipedia=pt:Museu TAM`. The polygon is
the MRO; the museum tags on it are wrong. The Museu Asas de um Sonho did share this
site and **closed in 2016**. Follow the wikidata link and you will model a museum.

---

## 3. What the photographs establish about the MRO

- **Roof form.** Shallow. `sdsc_field_from_sp318_2013` shows a **continuous barrel
  vault** on one hangar; `mro_centro_tecnologico_2009` shows two hangars with a very
  shallow pitch. Both readings are from photographs, and they are of **different
  hangars** — the site has more than one roof type. Not a gable.
- **Cladding.** Light grey / off-white ribbed metal sheet, with a **dark red-maroon
  band** carrying the wordmark under the eave.
- **Structure.** Deep steel space frame, painted **bright red**, white deck above.
  Consistent across 2006, 2007 and 2010 photographs.
- **Ramp.** Aircraft parked **nose-in, in a line** along the hangar frontage.
- **Perimeter.** White rendered wall + black welded-mesh fence on the landside;
  plain wire on square concrete posts on the airfield boundary.
- **Floodlight masts** are the tallest objects on the airfield, clearly taller than
  the hangars, and there are at least four of them in the 2013 frame.
- **Ground colour.** Red-brown latosol where bare; strong green grass in the wet
  season (Dec–Mar), drier and more olive in the dry season (Jun–Sep).

### And what they do **not** establish

- **The livery is TAM, not LATAM.** Every free-licence photograph of this base is
  from **2006–2014**, when it was TAM: red wordmark, red-and-white buildings. The
  rebrand to LATAM (indigo / coral) happened in 2016 and the base has been LATAM
  ever since. **No free-licence photograph of the base in LATAM colours was found.**
  What the buildings carry today — indigo, coral, the current wordmark, or nothing —
  is **not photographically confirmed**. This is the largest appearance gap, and it
  is exactly the thing an employee would notice.
- **Hangar 9 does not appear in any of them** — it was inaugurated on
  2025-09-26, eleven years after the newest photograph here.

---

## 4. What I measured, and how

Everything in this section is a number produced in this repository, not quoted.

| measurement | value | method |
|---|---|---|
| RWY true track | **001.026°** | exact WGS84 ENU between the two published thresholds |
| THR 02 → THR 20 | **1 619.98 m** vs 1 620 m implied by the published 1720 − 52 − 48 | idem; **0.02 m** |
| magnetic check | 001.026 + 22.0 W = **023.03°** vs the charts' published 023° | 0.03° |
| runway slope | **10.06 m fall** to the north, 0.62%, published; **12.0 m** in Copernicus | published THR elevations; DEM sample |
| OSM runway centreline | **1 710.56 m**, 9.4 m short of the published pavement | `sdsc_osm.json` |
| MRO site polygon | **684 088 m²**, 1 064 × 921 m | OSM landuse, ring-stitched |
| largest mapped MRO building | **471.5 × 137.3 m**, 43 140 m², long axis 001.1° | OSM minimum-area box |
| that building's height | **+12.9 m** above its platform (p90 +10.6 m) | Copernicus GLO-30 DSM: max inside the footprint shrunk 8 m, minus the median of a 45–115 m ring. 54 distinct 30 m cells inside. |
| MRO platform | **~770 m AMSL**, i.e. **~35 m below THR 02** | Copernicus, SRTM agrees within ~4 m |
| horizon band, whole 360° | **−0.32° to +1.30°** | `terrain/horizon_5deg.json` |
| wind favouring RWY 02 | **63.2%** of the hours the aerodrome is open | ERA5 2021–2025, `sdsc_operations_wind.json` |

---

## 5. Sources consulted

**Aeronautical (primary)**
- **AISWEB / DECEA**, ROTAER entry and declared-distance table for SDSC —
  `https://aisweb.decea.mil.br/?i=aerodromos&codigo=SDSC`, site AMDT 34/26,
  ROTAER D-AMDT 42/25, fetched 2026-08-23. Page fetched with `curl` and stripped to
  text, so the figures in `sdsc_aip_survey.json` are the published strings.
- **SDSC IAC RNP Z RWY 02** (`SDSC_IAC_00B`) and **IAC RNP Y RWY 20**
  (`SDSC_IAC_00A`), AIRAC AMDT 2512A1, 27 NOV 25. PDFs downloaded from AISWEB and
  their text layers extracted. Source of **VAR 22° W**, the threshold elevations and
  the magnetic final courses. Not redistributed.
- **There is no aerodrome chart.** SDSC is VFR; DECEA publishes only these two
  approach charts. See §6.1.

**Geographic**
- **OpenStreetMap** via the Overpass API, extracted 2026-08-23 — ODbL 1.0.
- **Copernicus DEM GLO-30** (primary) and **SRTM v3** (control) — `TERRAIN.md` §7.
- **ERA5** reanalysis via the **Open-Meteo** historical API, 2021–2025 hourly 10 m
  wind — for the runway-preference question. ERA5: Copernicus C3S / ECMWF.
  Open-Meteo data: CC BY 4.0.

**Text — read for figures, never copied**
- **LATAM Airlines**, *"LATAM inaugura hangar de R$ 40 milhões no maior centro de
  manutenção aeronáutica da América do Sul"*, 2025-09-26 —
  `https://www.latamairlines.com/br/pt/imprensa/noticias/latam-inaugura-hangar-de-r--40-milhoes-no-maior-centro-de-manute`.
  **HTTP 403 to this survey.** The same release is reproduced verbatim by the outlets
  below, which is how its figures were read.
- **CNN Brasil**, *"Latam inaugura hangar de R$ 40 milhões para ampliar centro de
  manutenção"*, 2025-09-26 — 95 000 m², 9 hangars, 22 workshops, ~2 000 staff,
  >60% of the group fleet's scheduled maintenance, EASA/FAA/DGAC, hangar 9's
  capability set.
- **CNN Brasil**, *"SP tem o maior centro de manutenção de aviões da América do Sul;
  conheça"* — 270 aircraft/year, up to 16 simultaneous, the workshop list, one week
  to 40 days per aircraft, ~70% of scheduled maintenance in Latin America, and the
  statement that **777 maintenance is done at Guarulhos, not here**.
- **Rede Voa**, *"Aeroporto de São Carlos: Latam inaugura hangar…"* — Alckmin's
  "we increased the runway from 1 400 m to over 1 700 m", referring to the 2001 works.
- **São Carlos Agora / aeroin / Aeroflap**, October 2020 — the **A350-900 PR-XTK**
  landing on 14 Oct 2020 at 11:51 from Confins, the largest aircraft ever received by
  the base; previous largest the **A330-200**. *(aeroin returned 307 and Aeroflap 402
  to direct fetches; these facts come from the search summaries of those pages and
  from São Carlos Agora, and should be treated as secondary reporting.)*
- **Portuguese Wikipedia**, `LATAM MRO` and `Aeroporto Internacional de São Carlos` —
  95 000 m² / 9 hangars / 22 workshops, the 2001 modernisation from 1 460 × 30 m, the
  2021 Rede Voa concession, the first 787-9 major overhaul in February 2026, and the
  reported pending request to extend the runway to 3 000 × 60 m. CC BY-SA 4.0, used
  as a pointer to referenced facts, never as geometry.

---

## 6. What I could **not** establish

1. **§6.1 — There is no aerodrome chart for SDSC, and that is a gap in the source.**
   DECEA publishes an ADC only for IFR aerodromes. For SDSC there is none. So there is
   **no published**: runway marking layout, threshold-stripe count, aiming-point or
   TDZ geometry, taxiway designators, apron plan, stand numbering, lighting layout, or
   holding-position positions. Santiago had all of this from AIP-Chile. Here, every
   one of those must come from imagery in phase 2 or be declared an estimate.
2. **Hangar 9 — no dimension, no position, no photograph I may use.** Not in LATAM's
   release, not in Aeroflap, Panrotas, CNN Brasil, Diário do Turismo, Rede Voa or
   Times Brasil; not in OpenStreetMap. The whole 2025 story is about a building whose
   size and location I could not establish. **Do not invent it.**
3. **The base in LATAM colours.** Every free-licence photograph is 2006–2014, i.e.
   TAM red. What the buildings look like today is unconfirmed. See §3.
4. **Building heights, except one.** Only `relation/7422965` (471 × 137 m) is wide
   enough for a 30 m DSM to measure — +12.9 m, and that is a floor, not the ridge.
   Every other building on the site returned 0.0–5.2 m, which is DSM smearing, not
   architecture. **No published height exists for any building on this field**, and
   no OSM `height` or `building:levels` tag either.
5. **Which OSM polygon is which hangar.** OSM tags three small polygons `hangar` and
   the huge 471 × 137 m block merely `building=yes`, unnamed. Whether that block is
   the hangar line, the workshop spine, or both, is not established. LATAM says nine
   hangars; OSM maps four hangar-tagged polygons on the site, five if the big block
   counts, and five *more* `hangar` polygons that belong to the **Aeroclube**, not to
   LATAM. **The counts do not reconcile and should not be forced to.**
6. **The MRO platform level.** Copernicus puts it ~35 m below THR 02, and SRTM agrees.
   That is a measurement, but it is scene-defining and unconfirmed by any photograph
   or levelling survey. Check it before building.
7. **On-field wind.** SDSC is absent from the Iowa State ASOS archive and REDEMET
   needs an API key. The runway-preference figure comes from **ERA5 reanalysis at
   ~25 km**, not from an anemometer on the field.
8. **The identity of the chequerboard tower** in `sdsc_field_from_sp318_2013`. It has
   the Brazilian obstruction chequer and whip antennas. OSM has a `water_tower` node
   at (1124, 1571) and a `mast` at (608, 1554), neither of which sits where the
   photograph puts this tower. SDSC has **AFIS, not ATC**, so it is probably not a
   control tower. Unresolved.
9. **The derelict concrete building** at the left of the same photograph. Unidentified.
10. **Stand layout on the MRO ramp.** OSM maps three `parking_position` ways, all at
    the *Aeroclube*, none at the MRO. The nose-in line in the 2009 photograph is
    evidence that stands exist; their number, spacing and headings are not surveyed.
11. **Whether the 3 000 × 60 m extension has progressed.** Only secondary reporting
    was found; no DAESP or Rede Voa primary document, no AIP supplement, no NOTAM.

---

## 7. Licences and what may be published

| file | may it be redistributed? | condition |
|---|---|---|
| the 13 `.jpg` under `refs/` | **not from here** — they are cited, not committed | if you do use them, attribute author + licence per `refs/manifest.json`; the CC BY-SA ones require share-alike, and `ga_*` are **GFDL 1.2**, which is the most awkward of the set |
| `refs/manifest.json`, `sdsc_references.md`, `sdsc_aip_survey.json` | yes | this repository's licence |
| `sdsc_osm.json`, `sdsc_osm_plan*.png` | yes, **but ODbL** | derived from OpenStreetMap: *"Airport geometry © OpenStreetMap contributors, ODbL 1.0"*, and share-alike applies to the derived database and to any mesh generated straight from it |
| `terrain/*.npy`, `terrain/*.png`, `horizon_*` | yes | Copernicus DEM attribution (see `TERRAIN.md` §7) and SRTM public domain |
| `sdsc_operations_wind.json` | yes | ERA5 © Copernicus C3S/ECMWF; Open-Meteo data CC BY 4.0 |
| `sdsc_operations_sun.json` | yes | computed here, no third-party data |
| the DECEA charts | **NO** | not redistributed. Only the numbers and the URLs are in this repository. |
| LATAM / Aeroflap / CNN / Rede Voa press photographs | **NO** | all rights reserved. Read for figures only; **none was downloaded**. |

Two authors carry almost this whole survey and deserve naming:
**MARCO AURÉLIO ESPARZ** (eight of the thirteen photographs, all via Panoramio) and
**Renato Spilimbergo Carvalho** (the three GA photographs).
