---
lane: editor
---
Central unsaved-changes registry and Save All.

Context: the editor was reworked Godot-style (docs/EDITOR_TODO.md, viewer_rs/src/ui/shell.rs, viewer_rs/src/ui/panels/editor.rs). This task fills one of the gaps listed there.

Owns: viewer_rs/src/app.rs, viewer_rs/src/ui/shell.rs, viewer_rs/src/ui/panels/*.rs (hook only).

Every panel that can hold edits reports `is_dirty()` and `save()` through one registry. File > Save All (Ctrl+Shift+S) saves everything, the window title shows a dot when anything is unsaved, the status bar lists what is dirty, and closing the app with unsaved edits asks first.

Verify: `cargo build --release` in viewer_rs, `cargo test --release`, and run the editor (`run_editor.bat`) to check the feature. Report what you checked.
