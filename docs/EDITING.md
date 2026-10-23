# Editing game assets: one page per kind of change

Every asset family has an editable copy under `game_assets/` and a tool that writes your edit
back into the original game file. You never edit `game_data/` or `original/` by hand.

The general loop is always the same:

1. Find the asset in the viewer (`run_viewer_rs.bat`); its detail panel shows the source file.
2. Edit the standard-format copy (PNG, glTF/OBJ, JSON, WAV, text).
3. Run the write-back tool; it produces a patched game file (most tools keep it **the same
   size**, see the table).
4. Put the patched file back into its pack and a copy of the ROM:
   `python tools/patch_asset.py --pack <pack> --member <file> --replacement <patched>`
   (maps use `python tools/patch_game.py --map <map>`).

The pack and RomFS layer no longer limits size: a member that grows or shrinks makes the PACK
lay its members out afresh, and a PACK that no longer fits its RomFS slot is appended at the end
of the RomFS data with its hash tree and the cartridge layout updated (see
[REBUILD.md](REBUILD.md#files-that-grow)). Compressed packs (`PACA`, e.g. `syscmn.pack` with the
item tables, many map packs) work too: the tools decompress, patch and recompress them.
The remaining "same size" limits in the table come from the format write-back tools themselves:
values, pixels, vertex positions and samples can change, but they cannot yet produce files with
new objects, longer strings or more vertices. A grown file has passed the hash and layout checks
but has not been boot-tested in an emulator yet.

| You want to change | Edit this | Write back with | Limits | Proven by test |
|---|---|---|---|---|
| A UI image | `game_assets/textures/**.png` | `tools/texture_tool.py rebuild` | same size and format | `test_texture_uncompressed_roundtrip` |
| A model's texture | PNG next to the model | `tools/bch_texture_patch.py` | same size; ETC1 is lossy | `test_etc1_texture_encoder_and_bch_replacement` |
| A model's shape | `.obj` next to the model (Blender) | `tools/model_patch.py` | keep vertex/index counts | `test_model_position_patch_roundtrip`, `test_bone_placed_position_patch_lands_where_edited` |
| A model's triangles | `.obj` faces | `tools/model_patch.py --indices` | keep index count | `test_model_index_patch_roundtrip` |
| A material colour | material index | `tools/model_material.py` | diffuse RGBA | `test_material_diffuse_patch` |
| A menu/screen layout | `game_assets/layouts/**.json` | `tools/layout_tool.py rebuild` | structure must stay valid | `test_layout_and_animation_roundtrip` |
| A script | `game_assets/scripts/**/script.nut` (disassembly); read `script.decompiled.nut` beside it to understand the code | `tools/sqbin.py` | edit at assembly level: the decompiled file is read-only, there is no compiler back to bytecode | `test_script_roundtrip`, `tests/test_squirrel_decompile.py` |
| An item price or model | row + field name, e.g. `"Medicinal herb" buy_price` | `tools/table_edit.py set` | named fields only (see `tools/table_schemas.json`) | `test_table_edit_by_field_name` |
| Any other table value | offsets from `game_assets/tables/**.json` | `tools/bxon_patch.py` | same-size values; strings via `Bxon.build_from_json` | `test_table_json_builder_roundtrip`, `test_table_string_roundtrip` |
| Music / sound | `game_assets/audio/**.wav` | `tools/bcstm_encode.py` | PCM16, original channel layout | `test_bcstm_pcm16_reencode_roundtrip` |
| Object placement in a level | Level Editor (`run_editor.bat`) | Export BXON + `tools/patch_game.py` | transforms of recovered records | `test_map_noop_patch_roundtrip`, `editor_float_patch_is_bounded_and_exact` |
| Native code | `src/replacements/*.c` | `tools/build.py` | function must fit its original size | `tests/test_source_replacement.py` |

## Finding your way

- **Names:** model and area lists show in-game names (`w1603b` = Flametang boomerang,
  `b001` = Heliodor Castle). They come from the game's own tables; see
  [ASSETS.md](ASSETS.md#in-game-names).
- **What a file is:** `game_assets/<family>/` mirrors `game_data/`, so the path tells you the
  source pack. Model folders hold `.gltf` (use this in Blender), `.obj`, and their PNGs.
- **Faces:** characters' faces are baked from three textures; pick other expressions in the
  viewer or with `tools/face_expressions.py`.
- **Checking your work:** `python tests/run_all.py`, `python tools/verify_project.py`
  and `python tools/audit_model_textures.py` should all stay green.

## Not possible yet

- Adding new content (objects, strings, meshes): the RomFS accepts larger files, but the format
  write-back tools do not yet create new records, longer strings or extra vertices.
- Editing every table by field name: only fields with recorded evidence are named
  (`tools/table_schemas.json`: items, monsters' model codes, areas). Add a field there with its
  evidence and `tools/table_edit.py` picks it up; everything else is edited by offset.
- Writing scripts as high-level Squirrel source. `tools/squirrel_decompile.py` turns every script
  into readable pseudo-source (`script.decompiled.nut`), but nothing compiles that back to
  bytecode: edits there are ignored. Change `script.nut` (assembly) and use the decompiled file
  to find what to change.

## Example: make Medicinal herbs cheaper

```powershell
python tools/table_edit.py list syscmn/item.json --grep herb
python tools/table_edit.py set syscmn/item.json "Medicinal herb" buy_price 5 --out build/item.bxon
python tools/patch_asset.py --pack syscmn.pack --member item.bxon --replacement build/item.bxon
```
