# LATAM fleet — 3D replicas

![Boeing 787-9 and Airbus A320neo in LATAM livery, rendered from several angles](capa.png)

Blender models of LATAM Airlines aircraft, built to one standard: **the
dimensions have to match the manufacturer's document, and the paint has to match
a photograph of that specific registration**. The bar is not "it looks like an
airliner" — it is a LATAM engineer recognising their own aircraft.

Two aircraft finished:

| Aircraft | Registration | File | Length |
|---|---|---|---|
| **Boeing 787-9 Dreamliner** | CC-BGK | [`boeing 787-9/B789_LATAM.blend`](boeing%20787-9/B789_LATAM.blend) | 62.81 m |
| **Airbus A320neo** | PT-TMN | [`airbus A320neo/A320neo_LATAM.blend`](airbus%20A320neo/A320neo_LATAM.blend) | 37.57 m |

![A320neo taking off: ground run, rotation, gear retracting, climb-out](airbus%20A320neo/a320_decolagem_v2.gif)

*A320neo takeoff — the camera orbits while the aircraft accelerates, rotates about
the main gear, lifts off and retracts the gear. There is also an
[orbit-in-place clip](airbus%20A320neo/a320_voo.gif) and a
[first camera pass](airbus%20A320neo/a320_decolagem.gif) kept for comparison.*

---

## Why this repository exists

Modelling an aircraft by eye is fast and comes out wrong. This project is the
opposite bet: **no mesh before there is a number**. Every dimension traces back
to an official manufacturer document (Airbus *ACAP*, Boeing *Airplane
Characteristics*), and whatever the document does not carry — how the livery is
applied, where the indigo wedge crosses the door, the exact shade — is measured
photogrammetrically from photographs of that registration, with the uncertainty
written down.

The practical payoff is that **the model is reconstructible**. If the `.blend`
disappears, each aircraft's `spec_<type>.json` holds the complete engineering
specification — nose stations, master section, windshield polygons, doors,
windows, wing planform, empennage, engine, landing gear — and the scripts
rebuild from it.

## The six phases

1. **Sources** — official dimensional document, photographs of the registration,
   open CAD only as a silhouette cross-check. → skill `fontes-aeronave`
2. **Extraction** — rasterise the views at 600 dpi, calibrate on a printed
   dimension, extract crown/keel/half-width → `curves.json` + `spec_<type>.json`.
   → skill `extrair-cotas`
3. **Hull** — a sparse control cage **on the real frame stations** plus a
   Catmull-Clark subsurf. A dense cage is what produces a dented nose; the sparse
   one is what makes it smooth. → skill `casco-parametrico`
4. **Livery** — official brand vectors, application measured from the photo,
   paint as a UV texture in `(x, θ)` — never as a 3D shell. → skill `livery-latam`
5. **Details** — doors, windows, gear, engines, antennas, belly. The standard is
   a complete, connected aircraft, not a painted hull.
6. **Visual gate** — six canonical angles, contact sheet, comparison against the
   photo. → skill `verificacao-visual`

```bash
python3 verificacao_visual.py "boeing 787-9"
```

## Skills

The pipeline is encoded as skills under [`.claude/skills/`](.claude/skills/) —
each one carries the traps that already cost rework.

| Skill | Phase |
|---|---|
| [`nova-aeronave`](.claude/skills/nova-aeronave/SKILL.md) | router: end-to-end pipeline for a new or derived aircraft |
| [`fontes-aeronave`](.claude/skills/fontes-aeronave/SKILL.md) | official ACAP/APR, registration photos, open CAD and licensing |
| [`extrair-cotas`](.claude/skills/extrair-cotas/SKILL.md) | drawing and photo → `curves.json` + `spec_<type>.json` |
| [`casco-parametrico`](.claude/skills/casco-parametrico/SKILL.md) | hull, wings, empennage and details in Blender |
| [`livery-latam`](.claude/skills/livery-latam/SKILL.md) | official mark, paint as UV texture, tail sash, materials |
| [`blender-mcp`](.claude/skills/blender-mcp/SKILL.md) | driving Blender over MCP: timeouts, render-file race |
| [`verificacao-visual`](.claude/skills/verificacao-visual/SKILL.md) | quality gate: 6 angles, contact sheet, checklist |

[`FONTES-FROTA.md`](FONTES-FROTA.md) is the inventory of the fleet's 12
variants: verified official document per type, useful open CAD, recommended
strategy.

## Coordinate frame

The whole repository uses one frame — mixing frames is the easiest way to
produce a crooked aircraft:

