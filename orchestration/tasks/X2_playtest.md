---
lane: editor
after: X1_export, E3_scripts, A_emu_harness, A_emu_dedupe
---
One-click "Play" and "Export" in DQXI Studio.

Owns: new `viewer_rs/src/ui/panels/playtest.rs`, minimal registration lines in `app.rs`/`panels/mod.rs`.

1. Toolbar buttons: **Export** (target luma/3ds/cia, output folder, shows log of
   `tools/export_mod.py`) and **Play**: export, then launch the project's Azahar via `tools/emu/`
   (built by A_emu_harness — read `docs/TESTING_EMULATOR.md`) with the mod applied. Options:
   "boot to title only" smoke test (headless check with screenshot shown in the panel) and a
   "load save state" picker. Settings page: SD card path for "Copy to SD" (copies
   `luma/titles/<TitleID>` to the SD) for testing on a real 3DS.
2. A "Changes" panel listing every file in the mod workspace vs original with revert per file.
3. Validation before export: run the per-asset validators; block export on errors.
4. cargo build/test green; update docs/EDITOR.md. Actually click Play once and paste the result.
