"""Render the 6 canonical angles of the 787-8.

Run headless:
  blender -b "boeing 787-8/B788_LATAM.blend" --python "boeing 787-8/render_canonicos.py"
  blender -b ... --python ... -- 50 64          # 50% resolution, 64 samples (cheap look pass)
"""
import bpy
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
S = bpy.context.scene
VIEWS = [
    ("CamFrontal", "render_frontal.png"),
    ("CamNariz", "render_nariz.png"),
    ("CamPerfil", "render_perfil.png"),
    ("CamHero", "render_hero.png"),
    ("CamCauda", "render_cauda.png"),
    ("CamBarriga", "render_frente_baixa.png"),
]

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if argv:
    S.render.resolution_percentage = int(argv[0])
if len(argv) > 1:
    S.cycles.samples = int(argv[1])
only = argv[2:] if len(argv) > 2 else None

print("[render] engine", S.render.engine, "res", S.render.resolution_x, S.render.resolution_y,
      "@", S.render.resolution_percentage, "%", "samples", getattr(S.cycles, "samples", "?"))
for cam, fn in VIEWS:
    if only and cam not in only:
        continue
    S.camera = bpy.data.objects[cam]
    S.render.filepath = os.path.join(BASE, fn)
    bpy.ops.render.render(write_still=True)
    print("[render] wrote", fn)