- **x = 0 at the nose tip**, increasing aft, in metres
- **z = 0 at mid-height of the constant section**, positive up
- **y = 0 on the symmetry plane**, positive to starboard

Watch out for manufacturer datums: Airbus stations are measured from an X0 that
sits 2540 mm ahead of the nose tip (`x = STA − 2540`), and the same family mixes
units between the SRM and the AMM.

## LATAM palette

| Colour | Hex | Where |
|---|---|---|
| White | `#E6E7EA` | fuselage |
| Indigo | `#2A0088` | fin, wordmark, rear wedge |
| Coral | `#ED1651` | fin bands, symbol |
| Flight gray | `#C8CACC` | light fin bands, leading-edge fillet |

## Fidelity rules (non-negotiable)

**0. Look at the aircraft before modelling.** Finding photographs of the real
registration is the first step — before the ACAP, before the spec, before any
research. It is not the validation at the end; it is the starting point, and it
costs a minute. **No prose description substitutes for seeing the aircraft**, not
even when the prose came from photogrammetry, not even when it survived
adversarial review. On the 787-9 the spec described an indigo sash running down
the hull to the tailcone; hours of photogrammetry, drawing measurement and agent
review missed the error — the first photo on Google settled it in seconds.

**1.** Exact mark: import the official vectors — never approximate with a
lookalike font.

**2.** Application as flown — checked against the photo, not against the
description.

**3.** Geometry from the manufacturer's document: dimensions, doors, gear,
engines.

**4.** When spec and photo disagree, **the photo wins** — and the spec is
corrected on the spot, with the reason written down, or the error comes back on
the next aircraft derived from it.

**5.** Nothing ships without passing the visual gate, and "passing the gate"
means **opening the images and looking** — not generating the files and assuming.

## How the tail was solved

Worth recording as an example of the method, because it is the part that
resisted longest. The LATAM sash is a set of **parallel bands crossing the fin
edge to edge**, each one flight-gray at both ends with a coral core, over an
indigo field. Earlier versions had a white fin with thick bands — wrong.

The geometry came out of a photograph of CC-BGP **rectified onto the plane of
the fin** by an affine transform, which turns the problem into direct reading in
`(x, z)`. Band slope `dz/dx = 0.372` (20.4°), band thickness 0.96 m
perpendicular, indigo gap 2.42 m, period 3.38 m. A closure test that needs no
calibration at all: the zones summed along the band normal
(2.09 + 0.96 + 2.42 + 0.96 + 1.25 = 7.68 m) only fit the fin planform at 20.4°.

The rear-fuselage indigo is bounded by three surfaces, and **they do not all
live in the same space** — missing that cost four rounds:

```
indigo ⟺ x ≥ 48.77 + 0.992·z          (forward: parallel to the straight LE, +0.86 m)
      ∧  θ ≤ 117.0 − 5.2·(x − 48.70)   (lower: a straight line in (x, θ), not (x, z))
      ∧  x ≤ 57.14 + 0.3858·z          (rear: the fin trailing-edge line)
```

Three traps worth carrying to any photo measurement:

- **Never calibrate on the aircraft's overall length.** A slight yaw shortens the
  nose-to-tail span; on one CC-BGP photo that was a 14% error — and because the
  error is a scale factor, it displaces *every* measurement plausibly. Use window
  pitch, which is a repeated dimension.
- **Check camera ELEVATION, not just yaw.** With the camera off-axis by `e`,
  every skin point is displaced by `w(z)·sin(e)`, where `w` is the local
  half-width — zero at the crown, ~2.9 m at the waist. That bends the projection
  of any boundary on the hull by up to 0.44 m at only 8.5°.
- **Colour thresholds cannot separate same-coloured parts that overlap in
  projection.** Measuring the rear wedge by "which pixels are indigo" failed
  repeatedly because the fin is also indigo and covers the hull in side view.

## Reproducing

Blender 5.2+. Open the aircraft's `.blend` and render — textures and materials
are packed into the file.

To run the pipeline from scratch you need the manufacturer documents and the
brand vectors, which are **not in this repository** for licensing reasons.
[`NOTICE.md`](NOTICE.md) lists each one and where to get it.

## Licence

- Code, skills and engineering data: **[MIT](LICENSE)**
- 3D models, renders and animations: **[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)**

**LATAM**, **Airbus**, **Boeing** and **Dreamliner** are trademarks of their
respective owners. This is an independent, non-commercial project with **no
affiliation, sponsorship or endorsement** from any of them. Details and excluded
third-party material: [`NOTICE.md`](NOTICE.md).
