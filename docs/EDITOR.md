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
8. `python -m tools.patch_game --map <map>` rebuilds the PACK and patches a copy of `romfs.bin`.

## Adding a new record type

1. Add the detection to `tools/bxon_struct.py` or `tools/map_tool.py`.
2. Emit a stable `kind`, `position`, `scale`, `rotation`, and `field_offsets`.
3. Extend `SceneObject` in `viewer_rs/src/ui/panels/editor.rs`.
4. Add a unit test for JSON round-trip and float patching (`viewer_rs/src/tests.rs`).
5. Re-run `python -m tools.map_tool export --all` and `cargo test`.

## Rebuilding a ROM

`tools/patch_game.py` requires same-size patched data. That is true for transform edits because
only float words change. It rebuilds and verifies the RomFS IVFC hash tree before repacking, so a
same-size level edit is a valid cartridge image. Size-changing edits (adding objects, strings,
meshes) need the full RomFS rebuild path in [REBUILD.md](REBUILD.md#files-that-grow).

## Transparency

The model viewport draws like the game: opaque draws first, then alpha-blended, multiply and
additive draws without depth writes. Alpha-tested materials cut out at their own threshold
(`dqxi_alpha_cutoff`), additive ones (mist over pits, glows) add light so their black parts
disappear.

## Code view

Code -> Decompiled functions lists all 18,787 entry points, 250 per page (search by name or address).
Each function opens in the **Readable** view (`decomp/readable/`, from `tools/readable_c.py`): known
function names in calls, `self` for the object a method works on, `self->f_274` instead of
`*(int *)(param_1 + 0x274)`, `u32`-style types, `g_` globals, locals named after what they hold
(`result`, loop counters `i`/`j`, `actorId = GetActorID(0)`), and a header listing named callers and
callees. **Raw Ghidra** shows the untouched output. **8,492 of 18,787 entry points (45.2%) now
have a real (`Subsystem_VerbNoun`) or `maybe_` name** from 128 naming batches; 79 of those names
come from the Squirrel binding tables (`python -m tools.recover_native_names`), which cover 352 of
the ~446 natives scripts call. To improve a name, edit `symbols.json` and rerun
`python -m tools.readable_c`. Sources & assembly lists each source tree, paged the same way.

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
`python -m tools.face_expressions scan` once); choosing one bakes that face in the background
with `tools/face_expressions.py bake` (needs `python` on PATH) and swaps the texture in place.

## Export & Play

The **Export** and **Play** buttons in the top bar (and the *Export & Play* section in the
sidebar) drive the mod pipeline without leaving the editor. They are deliberately thin front
ends for the tools that are already validated: `tools/export_mod.py` for the export and
`python -m tools.emu boot` for the emulator. Nothing about the cartridge or the emulator is
reimplemented in Rust.

### Export

Pick a **Target**, an **Output folder** (defaults to `out/`) and press **Export ...**:

| Target | What is written | When to use it |
|---|---|---|
| Luma LayeredFS folder | `out/luma/titles/<TitleID>/romfs/` with only the changed files, plus `code.ips` if the native executable changed | Recommended on CFW consoles; this is also what Play uses |
| Rebuilt `.3ds` image | `out/3ds/romfs.bin` + `out/3ds/DQXI_modded.3ds` (4 GiB) | Flashcarts / Godmode9; slower and needs 4 GiB free. **romfs.bin only** skips the image rebuild for a quick check |
| CIA | `out/cia/DQXI_modded.cia` + `out/cia/README.txt` (2.7 GB, built from the same validated `.3ds`) | Installing on CFW (FBI/Godmode9). Fakesigned, so signature patches are required. `--target cia` builds the `.3ds` first; budget a few minutes and ~7 GB free |

The panel shows the exact command, streams the exporter's log, and finishes with the
`out/EXPORT_REPORT.json` result. A failed validation or a non-zero export is reported in red;
nothing pretends to have worked when it did not.

### Play

**Play** runs the same pre-flight checks, exports the **Luma** target (Azahar's LayeredFS needs
that layout), then runs:

