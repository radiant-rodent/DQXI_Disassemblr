---
lane: editor
---
Parent/child scene tree from record paths.

Context: the editor was reworked Godot-style (docs/EDITOR_TODO.md, viewer_rs/src/ui/shell.rs, viewer_rs/src/ui/panels/editor.rs). This task fills one of the gaps listed there.

Owns: viewer_rs/src/ui/panels/editor.rs (scene dock).

scene.json objects have a `path` like `root/+0x38/items[0]/+0x04/items/+0x188/items`. Build a real tree (folders per container, collapsible, counts) in the Scene dock instead of the two flat Placements/Transforms groups. Keep keyboard navigation (Up/Down over visible nodes, Left/Right collapse/expand).

Verify: `cargo build --release` in viewer_rs, `cargo test --release`, and run the editor (`run_editor.bat`) to check the feature. Report what you checked.
