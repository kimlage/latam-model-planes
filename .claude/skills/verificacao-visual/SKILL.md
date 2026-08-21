---
name: verificacao-visual
description: The project's quality gate — render the 6 canonical angles, build the contact sheet, compare against the reference photos, and only then declare an aircraft finished. Use ALWAYS before delivering, showing or saying that something is done, and whenever the question is about status or quality: "is it ready?", "how did it turn out?", "check the model", "generate the renders", "compare it with the photo", "what changed". Use it as well when the owner complains about quality without pointing at the defect — the contact sheet is how you find the defect. Brings the checklist of the errors that have slipped through before.
---

# Visual verification

This gate exists because the project's most expensive failure was not
geometric: it was declaring something done without looking. The owner called
this out more than once — *"tenha certeza de realmente conseguir fazer a
verificacao final visual"* [make sure you can actually do the final visual
verification], and later *"o criterio de qualidade está muitooo baixo. vc nao
olhou oq esta fazendo"* [the quality bar is waaay too low. you didn't look at
what you're doing].

The rule is simple: **nothing ships without passing through here, and "passing
through here" means you open the images and look** — not generate the files and
assume.

## Running it

Two commands, always in this order:

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b "airbus A320neo/A320neo_LATAM.blend" \
    --python render_gate.py -- 1600 96
python3 verificacao_visual.py "airbus A320neo"
```

`render_gate.py` builds the **seven** canonical cameras from the fleet standard
in `cameras_canonicas.py` and renders them. Both scripts are at the root and
work on any aircraft in the repository — there is no longer a per-aircraft
camera list to drift. The old per-aircraft entry points
(`render_canonicos.py`, `b6_render.py`) still work; they are shims onto the
same standard.

| File | Angle | What it is for |
|---|---|---|
| `render_frontal.png` | front 3/4 | nose proportion, windshield, engines |
| `render_nariz.png` | nose close-up | glass, door 1 outline, radome |
| `render_perfil.png` | pure side profile | direct comparison with the reference photo |
| `render_hero.png` | classic 3/4 | overall read; this is what sells or delivers the model |
| `render_cauda.png` | tail | fin sash, hull sash, registration, stabilizers |
| `render_frente_baixa.png` | low front | belly, fairing, landing gear, nacelles |
| `render_headon.png` | **head-on** | windshield wrap and the frontal section |

Outputs: the seven renders, `cameras_gate.json` (the camera provenance) and
`verificacao_visual.png`, all in the aircraft's folder. Each panel of the sheet
is labelled with the lens and the distance that produced it.

The cameras are built **in memory and never saved into the `.blend`**. The
master is only read, so the gate can run while another session is editing the
aircraft.

To render safely (the render queue has a known race), see `blender-mcp` — in
particular `wait`, which stops you reading the previous render.

## The camera standard — read this before adding an aircraft

For a long time the gate judged every aircraft through a lens no reference
photograph uses. `CamNariz` was **45 mm at 18 m** from a 6.2 m nose;
`CamFrontal` **70 mm at 27 m**. Photographs of airliners are taken with long
glass from **90–250 m**.

The error is measurable, not a matter of taste. At 18 m the near surface of a
777 nose — 1.85 m closer than its own centreline — is magnified about **9%**,
while the barrel 10 m behind renders about **38% smaller**. That reads as a
bulging nose on a tapering body. The owner said the 777 nose looked bulbous; the
geometry measured correct against the APR (crown and keel within 0.03 m). The
camera was the defect.

Perspective depends **only on distance** relative to the depth of the subject.
Focal length just crops. So the standard fixes the distance and derives the
lens:

```
D_far  = clamp(3.00 x L, 90, 250) m   whole-aircraft angles
                                      (Frontal, Perfil, Hero, Cauda, Barriga)
