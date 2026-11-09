---
lane: editor
---
Edit level2d data in the Scene/Inspector layout.

Context: the editor was reworked Godot-style (docs/EDITOR_TODO.md, viewer_rs/src/ui/shell.rs, viewer_rs/src/ui/panels/editor.rs). This task fills one of the gaps listed there.

Owns: viewer_rs/src/ui/panels/editor.rs (new level2d mode), tools/map_tool.py.

Every map also has `level2d.bxon` (see scene.json `level2d_source`). Decode it, show its records in the Scene dock, draw them on a top-down 2D canvas, and edit them through the Inspector with the same undo/save/export flow as level3d.

Verify: `cargo build --release` in viewer_rs, `cargo test --release`, and run the editor (`run_editor.bat`) to check the feature. Report what you checked.
