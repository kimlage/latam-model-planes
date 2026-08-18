# A real departure from SCL — the details a LATAM employee notices

**Scope.** Which runway, in which direction, with which paint, along which taxi
route, under which sun. Everything here is a published number or a number
measured from imagery; nothing is estimated by eye. Where two sources disagree,
both are printed.

**Local metric frame used throughout this document**

| | |
|---|---|
| Origin | **RWY 17R threshold** — where a LATAM departure lines up |
| Latitude / longitude | **33°22′19,02″ S / 70°48′13,38″ W** = −33.3719500, −70.8037167 |
| Threshold elevation | 472,7 m AMSL (aerodrome elevation 474 m / 1 555 ft) |
| Axes | x = East, y = North, z = up, metres (local ENU tangent plane, WGS84) |
| Scale at the origin | 1° lat = 110 911,09 m · 1° lon = 93 059,13 m |
| Take-off direction | true track **177,423°**, unit vector (+0,044960, −0,998989) |

> **Frame conflict — read this before building anything.**
> `scl_osm.json` and `lib/frame.py` put the scene origin on the **17L**
> threshold, on the argument that a departure on 17L keeps the LATAM base on the
> right. Operationally that is the wrong runway: the AIP assigns **17L to
> arrivals and 17R to departures** (source below). The two frames differ by a
> pure translation — to convert a point from the 17L frame into this one:
> `p_17R = p_17L + (+1582,57, −459,34)` metres.
> That sibling origin also sits **1,23 m** from the AIP-surveyed 17L threshold
> (it is an OSM node, not the survey point).

---

## 1. Which runway, and in which direction

**The departure is RWY 17R, heading south, true track 177,4°.** This is not a
wind guess — it is a published preferential-runway rule, and it holds in over
95 % of afternoon observations.

### The rule (AIP-CHILE, AD 2 SCEL-9, section AD 2.20 "Local regulations")

| § | Text (translated) |
|---|---|
| 1.1 | "According to the general traffic circulation that normally prevails in Santiago TMA, **the runways in use will be RWY 17L and 17R**." |
| 1.2 | "**Segregated mode will preferentially be applied: RWY 17L ARR, RWY 17R DEP.** Other crew requests are subject to ATC delay." |
| 1.3 | "Whenever wind intensity does not exceed **10 knots of tailwind**, runways 17L/17R will be used." |
| 1.5 | "Flight crews requesting to operate on runways 35R/35L will be subject to the delay determined by ATC." |

Corroborated independently by an airline route manual for SCEL: *"Preferential
TKOF RWY 17L and 17R with tailwind up to 10 KT. The primary departure runway is
17R"* and *"The primary landing runway is 17L which is CAT IIIB capable."*

So: **17 essentially always; north-flow (35) is the exception, not a coin-flip.**

### The night exception — this one changes the answer

*AIP AD 2.21 Noise abatement:*

- **§1.1 — RWY 17R/35L is restricted between 00:00 and 06:00 LMT.** Exceptions:
  ICAO Annex 16 **Chapter 14** aircraft; landings without reverse; operational
  safety. So a 03:00 departure goes from **17L**, not 17R.
- **§1.2 — Chapter 3 aircraft above 50 000 kg MTOW may not take off between
  22:00 and 07:00 LMT**, on either runway.
- Full-power engine runs are **not** allowed on the apron. The run-up point is
  the **Test Area, north of taxiway PAPA** (labelled on the SCEL aerodrome
  chart).

### Does the wind actually support it? — 3 years of measured METAR

21 020 hourly observations at SCEL, 2023-01-01 → 2025-12-31 (IEM ASOS archive):

| Quantity | Value |
|---|---|
| Wind with a **headwind component on RWY 17** | **81,9 %** of non-calm observations |
| Wind favouring RWY 35 | 18,1 % |
| Calm (< 3 kt) | 7,2 % |
| Tailwind on 17 **exceeding the 10 kt limit** | **0,39 %** of all observations |

Direction histogram (30° bins, ≥ 3 kt), % of all observations:

```
150°  26,8 |||||||||||||||||||||||||||
180°  23,5 ||||||||||||||||||||||||
210°  19,5 ||||||||||||||||||||
030°   4,2 ||||
000°   3,7 ||||
CALM   7,2 |||||||
everything else ≤ 2,5 % each
```

**The wind has a strong daily clock, and this is the detail a Santiago-based
employee lives with.** It is a thermally driven valley wind:

