---
lane: merge
after: P0_regen, N_*
---
Merge all function-naming proposals into the project and regenerate the readable code.

Owns: `tools/merge_names.py` (new), `symbols.json`, `symbols_recovered.json`, `decomp/readable/`,
`decomp/ghidra/` (renaming only), `include/` headers.

1. Load `orchestration/naming/out/*.json`. Validate: valid C identifiers, unique names (on clash
   keep higher confidence, suffix the other `_2` and list it), addresses exist. Report counts by
   confidence and any batch that is missing or incomplete (list unnamed addresses → write a new
   task file `orchestration/tasks/N_redo_###.md` from `orchestration/naming/TEMPLATE.md` for them).
2. Spot-check 30 random proposals yourself against the code; if a batch is clearly poor
   (>30% wrong), queue it for redo the same way.
3. Apply: write names/signatures/summaries into the symbol files, regenerate `decomp/readable/`
   with names, typed parameters (from `params`) and a doc comment per function; propagate
   recovered struct/param types into `include/` where several proposals agree.
4. Bit-match build must still pass; tests green. Report named % before/after.
