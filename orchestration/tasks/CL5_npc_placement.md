---
lane: npc
after: CL1_level_format
---
Place and define NPCs in the editor.

Read first: docs/CUSTOM_LEVEL_PLAN.md (the target scenario and the state of every piece), orchestration/WORKER_RULES.md,
docs/EDITING.md. Existing tools to reuse: tools/level_records.py (duplicate/delete level records, guided decoder),
tools/bxon_struct.py, tools/map_tool.py, tools/asset_replace.py, tools/script_build.py, tools/text_tool.py,
tools/model_patch.py, tools/patch_asset.py. The user's earlier translation project at ../3DS_Translate
(read-only) has the Azahar emulator, tools/emu harness inputs and docs/AGENT_GUIDE.md: use them for every emulator proof.
A package is done only when its proof passes in the emulator (`python tests/emu/run_cases.py <case>`), and the editor
(viewer_rs, cargo build --release and cargo test --release) still builds. Add your case to tests/emu/run_cases.py.

Owns: tools/npc_tool.py, docs/NPCS.md, viewer_rs/src/ui/panels/editor.rs (NPC node kind only).

Using CL1's schema: how an NPC exists in a level: spawn record (position, rotation, model id, behaviour: stand / patrol / wander), the talk bank
(param/region/<area>/npc_ie.bxon: talk -> variants -> lines), and the script hooks (OnTalk, flags). Trace three retail NPCs end to end.

1. tools/npc_tool.py: list NPCs of a level; create a new one by duplicating a retail NPC record and its talk entry, set model, position, patrol path, talk text;
   remove one. 2. Editor: NPC palette (model chooser with thumbnails from the Models index), the real model drawn at the marker, Inspector fields
   (name, model, behaviour, talk lines editable inline), duplicate/delete working through level_records.

Proof (emulator case npc_new): a newly placed NPC stands at the position with the chosen model and speaks the chosen lines.
