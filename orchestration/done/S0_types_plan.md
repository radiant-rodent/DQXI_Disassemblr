# S0_types_plan - types, struct fields, globals and local variables (pipeline + batches)

## What this task delivered

Readability pass 2 is now a complete, re-runnable pipeline: evidence extraction from the retail
executable, worker batch generation, validation/merge of worker answers, real C headers, and the
readable-C view that prints `unit->targetUnit` / `g_titleState` / named locals. No names were
invented; every class, field, global and token in an output is tied to an access, an address or a
declaration in `structs.json` / `globals.json` / `locals.json`.

The package is **`tools/typedb/`**, not `tools/types/`. A concurrent worker on this same task
renamed the in-progress package to `typedb` while this session was running (the directory
`tools/types/` was deleted/recreated twice under me). `tools/typedb/` is the surviving, consistent
name: all 341 generated task files, `M2_types_merge.md`, `M3_vars_merge.md`,
`orchestration/types/README.md` and the Python imports use it. I adopted it and did not leave two
harnesses behind. This is a deliberate, documented deviation from the task wording.

## Files

**New/owned pipeline**

| File | Purpose |
|---|---|
| `tools/typedb/common.py` | shared paths, section map, name/subsystem helpers, UTF-8 JSON; added `readable_index()` because `functions_merged.jsonl` still stores pre-M1 file names (`FUN_...`) while the readable tree is renamed |
| `tools/typedb/struct_db.py` | class/field/vtable/ctor/allocation evidence -> `orchestration/types/structs.json` |
| `tools/typedb/inventory.py` | global addresses (resolves each Ghidra literal-pool slot to the real data object) + per-function variables/params -> `globals.json`, `locals.json` |
| `tools/typedb/make_batches.py` | S/G/V manifests and task files; fixed the `{batch}` escaping bug that had left a literal `{batch}` in all 341 task files |
| `tools/typedb/apply.py` | **new**: validate + merge S/G/V answers into `include/dqxi/*.h` and `orchestration/types/merged/*.json`; `--demo` merges the hand-written sample only |
| `tools/readable_c.py` | loads the merged maps; nested field chains via pointed-to class, global names, number-literal rendering, V-map renames, `self` retyping; auto-loads maps so `merge_names.py` (M3) benefits without changes |
| `include/dqxi/{dqxi_base,structs,globals,dqxi_types}.h` + `README.md` | real C structs with byte offsets/padding, extern globals, umbrella header |
| `orchestration/types/{structs,globals,locals}.json` | evidence databases |
| `orchestration/types/batches/{S,G,V}_###.json` | 341 worker manifests |
| `orchestration/types/out/` | worker answers (live; G_001.. in progress at report time) |
| `orchestration/types/samples/{demo_S,demo_G,demo_V}.json`, `BEFORE_AFTER.md` | the hand-applied sample used for the before/after proof |
| `orchestration/tasks/{S_###,G_###,V_###}.md` (341), `M2_types_merge.md`, `M3_vars_merge.md` | worker briefs + merge tasks |
| `orchestration/types/README.md` | one-page pipeline documentation |
| `tools/progress.py` | contains the requested "Types and names" table (structs %, fields %, globals %, locals %); the peer worker completed this part, I verified it runs and reports the expected rows |

`orchestration/types/merged_demo/` is the sample-only merge (1 class, 2 fields, 2 globals, 3
locals). `decomp/readable/` was **not** regenerated with the demo: the real tree stays at M1
quality until M2/M3 run on real answers.

## Numbers (2026-10-26, full run)