| Local hour (UTC−4) | Mean speed | % favouring 17 |
|---|---|---|
| 04 | 4,1 kt | 56 % |
| **07** | **3,8 kt** | **41 %** |
| 10 | 4,7 kt | 56 % |
| 13 | 8,2 kt | 90 % |
| **17** | **11,2 kt** | **96 %** |
| 20 | 8,5 kt | 93 % |
| 23 | 6,0 kt | 81 % |

Read that as: **early morning is nearly calm and often has a light down-valley
northerly** — the first waves of the day frequently roll on 17R with a light
tailwind, legal under the 10 kt allowance, because the preferential system, not
the wind, sets the direction. **By mid-afternoon the southerly is established at
10–11 kt and 17 is unambiguous.** If the model is to show a wind sock, an
afternoon scene points it at roughly 150–210°, i.e. almost straight down the
runway; a 07:00 scene should show it limp.

Full data: `scl_operations_wind.json`.

---

## 2. The two runways — survey numbers

Source: **AIP-CHILE VOL I, AD 2 SCEL, AMDT NR 67, 06 AUG 2026** (sections AD
2.12 / 2.13) and the **SCEL ADC** aerodrome chart, AMDT 102, 14 MAY 2026.

| | RWY 17R/35L (west) | RWY 17L/35R (east) |
|---|---|---|
| Dimensions | **3 800 × 45 m**, ASPH | **3 750 × 55 m**, ASPH |
| Strength | PCR 1120 F/D/X/T | PCR 560 F/B/X/T |
| Strip (*franja*) | 3 920 × 300 m | 3 870 × 300 m |
| Slope | 0,0 % | 0,0 % |
| Stopway / clearway | none | none |
| RESA | yes | yes |
| Published bearing | 177° GEO / 176° MAG | 177° GEO / 176° MAG |
| Bearing from the survey coordinates | **177,423°** | **177,415°** |

Thresholds, and the same points in the local frame:

| THR | Latitude | Longitude | x (m) | y (m) | Elev |
|---|---|---|---|---|---|
| **17R** | 33°22′19,02″S | 70°48′13,38″W | 0,00 | 0,00 | 472,7 m |
| 35L | 33°24′22,25″S | 70°48′06,77″W | +170,87 | −3 796,55 | 472,4 m |
| 17L | 33°22′33,89″S | 70°47′12,15″W | +1 582,78 | −458,12 | 472,4 m |
| 35R | 33°24′17,60″S | 70°47′06,57″W | +1 727,02 | −3 653,29 | 473,9 m |
| ARP | 33°23′39,99″S | 70°47′37,69″W | +922,58 | −2 494,58 | 474,0 m |

Declared distances (AD 2.13):

| RWY | TORA | TODA | ASDA | LDA |
|---|---|---|---|---|
| **17R** | **3 800** | 3 800 | 3 800 | 3 800 |
| 35L | 3 800 | 3 800 | 3 800 | 3 800 |
| 17L | 3 750 | 3 750 | 3 750 | 3 750 |
| 35R | 3 750 | 3 750 | 3 750 | **3 200** |

Three consistency checks that all pass, and which are the reason to trust these
numbers:

- 17R THR → 35L THR computed from the coordinates = **3 800,4 m** = the published
  TORA.
- 17L THR → 35R THR = **3 198,4 m** = the published 35R **LDA of 3 200 m**. That
  proves the 35R published threshold is the **displaced** one, sitting 550 m
  inside the pavement.
- Centreline separation between the two runways = **1 560,8 m** — comfortably
  above the ICAO minimum for independent parallel ILS approaches, which is why
  AD 2.20 §2 authorises simultaneous parallel approaches to 17L and 17R.

**Geometric relationships worth having in the scene.** The 17L threshold sits
**528,8 m down-field** of the 17R threshold along the 17R axis, and **1 560,8 m
to the east**. 17L/35R therefore extends about 479 m further south than
17R/35L: two staggered strips, not a mirrored pair.

**Magnetic variation.** The ADC prints **VAR 0,9° E (2023)**; WMM-2025 evaluated
for 2026,6 gives **+0,23° E**. Declination at Santiago is now effectively zero —
true and magnetic tracks coincide within a degree, and the "17/35" name is a
survival from when the easterly variation was large enough for a true 177,4° to
round to 17.

---

## 3. Runway markings — the standard, and what is actually painted

**Chile is an ICAO state and SCEL is painted to ICAO Annex 14, not FAA.** The
AIP states what exists (AD 2.9 item 2):

