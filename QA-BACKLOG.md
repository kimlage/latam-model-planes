# QA backlog — defects found, not yet fixed

Living triage list. Each entry says what is wrong, how it was found, and what
must not be assumed while fixing it. Delete an entry when its fix is committed.

Nothing here was found by inspection alone: every item came from a gate that
was itself improved, which is the pattern worth keeping — **when a defect
survives, suspect the instrument before the model**.

---

## Windshield: the glass never reaches the centreline

Found by the head-on angle added in `aa2d27d`. Same defect class as the 777's,
fixed in `22500e6`: paint and glazing measured in the **side projection**
cannot see the panes wrapping around the nose, so the glass stops short of the
plane of symmetry and the centre post — the "V" — is missing.

| Aircraft | Symptom |
|---|---|
| **A319, A320ceo, A320neo, A321ceo, A321neo** | Wide black wedge at the top of the windshield where a narrow centre post belongs. Plus a vertical crease on the radome's plane of symmetry converging to a point low on the nose. |

**Method that worked on the 777** (`boeing 777-300ER/spec_77w.json`, commit
`22500e6`) **and then on the 767** (`boeing 767-300ER/spec_763.json`):
re-measure on the manufacturer's **front** view at high dpi, self-calibrated
by fitting the drawn fuselage section from its own centre; store polygons in
`(|y|, z)` and put each vertex **on the surface** — the hull coupling then
generates the V and the 3D wrap by itself. Do not dilate the seal by a single
angle: use the **local** section radius, or the seal comes out ~25% thin
exactly at the crown, where the centre post is.

Three traps the 767 added to that recipe, all of which cost ~10% each and
none of which are visible without a real head-on photograph:

- **The drawn section may not be the real one.** On ACAP D6-58328 p.2-9 the
  front view draws the fuselage as a *circle* (5.545 x 5.466 m) where the
  767 is 5.03 x 5.41. The wingspan in the same view is right to 0.07%, so it
  is the section outline alone that is oversize. Read `(|y|, z)` normalised
  by the **drawn** section and remultiplied by the **true** one.
- **The front view can flatten the glazing.** Its glazing is 0.610 m tall
  against 0.666 m in the side view of the same sheet, and all three head-on
  photographs side with the side view.
- **Set-back and seal must live in the same space.** Head-on, a seal of arc
  `s` on the surface shows as `s·cos(theta)`, while a set-back done in the
  `(|y|, z)` plane shows in full. Mixing them left the outboard mullion 29%
  wide and the narrow No.3 pane 19% thin while the inboard one closed to 1%.

The A320 family stores its windshield as `(x, z)` polygons — the flawed
method — but its builder converts them to a band closing at the crown, which
is why it gets away with it on a much less blunt nose. Fix the method, not
just the numbers.

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

## 787 family: radome joint drawn on the front face

Found by the same head-on angle. On both the **787-8** and **787-9** the
radome joint is drawn as a **circle on the front face** of the nose, inside
the silhouette, instead of a ring at a fuselage station. The windshield
mullions are also wide black bars with torn edges.

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

## A320ceo: ghost door 1

A second tilted wedge outline abuts door 1. Present before the camera fix but
illegible at the grazing 11 m angle; unambiguous now.

---

## Fleet-wide, recorded but not scheduled

- **Tailstrike angles** run short across the A320 family (7.75° modelled
  against ~11.7° real) — a short gear leg or a low belly fitting, inherited by
  every derivation. Documented in each spec.
- **787-8 height** 16.48 m vs 16.92 published, inherited from the -9 (identical
  fin top and ground line in both blends). Fixing it invalidates the per-type
  fin art measured in `f162f73` — a fleet decision, not a local one.