```text
python -m tools.emu boot build/DQXI.3ds --mod out/luma --seconds 120 --shot ...
```

- **Title-screen smoke test** (on by default) boots, presses START at the end of the opening
  movie, waits for the title menu, takes a screenshot, writes the harness JSON report next to it
  and closes the emulator. The screenshot and the title/crash/hang verdict are shown in the
  panel. This is the fastest honest check that a mod still boots.
- With the smoke test **off**, the same command is run with `--keep-open`: Azahar stays at the
  title screen so you can play. **Stop emulator** closes the `ctl` session and, as a fallback,
  any `azahar.exe` from this project's own `third_party/emutest` folder (the harness uses one
  fixed RPC port and one user dir, so a leftover instance would make the next Play fail).
- **Save state** picks a name from `third_party/emutest/saves/` and passes `--save`. These are
  portable *in-game saves*, not Azahar UI snapshots (emulator states are tied to one Azahar build
  and contain the old heap, so they are not used).
- **Emulator** chooses Vulkan (fastest), OpenGL (workaround for known Azahar 2-way battle/shop
  bugs) or software. **timeout** is real seconds; the game runs 10–20× real time.

The harness itself is documented in `docs/TESTING_EMULATOR.md`; this panel only calls it.

### Pre-flight checks (what blocks an export)

Before writing anything the panel validates the `mod/` workspace and shows every result:

- `mod.json` must parse if present (missing is a warning); RomFS paths must **already exist** in
  the retail RomFS (`game_data/romfs/`). A new path is an error: LayeredFS and the RomFS rebuild
  can replace files but the retail directory/file tables have no free space for new ones.
- Every changed `PACK`/`PACA` is parsed with `tools/pack.py` to prove the archive is readable.
- `mod/code/code.bin`, when present, must be exactly 7,090,176 bytes and
  `tools/check_armv6k.py` must find no changed instruction that a real 3DS/2DS cannot execute.
  Azahar would run ARMv7/VFPv3 code that the hardware faults on, so this check cannot be skipped.
- Optional **Deep asset validators (+85 s)** also runs `tools/verify_assets.py` (a sample of every
  asset family) and `tools/verify_model_textures.py` (every model's `map_Kd` against the BCH
  manifest). On this machine that costs about 15 s + 72 s.

Any `ERROR` row blocks Export and Play; warnings (empty mod, missing `mod.json`, a file identical
to retail) are shown but do not.

### Changes

The **Changes** tab lists every payload file in `mod/` against `game_data/romfs/` (or
`original/exefs/code.decompressed.bin` for `code/code.bin`) with state, size and retail size.
**Revert** asks once, then deletes that override so the retail file applies again; empty
directories are pruned. `mod.json` is metadata and is not treated as an override.

### Settings — testing on a real 3DS/2DS

Set the **SD card root** (the folder that contains `Nintendo 3DS` / `luma`) and press
**Copy to SD**. The panel clears the previous copy of
`<SD>/luma/titles/<TitleID>` and copies the freshly exported title folder there, so a stale
override cannot survive. Enable *Enable game patching* in Luma3DS (hold SELECT at boot). This is
a plain file copy; it does not touch the game or the cartridge image.

Settings (SD path, target, output folder, save, GPU, timeout, check options) are stored in
`editor_projects/playtest_settings.json`. The panel never writes into `original/`,
`game_data/`, or `3DS_Translate/`.

### Limits

- Play uses the project's Azahar install (`third_party/emutest/`, from `tools/emu setup`) and
  `build/DQXI.3ds`. Both must exist; the panel names the missing path instead of guessing.
- The title detector is calibrated for the retail Japanese title data (with a parchment
  fallback for translated/retextured menus) — see `docs/TESTING_EMULATOR.md` §7. A mod that
  changes the boot movie or the title background may need `--no-start` / a custom input movie,
  which this panel does not expose yet.
- CIA export is fakesigned and needs CFW with signature patches. It is a real, verified archive
  (`tools/ctr_cia.py`, 2.7 GB) built from the same `.3ds`; installing it on a real console was not
  tested here (see `docs/EXPORT.md`).

