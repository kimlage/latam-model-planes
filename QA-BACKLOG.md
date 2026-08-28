# QA backlog — defects found, not yet fixed

Living triage list. Each entry says what is wrong, how it was found, and what
must not be assumed while fixing it. Delete an entry when its fix is committed.

Nothing here was found by inspection alone: every item came from a gate that
was itself improved, which is the pattern worth keeping — **when a defect
survives, suspect the instrument before the model**.

---

## Scene-detail + clips-refresh round 2026-08-27: found in passing, deferred with reasons

1. **TECA massing tubes reach the freighters.** `checks/fleet_cargo.png`
   shows the pre-existing massing jetbridges on the cargo-terminal face
   reaching toward the two LATAM Cargo 767s — a pax bridge on a freighter
   is wrong in reality. The C-stands were deliberately left OUT of the
   articulated tier this round (the tour/departure cameras never resolve
   the cargo frontage); the honest fix is to exclude the TECA face from
   the massing pass entirely and let the freighters work the ramp with
   GSE only.
2. **R910/HGR AABB overlap warning.** Every `fleet_placement.populate`
   prints `!! R910 and HGR overlap by 37.8 x 5.3 m`. The envelopes are
   world AABBs of ROTATED aircraft, so they overstate; the hangar check
   still (`checks/fleet_hangar_777.png`) shows no visible contact between
   the 767's wing and the hangar 777. Needs a verdict with oriented
   envelopes (or a stand shift) rather than a silenced warning.
3. **GRU dusk showcase deferred.** PENDENCIAS item 4 floated "variantes
   de luz (anoitecer GRU)". The shared field's light was chosen at 17:30
   for flow-honesty and must not change; a dusk set needs its own sun rig
   in a derived scene. Deferred — this round's budget went to the eight-
   clip refresh.
4. **Apron light pools skipped, with reason.** At the shipped 17:30 sun
   (16.5° up) emissive pools under the mast heads would not read, and
   `refs/` holds no night frame of the mast layout to paint them from.
   Unphotographed scene detail is skipped per the round's own rule.

---

## SETTLED 2026-08-27: the 787 wedges — the record was right, the painter drifted

The old entry asked whether the rule or the paint was the measurement, and
said settling it needed one rectifiable profile photograph. The hunt found
four (two per type, opposite flanks: CC-BGF landing at PEK + CC-BGG on
approach at MAD for the -9; the folder's own CC-BBF and CC-BBB frames for the
-8), and the verdict came from a method **stronger than the rectification**:
the boundary line fitted on >110 scan rows per frame, intersected with the
painted door-4 ring, using the ring's own 2.06 m height as the local scale —
no homography, no flank parallax, no lens distortion in the loop.

    787-9   ring crossings 0.872 / 0.90  ->  c = 48.90 / 48.84
            (paint wore 49.31; the kit rule says 48.77)
    787-8   ring crossings 0.80 / 0.96   ->  c = 42.94 / 42.61
            (paint wore 43.17; the rule says 42.68)

**c(-9) − c(-8) = 6.09 m — exactly the fin shift between the types.** Real
boundary = rule + 0.10 ± 0.12 on both; the paint sat 4 sigma aft. The offsets
were the -9 painter's drift and its column-resampled echo. Both wedges were
re-rasterized ON the rule (`reparar_echarpe.py`, 50768 + 37836 texels), gates
re-rendered, texture medians verified at 48.777 / 42.687.

Three method lessons, kept because they will bite again:

- **The 08-22 trial's "OK" rows for both 787s were artifacts.** The CC-BBB
  frame CUTS THE NOSE at x = 0 and the old homography squeezed the whole
  silhouette into the frame — 81.6 px/m against 97 real (the door ring is
  196 px for 2.06 m). Before fitting a silhouette, check the frame holds the
  whole aircraft.
- **Hull-anchored homographies carry ~0.35 m of flank bias at frame edges**
  (lens distortion; the door-ring prediction showed +23 px on the best-behaved
  frame). Verdicts should come from LOCAL reads; H is for finding, not proving.
- **The blend's fin ≠ the spec's fin ≠ the photograph's fin.** The built -9
  fin runs BF x = 57.165+0.4356z (the OLD 66.8° line) where the CORRECAO says
  0.3858, and the photo splits the difference, ~0.2-0.3 m wide of the built
  chord. Recorded in spec_b789 `cunha_assentada_2026-08-27.avisos_de_metodo`;
  a fin round, not this one.

---

## CLOSED 2026-08-27: the single painter — the eleven builders paint flat, refazer_marcas paints marks

The round happened (`fd1fbcf` + `e4d53b2`, plumbing only, zero renders, no
master texture touched). What it closed:

- **The three named offenders are gone from the builders.** The 767 family's
  spliced `zc_rz()` no longer feeds the wedge (the rule comes from
  `reparar_echarpe.FROTA` over `kit.secoes_do_casco`; the spliced table stays
  only for doors/windows/windshield, which were AUTHORED in it); the A321s'
  difference-mask re-solve and the `fac[m]=0` erasers over the wedge are
  replaced by absolute rasterization + stated-base erases; the 787-8's
  `abs(sin θ) > 0.10` guard is replaced by the colour test.
