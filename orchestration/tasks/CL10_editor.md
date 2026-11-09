---
lane: editor
after: CL0_warps,CL2_collision,CL4_new_map,CL5_npc_placement,CL6_monsters,CL9_events
---
Make the editor do all of it with ease.

Read first: docs/CUSTOM_LEVEL_PLAN.md (the target scenario and the state of every piece), orchestration/WORKER_RULES.md,
docs/EDITING.md. Existing tools to reuse: tools/level_records.py (duplicate/delete level records, guided decoder),
tools/bxon_struct.py, tools/map_tool.py, tools/asset_replace.py, tools/script_build.py, tools/text_tool.py,
tools/model_patch.py, tools/patch_asset.py. The user's earlier translation project at ../3DS_Translate
(read-only) has the Azahar emulator, tools/emu harness inputs and docs/AGENT_GUIDE.md: use them for every emulator proof.
A package is done only when its proof passes in the emulator (`python tests/emu/run_cases.py <case>`), and the editor
(viewer_rs, cargo build --release and cargo test --release) still builds. Add your case to tests/emu/run_cases.py.

Owns: viewer_rs/src/ui/**, docs/EDITOR_TODO.md.

Bring the finished tools into DQXI Studio so the whole scenario can be authored without leaving it: New level wizard, collision overlay and editing, palette
(NPC / monster / chest / warp / locator), real models at markers (ED_scene_models), the map graph, an Events tab, an Items browser, Play this level
(ED_play_in_editor), Save All across everything, a quit prompt, undo for every panel (ED_global_undo), docks that can be rearranged (ED_docking). Work through
every open ED_* task in orchestration/tasks that is now unblocked. Record a screen walkthrough as a doc (docs/WALKTHROUGH_CUSTOM_ROOM.md) with screenshots.

Proof: someone who has never seen the project builds the scenario using only the editor, following the walkthrough.
