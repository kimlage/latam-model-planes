#!/usr/bin/env python3
"""Render an SDSC clip's frames on the GPU. The pattern is `../scenario/README.md` section 8.

    blender -b scenario_sdsc/sdsc_takeoff_v1.blend \\
        -P scenario_sdsc/render_clip.py -- --out /tmp/frames_sdsc_dep/

Options: --out DIR, --samples N, --res W H, --range A B.
Everything else - fps, motion blur, view transform - comes from the .blend the
clip script saved, on purpose: the shot's settings belong to the shot.
"""
import bpy
import os
import sys


def main():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = a[a.index("--out") + 1] if "--out" in a else "/tmp/frames_sdsc/"
    scn = bpy.context.scene
    if "--samples" in a:
        scn.cycles.samples = int(a[a.index("--samples") + 1])
    if "--res" in a:
        i = a.index("--res")
        scn.render.resolution_x = int(a[i + 1])
        scn.render.resolution_y = int(a[i + 2])
    if "--range" in a:
        i = a.index("--range")
        scn.frame_start, scn.frame_end = int(a[i + 1]), int(a[i + 2])

    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "METAL"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = (d.type == "METAL")
    scn.cycles.device = "GPU"

    os.makedirs(out, exist_ok=True)
    scn.render.filepath = out
    scn.render.image_settings.file_format = "PNG"
    print("rendering %d..%d at %dx%d, %d samples -> %s"
          % (scn.frame_start, scn.frame_end, scn.render.resolution_x,
             scn.render.resolution_y, scn.cycles.samples, out))
    bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
