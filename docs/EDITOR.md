# Level Editor

The editor lives in `viewer_rs/` and is opened with `run_editor.bat`. It loads the data produced
by `tools/map_tool.py export --all`.

## What the editor knows

For each map, `game_assets/maps/<map>/scene.json` contains:

- `id`, `source` (the original `level3d.bxon`), `background_bch`;
- `objects`: records recovered from fixed-size structures in the BXON graph.

Two record shapes are currently exposed:

| Shape | Fields | Interpretation |
|---|---|---|
| 68 bytes | position `+0x00`, scale/size `+0x30`, type `+0x3C` | placement / collision / locator candidate |
| 120 bytes | position `+0x00`, scale `+0x18`, rotation `+0x60` | transform candidate |

Every object also carries exact `field_offsets`, so the editor writes edits back as little-endian
floats at those byte offsets. `structure.json` next to the scene holds the full structural graph
for inspection.

This is deliberately conservative: the original schema is not stored in the file, and the
semantic name of each record type is still being recovered. The marker labels tell you what is
known, not more.

## Workflow

1. Pick a map in the left list.
2. The environment mesh is loaded from
   `game_assets/models/packs/3d/bg/<map>/<map>/<map>.obj` (or a map-named fallback).
   `usemtl` groups, UVs, and MTL `map_Kd` textures are applied per material, so floors, walls,
   props, and character models render with their extracted textures.
3. Drag with the left mouse button to orbit, right/middle drag to pan, wheel to zoom (each wheel
   notch is a steady ~12% step; the Models section also has − / + buttons and **Open in Blender**,
   which loads the glTF with its textures).
4. Click a marker to select it. With **Drag selected** on, drag the marker to move it in the camera plane; **Snap 0.25** rounds to quarter units. The inspector also exposes exact numeric position, scale and rotation.
5. **Bounds** draws the recovered box extents; **Focus** centers the camera on the selected marker. Undo/Redo uses in-memory snapshots.
6. **Save project** writes `editor_projects/<map>.json`; **Load project** restores it (including undo).
7. **Export BXON** writes `game_assets/maps/<map>/level3d.patched.bxon`.
8. `python tools/patch_game.py --map <map>` rebuilds the PACK and patches a copy of `romfs.bin`.

## Adding a new record type

1. Add the detection to `tools/bxon_struct.py` or `tools/map_tool.py`.
2. Emit a stable `kind`, `position`, `scale`, `rotation`, and `field_offsets`.
3. Extend `SceneObject` in `viewer_rs/src/ui/panels/editor.rs`.
4. Add a unit test for JSON round-trip and float patching (`viewer_rs/src/tests.rs`).
5. Re-run `python tools/map_tool.py export --all` and `cargo test`.

## Rebuilding a ROM

`tools/patch_game.py` requires same-size patched data. That is true for transform edits because
only float words change. For size-changing edits (adding objects, strings, meshes), rebuild the
whole RomFS and regenerate its IVFC hash tree first.

The current patcher does **not** regenerate the RomFS hash tree. Use an emulator that tolerates
that, or implement the hash rebuild before relying on strict hardware checks.

## Transparency

The model viewport draws like the game: opaque draws first, then alpha-blended, multiply and
additive draws without depth writes. Alpha-tested materials cut out at their own threshold
(`dqxi_alpha_cutoff`), additive ones (mist over pits, glows) add light so their black parts
disappear.

## Code view

Code -> Decompiled functions lists all 18,787 functions, 250 per page (search by name or address).
Each function opens in the **Readable** view (`decomp/readable/`, from `tools/readable_c.py`): known
function names in calls, `self` for the object a method works on, `self->f_274` instead of
`*(int *)(param_1 + 0x274)`, `u32`-style types, `g_` globals, locals named after what they hold
(`result`, loop counters `i`/`j`, `actorId = GetActorID(0)`), and a header listing named callers and
callees. **Raw Ghidra** shows the untouched output. 460 functions (2.4%) have a recovered name, 79 of
them from the Squirrel binding tables (`python tools/recover_native_names.py`), which name 352 of the
~446 natives scripts call;
the rest stay `func_<address>` until named (add names to `symbols.json`, then rerun
`python tools/readable_c.py`). Sources & assembly lists each source tree, paged the same way.

## Model categories

Models are grouped by the game's naming: `cha` Characters, `m` Monsters, `w` Weapons, `g` Props,
`ccg`/`fcg` Cutscene models, `ani` Animals, `r` Mounts, and everything under `bg/` Maps.

## Start-up and the other sections

The window is usable immediately. Textures, models, layouts, scripts, tables and audio are indexed
in parallel in the background, and each section opens as soon as its own index is ready (the
sidebar shows `n / 7`). Map areas are built last because they cross-reference all the others.

Model and area lists show in-game names where the game tables provide them
(`tools/build_model_names.py`): "Flametang boomerang" for `w1603b`, "Heliodor Castle" for `b001`.
Search matches both the id and the name.

The audio player has a seek bar, ±10 s buttons, and a clickable waveform: click or drag anywhere
on the waveform to jump there; the gold line is the playhead.

Character models with a layered face get an **Expression** dropdown in the Models viewport. It
lists the most common eye/mouth poses from `game_assets/models/face_expressions.json` (run
`python tools/face_expressions.py scan` once); choosing one bakes that face in the background
with `tools/face_expressions.py bake` (needs `python` on PATH) and swaps the texture in place.
