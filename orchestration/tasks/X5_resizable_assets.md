---
lane: export
after: E4_assets
---
Lift the "same size only" restriction so modders can grow and add content.

Read first: `orchestration/done/E4_assets.md` (§Open problems: no new objects/panes/meshes, no longer
strings, no dimension changes), `orchestration/done/X1_export.md` (RomFS files can only be
replaced), `orchestration/done/E2_text.md`, `docs/EXPORT.md`, and how the translation project
(`..\3DS_Translate\dq11tool\`, read-only) already grows text, packs and layouts — it
ships longer English strings, so it has solved much of this.

Owns: `tools/pack.py`, `tools/patch_asset.py`, `tools/bxon*.py`, `tools/layout_tool.py`,
`tools/export_mod.py`, `tools/repack_rom.py`, tests, `docs/EXPORT.md` / `docs/EDITING.md`.

1. Container level: rebuild PACK/PACA (and SARC where used) with members of any size — recompute
   offsets/size tables/alignment; round-trip identical when unchanged (test over all packs).
2. RomFS level: for the `3ds`/`cia` targets, rebuild the RomFS image (directory/file metadata,
   hash tables, IVFC levels) so files may change size and NEW files may be added; for `luma`,
   LayeredFS already takes any size — verify that path with a grown file.
3. Format level, in this order of modder value: text banks (longer strings — relocate the string
   blocks in BXON), BXON tables (more records), BFLYT (more panes / longer pane text), BCLIM/BFLIM
   (different dimensions/format), BCSTM (different length). Each: unchanged = identical bytes;
   grown = re-parses correctly. Respect the engine limits documented in the translation project's
   AGENT_GUIDE (message window limits, UI heap, Old-3DS memory).
4. Prove one grown text line and one grown table in the emulator via `tools/emu` / `tests/emu`
   (as X3_boot_tests did for same-size edits).
5. Update the editor-side size checks/warnings in the tools so grown edits are allowed where safe
   (the viewer_rs panels call these tools; change Rust only if a check is hard-coded there).
