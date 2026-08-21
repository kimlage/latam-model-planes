"""Render the six canonical angles of whichever master is open.

    blender -b "<aircraft>/<MASTER>.blend" --python render_canonicos.py
    blender -b ... --python render_canonicos.py -- 50 64     # cheap look pass

Output goes next to the .blend, with the names verificacao_visual.py expects.
"""
import bpy, os, sys

S = bpy.context.scene
VIEWS = [("CamFrontal", "render_frontal.png"),
         ("CamNariz", "render_nariz.png"),
         ("CamPerfil", "render_perfil.png"),
         ("CamHero", "render_hero.png"),
         ("CamCauda", "render_cauda.png"),
         ("CamBarriga", "render_frente_baixa.png")]

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if argv:
    S.render.resolution_percentage = int(argv[0])
if len(argv) > 1 and hasattr(S, "cycles"):
    S.cycles.samples = int(argv[1])
base = os.path.dirname(bpy.data.filepath)
print("[render] %s  %dx%d @%d%%  samples %s" % (
    os.path.basename(bpy.data.filepath), S.render.resolution_x,
    S.render.resolution_y, S.render.resolution_percentage,
    getattr(S.cycles, "samples", "?")))
for cam, fn in VIEWS:
    ob = bpy.data.objects.get(cam)
    if ob is None:
        print("[render] missing camera", cam); continue
    S.camera = ob
    S.render.filepath = os.path.join(base, fn)
    bpy.ops.render.render(write_still=True)
    print("[render] wrote", fn)
print("[render] done")
