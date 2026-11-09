# P1_progress_types — show globals, classes and locals on the progress overview

## Summary

`tools/progress.py` and the generated `progress/` pages now track Phase 2 type-recovery progress across global variables (`G_*`), classes and struct fields (`S_*`), and local variables (`V_*`) at every stage of the pipeline:

1. **Inputs to recover**: `orchestration/types/{globals,structs,locals}.json` (falling back to `orchestration/types/batches/{G,S,V}_*.json` and `merged/report.json` when evidence DBs are absent) plus batch completion counts (`done / total` per kind, where `done` means `orchestration/done/<id>.md` exists).
2. **Live worker answers**: `orchestration/types/out/{G,S,V}_*.json`, classified with the same rule as native functions:
   - **`named`**: non-empty identifier without a `maybe_` prefix, not an `unknown*` / raw decompiler placeholder, and `confidence >= 0.5`.
   - **`guessed`**: `maybe_`-prefixed identifier (or `maybe_` class C type) or `confidence < 0.5`.
   - **`answered`**: all worker entries for unique targets (including honest `unknown` / `unknown_*` entries at confidence `0.0`, which count in `answered` without inflating `named` or `guessed`).
3. **Merged into headers & maps**: `orchestration/types/merged/{globals,fields,locals}.json` (falling back to `include/dqxi/{globals,structs}.h`), reported separately from live worker answers so `tools/typedb/apply.py --validate` runs (which rewrite `merged/report.json` without updating headers/maps) never falsely inflate `merged`.
4. **Defensive parsing**: missing, truncated, invalid-UTF-8, wrong-root-shape, or non-object-entry JSON files are counted in `types.malformed_files` / `types.malformed` and skipped without raising, so `dispatch.py`'s post-task refresh cannot silently freeze the progress page.

---

## Resumed Task Audit

A previous worker (`a1e9e314`) implemented `collect_types()`, the side-by-side overview cards, `badge-types.svg`, the history series, and `tests/test_progress.py`, then hit the session step limit before running full project verification or writing `AGENT_LOG.md` and this done report. All existing changes were audited against `tools/typedb/{inventory,struct_db,make_batches,apply}.py` and real files in `orchestration/types/`:

- Verified `structs.json`, `globals.json`, `locals.json`, `batches/`, `out/G_*.json`, `merged/*.json`, and `include/dqxi/*.h` schemas against `collect_types()`.
- Tightened `collect_types()` so non-object elements inside `out/*.json` entry lists (or `fields` lists) also record the file in `malformed_files` while still recovering valid sibling entries.
- Extended `tests/test_progress.py` to test non-object array entries and strict UTF-8 decoding of all generated `progress/*` files.
- Regenerated `progress/` and ran unit tests, `python tools/verify_project.py`, and `python tests/run_all.py`.

---

## Live Numbers in `progress/progress.json` & `progress/progress.html`

Generated on `2026-10-30 18:20` (`source: "orchestration/types + include/dqxi"`, `malformed_files: 0`, last validation report `errors: 1, warnings: 0`):

| Kind | Batch prefix | Total | Answered | Named (&ge;0.5) | Guessed (`maybe_`) | Merged (`include/dqxi` / `merged/`) | % Named | Batches (`done / total`) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **Globals** | `G_*` | 4,490 | 1,410 | 1,240 | 170 | 623 | 27.62% | 22 / 58 |
| **Classes** | `S_*` | 1,649 | 0 | 0 | 0 | 0 | 0.00% | 0 / 151 |
| **Struct fields** | `S_*` | 26,097 | 0 | 0 | 0 | 0 | 0.00% | 0 / 151 |
| **Locals** | `V_*` | 116,237 | 0 | 0 | 0 | 0 | 0.00% | 0 / 132 |
| **Total** | `G/S/V` | **148,473** | **1,410** | **1,240** | **170** | **623** | **0.84%** | **22 / 341** |

- **Badge (`progress/badge-types.svg`)**: `data & types | 0.8% (22/341)` (green `#15803d`, linked in the overview badge row right next to `badge-functions.svg`).
- **History (`progress/history.jsonl`, `progress/history.svg`, `progress/history.html`)**: `2026-10-30` records `types_named_pct: 0.84` (`types_globals_pct: 27.62`, `types_named: 1240`, `types_guessed: 170`, `types_merged: 623`, `types_total: 148473`, `types_batches_done: 22`, `types_batches_total: 341`). Earlier entries (`2026-10-25`, `2026-10-26`, `2026-10-27`) remain untouched and plot cleanly at `0.0%`.

---

## Native Functions Numbers — Before vs After

`collect_native()` was not altered. Comparing `progress/progress.json` before `P1_progress_types` vs after regeneration:

