# E3b_script_compiler_fix — safe source-tier Squirrel builds (resumed)

**Status: complete for the compiler fix, the frame gate, the unit tests and the emulator
boot proof.** The original crash was not reproduced again with the old pack in the final
emulator window (the host emulator exited with `-1`, no guest fault, twice); see §6. The
fixed pack loads the field and runs in Azahar — the scene-load event's shop menu is live in
the UI heap and its shopkeeper line is in the text log (§5.1) — and the earlier 8-case suite
run by this lane passed. No hardware was available.

## 1. What the previous attempt left behind

A first worker had already done most of the diagnosis and had edited the files, then stopped
before writing a report:

- `tools/script_build.py`: every `CALL` now has a real destination (`fn`) instead of the
  stock `-1`/`0xFF` used for statement-position calls; `validate_nut()` checks register
  operands, call argument ranges, `CALL` targets, literals, `CLOSURE` prototype indices,
  jumps, local slots and line-info entries before a build writes a pack;
  `compile_function()` matches child functions by unique name instead of list position;
- `tests/test_script_build.py`: 16 tests (frame rules, the scene-load edit, name-matched
  reuse, validator refusal, pack staging, both tiers);
- `tests/emu`: a `script_load` case and fixtures, but the fixture, the driver and the
  pass criteria disagreed with each other (church menu vs shop menu vs screenshot only),
  and no report/AGENT_LOG entry existed.

This session completed the work, fixed two gaps found while validating it, and re-ran the
checks.

## 2. Root cause

Two defects compounded in the source tier; either one is enough to boot-test a bad pack.

1. **A discarded `CALL` result went to register `0xFF`, which this VM reads as 255.** Stock
   Squirrel emits `CALL -1, fn, this, nargs` when a call is a statement and its result is
   thrown away. This VM loads the 8-bit target operand **unsigned** (`Sq_VmExecute`,
   0x005B64CC: `uVar15 = (u32)*(u8 *)(ip + 5)`), so `0xFF` is 255, not -1. It then stores a
   closure's or native's result at `STK(stackbase + target)`; on a suspended callee
   (`WaitFrame`, `WaitMenu`, `MessageLoop`, …) it records the same value and
   `Script_Vm_Resume` (0x006BDBE4) writes the resumed value at
   `STK(stackbase + target)` **without** the `target != -1` guard that Squirrel 3.2's
   `sq_wakeupvm` has. `STK(stackbase + 255)` is outside the callee frame — 255 slots past it,
   in the caller's frame or beyond the VM stack. The pack loads, then the scene crashes with
   no script error. Checked across the retail corpus: **190,229 `CALL`s, 0 with arg0 = 0xFF**;
   the first broken b011 pack had **183**. That is the definitive frame-rule violation, and
   it is what `validate_nut` now refuses.

2. **Inserting one function recompiled 13–15 functions.** Child prototypes were paired by
   list position: one insertion shifted every later child, so the “unchanged” functions were
   compared with their new neighbours and recompiled. Each avoidable recompile multiplied
   the chance of hitting a compiler gap and made the pack larger and different from retail.
   Matching by **unique function name** reduces the same edit to 3 compiled functions (the
   new event, its caller `OnBeginScene`, and the module root that holds the prototype table);
   all other 14 are copied byte-for-byte from retail.

A third, smaller defect surfaced when the frame rule was enforced: a discarded call whose
target was the call's own `fn` register stayed “pending” in the decompiler, because the
next statement did not overwrite it. Five long `a || b || c` packs then decompiled to an
`ASM FALLBACK`/`$rN` and the whole-corpus semantic check dropped from 769/769 to 764/769.
**Fix:** a discarded result is written to the lowest free temporary (`local_top`), which is
inside the frame and is reused by the next statement; the decompiler then reads the call as
a finished statement. A result that is used still goes to `fn` and is moved to its
destination exactly as before.

## 3. What changed this session

