# QA backlog — defects found, not yet fixed

Living triage list. Each entry says what is wrong, how it was found, and what
must not be assumed while fixing it. Delete an entry when its fix is committed.

Nothing here was found by inspection alone: every item came from a gate that
was itself improved, which is the pattern worth keeping — **when a defect
survives, suspect the instrument before the model**.

---

## The 787 wedges sit aft of the rules they were validated against

Found by the fleet-wide tail audit that fixed the wedge rasterizer. Both
Dreamliners' painted wedge is a rigid translation of the rule in their own
builders/specs, aft along x:

| aircraft | forward edge | aft edge | residual after the offset |
|---|---|---|---|
| 787-8 CC-BBF | **+0.48 m** | +0.15 m | 3.8% of the flat wedge |
| 787-9 CC-BGK | **+0.56 m** | +0.65 m | 1.20% |

Both offsets were fitted by minimising the disagreement between the rule and
the flat paint over the tail zone (0.01 m steps). With them in place both
wedges are otherwise clean — smooth boundary, no hole, no splinter — so this is
a **siting** question, not a rasterization one, and `reparar_echarpe.py` carries
the offsets explicitly so its repair removes defects without moving the wedge.

Why it is probably the -9 that is wrong and the -8 that inherited it: the -8's
texture is a piecewise COLUMN RESAMPLE of the -9's (`build_788_livery.py`,
"two plug bands removed, 3-zone mapping"), so whatever the -9's wedge is, the
-8's is that shape pushed through a non-uniform map — which is exactly how two
different offsets arise from one error. The -9's builder is **not in the
repository**; only `extract_b789.py` and `nose_art.py` are. The rule quoted in
`latam_livery_kit`'s own header (`x >= 48.77 + 0.992 z`, `theta <= 117.0 - 5.2
(x - 48.70)`, `x <= 57.14 + 0.3858 z`) is therefore the only written record, and
nothing says whether it or the paint is the measurement.

Settling it needs one profile photograph of CC-BGK or CC-BBF with the fin
trailing edge and the wedge boundary both visible, rectified the way
`spec_763.livery_cc_cwy.fin_bandas_2026-08-20` describes. Until then **do not
"correct" one Dreamliner against the other**. Their offsets are not the same
(0.08 m apart forward, 0.50 m apart aft), and that difference is itself
evidence: a rigid error would carry across unchanged, a resampled one would not.
Copying the -9's numbers onto the -8 would erase the only clue there is.

---

## The wedge rasterizer is shared now; the eleven builders are not

`latam_livery_kit.secoes_do_casco` / `cobertura_echarpe` / `reparar_echarpe`
were added by the tail round and `reparar_echarpe.py` drives them, but **the
per-aircraft builders were not rewritten to call them**. Each still carries its
own copy of the (x, z) -> (x, theta) bridge, so re-running any builder puts its
own defect back. Three specific ones:

- `boeing 767-300ER/b5_livery.py`, `767-300F/b5f_livery.py` and
  `767-300BCF/b5b_livery.py` still define `zc_rz()` with the splice at
  **x = 41.0** — the constant mid-section below, `spec_763.cauda_estacoes`
  above, `dzc = +0.117 m` and `drz = -0.117 m` across one station. Only the
  -300ER's wedge crosses that station (the freighters' starts at x 41.55), so
  only the -300ER showed the 3.0-degree step; the splice is in all three.
- `airbus A321neo/build_a321_fase2_livery.py` and
  `A321ceo/build_a321ceo_fase2_livery.py` still re-solve the wedge as a
  DIFFERENCE of two rules gated on `flat_w` / `flat_i`, and still erase with
  `fac[m] = 0`. The two boxes that punched white into the indigo are
  `box(36.9, 38.45, 0.95, 1.50)` ("old reg, remapped") and
  `box(33.70, 37.05, 1.10, 1.55)` ("old type titles").
- `boeing 787-8/build_788_livery.py` still guards its white-in-wedge refill with
  `np.abs(np.sin(THg)) > 0.10`, which skips `|theta| <= 5.74` deg.

Rewriting them is not a texture round: their wedge paint comes before every
mark, so re-running one re-does the registration, the titles, the lockup and
the door rings, and those went through `refazer_marcas.py` afterwards. The
honest sequence is to make `refazer_marcas.py` the only thing that paints marks
and let the builders paint nothing but flat livery — a round of its own.

Also left, deliberately: **seven of the eleven wedge boundaries are still a
hard binary cut**, painted by `mask -> colour` with no anti-aliasing. Measured
by `reparar_echarpe.py --seco`, the boundary texels that would change if they
were anti-aliased are A319 4627, A320ceo 5583, A320neo 4535, 767-300F 2340,
767-300BCF 2310, 777-300ER 3109, 787-9 3851. It is cosmetic at this scale — one
texel is 9-18 mm on the hull against 32 mm per rendered pixel at the gate's
`CamCauda` — and repainting them means re-rendering seven aircraft for a
change no angle in the gate can resolve. The 777 was already supersampled by
its own builder; it is where the shared function came from.

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

## 2026-08-22 — a écharpe traseira posta em julgamento contra a foto

O que a rodada de `d981dd8` mediu foi a TINTA contra a REGRA. Esta mediu a regra
contra a aeronave. `conferir_echarpe.py` retifica a foto da matricula para o
(x, z) do proprio modelo e amostra a pele atravessando a fronteira que a regra
desenha; o numero abaixo e a mediana de "foto menos regra".

| tipo | dianteira (m) | inferior (graus) | controle na deriva | veredito |
|---|---|---|---|---|
| A319 | +0.33 +-0.40 (n=15) | +18.5 (n=2) | BA/BF a 0.04/0.06 m | **corrigida** — a regra antiga inclinava ao contrario e ia a \|theta\| 150 |
| A320ceo | +0.65 +-0.19 (n=14) | +4.5 (n=2) | sem controle | dentro da resolucao; nao mexida |
| A320neo | +0.70 +-0.07 (n=8) | +19.5 (n=3) | sem controle | idem |
| A321ceo | +0.12 +-0.05 (n=18) | -1.5 (n=3) | sem controle | concorda |
| A321neo | +0.78 +-0.07 (n=22) | -7.0 (n=4) | sem controle | dentro da resolucao; nao mexida |
| 767-300ER | -0.53 +-0.05 (n=9) | sem leitura | sem controle | idem |
| 767-300F | -0.48 +-0.06 (n=4) | +13.0 (n=2) | sem controle | asa cruza a cunha na foto |
| 767-300BCF | +1.30 +-0.06 (n=4) | -10.5 (n=1) | sem controle | asa cruza a cunha na foto |
| 777-300ER | -0.86 (grade 0.25 m, 8 linhas) | sem leitura | BA/BF a 0.18/0.18 m | **corrigida** — comecava 0.86 m atras demais |
| 787-8 | -0.12 +-0.16 (n=6) | sem leitura | sem controle | concorda |
| 787-9 | +0.38 +-0.18 (n=24) | -6.0 +-4.1 (n=10) | sem controle | concorda |

### em aberto

1. **A PORTA 4, O TITULO E A MATRICULA DO A319 ESTAO ~1.2..2.0 m ATRAS DO REAL.**
   Medido na mesma retificacao que valida a deriva a 0.07 m: a porta 4 da PT-TMT
   esta em x 24.60 (modelo 25.81), a matricula em 25.20..27.00 (modelo
   26.46..28.44), o titulo em ~21.2..22.7 (modelo 23.45..25.20). O desenho do
   ACAP concorda com o MODELO na porta, entao ou a derivacao dos plugs errou ou
   o ACAP nao e a PT-TMT. A cunha nao foi ancorada nessas marcas por isso.
2. **O `Reg_E` do A319 guarda PT-TMN, nao PT-TMT.** Pintar a matricula por
   `refazer_marcas.py` escreve a matricula do master. Os glifos certos existem
   so como tinta; `fix_matricula_a319.py` os move como tinta.
3. **Marca indigo sobre branco e invisivel ao teste de cor** de
   `reparar_echarpe`: ela esta SOBRE o segmento branco->indigo. Os titulos do
   A319 e do 777 so sobreviveram porque a regra ganhou caixas `poupar`. Toda
   marca chapada de indigo precisa de uma.
4. **As fronteiras INFERIORES quase nao puderam ser lidas**: o flanco baixo esta
   em sombra em quase todas as fotos e o ventre so aparece em vista obliqua, que
   e onde a paralaxe morde. Dos onze, so o 787-9 deu n=10.
5. **As duas fotos de carga (N568LA, CC-CXE) tem a ASA cruzando a cunha.** Os
   numeros acima para o -300F e o -300BCF valem pouco; falta foto util.
