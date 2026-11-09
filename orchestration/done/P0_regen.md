# P0_regen — regenerate every generated output

**Status:** complete and verified (2026-10-25)
**Agent:** `P0_regen`
**Scope:** `original/`, `asm/`, `build/`, `decomp/`, `game_data/`, `game_assets/`, `audit/`,
`orchestration/naming/`, plus new `tools/regen_all.ps1` and `tools/make_naming_batches.py`.

Nothing in `..\3DS_Translate` was modified; the retail ROM is only read. No
software was installed or downloaded. Every tool needed (Ghidra 12.1.4, JDK 21, .NET 9,
ARM GCC, Rust/cargo) was already on disk.

## Result

All previously missing generated trees were rebuilt from `..\3DS_Translate\DQXI.3ds`
and the pipeline was exercised end to end, including the bit-matching rebuild and the patched-ROM
path. The final one-shot verifier passes:

```
[PASS] code.bin size: 7090176 bytes
[PASS] code.bin hash: dfcd1b7ad170eab3932abfaa702b694e6673dc0a8744bfc070765cc8c8cc24d8
[PASS] asset verification: audit/ASSET_VERIFICATION.json
[PASS] assets textures: {'files': 3486, 'expected': 3486, 'checked': 150, 'errors': 0}
[PASS] assets layouts: {'files': 7232, 'expected': 7232, 'checked': 150, 'errors': 0}
[PASS] assets models: {'files': 4779, 'expected': 4779, 'checked': 150, 'errors': 0}
[PASS] assets scripts: {'files': 769, 'expected': 769, 'checked': 150, 'errors': 0}
[PASS] assets tables: {'files': 5929, 'expected': 5929, 'checked': 150, 'errors': 0}
[PASS] assets audio: {'files': 5877, 'expected': 5877, 'checked': 150, 'errors': 0}
[PASS] assets maps: {'files': 1196, 'expected': 1196, 'checked': 150, 'errors': 0}
[PASS] model texture manifest: models=4779 manifest=10542 unexpected_models=0 missing_files=0 no_source=0
[PASS] native entry points: 18787
[PASS] native decompiled: 18748
[PASS] decoded maps: 1196
[PASS] patch report: build\DQXI_patched.3ds
[PASS] patched ROM exists: build\DQXI_patched.3ds
[PASS] editor binary: .\viewer_rs\target\release\viewer_rs.exe
[PASS] C source replacement: [ … 4 entries, all "ok": True … ]
[PASS] build/DQXI.3ds: 0f04b51bc6dc145106fb7bc957fa41991cd02d89e0af2c8775db9d12a37a9b74
[PASS] build/DQXI_patched.3ds: 0bdbb7bb07cc8a5eb8043e8e2a9d1953746cd79923755721f4062f90df1ee740

OVERALL: PASS -> audit/PROJECT_VERIFICATION.json
```

(Only the long C-replacement JSON line is elided; the full run is in
`orchestration/logs/P0_verify_project.log`.)

## What was regenerated

