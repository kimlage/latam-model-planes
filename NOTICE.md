# Legal and third-party notices

## How this repository is licensed

The project carries two licences, because it holds two kinds of content:

| Content | Licence |
|---|---|
| Code — `*.py`, `*.sh`, skills under `.claude/skills/` | [MIT](LICENSE) |
| Engineering data — `spec_*.json`, `*_curves.json`, `*_planform.json` | [MIT](LICENSE) |
| 3D models (`*.blend`), renders (`*.png`), animations (`*.gif`) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |

Suggested attribution for the models and images:

> LATAM fleet 3D replicas — Kim Lage — CC BY 4.0

## Trademarks

**LATAM**, the LATAM symbol, **Airbus**, **A319**, **A320neo**, **Boeing**, **787** and
**Dreamliner** are trademarks of their respective owners. This is an
**independent, non-commercial project with no affiliation, sponsorship or
endorsement** from LATAM Airlines Group, Airbus S.A.S. or The Boeing Company.

The licences above cover **this project's own authorship** — the mesh, the
scripts, the measurements. They **grant no rights** over the trademarks depicted.
Commercial use of the livery or the marks requires permission from the owners;
CC BY 4.0 is not a substitute for it.

## Third-party material that is NOT in this repository

These files are part of the workflow but were deliberately excluded (see
[.gitignore](.gitignore)), because they cannot be redistributed under the
licences above. To reproduce the pipeline from scratch, get them from the source:

| File | What it is | Where to get it |
|---|---|---|
| `A320_ACAP_airbus.pdf` | A320 *Aircraft Characteristics — Airport & Maintenance Planning* | Airbus **Aircraft Characteristics** page (free) |
| `airbus A319/A319_ACAP_airbus.pdf` | A319 ACAP, Rev. 30 Jul/26 | Airbus **Aircraft Characteristics** page (free) |
| `airbus A321neo/A321_ACAP_airbus.pdf` | A321 ACAP, Rev. 35 Jul/26 (covers neo/ACF/XLR) | Airbus **Aircraft Characteristics** page (free) |
| `boeing 787-9/B787_APR_boeing.pdf` | 787 *Airplane Characteristics* D6-58333 | Boeing, **Airport Compatibility / ACAPs** section (free) |
| `latam_logo_indigo.svg` | Official LATAM lockup (symbol + wordmark) | Wikimedia Commons |
| `airbus_a320neo_logo.svg`, `airbus_a321neo_logo.svg`, `dreamliner_logo.svg` | Manufacturer titles | Wikimedia Commons |
| `ref_CC-BGP_wikimedia.jpg`, `ref_PT-TMN_wikimedia.jpg` | Reference photographs of the registrations | Wikimedia Commons / JetPhotos / Planespotters |
| `airbus A321neo/ref_PS-LBO_wikimedia_*.jpg` | PS-LBO reference photographs (CC BY-SA 4.0, share-alike — cited, not shipped) | credits in `airbus A321neo/refs_manifest.json` |

The manufacturer documents are free downloads, but **free to download is not
free to redistribute**: the rights stay with Airbus and Boeing.

The reference photographs were excluded for a different and equally simple
reason: the project did not record the author and licence of each one at
download time, and without that it is impossible to meet the attribution that
Creative Commons licences require. **Lesson folded into the pipeline:** every new
photograph enters with its URL, author and licence recorded in the aircraft's
`spec_*.json`.

## Elevation and geographic data (the SCL scenario)

The terrain under `scenario/` is derived from open data. The raw DEM tiles
(~1.5 GB) are **not** in the repository — `scenario/fetch_dem.sh` re-downloads
them. Full detail in [`scenario/TERRAIN.md`](scenario/TERRAIN.md).

| Source | Used for | Licence |
|---|---|---|
| **Copernicus DEM GLO-30** (WorldDEM-30) | primary elevation, all heightfields | Free & Open licence, adaptation expressly permitted — notices below |
| **SRTM v3 1 arcsec** (NASA/USGS) | independent control DEM | Public domain |
| **OurAirports** | SCEL runway thresholds, headings, elevations | Public domain |
| **GeoNames** | peak names and elevations | CC BY 4.0 |
| **OpenStreetMap** | peak and volcano names | ODbL 1.0 |

The Copernicus data here is **modified** (resampled into a local metric frame),
so its licence requires these two notices to travel with any redistribution:

> produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus
> Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European
> Union and ESA; all rights reserved

> The organisations in charge of the Copernicus programme by law or by
> delegation do not incur any liability for any use of the Copernicus
> WorldDEM-30

GeoNames attribution: *this product uses data from GeoNames
(https://www.geonames.org), licensed under CC BY 4.0*.
OpenStreetMap attribution: *© OpenStreetMap contributors*. Note that ODbL is
**share-alike**: derived databases distributed from the OSM-sourced peak names
carry that obligation. Each entry in `scenario/refs/gazetteer.json` records which
of the two gazetteers it came from, in its `src` field.

### The airport mesh is an OSM derivative — ODbL, share-alike

`scenario/scl_field.blend` is generated directly from `scenario/scl_osm.json`:
every building footprint, taxiway centreline, apron polygon, stand and jet-bridge
position in that file comes from OpenStreetMap. A mesh built straight from an
ODbL database is a **derived database**, so redistributing `scl_field.blend` — or
renders of it, or an aircraft file that links it — carries both obligations:

> Airport geometry © OpenStreetMap contributors, ODbL 1.0
> (https://opendatacommons.org/licenses/odbl/1-0/)

and share-alike on the derived geodata. The runway survey itself (thresholds,
widths, declared distances, marking geometry) comes from **AIP-Chile / DGAC** and
is quoted as fact; no chart is redistributed. Full breakdown in
[`scenario/README.md`](scenario/README.md) §6.

## What the models contain

The `.blend` files carry the livery textures packed in, including the marks
described above. They were generated in this project from the official vectors
and from photographic measurement. The aircraft geometry is **entirely
original**, built from the dimensions in the manufacturer documents — no
third-party mesh was used as a base (see the `fontes-aeronave` skill, *Licences*
section).
