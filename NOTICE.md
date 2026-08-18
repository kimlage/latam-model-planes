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

**LATAM**, the LATAM symbol, **Airbus**, **A320neo**, **Boeing**, **787** and
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
| `boeing 787-9/B787_APR_boeing.pdf` | 787 *Airplane Characteristics* D6-58333 | Boeing, **Airport Compatibility / ACAPs** section (free) |
| `latam_logo_indigo.svg` | Official LATAM lockup (symbol + wordmark) | Wikimedia Commons |
| `airbus_a320neo_logo.svg`, `dreamliner_logo.svg` | Manufacturer titles | Wikimedia Commons |
| `ref_CC-BGP_wikimedia.jpg`, `ref_PT-TMN_wikimedia.jpg` | Reference photographs of the registrations | Wikimedia Commons / JetPhotos / Planespotters |

The manufacturer documents are free downloads, but **free to download is not
free to redistribute**: the rights stay with Airbus and Boeing.

The reference photographs were excluded for a different and equally simple
reason: the project did not record the author and licence of each one at
download time, and without that it is impossible to meet the attribution that
Creative Commons licences require. **Lesson folded into the pipeline:** every new
photograph enters with its URL, author and licence recorded in the aircraft's
`spec_*.json`.

## What the models contain

The `.blend` files carry the livery textures packed in, including the marks
described above. They were generated in this project from the official vectors
and from photographic measurement. The aircraft geometry is **entirely
original**, built from the dimensions in the manufacturer documents — no
third-party mesh was used as a base (see the `fontes-aeronave` skill, *Licences*
section).