| Tree / artifact | Command | Result |
|---|---|---|
| `original/` containers | `python tools/extract_rom.py` then `python tools/verify.py` | 16/16 PASS, `romfs.bin` 2,679,185,408 B |
| `asm/` | `python tools/disasm.py` | 25 text + 4 rodata + 3 data slices + start/init/bss (35 files) |
| `build/code.bin` | `python tools/build.py` | 7,090,176 B, SHA-256 `dfcd1b7a…` — bit-match |
| `build/code.compressed.bin` | `python tools/build.py` | 3,920,924 B, SHA-256 `ea3d2c02…` — bit-match |
| C replacements | `python tools/build_c_replacement.py` | 4/4 exact (`InitBss`, 3 × `GetTalkParty*`) |
| full retail image | `python tools/recompile_game.py` | 4,294,967,296 B, SHA-256 `0f04b51b…` — bit-match |
| Ghidra project | `analyzeHeadless … -import …` | analysis succeeded (347 s) |
| `decomp/ghidra/functions/` | `ExportDQXI.java` | 18,159 `.c`; 628 initial missing entry points |
| `decomp/ghidra/recovered/` | `DiagnoseMissing.java` | 38 covered, 589 recovered, 1 failed (`0x003D7BC8`) |
| `decomp/ghidra/` index + views | `python tools/organize_ghidra.py` | 18,787 discovered / 18,748 decompiled / 38 covered / 1 unrecovered |
| native names | `python tools/recover_native_names.py` | 454 binding names, 79 renames, 460 named total |
| `decomp/readable/` | `python tools/readable_c.py` | 18,748 readable `.c` (functions + recovered) |
| legacy `decomp/functions/` | `python tools/decompile_native.py` | 18,787 files + `decomp/functions_index.json` |
| RomFS + PACK/PACA | `python tools/extract_game_data.py --all` | 21,250 RomFS files, 13,469 packs, 21,273 members, 0 errors |
| SARC archives | `python tools/extract_arcs.py` | 398 archives, 10,718 members (3,486 bflim / 4,394 bflyt / 2,838 bflan) |
| maps | `python tools/map_tool.py export --all` | 1,196 scenes, 5,022 candidate objects |
| SPICA manifests | `SpicaRef.exe materials` / `skin` | 10,542/10,542 ok, 0 failed; 3,505 skins need bone placement |
| textures | `convert_assets.py --textures` | 3,486 PNG, 0 errors |
| layouts | `convert_assets.py --layouts` | 7,232 JSON, 0 errors |
| scripts | `convert_assets.py --scripts` + `squirrel_decompile.py --all` | 769 listings + 769 `.decompiled.nut`; 8,960/8,960 functions structured, 0 fallbacks |
| tables | `convert_assets.py --tables` | 5,929 JSON, 0 errors |
| models | `convert_assets.py --models` | 4,779 glTF + 4,779 OBJ, 0 errors (471 s) |
| audio | `convert_assets.py --audio` | 5,877 WAV, 0 errors (1,105 s) |
| audio catalogue | `python tools/audio_catalog.py` | 155 BGM, 37 jingles, `AUDIO_CATALOG.md` + `ost.json` |
| model/area names | `python tools/build_model_names.py` | 1,711 name stems, 113 areas |
| face expressions | `python tools/face_expressions.py scan` | 2,855 animations in 155 motion files, 185 poses |
| audits | `audit_project.py --packs`, `verify_assets.py`, `verify_model_textures.py` | all pass (see below) |
| editor binary | `cargo build --release --offline` | `viewer_rs/target/release/viewer_rs.exe` |
| naming batches | `python tools/make_naming_batches.py --batch-size 150` | 128 batches / 18,327 unnamed functions + 128 task files |

### Asset verification (exact counts, not just minima)

```
textures   files=  3486 expected=3486 checked= 150 errors=0
layouts    files=  7232 expected=7232 checked= 150 errors=0
models     files=  4779 expected=4779 checked= 150 errors=0
scripts    files=   769 expected= 769 checked= 150 errors=0
tables     files=  5929 expected=5929 checked= 150 errors=0
audio      files=  5877 expected=5877 checked= 150 errors=0
maps       files=  1196 expected=1196 checked= 150 errors=0
OK=True  ->  audit/ASSET_VERIFICATION.json
```

Model texture reconciliation: `models=4779 manifest=10542 unexpected_models=0 missing_files=0 no_source=0`.

## Tests

| Check | Command | Result |
|---|---|---|
| E2E tiers | `python tests/run_all.py` | **187/187 PASS** (70 + 70 + 14 + 33), exit 0 |
| Asset round-trip | `python -m unittest tests.test_asset_roundtrip -v` | **38 tests OK** (1 skipped) |
| Project verification | `python tools/verify_project.py --hash-rom` | **OVERALL PASS**, both 4 GiB hashes |
| Editor unit tests | `cargo test --offline --manifest-path viewer_rs/Cargo.toml` | **23 passed**, 1 ignored, 0 failed |
| Asset verification | `python tools/verify_assets.py` | `OK=True` |
| Model textures | `python tools/verify_model_textures.py` | `OK -> audit/MODEL_TEXTURE_VERIFICATION.json` |
| Pack audit | `python tools/audit_project.py --packs` | 13,469 packs, 21,273 members, 0 errors |

```
Tier 1: Feature Coverage           | 70    | 70    | 0     | 0     | 7.65     | PASS
Tier 2: Boundary & Corner Cases    | 70    | 70    | 0     | 0     | 7.68     | PASS
Tier 3: Pairwise Combinations      | 14    | 14    | 0     | 0     | 1.73     | PASS
Tier 4: Real-World Scenarios       | 33    | 33    | 0     | 0     | 15.97    | PASS
TOTALS                             | 187   | 187   | 0     | 0     | 33.02    | SUCCESS
ALL TEST TIERS COMPLETED SUCCESSFULLY (Exit Code 0)
```

### Patched-ROM smoke test

`python tools/map_tool.py patch editor_projects/b001_101a.json` then
`python tools/patch_game.py --map b001_101a`:

