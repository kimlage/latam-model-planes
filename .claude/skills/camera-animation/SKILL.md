---
name: camera-animation
description: Build and fix animated shots of the aircraft — takeoff, orbit, flybys — and the GIF/video they ship as. Use ALWAYS when the subject is animation, camera movement, or a clip that does not feel right: "make an animation", "the camera is too fast", "it feels disorienting", "it stutters", "objects flicker", "the movement isn't fluid", "follow the aircraft". Brings the measurement tools and the defects that reached the owner, each of which had a cause nobody guessed correctly on the first try.
---

# Camera and animation

Every camera defect in this project was diagnosed wrong on the first attempt,
including by the person who wrote this file. The pattern: the visible symptom and
the actual cause were in different layers — motion curve, render setting,
trajectory, or file container. **Measure before fixing.**

## Measure in frame-widths per second, not degrees per second

Degrees per second is not what the eye feels. The perceptual quantity is **how
much of the frame the content crosses per second**, and it depends on the lens as
much as on the pan.

- below ~0.5 w/s — comfortable
- above ~1.0 w/s — disorienting

Measure it honestly: ray-cast a grid of screen points into the scene, re-project
them one frame later, and take the screen displacement. `scenario/camera_metrics.py`
does this. Do not infer it from the curves.

**The lens is the gain on the pan curve.** A shot judged good at 35 mm became
disorienting at 140 mm with a *byte-identical* azimuth curve: 3.7× the focal
length is 3.7× the screen speed. If you reframe by changing the lens, the motion
you already approved is no longer the motion you get.

## The four causes of "it isn't fluid", in the order they were found

**1. Concatenated ease-in/ease-out segments stop the move.** Four eased segments
chained together made the pan rate collapse to 6–11% of its mean at three points
— a 34.5:1 speed ratio inside one continuous movement. It reads as the camera
hitching. Keep the max/min pan-rate ratio under ~5:1 across the whole shot.

**2. A per-frame solver is not a smooth curve.** A bisection that keeps the
subject at a target frame fraction re-solves every frame against the silhouette.
When the *binding* extreme point switches — sharklet to nose tip — the derivative
steps. One switch took apparent width from shrinking 11.2 px/frame to growing
3.9 px/frame in a single frame. Solve, then **smooth the result**, then re-check
the framing globally instead of clamping per frame.

**3. A 360° euler wrap plus motion blur ghosts two frames.** Baked euler Z going
179.616° → −178.813° makes Cycles integrate the transform *across* the wrap: at
subframe 51.25 the camera points 90° away. Both frames render as a translucent
ghost. Unwrap eulers before baking. This is invisible in every curve plot and
shows up only as per-frame sharpness — measure it.

**4. The GIF container carries the stutter.** GIF stores delay in **hundredths of
a second**. 24 fps is 41.667 ms, so encoders alternate 4 cs and 5 cs to hold the
average, and the uneven frames read as hitching. **Pick a frame rate whose period
is a whole number of centiseconds: 25, 20, 10 fps. 24 and 30 are not.** Verify by
parsing the finished file, not by trusting the encode flags.

## "Objects pass too fast" is parallax, not pan

Screen speed of a foreground object scales with the inverse of its distance. A
camera doing 114–158 m/s at 5–19 m altitude was flying **through** a tree line:
the nearest in-frame object was a poplar at 12 m sweeping at 582°/s, wiping the
whole frame in 2–3 frames. No pan adjustment can touch that — the trajectory has
to leave the obstacle.

So: **check the nearest in-frame scenery per frame**, with the object's name.
Design the path around it. If you must remove scenery instead, do it in the
aircraft's file with an exclusion collection — never mutilate the shared
`scenario/` library that other aircraft link.

## "It flickers" — three suspects, and the obvious two are usually wrong

Test in this order, because the cheap test separates them: if it flickers in the
PNGs it is the render; if only after quantisation it is the GIF.

- **Temporal aliasing** on sub-pixel geometry. *Measure the projected width* before
  believing it — masts blamed for flicker measured 2.18–10.40 px, never sub-pixel.
- **Dither crawl.** Also usually innocent: bayer vs none vs sierra2_4a and
  stats_mode diff vs full moved the flicker score under 1%, and the finished GIF
  scored *lower* than its own source frames.
- **Strobing from too little shutter.** This was the real cause. Thin geometry
  stepping ~68 px per frame with 10 px of blur behind it, because the shutter had
  been cut to 0.15 to stop a fast pan smearing the background. Note the coupling:
  a fast pan forces a short shutter, which strobes the foreground. Slowing the pan
  buys back a proper 180° shutter (0.50).

## Making a takeoff read as a takeoff

- **Rotate about the main-gear contact point**, not the aircraft centre. Rotating
  about the centre buries the tail in the runway.
- **The nose gear leaves the ground before the main gear** — 1.3 s in the shot
  that worked. Lifting together reads as the aircraft levitating.
- **Check the tailstrike angle from the evaluated mesh**: rotate every vertex
  about the main-gear contact and find the first one reaching the runway. The
  A320neo model allows only 7.75° against ~11.7° on the real aircraft — a short
  gear leg or a low belly fitting hides here and no static render reveals it.
- Retract the gear *after* liftoff, not during the roll.

## A reveal is bought with angle, not distance

Ending a shot by pulling straight back reads as a dead zoom-out. The owner's
correction, and it is right: **keep orbiting while climbing**, subject centred,
and let altitude and tilt open the frame. In the shot that worked the camera
climbed at 27.5 m/s against the aircraft's 9.9 and swung 21° around it while the
distance only went 129 → 270 m.

Two costs to watch: opening with a *long* lens magnifies motion exactly when it
should calm, so the lens usually shortens into the reveal; and a wide lens shrinks
the background — the Andes went from 44% to 12% of frame height, which is
physically correct and dramatically weaker.

Keep a stable anchor in frame — a pinned horizon — or the eye loses orientation
even when the measured flow is low.