> *SGL RWY: Designadores, eje, borde, zona toma contacto, punto de visada,
> letreros, NO ENTRY.*
> (designators, centre line, edge, touchdown zone, aiming point, signs, NO ENTRY)

Everything below was then **measured independently**: Esri World Imagery was
rectified onto the 17R axis at 0,25 m/px and the paint was detected numerically.
Imagery was used for measurement only and is not redistributed.

| Marking | ICAO Annex 14 requirement | **Measured on RWY 17R** |
|---|---|---|
| Threshold stripes | 12 stripes for a 45 m runway (Table in 5.2.4.5); ≥ 30 m long, ≈ 1,80 m wide, ≈ 1,80 m gaps, double gap at the centre; start 6 m from the threshold | **12 stripes**; start **6 m**; length **30,2 m**; width **1,75 m**; gap **1,8 m**; central gap **4,0 m**; outer edge at **±22,25 m** |
| Designation | Fig. 5-2 (B), parallel runways: stripes, then 12 m, then the **letter** (9 m), 6 m, then the **number** (9 m), 12 m, then the centre line. Character height 9,0 m, stroke 1,5 m, digit width ≈ 3,0 m (Fig. 5-3) | **Stacked, letter first**: "R" at **45,8–55,0 m** from the threshold (9,2 m tall), "17" beyond it at ≈ 62–72 m. A pilot reads *17* over *R*. **This is not the American single-line "17R"** |
| Centre line | Stripe + gap 50–75 m; stripe ≥ max(gap, 30 m); width ≥ **0,90 m** on CAT II/III (5.2.3.3–4) | **Stripe 30,0 m, gap 30,0 m, period 60,0 m**, measured over 8 consecutive periods between 1 438 m and 1 888 m (59,75–60,25 m). Width is below imagery resolution; the CAT III requirement of 0,90 m applies |
| Aiming point | LDA ≥ 2 400 m → begins **400 m** from the threshold, 45–60 m long, 6–10 m wide, inner sides 18–22,5 m apart (Table 5-1 col. 5) | Begins **383 m**, ends **428 m** → **45,3 m long**, **6,0 m wide**, inner edges at **±9,25 m** = **18,5 m** spacing |
| Touchdown zone | Pairs every 150 m from the threshold, 6 pairs for LDA ≥ 2 400 m, each mark ≥ 22,5 m long; **delete any pair within 50 m of the aiming point** (5.2.6.3–4). Pattern A = one 3 m bar, pattern B = three 1,8 m stripes 1,5 m apart | **Pattern B (three stripes per mark)**; pairs at **150, 300, 600, 750, 900 m**; the **450 m pair is deleted**, exactly as the rule requires. Mark length **23,8 m** |
| Side stripe | ≥ 0,90 m on runways 30 m or wider (5.2.7.5), outer edge on the runway edge | **≈ 1,0 m**, outer edge at **±22,5 m** = the 45 m runway edge |
| Distance remaining | **Not an ICAO marking.** ICAO has no painted distance-remaining marks; distance-to-go boards are an FAA/military convention | **Not present.** Do not paint them |

Also on the surface, from the AIP:

- **LVP "pink spots"** — position markings painted **west of the centre line of
  taxiways ZULU, ALFA, PAPA and KILO**: a black alphanumeric on a **3 m
  diameter pink disc**, ringed in black and then white (AD 2.9 item 5). These
  are unusual and instantly recognisable to anyone who works there.
- Taxiway width **23 m**; **TWY ALFA is 36 m** (concrete, PCR 740 R/D/W/T) —
  it was wide enough to serve as a temporary runway 18/36 during 2018 runway
  works. **TWY TANGO** is asphalt, PCR 1120 F/D/W/T. Apron is **concrete**,
  PCR 770 R/D/W/T.

### Lighting (AD 2.14)

| RWY | Approach | THR | PAPI | TDZ lights | Centre line | Edge |
|---|---|---|---|---|---|---|
| **17R** | **ALSF-2** | green | 3,0° **LEFT** | no | 3 200 m every **15 m** white, then red to 3 800 m | — |
| 17L | **ALSF-2** | green | 3,0° LEFT | **yes** | white LIH to 2 600 m; white/red 2 500–3 150 m; red 3 150–3 750 m *(as published; the 2 600/2 500 pair is internally inconsistent in the AIP)* | 3 750 m every 60 m, white LIH |
| 35R | SSALS | green | 3,0° LEFT | no | — | 600 m red every 60 m; 3 200 m white every 60 m LIH |
| 35L | — | — | 3,0° LEFT | no | 3 200 m every 15 m white, then red to 3 800 m | 3 800 m every 50 m |

