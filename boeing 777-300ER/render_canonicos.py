"""Render the 6 canonical angles of the 777-300ER.

blender -b "boeing 777-300ER/B77W_LATAM.blend" --python "boeing 777-300ER/render_canonicos.py" -- [pct] [samples]
"""
import bpy
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
S = bpy.context.scene
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
pct = int(argv[0]) if argv else 100
smp = int(argv[1]) if len(argv) > 1 else 96
S.render.resolution_percentage = pct
if hasattr(S, "cycles"):
    S.cycles.samples = smp
VIEWS = [
    ("CamFrontal", "render_frontal.png"),
    ("CamNariz", "render_nariz.png"),
    ("CamPerfil", "render_perfil.png"),
    ("CamHero", "render_hero.png"),
    ("CamCauda", "render_cauda.png"),
    ("CamBarriga", "render_frente_baixa.png"),
    # head-on de verdade (azimute 0, camera 3 graus abaixo do eixo, tele) para
    # comparar o parabrisa com a foto de S2-AFO em refs/. Sem este angulo o
    # defeito do "V" ausente nao aparece em nenhum dos seis canonicos.
    ("CamHeadOn", "render_headon.png"),
]
print("[render] engine", S.render.engine, "res", S.render.resolution_x, S.render.resolution_y,
      "@", pct, "% samples", smp)
for cam, fn in VIEWS:
    if cam not in bpy.data.objects:
        print("[render] SEM CAMERA", cam)
        continue
    S.camera = bpy.data.objects[cam]
    S.render.filepath = os.path.join(BASE, fn)
    bpy.ops.render.render(write_still=True)
    print("[render] wrote", fn)
