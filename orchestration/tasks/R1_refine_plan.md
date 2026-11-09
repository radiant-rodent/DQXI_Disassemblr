---
lane: refine
after: M1_merge_names
---
Second naming pass for the ~10,300 functions that only have a `maybe_` (low-confidence) name.

Why: the first pass named most functions while nearly everything around them was still
`func_XXXXXXXX`. After M1_merge_names the readable C shows ~8,500 confident names, so many `maybe_`
functions now have named callers/callees/siblings and can be named properly.

Owns: new `tools/make_refine_batches.py`, `orchestration/naming/refine/`, new task files
`orchestration/tasks/R_###.md`, `orchestration/tasks/M1b_merge_refined.md`, and a new template
`orchestration/naming/REFINE_TEMPLATE.md`.

1. `tools/make_refine_batches.py`: list every function whose merged name starts with `maybe_` (or
   confidence < 0.5). Score each by how much confident context it now has (named callers + named
   callees + named vtable siblings + string/constant evidence). Sort by that score, highest first,
   so the easiest wins come first; group neighbours (same caller/vtable/address block) into batches
   of ~150 → `orchestration/naming/refine/batches/R_###.txt` (address, current maybe_ name,
   confidence, readable-C path, context score).
2. `REFINE_TEMPLATE.md` (based on `orchestration/naming/TEMPLATE.md`): same output format into
   `orchestration/naming/refine/out/R_###.json`, plus: start from the existing guess and its
   evidence (from `orchestration/naming/out/`), re-read the function with the now-named neighbours,
   then either confirm (raise confidence, drop `maybe_`), correct, or keep `maybe_` honestly. Each
   entry records `previous_name` and what new evidence changed. Never invent; a correct vague name
   beats a precise wrong one.
3. Generate one `R_###.md` per batch from the template (`after: R1_refine_plan`).
4. Write `M1b_merge_refined.md` (`after: R_*`): same checks as M1_merge_names (identifiers, clashes,
   30-entry spot check, redo weak batches), then apply the refined names, regenerate
   `decomp/readable/`, keep the bit-matching build green, and report the `maybe_` count before/after.
   If >1,500 `maybe_` remain and the last pass still converted >20% of its inputs, it may generate
   one more refine round the same way (`R2_###`); otherwise stop and list what's left as needing
   manual reverse engineering.
5. Report: how many maybe_ functions, the context-score distribution, batches generated.

NOTE (orchestrator, 2026-10-26): an earlier worker on this task went off-task and was stopped. It left
`tools/make_refine_batches.py`, `orchestration/naming/refine/` and 82 `tasks/R_###.md` files. Treat
all of them as unverified: re-check (or regenerate) the batches and every R task file against
steps 1–3, keep `after: R1_refine_plan` in each R task, and say in your report what you kept.