D_near = clamp(1.25 x L, 70, 150) m   nose close-ups (Nariz, HeadOn)
```

`L` is the aircraft's overall length, so the standoff scales with the fleet just
as it does in real photography: **A319 at 102 m, A320 at 113 m, A321 at 134 m,
767 at 165 m, 787-8 at 170 m, 787-9 at 189 m, 777-300ER at 222 m.** Sensor is
36 mm full frame throughout. Resulting lenses run **91–538 mm**.

Three rules make it behave:

**Framing is preserved, two ways.** Where the fuselage overflowed the frame on
purpose (the crops: Frontal, Cauda, Nariz, HeadOn), the frame width `W` at the
target plane is kept and the lens comes out as `f = 36 x D / W`. Where the whole
fuselage fitted (Perfil, Hero, and Barriga on the narrowbodies), keep `W`
instead and the subject *shrinks* — flattening the perspective stops magnifying
the near half. So those match the **projected silhouette fill** instead, which
is what the eye actually reads. On the A319 hero that is the difference between
a 107 mm lens and the correct 129 mm.

**Pull back, do not climb.** Moving the camera along its own ray multiplies the
height difference by the same ratio as the distance. `CamNariz`, 2.2 m above its
target at 13 m, would end up 11.7 m above it at 70 m — a crane shot; and the
A319's `CamBarriga` would end up 1.9 m *below* the runway. What a photographer
does is walk backwards. So the **azimuth** and the **height difference in
metres** are preserved, and the horizontal distance becomes `sqrt(D² - dz²)`.
The elevation angle flattens by itself, which is the whole point.

**Floor.** No camera below runway + 1.30 m. On the current fleet this binds only
on `CamBarriga`, by about 3 cm.

The standard validates itself: the `D_near` rule reproduces the `CamHeadOn` that
the 777 agent had found by hand — `1.25 x 73.94 = 92.4 m` against its 93 m, and
aiming at windshield height from eye height (runway + 1.60 m) gives **2.99°**
against its 3°. A rule that re-derives a number measured by another route.

Applying the standard twice gives the same cameras, so it is safe to re-run.

### CamNariz has to frame the NOSE

On all five Airbus narrowbodies `CamNariz` sat at (11, 7.5, 1.6) looking *aft*.
The frame landed on **passenger door 1** and the cabin windows; the windshield
was clipped at the edge of the frame, at a grazing angle. The "NOSE CLOSE-UP"
panel of the contact sheet had never shown the windshield of any Airbus in the
fleet — which is precisely how a windshield defect can survive a gate.

All nine now use the same geometry: **44.2° off the nose axis, from ahead, with
the camera 0.46 x fuselage diameter above the target**, framing `2.20 x` the
fuselage diameter. When you add an aircraft, open `render_nariz.png` and confirm
you are looking at glass, not at a door.

### The seventh angle

`CamHeadOn` exists because none of the six canonical angles showed that the
777's windshield had no centre post — 1.16 m of white paint sat where the "V"
belongs. It is dead on the centreline, at eye height, framing `1.40 x` the
fuselage diameter (wider than the 777's original windshield-specific crop, so
the frontal section reads too). Anything about symmetry, about the plane of
symmetry, or about how a feature wraps around the front shows up here and
nowhere else.

## Compare, do not admire

Open the sheet **side by side with the reference photos of the registration**.
The goal is not to find it pretty; it is to find the divergence. For each panel,
ask what would change if you overlaid the photo.

**If you do not have the photo, stop and go find it now** — `WebSearch` for the
registration, JetPhotos, Planespotters, Wikimedia. Comparing the render with the
*description* in a spec is comparing it with nothing: the description may be
wrong, and in that case the gate approves the error with full confidence. That
is exactly what happened with the 787-9 sash, refined for hours against a text
describing paint that did not exist.

It is worth measuring when the doubt is about proportion: crop the same stretch
from the render and from the photo at the same scale and compare. That is faster
than arguing about whether it "looks" right.

## Checklist — the defects that have slipped through

Every item here is a real error that reached the owner. If you cannot say "I
checked it and it is fine" for all of them, it is not ready yet.

**Nose**
- dented or rippled under the glossy paint (cage too dense — see
  `casco-parametrico`)
- flattened, without the pinched upper lobe — the windshield does not "turn
  forward"
- windshield in the wrong position or the wrong size relative to the tip

**Body**
- phantom waist on the barrel (dimension halo in the extraction)
- barrel rippling instead of constant section
- visible transition between nose, barrel and tail

**Connected parts**
- wing, fin, stabilizer or pylon with a gap at the root
- "floating" landing gear — leg too short, not entering the bay
- any element visibly detached from the body

**Surface and details**
- door reading "half there" (only the top and bottom arcs)
- door buried by the subsurf shrinkage
- windows white or mirrored instead of dark glass
- windows or doors missing on one side only

**Tail — the region that has failed the most**
- indigo hull wedge too small (lower boundary modelled as a straight line in
  `(x,z)` instead of `(x,θ)` — see `livery-latam`)
- jagged boundary or loose islands of indigo (fixed by working per texture line
  instead of per texel)
- hole in the paint over a panel line and a door outline (painted "only where it
  was already white")
- registration broken or duplicated after moving the boundary
- **junction of the fin TE root × stabilizer × tailcone** — check that corner
  specifically, zoomed in; it is where three parts meet and where the owner
  pointed out a defect with everything else already approved

**Livery**
- brand drawn with a lookalike font instead of the official SVG
- fin sash with the leading-edge fillet too wide
- rear sash as a circumferential wrap instead of a diagonal
- belly or tailcone in indigo when they should be white
- registration in the wrong style for that registration/period

**Geometry checks that no render shows**
- **tailstrike angle**: rotate the evaluated mesh about the main-gear contact
  point and find the first vertex reaching the runway. The A320neo model allows
  only 7.75° (limited by the aft drain mast) against ~11.7° on the real
  aircraft — a gear leg that is too short, or a belly fitting too low, hides
  here and never shows up in a static render. Cheap to run, worth running on
  every aircraft.

**Render**
- blown-out white (use `#E6E7EA`, controlled exposure)
- surface with constant roughness reading as plastic