- **`refazer_marcas.py` is the only mark painter**, with three legacy engines
  (767/777 uint8, A320-family SS2, A321 raster_side, 787-8 coverage) carrying
  each family's constants and bridges verbatim, cited. Seven mark scripts are
  absorbed and marked historical (fase2b espelho, fix_titulo, fix_reg_ghosts,
  fix_matricula_a319, build_788_livery2).
- **The acceptance was measured offline** (dump-and-diff of the effective
  colour on scratch copies, per aircraft): the 767-300ER reproduces the
  shipped texture byte-identically except the 25-texel splice signature, and
  re-running its pipeline is byte-idempotent; the full per-aircraft table,
  the rebuild sequences, and the tolerance classes live in **`REBUILD.md`**.

What the round measured and left OPEN, on purpose:

- **`portas_familia`'s ring repaint is not byte-stable**: its erase reads the
  background back by DIFFUSION from the neighbourhood, so re-running it on
  the shipped A320neo alone moves ~5.9k texels at ring edges (sub-visible,
  1-texel AA fringes). Pre-existing, cosmetic, and now named: door rings are
  verified by class, not byte by byte. A byte-stable ring painter would need
  the base stated instead of diffused — same lesson as the wedge.
- **Seven of the eleven wedge boundaries are still a hard binary cut**
  (deliberate, unchanged): A319 4627, A320ceo 5583, A320neo 4535, 767-300F
  2340, 767-300BCF 2310, 777-300ER 3109, 787-9 3851 texels by `--seco`.
  The migrated builders paint the SAME binary cut on purpose (ss=1), so a
  re-run does not sneak the deferred anti-aliasing in; flipping to ss=3 is a
  one-argument change when a texture round wants it, with re-renders.
- **Marks whose shipped ink is a degraded copy** now rebuild crisper, not
  byte-equal: the A319 registration (shipped = double resample; rebuild =
  first-generation raster in the SAME glyph rows/columns) and the 787-8
  registration (same). The A319 title rebuild restores the "19"+swirl the
  old wedge destroyed (its own QA entry stays open for the SVG re-import).
  None of this is shipped — it materializes only when a rebuild actually
  runs, and that run ends at the visual gate as always.
- **Two operational traps recorded in REBUILD.md**: Blender returns rc=0
  even when the script dies with a traceback (every headless pipeline must
  grep the log), and scratch copies of a master need the folder's aux files
  (rings json, specs) linked beside them or scripts fail silently.

---

## Reported as tail defects, measured, and NOT defects

Kept because the same three reports will come back otherwise, and each one was
a reasonable thing to see.

- **A320neo PT-TMN: "a large white gap in the wedge."** There is none in the
  paint. The A320neo's wedge mask was differenced against the A320ceo's, which
  shares its hull, its UV and its texture size: 41776 texels indigo on the ceo
  and not the neo, 12396 the other way, and **all of it is a rim** — the ceo's
  aft boundary sits about 0.2 m further aft, and the two forward boundaries
  differ by one to two texels. Against the neo's own published rule the paint
  agrees to 1.31%. What the tail render shows is the wedge's real shape seen at
  `CamCauda`: the forward boundary is `x >= 28.51 + 0.63 z`, which is furthest
  AFT at the crown, so between the fin fillet and the horizontal stabiliser the
  hull is genuinely white — and it is white in `ref_PT-TMN_wikimedia.jpg` too.
- **"The registration is cut by the door frame."** True on all five Airbus and
  true on the aeroplane. Measured on the textures: the first glyph starts
  +0.140 m (A319), +0.149 (A320ceo), +0.261 (A320neo), +0.152 (A321ceo) and
  +0.152 (A321neo) aft of the door leaf's aft edge. The leaf is a 3-D object
  seated 10 mm proud of the hull (`kit.assentar_na_secao`), so at `CamCauda`'s
  oblique angle it occludes the first glyph — exactly as the door frame clips
  the "P" of PT-TMN in the reference photograph. The six Boeings cannot show
  this at all: their doors are paint, not geometry.
- **Head-on gates: a dark serrated wedge floats beside the nose** (both
  flanks, every type with geometric pax windows). Not a defect and NOT from
  the appendages round — it is the cabin-window row stacked by the 449 mm
  telephoto: at 70-92 m the whole forward window strip projects beside the
  nose silhouette, and the dark panes read as one serrated mass. Verified
  2026-08-27 on the 767: present pixel-for-pixel in the PRE-round committed
  render, and it survives hiding every `Apx_*` object. Real head-on photos
  show the same stacking, softer only because real panes reflect sky.
- **A319: the wedge runs forward over the type title.** Real, and already its
  own entry below — but the wedge's SHAPE is not the fault. The A319's forward
  boundary is a quadratic swoosh leaning the opposite way from the A320's
  (forward at the crown, sweeping aft going down), photo-measured on PT-TMT and
  confirmed on PR-MBU: `spec_a319.livery_pt_tmt.echarpe_fronteira`. It is
  type-specific art. Do not straighten it into the A320's line.

