---
lane: editor
---
Action palette next to Quick Open.

Context: the editor was reworked Godot-style (docs/EDITOR_TODO.md, viewer_rs/src/ui/shell.rs, viewer_rs/src/ui/panels/editor.rs). This task fills one of the gaps listed there.

Owns: viewer_rs/src/ui/shell.rs.

Ctrl+Shift+P lists commands (Export mod, Play, Save, Revert level, Toggle docks, Go to section, Open Azahar...) with their shortcuts and runs them. Reuse the Quick Open window; commands come from a single registry so the menu bar uses the same list.

Verify: `cargo build --release` in viewer_rs, `cargo test --release`, and run the editor (`run_editor.bat`) to check the feature. Report what you checked.