All four ends have **REIL** and **RTHL**; 17R also has **TCLL**. The aerodrome
beacon on the tower is **flashing white every 10 s, H24**. Taxiways have edge
and centre-line lighting (or lit + retro-reflective markers with centre-line
lighting).

For a daylight scene the PAPI matters visually: **all four PAPIs are on the LEFT
side of the runway**, i.e. on the **east** side when you are rolling on 17R.

---

## 4. The path — how LATAM gets from the stand to 17R

The AIP publishes **standardised taxi routes** (AD 2 SCEL-46/48, §14), valid
only when 17L/17R are in use — which is essentially always.

**Departures:**

| From | To RWY 17R | To RWY 17L |
|---|---|---|
| North stands | **G, P, T, Z, V or V1** | G, K, T, A |
| East stands | **K, T, Z, V or V1** | K, T, A |
| West stands | **P, T, Z, V or V1** | P, T, A |

**Arrivals vacate** 17L via **C, B or A1**, and 17R via **U, W or Y** — which the
geometry confirms exactly: measured from the 17R threshold along the 17R axis,
the exits sit at **R 1 746 m, U 2 144 m, W 2 858 m, Y 3 705 m**; and on 17L
(datum still the 17R threshold) at **C 2 168 m, B 2 519 m, A1 3 668 m**.

**Stand groups** (AIP): *east* = cargo 41–47, Concourse **D** and **F**, stands
26–28. *West* = cargo W1–W9B/V1/V2, Concourse **C** and **E**, A12/A13. *North*
= A14/A15, 16–25.

**So the canonical LATAM international departure is: push back at a T2
concourse, taxi north on P (or K from the east side), cross the field westbound
on T, turn north onto Z, and enter the runway at V or V1 at the 17R
threshold.** Entry is at the very top of the field — **V1 is 61 m and V is 76 m
short of the threshold** on the axis, so it is a **full-length** departure with
all 3 800 m of TORA ahead.

Two rules that shape how that taxi looks:

- **Give way**: aircraft on **ZULU give way to traffic vacating 17R via UNIFORM
  or WHISKY**; aircraft on **ALFA give way to traffic vacating 17L via BRAVO or
  CHARLIE** (AD 2, §13.1).
- **MROT** (minimum runway occupancy time) is in force: at the holding point you
  must be ready to line up and go immediately, or the clearance is cancelled and
  you are sent off at the first taxiway. **There is no "line up and wait, then
  finish the checklist" at SCL.**

### What is out the window on that taxi

Positions below are *along* = metres down the 17R take-off axis from the 17R
threshold, *east* = metres east of the 17R centre line. Heading **north** up
P/Z, **east is on the right**.

| Feature | along | east | What it looks like |
|---|---|---|---|
| Espigón E "Lagos" (T2) | 3 484 | 495 | glass-and-white pier, opened 2019 |
| Espigón F "Patagonia" (T2) | 3 485 | 1 069 | opened 2024 |
| Terminal 2 Internacional | 3 271 | 788 | the 2022 central processor |
| Espigón C "Isla de Pascua" | 3 136 | 483 | opened 2018 |
| Espigón D "Desierto de Atacama" | 3 127 | 1 071 | opened 2021 |
| Terminal 1 Nacional | 2 780 | 796 | the 1994 domestic terminal |
| **DGAC control tower** | **2 277** | **805** | **60 m** tall, ~16 × 16 m footprint |
| Sky Airline maintenance base | 2 152 | 664 | the magenta-fronted hangar |
| Plataforma Papa | 1 868 | 676 | |
| **Plataforma LATAM (MRO apron)** | **1 776** | **945** | the LATAM ramp — widebodies parked nose-in |
| **LATAM Base de Operaciones y Mantenimiento** | **1 791** | **845** | the main ops + maintenance building |
| Engine run-up **Test Area** | ≈ 900–1 100 | | marked on the ADC, north of TWY PAPA |
| **TWY T** — the cross-field taxiway | **1 307–1 345** | 191 → 1 364 | this is where you turn west |
| **TWY V / V1** — runway entry | **−76 / −61** | | |

So the LATAM base passes **on the right**, about **1,4 km** after leaving a T2
stand and still **1,8 km short of the 17R threshold**, sitting **650–750 m** east
of the taxiway. Between it and the runway there is nothing but bare infield. On
the same leg, the **60 m control tower** goes by on the right at 2 277 m from the
threshold, and the **Test Area** — where engines get run at full power, because
the apron is off limits for it — is on the right shortly before TWY T.

