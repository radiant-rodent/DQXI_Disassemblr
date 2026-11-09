---
lane: editor
---
One undo/redo history for the whole editor.

Context: the editor was reworked Godot-style (docs/EDITOR_TODO.md, viewer_rs/src/ui/shell.rs, viewer_rs/src/ui/panels/editor.rs). This task fills one of the gaps listed there.

Owns: viewer_rs/src/app.rs, viewer_rs/src/ui/shell.rs, a new viewer_rs/src/ui/history.rs.

Today only the Level Editor has undo. Add a command-style history shared by all panels (tables cell edits, dialogue edits, script edits, layout edits): labelled steps, Edit > Undo/Redo, Ctrl+Z / Ctrl+Y on whatever panel is active, and a History dock in the Output area showing the steps. Panels register their edits through a small trait; do not rewrite panel internals beyond that hook.

Verify: `cargo build --release` in viewer_rs, `cargo test --release`, and run the editor (`run_editor.bat`) to check the feature. Report what you checked.
