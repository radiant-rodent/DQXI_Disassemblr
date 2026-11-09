---
lane: editor
---
Play this level from the editor toolbar.

Context: the editor was reworked Godot-style (docs/EDITOR_TODO.md, viewer_rs/src/ui/shell.rs, viewer_rs/src/ui/panels/editor.rs). This task fills one of the gaps listed there.

Owns: viewer_rs/src/ui/panels/editor.rs, viewer_rs/src/ui/panels/playtest.rs (hook), tools/emu.

A Play button in the Level Editor toolbar that saves, stages the mod, and boots Azahar directly into the open map (use the harness in ../3DS_Translate/emutest via tools/emu). Show progress in the Output dock.

Verify: `cargo build --release` in viewer_rs, `cargo test --release`, and run the editor (`run_editor.bat`) to check the feature. Report what you checked.