*(Cross-check: the sibling dataset `scl_osm.json` puts the tower at
(−676,41, −1 778,83) and the LATAM base cluster at (−588,6, −1 314,9) in the 17L
frame; adding the translation above reproduces the numbers in this table.)*

### Radio, because it is on the ATIS and in every crew's ear

`ATIS DEP 132,7 · ATIS ARR 132,1 · DLVRY 136,7 · TWR 118,10 · RDR 119,7 ·
GNDC W 122,5 · GNDC E 122,2 / 122,6` (SCEL ADC). PDH VOR/DME **117,2** —
**the 17R runway track is literally radial 177 of PDH.**

### After lift-off

Every 17R SID starts the same way: **straight ahead on the runway track,
TR 176–177° (PDH R177)**. The recommended departures — **DILOK, GUVOL, DONTI** —
then *climb on TR 177° to 4 000 ft, turn **right** direct SEKSU–TEPOK–TEMUS–
TINGO–EL680*. 4 000 ft is **1 219 m AMSL = 745 m above the field**, which for a
narrowbody is roughly **5–7 km straight south of the threshold** before the
first turn.

The turn is to the **right — away from the Andes**. That is deliberate: the
recommended SIDs buy track miles over the valley so the aircraft has altitude
before it crosses the cordillera. Short easterly SIDs exist but are not usable
without a significant payload penalty.

---

## 5. Sun and hour — how to set the light

Santiago is at latitude −33,39°, longitude −70,79°. Two facts dominate:

1. **The sun is always in the northern half of the sky at local noon.** Maximum
   solar elevation is **80,05°** (21 Dec) and **33,20°** (21 Jun), and the noon
   azimuth is 0°/360°. *(Independently published figure for 21 June: 33,1°.)*
2. **Runway track 177,4° means you take off almost due south.** Everything below
   is expressed relative to the aircraft's nose.

Chile: **UTC−4** in winter, **UTC−3** on summer time. Summer time in 2026 starts
**Saturday 5 September at 24:00** and runs to **3 April 2027** (Decreto N° 98).

### Solar geometry, computed (NOAA/Meeus, apparent elevation with refraction)

| Date | Sunrise (local / az) | Solar noon (local / elev) | Sunset (local / az) |
|---|---|---|---|
| 15 Jan | 06:51 / 115,9° | 13:53 / 77,6° | 20:55 / 244,1° |
| 20 Feb | 07:26 / 103,3° | 13:57 / 67,4° | 20:29 / 256,7° |
| 21 Mar | 07:49 / 89,9° | 13:50 / 56,2° | 19:52 / 270,2° |
| 21 Jun | 07:49 / 61,9° | 12:45 / 33,2° | 17:42 / 298,0° |
| 23 Sep | 07:33 / 90,5° | 13:36 / 56,9° | 19:40 / 269,1° |
| 21 Dec | 06:32 / 118,8° | 13:41 / 80,1° | 20:52 / 241,0° |

Validated: computed solar noon for 18 Aug 2026 = **12:47** local, against a
published 12:47; computed 21 Jun maximum elevation 33,20° against a published
33,1°. Sunrise/sunset azimuths agree with published values to ≈ 2–3°, the
difference being the upper-limb versus centre convention.

### The mountains eat the ends of the day

A 360° terrain horizon was computed from SRTM 30 m (curvature and standard
refraction applied), observer at the field, 474 m:

| Sector | Terrain horizon | Distance | Summit |
|---|---|---|---|
| Andes, az 045–115° | **2,5 – 4,1°** | 35–85 km | 2 800 – 4 700 m |
| Cordillera de la Costa, az 255–310° | **2,3 – 4,3°** | 12–30 km | 1 200 – 2 100 m |
| South, az 165–195° (the departure direction) | **0,3 – 1,0°** | — | flat valley |

Consequence, in minutes:

| Date | Astronomical sunrise | **First direct sun on the field** | Last direct sun | Astronomical sunset |
|---|---|---|---|---|
| 15 Jan | 06:51 | **07:04** (+13) | 20:51 (−4) | 20:55 |
| 21 Mar | 07:49 | **08:03** (+14) | 19:33 (−19) | 19:52 |
| 21 Jun | 07:49 | **08:11** (+22) | 17:19 (−23) | 17:42 |
| 23 Sep | 07:33 | **07:46** (+13) | 19:21 (−19) | 19:40 |
| 21 Dec | 06:32 | **06:46** (+14) | 20:49 (−3) | 20:52 |

