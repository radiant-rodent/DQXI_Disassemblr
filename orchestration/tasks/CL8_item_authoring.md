---
lane: npc
after: CL1_level_format
---
Author items end to end: definition, icon, shop, chest.

Read first: docs/CUSTOM_LEVEL_PLAN.md (the target scenario and the state of every piece), orchestration/WORKER_RULES.md,
docs/EDITING.md. Existing tools to reuse: tools/level_records.py (duplicate/delete level records, guided decoder),
tools/bxon_struct.py, tools/map_tool.py, tools/asset_replace.py, tools/script_build.py, tools/text_tool.py,
tools/model_patch.py, tools/patch_asset.py. The user's earlier translation project at ../3DS_Translate
(read-only) has the Azahar emulator, tools/emu harness inputs and docs/AGENT_GUIDE.md: use them for every emulator proof.
A package is done only when its proof passes in the emulator (`python tests/emu/run_cases.py <case>`), and the editor
(viewer_rs, cargo build --release and cargo test --release) still builds. Add your case to tests/emu/run_cases.py.

Owns: tools/item_tool.py, docs/ITEMS.md, viewer_rs/src/ui/panels/tables.rs (item hooks only).

Items can be added by claiming one of the 189 placeholder rows (proven). Make that a first-class workflow: 'New item' in the editor picks a free row,
sets name, description, icon, price, category and effect from a template item, and registers it in the item tables the game cross-checks
(item.json, item_kana_order.json, battle_item.bxon). Chest placement: a chest record in a level (CL1) holding that item. Shop entry through the shop table.

Editor: an Items browser with icon thumbnails, New / Duplicate / Delete (free row management), and 'place a chest' from the level editor palette.

Proof (emulator case item_chest): a new item with a custom name and icon is found in a chest placed in a level, appears in the bag, and can be sold in a shop.
