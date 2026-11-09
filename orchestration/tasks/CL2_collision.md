---
lane: argon
after: CL1_level_format
---
Understand and edit collision / walkable area.

Read first: docs/CUSTOM_LEVEL_PLAN.md (the target scenario and the state of every piece), orchestration/WORKER_RULES.md,
docs/EDITING.md. Existing tools to reuse: tools/level_records.py (duplicate/delete level records, guided decoder),
tools/bxon_struct.py, tools/map_tool.py, tools/asset_replace.py, tools/script_build.py, tools/text_tool.py,
tools/model_patch.py, tools/patch_asset.py. The user's earlier translation project at ../3DS_Translate
(read-only) has the Azahar emulator, tools/emu harness inputs and docs/AGENT_GUIDE.md: use them for every emulator proof.
A package is done only when its proof passes in the emulator (`python tests/emu/run_cases.py <case>`), and the editor
(viewer_rs, cargo build --release and cargo test --release) still builds. Add your case to tests/emu/run_cases.py.

Owns: tools/collision_tool.py, docs/COLLISION.md, viewer_rs/src/ui/panels/editor.rs (overlay only).

Find how the game decides where the player may walk and what blocks them: it may live in level3d.bxon, in a separate file in the level
pack (see game_data/packs/level3d/<map>/ and level2d/<map>/), in the BCH, or be computed from the background model. Use the native
functions (decomp/readable names with Collision, Hit, Ground, Nav, Wall, Height) and diff levels.

1. Document the format in docs/COLLISION.md with evidence. 2. tools/collision_tool.py: export to OBJ (for viewing) and import back; a generator that
builds collision from a model (axis-aligned boxes or a triangle soup, whichever the format needs). 3. Editor: a collision overlay in the level viewport.

Proof (emulator case collision_wall): move or add a solid wall in a known level and the player is blocked; remove one and the player passes.
