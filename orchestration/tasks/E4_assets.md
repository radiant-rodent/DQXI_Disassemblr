---
lane: editor
after: X2_playtest
---
Asset replacement workflows in DQXI Studio: textures, models, audio, UI layouts, maps.

Owns: viewer_rs panels textures.rs, models.rs, audio.rs, layouts.rs, maps.rs/editor.rs and their
data modules; tools texture_tool.py, model_tool.py, model_patch.py, bch_texture_patch.py,
etc1_encode.py, bcstm_encode.py, layout_tool.py, map_tool.py; docs/EDITING.md asset sections.

For each family: "Export…" (PNG / glTF / WAV / JSON), "Replace…" (import edited file, encode to
the original 3DS format — correct pixel format, mip count, power-of-two sizes, vertex formats,
DSP-ADPCM — and warn about hardware limits such as VRAM/texture size), preview after replace,
save into the mod workspace. Map editor: object placement edits saved into the level3d data.
Add round-trip tests (unchanged → identical bytes) per family. cargo build/test + tests green.
