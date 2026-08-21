---
name: fontes-aeronave
description: Gather the sources for an aircraft before modelling — the manufacturer's official dimensional document (Airbus ACAP / Boeing APR), reference photos of the specific LATAM registration, and open CAD/3D models usable as a blocking reference. Use ALWAYS when you need dimensions, dimensioned drawings, reference photos or existing models of an aircraft: "find the 777 measurements", "where is the 767 drawing", "is there ready-made CAD for this aircraft?", "I need photos of the tail", "what are the real dimensions". Also use before starting any new aircraft, and whenever the model is diverging from reality and the cause may be missing data. Covers licensing — what may become mesh and what may only become reference.
---

# Sources for an aircraft

A faithful model starts in a document, not in Blender. This skill is about
getting the data — and about not contaminating yourself with a source you are
not allowed to use.

## Step zero: look at the aircraft

**Before anything else, find photos of the real registration and look at
them.** This is not the validation step at the end of the pipeline — it is the
first one, and it takes a minute: `WebSearch` for "<airline> <type>
<registration>", or JetPhotos / Planespotters / Wikimedia Commons. If the owner
already sent a photo, that is the highest-authority source that exists in the
project.

The reason is concrete. On the 787-9, `spec_b789.json` described an indigo sash
running down from the fin, along the hull, to the tailcone. That text made it
through photogrammetry, drawing measurement at 600 dpi, two research workflows
and a round of adversarial verification — and nobody caught it. Hours were
spent refining the shape of that sash: limiting it by z, then by angle, then
with a local dip so it would not erase the registration. **The first photo on
Google showed that the fuselage of CC-BGK is entirely white and the indigo
exists only on the fin.** The sash did not exist. All that refinement was fine
tuning of the wrong thing.

Two consequences that hold for any new aircraft:

- **Prose is not a substitute for a photo**, even when the prose came from
  measurement. A textual description is a second-hand reading; the photo is the
  aircraft.
- **When spec and photo disagree, the photo wins** — and the spec is corrected
  right then, with the reason written down, or the error comes back on the next
  aircraft derived from it.

The inventory already gathered and verified for the 12 variants of the LATAM
fleet is in [FONTES-FROTA.md](FONTES-FROTA.md): official URL per type,
verification status, useful open CAD and recommended strategy. **Always start
there.** If the requested aircraft is in it, the research is already done — just
confirm the URL still responds and move on. If it is not, research it and **add
the row to the file**, because the next aircraft will need it.

## The hierarchy of sources

Not every source carries the same weight. Mixing levels is how the model ends
up wrong.

**1. Manufacturer's dimensional document — the truth.**
Airbus publishes the *ACAP* (Aircraft Characteristics — Airport & Maintenance
Planning); Boeing publishes the equivalent as *Airplane Characteristics /
APR* (e.g. D6-58333 for the 787). Both are public, free, and carry dimensioned
3-views in vector CAD, plus positions for doors, landing gear, engines and
cockpit visibility envelopes. Every dimension in the model must trace back to
here.

**2. SRM/AMM and frame tables (FR/STA) — internal structure.**
They give the real frame spacing, which is what makes the hull smooth for the
right reason (see `casco-parametrico`). Not always available; when it is, it is
worth a lot.

**3. Photos of the specific registration — the paint and the finish.**
The ACAP does not say where the indigo sash crosses door 2. That is measured in
a photo.

**4. Open CAD/models — blocking and silhouette checking only.**
Never a base mesh. See "Licenses" below.

## Downloading the official document

The PDFs are over 10 MB — WebFetch cannot handle them. Download with `curl`
straight into the aircraft's folder:

```bash
curl -L -o "boeing 787-9/B787_APR_boeing.pdf" "<apr-url>"
```

Stability notes that have already cost time: Airbus moved the A320 family to
the `mediaassets` CDN (the URLs rotate — the stable entry point is the *Aircraft
Characteristics* page on the Airbus site); Boeing moved the ACAPs to
`content/dam/boeing/v2/airports/acaps/` and the old paths return 404. If a link
in FONTES-FROTA.md breaks, look for the landing page, not for the file.

Confirm you downloaded what you expected before spending time rasterizing:
plausible size, and a Read of the PDF on the 3-view pages showing the right
aircraft.

A single document usually covers a whole family (AC_A320 covers ceo and neo
with "ON A/C" blocks; D6-58333 covers -8/-9/-10 with separate 3-views). But the
A320 family has **one document per member** — AC_A320 covers neither the A319
nor the A321.

## Reference photos

Ask for or find photos of the **registration that is going to be replicated**,
not of the type in general. The LATAM livery changed between 2016 and today,
and the same aircraft has documented variations: PT-TMN left the factory with
its registration in white letters inside the indigo and today flies with the
registration in indigo over white. When the owner's photo disagrees with what
you found on the internet, **the owner's photo rules** — it is what defines the
target.

What a good photo source needs, in order of usefulness:

- **pure side profile, high resolution** (JetPhotos at 1920 px will do): that is
  where photogrammetry works, because the projection is nearly orthographic at
  mid-fuselage;
- **elevated angle** (from a terminal or jet bridge): shows the crown, where the
  sash begins;
- **view from below, on takeoff**: the only way to resolve the belly, which
  almost never appears;
- **close-ups of nose and tail**: for windshield and fin sash.

For how to measure from those photos (calibration, uncertainty, what is
trustworthy and what is not), see `extrair-cotas`, photogrammetry section.

## Where the photos go: links, never files

