---
lane: types
after: M1_merge_names
---
Phase 2 of readability: types, struct fields, globals and local variables. After M1 the functions
have names, summaries and (some) parameter names, but the readable C still shows `iVar2`,
`local_44`, `uStack_40`, `arg1->f_1b4->f_7c`, `int` for object pointers and `g_007BE330`.
Your job is to build the pipeline and generate the worker batches — not to name everything yourself.

Owns: new `tools/typedb/` (NOT `tools/types/`: that name shadows Python's stdlib `types` module and breaks every tool) (struct DB, apply step), `include/dqxi/` headers, `tools/readable_c.py`
(apply rename maps), `orchestration/types/`, new task files `orchestration/tasks/S_###.md`,
`orchestration/tasks/V_###.md`, `orchestration/tasks/G_###.md`.

1. **Struct/class recovery (automated first):** from the Ghidra export + readable C, collect every
   `X->f_NNN` access per base pointer, constructors (vtable stores at +0), allocation sizes,
   vtables and the class names the naming batches already found (`Ui_GaugeWindow_*` → class
   `Ui_GaugeWindow`). Cluster accesses into candidate classes (same vtable / same ctor / same
   allocation size + field set) and write `orchestration/types/structs.json`
   (class, size, vtable, base class, fields{offset,size,type guess,uses}). Inheritance from
   base-ctor calls.
2. **Batches:** write `S_###` tasks (~15 related classes each): name the class and every field
   (`f_1b4` → `targetUnit`), type them, with evidence; output `orchestration/types/out/S_###.json`.
   `G_###` tasks (~300 globals each, grouped by address/user subsystem): name + type + comment.
   `V_###` tasks (~150 functions, same grouping as N batches): local variable rename map per
   function `{func: {"iVar2": "partyCount", ...}}` + parameter names still left as `aN`, using the
   struct/global names. V tasks must declare `after: M2_types_merge` (step 3) and use the merged
   headers; S and G tasks run first.
   Every template must say: never invent; vague-but-true beats precise-but-wrong; `maybe_` /
   confidence field; save progress every ~25 items; read WORKER_RULES context.
3. Write task `orchestration/tasks/M2_types_merge.md` (after: S_*, G_*): validate + merge S/G
   outputs into `include/dqxi/*.h` (real C structs, padding where unknown), make
   `tools/readable_c.py` cast/declare with those types and print `unit->targetUnit` instead of
   `f_1b4`. And `M3_vars_merge.md` (after: V_*): apply local rename maps in readable_c.py; then
   regenerate `decomp/readable/`.
4. Make sure the bit-matching build is untouched (readable view only; `src/` matching C may use
   the headers). Tests green. Extend `tools/progress.py` with "Types" (structs/fields named %),
   "Globals named %" and "Locals named %" rows.
5. Report: number of classes found, fields, globals, batches generated, and a sample of a
   function before/after (by hand-applying a few fields) to show the target quality.

NOTE (orchestrator, 2026-10-26 19:45): the package was renamed `tools/types/` → `tools/typedb/` while
you were running (the old name shadowed Python's stdlib `types` and broke every tool). Your later
edits landed in a new `tools/types/make_batches.py`. Before finishing: merge any newer work from
`tools/types/` into `tools/typedb/` (compare with `tools/typedb/make_batches.py`), use
`tools.typedb.*` imports everywhere, delete `tools/types/` entirely, and confirm
`python tools/build.py --help` and `python tools/progress.py` still run.
