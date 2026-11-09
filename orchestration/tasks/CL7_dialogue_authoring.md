---
lane: npc
---
Author new dialogue: new talks, variants and banks.

Read first: docs/CUSTOM_LEVEL_PLAN.md (the target scenario and the state of every piece), orchestration/WORKER_RULES.md,
docs/EDITING.md. Existing tools to reuse: tools/level_records.py (duplicate/delete level records, guided decoder),
tools/bxon_struct.py, tools/map_tool.py, tools/asset_replace.py, tools/script_build.py, tools/text_tool.py,
tools/model_patch.py, tools/patch_asset.py. The user's earlier translation project at ../3DS_Translate
(read-only) has the Azahar emulator, tools/emu harness inputs and docs/AGENT_GUIDE.md: use them for every emulator proof.
A package is done only when its proof passes in the emulator (`python tests/emu/run_cases.py <case>`), and the editor
(viewer_rs, cargo build --release and cargo test --release) still builds. Add your case to tests/emu/run_cases.py.

Owns: tools/text_tool.py (growth paths only), docs/DIALOGUE_AUTHORING.md, viewer_rs/src/ui/panels/dialogues.rs (authoring hooks only).

Today existing lines can be edited. Make it possible to add a conversation: new talk entries and variants (talk -> variants -> 28-byte lines with speaker),
multi-box messages ({PAGE}), choices/branches if the format has them, and speaker names. Check growth limits (row counts constants like items).
Editor: add / duplicate / delete a talk, variant or line in the Dialogues panel with undo, a preview of the message box as the game shows it, a length
warning from the real message-window limits (docs/EDITING.md, AGENT_GUIDE.md), and the unsaved count / Save All.

Proof (emulator case dialogue_new): a new conversation with three boxes and a speaker name plays in game.
