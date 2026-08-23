# What makes SDSC recognisable — and what would make it wrong

The yardstick the owner set for Santiago holds here: **a LATAM MRO mechanic who
works at São Carlos every day should recognise the place.** This file is the short
list of the things that decide that, and the mistakes that are available to make.

Sibling of `../scenario/RECOGNITION.md`. Read it with `sdsc_references.md` §3, which
carries the photographic evidence for everything asserted here.

---

## 1. Which way round is it? — the mirror question

At Santiago this was the scar: an earlier round put the whole base on the wrong side
because it assumed the wrong departure runway. Here is the SDSC answer, with the
evidence.

**Departures are from RWY 02 — northbound, true track 001.026°.**

| evidence | value |
|---|---|
| wind favouring 02, all hours | 53.4% |
| wind favouring 02, **during the aerodrome's published opening hours** | **63.2%** |
| slope | RWY 02 is **downhill**, 10.06 m over 1 620 m |
| TORA | 1 672 m on 02 against 1 668 m on 20 |
| crosswind above 15 kt | 0.03% of hours — the wind almost never forces the choice |

Wind figures are ERA5 2021–2025, `sdsc_operations_wind.json`. **Nothing forces 02**;
the aerodrome is VFR with AFIS, not an ATC-assigned flow, and both ends have RNP
approaches. But every indicator leans the same way, and 02 is also the direction that
makes the shot work.

**On a RWY 02 departure the LATAM MRO is on the RIGHT.** It comes abeam between
**1 602 m and 1 937 m** into the roll — at or just after rotation — at **797 to
1 287 m** off the centreline. The only thing on the **LEFT** is the **Aeroclube de
São Carlos**, in the first 500 m of the roll, 180–280 m out: five small GA hangars,
a small terminal, a windsock and a handful of light aircraft.

Build it mirrored and a mechanic sees their own base on the wrong side.

**Do not accidentally build Santiago's geometry.** At SCL the base is 620–720 m off
the centreline and is abeam at 1 200–1 300 m — *before* rotation. Here it is roughly
twice as far out and comes abeam *after* rotation. It is a smaller, more distant
object seen from higher up.

---

## 2. The five things that say "São Carlos" and not "some airport"

1. **The runway is nearly true north–south and it is short.** 1 720 m of pavement,
   1 672 m of TORA, 45 m wide, single runway, no parallel taxiway for most of its
   length. Everything about the field reads *small* until you see what is parked on it.
2. **The hangar line and the row of aircraft in front of it.** Light-grey ribbed
   metal, very shallow roofs (one barrel vault, others near-flat), a broad **dark
   red-maroon fascia band** under the eave carrying the wordmark, and five or six
   airliners parked **nose-in in a line** along the frontage. That row is the base.
3. **The ground is red.** Brazilian latosol — red-brown where bare, strong green grass
   in the wet season, olive and dusty in the dry. Nothing like Santiago's pale ochre.
   `refs/ga_cessna150_2007.jpg` is the colour reference.
4. **Sugar cane.** The field is surrounded by cane and pasture, right up to the
   boundary. `refs/mro_centro_tecnologico_2009.jpg` is taken *through* a cane field
   with the hangars on the skyline.
5. **The floodlight masts** are the tallest built objects over the ramps — four of
   them are visible in `refs/sdsc_field_from_sp318_2013.jpg`. **But they are short.**
   Measured in that frame against the hangar beside them (`sdsc_references.md` §2.1,
   the phase-2 correction), the lamp clusters sit within about a metre of a 12.7 m
   apex. These are ~16 m masts, not the 30 m high-masts an international apron
   carries, and Santiago's figure must not be copied across.

---

## 3. The horizon is a number, and the number is "none"

`TERRAIN.md` §3: the whole 360° horizon band spans **−0.32° to +1.30°**. There is no
skyline. The only relief a camera will notice is a **low rise 1–3 km west of the
runway, ~40 m above field level, up to 1.30°** — and it is *behind* a 02 departure as
seen from the east.

Two consequences that are easy to get wrong:

- **A terrain mesh alone will render a horizon that is too low and too clean.** At a
  third of all azimuths the real horizon is vegetation and buildings inside 1.5 km,
  not terrain. The scene owes itself a tree line.
- **The runway is not level.** It falls 10 m to the north. On a long lens down the
  centreline that is visible, and it changes where the horizon cuts a departing
  aircraft.

---

## 4. Light

`sdsc_operations_sun.json`. Latitude −21.88, so the sun is high: **87° at noon at the
summer solstice, and never below 45° at noon even in winter.** A midday shot at São
Carlos is flat, top-lit and unflattering — the opposite problem from Santiago, where
the danger was the sun being too low.

For a raking light on a northbound RWY 02 departure the sun must be in the **west**,
i.e. **16:00–18:00 local**, which also puts it behind a camera placed west of the
runway looking east at the MRO — the framing of
`refs/sdsc_field_from_sp318_2013.jpg`.

| date | 16:00 | 17:00 | 18:00 | sunset |
|---|---|---|---|---|
| 21 Dec (summer) | 37.2° / 256.5° | 23.8° / 253.1° | 10.7° / 248.9° | 18:54, az 244° |
| 26 Sep (hangar 9 anniversary) | 28.9° / 280.9° | 15.1° / 274.5° | 1.2° / 268.8° | 18:09, az 268° |
| 21 Jun (winter) | 18.7° / 306.0° | 6.9° / 298.7° | — | 17:37, az 295° |

Brazil has had **no daylight saving since 2019**; local time is UTC−3 year round.

Note that the aerodrome's published service hours end at **20:00 local Mon–Sat**
(18:00 Sun) and **the runway lights are switched on only by request, four hours'
notice**. A night departure from SDSC is not a normal event.

---

## 5. The traps, in the order they will catch you

1. **Modelling the runway on its designator.** It is 02/20 but its true bearing is
   **001°**. Brazil's magnetic variation here is **22° W**. Build it on 020° and the
   whole field is rotated 19° against the terrain, the OSM footprints and the sun.
2. **Following OSM's `wikidata` tag on the MRO polygon.** It points at the **Museu
   TAM**, which closed in 2016. The polygon is the maintenance base.
3. **Believing OSM's building set.** Every MRO footprint in OSM is **version 1 from a
   single tracing session on 2017-07-27**. **Hangar 9 (opened 2025-09-26) is not
   there.** Neither, probably, is anything else built since 2017.
4. **Counting hangars from OSM.** LATAM says nine. OSM tags four polygons `hangar` on
   the MRO site — plus five more that belong to the **Aeroclube**, on the other side
   of the field. The counts do not reconcile; do not force them.
5. **Painting the base in TAM red.** Every free-licence photograph of this site is
   2006–2014, when it was TAM. It has been **LATAM since 2016** and no photograph of
   the base in LATAM colours was found. Whatever you do here is inference — say so.
6. **Putting a 777 on the ramp.** CNN Brasil's feature on the base states 777
   maintenance is done at **Guarulhos**, not São Carlos. It is the one LATAM type with
   positive evidence *against* it being here.
7. **Building the MRO at runway level.** Copernicus and SRTM both put the platform
   ~35 m *below* THR 02. Measured, but unconfirmed — check it, don't assume either way.
8. **Assuming an ADC exists.** It does not. SDSC is VFR and DECEA publishes no
   aerodrome chart. Every marking, taxiway designator and stand position is
   unpublished. Anything you draw there is an estimate and must be labelled one.
