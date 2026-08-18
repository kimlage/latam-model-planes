# Would a LATAM SCL employee recognise this? — skeptic's pass

Reviewed: `scl_osm.json`, `TERRENO.md` + `terreno/`, `scl_referencias.md`, `scl_operacao.md`.
Own photographic check: 8 images opened and read directly (5 newly downloaded).
Date: 2026-08-18.

**Verdict: not as currently specified.** The geometry, the terrain and the operational
data are good. But the document that defines the *framing* of the scene —
`scl_referencias.md` — puts the aeroplane on the wrong runway, and therefore puts the
whole airport on the wrong side of the aircraft. Build to it as written and the employee
sees their own base mirrored. Fix that one thing and the scene becomes buildable.

---

## 1. The blocking error: wrong departure runway

`scl_referencias.md` §1 states the departure is from **17L**, and builds its entire
landmark table on "everything passes on the RIGHT". Its cited source is an OPSGROUP blog
post titled *"Temporary Runway Changes"*, read as a general rule.

It is not a general rule. It is the **00:00–07:00 noise-abatement exception**.

> "Preferential TKOF RWY 17L and 17R with tailwind up to 10 KT. **The primary departure
> runway is 17R**, except between 0000 and 0700 local time when it is not available for
> noise abatement reasons."
> — Route Information Manual, SCEL, DEPARTURE section
> (https://planning.simfest.co.uk/rim/SCEL.pdf), which also gives
> "The primary landing runway is 17L which is CAT IIIB capable."

This corroborates `scl_operacao.md` §1, which cites AIP-CHILE AD 2 SCEL §1.2 directly:
segregated mode, **17L ARR / 17R DEP**. Two independent sources agree. `scl_operacao.md`
is right; `scl_referencias.md` is wrong.

**Consequence, computed in the project frame:**

| | on 17L (as written) | on 17R (actual) |
|---|---|---|
| LATAM MRO | 647 m to the **RIGHT**, at 1287 m of roll | 914 m to the **LEFT**, at 1816 m of roll |
| Andes | LEFT | LEFT |
| Named features to the right of the aircraft | all of them | **zero** |

I projected every named feature in `scl_osm.json` onto the 17R take-off axis. **All 34 of
them fall on the left.** West of 17R there are eleven building footprints, none named,
nine of them outside the aerodrome fence. The right side of a 17R departure is empty
grass.

**The correction is an improvement, not a loss.** On 17L the two recognition anchors — the
LATAM base and the cordillera — sit on *opposite* sides of the aircraft and cannot be
framed together. On 17R they are on the *same* side, and stack.

Also note the base comes abeam at **1816 m**, which for an A320 is at or just after
rotation — better cinematically than the 1287 m figure it replaces.

Secondary: the two docs place the MRO 25–40 m apart along-track. `scl_osm.json` records
that **no threshold node exists for 17R in OSM** and that zero displacement was *assumed*;
`scl_operacao.md` had the AIP. Take the AIP figure and reconcile once.

---

## 2. The shot that actually works

Camera **west of RWY 17R, looking east**, late afternoon, sun behind camera. The aircraft's
starboard side is lit, and everything the employee knows stacks in depth behind it:

| behind the aircraft | distance | apparent height |
|---|---|---|
| LATAM MRO | 1 915 m | 0.57° (at an assumed 22 m) |
| Torre de Control SCL | 1 913 m | 1.71° (60 m) |
| Terminal 2 | 2 430 m | 0.52° (25 m) |
| **Andes crest behind the MRO (az 93°)** | **54.8 km** | **3.40°** |
| Andes crest behind the tower (az 108°) | 34.5 km | 4.06° |

(camera at x=−2500, y=−1200, eye 3 m, in the existing frame.)

**The mountains sit about six times higher in frame than the MRO and roughly 2.4× higher
than the 60 m control tower.** That ratio is the thing to get right. Everything built is
low and flat; the wall behind it is not.

**A correction worth having:** from the LATAM ramp itself, an employee watching a
departure looks **west** — 17R is 982 m west of the Plataforma LATAM, 17L is 647 m east of
it. So the view they have of their own aircraft leaving has the **brown Coastal Range and
the setting sun behind it, not the Andes**. The Andes are at their back. Aircraft they see
against the Andes are *arrivals* on 17L. Getting this backwards is a subtle, persistent
wrongness.

---

## 3. What makes recognition happen, in order of weight

**1. The Andes wall — shape and angular scale.** Best-covered element in the project.
`terreno/` is validated against two independent DEMs and a sibling's independent
calculation. The 2–5° angular band is the number that stops the classic error of modelling
the range too large. Cerro El Plomo (az 74°, 55 km) and the Sierra de Ramón wall (az 108–111°,
34 km) are the anchors; Aconcagua and Tupungato are correctly excluded as blocked.
*Minor caveat nobody flagged:* the horizon was computed at the 17L threshold, 1.6 km east
of where the camera now sits. For 34–55 km peaks the azimuth shift is 1.7–2.7° and the
elevation shift negligible — reusable, but say so rather than assume it.

**2. Aircraft on the ground. — NOT COVERED AT ALL.** This is the largest uncovered item and
I think it outranks every building. An employee does not recognise footprints; they
recognise *the ramp with their own tails on it*. `scl_osm.json` maps 208 parking positions
and 65 jet bridges with their real designators (A01…A16, B01…B09, C1…C11, D1…D10, E1…E12,
F1…F9, W1…W9) — the sockets exist and nothing has been said about filling them. An empty
SCL reads as a construction site. Needed: LATAM dominant, widebodies nose-in on the
Plataforma LATAM, Sky (purple/green) at its own base, JetSmart (orange) and the foreign
carriers at T2. In `spotting_2012_otherside.jpg` the row of tails *is* the terminal's
silhouette; the building behind is barely legible.

**3. Haze / aerial perspective. — described, never quantified.** Both docs say "haze is not
optional" and stop. It is the single strongest "this is Santiago" lever and it carries no
numbers anywhere in the deliverable. My own reading of the photos: in
`spotting_2012_otherside.jpg` the terminal at ~1.5 km has already lost most of its
contrast, and the cordillera is **completely invisible** — a flat grey wall. In
`latam_a320neo_landing_scel_2025.jpg` the range behind is a pale desaturated blue at very
low contrast. This needs an extinction coefficient with a stated visibility, not an
adjective.

**4. The bare ochre infield.** Covered well by `scl_operacao.md` §7 and confirmed in every
photo I opened. Cheap, high-impact, and a green European infield would break the scene
instantly.

**5. The LATAM MRO buildings. — the honest hole.** No daytime photograph exists. I searched
Wikimedia Commons three ways (geosearch within 1.2 km of the MRO centre, 56 results; plus
three text searches) and there is **nothing**. The sibling's conclusion was correct, not
lazy. What *is* confirmed: the illuminated "LATAM" sign with the coral brandmark, high on
a facade above 2–3 lit office floors — but the evidence is a small distant blur seen
through Sky's hangar door at night (`_detalhe_letreiro_latam_noite.jpg`, which I opened).
Facade colour, cladding, and hangar-door count remain unknown. Heights are unknown: of 748
buildings extracted, 4 have a height tag. At 914 m lateral in a moving shot this matters
less than items 2–4, but it is the thing the employee is most entitled to be picky about.

**6. The control tower silhouette.** One usable photo, and the description in
`scl_referencias.md` §3.3 undersells it. Looking at `apron_panoramio_2011.jpg` myself: the
identity is a **pronounced outward-flaring conical collar** under the cab, much more
dramatic than "cabine mais larga que o fuste", plus a dark shaft with a lighter vertical
strip, a small mid-height balcony, and the horizontal-bar radar on the roof deck. Height is
disputed, 60 m (OSM) vs 65 m (DGAC) — 8 % of the tower, and it is the tallest thing on the
field.

**7. The DGAC building. — missing entirely.** Visible in the same photo directly beneath
the tower: a long low grey block with a distinctive perforated/dotted panel facade, a
continuous window band, and blue "DGAC Chile" lettering. It is not in any deliverable.

**8. Terminal roofline + the light masts.** Covered. The masts read as taller than the
terminal in every ground view and are a large part of the silhouette.

**9. Blue "Banco de Chile" jet bridges.** Excellent, well-sourced catch — but wrong scene.
At 2.8–3.5 km of roll the aircraft is airborne and 800 m away; the lettering will not
resolve. Keep it for a ramp-level shot.

**10. Airside face of the T2 piers.** Declared gap, still a gap: no free-licence photo
exists of the side that actually faces the runway. Inferred from plan and landside only.

---

## 4. What I checked myself

Newly downloaded (Wikimedia Commons API, geosearch + text search):
`Chilean Andes Sunset from the Airport - panoramio.jpg` (CC BY 3.0),
`LAN B787 at SCEL.jpg` (CC BY-SA 3.0),
`Aeropuerto de Pudahuel, Santiago Chile. - panoramio.jpg` (CC BY-SA 3.0),
`Comodoro Arturo Merino Benítez International Airport-CTJ-IMG 6744.jpg` (CC BY 3.0),
`FIDAE 2022 - BugWarp (34).jpg` (CC BY-SA 4.0).
Held in scratch only, not copied into the repo.

One claim I corrected from my own reading: `scl_referencias.md` §3.5 gives the cordillera
as uniformly "azul-acinzentada pálida, muito dessaturada". The sunset photograph shows the
opposite mode — warm pink alpenglow, high contrast, full relief detail. Both are real; the
scene has to pick one, and the ops doc's late-afternoon recommendation lands squarely in
the alpenglow case, not the pale-blue one. The two documents are quietly inconsistent here.

Also worth recording: `hangar_sky_2021.jpg` is the interior of **Sky's** hangar, not
LATAM's. The truss and roof description in §3.1 is therefore Sky's structure being used as
a proxy for LATAM's. Reasonable, but it should be labelled as inference.

---

## 5. Order of work to make the answer "yes"

1. **Move the departure to 17R and mirror the framing.** Blocking; everything downstream
   depends on it.
2. **Populate the aprons.** Highest recognition return per unit effort; the sockets already
   exist in `scl_osm.json`.
3. **Put a number on the haze.** Pick a visibility, derive the extinction, apply it.
4. **Bare ochre infield, not grass.**
5. **Reconcile the two along-track datums** and settle the tower height at 60 or 65 m.
6. **Accept the MRO facade as unknown** and model it as a declared range (18–25 m door
   height), flagged in the file — do not invent it, and do not let it hold up the rest.