| Item | Count |
|---|---:|
| candidate classes | **1,930** (1,649 with field evidence, 281 name-only namespaces) |
| field accesses clustered | **26,097** (21,914 x 4 B, 3,427 x 1 B, 727 x 2 B, 29 x 8 B) |
| classes with a vtable / a base class | 488 / 446 |
| resolved globals | **4,490** (rodata 2,470, data 1,637, bss 383) |
| functions with variable evidence | **18,737** |
| variables (params + locals) | **170,492**, of which 116,237 are still Ghidra placeholders |
| batches generated | **151 S**, **58 G**, **132 V** |
| task files generated | 341 + 2 merge tasks |
| globals already merged from live G answers | **623 / 4,490 = 13.9%** (G workers still running; M2 re-merges) |
| G batch size | mean 77, max 300 (see decision 2) |

S batches are balanced at <=15 related classes and <=420 fields; a single 532-field class
(`Field_SceneObject`) gets its own batch so two workers cannot disagree about one layout.

## Verification

* `python tools/typedb/apply.py --validate` on the live G answers: latest run **623 globals merged**
  (13.88% of 4,490), **0 errors / 0 warnings**. The first run exposed two real pipeline issues,
  both fixed rather than suppressed: (a) 133 false rejections of the legal low-confidence spelling
  `maybe_g_...` (the prefix rule now accepts both `g_` and `maybe_g_`), and (b) one genuine
  duplicate name (`g_actorActionVtable` claimed by two addresses) which the G worker has since
  resolved. Validation also correctly rejected a synthetic bad file (offset 9999 beyond the class,
  field named `self`, unknown class, unknown type).
* `python tools/typedb/apply.py --merge --demo` + `gcc -m32 -std=c11 -fsyntax-only` with
  `_Static_assert(sizeof(UiGaugeWindow) == 0x3FC)` and `offsetof(...gaugePane) == 0x4C`:
  **PASS** (-m32 is required because pointers are 8 B on the host; noted in M2_types_merge.md).
* `python tools/verify_project.py`: **OVERALL PASS**; `code.bin` SHA-256
  `dfcd1b7ad170eab3932abfaa702b694e6673dc0a8744bfc070765cc8c8cc24d8` (bit-match untouched).
* `python tests/run_all.py`: **222 / 223 PASS**. The single failure is *not* in this lane; see
  BLOCKED below.
* `python tools/typedb/apply.py --merge` on those live answers writes **623 extern globals** to
  `include/dqxi/globals.h` and the merged maps; `gcc -m32 -std=c11 -fsyntax-only -I include`
  including `dqxi/dqxi_types.h` is clean (also clean for the demo headers).
* `python tools/progress.py` runs and now prints
  `types fields 0.0% / globals 13.9% / locals 0.0%`; the "Types and names" table in
  `progress/progress.html` shows the four requested rows (classes, fields, globals, locals).

## Sample before/after (full text: `orchestration/types/samples/BEFORE_AFTER.md`)

Before (M1 readable C of `Ui_GaugeWindow_InitPanesB`, with only M1 names):

```c
void Ui_GaugeWindow_InitPanesB(int self,int *arg2)
{
  int *piVar1;  int *piVar2;  int *piVar3;
  piVar1 = g_00412aac;
  ...
  self->f_4c = piVar2;
  ...
  self->f_50 = piVar2;
}
```

After (demo S/G/V maps merged; M2/M3 target quality):

```c
void Ui_GaugeWindow_InitPanesB(UiGaugeWindow *self,int *arg2)
{
  int *sentinelPart;  int *foundPane;  int *listCursor;
  sentinelPart = &g_uiPartSentinel;
  ...
  self->gaugePane = foundPane;
  ...
  self->flashPane = foundPane;
}
```

`f_f4` deliberately stays unresolved: there is no S answer for that offset yet, and the pipeline
never invents a name.

## Decisions

1. **Package name `tools/typedb`.** A concurrent worker on this task renamed `tools/types` while
   the session was live and deleted the original directory; I adopted the surviving package
   instead of racing it. All generated artefacts reference `tools/typedb`.
