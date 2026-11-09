---
lane: events
after: CL0_warps,CL5_npc_placement,CL7_dialogue_authoring,CL8_item_authoring
---
A script builder: author events without writing Squirrel.

Read first: docs/CUSTOM_LEVEL_PLAN.md (the target scenario and the state of every piece), orchestration/WORKER_RULES.md,
docs/EDITING.md. Existing tools to reuse: tools/level_records.py (duplicate/delete level records, guided decoder),
tools/bxon_struct.py, tools/map_tool.py, tools/asset_replace.py, tools/script_build.py, tools/text_tool.py,
tools/model_patch.py, tools/patch_asset.py. The user's earlier translation project at ../3DS_Translate
(read-only) has the Azahar emulator, tools/emu harness inputs and docs/AGENT_GUIDE.md: use them for every emulator proof.
A package is done only when its proof passes in the emulator (`python tests/emu/run_cases.py <case>`), and the editor
(viewer_rs, cargo build --release and cargo test --release) still builds. Add your case to tests/emu/run_cases.py.

Owns: tools/event_builder.py, docs/EVENTS.md, viewer_rs/src/ui/panels/scripts.rs (a visual event tab only).

The area scripts are Squirrel; tools/script_build.py compiles a limited subset. Provide a small event model (a list of steps: show message, ask a choice, give / take
item, set / test flag, play sound, move NPC, fade, warp to map+locator, start battle, open shop) that generates the Squirrel for a function and splices it into the area
script (new event function plus the hook that triggers it: OnTalk, a trigger, scene start), using the compiler's supported constructs and verifying it compiles.

Editor: an 'Events' tab in the Scripts panel to build and test events, and 'on interact' / 'on enter' slots in the NPC / trigger / chest Inspectors that open it.

Proof (emulator case event_chain): talking to a new NPC shows a message, gives a new item once (flag set), and warps the player on the second talk.
