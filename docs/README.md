# Guides

Start with the front door in [`../README.md`](../README.md). This folder is the manual.

## New here?

1. **[Your first mod in 10 minutes](FIRST_MOD.md)** — change an item price and a line of text,
   see them in the emulator, put them on a Luma3DS SD card. Every command and output was run on
   this tree; the guide says what was not.
2. **[Project tour](PROJECT_TOUR.md)** — folder map, the pipeline, which engine subsystem lives
   where, the main loop, scene/state machine, battle flow, script VM bindings, file system and
   rendering, with links into `decomp/readable/`.
3. **[Getting started](GETTING_STARTED.md)** — prerequisites and how to regenerate the extracted
   and converted data trees if they are missing.

## Task guides

| Guide | Use it for |
|---|---|
| [Editing assets](EDITING.md) | The per-family cheat sheet: tables, text, scripts, maps, textures, models, audio, layouts — plus what is *not* possible yet |
| [DQXI Studio](EDITOR.md) | The Rust app: 13 sections, the level editor's data model, Export & Play, hardware settings |
| [Scripts](SCRIPTS.md) | Squirrel CNUT format, the decompiler, the source compiler/assembler and the script index |
| [Assets](ASSETS.md) | Extraction tree, BCH/glTF/OBJ, texture assignment, table schemas, round-trip tools |
| [Native code](CODE.md) | The readable C tree, coverage, how to read a function, the decompiler workflow |
| [Source replacement](SOURCE_REPLACEMENT.md) | The bit-verified C path and how to replace more assembly |
| [Rebuild and patch](REBUILD.md) | Baseline ROM, patched ROM, RomFS hash-tree caveats |
| [Export for hardware](EXPORT.md) | The `mod/` workspace, Luma LayeredFS, rebuilt `.3ds`, installable `.cia`, the real-console checklist |
| [Testing in the emulator](TESTING_EMULATOR.md) | Azahar harness: `tools.emu boot`, `ctl` sessions, saves, crash/hang diagnosis |
| [Audio / OST](AUDIO.md) | Soundtrack filters, durations, catalogs and stream replacement |

## Command style

Run tools from the repository root as modules:

```powershell
python -m tools.export_mod --target luma
python -m tools.table_edit tables
python -m tools.emu info
```

The equivalent `python tools/<tool>.py` form also works from the repository root; the guides use
the `-m` form so the command is unambiguous no matter which directory you start in.

## Status and evidence

- [Progress page](../progress/progress.html) — native coverage per subsystem, assets, editor
  features, build health. Regenerate with `python -m tools.progress`.
- [`../audit/GAP_REPORT.md`](../audit/GAP_REPORT.md) and
  [`../audit/SOURCE_QUALITY.md`](../audit/SOURCE_QUALITY.md) — the skeptical measurements that
  the progress page summarises.
- [`../audit/PROJECT_VERIFICATION.json`](../audit/PROJECT_VERIFICATION.json) — the last
  `python -m tools.verify_project` run, check by check.
- `docs/images/` — the screenshots used in these guides (Studio, emulator proofs, hardware
  checklists). They are captured from real runs, not mock-ups.

## What was verified in this manual (2026-10-26)

Run while writing these pages, in this tree:

- every one of the 150 local Markdown links in `README.md` + `docs/*.md` resolves, and all 17
  text/JSON files re-read as strict UTF-8 (no replacement characters);
- `python -m tools.build --verify` → both code images match retail
  (`dfcd1b7a…c8cc24d8`, `ea3d2c02…08c298a2f`);
- `python -m tools.verify_project` → **OVERALL: PASS** (18 checks);
- `python -m tools.verify` → the rebuilt `build/DQXI.3ds` is
  `0f04b51b…a9b74`, bit-identical to the retail image; `tools.romfs_hash --verify
  original/romfs.bin` → `ok=True` (0 bad blocks at all three levels);
- `python -m tools.table_edit verify` → 42 tables, **235,769 field writes, 0 failures**;
- `python -m tools.text_tool verify` → **792 banks, 68,316 strings, 0 failures**;
- `python -m tools.script_build verify` → assembly **769/769**, unchanged-source reuse
  **769/769**, semantic round-trip **769/769** (from-scratch bytes 0/769, as documented);
- `python -m tools.merge_names --check` → 128 batches, 0 bad entries, 0 unknown addresses;
  `python -m tools.build_c_replacement` → `ALL REPLACEMENTS BIT-MATCH`;
- `python tests/run_all.py` → **223 / 223 PASS** (exit 0) in a fresh full run after the
  resizable-assets lane stopped editing: Tier 1 70/70, Tier 2 70/70, Tier 3 14/14, Tier 4 69/69.
  Two earlier runs this evening hit 222/223, once on `tools/romfs_build.py` (mapping vs pairs) and
  once on a mid-edit `NameError: RomFsIndex`; both were transient failures while
  `X5_resizable_assets` was changing those files, and neither check was weakened or edited here;
- the table and text edits in [FIRST_MOD.md](FIRST_MOD.md) were applied, staged, exported as a
  Luma folder, booted to the title screen in Azahar (`game t=478.8s`, 54.6 s real, exit 0) and the
  emulator log shows `LayeredFS replacement file in use for /syscmn.pack` and `/ui/title.pack`.
  Re-reading the staged PACKs independently: `item.bxon` differs from retail only in the u32 at
  `0x44` (**8 → 5**, same size), and `title_msg.bxon` contains both new UTF-16LE lines.
  [the in-game screenshot](images/first-mod/dialogue.png) shows `FIRST MOD OK!` /
  `The dialogue line is editable.` in a message window;
- `cd viewer_rs; cargo test` → 75 passed, 0 failed, 1 ignored.

Deliberately **not** re-run or not verified here:

- **No physical 3DS/2DS.** Luma install steps and the hardware checklist are documented, but this
  machine has no console. The emulator is a smoke test, not hardware proof.
- The full extraction/conversion pipeline (`extract_game_data --all`, `convert_assets --all`) and
  the Ghidra re-export: the generated trees already existed and were checked by
  `verify_project`, not regenerated end to end.
- `.3ds`/`.cia` rebuilds: the exporter and the historical evidence are documented in
  [EXPORT.md](EXPORT.md); only the Luma target was exercised for the first-mod walkthrough
  (`out/cia/` does not exist on this tree, so the `tools.ctr_cia verify` commands could not be
  re-run).
- `tools/bxon_patch.py` (raw-offset patching, not used by the walkthrough) prints a Unicode arrow
  in its description and therefore crashes on this machine's cp1252 console unless
  `PYTHONIOENCODING=utf-8` is set; [EXPORT.md](EXPORT.md#2-first-mod-in-five-minutes-one-table-value)
  now sets it. The raw-offset example was re-run: offset `0x44` (not `0x18`, which is the row
  offset) writes the herb price and leaves the file at 516,912 bytes.
- Claims marked `maybe_` in `symbols.json`, and all struct field offsets, remain static-analysis
  hypotheses.

## House rules for contributors

- `original/` and `game_data/` are read-only; work in `game_assets/`, `editor_projects/`, `mod/`.
- `python -m tools.build` must keep reassembling the retail `code.bin` with zero differences.
- Anything exported must stay valid for the original engine and run on a real 3DS/2DS: no
  emulator-only formats, ARMv6K/VFPv2 only in code patches, Old-3DS memory limits.
- Write text/JSON as UTF-8. One cp1252 byte makes a whole batch unreadable.
