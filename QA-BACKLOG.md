# QA backlog — defects found, not yet fixed

Living triage list. Each entry says what is wrong, how it was found, and what
must not be assumed while fixing it. Delete an entry when its fix is committed.

Nothing here was found by inspection alone: every item came from a gate that
was itself improved, which is the pattern worth keeping — **when a defect
survives, suspect the instrument before the model**.

---

## Fleet-wide: the nose tip is a valence-32 pole

The other half of the head-on complaint from `aa2d27d` — "a vertical crease on
the radome's plane of symmetry converging to a point low on the nose". The
windshield fix left it alone, because it is not paint and not the mask.

The fuselage cage ends in **one** vertex at (-0.040, 0, -0.716) with **32 edges
and 32 faces**: every station behind it carries 32 vertices and they all
converge there. Catmull-Clark keeps an extraordinary vertex of that valence
tangent-plane continuous but lets the curvature blow up, and the paint's clear
coat (Coat 1.0, Coat Roughness 0.05) turns that into a dark radial wedge with a
bright specular eye at the apex. It sits on the plane of symmetry because the
pole does, and it reads *low* on the nose because CamHeadOn is at eye height,
2.95 m below the nose tip — we are looking at the underside of the radome.

Measured on the A320neo. All five Airbus share that cage (identical station
list) and the Boeings are built by the same recipe, so expect it fleet-wide.

Fixing it is a HULL change: the tip needs a quad cap instead of a 32-fan, which
moves every vertex of the first stations and invalidates the nose gates. Left
open for the same reason the 767's cockpit pinch was.

---

## 767-300ER: the cockpit pinch is now unjustified

Left open by the windshield fix (`d401766`). The hull's cockpit pinch was
calibrated visually against "glazing out to |y| ~ 1.71", which turned out to
be the isotropic misreading of a front view that draws the section oversize —
the corrected figure is 1.564. The pinch was not touched, because changing it
changes the hull and invalidates other gates.

Two independent signals say it is worth re-measuring: head-on, the glazing
occupies a smaller fraction of the nose width than in the photographs while
the glazing's **own** aspect matches to 2% — which points at the nose being
too blunt at the cockpit rather than at the glass. The fuselage silhouette
could not be measured in any of the nine reference frames (trees, heat
shimmer, or white against a white sky), so this needs a better photograph or
a different method.

Also open on the same aircraft: the glazing's z position is 0.068 m
unresolved — the front view puts its centre at z = 0.876 and the side view of
the same sheet at 0.808, and no photograph resolves it head-on.

---

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

## A321ceo / A321neo: the rear écharpe splinter and its dotted boundary

What is left of the old "broken M" entry. The **wordmark half is fixed**: the
bisection was the forward plug's +4.27 m shifting the texture columns aft of
its station, cutting the mark into "LATAN" plus an orphan 0.385 m of the "M" at
x 15.77–16.16. Both A321s were re-rasterized in `(x, θ)` and the orphan station
now measures **0 indigo texels**.

Still open on both: the rear écharpe carries a **detached indigo splinter** and
a **dotted lower boundary** where the wedge meets the TE root fairing. Present
before and after the marks round — it is a wedge-rasterization defect, not a
brand one.

Worth keeping from the original entry: this was **already visible in the old
profile render**, which barely changed under the new cameras. It did not hide —
it was looked at and passed.

Looked at again during the windshield round (2026-08-21) and **not** fixed: the
splinter and the dotted edge live where the wedge's forward straight line
`x >= 28.51 + 0.63 z` meets the keel cut `z >= -1.2, |theta| <= 145`, which is
the echarpe rasteriser, not the nose mask. Fixing it means re-running the wedge
paint on both A321s, which is a different round from this one.

---

## A319: the type title reads "AIRBUS A3"

Found by the `(x, θ)` marks audit, which measured the right box on the PT-TMT
photo (`refs/ref_sdu_00.jpg`: x 22.40–24.35, whole title on the white, rear end
~0.12 m ahead of the boundary) and then **declined to move the ink**.

The reason is worth stating: the glyphs "1", "9" and the Airbus swirl were
destroyed when the wedge was painted over them, and **the source art no longer
exists in the blend** — there is no A319 title mesh. Moving the surviving ink
would only float a truncated title at the right station. The fix needs
`airbus_a320neo_logo.svg` re-imported and the digits rebuilt, which is the
deviation `spec_a319.json → livery_pt_tmt.titulo` already documents.

---

## Door outlines painted in the (x, z) projection — "ghost door 1"

Was "A320ceo: ghost door 1"; measured during the windshield round and it is the
**same defect class the windshield had**, so it is worth stating in those terms.

`door_ring()` in the livery builders (`airbus A320ceo/build_a320ceo_livery.py`,
and the master's ancestor of it) takes the door's **(x, z) bounding box** and
paints `rounded_rect(Xg, Zg, x0, x1, z0, z1, r)` — a rectangle in the SIDE
projection. The door leaf itself is built analytically **on the surface**. On
the shoulder the two diverge badly:

| where the door is at z > 1.4 | `|y|` |
|---|---|
| door 1 mesh (`Porta1_D`) | 1.571 .. 1.831 |
| painted ring in LiveryTex | 0.865 .. 1.114 |

0.5-0.7 m apart on the same hull, which is what reads as a second, tilted door
outline abutting the real one. Measured on the **A320neo** (the master) and the
**A320ceo**; the A319 and both A321s inherit the same texture recipe, and door
2, the overwing exits and the three cargo doors all go through the same
function.

The fix is the windshield's fix — describe the ring on the developed surface and
rasterise it in `(x, theta)` — not a numeric tweak, and it is a livery round for
five aircraft. Left for one.

---

## A320 family: the wingspan is 2.4-2.8 m over

Found by the export pipeline (`457cbfe`), which compared every exported
bounding box against the aircraft's own spec. The four Boeings agree to a few
centimetres. All five Airbus do not:

| Aircraft | declared span | model measures | over by |
|---|---|---|---|
| A320neo, A320ceo, A321ceo, A321neo | 35.80 m | **38.23 m** | +2.43 m (6.8%) |
| A319 | 34.10 m | **36.92 m** | +2.82 m (8.3%) |

Blender measures the same figure directly on the masters, so this is the
geometry, not the exporter. The A321ceo build had already flagged it in
passing as an "inherited family deviation", and the sharklet round noted a
~7% oversize wing from a third direction — three independent sightings, now
with numbers.

It is a MASTER defect: the A320neo is the family parent, so every derivation
inherited it. Fixing it means the wing planform, which is upstream of the
sharklets/fences, the engine stations and every gate render.

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

- **Tailstrike angles** run short across the A320 family (7.75° modelled
  against ~11.7° real) — a short gear leg or a low belly fitting, inherited by
  every derivation. Documented in each spec.
- **The hulls render pure white.** 76% of `LiveryTex` is exactly `1.0`,
  against `#F5F6F8` in the specs and `#E6E7EA` in the livery rule — the
  eurowhite the whole fleet is supposed to wear. Found on the 787s while
  fixing their mullions, but it is fleet-level and pre-existing: a hull that
  clips to pure white loses the shading that tells a viewer it is a curved
  surface, which is part of why the noses read as flat in some angles.
- **787-8 height** 16.48 m vs 16.92 published, inherited from the -9 (identical
  fin top and ground line in both blends). Fixing it invalidates the per-type
  fin art measured in `f162f73` — a fleet decision, not a local one.

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
