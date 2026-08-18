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

Render the six canonical angles and build the sheet:

```bash
python3 verificacao_visual.py "airbus A320neo"
```

The script is at the root and expects these files in the aircraft's folder:

| File | Angle | What it is for |
|---|---|---|
| `render_frontal.png` | front 3/4 | nose proportion, windshield, engines |
| `render_nariz.png` | nose close-up | glass, door 1 outline, radome |
| `render_perfil.png` | pure side profile | direct comparison with the reference photo |
| `render_hero.png` | classic 3/4 | overall read; this is what sells or delivers the model |
| `render_cauda.png` | tail | fin sash, hull sash, registration, stabilizers |
| `render_frente_baixa.png` | low front | belly, fairing, landing gear, nacelles |

Output: `verificacao_visual.png` in the aircraft's folder.

To render safely (the render queue has a known race), see `blender-mcp` — in
particular `wait`, which stops you reading the previous render.

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
