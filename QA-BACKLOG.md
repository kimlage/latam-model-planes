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
| **767-300ER** | Glazing stops short of the centreline; a jagged-edged black seal band arches across the crown joining both sides. No centre post, no V. One pane also renders light instead of dark glass. |
| **A319, A320ceo, A320neo, A321ceo, A321neo** | Wide black wedge at the top of the windshield where a narrow centre post belongs. Plus a vertical crease on the radome's plane of symmetry converging to a point low on the nose. |

**Method that worked on the 777** (`boeing 777-300ER/spec_77w.json`, commit
`22500e6`): re-measure on the APR **front** view at high dpi, self-calibrated
by fitting the fuselage circle from its own centre; store polygons in
`(|y|, z)` and put each vertex **on the surface** by bisection — the hull
coupling then generates the V and the 3D wrap by itself. Do not dilate the
seal by a single angle: use the **local** section radius, or the seal comes
out ~25% thin exactly at the crown, where the centre post is.

The A320 family stores its windshield as `(x, z)` polygons — the flawed
method — but its builder converts them to a band closing at the crown, which
is why it gets away with it on a much less blunt nose. Fix the method, not
just the numbers.

---

## 787 family: radome joint drawn on the front face

Found by the same head-on angle. On both the **787-8** and **787-9** the
radome joint is drawn as a **circle on the front face** of the nose, inside
the silhouette, instead of a ring at a fuselage station. The windshield
mullions are also wide black bars with torn edges.

---

## Brand fidelity: the LATAM wordmark's final "M" is broken

**A321ceo and A321neo.** The last diagonal of the "M" sits detached, roughly
14 window pitches aft of the wordmark. The rear écharpe on the same aircraft
carries a detached indigo splinter and a dotted boundary.

This one is different from the others and worth remembering: it was **already
visible in the old profile render**, which barely changed under the new
cameras. It did not hide — it was looked at and passed. Repo rule 1 is exact
brand from the official vectors; a broken glyph is a rule-1 failure.

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
- **Brand symbol proportion**: the 787-8 measures the symbol at 1.58–1.62 m
  wide on two photographs against 1.16 m in the official SVG at the same
  height, while the overall lockup ratio (4.30) matches. The aircraft
  application may use a different symbol/wordmark split than the print vector.