| Metric | Before edit | After edit | Delta |
|---|---:|---:|---:|
| `native.total` (entry points) | 18,787 | 18,787 | 0 |
| `native.decompiled` | 18,748 | 18,748 | 0 |
| `native.covered_by_container` | 38 | 38 | 0 |
| `native.unresolved` | 1 | 1 | 0 |
| `native.named` | 11,486 (61.14%) | 11,486 (61.14%) | 0 |
| `native.proposed` | 7,301 | 7,301 | 0 |
| `native.documented` | 11,068 (58.91%) | 11,068 (58.91%) | 0 |
| `native.matching_c` | 4 (0.02%) | 4 (0.02%) | 0 |
| `native.proposals` (`addresses / high_conf / batches`) | 18,327 / 8,024 / 128 | 18,327 / 8,024 / 128 | 0 |
| Per-subsystem totals (all 12 domains) | 18,787 total / 11,486 named | 18,787 total / 11,486 named | 0 |

### Runtime

- `collect_types()` runs in **~0.99 s** (parsing `structs.json` [26 MB], `globals.json` [3.4 MB], `locals.json` [53 MB], 22 `out/G_*.json` files, and `merged/*.json`).
- Full `python tools/progress.py` completes in **13.98–14.20 s** wall-clock (dominated by `collect_assets()` walking `game_data/` + `game_assets/` in ~8.56 s and `collect_tasks()` in ~1.81 s), keeping post-task refresh time essentially unchanged (~7% overhead).

---

## Decisions Recorded

1. **`classes.total = 1,649` (classes with field evidence)**: `structs.json` lists 1,930 candidate classes, of which 281 are empty namespace-only groupings that receive no `S_*` batch. Using `1,649` matches `make_batches.py` and `apply.py`'s `inputs.classes_with_fields` so 100% completion of all 151 `S_*` batches can reach 100% of `classes.total`.
2. **`locals.total = 116,237` (placeholder tokens)**: `locals.json` records 170,492 total declarations across 18,737 functions, of which 54,255 are `self` or already-named M1 signature parameters and 116,237 (`stats.variables_placeholder`) are the Ghidra placeholder tokens (`iVar2`, `local_44`, `uStack_10`, `argN`) that `V_*` workers actually rename.
3. **`merged` reads actual maps/headers, not `report.json`**: `G_*` workers routinely run `python tools/typedb/apply.py --validate`, which overwrites `orchestration/types/merged/report.json` (`merged.globals: 1409`) without writing `merged/globals.json` or `include/dqxi/globals.h` (`623`). Counting `merged/{globals,fields,locals}.json` (with fallback to `include/dqxi/{globals,structs}.h`) keeps "merged into headers" strictly separate from "answered by a worker".
4. **Backwards-compatible keys retained**: `types` in `progress.json` includes the new nested `globals`, `classes`, `fields`, `locals`, and `batches` objects while preserving legacy flat keys (`globals_total`, `globals_named`, `pct_globals`, etc.) so any external reader of the earlier S0 table continues to work.

---

## Files Changed

| Path | Change |
|---|---|
| `tools/progress.py` | Added full `collect_types()`, `types_fallback()`, `stacked_bar_html()`, side-by-side `#functions-card` + `#data-types-card` overview cards, upgraded `#types` table, `badge-types.svg`, and `types_named_pct` history series with right-label collision avoidance |
| `tests/test_progress.py` | Created 5-test unit suite (`ProgressTypesTests`) covering fake G/S/V + malformed types tree, header fallback + deduplication, binary/corrupt/non-object tolerance, overview HTML + badge + legacy history preservation, and live `progress/` schema & strict UTF-8 |
| `progress/progress.json` | Regenerated with full `types` block |
| `progress/progress.html` | Regenerated with "Native functions" and "Data & types" overview cards, `badge-types.svg`, and updated `#types` table |
| `progress/badge-types.svg` | Generated (`data & types: 0.8% (22/341)`) |
| `progress/history.jsonl`, `progress/history.svg`, `progress/history.html` | Updated with `data & types` trend line and table column |
| `progress/map.html`, `progress/progress.svg`, `progress/tasks.html`, `progress/badge-{functions,assets,editor}.svg` | Regenerated by `tools/progress.py` |
| `AGENT_LOG.md` | Appended Entry 224 (`agent_id: P1_progress_types`) |
| `orchestration/done/P1_progress_types.md` | This completion report |

---

## Test & Verification Results

1. **`python tools/progress.py`**:
   ```text
   progress: native named 61.1% (11,486/18,787), documented 58.9%, assets 85.5%, editor 93.8%, types 0.84% (globals 27.6%, classes 0.0%, fields 0.0%, locals 0.0%, batches 22/341), tasks 225/579 done -> .\progress
   ```
