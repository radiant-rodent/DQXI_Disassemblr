# T0_progress — human-facing progress tracker

## What I built

`tools/progress.py` (stdlib only, no network, no JavaScript) now generates the whole
`progress/` directory, modelled on AnyPS5's progress page:

| Output | Contents |
|---|---|
| `progress/progress.json` | every raw number plus an ISO timestamp and the local generation time |
| `progress/progress.html` | overview: native code per subsystem, scripts, assets per family, editor checklist, build health, counting-rule notes |
| `progress/progress.svg` | coverage map, one 4×4 cell per native function, grouped in labelled subsystem blocks ordered by address |
| `progress/badge-functions.svg`, `badge-assets.svg`, `badge-editor.svg` | shields-style percentage badges |
| `progress/history.jsonl` | one line per calendar day (last run of a day replaces earlier runs) |
| `progress/history.html` | inline SVG line chart for named % / assets % / editor % plus a table |
| `progress/tasks.html` | live worker board (auto-refresh 30 s) |
| `progress/features.json` | user-editable editor-feature checklist seeded from `orchestration/PLAN.md` |

All pages share a nav bar and are static, readable, and work in light and dark mode. Every
section reads from disk defensively: when a generated tree is missing it shows 0 or
“not generated yet”, and a broken section cannot stop the other sections from being written.

### Counting rules implemented

- **Named**: effective name is not a placeholder (`FUN_`, `func_`, `sub_`, `thunk_`, `LAB_`,
  `maybe_`, `DAT_`, …). A high-confidence proposal in `orchestration/naming/out/*.json` counts
  as named even before `M1_merge_names`.
- **Proposed**: has a proposal but stays provisional (`maybe_` prefix or confidence < 0.5), so it
  colours amber rather than blue.
- **Documented**: a named function with a summary field, a naming-proposal summary ≥ 20 chars, or a
  human comment block in its readable C beyond the export boilerplate. A `maybe_` proposal's
  summary does *not* turn a function green.
- **Matching C**: only functions in `build/replacement_report.json` with `ok: true` (or the last
  `audit/PROJECT_VERIFICATION.json` snapshot). Readable Ghidra C is never counted as matching.
- **Scripts**: CNUT total, decompiled `.nut`, recompile-verified (requires a recompile manifest or
  `*.recompiled.*` output; decompiling is not recompiling).
- **Assets**: source counts from a single walk of `game_data/` when generated, else the documented
  audit baseline; converted counts from `game_assets/` with `audit/ASSET_VERIFICATION.json` as
  fallback; editable is a capability count for the same-size write-back tools.
- **Editor**: checklist weighting, done = 1 / partial = 0.5.
- **Build health**: hashes `build/code.bin` against the retail SHA-256, parses
  `build/replacement_report.json`, `audit/PROJECT_VERIFICATION.json`, optional
  `build/test_report.json` / `audit/TEST_RESULTS.json`, and falls back to
  `audit/FINAL_REPORT.md` for the last documented test run.

### Dispatcher integration

`orchestration/dispatch.py` got three additive changes only (rest untouched):

1. `PROGRESS`, `progress_lock` and `refresh_progress()` (subprocess, 600 s timeout, failures ignored,
   serialised so two workers cannot write `progress/` at the same time).
2. `refresh_progress()` after `state[tid] = "DONE"` and after `state[tid] = "FAILED"`.
3. One `refresh_progress()` at dispatcher startup (skipped for `--dry`).

`run_progress.bat` regenerates and opens `progress\progress.html`. `README.md` has a new
**Progress** section at the top linking all pages.

## Files changed

| File | Change |
|---|---|
| `tools/progress.py` | new generator (~1,000 lines, stdlib only) |
| `progress/features.json` | new default checklist (24 features in 4 groups) |
| `progress/progress.{html,json,svg}` | generated |
| `progress/badge-*.svg` | generated |
| `progress/history.{html,jsonl,svg}` | generated |
| `progress/tasks.html` | generated |
| `orchestration/dispatch.py` | additive progress refresh only |
| `run_progress.bat` | new launcher |
| `README.md` | Progress link section at the top |
| `AGENT_LOG.md` | Entry 39 |

## Test results

Run on 2026-10-25 while `P0_regen` was still regenerating the deleted trees.

