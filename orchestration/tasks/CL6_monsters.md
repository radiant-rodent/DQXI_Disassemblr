---
lane: npc
after: CL1_level_format
---
Define monsters and place encounters.

Read first: docs/CUSTOM_LEVEL_PLAN.md (the target scenario and the state of every piece), orchestration/WORKER_RULES.md,
docs/EDITING.md. Existing tools to reuse: tools/level_records.py (duplicate/delete level records, guided decoder),
tools/bxon_struct.py, tools/map_tool.py, tools/asset_replace.py, tools/script_build.py, tools/text_tool.py,
tools/model_patch.py, tools/patch_asset.py. The user's earlier translation project at ../3DS_Translate
(read-only) has the Azahar emulator, tools/emu harness inputs and docs/AGENT_GUIDE.md: use them for every emulator proof.
A package is done only when its proof passes in the emulator (`python tests/emu/run_cases.py <case>`), and the editor
(viewer_rs, cargo build --release and cargo test --release) still builds. Add your case to tests/emu/run_cases.py.

Owns: tools/monster_tool.py, docs/MONSTERS.md, viewer_rs/src/ui/panels/editor.rs (encounter zone kind only), viewer_rs/src/ui/panels/tables.rs (monster hooks only).

Trace: encounter zone records in a level -> gamecmn/encount_table.json -> enemy_base / enemy_battle / enemy_AI / enemy_pop tables -> model and skills.
Visible-on-field enemies (symbol encounters) versus random ones. See docs/EDITING.md (Encounters) for what is editable.

1. Can new monster rows be added (row-index limits like items?) or must a placeholder / unused row be claimed? Document with evidence.
2. tools/monster_tool.py: create a monster from an existing one (clone row across the enemy tables, new name/stats/skills/drops, re-skinned texture),
   assign it to an encounter group, place an encounter zone / symbol enemy in a level.
3. Editor: Monster palette, encounter zone volumes in the viewport, an Inspector that shows the monster's stats and edits them.

Proof (emulator case monster_new): the new monster appears in a battle in the new location with the chosen stats, and the battle ends normally.