The fin sash was audited the same way and is clean fleet-wide. Crossings were
read off the `FinSashE` texture in the fin's own (x, z) domain, normalised as
zeta along the fin's own silhouette, root to tip. A320ceo, A320neo, A321ceo and
A321neo agree to **0.001 zeta** on every crossing (LE 0.184, 0.605, 0.899; TE
0.315, 0.368, 0.502, 0.803); the three 767s agree to 0.001; the two 787s agree
to 0.001. Against `spec_a320.cauda_livery.fin_bandas_2026-08-20` the LE
crossings land within 0.001-0.020 of the declared 0.175 / 0.585 / 0.90. The
A319 sits up to 0.036 off the family template, which is its fin-root stretch
(its fin cage bottoms at z 1.55 against the A320's 1.05), not its art. The
777's single grey mass at the tip and the freighters' shallower wedge are the
type-specific art `f162f73` established and were left alone.

---

## FIXED 2026-08-27: the valence-32 nose pole — and what the cap taught

`nariz_quad_cap.py` replaced the 32-fan with an 8x8 Coons-grid quad cap on
TEN of the eleven hulls (corners at 45 deg off the symmetry plane — the first
attempt put a valence-3 corner on the keel and the crease showed up exactly
there). The Catmull-Clark shrink is solved by per-vertex fixed point, and
the lesson that cost two render rounds: **the old limit surface near the
apex IS the defect** — a near-cone — and fitting the new cap to it
faithfully (<=2 mm, verified) reproduced the artifact pixel for pixel. The
shipped cap fits an OGIVE to each hull's own trusted annulus (rho
0.55-0.95) with a minimum apex radius of 0.05 m (declared estimate; 3 px at
600 dpi resolves nothing). Profiles preserved <=2 mm beyond x=0.35
everywhere; tip stations move <=2-3.5 cm (the rounding itself).

What the complaint contained that the pole did NOT explain, measured and
left open:

- **The nose sections' keel line carries a real normal kink** — 8.3 / 6.0 /
  2.2 deg across the symmetry plane at x 0.1 / 0.3 / 0.6, zero by x = 4
  (A320neo, evaluated normals at |y| 0.02). It is the ovoid exponent law
  (e(x) rising to ~1 gives the section a finite-angle corner at the keel),
  it focuses the under-nose "V" the clear coat shows, and the windshield
  fit constrains the exponents — re-deriving them is its own round.
- **The tail tip has the same valence-32 pole**, spanning ~3 cm of cone;
  it resolves in no current render and was left.
- **The 777 kept its pole.** Its radome is blunt enough that the 8x8 cap
  reads as a BUTTON at the cap/band seam (measured in the gate; three
  solver variants tried — ogive target, deviation clamp, Laplacian-relaxed
  pure fit — all ±1 cm coherent bulge). The old starburst-and-eye artifact
  therefore still stands on the 777 head-on; killing it needs a denser cap
  with a transition ring, a dedicated round. `construir -1` runs the pure
  cap if someone wants to trade starburst for button meanwhile.

---

## 767-300ER: cockpit pinch — plan taper EXONERATED 2026-08-27, upper lobe unmeasurable

The geometry-truth round measured what could be measured: the evaluated
hull's **max half-width per station against the ACAP p2-9 top view** (600
dpi, normalized by the drawn constant section) agrees to **±0.03 m (≤1.5%)
over the whole nose** — x1 1.010/1.045, x4 2.130/2.110, x7 2.521/2.515.
The nose in PLAN is right; "too blunt" cannot live there.

The upper lobe at the cockpit (what the pinch actually shapes) has **no
measuring source in the repo**: the front view only draws the master
section (local width is inside the silhouette), the top view shows the max
per station, and the nine photos yield no silhouette. The pinch stays as
built, its stale justification replaced by the recorded measurement. Also
recorded: the "glazing fraction of nose width" render-vs-photo comparison
is distance-sensitive (a close head-on fattens the near nose against the
far master section), so part of the original signal may be perspective,
not hull. Re-measuring needs a dimensioned cockpit cross-section (SRM/NC)
or a calibrated close head-on.

Also open on the same aircraft: the glazing's z position is 0.068 m
unresolved — the front view puts its centre at z = 0.876 and the side view of
the same sheet at 0.808, and no photograph resolves it head-on.

---

## FIXED 2026-08-27 (crown/keel UV): only the -9 carried it — 152+152 loops snapped

`uv_coroa_787.py`: the -9's hull loops at v 0.50712/0.99288 snapped to
0.5/1.0; the plane of symmetry is back at v = 0.5. The **-8 measured
clean already** (0.5/1.0 exact — "both 787s" below was stale; some later
-8 rebuild had already regenerated its UV). Marks repainted per REBUILD;
the -8's texture is byte-identical, the -9's 9.1k-texel diff is the
documented refazer re-blend class (lockup, window mirror) with the crown
band nearly untouched — the ink was always on the right texels, the
MAPPING displaced it on render. The radome-oval-vs-glazing question at the
end of the entry stays open (photo ambiguity unchanged). Original entry
kept below for the record.

## 787 family: the hull's crown and keel carry the wrong UV

What the nose-art fix left open. The windshield half of the old entry is
**done**: the mullions were not "wide black bars" by accident — the mask
painted the whole post dark, when on the real aircraft the post is *hull
white* with a thin dark seal each side, so the light slit between the panes
did not exist at all. Re-measured on two free-licence head-on photographs,
normalised by the half-width of the dark blob (the only scale-, lens- and
distance-free normalisation), the slit is `0.0740` at the centre post and
`0.0497` at the middle one; the two photographs agree to 2% and 8%.

