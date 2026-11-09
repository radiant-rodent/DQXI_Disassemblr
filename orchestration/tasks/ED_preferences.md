---
lane: editor
---
Editor Settings window.

Context: the editor was reworked Godot-style (docs/EDITOR_TODO.md, viewer_rs/src/ui/shell.rs, viewer_rs/src/ui/panels/editor.rs). This task fills one of the gaps listed there.

Owns: viewer_rs/src/ui/shell.rs, viewer_rs/src/theme.rs.

Editor > Editor Settings: UI scale, font size, snap defaults, default workspace, key bindings (rebindable), auto-save interval. Persist to `editor_settings.json` next to the project and apply live.

Verify: `cargo build --release` in viewer_rs, `cargo test --release`, and run the editor (`run_editor.bat`) to check the feature. Report what you checked.