- `build/DQXI_patched.3ds`, 4,294,967,296 B,
  SHA-256 `0bdbb7bb07cc8a5eb8043e8e2a9d1953746cd79923755721f4062f90df1ee740`
- Patched PACK 24,960 B at RomFS `0x55E65C60` (ROM-absolute `0x5629DC60`), no relocation
- IVFC rebuilt and verified: 648,986 data / 5,071 level-1 / 40 master blocks, zero bad hashes
- Two runs with the same input produce the same hash (deterministic)

## New / changed tools

- **`tools/regen_all.ps1` (new):** one documented command order for the whole pipeline, with
  `-Jobs`, `-SkipPacks`, `-SkipGhidra`, `-SkipAssets`, `-FullTextureAudit`. Syntax-checked with the
  PowerShell parser. It builds seeds before the Ghidra import, runs the readable pass after the
  name recovery, restores the checked-in smoke edit after the round-trip test (that test rewrites
  `level3d.patched.bxon`), then runs every verifier.
- **`tools/make_naming_batches.py` (new):** discovers the same 18,787 entry points as
  `disasm.py`/Ghidra, writes `decomp/function_seed.tsv`, propagates subsystem labels through the
  readable-C call graph, and writes `orchestration/naming/batches/N_###.txt`,
  `orchestration/tasks/N_###.md` and `batches/index.json`. Batch paths resolve to the readable
  view, the raw Ghidra file, or the container function when Ghidra merged an entry point.
- `tools/face_expressions.py`: fixed a real crash (`KeyError: 'material'`) caused by mesh-visibility
  animation tracks; the scan now skips `kind == "visibility"` and uses `e.get("material")`.
- `tools/readable_c.py`: also mirrors `decomp/ghidra/recovered/`, so all 18,748 decompiled functions
  have a readable view (previously only 18,159).
- `tools/organize_ghidra.py`: retries the Windows `rmtree` of `by_subsystem` (one run failed with
  `WinError 145`, the retry succeeded).

## Decisions / deviations

- `asm/` was not in the original owns list but is required by `tools/build.py`; regenerated with
  `tools/disasm.py`.
- `decomp/function_seed.tsv` was missing and required by `ExportDQXI.java`; generated from the
  prologue scan (`--seeds-only`/`--dry-run`/`--batch-size` modes in the new tool).
- Seed names come from `symbols_recovered.json`, then `symbols.json` (`function`/`thunk`), then the
  Ghidra index, else `FUN_<addr>`.
- The legacy curated views (`game_scripts/`, `game_tables/`, `game_textures/` and their organizers)
  were **not** regenerated: README calls them legacy and those organizers write outside the owned
  trees. `game_assets/` is the canonical library.
- `viewer_rs` was built offline (`cargo build --release --offline`); no source changes were made.
- The prebuilt `SpicaRef.exe` was used instead of `dotnet build` (avoids restore/download).
- The script was assembled from the commands that were actually run in this order; it was **not**
  executed as one uninterrupted invocation (a full cold run takes roughly 1.5–2 h).

## Open problems / honest caveats

1. **Documented patched-ROM hash is stale.** `README.md`, `audit/FINAL_REPORT.md` and AGENT_LOG
   Entry 11 quote `97712a2d…e5088f` from 2026-10-19; the regenerated image is `0bdbb7bb…`. This is
   not a broken rebuild: rebuilding the retail RomFS hash tree is byte-identical (verified on a copy
   of `original/romfs.bin`), an unmodified PACK rebuild is byte-identical, and the patched image
   verifies with zero bad IVFC hashes. `pack.py`, `romfs_hash.py`, `patch_game.py` and
   `repack_rom.py` were revised on 2026-10-22, after the quoted hash was recorded, so the drift is
   in the recorded smoke-edit input/tool state, not in the current pipeline. The README/FINAL_REPORT
   values were **not** edited (not owned by this task).
2. **No emulator or real-hardware boot test** was performed. Validity is proven by shape checks,
   bit-matching rebuilds, PACK/BXON round-trips and IVFC verification, not by running the game.
3. **`tests.test_asset_roundtrip` has a side effect:** it overwrites
   `game_assets/maps/b001_101a/level3d.patched.bxon` with its own one-float sample. The artifact was
   restored afterwards and `regen_all.ps1` now does that automatically; a cleaner fix would make the
   test write to a temp directory.
4. **Subsystem labels are heuristic.** `make_naming_batches.py` propagates labels through the call
   graph; the resulting split (e.g. `Camera` 6,151, `Unknown` 448) is a work-queue grouping, not a
   semantic claim. Workers must judge each function from its code.
