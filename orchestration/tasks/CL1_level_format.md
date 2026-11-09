---
lane: argon
---
Decode what every record in level3d.bxon means.

Read first: docs/CUSTOM_LEVEL_PLAN.md (the target scenario and the state of every piece), orchestration/WORKER_RULES.md,
docs/EDITING.md. Existing tools to reuse: tools/level_records.py (duplicate/delete level records, guided decoder),
tools/bxon_struct.py, tools/map_tool.py, tools/asset_replace.py, tools/script_build.py, tools/text_tool.py,
tools/model_patch.py, tools/patch_asset.py. The user's earlier translation project at ../3DS_Translate
(read-only) has the Azahar emulator, tools/emu harness inputs and docs/AGENT_GUIDE.md: use them for every emulator proof.
A package is done only when its proof passes in the emulator (`python tests/emu/run_cases.py <case>`), and the editor
(viewer_rs, cargo build --release and cargo test --release) still builds. Add your case to tests/emu/run_cases.py.

Progress so far (read docs/LEVEL_FORMAT.md first, do not redo it): container layout, the 300 array kinds, the 100-byte actor placement partly
read from Field_ActorGimmick_InitFromRecord; method = perturb one word and observe in Azahar; tools/level_inventory.py profiles every kind.

Owns: tools/level_schema.json, tools/level_format.py, docs/LEVEL_FORMAT.md, tools/map_tool.py (scene.json export only).

tools/map_tool.py today finds 'placement' (68-byte) and 'transform' (120-byte) records by plausibility. Nobody knows
what they are. Build the real schema.

1. Walk all 1,196 decoded levels (python -m tools.bxon_struct, game_data/packs/level3d/*/level3d.bxon) and classify every
   array by (path, element size, field statistics). The root has arrays of 16-byte records whose +0x04 points to a 1,092-byte
   container with many sub-arrays (see b001_102c: offsets +0x78, +0x188, +0x1C8, +0x230, +0x240, +0x248, +0x2A0, +0x2F0, +0x300).
2. Find the meaning of each by cross-reading: the native functions that consume level data (decomp/readable, names starting
   Field_, Level_, Actor_, Gimmick_, Locator_, Trigger_), the area scripts (game_assets/scripts/packs/script/<area>/script.decompiled.nut:
   OnPreSetupLevel, OnBeginScene, TrgMapJumpEvent, GetGimmickActorID, GetMapJumpLocatorID...), and by diffing levels that differ in one known way
   (a level with one more NPC, one more chest).
3. Produce tools/level_schema.json: per record kind, the element size, field names/types/units, and which fields are references
   (to another array, a string, a table row). Kinds to cover at minimum: NPC / actor spawns, treasure chests, map-jump triggers
   (map id + locator + jump type), locators (named points), gimmicks (doors, switches), encounter zones, collision/geometry references,
   camera, lights. Mark every field you are unsure about as unknown with the evidence you have.
4. Rebuild map_tool's scene.json export on this schema (kind names instead of 'placement'/'transform'), keeping the old objects readable
   for the editor until the viewer switches over. Keep field_offsets so level_records/edits still work.
5. docs/LEVEL_FORMAT.md: the format, the evidence, the gaps.

Proof: a test (tests/test_level_format.py) that decodes every level with the schema, reports unknown-shape counts per kind (target: 0 for the
kinds listed above), and round-trips each level through the schema writer byte-identically. Emulator: change one decoded field per kind
(an NPC position, a chest item id, a trigger's target map) and observe it in game (case level_format_fields).
