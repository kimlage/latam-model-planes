"""Starboard profile — evidence for the lockup mirroring fix (the canonical six are all port).

Run headless:
  blender -b "boeing 787-8/B788_LATAM.blend" --python "boeing 787-8/render_perfil_estibordo.py"
"""
import bpy, os, mathutils
BASE = os.path.dirname(os.path.abspath(__file__))
S = bpy.context.scene
src = bpy.data.objects["CamPerfil"]
cam = src.copy(); cam.data = src.data.copy()
S.collection.objects.link(cam)
cam.location = (src.location.x, -src.location.y, src.location.z)
tgt = mathutils.Vector((28.4, 0.0, 0.6))
cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
S.camera = cam
S.render.filepath = os.path.join(BASE, "render_perfil_estibordo.png")
bpy.ops.render.render(write_still=True)
print("[render] wrote render_perfil_estibordo.png")
