---
lane: editor
after: CL10_editor,CL3_model_import
---
The acceptance scenario, as an emulator case.

Read first: docs/CUSTOM_LEVEL_PLAN.md (the target scenario and the state of every piece), orchestration/WORKER_RULES.md,
docs/EDITING.md. Existing tools to reuse: tools/level_records.py (duplicate/delete level records, guided decoder),
tools/bxon_struct.py, tools/map_tool.py, tools/asset_replace.py, tools/script_build.py, tools/text_tool.py,
tools/model_patch.py, tools/patch_asset.py. The user's earlier translation project at ../3DS_Translate
(read-only) has the Azahar emulator, tools/emu harness inputs and docs/AGENT_GUIDE.md: use them for every emulator proof.
A package is done only when its proof passes in the emulator (`python tests/emu/run_cases.py <case>`), and the editor
(viewer_rs, cargo build --release and cargo test --release) still builds. Add your case to tests/emu/run_cases.py.

Owns: tests/emu/cases/custom_room.py, docs/WALKTHROUGH_CUSTOM_ROOM.md.

Build the scenario in docs/CUSTOM_LEVEL_PLAN.md using only the editor's save paths, export the mod (Export & Play), and add the emulator case custom_room that:
boots a new game save at a village with a well, descends, walks the tunnel, arrives in the new room, talks to the placed NPC (custom lines), opens the chest (new item
appears in the bag), triggers the monster battle, and returns through the tunnel. Capture screenshots as evidence. Also produce the Luma3DS folder and a CIA
(tools/export_mod.py) and report whether it passes the real-hardware rules (ARMv6K, memory limits).

Proof: python tests/emu/run_cases.py custom_room passes, and the report lists anything that only worked in the emulator.
