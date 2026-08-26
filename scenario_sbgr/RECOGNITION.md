# What makes SBGR recognisable — and what would make it wrong

The yardstick stands for the third time: **someone who works this ramp every
day should recognise the place.** At Guarulhos that person is a LATAM
mechanic walking out of the 777 hangar. Sibling of
`../scenario_sdsc/RECOGNITION.md`; read with `sbgr_references.md` §3.

---

## 1. Which way round is it? — the mirror question

**Departures are from RWY 10L — ESE-bound, true track 073.65 — in the east
flow that stands about two-thirds of the time.** The evidence chain
(`sbgr_aip_survey.json → which_runway_for_the_departure_clip`):

| evidence | value |
|---|---|
| AGMC chart set | DEP charts for all four ends; the only ARR chart is **10R** |
| CAT III | on **10R** — the south runway is the low-visibility *landing* runway |
| intersection-departure notes | protect full length on **10L** (TWY H) and **28R** (TWY P) only — the north runway is the departure runway in *both* flows |
| TORA | north 3 700 m vs south 3 000 m — the 777 wants the north |
| ERA5 2021–2025 | east flow available **67.4%** of hours; ~78% mornings; **dips to 39–46% at 12–15 local** (sea-breeze turn); 62% again by 17:00 |

**On a 10L departure the LATAM hangar is on the LEFT**, abeam at **2 575 m**
— right where a heavy 777 rotates — **654 m** off the centreline, with the
American Airlines hangar just before it and the whole terminal frontage
(T2 at 325 m, T3 at 983 m along) playing past earlier in the roll. The only
things on the RIGHT are the air base (BASP) and the GA block.

Build it mirrored and the mechanic watches the aeroplane rotate over the
wrong shoulder. **Do not accidentally build São Carlos**: there the base is
on the *right* at 800–1 300 m; here it is on the *left* at 654 m, closer,
bigger, and backed by terminals instead of cane.

---

## 2. The six things that say "Guarulhos" and not "some airport"

1. **Two parallel runways almost touching.** 3 700 m and 3 000 m, centrelines
   ~375 m apart, both on 073.65 true. Aircraft hold between them; a landing
   and a departure run side by side. No other Brazilian airport looks like
   this from the ground.
2. **The tower.** A bare concrete shaft with a two-ring gallery, glazed cab
   and a **white radome ball**, standing among the terminals on the north
   side (ENU ≈ 301, 1323). Three photographs and two chart labels agree.
3. **The city at the fence.** Guarulhos — 1.3 M people — presses against the
   north and east boundaries: sheds, houses, mid-rises, red-soil lots. The
   middle distance is CITY. The only green gap is the Rio Baquirivu-Guaçu
   belt along the north edge. The anti-São-Carlos.
4. **The ring.** The Cabuçu spur of the Serra da Cantareira stands
   **1.8–3.2°** tall across the whole northern horizon at 4–5 km, the
   Cantareira crest and the Jaraguá sector 1.2–2.2° across the west, a near
   ridge 1.5–2.1° SSE. Only the departure direction ESE is low (0.22–0.72°).
   From the ramp, the ridge is the backdrop of everything.
5. **The NE maintenance corner.** The LATAM hangar (137×92 m, ridge-line
   parallel to the runways) beside the American Airlines hangar
   (179×95 m, perpendicular) over the numbered remote stands 901–912.
   That L-shaped pair of big roofs is the corner's signature from the air.
6. **Heavies everywhere, and the mast forest.** 747s, A340s, 777s at the
   piers in every era of photograph; ILS approach lattices off both ends;
   two designs of floodlight mast walking the frontage. This is South
   America's biggest international ramp and has to read busy.

---

## 3. Light

`sbgr_operations_sun.json`. Latitude −23.43: **the Tropic of Capricorn runs
through São Paulo**, so at the December solstice the noon sun is at **89°** —
literally overhead, shadowless. June noon is 43° toward the north.

- **Morning east flow** (78% of non-calm hours): the 10L roll points within
  10° of the June sunrise azimuth (065°). A dawn departure rolls INTO the
  sun through fog — photographed exactly so in
  `refs/thr_09l_lineup_dawn_2012.jpg`.
- **The raking light** is after ~16:00: December 17:30 puts the sun at 16.5°
  up, 251° true — behind a south-west camera looking north-east at the
  hangar line with the Cantareira behind. **But 12–15 local is when west
  flow is most likely** (ERA5); by 17:00 east flow is back to 62%. Check
  flow and light together before framing the clip.
- No DST in Brazil since 2019; UTC−3 year round.

---

## 4. The traps, in the order they will catch you

1. **Building on the designator.** 10L/28R is magnetic; the true track is
   **073.65°**. VAR is 22 W on the charts. Lay the field out on 095 and it is
   rotated 21° against the terrain, the sun and the city.
2. **Trusting old signage in photographs.** Until mid-2019 these runways were
   **09L/09R–27L/27R**, and most free photographs (2007–2017) show 09/27 on
   signs and captions. Same pavement, renamed. The build paints 10/28.
3. **Treating the published thresholds as exact.** They are whole seconds
   (±30 m). The OSM centreline tracing is the finer relative geometry and the
   adopted bearing; the survey records the reconciliation. Do not mix the two
   silently.
4. **Believing the DSM's building heights.** Copernicus is a 2011–14 surface
   model: it reads Terminal 3 and the LATAM hangar as FLAT GROUND. Every
   height for post-2014 structures is phase-2 inference, declared as such.
5. **Reading 790/810 as PCN.** They are **PCR** values (the post-2024 ICAO
   system, ROTAER footnote [9]); SDSC's PCN 47 is a different scale entirely.
6. **Copying the 2017 photo's livery.** PT-MUH wears TAM colours in the only
   free 777-at-GRU frame. The scenery's aircraft are the repository's
   masters in current LATAM livery; the *hangar* branding is unphotographed
   and therefore declared inference either way.
7. **Forgetting the afternoon flow swing.** GRU is H24 and ATC-flowed; a
   13:00 scene departing 10L fights a 54–61% chance the field is actually on
   the 28s at that hour. Morning or ~17:00 keeps the 10L departure honest.
8. **Inventing stand allocation.** 215 parking positions and 171 gates are
   mapped, but nothing published says which are LATAM's. If the ramp shows
   LATAM tails at specific gates, that is a decision to declare.
9. **Importing SDSC's terrain habits.** There is no 35 m platform, no runway
   crest, no graded-function machinery needed — the whole field spans 6 ft of
   published elevation. The GRU trap is the opposite: believing a *surface*
   model in a city (buildings and trees are in the DEM everywhere outside
   the fence).
10. **Rendering an empty surround.** At São Carlos the missing surround was
    cane; here it is a metropolis. A bare green ring around the fence would
    be as wrong as the floating aerodrome was. Phase 2 must decide HOW to
    show the city (landuse tint + procedural blocks + the mapped major
    roads/rail), but not WHETHER.
