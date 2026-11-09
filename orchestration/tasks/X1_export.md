---
lane: export
after: P0_regen
---
Export pipeline that turns the mod workspace into something that runs on a real 3DS/2DS.

Owns: new `tools/export_mod.py`, `tools/repack_rom.py`, `tools/patch_game.py`, `tools/recompile_game.py`,
new `docs/EXPORT.md`, new `run_export.bat`.

1. Define/confirm the mod workspace convention `mod/` (`mod/romfs/<same paths as RomFS>`,
   `mod/code/` for native changes, `mod/mod.json` name/version/author). Coordinate with what the
   editor tasks wrote (grep viewer_rs for "mod/") and document it in docs/EXPORT.md.
2. `tools/export_mod.py` targets:
   - `luma`: `out/luma/titles/<TitleID from exheader>/romfs/` with only changed files, plus
     `code.bin` (or `code.ips` against the original decompressed code) if native code changed.
     This is the recommended path for real hardware (Luma3DS game patching enabled).
   - `3ds`: full rebuilt `.3ds` with patched RomFS (and code) — reuse repack_rom.py; fix
     NCCH/ExeFS/RomFS hashes and sizes so it boots on hardware (flashcart/ Godmode9).
   - `cia`: if a CIA builder exists in third_party or can be written in Python from the NCCH
     (stdlib only), produce an installable CIA; otherwise BLOCKED with explanation.
   Validate every output: re-parse it, check all hashes the 3DS checks (ExeFS/RomFS superblock
   SHA-256, IVFC levels), size limits, and that an empty mod exports a byte-identical .3ds.
3. Tests in `tests/` for: empty-mod identity, one modified table → file appears in luma output
   and in the rebuilt .3ds RomFS with correct hashes.
4. `run_export.bat` (asks target, writes to `out/`). Docs: how to copy to SD card / install.
