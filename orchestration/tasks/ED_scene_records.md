---
lane: editor
---
Finish record editing in the Level Editor: new nodes of any kind, and proof the game accepts them.

Context: duplicate and delete exist (docs/EDITOR_TODO.md, `tools/level_records.py`, `tests/test_level_records.py`,
Ctrl+D / Delete in `viewer_rs/src/ui/panels/editor.rs`). An array is copied to the end of
`level3d.bxon` with the element added or removed, so no existing pointer moves. Every operation is verified
by re-decoding with a guided decoder; the self-test over every level (4 records each, duplicate and delete) verifies
3,789 of 3,789.

Owns: `tools/level_records.py`, `tests/test_level_records.py`, the node actions in `viewer_rs/src/ui/panels/editor.rs`.

1. **Emulator proof.** Use the harness in `../3DS_Translate/emutest` (via `tools/emu`) to boot a
   mod containing a level with a duplicated placement, a duplicated transform and a deleted transform. Record
   what the game does (loads / hides / crashes) in `docs/EDITING.md`. If the engine rejects appended blocks, say so
   and switch to in-place growth (shift blocks and fix pointers with the guided decoder as the oracle).
2. **Index references.** Find which scripts and tables address level records by index (search `script.nut`
   listings for the level id and the arrays' indices). Make the editor warn on delete when a reference exists.
3. **New kinds.** Add-from-template: let the user add a placement or transform to a level that has none by
   copying from another level's record, with the same verification.
4. **Reparent / move between arrays** (only after 1-3).

Verify: `python -m unittest tests.test_level_records`, `python -m tools.level_records --selftest`,
`cargo test --release` in viewer_rs, and the emulator run. Report what you checked.
