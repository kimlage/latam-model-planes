"""Render the 6 canonical angles of the A320ceo.

Run headless:
  blender -b "airbus A320ceo/A320ceo_LATAM.blend" --python "airbus A320ceo/render_canonicos.py"
"""
import bpy
import os

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
print("[render] engine", S.render.engine, "res", S.render.resolution_x, S.render.resolution_y,
      "samples", getattr(S.cycles, "samples", "?"))
for cam, fn in VIEWS:
    S.camera = bpy.data.objects[cam]
    S.render.filepath = os.path.join(BASE, fn)
    bpy.ops.render.render(write_still=True)
    print("[render] wrote", fn)
