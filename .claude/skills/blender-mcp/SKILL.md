---
name: blender-mcp
description: Drive Blender through the MCP addon in this project without losing work or drawing the wrong conclusion — start/restart the server, survive socket timeouts on long runs, avoid the render-file race that makes you read the previous render, and the saving rules. Use ALWAYS when running code in Blender, rendering, or when something strange happens: "Blender froze", "no data received", "the render is black", "the object disappeared", "I restarted the computer", "the server went down". Read it BEFORE diagnosing any unexpected render result — several "bugs" in this project were operational artifacts, not modelling ones.
---

# Driving Blender through MCP

The MCP addon listens on port **9876** and runs arbitrary Python inside Blender.
It is quick to use and has three behaviours that mislead you. All three have
already produced a false diagnosis and rework in this project.

`scripts/blender_mcp.sh` wraps the operational side:

```bash
.claude/skills/blender-mcp/scripts/blender_mcp.sh start "airbus A320neo/A320neo_LATAM.blend"
.claude/skills/blender-mcp/scripts/blender_mcp.sh status
T=$(.claude/skills/blender-mcp/scripts/blender_mcp.sh marca)   # BEFORE rendering
.claude/skills/blender-mcp/scripts/blender_mcp.sh wait "airbus A320neo/render_perfil.png" 20 "$T"
```

Take the timestamp **before** firing the render. A batch of 6 angles takes about
2.5 min and often finishes before you get back to waiting for it; a waiter that
only looks forward in time gets stuck waiting for a write that already happened.
The same goes for `find -newermt` with a relative time: `-newermt '1 minute ago'`
evaluated after the batch sees only the last files and makes it look as if the
render hung.

## Trap 1 — "No data received" does not mean it failed

A long render blows the socket timeout. What you get back is an error; what is
happening inside Blender is the run continuing normally to the end.

If you react to the error by resending the command, there are now **two**
renders in the queue, both writing to the same file. That is how trap 2 was
born.

After a timeout: do not resend. Check the side effect (the file, or a `print`
you left in the code) and carry on from the real state.

## Trap 2 — the render-file race

Queued renders write to the same path, one after another. A naive waiter — "the
file exists, so read it" — picks up the **first** one, which is the old render,
made with the previous material graph.

That cost three false "black hull" diagnoses while the material was correct —
later proved by 320 px test renders, all white.

The defence is in the script's `wait`: it waits for the first write after the
start time, applies a 15–25 s margin, and then waits for the file to **stop
changing** in size and mtime. Only then does it read.

A cheap complement: render at 320 px to answer binary questions ("is the
material black or not?"). Seconds instead of minutes, and it isolates material
from geometry before you spend a good render.

## Trap 3 — state that does not survive a reload

**A hidden object's `matrix_world` comes back stale.** After reopening the
`.blend`, objects with `hide_viewport` may return the identity matrix. Before
any code that reads the position of a hidden object (rasterizing decals, for
example), reveal it temporarily and call
`bpy.context.view_layer.update()`. The symptom is cruel: nothing fails, the
result simply comes out wrong — titles vanish from the texture and the count of
painted pixels drops with no error at all.

**A mesh with no user disappears on purge.** Support meshes (registration
glyphs, temporary targets) get collected when nothing references them. If you
are going to depend on them after a reload, set `use_fake_user = True`.

**A crash mid-run leaves the file half-done.** A script that deletes before
recreating, interrupted halfway, saves the deleted state. Prefer creating the
new one and only then removing the old; and save with
`bpy.ops.wm.save_mainfile()` at the end of every block that worked — the
`.blend1` is the only backup there is.

## Starting and restarting

```bash
/Applications/Blender.app/Contents/MacOS/Blender "<path.blend>" \
  --python-expr "import bpy; bpy.ops.preferences.addon_enable(module='blender_mcp_addon'); bpy.ops.blendermcp.start_server()"
```

The script's `start` checks first whether the port is already taken and does not
bring up a second instance — two instances fighting over the same `.blend`
corrupt the file.

Restarting discards everything unsaved. If Blender still answers MCP, save
through it before killing the process. If it is fully hung, `restart` kills it
and brings it back up — and you lose everything since the last `save_mainfile`,
which is one more argument for saving early and often.

After a machine restart, Blender does not come back on its own: the first thing
to do in a new session is `status`, and `start` if it is closed.

## Hygiene for the code you send

**Print whatever can be checked.** Painted pixel counts, vertex counts,
dimensions measured by raycast. Since the socket may drop, the `print` is often
the only evidence of what happened — and it is what lets you compare across runs
("painted pixels fell from 250444 to 192238" is a sign that something
disappeared).

**One block, one subject.** Long blocks that do geometry, material and render
together are hard to resume after a timeout, because you do not know how far
they got.

**Render last, and save first.** If the render blows the socket, the work is
already on disk.
