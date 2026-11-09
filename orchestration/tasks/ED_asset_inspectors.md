---
lane: editor
---
Inspector panels for models, textures and sounds.

Context: the editor was reworked Godot-style (docs/EDITOR_TODO.md, viewer_rs/src/ui/shell.rs, viewer_rs/src/ui/panels/editor.rs). This task fills one of the gaps listed there.

Owns: viewer_rs/src/ui/panels/models.rs, textures.rs, audio.rs (inspector parts).

Give each asset editor the same right-hand Inspector layout as the Level Editor: collapsible groups, editable fields where the tools support it (material blend/alpha, texture format/mips, loop points), revert buttons and a Changes list. Read-only fields stay read-only but are shown.

Verify: `cargo build --release` in viewer_rs, `cargo test --release`, and run the editor (`run_editor.bat`) to check the feature. Report what you checked.
