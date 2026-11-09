---
lane: editor
---
Draw real models at level markers.

Context: the editor was reworked Godot-style (docs/EDITOR_TODO.md, viewer_rs/src/ui/shell.rs, viewer_rs/src/ui/panels/editor.rs). This task fills one of the gaps listed there.

Owns: viewer_rs/src/ui/panels/editor.rs (viewport overlay), tools/map_tool.py (type->model table).

Placement records carry a `type` id (e.g. 0x40404003). Work out which model/asset each type spawns (scripts + tables), export that mapping to game_assets/maps/type_models.json, and have the Level Editor viewport draw the model (low LOD `_l`) at each marker, tinted when selected, falling back to the current dot + box.

Verify: `cargo build --release` in viewer_rs, `cargo test --release`, and run the editor (`run_editor.bat`) to check the feature. Report what you checked.
