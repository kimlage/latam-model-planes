"""Chunked, resumable animation render - skips frames already on disk.

    blender -b <scene.blend> -P scenario_sbgr/render_chunks.py -- \
        --dir <frames_dir> --start 1 --end 240 [--no-blur]

One process renders one chunk; the driver shell loops chunks so no single
process lives long enough to matter. GPU pinned to Metal explicitly every
time - device selection has gone intermittent on this machine before.
"""
import bpy, os, sys, time
a = sys.argv[sys.argv.index("--") + 1:]
d = a[a.index("--dir") + 1]
f0 = int(a[a.index("--start") + 1]); f1 = int(a[a.index("--end") + 1])
prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'METAL'; prefs.get_devices()
for dev in prefs.devices: dev.use = (dev.type == 'METAL')
scn = bpy.context.scene
scn.cycles.device = 'GPU'
if "--no-blur" in a:
    scn.render.use_motion_blur = False
scn.render.use_persistent_data = True
os.makedirs(d, exist_ok=True)
for f in range(f0, f1 + 1):
    p = os.path.join(d, "%04d.png" % f)
    if os.path.exists(p):
        continue
    t0 = time.time()
    scn.frame_set(f)
    scn.render.filepath = os.path.abspath(p)
    bpy.ops.render.render(write_still=True)
    print("frame %d  %.1fs" % (f, time.time() - t0), flush=True)
print("CHUNK DONE", f0, f1)
