---
lane: editor
---
Fix the Squirrel source-tier compiler crash found by the emulator boot tests.

Read first: `orchestration/done/X3_boot_tests.md` (§6 item 3 and its evidence),
`orchestration/done/E3_scripts.md`, `tools/script_build.py`, `tools/sqbin.py`, `docs/TESTING_EMULATOR.md`.

Symptom: recompiling `.nut` source works for small edits (e.g. only `TrgRCommand`), but a new
function or a `StartEvent` from `OnBeginScene` (13–15 recompiled functions) yields a pack that
crashes at/near boot in Azahar. The assembly tier (byte-exact) is fine.

Owns: `tools/script_build.py`, the source compiler module(s) it uses, `tests/` for scripts,
`tests/emu/` script cases, `docs/EDITING.md` (scripts section).

1. Reproduce with `tests/emu` (or `python -m tools.emu boot` with the failing mod). Diff the
   recompiled CNUT against retail per function: stack size / register allocation, literal and
   function-proto tables, outer-value (closure) indices, line/local-var info, default params,
   `NEWSLOT`/`CLOSURE` operands, jump offsets after code-size changes.
2. Find the root cause (the Squirrel 2.2-style VM in this game is unforgiving about stacksize,
   outer values and proto indices); fix the compiler, not the test. Add a unit test that pins it.
3. Prove in the emulator: the previously crashing edit (new function + StartEvent from
   OnBeginScene) boots and runs; plus a re-run of the existing script emu tests.
4. If some constructs can't be made safe, make `script_build.py` refuse them with a clear message
   pointing to the assembly tier, and document it.