- `python tests/run_all.py` → **SUCCESS, 187 / 187 PASS** (Tier 1 70/70, Tier 2 70/70,
  Tier 3 14/14, Tier 4 33/33).
- `python tools/progress.py` → exit 0:
  `progress: native named 2.5% (460/18,787), documented 0.0%, assets 74.9%, editor 50.0%,
  tasks 0/10 done -> progress`
- `python -m py_compile tools/progress.py orchestration/dispatch.py` → OK.
- Synthetic fixture test (temporary tree, not committed) exercised naming/proposal/documentation/
  matching classification and produced the expected 5 → 2 named / 1 proposed / 2 documented /
  1 matching result, plus a non-empty coverage map, history chart and badges.
- `python tools/verify_project.py` → **OVERALL: FAIL**, but only because the generated data was
  mid-regeneration:
  - PASS: code.bin size + exact SHA-256, all asset group counts, decoded maps, editor binary,
    C source replacement (4/4).
  - FAIL: `model texture manifest` (no output), `native index`
    (`decomp/ghidra/functions_index.json` missing), `patch report`
    (`build/PATCH_REPORT.json` missing).
  - This run rewrote `audit/PROJECT_VERIFICATION.json` with that honest FAIL; the progress page now
    shows it as FAIL with the three failing check names. Rerun `verify_project.py` after P0_regen
    finishes.

### Summary numbers in the generated snapshot

| Area | Value |
|---|---|
| Native entry points | 18,787 (18,748 decompiled, 38 covered, 1 unresolved) |
| Named | 460 (2.45%) |
| Naming proposals | 0 (no `orchestration/naming/out/*.json` yet) |
| Documented | 0 |
| Matching C | 4 (InitBss + 3 GetTalkParty wrappers) |
| Scripts | 769 CNUT → 769 readable `.nut` (100%), 8,960 functions; 0 recompile-verified |
| Assets | 25,676 / 34,262 converted (74.9%) at snapshot; complete audit baseline is 28,427 / 34,262 = 83.0% |
| Editor checklist | 50.0% (8 done, 8 partial, 8 todo of 24) |
| Build | bit-match PASS (`code.bin` SHA-256 matches retail); tests 187/187 run now |
| Worker board | 10 tasks; 2 RUNNING, 8 pending at snapshot |

## Open problems / not verified

- `decomp/ghidra` did not exist at snapshot time, so the coverage map shows the explicit
  “no per-function index yet” placeholder. The SVG/HTML code path was tested with a synthetic
  fixture; the real 18,787-cell map was **not** visually inspected yet.
- `verify_project.py` currently fails because P0_regen has not finished; this is a workspace state,
  not a regression from this task. `audit/PROJECT_VERIFICATION.json` was overwritten with that
  snapshot.
- The build-health test card shows “Last documented: 187 / 187 PASS (2026-10-19)”, although the
  suite passed today. There is no machine-readable test report in the repo; `tests/run_all.py`
  only prints to stdout. I did not modify it because it is outside this task's ownership.
- Asset percentages move while P0 writes `game_assets/`; live counts intentionally win over the
  older audit manifest.
- Text is reported as 0 (E2 has not produced readable message files) and tables are 0
  round-trip-editable (no general BXON object-graph writer yet).
- Recompile-verified scripts are 0 because no recompile manifest/output exists.
- The task board derives DONE from `orchestration/done/<id>.md` as well as `state.json`; a stale
  `state.json` entry therefore cannot hide a finished task. It was only tested with the live
  two-task state plus this report, not with a FAILED task.

## Suggested follow-ups

1. After `P0_regen` finishes: rerun `python tools/verify_project.py` and `python tools/progress.py`;
   confirm the real per-subsystem table and 18,787-cell map.
2. Add a small `audit/TEST_RESULTS.json` writer to `tests/run_all.py` (or make `progress.py` read a
   CI artefact) so the test card is fresh instead of “last documented”.
3. After `N_*` naming batches and `M1_merge_names`, verify the proposed/blue/green split and tune the
   documentation heuristic against real merged comments.
4. Update `progress/features.json` statuses as E1/E2/E3/E4/X1/X2/D1 land; add a tiny test for
   `tools/progress.py` (missing-data, empty-history, done-report board).
5. Optional: publish `progress/` to GitHub Pages like AnyPS5; the pages are already static.
