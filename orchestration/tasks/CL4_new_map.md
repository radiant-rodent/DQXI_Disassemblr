---
lane: argon
after: CL1_level_format,CL3_model_import
---
Add a new map: registry row, level pack files, RomFS entries.

Read first: docs/CUSTOM_LEVEL_PLAN.md (the target scenario and the state of every piece), orchestration/WORKER_RULES.md,
docs/EDITING.md. Existing tools to reuse: tools/level_records.py (duplicate/delete level records, guided decoder),
tools/bxon_struct.py, tools/map_tool.py, tools/asset_replace.py, tools/script_build.py, tools/text_tool.py,
tools/model_patch.py, tools/patch_asset.py. The user's earlier translation project at ../3DS_Translate
(read-only) has the Azahar emulator, tools/emu harness inputs and docs/AGENT_GUIDE.md: use them for every emulator proof.
A package is done only when its proof passes in the emulator (`python tests/emu/run_cases.py <case>`), and the editor
(viewer_rs, cargo build --release and cargo test --release) still builds. Add your case to tests/emu/run_cases.py.

Owns: tools/map_new.py, docs/NEW_MAP.md, viewer_rs/src/ui/panels/editor.rs ('New level' wizard).

The map registry is syscmn/level_map.json (LevelMapCommonParam, 28 bytes/row, row index = map id, ~2,286 rows). The item table is capped by
constants in code.bin (docs/EDITING.md explains how that was found); check the same for level_map: Pack_LoadMasterTables, constants equal to the row
count, per-map arrays sized by it (visited-map flags in the save, area names, map type tables level_mapType.json, BGM level_BGM_param.json,
weather level_weatherVisual.json, time level_3dBGTime.json ...).

1. Decide: can the table grow, or must a new map claim an existing/unused row? List every table keyed by map id that needs a matching entry.
2. tools/map_new.py: create everything for a new map from a template level: level3d / level2d bxon, background model pack, script pack (area script),
   registry row, map type / BGM / time / weather rows, RomFS hash tree and pack entries (tools/romfs_build.py, romfs_hash.py, pack.py).
   Include 'clone map X as Y' (copy then edit) as the first, safest mode.
3. Editor: 'New level' wizard (template + name), the new level appears in the Project dock and opens in the Level Editor.

Proof (emulator case new_map): a script retargets a retail warp to the new map id and the game loads it and the player appears; the save still loads.