The radome half of the old entry was a **misdiagnosis** and is withdrawn. The
joint was already a ring at a fuselage station — measured on the old texture
it runs `x = 1.109` at the crown to `1.389` at the keel, and the APR's side
view gives 1.078 and 1.403. Head-on, a ring at that station *does* project as
a closed oval inside the silhouette; the APR's own front view draws it that
way and so do all three head-on photographs. Only the stroke was wrong (0.039 m
of flat grey with a stair-step, and no relief).

What the fix found and did **not** repair: on both 787s every ring vertex of
the hull cage carries `v = i/32` exactly **except two**. The crown vertex
carries `0.50712` instead of `0.5`, the keel vertex `0.99288` instead of `1.0`.
On the evaluated surface the plane of symmetry therefore lands at `v = 0.5044`,
4.5 texture rows off centre — which is why the old centre post sat 0.045 m to
port, split by a 0.018 m slit of white hull. The 767, 777 and A319 hulls are
clean at `v = 0.5` / `1.0`, so this is a 787-family defect, not a fleet one.

`nose_art.py` is immune because it tests every texel by its own 3-D position on
the evaluated mesh, but **nothing else painted on these two hulls is** — in
particular the rear écharpe, which crosses the crown. The distortion is ~0.7%
of the circumference, concentrated within ±11° of the crown and the keel.

Also open on the same aircraft: the **radome oval against the glazing**. The
ratio of their half-widths is 0.770 in the model, 0.697 in the APR front view,
**0.673** on the A7-BCC head-on and **0.835** on the N805AN head-on. The two
photographs disagree by 22% — the N805AN is shot from above the windshield,
which foreshortens the outer pane exactly where it climbs the shoulder — so
nothing was changed. The APR and the better photograph both sit near 0.68,
which would make the glazing ~10% narrow. The hull is not the suspect: the
APR's **top** view gives the nose half-width to 1.3% of the model, after
normalising by the section the drawing itself draws (3.3% oversize in the top
view, 11% in the front view — the 767's trap again). This needs one head-on at
eye level on a light nose.

---

## CLOSED 2026-08-27: the A319 title reads "AIRBUS A319" again

The surface-print round rebuilt the whole title from real art through the
single painter (`refazer_marcas.py -- a319 titulo`): AIRBUS+A+3 from the
`MarkAirbusNeo_E` islands (the official a320neo SVG), the **'1' is the real
glyph from `airbus_a321neo_logo.svg`** (same title font), and the digits sit
in the official '2'/'0' SLOTS so the letterspacing is the mark's own. The
'9' is the one glyph with no SVG source anywhere in the repo: built from the
official '0''s own bowl (0.72 cap, top-aligned) + a 0.19-cap stem, checked
against the PT-TMT crop (`refs/ref_sdu_00.jpg`) — declared in
`spec_a319.json → livery_pt_tmt.titulo`. Navy #1C2E63 (off the white→indigo
segment, so `reparar_echarpe`'s colour guard also protects it; the `poupar`
box was widened to x 23.40–25.00 anyway). The legacy ring-'9' block in
`_marcas_a319` is retired; rebuilds run the `titulo` task. Method note: the
digit islands are 0.64 of the AIRBUS cap in the official art and the first
'1'-import merged italic glyphs when clustered by x-interval — cluster by
mesh connectivity and scale digits by the '3''s own cap.

---



## Surface-print round 2026-08-27: what was deferred, and why

The round that put panel joints, the belly-fairing seam, wing cutlines, the
under-wing registration and the rudder line on the fleet (PENDENCIAS item 3)
left four things named:

- **A320-family under-wing registration box is fleet-law, not photo.** No
  frame in the repo shows a LATAM A320-family wing underside. The five
  Airbus boxes (y 10.21–14.85, aileron band) apply the law measured on
  PT-MUG/CC-BGG/N536LA/CC-CXE — wing, orientation and cove anchor are
  photographic; the SPAN PLACEMENT is derived. One from-below frame of any
  fleet A320 closes it (spec `impressao_2026-08-27.asa.matricula`).
- **777 spoiler lines deferred.** The 777's shipped AsaLinhas NEVER rendered
  — AsaD/E carry no UV layer, so the shader sampled texel (0,0) — and its
  authoring frame is unrecoverable (no script; symmetric-mid fit is
  degenerate, no pylon gap in the art). The round repainted the wing print
  from the PT-MUG underside photo (TE zones + slats, canoe-anchored, ±1 m)
  in a declared domain, but the photo shows no extradorso: spoiler panels
  need a wing-top photo of a LATAM 777.
- **Elevator cutlines deferred fleet-wide.** The stabilizers carry flat
  materials (LATAM_Branco or CinzaAsa without UV); giving them a texture
  channel is material surgery on 11 masters for a line that reads only at
  CamCauda. Do it if a gate ever misses it.
- **787-8 joints and under-wing box are derived, not measured**: the -9's
  photo-measured barrel joins shifted by the derivation plugs, and the -9's
  reg band on the identical wing. A CC-BBF/BBB frame would close both.

Also named: `impressao`/`empenagem` are **not idempotent** (tint composites
— running twice doubles the darkening); `asa` is (channel B is wiped and
lines compose by max). REBUILD.md carries the run-once rule.