- `tools/script_build.py`
  - discarded `CALL` target is `self.local_top` (not `fn`, never `0xFF`); all three call
    sites (member call, bare-name call, closure call) use the same rule;
  - comments updated to state the frame rule and why the temporary is chosen;
  - (from the first attempt, kept) `validate_nut` / `require_valid`, name-matched child
    reuse, and the `CALL`-target check.
- `tests/test_script_build.py` — 2 new tests:
  - `test_discarded_call_targets_reusable_temporary` pins the target to the first free
    temporary and below `stacksize`;
  - `test_chain_of_or_operators_round_trips_through_the_decompiler` pins the b009 `||` chain
    and forbids an `ASM FALLBACK` in the compiled output.
- `tests/emu/fixtures.py` — the scene-load edit is now “new `X3SceneEvent` starts the game's
  own `common.ShopEvent` from `OnBeginScene`”, the same pattern as the proven assembly case.
- `tests/emu/drive.py` — boots the edited pack, polls the live UI heap, records
  `place_live`, `shop_live`, the clock and the screenshot; no longer presses A/B after the
  field label appears.
- `tests/emu/run_cases.py` — `script_load` asserts a live field place label, the screenshot,
  game time past the title and no crash.
- `tests/emu/runner.py` — the quick runner's scene-load case (`tests.emu --case script_load`)
  adds a new function that opens the shop **in its own event thread** and asserts the shop
  entry label + the shopkeeper's line in the dynamic UI heap; it waits for a free RPC port and
  presses START at 430 game seconds like the `boot` movie, so a contended/slow host does not
  produce a false failure.
- `tests/emu/README.md` — distinguishes the two scene-load cases: the light runner asserts the
  shop menu label and the shopkeeper's line, the `run_cases.py` variant (nested
  `common.ShopEvent` start) asserts the field place label only.
- `docs/EDITING.md` — script section already carried the frame-rule/CALL explanation; the
  compiled-source semantic number is **769 / 769**, and the limits now say the source and
  assembly tiers plus the scene-load case have booted in Azahar, no hardware.
- `docs/SCRIPTS.md` — the `CALL` operand row now says the target is a real register (never
  `0xFF`), the compiler steps say children are matched by unique name and every build is
  validated, and the frame-rule section explains the unsigned 8-bit read (`STK(stackbase +
  255)`) with the retail count (0/190,229).
- `audit/SCRIPT_BUILD.md` — regenerated (769/769 on every metric, no failures).
- `orchestration/done/E3b_script_compiler_fix.md` — this report.
- `AGENT_LOG.md` — two entries for this lane (Entry 214 from the completing pass, Entry 230
  from the resumed session that added the positive scene-load proof and re-ran the gates).

The unrelated `tests/tier4_real_world/test_scenario_9_mod_export.py` `RomFsIndex` NameError
seen in one run was fixed by another lane while this task ran (`self.export_mod.RomFsIndex`);
I did not change or weaken that test.

## 4. Unit / corpus checks (this session)

```text
python -m unittest tests.test_script_build -v
  Ran 18 tests in 1.636s — OK

python -m tools.script_build verify
  scripts: 769
    assembly identical:      769/769
    source parses/compiles:  769/769
    source byte-identical:   0/769
    unchanged reuse exact:   769/769
    source semantic roundtrip:769/769
    report: audit/SCRIPT_BUILD.md
  → no failures
```

The last two lines are the important ones: the frame-safe compiler did **not** lose the
semantic round-trip for the five `||`/pending-call packs (it is 769/769 again), and an
untouched script is still bit-identical.

## 5. Emulator proof

The suite is opt-in and needs exclusive use of Azahar's fixed RPC port:

```powershell
python tests/emu/run_cases.py script_src script_load script_asm
```

The full 8-case run in this lane (`orchestration/logs/E3b_script_compiler_fix.log` at 20:30–20:39)
reported **8/8 PASS**: `empty`, `empty_save`, `text`, `table`, `script_src`, `script_asm`,
`script_load`, `native`. A later `--summary-only` run (no emulator) preserved the three script
cases in `out/emu/x3/summary.json` after another lane overwrote the mixed summary with its own
`table_grow` case.

