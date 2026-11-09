---
lane: editor
after: CL1_level_format
---
Make warps authorable: list, retarget and create map jumps.

Read first: docs/CUSTOM_LEVEL_PLAN.md (the target scenario and the state of every piece), orchestration/WORKER_RULES.md,
docs/EDITING.md. Existing tools to reuse: tools/level_records.py (duplicate/delete level records, guided decoder),
tools/bxon_struct.py, tools/map_tool.py, tools/asset_replace.py, tools/script_build.py, tools/text_tool.py,
tools/model_patch.py, tools/patch_asset.py. The user's earlier translation project at ../3DS_Translate
(read-only) has the Azahar emulator, tools/emu harness inputs and docs/AGENT_GUIDE.md: use them for every emulator proof.
A package is done only when its proof passes in the emulator (`python tests/emu/run_cases.py <case>`), and the editor
(viewer_rs, cargo build --release and cargo test --release) still builds. Add your case to tests/emu/run_cases.py.

Progress so far (read docs/LEVEL_FORMAT.md, section Warps, first): map id = level_map row; candidate trigger arrays +0x1B8[48] and +0x68[24];
MapJumpEvent -> LoadField traced; a script-started jump fades to black but does not load. Emulator tools: tools/emu/level_probe.py (actions: B, A,
WALK:<dir>), a save made outdoors is the missing piece (record one with the harness's Movie / ctl). Next: outdoor save, walk into a trigger, find locators.

Owns: tools/warp_tool.py, docs/WARPS.md, viewer_rs/src/ui/panels/editor.rs (Warp node kind only).

A warp is a trigger record in the level that fires TrgMapJumpEvent(map_id, locator, jump_type, fade_time) in the area script;
the script may rewrite the arguments, then runs StartEventArg(MapJumpEvent, ...). map_id is the row index of syscmn/level_map.json.
See docs/CUSTOM_LEVEL_PLAN.md.

1. Using CL1's schema find the warp trigger records and the locator records, and how a trigger names its destination
   (map id / locator id / jump type). Explain how the area scripts override them (a_010, a_020 ... examples) and which natives
   are involved. Find one concrete well or door in a village and trace it from record to arrival point.
2. tools/warp_tool.py: list every warp of a level with its source position, destination map (name via level_map.json), locator and type; retarget a warp;
   create a new warp by duplicating an existing trigger (tools/level_records.py) and setting its destination; create a new locator.
3. Editor: Warp nodes in the Scene tree and viewport (arrow to the destination, destination picker from the project's level list), through the same
   Inspector / undo / Save-to-mod path as other nodes. A 'map graph' view in the World workspace showing which levels connect.

Proof (emulator case warp_retarget): a retail door/well is retargeted to another map and the player arrives at the chosen locator; a duplicated
trigger works too.