---

## A320 family: the flap-track fairings are not at the ACAP stations

Found while carrying them along with the wingspan fix. The ACAP plan view
(`A320_ACAP_airbus.pdf` p.45, read as vector) shows trailing-edge bumps
centred at `|y|` **4.95, 8.48 and 12.21** — the inboard ones are hidden behind
the nacelle and the belly fairing, so three is all the drawing gives.

The model has **five**, and after the span fix they sit at 3.11, 4.70, 6.66,
8.57 and 10.30. Two of them land within 0.25 m of a drawn bump; the outermost
is 1.9 m inboard of one. The count may be wrong too — the A320 carries four
per wing.

They were moved by the same spanwise map as the wing and re-anchored on the new
trailing edge, so they are attached and their protrusion aft of the TE is
unchanged. Putting them on the drawn stations is a round of its own, and it
should settle the count first.

---

## A320 family: the sharklet is a straight blade, not the ACAP's J

The wingspan fix put both ENDS of the sharklet exactly where the ACAP does —
tip at `|y|` 17.90 (span 35.80) and 2.43 m above the wing tip — and the blade
runs straight between them, at 31.3 degrees from vertical.

The drawing's sharklet is not straight. Measured on the front view, `(dy, dz)`
from the wing tip:

    (0, 0) (0.660, 0.182) (0.886, 0.276) (1.055, 0.394) (1.143, 0.494)
    (1.178, 0.557) (1.210, 0.642) (1.235, 0.754) (1.480, 2.430)

— a wide, nearly horizontal blend carrying the surface 1.24 m outboard while
rising 0.75 m, and then a near-vertical blade. The model's straight blade is
the CHORD of that curve: right at both ends, missing the belly.

It was left straight deliberately. The blade's mesh sections are HORIZONTAL
slices (chord in x, thickness in y), and a nearly horizontal blend sliced that
way degenerates — the sections end up almost parallel to the surface they are
supposed to describe. Fixing it means re-parameterising the blade along its own
arc, which is a new loft, not a remap.

---

## A320 family: the pax door leaf is 0.09 m too tall

Measured during the door round. Each leaf now sits on the hull and keeps its
angular footprint, which is **2.02 m of arc** — against the `0.89 x 1.93`
that every spec in the family declares for the modelled leaf.

The seating preserves size on purpose: it fixes where the panel is, not how big
it is, and changing both at once would have made the before/after unreadable.
The 0.09 m predates the z-lift — the leaf was built 2.06 m tall in the SIDE
PROJECTION back when the door sat near the widest point of the section, where
arc and `dz` happen to agree.

---

## Licensing: photo pixels in git history — closed

Closed going forward in `0da5329` — five `comparacao_fin_sash.png` sheets were
removed from the index and ignored, because each is roughly two thirds
photograph (PT-TMN, PS-LBO, CC-BBB) and `NOTICE.md` records those images as
**"cited, not shipped"**: CC BY-SA share-alike is incompatible with the CC BY
4.0 the models ship under.

**Decided by the owner: the history stays as it is.** The decision is safe on
its own terms — `origin/main` sits at `88715a6`, from before the fleet work,
so the 75 commits that carry those pixels were never pushed. Nothing was
published; the working tree is clean; the remote never saw them.

Worth noting how it happened, because it is a pattern rather than a slip: the
sheets were committed by an early round, and two later rounds independently
declined to commit theirs and flagged the inconsistency — the policy was
written after the practice, and nobody went back to reconcile the two.

---

## Fleet-wide, recorded but not scheduled

