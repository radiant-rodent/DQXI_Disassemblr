# Getting started (environment and data tree)

Read [`../README.md`](../README.md) for what the project is, then
[`FIRST_MOD.md`](FIRST_MOD.md) for the 10-minute edit. This page is only about *preparing the
machine and the generated data*.

## Prerequisites

- Windows 10/11 with PowerShell (the commands below are PowerShell-compatible).
- Python 3.12 with `Pillow`, `numpy` and `capstone` (used by conversion, model and disassembly
  tools). `python -m pip install pillow numpy capstone` if they are missing.
- Rust toolchain (`cargo`) only for DQXI Studio / the viewer.
- Ghidra 12.1.4 + JDK 21 only if you want to regenerate the raw decompiler export.
- Your own legally obtained `DQXI.3ds` dump. The reference copy is
  `..\3DS_Translate\DQXI.3ds`; the project's extracted baseline lives in
  `original/` and `build/`.
- Optional for a real console: a 3DS/2DS with Luma3DS and an SD card.

Run everything from the repository root. Use the module form shown here:

```powershell
python -m tools.verify_project
```

`OVERALL: PASS` means the generated tree is consistent (build, assets, readable code, maps,
editor binary). The first run prints one line per check. If it fails, fix that check before
editing anything — see `audit/PROJECT_VERIFICATION.json`.

The guides use `python -m tools.<tool>` from the repository root; the equivalent
`python tools/<tool>.py` form also works.

## 1. Regenerate the extracted tree (only if `game_data/` is missing)

The extraction is about 10 GB and takes several minutes:

```powershell
python -m tools.extract_game_data --all
python -m tools.extract_arcs
```

Result:

- `game_data/romfs/` — exact original files, including `.pack`/`.paca` containers;
- `game_data/packs/` — every archive member exploded;
- `game_data/arcs/` — every SARC member (`bflyt`, `bflan`, `bflim`, …).

If a command stops, fix the first reported file; do not silently skip it. The manifests in
`audit/` and `game_data/manifest.json` are the source of truth for coverage.

## 2. Convert to standard formats (only if `game_assets/` is missing)

```powershell
python -m tools.convert_assets --all
python -m tools.map_tool export --all
```

This writes `game_assets/`. One family at a time is also supported and is what you want when
iterating:

```powershell
python -m tools.convert_assets --textures
python -m tools.convert_assets --models --workers 12   # ~2.5 min for all 10,542 BCH
python -m tools.convert_assets --tables
```

The text banks (`game_assets/text/`) are produced separately:

```powershell
python -m tools.text_tool export
```

`tools.table_edit` and `tools.text_tool` also work directly on the extracted BXON files if you do
not want the JSON dump first; the editors use the dump.

## 3. Open DQXI Studio

```powershell
run_editor.bat        # level editor
run_viewer_rs.bat     # project browser
```

Both build `viewer_rs/target/release/viewer_rs.exe` on first use (a few minutes). Set
`DQXI_START_SECTION=<section>` to choose the start panel; the 13 sections are listed in
[EDITOR.md](EDITOR.md).

The Studio's data-edit buttons shell out to the same Python tools, so the CLI commands in
[EDITING.md](EDITING.md) are also available without the GUI.

## 4. Verify before you edit

```powershell
python -m tools.build            # asm/ -> build/code.bin, must say 0 differences
python -m tools.verify_project   # data + coverage + editor + patched-ROM report
python tests/run_all.py          # tier 1-4 end-to-end suite
cd viewer_rs; cargo test; cd ..
```

`tools.build` is the safety net for the whole native-code side: if it is green, the assembly
tree still describes the retail executable. Never weaken that check to make an edit pass.

## 5. If something looks wrong

- `audit/GAP_REPORT.md` and `audit/SOURCE_QUALITY.md` for known coverage gaps,
- `game_assets/*_summary.json` / `*_manifest.jsonl` for conversion errors,
- `progress/progress.html` for the current state of every subsystem,
- [`TESTING_EMULATOR.md`](TESTING_EMULATOR.md) for emulator start-up problems (the fixed RPC
  port is the usual cause: only one Azahar at a time).

Never modify `..\3DS_Translate`; it is a read-only reference (the translation
workspace is also the source of the emulator harness).
