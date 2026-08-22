#!/usr/bin/env python3
"""Orthographic elevation of the fin — the frame the sash artwork is judged in.

    /Applications/Blender.app/Contents/MacOS/Blender -b "<aircraft>/<X>.blend" \
        --python render_fin_ortho.py -- [px] [samples]

Writes `render_fin_ortho.png` next to the .blend. Like `render_gate.py`, the
camera is built in memory and the master is NEVER saved, so the panel can be
re-shot while another session edits the aircraft.

------------------------------------------------------------------------------
WHY THIS EXISTS
------------------------------------------------------------------------------
The fin sash is specified as CROSSINGS: fractions of the exposed fin at which
each band edge cuts the leading edge, the trailing edge and the root (see
`spec_*.json` -> `fin_bandas_2026-08-20`, and the "per-type fin" section of the
livery-latam skill). Reading a crossing off a render means measuring a length
along the LE against the LE's full length — which only works in an elevation of
the fin, in the same (x, z) domain the texture is rasterized in.

None of the seven canonical gate angles is that. They are perspective cameras
at 90-250 m aimed at the whole aircraft; CamCauda is the closest and it still
foreshortens the fin and rakes the root. So the fin panel is a separate shot,
and `spec_77w.json` already cites the 777's copy by name as the model-only
evidence for its sash conference.

Three of these panels (A319, A320neo, A321neo) were made by a scratchpad script
in the 2026-08-20 sash round and committed without it. The ACAP empennage round
of 2026-08-21 moved two of those fins and raised the doors under all three, and
there was nothing in the repository to re-shoot them with — so they sat in the
tree showing geometry the fleet no longer had. That is the whole reason this
file is here rather than in a scratchpad: the panel is only evidence for as long
as it can be refreshed by whatever moves the geometry.

------------------------------------------------------------------------------
THE FRAME
------------------------------------------------------------------------------
Orthographic, square, PORT side: the camera sits far out on -Y looking towards
+Y, so world +X (aft) runs to the right and the panel shows `Deriva_Sash_E` —
the same side as CamPerfil and as the reference photographs the bands were
measured on.

The frame is derived from the fin's own world bounding box, so every type is
shot the same way and two types can be laid side by side:

    S  = MARGEM x max(fin span in x, fin span in z)     square, metres
    c  = centre of the fin bounding box

MARGEM leaves a little air around the tip and the trailing edge and pulls in the
hull under the root — the fin-root fillet and the écharpe boundary are part of
what the sash has to line up with, so the junction belongs in the frame.

Nothing here is read from the .blend's own cameras: an elevation has no
photographic distance to preserve, and the whole point is that the frame follows
the fin. Move the fin and the panel re-centres on it.

BACKGROUND. The master's world is a sky texture, which tints white paint. The
panel swaps a flat neutral grey in front of CAMERA rays only (Light Path ->
Is Camera Ray); every other ray still sees the master's sky, so the lighting is
the master's lighting and only the backdrop changes. The grey matches the one
the 2026-08-20 panels were shot against, so old and new sheets compare.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

# ---------------------------------------------------------------- constantes

FIN = "Deriva"          # fleet-wide name of the fin mesh
MARGEM = 1.12           # frame side, x the fin's largest span
FUNDO = 0.58            # flat backdrop, linear; renders to sRGB 146 under AgX
SAIDA = "render_fin_ortho.png"


def _caixa(ob):
    return [ob.matrix_world @ Vector(c) for c in ob.bound_box]


def enquadrar(scene=None):
    """Frame the fin: returns (centro, lado) in metres."""
    scene = scene or bpy.context.scene
    bpy.context.view_layer.update()      # matrix_world fresca, senao mente
    fin = bpy.data.objects.get(FIN)
    if fin is None or fin.type != "MESH":
        raise RuntimeError("fin mesh '%s' not found in %s"
                           % (FIN, os.path.basename(bpy.data.filepath)))
    b = _caixa(fin)
    x0, x1 = min(p.x for p in b), max(p.x for p in b)
    z0, z1 = min(p.z for p in b), max(p.z for p in b)
    y0 = min(p.y for p in b)
    lado = MARGEM * max(x1 - x0, z1 - z0)
    centro = Vector(((x0 + x1) / 2.0, y0, (z0 + z1) / 2.0))
    return centro, lado, (x0, x1, z0, z1)


def _fundo_liso(scene):
    """Flat grey for camera rays; the master's sky still lights the aircraft."""
    world = scene.world
    if world is None or not world.use_nodes:
        return
    nt = world.node_tree
    saida = next((n for n in nt.nodes if n.type == "OUTPUT_WORLD"), None)
    if saida is None or not saida.inputs["Surface"].links:
        return
    ceu = saida.inputs["Surface"].links[0].from_socket

    plano = nt.nodes.new("ShaderNodeBackground")
    plano.inputs["Color"].default_value = (FUNDO, FUNDO, FUNDO, 1.0)
    plano.inputs["Strength"].default_value = 1.0
    caminho = nt.nodes.new("ShaderNodeLightPath")
    mistura = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(mistura.inputs["Fac"], caminho.outputs["Is Camera Ray"])
    nt.links.new(mistura.inputs[1], ceu)             # Fac 0: todo o resto
    nt.links.new(mistura.inputs[2], plano.outputs["Background"])   # Fac 1: camera
    nt.links.new(saida.inputs["Surface"], mistura.outputs["Shader"])


def renderizar(pasta=None, px=1300, amostras=96, scene=None):
    scene = scene or bpy.context.scene
    pasta = pasta or os.path.dirname(os.path.abspath(bpy.data.filepath))
    centro, lado, cx = enquadrar(scene)

    cam_ob = bpy.data.objects.get("CamFinOrtho")
    if cam_ob is None or cam_ob.type != "CAMERA":
        cam_ob = bpy.data.objects.new("CamFinOrtho", bpy.data.cameras.new("CamFinOrtho"))
        scene.collection.objects.link(cam_ob)
    cam_ob.parent = None
    cam = cam_ob.data
    cam.type = "ORTHO"
    cam.ortho_scale = lado
    cam.shift_x = 0.0
    cam.shift_y = 0.0
    cam.clip_start = 0.1
    cam.clip_end = 4000.0
    cam.dof.use_dof = False
    # 200 m out on -Y, looking towards +Y with world +Z up: an elevation has no
    # distance of its own, so the standoff only has to clear the aircraft.
    cam_ob.location = Vector((centro.x, centro.y - 200.0, centro.z))
    cam_ob.rotation_euler = (math.pi / 2.0, 0.0, 0.0)
    for c in list(cam_ob.constraints):
        cam_ob.constraints.remove(c)

    _fundo_liso(scene)

    scene.camera = cam_ob
    scene.render.resolution_x = px
    scene.render.resolution_y = px
    scene.render.resolution_percentage = 100
    scene.render.engine = "CYCLES"
    if hasattr(scene, "cycles"):
        scene.cycles.samples = amostras
        scene.cycles.use_denoising = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = os.path.join(pasta, SAIDA)

    print("[fin] %s  fin x %.3f..%.3f  z %.3f..%.3f" %
          (os.path.basename(bpy.data.filepath), cx[0], cx[1], cx[2], cx[3]))
    print("[fin] frame %.3f m square, centre (%.3f, %.3f), %d px -> %.4f m/px"
          % (lado, centro.x, centro.z, px, lado / px))
    bpy.ops.render.render(write_still=True)
    print("[fin] %s" % SAIDA)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    renderizar(px=int(argv[0]) if argv else 1300,
               amostras=int(argv[1]) if len(argv) > 1 else 96)