- **Appendages round 2026-08-27, declared simplifications** (all cited in
  each spec's `apendices_2026-08-27.fonte`): wick SPACING is uniform while
  the N536LA photo concentrates them on the outer wing panel (count is
  consistent; redistribute only if a gate ever reads it); the A320 family's
  retractable landing lights are deliberately NOT modelled (flush when
  retracted — the nose-gear taxi/TO lamp is what the photos show lit); the
  A320 pitot standby (3rd probe) is not modelled (sub-resolution at every
  gate); all light emission is CONSTANT — a strobe/beacon flash cycle is a
  clip-level decision at 25 fps, noted in PENDENCIAS item 2. The
  `export/` GLB fleet is now one round behind the masters (appendages not
  re-exported).
- ~~**Tailstrike angles** run short across the A320 family~~ — **FIXED
  2026-08-27**: it was BOTH suspects at once, plus a third — gear 0.28 short
  (keel clearance 1.605 vs 1.885 ACAP), belly fairing 0.20 too deep (-2.443
  vs -2.24 = jacked BF1), and the aft keel up to 0.29 low with the upsweep
  starting 2 m late. `trem_familia.py` + per-type ACAP keel tables in each
  spec (`estancia_e_quilha_2026-08-27`). Fuselage tailstrike now A320 12.63
  (published 11.7c/13.5e), A319 15.02 (13.9/15.5), A321 10.32 (9.7/11.2) —
  each static angle between compressed and extended. Residuals recorded in
  the specs: upsweep onset smoothed by the sparse cage (≤0.07 m over the
  first metre), the APU-cone zone (model 0.1-0.2 above the drawing, AP cota
  ambiguous) untouched, drain-mast protrusion 0.15 m is a declared estimate,
  and the aft mast still touches ~1.3 deg before the hull — as on the real
  aircraft, where the published number is fuselage contact.
- **"The hulls render pure white" — CLOSED 2026-08-26 as a stale diagnosis.**
  The 76% of `LiveryTex` at exactly `1.0` is real and INVISIBLE: those texels
  sit under `LiveryFac = 0`, and the shader shows `mix(base, tex, fac)` — the
  viewer sees the base. Audited across ALL ELEVEN masters: every hull's mix
  base is `#E6E7EA` (linear .784/.792/.820), every visible flat white in the
  textures is `#E6E7EA` (the 767/777, whose fac is 1.0 everywhere, carry it
  baked at 85–87% of the texture), and the committed profile renders keep the
  lit flank at 0.69–0.72 with ≤0.03% of white pixels above 252 — the shading
  that says "curved surface" is there. Whatever round migrated the materials
  fixed this without closing the entry. The absolute tint cannot be
  photo-measured from the available frames (no neutral reference in any of
  them; extrapolating a per-channel map from the indigo+coral anchors
  diverges at the white end), so `#E6E7EA` stands on the approved recipe and
  on internal coherence. What the audit DID find worth keeping: the fleet has
  THREE whites on purpose — hull `#E6E7EA`, mark white `#F2F3F5`
  (`refazer_marcas.BRANCO_MARCA`), raster-art white `#F7F9FA`
  (`COR_TEX["branco"]`) — and the two bright ones are SENTINELS that keep
  white glyphs and rings off the white→indigo segment the repair guards test.
  Unifying them onto the hull white would make the guards blind to every
  white mark. Documented in `latam_livery_kit.py`'s palette header; the one
  stale constant (`PALETA["LATAM_Branco"]`, still `#F7F9FA` while every blend
  already carried `#E6E7EA`) is fixed so a palette rebuild cannot regress it.
- ~~**787-8 height** 16.48 m vs 16.92 published~~ — **FIXED 2026-08-27, and
  the suspicion inverted**: the FIN was innocent (keel-to-fin-top 14.57 in
  the model vs 14.47 ±0.05 on the -9 APR side view, self-calibrated by its
  own height extent), so the f162f73 fin art was never at risk. The LEGS
  were short (keel clearance 1.91 vs 2.55 drawn) — and coupled to them, the
  engines hung 0.52 too high relative to the hull (F + keel chain) and the
  belly fairing sat 0.33 too deep (cota D). `trem_787.py`: -9 now 17.020 m
  with F 0.70 (0.69-0.76) and D 1.75 (1.75-1.85); -8 16.920 m with declared
  level-attitude residuals (F 0.60 vs its 0.74 min; D 1.65 vs 1.68).

---

## CLOSED (SBGR clips): the 777 shipped sunk to its belly, and the rule that came out of it

Two published GRU GIFs — the departure `_v2` and the roll-out `_v1` — shipped
with the 777 sunk to its belly on the ramp. The placement cited "wheels at
z 0" from the exported GLB, but `export_frota.py` seats every aircraft on the
floor by its own rule, so that datum describes the export and not the master.
**The owner caught it in the published GIFs**; none of the pipeline's numeric
checks had ever been pointed at where the wheels were.

CLOSED: the gear datum is now measured in the master itself — the 777's
`03_Trem` hangs to **z = −5.670** (`scenario_sbgr/place_777.py`,
`hangar_rollout.py` both carry the number and the reason) — and the two clips
were re-shot as `_v3` and `_v2`, since refreshed again over the detailed fleet.

**The review rule this leaves: three frames of every GIF, by eye, before it
ships.** It is the clip-level sibling of the render-and-look gate, and it is the
same lesson as the header of this file read backwards — a numeric check can only
fail on the quantity it was aimed at. Its companions are in `PENDENCIAS.md`:
prove ONE frame before rendering a batch, and treat a GIF outside the historical
size band as a symptom, not luck.

---

## SBGR surround round — what it closed, and what it leaves thin

The 2026-08-26 surround round answered "o entorno está todo muito vazio"
(street-mask fabric, real footprints, the serra canopy, the warehouse belt —
`scenario_sbgr/README.md` §9.4/§10.2). Two findings worth keeping:

- **The "tint sawtooth" on the NE knoll was never landuse tint.** The probe
  found NO landuse polygons under the stepped camo; it was `build_ground`'s
  160 m pad skirt climbing the flank in ragged 25 m infield-grass quads.
  CLOSED: the skirt now clips to flat ground (`dem_slope < 0.12`) and the
  knoll carries scrub crowns. When a defect looks like a texture problem,
  check which MESH owns the pixels first.
- **Streets are the urbanization truth in Brazilian OSM, landuse is not**
  (Bonsucesso: ~50 km of mapped streets under <1 km² of mapped landuse).
  `surround_osm.py` documents the re-query; the mask is reusable for any
  future Brazilian base.

Left thin, none of it gate-blocking:

- **The far NE hills (5–9 km) in the tour's close beat** still read hazy
  olive-tan with sparse crowns — partly honest 17:30 haze, partly the crown
  lattice thinning past 7.2 km. If the owner points there, densify the
  far-flank crowns before touching the haze.
- **The eye-level knoll flank is bare earth** at ranges only
  `ground_city_fence_ne` visits (10 m AGL); the clips obey the >100 m rule
  so no shipped frame shows it. A ground-level clip near the NE fence would
  need a real scrub treatment there.
- **Beyond the 9 km tint reach the height split shades high far city as
  forest** (the Paulista ridge sits ~+50 m over the datum). Under haze it
  reads as dark mass either way; wrong in principle, invisible in every
  current framing.
- **Fabric tint is uniformly residential** where only the street mask says
  urban — the commercial corridors along the Dutra render as house fabric.
  Landuse nuance there needs data OSM does not carry.

---

## Housekeeping: three docstrings name the retired manifest path

`refs_manifest.json` moved to `<aircraft>/refs/manifest.json` in `37cf7b8`, but
three docstrings still quote the old name: `airbus A320neo/fix_sharklet_indigo.py`,
`airbus A321ceo/fix_sharklet_indigo.py` and `boeing 787-9/nose_art.py`.

The peer session fixed the 787-9 docstring (`765d4b7` on its own branch) and
handed the rest back. The two Boeing spec `fonte` fields are done here. **Still
open, deferred on purpose:** the two Airbus docstrings and the two Airbus spec
`fonte` fields (`airbus A321neo/spec_a321.json`, `airbus A321ceo/spec_a321ceo.json`)
— all four sit in folders the wingspan/door round is mid-way through, and that
round is folding per-aircraft builder copies into family modules, so those
scripts may be retired outright.

Three things that outlive the rename, and are the reason this is a hand sweep
and not a find-and-replace:

- **`refs_fetch.py` names `refs_manifest.json` on purpose.** It scans for that
  filename as a STRAY legacy manifest left behind in a folder. A blanket
  substitution across the repo would rename the very string the guard hunts
  for and disarm it silently. Verified: the check is real.
- **`airbus A321ceo/fix_sharklet_indigo.py` — the wording, not the width.**
  Line 3 reads `Photo evidence (all in refs_manifest.json): PT-MXD 2021 …`, and
  "all in" was never true: PT-MXD, PT-MXP and PT-XPB are in
  `airbus A321ceo/refs/manifest.json`, while the PS-LBO frame the same sentence
  cites is in `airbus A321neo/refs/manifest.json`. Manifests were per-folder
  under the old name too. The path swap is the same length here, so no re-wrap
  — but fixing the path alone leaves a sentence that is still wrong. Suggested:
  "all in refs/manifest.json except the neo's PS-LBO, which is in
  airbus A321neo/".
- **`airbus A320neo/fix_sharklet_indigo.py` — the width, not the wording.**
  Line 3 reads `Photo evidence (A321ceo refs_manifest.json: PT-MXD 2021, …` and
  becomes `(airbus A321ceo/refs/manifest.json:` — seven characters longer, on a
  77-column line in a block wrapped at 78. Lines 3–7 want a re-wrap. This file
  never says "all in"; its wording is fine.

The two bullets above were crossed in the first version of this entry, which is
worth a moment: whoever picks this up would grep the A320neo file for "all in",
find nothing, and lose trust in the whole entry. A peer session caught it by
running the grep instead of reading the prose.

## 2026-08-22 — a écharpe traseira posta em julgamento contra a foto
## 2026-08-26 — e o julgamento posto em julgamento: a paralaxe de flanco

O que a rodada de `d981dd8` mediu foi a TINTA contra a REGRA. A de 2026-08-22
mediu a regra contra a foto — mas retificou a foto para o plano y = 0 (o da
deriva, que e o do controle) e leu a PELE, que vive em |y| ~2. Um ponto do
flanco aparece deslocado por y·v, onde v e a projecao do eixo y no quadro; num
telefoto quase-perfil v e nada, num quadro em subida ou de camera proxima chega
a dezenas de px por metro — e desloca TUDO que esta no flanco para a frente ou
para tras, enquanto o controle na deriva continua perfeito. v e mensuravel
dentro do proprio quadro (as duas pontas do estabilizador estao em (x, z)
conhecidos e ±y): `conferir_echarpe.py` agora aceita `v`/`lado`/`rry` por
quadro e amostra a pele no lugar certo. Os quatro "suspeitos" e a "contradicao"
do A319 eram esse artefato:

| tipo | 08-22 (sem v) | 08-26 (com v, deriva ancorada) | veredito |
|---|---|---|---|
| A320ceo | +0.65 | **-0.03 +-0.22** (CC-BFO, H re-ajustado na deriva: BA 0.089/BF 0.037 m) | **exonerada** |
| A320neo | +0.70 | sem veredito no quadro PT-TMN (1024 px, era de entrega); frota atual PR-XBP: **+0.95** | **fica** (regra ancorada na porta 4 da PT-TMN); +0.95 e VARIANTE DE ERA da frota atual, registrada |
| A321neo | +0.78 | **+0.25 +-0.07** (DSC00682, bombordo) e **+0.18 +-0.04** (DSC00896, estibordo) | **exonerada** — dois flancos opostos, paralaxe com sinais trocados, concordam; o +0.78 vinha da DSC00834 (camera proxima) |
| 767-300ER | -0.53 | **+0.03 +-0.04** (CC-CWY MIA) e **+0.15 +-0.08** (CC-CXC em rotacao, az local 26 graus) | **exonerada** — dois quadros, azimutes muito diferentes, concordam |
| 777-300ER | (corrigida em 08-22) | +0.03 +-0.28; v medido e pequeno (vx -0.06 m/m) | a correcao de 08-22 **fica** (aquele quadro e quase perpendicular) |
| A319 | (corrigida em 08-22) | a correcao de 08-22 CARREGAVA a paralaxe inteira (quadro em subida, v = 57 px/m): fronteira re-medida **+0.80 +-0.11 atras** da regra de 08-22 | **movida de novo**: +0.76 m para tras (x >= 24.26 + 1.00z), traseira restaurada a linha do BF da deriva; repintada |

O criterio que tornou os vereditos seguros: **dois quadros independentes por
aeronave** (idealmente flancos opostos — a paralaxe troca de sinal e nao
sobrevive a concordancia) e a **fracao de cruzamento na porta**, que nenhuma
homografia distorce: no A319 a fronteira cruza o TOPO da folha da porta 4 a
58% (PT-TMT corrigida) e 57% (PR-MBU) — a regra de 08-22 punha o topo inteiro
no indigo.

### resolvido em 2026-08-26

- **A "contradicao" da porta 4 do A319 nao existia.** Com v medido no proprio
  quadro, a porta esta a -0.10 +-0.19 m do ACAP (sem v: -1.2 m). O ACAP e o
  modelo estavam certos; a foto tambem — mal lida. A matricula e consistente
  com a caixa atual dentro de +-0.4 m. O titulo segue em aberto (abaixo).

### em aberto

1. ~~O titulo do A319 ainda precisa de arte~~ — **fechado 2026-08-27**
   (entrada propria acima): glifos reconstruidos de arte real na caixa do
   modelo, que a sdu_01 corrobora; a caixa nao foi movida.
2. **O `Reg_E` do A319 guarda PT-TMN, nao PT-TMT.** Pintar a matricula por
   `refazer_marcas.py` escreve a matricula do master. Os glifos certos existem
   so como tinta; `fix_matricula_a319.py` os move como tinta.
3. **Marca indigo sobre branco e invisivel ao teste de cor** de
   `reparar_echarpe`: ela esta SOBRE o segmento branco->indigo. Os titulos do
   A319 e do 777 so sobreviveram porque a regra ganhou caixas `poupar`. Toda
   marca chapada de indigo precisa de uma.
4. **As fronteiras INFERIORES continuam quase ilegiveis**, e 08-26 nomeou a
   armadilha: flanco sombreado com ceu azul de preenchimento classifica sombra
   como tinta (a320ceo: -11.5 +-8.6 graus; a319: n=2 ao poente). A inferior do
   A319 foi TRANSPORTADA com a fronteira (+0.76), nao re-medida — confianca
   baixa declarada no spec. Precisa de um quadro com o ventre iluminado.
   *2026-08-27: o 787-9 ganhou a sua primeira leitura de ventre — o quadro da
   CC-BGG (barriga ao sol) da +5.0 +-3.3 graus da regra, n=18, dentro da
   tolerancia; o da CC-BGF e ao anoitecer e nao responde (n=1).*
5. **Cargueiros, 2026-08-27: as fotos uteis EXISTEM agora — e mudaram a
   pergunta.** A caça achou quadros com a asa LIMPA da cunha: a
   `ref_CC-CXE_appr2.jpg` (que ja estava na pasta do BCF sem ninguem notar),
   a `ref_N536LA_ldg26.jpg` (nova, pouso, 5765px), a `ref_N540LA_stn21.jpg`
   (ja estava na pasta do -300F) e a `ref_N566LA_gua25.jpg` (nova; camera
   quase na vertical — serve de documento, nao de medida). Primeiras leituras
   locais (fronteira x matricula, mesmo flanco = sem paralaxe):
   - na CC-CXE a fronteira dianteira (reta limpa, inclinacao 0.99, n=49
     linhas) TOCA a ponta dianteira da caixa da matricula — a regra
     (`x = 42.65 + 1.00z`, medida na N568LA) poe 0.85 m de folga ali. Ou a
     cunha da CC-CXE esta 0.85 atras da regra, ou a matricula dela esta 0.85
     a vante da caixa herdada — o desempate exige ancora na deriva.
   - **a frota cargueira NAO e uniforme**: contra a altura da fuselagem de
     cada quadro, a matricula mede ~1.7 m na CC-CXE, ~2.2 na N540LA e ~2.6 na
     N536LA — a caixa de spec (1.53 x 0.372, medida na N568LA e herdada por
     todos) nao veste a frota. Matricula-a-matricula, nao ha um "layout de
     frota" unico para validar com um unico quadro.
   - a fronteira INFERIOR esta enfim visivel em dois quadros, mas o
     estabilizador de perfil cruza as colunas de medida e o classificador
     confunde a lamina com tinta — a leitura limpa precisa mascarar o estab.
   O que falta: uma rodada propria, com ajuste ancorado na deriva POR
   AERONAVE-ALVO (CC-CXE para o BCF, N536LA para o -300F), estab mascarado
   para a inferior, e a questao do tamanho da matricula resolvida antes de
   mover qualquer tinta.