**The morning sun comes up from behind the cordillera 13–22 minutes late, and in
winter the sun quits the field ~23 minutes before the printed sunset.** Getting
this wrong is exactly the kind of thing an SCL employee feels without being able
to name.

### Which side of the aircraft is lit

Take-off heading 177,4°. Facing south, **east is on the port (left) side and
west is on the starboard (right) side.**

| Time | Sun azimuth | Where it is relative to the nose |
|---|---|---|
| Summer morning, 07:00–07:45 | 109–115° | **68–63° to the LEFT** (port), i.e. abeam-forward on the east side |
| Summer evening, 20:00–20:45 | 245–251° | **68–74° to the RIGHT** (starboard), abeam-forward on the west side |
| Winter morning, 08:00–08:45 | 54–60° | **117–124° to the LEFT** — behind the left wing |
| Winter evening, 16:45–17:15 | 302–306° | **125–129° to the RIGHT** — behind the right wing |

### Recommendation: **late-afternoon / evening, sun in the west**

Three reasons, all checkable:

1. **The Andes are lit.** They are east of the field; a low western sun rakes the
   slopes that face the airport. A low eastern sun puts them in silhouette
   against their own glare.
2. **The wind agrees.** At 17:00 local the southerly is at 11,2 kt and favours
   RWY 17 in **96 %** of observations — the scene is operationally honest.
3. **It lights the aircraft's starboard side**, which is the side a camera
   trailing a southbound departure naturally sees, and the sun is 65–75° off the
   nose — front-quarter light, not flat backlight.

Concrete sun settings for the Blender lamp, mid-February (a warm, clear,
high-traffic season):

| Local time | Elevation | Azimuth | Note |
|---|---|---|---|
| 19:30 | 11,5° | 264,7° | still hard light, long shadows across the runway |
| **19:45** | **8,4°** | **262,7°** | **suggested — full golden, aircraft still fully lit** |
| 20:00 | 5,3° | 260,7° | deep gold, colour temperature falling fast |
| 20:15 | 2,4° | 258,6° | last light; the coastal range is already cutting in |
| 20:30 | −0,6° | 256,6° | civil twilight — the runway lighting takes over |

Shadow length on the ground = aircraft height ÷ tan(elevation). At 8,4° that is
**6,8 × height**: an A320neo tail 11,76 m up throws an **80 m** shadow. Point it
along azimuth 262,7° + 180° = **82,7°**, i.e. east-north-east across the runway.

For an anchor with a real photograph: the Commons image
*"CC-AWJ JetSMART A320neo golden 24.04.2022"* — a low-sun climb-out at SCL —
carries an EXIF time of 17:34 local, which computes to **sun elevation 6,5°,
azimuth 290,2°**. That is what this light actually looks like on this airfield.

Full per-minute tables: `scl_operations_sun.json`.

### If you want the morning instead

Do it **in summer, between 07:00 and 07:45**, when the sun is at 109–115° and
3–10° up. But expect a nearly calm or light-northerly wind sock, weak or absent
southerly, and the Andes as a flat silhouette. And do not start the light before
**07:04** — the ridge is still in the way.

---

## 6. Elevation 474 m — what it actually changes

Aerodrome elevation **474 m / 1 555 ft**; ISA temperature at that height is
**11,9 °C** and ISA pressure **957,6 hPa**. Measured monthly temperatures at
SCEL, 2023–2025:

| | Jan | Feb | Jun | Jul |
|---|---|---|---|---|
| mean | 22,8 °C | 23,5 °C | 10,0 °C | 9,9 °C |
| max | 37,0 °C | 36,0 °C | 26,0 °C | 24,0 °C |

Density altitude:

| OAT | σ = ρ/ρ₀ | 1/√σ | **Density altitude** |
|---|---|---|---|
| 8 °C (winter morning) | 0,969 | 1,016 | 331 m / 1 086 ft |
| 12 °C (≈ ISA) | 0,955 | 1,023 | 477 m / 1 565 ft |
| 25 °C | 0,913 | 1,046 | 934 m / 3 064 ft |
| **32 °C (summer afternoon)** | **0,892** | **1,059** | **1 170 m / 3 838 ft** |
| 35 °C (heat wave) | 0,884 | 1,064 | 1 269 m / 4 163 ft |

