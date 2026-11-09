---
lane: editor
---
Dockable, tabbed workspace with a saved layout.

Context: the editor was reworked Godot-style (docs/EDITOR_TODO.md, viewer_rs/src/ui/shell.rs, viewer_rs/src/ui/panels/editor.rs). This task fills one of the gaps listed there.

Owns: viewer_rs/src/ui/shell.rs, viewer_rs/src/app.rs.

Evaluate egui_dock (or a small in-house tab/dock tree). Goal: several documents open as tabs (two levels, a table and a model at once), docks that can be dragged between left/right/bottom, a View > Reset layout command, and the layout saved to `editor_layout.json` and restored at start-up.

Verify: `cargo build --release` in viewer_rs, `cargo test --release`, and run the editor (`run_editor.bat`) to check the feature. Report what you checked.