The scene-load result that matters (`out/emu/x3/script_load/run/result.json`):

- edit: `b011`, source tier, **3 compiled / 14 reused**, 21,977-byte CNUT in a 22,053-byte
  `script/b011.pack`, `X3SceneEvent` present, `OnBeginScene` starts it;
- `place_live`: `0x33DA…` (the field's place label in the dynamic UI heap);
- `game_time`: 93.92 s, clock still advancing;
- `crash`: null (no guest fault; the emulator was closed normally);
- screenshot: `out/emu/x3/script_load/run/scene_event.png` (published as
  `docs/images/emu/script_load_event.png`).

An earlier positive proof is the **church-menu screenshot** from a separate run: the same edit
with `X3TestEvent` opening the church menu
(`StartUI(24, target); WaitMenu(); EndUI(24);`) from `OnBeginScene` —
`build/e3b/emu_proof.py` wrote `out/emu/tests/script_load_fixed/report.json`
(`reached_field: true`, `game_time: 1120.2`, six `txt_place` events) and
`field2.png`. The screenshot shows the church service menu (`おいのりをする`,
`いきかえらせる`, `どくのちりょう`, `のろいをとく`, `ふっかつ`, `やめる`) and the priest's
greeting, so the **new function executed** — this is more than "the field loaded". The
`reached_field` flag alone is weaker: its `txt_place` pane also logged a monster list, so
quote the screenshot when this proof is cited. §5.1 below adds the strongest evidence
(shop menu label in the dynamic UI heap plus the shopkeeper's typed line).

### Independent audit (2026-10-30, resumed worker)

- The pre-fix and post-fix b011 packs are the same source edit and were compared field by
  field: 17 functions, identical stack sizes, parameter/literal/outer/local/line/default
  tables, prototype order and jump targets. The **only** difference is 183 `CALL` arg0
  words, `0xFF` → a real register. That isolates the crash mechanism to the `CALL` target.
- Current scene edit: 3 compiled / 14 reused; `validate_nut` clean; the module's `CLOSURE`
  indices resolve to `X3SceneEvent` (proto 2) and `OnBeginScene` (proto 3) after the insert;
  no jump leaves its function.
- `python -m unittest tests.test_script_build -v`: **18/18 OK**.
- `python -m tools.script_build verify`: assembly 769/769, source compiles 769/769,
  unchanged reuse 769/769, semantic round-trip 769/769, from-scratch byte-identical 0/769
  (expected).
- `python tests/run_all.py`: **384 run, 383 pass, 1 skip, 0 fail** (SUCCESS).
- `python tools/verify_project.py`: **OVERALL: PASS**.

The three script cases were re-checked from the saved results without booting again:

```text
python tests/emu/run_cases.py --summary-only script_src script_load script_asm
script_src   PASS   (book message differs from the field)
script_load  PASS   (field place label live, screenshot, game time, no crash)
script_asm   PASS   (shop menu live, screenshot, no crash)
```

A controlled **old-vs-fixed** boot was also attempted twice with the pre-fix pack
(`out/emu/script_load/luma/.../b011.pack`, 183 `CALL 0xFF`, 15 recompiled functions) and the
same source rebuilt by the fixed compiler (0 `CALL 0xFF`, 3 compiled). Both packs reached the
field (`place_live`) and then the **host emulator process exited with `-1`**, with no
`Data/Prefetch Abort`, `Unmapped` or `svcBreak` line: this host's documented Azahar startup
flake, made more frequent by other lanes' emulator runners killing each other's process.
So the original boot crash was **not re-observed** in this window; the evidence that the
old pack violates the frame rule is the static one above (183 registers `0xFF` vs 0 retail
occurrences), and the fixed pack is the one that is proven to boot and run.

### 5.1 Positive scene-load proof (light runner, resumed session)

The quick runner's `script_load` case was run after the last compiler change and passed on the
first attempt (`out/emu/tests/script_load/report.json`, emulator in OpenGL mode because Vulkan
hangs on this host):

```powershell
python -m tests.emu --case script_load
```

- edit: `b011`, source tier, **3 compiled / 14 reused** (`X3SceneEvent`, `OnBeginScene`, root);
- the new event runs **in its own thread** and opens the shop:
  `WaitFrame(30); StartUI(2, -1); WaitMenu(); EndUI(2);`;
- `menu_labels`: `かいにきた` live at `0x33D8A5B0` in the dynamic UI heap (the same probe
  X3 used for menus; the resource copy at `0x31/0x32` is outside the scan range);
- the pane-text log recorded the shopkeeper's line
  `「ここは　武器屋だ。どんな用だい？」` typed after the load — direct evidence that the
  recompiled event executed, not just that the pack loaded;
- `game_time` 696.5 s, clock still advancing, `crash: null`, `hook_alive: true`;
- screenshot: `out/emu/tests/script_load/field_after_load.png` (shop menu over the fading
  field: `かいにきた / うりにきた / やめる` and the shopkeeper's message), also published as
  `docs/images/emu/script_load_menu.png`.

A **negative control** was built from the same source: one statement-position `CALL` target
patched back to `0xFF` (`WaitMenu()`, `call_before: 1` → `call_after: 255`); `validate_nut`
reports it (`... CALL discards its result into register -1 (0xFF) ... stack 6`) and
`require_valid` refuses the build, so the control pack had to be produced by bypassing the
gate with `sqbin.build`. That boot attempt (`out/emu/e3b/script_load_call255/report.json`) was
inconclusive: the host emulator exited with `-1` before the title. The causal claim therefore
rests on the static rule (§2) plus the fact that the fixed pack is the one that boots and runs.


## 6. What is NOT verified / open problems

1. **No hardware run.** Azahar on the Old-3DS profile is necessary, not sufficient. The
   §10 checklist in `docs/EXPORT.md` still has to be run on a real 2DS/3DS.
2. **The old crash was not reproduced in the final window.** The first pass (X3) saw the
   crash; the later A/B was inconclusive because the host emulator exited (the old-vs-fixed
   pair above and the `0xFF` control in §5.1). The static rule and the retail corpus
   (0/190,229 `0xFF`) are what justify the fix; a fresh machine with a quiet emulator should
   repeat the A/B once.
3. **Scene-load UI is asserted only by the light runner.** `tests.emu --case script_load` proves
   the shop menu and the shopkeeper's line after the load (§5.1) when the new function drives
   the UI itself. The `run_cases.py` variant starts `common.ShopEvent` through a nested
   `StartEvent` (the thread slot is replaced) and therefore asserts only the field place label,
   the clock and no crash.
4. **Outer values, generators, classes, `try`/`throw`, `foreach`** are still rejected with a
   line number rather than compiled; the retail corpus does not use them. Edits that need
   them must use the assembly tier.
5. **Emulator lanes still collide.** Two runners and other workers share the compiled-in
   RPC port 45987; `kill_emulators()` only kills the path it owns, so a main-root runner can
   kill a main-root run while an isolated-root runner is alive. A lock file or configurable
   port is still the right fix (X3 follow-up).
6. **Source tier is semantically, not byte-, equal to retail** (0/769 identical from
   scratch). That is unchanged and expected; the assembly tier is bit-exact.

## 7. Suggested follow-up tasks

1. Re-run the old-vs-fixed A/B on a quiet machine (or after adding an emulator lock) to
   capture the original crash and the fixed boot in one summary.
2. Make `tests/emu/run_cases.py` reserve the RPC port / write a lock file so concurrent
   lanes cannot kill each other's evidence.
3. If a visible scene-load event is wanted, try `WaitLoadingEnd(); StartEvent(common.ShopEvent);`
   in `X3SceneEvent` and assert the shop labels; keep the current field-label check as the
   minimum.
4. Hardware pass for one source-tier and one assembly-tier edit (§10 of `docs/EXPORT.md`).
