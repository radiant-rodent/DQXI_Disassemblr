---
lane: editor
---
Multi-select and group transform in the viewport.

Context: the editor was reworked Godot-style (docs/EDITOR_TODO.md, viewer_rs/src/ui/shell.rs, viewer_rs/src/ui/panels/editor.rs). This task fills one of the gaps listed there.

Owns: viewer_rs/src/ui/panels/editor.rs.

Shift/Ctrl-click and box-select markers, a combined gizmo at the selection centre, one undo step per drag, and an Inspector that shows `(mixed)` fields and edits all selected nodes.

Verify: `cargo build --release` in viewer_rs, `cargo test --release`, and run the editor (`run_editor.bat`) to check the feature. Report what you checked.