2. **G batch granularity.** The task asked for ~300 globals per batch. The generator packs whole
   subsystems first (which the task also requires) and caps at 300, so small subsystems produce
   small batches: 58 batches, mean 77, max 300. Merging unrelated subsystems to reach 300 would
   make each worker's context worse; leaving it also means G workers are already running.
3. **`maybe_g_...` is legal.** The template requires a `g_`-prefixed name *and* a `maybe_` prefix
   for low confidence; several G workers correctly wrote `maybe_g_x`. `apply.py` now accepts both
   `g_...` and `maybe_g_...` (and reports anything else), which removed 133 false validation
   errors.
4. **Demo is separate.** The hand-written sample merges to `orchestration/types/merged_demo/` and
   its readable proof is stored as text, so the real headers/readable tree cannot be contaminated
   by sample names.
5. **Literal-pool resolution.** The export labels the `.text` literal slot, not the data object;
   `g_00160900` is the slot whose value is the real global. `inventory.py` resolves the slot,
   `readable_c.py` prints the object name, and a literal that is a plain number now prints as a
   number (`InitBss` bounds read `0x008398E4`, not `g_00100044`).

## Open problems / suggested follow-ups

* `orchestration/types/out/G_*.json` had a duplicate name for `0x0075FCFC` and `0x0075DD00`
  (`g_actorActionVtable`); the G worker has since resolved it (latest validation: 0 errors). M2
  should still check for duplicates before merging a new wave of answers.
* The 281 namespace-only classes get no S batch. If a modder needs them as opaque types, generate
  `S_ns_###` batches (no fields to name, only class summaries).
* `globals.json` type guesses are access-width evidence, not semantic types; G workers are doing
  the real typing. Do not treat `type_guess` as final.
* The readable view still leaves `s_gauge_0028a1fc`-style string labels and unnamed callees
  (`func_003E043C`); those belong to the M1/naming lanes, not to S0.
* Struct sizes above 0x20000 with only "max field" evidence are cut at the last field and
  commented; M2 should re-check those classes against allocation evidence.

## BLOCKED (outside this lane, reported honestly)

**One test failure in `tests/run_all.py`:** 222/223 PASS, Tier 4
`test_scenario_9_mod_export.test_new_files_are_refused_on_luma_but_added_on_the_full_image`.

* During the full suite the mod export died in the in-flight `X5_resizable_assets` work:
  `tools/romfs_build.py:200 KeyError: 0` (`for path, data in sorted(additions, key=lambda x: x[0])`).
  That edit predates this lane and is not mine.
* I re-ran only that test after X5's fix: the export now succeeds, but the **test itself** raises
  `NameError: name 'RomFsIndex' is not defined` at
  `tests/tier4_real_world/test_scenario_9_mod_export.py:351` (the file has no import for the helper
  used there; its mtime is 19:05, before this lane started). This is a defect in the test, not in
  the pipeline, and fixing it by weakening the check is forbidden - so I report it instead.

The bit-matching build itself is green (`verify_project.py` OVERALL PASS, retail `code.bin` hash
unchanged). Re-run `python tests/run_all.py` once X5 (and the test owner) have finished.

**Concurrent same-task worker.** `S0_types_plan` was being run by at least one other process
(dispatcher state had several `S0`/`G_*` lanes live, and `tools/types/` was deleted/renamed under
this session). The artefacts are consistent at report time, but a later concurrent write to
`tools/typedb/apply.py` / `include/dqxi/` / task files cannot be ruled out. The authoritative
state is the files listed above; rerun `apply.py --validate` before M2.

## Not verified

* The demo names (`gaugePane`, `flashPane`, `g_uiPartSentinel`, `g_saveDataPathPrefix`) are
  **hypotheses** from real evidence, not runtime-confirmed; they exist only in
  `merged_demo/`/`samples/`.
* No S or V worker has run yet, so M2/M3 have **not** been executed against real S/V answers;
  validation has only seen live G answers.
* No emulator or hardware boot was run for this task (readable view only; no game binary changed).
