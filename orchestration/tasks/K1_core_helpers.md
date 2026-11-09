---
lane: argon
after: P1_progress_types
---

# K1_core_helpers - pin down the most-called unnamed helpers (highest leverage naming)

Every misread small helper poisons the names of all its callers (example: `Item_LookupRecord`
was misread once and dozens of item functions became "Text_*"). The bulk batches name functions
top-down; this task goes **bottom-up**: the helpers everything else calls.

Owns ONLY: `orchestration/naming/refine/out/R_K01.json`, `orchestration/naming/FACTS.md`
(append facts), `orchestration/done/K1_core_helpers.md`, `AGENT_LOG.md`. Scratch files go to
`out/scratch/K1/` (WORKER_RULES 12b).

## Pick

From `orchestration/naming/refine/scores.jsonl` take functions whose current name is
`maybe_*` or `func_*`, sort by `callers_conf` (named callers) descending, and work down the list.
Target: the top 120 (stop earlier if your session runs low; quality over count). Skip ones
already in `orchestration/naming/refine/out/R_S01.json`.

## For each

1. Read the **disassembly**, not only the Ghidra C: `asm/` or the `Address:` in
   `decomp/functions/<name>.c`; Ghidra drops return values and mangles registers (see
   FACTS.md "Ghidra traps"). Small helpers are often 5-30 instructions: decode them exactly.
2. Check 3-5 named callers to see how the result is used.
3. Decide: confirmed / corrected / kept_maybe, same rules and JSON format as the refine
   batches (`orchestration/naming/REFINE_TEMPLATE.md`). Put the decoded behaviour
   ("returns obj+0x24+idx*4, or obj->f_C4 for 0xFF") in `evidence`.
4. When a helper reveals a reusable fact (a record layout, a manager at work+8->+0xNN, an id
   range), append it to `FACTS.md` under the right heading with one line of evidence. Every
   later worker gets FACTS.md in its prompt, so this is where your work multiplies.

## Done when

- `R_K01.json` exists; `python tools/check_refine.py` is not used for it (no batch file), so
  check by hand: valid identifiers, `maybe_` iff confidence < 0.5, every entry has evidence.
- `python tools/merge_names.py --check` reports 0 bad entries; then run
  `python tools/merge_names.py` and `python tools/build.py` (must print the bit-match PASS).
- Report: how many confirmed/corrected/kept, the facts you added, and the 10 most important
  corrections with their caller counts.