5. **`regen_all.ps1` needs a prior NuGet restore** for `tools/spica_ref` if the prebuilt binary is
   absent (`dotnet build --no-restore`). On this machine the binary and `obj/project.assets.json`
   already existed.
6. `original/` contains the retail partitions (12 GB total); `build/` contains two 4 GiB images.
   Re-running the script needs that free disk space.
7. `audit/pack_members.jsonl` and `game_assets/*_manifest.jsonl` are large by design; the human
   summaries are `audit/pack_summary.json`, `audit/ASSET_VERIFICATION.json` and
   `game_assets/*_summary.json`.

## Suggested follow-ups

1. Refresh the patched-ROM hash (or regenerate the smoke-edit artifact referenced by the text) in
   `README.md` and `audit/FINAL_REPORT.md`, and note the tool revision that changed it.
2. Make `tests.test_asset_roundtrip` write its BXON to a temporary directory so tests never modify
   the asset tree.
3. Run `tools/regen_all.ps1` once on a clean checkout to validate the script as a single invocation
   (the individual steps are all known good here).
4. Boot the patched ROM once in an emulator and on hardware for the smoke edit; nothing in this
   task can substitute for that.
5. Add the `recovered/` tree to any viewer search paths if the editor currently lists only
   `decomp/readable/functions/`.

## Resumed verification and follow-up fixes (2026-10-25 13:15 local)

The task was resumed after the first completion pass. I re-checked every generated count and
found three issues that the first pass had not covered; all are fixed and verified:

1. **`audit/GAP_REPORT.md` was misleading, not merely skeptical.** `tools/audit_project.py`
   still inventoried the legacy `game_models/`, `game_textures/`, ... folders (empty by design)
   and read `pack_summary.json["member_extensions"]`, while the file writes `"by_extension"`.
   The report therefore claimed 0 glTF / 0 JSON / 0 WAV and 0 `by_subsystem` files. It now
   inventories `decomp/ghidra/*`, `decomp/readable` and `game_assets/*`, accepts the historical
   key name, and excludes `*.decompiled.nut` from the CNUT conversion ratio (that made it read
   200%). Current GAP_REPORT: 18,748 `by_subsystem`, BCH 4,779/10,542 = 45.3%, BXON 5,929/5,929,
   CNUT 769/769, BCSTM 5,877/5,877.
2. **Name recovery was not persistent.** `tools/recover_native_names.py` rewrote only
   `functions_merged.jsonl`; a later `organize_ghidra.py` rebuilt it from `functions.jsonl` and
   silently dropped the 79 recovered names (observed as 18,406 unnamed after a concurrent
   re-organise). The tool now writes the names back to `functions.jsonl` too, and
   `tools/regen_all.ps1` runs `organize_ghidra.py` a second time so `by_subsystem/` filenames use
   the real names. Final state is stable at **460 named / 18,327 unnamed / 18,787 entries**.
3. **The naming batches were revalidated line by line:** 128 files, 18,327 unique addresses =
   every unnamed function exactly once, 0 missing readable paths (28 covered/unrecovered entry
   points correctly point at `decomp/ghidra/functions_index.json` instead of a non-existent
   `.c`), 128 task files with `{{BATCH}}` substituted. `decomp/function_seed.tsv` has 18,787
   rows / 460 named.

Re-run evidence after those fixes:

| Check | Result |
|---|---|
| `python tools/build_c_replacement.py` | 4/4 exact |
| `python tools/build.py` | `code.bin` + `code.compressed.bin` bit-match (0 differences) |
| `python tools/recompile_game.py` | 4 GiB image `0f04b51b…` bit-match, 16/16 containers |
| `python tools/verify.py` | 16/16 PASS |
| `python tests/run_all.py` | **187/187 PASS** |
| `cargo test --offline` | 23 passed, 1 ignored |
| `python tools/verify_project.py --hash-rom` | **OVERALL PASS**; patched ROM `0bdbb7bb07cc8a5eb8043e8e2a9d1953746cd79923755721f4062f90df1ee740` |
| `python tools/face_expressions.py scan` | 2,855 animations / 155 files / 185 poses |
| `python tools/audit_project.py --packs` | 13,469 packs / 21,273 members / 0 errors |
| `python tools/readable_c.py` | 18,748 readable `.c` (18,159 + 589 recovered) |

Still not verified (unchanged): no emulator or hardware boot of the patched image, no visual QA
of converted models, and `tools/regen_all.ps1` was exercised step by step rather than as one
cold ~2 h invocation. The stale README/FINAL_REPORT patched-ROM hash (`97712a2d…`) remains a
documentation follow-up (not this task's file ownership).