**What that means for an animation that has to look right:**

- **The aircraft goes over the ground faster than the airspeed indicator says.**
  TAS = IAS / √σ.

  | | IAS | ISA morning | Hot afternoon (32 °C) | Sea level for comparison |
  |---|---|---|---|---|
  | A320neo, V<sub>R</sub> | 140 kt | 73,7 m/s | **76,2 m/s** | 72,0 m/s |
  | A320neo, V₂ | 150 kt | 79,0 m/s | **81,7 m/s** | 77,2 m/s |
  | 787-9, V<sub>R</sub> | 155 kt | 81,6 m/s | **84,4 m/s** | 79,7 m/s |
  | 787-9, V₂ | 165 kt | 86,9 m/s | **89,9 m/s** | 84,9 m/s |

  A takeoff animation built at sea-level speeds will look **~6 % too slow** over
  the ground on a hot Santiago afternoon.
- **The ground roll is longer** — higher true speed to reach and less thrust from
  the engines. This is precisely why the runways are 3 750 and 3 800 m rather
  than 3 000, and why a full 17R departure uses the whole length.
- **The initial climb gradient is shallower** for the same reason, which
  compounds with the second-segment problem of a cordillera at 4 000–5 000 m
  within 55 km. Hence the SID design: climb to 4 000 ft straight ahead, turn
  right, gain altitude over the valley, and only then head east.
- The AIP publishes runway **slope 0,0 %** on both runways, and the four
  threshold elevations lie within **1,5 m** of each other (472,4 – 473,9 m). For
  modelling purposes the runway surface is **flat** — do not model a crown or a
  grade. It is the *air*, not the ground, that the elevation changes.

---

## 7. Things you can only get from photographs

I looked at these before writing any of the following. Attribution and licence
are recorded; no image is copied into this repository.

- **The infield is bare earth, not grass.** The strip between the runway and the
  parallel taxiway is dry ochre-to-reddish soil with darker ploughed-looking
  patches — no turf anywhere inside the fence. A European-airport green infield
  is the single fastest way to make this scene read as wrong.
  → *Aero Merino Benitez aire.JPG* (CC BY-SA 4.0, Ivotoledo45, 2014);
  *LATAM Chile Boeing 787-9 at Santiago Airport (2017).jpg* (CC BY-SA 4.0).
- **The runway asphalt is a dark grey-green**, with a crisp white side stripe and
  slightly lighter paved shoulders outside it.
- **The western backdrop is brown, not white.** The Cordillera de la Costa —
  what you see from the terminal looking west — is arid, 1 300–1 700 m, and
  carries no snow. The snow-capped range is the Andes, on the *other* side.
  → *Ramp view, Santiago Airport, 27 Dec 2010* (CC BY 2.0, Phillip Capper).
- **Haze is not optional.** Santiago's air flattens the distant ranges into
  layered purple-grey silhouettes with very little detail. Without an
  aerial-perspective/fog term the mountains will look like cut-out cardboard.
  → *LATAM 787-9 at SCL (2017)*, dusk, shows the effect strongly.
- **A line of poplars/eucalyptus** runs along the airfield boundary, sitting
  between the pavement and the hills in nearly every ground-level view.
- **The apron floodlight masts** are tall white lattice columns with a
  cylindrical lamp crown — distinctive, and they appear in the background of
  every stand photo. → *SCL 20220211.jpg* (CC BY-SA 4.0, Aeveraal).
- **Outside the west fence** the ground is farmland — irrigated green rectangles
  next to ploughed brown ones — crossed by a dual-carriageway road parallel to
  RWY 17R. North of the field, toward Quilicura, there is dusty open ground with
  brick kilns.

---

## 8. Sources

