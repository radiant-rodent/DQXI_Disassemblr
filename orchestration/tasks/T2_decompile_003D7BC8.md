---
lane: decompile
---

# T2_decompile_003D7BC8 - write the C for the one function Ghidra could not decompile

Ghidra decompiled 18,748 of 18,787 entry points. 38 of the rest sit inside bigger functions (their code is
already in the container's C). **One is unrecovered: `0x003D7BC8`** (ARM, name `maybe_Ui_DiveForm_UpdateCommandList`,
about 135 instructions, up to the next prologue at `0x003D7DDC`). See `decomp/ghidra/COVERAGE.md` and
`decomp/ghidra/missing_result.jsonl` (`status: unrecovered`).

Owns ONLY: `decomp/ghidra/recovered/FUN_003D7BC8_003d7bc8.c` (new; same naming and header style as the other files in
`decomp/ghidra/recovered/`), `decomp/ghidra/missing_result.jsonl` (change this one row from `unrecovered` to
`recovered`, with `name` and `file` set like its neighbours), `decomp/ghidra/COVERAGE.md` (counts: Unrecovered 0,
Decompiled 18,749 / 99.79 %), `orchestration/done/T2_decompile_003D7BC8.md`, `AGENT_LOG.md`.
Scratch in `out/scratch/T2/`. Do not touch other recovered files.

## Method

1. `python tools/fn.py 0x003D7BC8 --asm 200` (the dossier tool has no C for it, but shows callers/callees and
   the assembly); read `orchestration/naming/FACTS.md` first (Ghidra traps, singleton accessors, offsets).
   Never walk or grep the `asm/` or `decomp/` trees (rule 14): use `tools/fn.py` and `tools/xref.py`.
2. Find out why Ghidra failed (the assembly has a `muls` followed by a `nop`, and `bics r0, r0, #0xbd` right at the
   start; check for undecodable data words inside the code, a function that falls through into the next
   one, or a jump table) and write the cause in the report.
3. Translate to C by hand, instruction by instruction, in the style of the neighbours in
   `decomp/ghidra/recovered/` (they use `u32`, `func_XXXXXXXX` for callees and the project's accessor names).
   Resolve callees with `python tools/fn.py ADDR -b 0 --max 3` so you use their CURRENT names
   (for example `0x00654098`, `0x0011FE8C`, `0x0011CFAC`, `0x00116AE0`).
4. Keep behaviour exact: every branch, every memory access with its offset, literal pool loads
   (`ldr rN,[pc,#...]`) resolved to their values or symbol names. Mark anything you could not resolve with
   `/* TODO: ... */` and list it in the report; never invent behaviour.

## Done when

- The C file exists and is readable by a person; the report lists each branch target and callee and how it maps.
- `python tools/merge_names.py --check` shows 0 bad entries and `python tools/progress.py` runs;
  the decompiled count reads 18,749 of 18,787.
- If the function cannot be written with confidence, say so under `## BLOCKED` with the exact obstacle instead
  of guessing (an honest partial with TODOs beats a plausible-looking wrong function).
