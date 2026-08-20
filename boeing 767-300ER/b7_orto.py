"""Camera ortografica de perfil (bombordo) alinhada com o mapa da foto de
CC-CWY, para comparar render x foto na MESMA escala.

Enquadramento: x 0..56 m, z centrado em 3.5, ortho_scale 56.
Assim  px = (x/56)*LARG  e  z = 3.5 + (0.5 - py/ALT) * 56 * ALT/LARG.

/Applications/Blender.app/Contents/MacOS/Blender -b "boeing 767-300ER/B763_LATAM.blend" --python "boeing 767-300ER/b7_orto.py" -- 2240
"""
import bpy
import math
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
arg = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
LARG = int(arg[0]) if arg else 2240
ESCALA = 56.0
CX, CZ = 28.0, 3.5

cam = bpy.data.objects.get("CamOrtoPerfil")
if cam is None:
    cd = bpy.data.cameras.new("CamOrtoPerfil")
    cam = bpy.data.objects.new("CamOrtoPerfil", cd)
    bpy.data.collections["09_Cenario"].objects.link(cam)
cam.data.type = "ORTHO"
cam.data.ortho_scale = ESCALA
cam.location = (CX, -400.0, CZ)
cam.rotation_euler = (math.radians(90), 0, 0)

sc = bpy.context.scene
sc.camera = cam
sc.render.engine = "CYCLES"
sc.cycles.samples = 64
sc.cycles.use_denoising = True
sc.render.resolution_x = LARG
sc.render.resolution_y = int(LARG * 17.0 / 56.0)
sc.render.resolution_percentage = 100
sc.view_settings.view_transform = "AgX"
sc.view_settings.look = "AgX - Punchy"
sc.view_settings.exposure = 0.20
sc.render.film_transparent = True
sc.render.image_settings.color_mode = "RGBA"
sc.render.filepath = os.path.join(BASE, "render_orto_perfil.png")
bpy.ops.render.render(write_still=True)
sc.render.film_transparent = False
sc.render.image_settings.color_mode = "RGB"
print("OK render_orto_perfil.png  ortho_scale", ESCALA, "res",
      sc.render.resolution_x, sc.render.resolution_y)
bpy.ops.wm.save_mainfile()