| Source | What it gave | Licence / status |
|---|---|---|
| [AIP-CHILE VOL I, AD 2 SCEL, AMDT NR 67, 06 AUG 2026](https://aipchile.dgac.gob.cl/dasa/aip_chile_con_contenido/ais/3%20AD%20Parte%203/AD%202a%20Aeropuertos/8%20-AD%202%20SCEL.pdf) | Runway physical characteristics, declared distances, lighting, apron/taxiway data, local traffic regulations (preferential runway), noise abatement, standardised taxi routes, LVP | Official state AIP, DGAC Chile. Free to consult; data are facts, not copyrightable expression. Cite the amendment. |
| [SCEL ADC aerodrome chart, AMDT 102, 14 MAY 2026](https://aipchile.dgac.gob.cl/dasa/aip_chile_con_contenido/aipmap/SCEL/SCEL%20ADC.pdf) | ARP, thresholds, elevations, strip dimensions, taxiway letters, magnetic variation, frequencies, Test Area | idem |
| SCEL SID charts SID1…SID12, `aipmap/SCEL/` | First segment of every 17R departure, recommended SIDs, the 4 000 ft right turn | idem |
| [ICAO Annex 14 Vol I, 8th ed. 2018, Ch. 5](https://www.iacm.gov.mz/app/uploads/2018/12/an_14_v1_Aerodromes_8ed._2018_rev.14_01.07.18.pdf) | Marking standards: designation, centre line, threshold, aiming point, TDZ, side stripe, Figures 5-2, 5-3, 5-5, Table 5-1 | ICAO © — used as a specification reference, quoted only in short fragments |
| [OpenStreetMap](https://www.openstreetmap.org/) via Overpass API | Runway, taxiway, apron, terminal and hangar geometry; LATAM base and Plataforma LATAM identification | **ODbL 1.0** — attribution and share-alike required for derived geodata |
| [Iowa Environmental Mesonet ASOS/METAR archive, station SCEL](https://mesonet.agron.iastate.edu/request/download.phtml?network=CL__ASOS) | 21 020 hourly wind and temperature observations, 2023–2025 | Public archive of state-produced METAR |
| [OpenTopoData](https://www.opentopodata.org/) / SRTM 30 m (NASA) | 360° terrain horizon profile | SRTM: public domain (NASA/USGS) |
| Esri World Imagery | Rectified measurement of the RWY 17R markings | © Esri and imagery contributors — **used for measurement only, not redistributed**. No pixels from it are in this repository |
| Airline Route Information Manual for SCEL (flight-simulation reissue, Oct 2021) | Independent corroboration of the 17L-ARR / 17R-DEP split, taxi-route preferences, runway-incursion hot spots | Third-party document, used only as a second opinion — the AIP is the authority |
| NOAA/Meeus solar position algorithm; WMM-2025 via `pygeomag` | Solar elevation/azimuth, magnetic declination | Public-domain algorithms |
| Wikimedia Commons photographs, listed in §7 | Appearance of the infield, mountains, haze, apron furniture | CC BY 2.0 / CC BY-SA 4.0 — **URLs and authors recorded; no image copied into this repository** |

## 9. What is uncertain, and what I could not do

- **The runway centre-line stripe width** could not be measured — 0,90 m is below
  the resolution of the available imagery. The ICAO CAT II/III requirement of
  ≥ 0,90 m is quoted instead. Confidence: high that it is 0,90 m, but it is a
  standard, not a measurement.
- **The AIP's own 17L centre-line lighting entry is internally inconsistent**
  ("2 600 m … FM 2 500 m"). It is reproduced verbatim above rather than
  silently corrected. 17R and 35L publish a 15 m spacing; 17L publishes 50 m,
  which is unusual for a CAT IIIB runway and may be a typographical error for
  15 m. **Do not treat the 17L figure as settled.**
- **The exact stands LATAM occupies** are not published per airline. The AIP
  gives stand groups and their taxi routes; which concourse a given LATAM flight
  uses depends on domestic/international and on the day. The route via
  **P/K → T → Z → V** holds for every one of them.
- **Imagery georeferencing** carries roughly a **2 m** along-track bias: the
  threshold stripes measure as starting at 4,0 m rather than the specified 6,0 m.
  All marking distances above should be read with a ±2 m offset.
- **Colour values** for asphalt, paint and soil were not sampled numerically —
  the photographs listed in §7 were read qualitatively. If exact albedos matter,
  that is a separate measurement job.
- The **wind statistics are hourly METAR**, so gusts and short-lived direction
  swings are under-represented; the 10 kt tailwind exceedance of 0,39 % is
  therefore a lower bound.

---

## Files produced

| File | Contents |
|---|---|
| `scl_operations.md` | this document |
| `scl_operations_runway.json` | AIP survey data, declared distances, lighting, measured marking geometry, taxiway stations on the runway axes, standardised taxi routes, facility positions, SID first segment, frame transform to the 17L frame |
| `scl_operations_sun.json` | per-date solar tables: sunrise/sunset with azimuth, solar noon, declination, equation of time, and 15-minute samples through the golden-hour band with the angle off the 17R nose |
| `scl_operations_wind.json` | 3-year SCEL METAR climatology: runway-preference split, direction histogram, hour-by-hour diurnal cycle, monthly temperatures |
