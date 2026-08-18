---
name: nova-aeronave
description: Complete pipeline for building (or resuming) the 3D replica of a LATAM fleet aircraft in Blender — from the manufacturer's official document to a model approved at the visual gate. Use ALWAYS when the request involves starting, continuing, deriving or refining an aircraft in this repository: "let's build the 767-300ER", "model the A321neo", "duplicate the A320 into an A319", "continue the 787", "why does the model look different from the photo". Also use when someone asks how the project works or what the order of the steps is. This skill is the router — it decides which of the specific skills (fontes-aeronave, extrair-cotas, casco-parametrico, livery-latam, verificacao-visual, blender-mcp) takes over in each phase.
---

# New aircraft — the project pipeline

This repository exists for one thing: replicas that a LATAM engineer would
recognize as their own aircraft. The bar is not "it looks like an airplane" — it
is "the dimensions match the manufacturer's document and the paint matches the
photo of that registration".

Two aircraft have already been through this pipeline (A320neo/PT-TMN and
787-9/CC-BGK). Almost all of their cost was rework caused by skipping a step.
The order below is the result of that rework — follow it even when modelling
"by eye" looks faster.

## Rule zero: look at the aircraft before anything else

Before the document, before the spec, before opening Blender: **find photos of
the real registration and look at them**. One minute of `WebSearch` or
JetPhotos. If the owner sent a photo, that is the highest-authority source in
the project.

This is not end-of-line validation — it is the starting point, and it exists
because it already failed expensively: the 787-9 spec described an indigo sash
on the hull that simply **does not exist** on the real aircraft. That
description survived photogrammetry, drawing measurement, two research
workflows and adversarial verification. The first photo on Google settled it in
seconds.

Seeing the aircraft is what lets you get the fine detail right — and what stops
you from spending hours carefully refining something that should not be there
at all. Details in `fontes-aeronave`.

## The rule that organizes everything: data before mesh

Never model before you have a number. If the dimension exists in an official
document, looking it up costs minutes; finding out later that the whole hull is
wrong costs hours plus a round of frustration from the project owner. Every
time the model diverged from the photo, the cause was the same: someone
estimated where data was available.

When the data does not exist in a document (livery application, exact shade,
weathering), measure it in a photo by photogrammetry — that is data too, with a
declared uncertainty. What is not acceptable is guessing.

## The six phases

### 1. Sources — before opening Blender
Obtain the official dimensional document (Airbus ACAP / Boeing APR), the photos
of the specific registration to be replicated, and whatever open CAD exists as
a blocking reference.

→ Use **`fontes-aeronave`**. The ready-made inventory of the 12 fleet types is
in [FONTES-FROTA.md](FONTES-FROTA.md) — start there.

Before treating the aircraft as new, check whether it is a derivative of one
already built. The fleet shares a lot of airframe (A320ceo/neo, A321ceo/neo,
767-300ER/-300F/-300BCF, 787-8/-9). Deriving by parametric stretch/plug from a
validated hull is faster and more faithful than extracting from scratch — but
validate the derivative against its own 3-view, because doors, gear and wingtip
change.

### 2. Extraction — the dimensioned drawing becomes numbers
Rasterize the PDF views at 600 dpi, calibrate against a printed dimension,
extract crown/keel/half-width, and write `<aircraft>/<type>_curves.json` +
`spec_<type>.json`.

→ Use **`extrair-cotas`**.

The `spec_*.json` is the most valuable artifact in the repository: it is what
survives any rebuild of the model. Treat it as the source of truth and keep it
up to date whenever you measure something new.

### 3. Hull and structure — the geometry
Sparse control cage on the real frames + Catmull-Clark subsurf, ovoid sections
in the nose, wings/empennage by NACA loft, roots buried inside the body.

→ Use **`casco-parametrico`**.

### 4. Livery — the brand
Official brand vectors (never a lookalike font), application measured on the
photo of the registration, paint as a UV texture `(x,θ)` — not as a 3D shell.

→ Use **`livery-latam`**.

### 5. Details — the whole aircraft
Doors, windows, landing gear, engines, antennas, belly. The owner has already
rejected a model with "vários elementos desconectados da carroceria"
[several elements disconnected from the body] and "trens de pouso fora voando"
[landing gear floating outside]: the criterion is the complete, connected
aircraft, not the painted hull.

Covered by `casco-parametrico` (analytic geometry on the surface) and
`livery-latam` (outlines and markings painted into the texture).

### 6. Visual gate — only then is it done
Render the 6 canonical angles, build the contact sheet and **look**, comparing
against the reference photos.

→ Use **`verificacao-visual`**. Nothing ships without passing through here.

In any phase that involves talking to Blender, **`blender-mcp`** has the
operational traps (socket timeout, render-file race, stale matrix) that have
already caused expensive false diagnoses.

## Folder structure

One folder per aircraft, at the repository root, named after the commercial
designation in lower case (`airbus A320neo/`, `boeing 787-9/`). Inside:

| File | What it is |
|---|---|
| `<TIPO>_LATAM.blend` | the model |
| `spec_<tipo>.json` | engineering specification — the source of truth |
| `<tipo>_curves.json` | raw outlines extracted from the drawing |
| `<tipo>_hull_smooth.json` | densified curves (PCHIP) ready for lofting |
| `extract_<tipo>.py` | the extraction script for that drawing, with its anchors |
| `<DOC>_<fabricante>.pdf` | the official document |
| `render_*.png` | the 6 canonical angles |
| `insp_*.png` | inspection crops used to anchor/measure |
| `verificacao_visual.png` | the gate's contact sheet |

Shared at the root: `latam_livery_kit.py`, the official brand SVGs,
`verificacao_visual.py`, `FONTES-FROTA.md`, `README.md`.

## Reusing work between aircraft

The second aircraft cost a fraction of the first because it reused. When
starting a new one, duplicate the `.blend` of a finished aircraft: materials,
cameras, set and world come along, and the cameras only need rescaling by the
length ratio (787/A320 = ×1.672). The official brand marks can be imported from
the other blend with `bpy.data.libraries.load` — it is the same brand, so it is
literally the same geometry, with no risk of drift.

## When a better spec turns up

Owner's directive: **better spec found → refine what already exists.** If
research turns up a newer or more precise document for an aircraft already
built (e.g. ACAP A320 Rev 46 from Jul/2026 replacing the Jun/24 in use), diff
the drawings and adjust the model. Do not let the old model diverge from the
best available source just because it "was already finished".

## A word about pace

The real cycle is: build → render → look → the owner points out the defect →
fix. You will go around many times. The expensive laps are the ones that burn a
whole round to discover something a 320 px render would have shown. Render
cheap and early, look at it yourself before showing it, and only call the owner
when you have something you would approve yourself.