2. **`python -m unittest discover -s tests -k progress -v`** (7/7 PASS in `0.775s`):
   - `test_empty_and_corrupt_binary_files_never_crash` — `ok`
   - `test_fake_types_tree_counts_and_malformed_tolerance` — `ok`
   - `test_header_fallback_and_answer_deduplication` — `ok`
   - `test_live_progress_json_and_badge_on_disk` — `ok`
   - `test_overview_html_badge_and_history_preserve_old_entries` — `ok`
   - `test_scenario_4_diff_tool_automated_verification` — `ok`
   - `test_scenario_4_init_bss_exact_bytecode_equivalence` — `ok`
3. **`python tools/verify_project.py`**:
   - **18 / 18 checks PASS** (`OVERALL: PASS -> audit/PROJECT_VERIFICATION.json`), including `code.bin size` (`7,090,176` bytes), `code.bin hash` (`dfcd1b7ad170eab3932abfaa702b694e6673dc0a8744bfc070765cc8c8cc24d8`), all asset families, `native entry points` (`18,787`), `native decompiled` (`18,748`), `decoded maps` (`1,196`), `editor binary`, and `C source replacement` (`4/4`).
4. **`python tests/run_all.py`**:
   ```text
   Tier 1: Feature Coverage           | 70  | 70  | 0 | 0 | 2.32   | PASS
   Tier 2: Boundary & Corner Cases    | 70  | 70  | 0 | 0 | 6.97   | PASS
   Tier 3: Pairwise Combinations      | 14  | 14  | 0 | 0 | 1.16   | PASS
   Tier 4: Real-World Scenarios       | 69  | 69  | 0 | 0 | 167.32 | PASS
   Tier 5: Challenger                 | 40  | 40  | 0 | 0 | 35.47  | PASS
   Tool unit tests (tests/test_*.py)  | 121 | 120 | 1 | 0 | 138.33 | PASS
   TOTALS                             | 384 | 383 | 1 | 0 | 351.57 | SUCCESS (Exit Code 0)
   ```
5. **Strict UTF-8 decode**: verified across `tools/progress.py`, `tests/test_progress.py`, `AGENT_LOG.md`, `orchestration/done/P1_progress_types.md`, and generated `progress/*` files.

---

## BLOCKED (minor environment tool missing)

- **`pytest` is not installed on this machine**: running `python -m pytest tests -q -k progress` fails with `No module named pytest` on the sole installed Python (`%LOCALAPPDATA%\Programs\Python\Python312\python.exe`; searched `C:\`, `C:\Program Files`, `%USERPROFILE%`, `%LOCALAPPDATA%`, and `%APPDATA%` per Rule 4, and did not install packages per Rules 3 & 4).
- `tests/test_progress.py` is implemented with standard-library `unittest.TestCase`, so `python -m unittest discover -s tests -k progress -v` runs and passes all 7 `-k progress` tests today, and `python -m pytest tests -q -k progress` will discover and run the exact same tests without changes if `pytest` is installed on the host later.

---

## Open Problems & What Is NOT Verified

- **Live `S_*` and `V_*` worker outputs**: 0 of 151 `S_*` batches and 0 of 132 `V_*` batches have produced `orchestration/types/out/{S,V}_*.json` on disk yet; their parsing and counting paths are verified via synthetic fixtures modeled on `orchestration/types/samples/demo_{S,V}.json` and `tools/typedb/apply.py`, not yet on real worker batches.
- **Visual browser rendering**: `progress/progress.html`, `progress/badge-types.svg`, and `progress/history.html` were verified structurally and via HTML/SVG assertions, not opened in a GUI browser window.
- **`tests/run_all.py` module list**: `tests/run_all.py` hardcodes its `--tier tools` module list (`tests.test_asset_replace`, etc.) and is outside this task's file ownership, so `tests.test_progress` is run via `unittest discover -s tests -k progress` (or `pytest -k progress`) rather than inside `run_all.py`.

---

## Suggested Follow-up Tasks

1. **Register `tests.test_progress` in `tests/run_all.py`**: add `"tests.test_progress"` to `TIERS[5]["modules"]` in a task that owns `tests/run_all.py` so every full E2E run guards `tools/progress.py`.
2. **Resolve duplicate global name in `G_020`**: `orchestration/types/merged/report.json` currently flags 1 validation error (`G_020` `0x007602B4` duplicate global name `g_fsChannelTableVtable`, also at `0x0078295C`) for `M2_types_merge` to disambiguate before merging all completed `G_*` batches.
