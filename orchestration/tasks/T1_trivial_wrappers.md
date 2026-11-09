---
lane: tooling
after: M1b_merge_refined
---

# T1_trivial_wrappers - name tiny wrappers, getters and constant-returners by script, not by model

Run analysis (docs/WORKFLOW_FINDINGS.md): 86 % of worker time is model turns. A large share of the
still-unnamed functions are 3-30 instruction stubs whose behaviour is fully visible in the assembly
(return a field, return a constant, forward to another function, set a field). Naming those needs no model.
Build a rule-based namer that proposes names and summaries for them with real evidence, and feed the result
through the normal merge path. Never invent: if a function does not match a rule exactly, leave it.

Owns ONLY: `tools/trivial_names.py` (new), `tests/test_trivial_names.py` (new),
`orchestration/naming/refine/out/R_T01.json` (generated overlay, same entry format as
`orchestration/naming/refine/out/R_S01.json`), `docs/WORKFLOW_FINDINGS.md` (append a short result
section), `orchestration/done/T1_trivial_wrappers.md`, `AGENT_LOG.md`. Scratch in `out/scratch/T1/`.
Do not edit dispatch.py, merge_names.py or other workers' outputs.

## Inputs (all local, fast)

- `decomp/ghidra/functions.jsonl` (address, size, mode, current name) and `decomp/xref.json`
  (`python tools/xref.py` rebuilds it) for callers/callees; `python tools/fn.py 0xADDR --asm 40` shows how
  a dossier looks; read the facts in `orchestration/naming/FACTS.md` first (Ghidra traps!: VFP returns
  in s0, dropped r1..r3 forwards, 8-byte-aligned push prologues).
- Assembly: `asm/text/text_*.s`, lines like `/* 0x0066A720: 08402de9 */  push {r3, lr}`; ARM and Thumb.
- Current names: `decomp/readable/functions/<name>_<addr>.c`; only touch functions whose name is
  `func_*`/`FUN_*`/`maybe_*` (confidence < 0.5) - never rename a confident name.

## Rules to implement (each must be decoded from the instructions, not guessed from Ghidra's C)

1. **Field getter**: `ldr r0,[r0,#N]` / `ldrb` / `ldrh` / `ldrsh` then return -> `Get<Field>` style name is
   NOT possible without semantics, so name them by shape: `Obj_GetU32At0xNN`, `..._GetU8At0xNN`.
   Use a class prefix only when 3+ named callers/siblings agree (vtable siblings via
   `orchestration/naming/refine/scores.jsonl`). Confidence 0.45-0.6 (shape is certain, meaning is not).
2. **Field setter**: `str r1,[r0,#N]` then return -> `Obj_SetU32At0xNN` (same rules).
3. **Constant return**: `mov r0,#K` (or `mvn`, or movw/movt pair, or ldr literal) then return -> `ReturnsConstant0xK`
   (`ReturnsTrue`/`ReturnsFalse`/`ReturnsZero`, `ReturnsMinusOne` for 1, 0, 0, -1). Check the literal in the
   asm; these are usually vtable slot stubs.
4. **Pure forwarder**: only moves/loads arguments then `b` / `bl`+return to ONE callee -> `<CalleeName>Thunk`
   when the callee has a confident name, else `Thunk_<ADDR>` with kept_maybe.
5. **Empty stub**: `bx lr` / `pop {pc}` only -> `Nop_<ADDR>` or, if it sits in a vtable with named siblings,
   `<Class>_NoOp`.
6. **Two-callee wrappers and getters that call the singleton accessors** (e.g. `Os_GetGameWork`,
   `Game_GetDataManager`, `Game_GetWork`): name `<Accessor>Field0xNN` only if the offset chain is fully decoded.

Always: confidence < 0.5 requires the `maybe_` prefix (same rule as the refine batches); put the decoded
instruction sequence in `evidence`; set `previous_name`/`previous_confidence`/`change` like R_S01.json;
skip functions that are already in any `out/R*_*.json` with confidence >= 0.5.

## Validate and merge

- `python tools/check_refine.py` does not apply (no batch file). Check yourself: valid C identifiers, `maybe_`
  iff confidence < 0.5, every entry has evidence, no duplicate addresses.
- Unit test (`tests/test_trivial_names.py`): synthetic instruction sequences for each rule, plus 20 real
  functions you verified by hand in the asm (list their addresses in the test).
- `python tools/merge_names.py --check` shows 0 bad entries; run `python tools/merge_names.py` (it takes
  the merge lock, so it can wait for another merge) and `python tools/build.py` (bit-match PASS).

## Done when

The report states how many functions each rule named, how many were left alone and why, the false-positive
rate on a 30-function hand check, and the named share before/after (`merge_names.py --check` output).