**Photographs never enter git. Their citation does.** They are CC0 / CC BY /
CC BY-SA works: share-alike conflicts with the CC BY 4.0 the models ship under,
and CC BY would require embedding the credit in the file. This is not optional
and it is not per-aircraft folklore — it is one convention, in one place:

    <aircraft folder>/refs/            the photographs (ignored by git)
    <aircraft folder>/refs/manifest.json   the citation (committed)

The manifest is schema `latam-refs/1`: a JSON object with `schema`, `subject`,
`policy` and `photos`, where every entry in `photos` carries at least

```json
{ "file": "refs/ref_CC-CWY_perfil_mia.jpg",
  "url": "https://commons.wikimedia.org/wiki/Special:FilePath/....jpg",
  "page_url": "https://commons.wikimedia.org/wiki/File:....jpg",
  "author": "Duncan Kirk", "license": "CC BY 4.0",
  "date": "2026-02-19", "resolution": "5398x3599",
  "notes": "what this photograph settled" }
```

`file` is relative to the aircraft folder; new photos go under `refs/`. Use
`file: null` for a source you consulted but did not download — the citation
still counts. Any extra key you need (`registration`, `view`, `ressalva`, …)
is allowed and preserved; only `url`, `author` and `license` are enforced.

Three commands, from the repository root:

```bash
python3 refs_fetch.py "boeing 767-300F"   # bring the photos back from the manifest
python3 refs_fetch.py                     # ... for the whole fleet
python3 refs_fetch.py --verificar         # RUN THIS BEFORE YOU COMMIT
```

`--verificar` checks that every entry carries URL + author + licence **and**
that no photograph is tracked by git or exposed to the next `git add`, and exits
non-zero if either fails. It is the check you cannot forget to run.

**Adding an aircraft:** create `<folder>/refs/manifest.json` in that schema and
nothing else. Do **not** add a folder-level `.gitignore` — the root one already
denies `**/refs/*` and re-admits only `*.json`/`*.csv`/`*.md`, so a photograph
is ignored the day it lands, whatever it is called. Every folder-level ignore
that used to exist for this was a rule someone had to reinvent, and a rule that
has to be reinvented is one that will eventually be missed.

**Record author and licence at download time, not later.** Four entries in this
repository are permanently incomplete because an early session downloaded the
file and not the credit; they now fail `--verificar` on every run and cannot be
published. Recovering it afterwards is sometimes possible — the Commons API
`extmetadata.Artist` field recovered three A320ceo authors — and sometimes not.

Wikimedia note: prefer `https://commons.wikimedia.org/wiki/Special:FilePath/<name>`
over a direct `upload.wikimedia.org` link. The latter starts returning 429 after
about ten anonymous originals; `refs_fetch.py` already derives the former from
`page_url`.

## Existing CAD and 3D models

They are useful — but for one thing only: **checking that you understood the
shape**. Silhouette, where the gear retracts, how the pylon meets the wing, the
proportion of the raked wingtip. Never to become the model's mesh.

Two reasons. The first is fidelity: someone else's model carries someone else's
errors, and you have no way of knowing which ones without checking against the
ACAP — and if you are going to check everything against the ACAP, model from
the ACAP. The second is licensing.

Sources that come up often and how to treat them:

| Source | Typical license | How to use |
|---|---|---|
| FlightGear (GitHub) | GPL — viral | Blocking reference for gear/doors/cockpit. Never copy the mesh. |
| Sketchfab | a lottery of CC badges (many NC/ND) | Silhouette checking, **after checking the badge on that specific model**. |
| GrabCAD | non-commercial, no redistribution | Look only. Uneven quality. |
| OpenVSP Airshow | clean parametric geometry | Excellent independent cross-check of the curves extracted from the raster. |
| CGTrader "free" | royalty-free, personal use | Prototyping livery application, at most. |

Personal use is not blocked by any of this, but the project is headed for a
portfolio and a video. A mesh contaminated by GPL or NC today becomes a
publication problem later, and there is no way to "decontaminate" a hull. The
project rule is simple and worth keeping: **ACAP as the dimensional source of
truth; open assets only as blocking/silhouette reference, never as a base
mesh.**

## Delegating the research to agents

What worked very well was running the research as a workflow of parallel agents
with a **structured output schema** — each agent returns an object with
numbers, not prose. The gain is not speed: it is that the schema forces the
agent to deliver coordinates in metres in the aircraft's reference frame,
instead of "the windshield is quite raked".

What makes a schema pay off:

- **declare the reference frame in the field text itself** — "x=0 at the nose
  tip, growing aft, z=0 at the mid-height of the constant section, metres";
- **ask for polygons, not adjectives** — `corners_xz: [[x,z], ...]` closing the
  outline;
- **ask for the validation alongside** — a field asking which known dimensions
  the result was cross-checked against, and the estimated uncertainty;
- **ask what distinguishes this aircraft from a similar one** — "what makes it
  read as an A320 and not a 737" extracts the detail that generic prose hides.

These workflows delivered the calibrated windshield geometry of the A320, the
FR1–FR12 frame table, the complete photogrammetry of the PT-TMN tail and the
measured livery of CC-BGK. That is how the `spec_*.json` of each aircraft was
born.

Trust, but verify: one workflow delivered "length 62.00 m" for the 787-9
because it read the ground dimension instead of the overall length — the right
value is 62.81 m to the tip of the tailcone, at z=+1.66. Every number coming
from an agent goes through the same sanity test against official dimensions
described in `extrair-cotas`.
