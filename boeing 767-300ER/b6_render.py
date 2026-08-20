"""Renderiza os 6 angulos canonicos do gate (verificacao-visual).

/Applications/Blender.app/Contents/MacOS/Blender -b "boeing 767-300ER/B763_LATAM.blend" --python "boeing 767-300ER/b6_render.py" -- 900 96
"""
import bpy
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
arg = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
LARG = int(arg[0]) if arg else 900
AMOSTRAS = int(arg[1]) if len(arg) > 1 else 96
ALVOS = arg[2:] if len(arg) > 2 else None

VISTAS = [
    ("CamFrontal", "render_frontal.png"),
    ("CamNariz", "render_nariz.png"),
    ("CamPerfil", "render_perfil.png"),
    ("CamHero", "render_hero.png"),
    ("CamCauda", "render_cauda.png"),
    ("CamBarriga", "render_frente_baixa.png"),
]

sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.samples = AMOSTRAS
sc.cycles.use_denoising = True
sc.render.resolution_x = LARG
sc.render.resolution_y = int(LARG * 9 / 16)
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = "PNG"
sc.view_settings.view_transform = "AgX"
sc.view_settings.look = "AgX - Punchy"
sc.view_settings.exposure = 0.20

for cam, fn in VISTAS:
    if ALVOS and fn not in ALVOS and cam not in ALVOS:
        continue
    ob = bpy.data.objects.get(cam)
    if ob is None:
        print("SEM CAMERA", cam)
        continue
    sc.camera = ob
    sc.render.filepath = os.path.join(BASE, fn)
    bpy.ops.render.render(write_still=True)
    print("OK", fn)
print("FIM")