**The gate itself** — twice now the defect was in the instrument, not the model
- **judging shape through a short lens.** If a nose looks bulbous, check the
  camera before touching geometry: at gate distances under ~30 m the near
  surface is magnified by several percent over its own centreline. Read the
  lens and the distance off the contact sheet's own panel labels.
- **a panel that does not show what its title says.** The "NOSE CLOSE-UP" was
  framed on door 1 on five of the nine aircraft. Look at what is actually in
  each frame, not at what the label promises.

## When the owner points out a defect

Three things that worked better than answering fast:

**Reproduce the defect in your own render before touching anything.** If you
cannot see what he saw, you will fix something else. Render the same angle as
the screenshot he sent.

**And render that same angle again afterwards — before saying you fixed it.**
Measuring the artifact (texture, mesh, spec) proves that *something* changed,
not that it changed where he is looking. On the 787-9 a sash correction improved
the numbers from x=55 aft and left x 47–55 untouched; the measurement looked
great and the owner replied *"não mudou nada"* [nothing changed] — because his
region was precisely the one left over. A before/after pair with the **same
camera and the same light** is the only evidence that counts, and it is cheap:
two renders at 320–900 px.

**Attack the cause, not the symptom.** *"O bico está amassado"* [the nose is
dented] was addressed three times by densifying the mesh, and got worse all
three times. The cause was the method, not the resolution.

**Close the loop with evidence.** After the fix, render the same angle and
compare it with the previous one. Saying "fixed" without showing the before and
after is what generates the next round of frustration.

## After the gate

Once the sheet is approved, update `spec_<type>.json` with what the cycle
taught and record in `README.md` what changed. The model is rebuildable from the
spec; whatever is not written there is lost at the next rebuild.
