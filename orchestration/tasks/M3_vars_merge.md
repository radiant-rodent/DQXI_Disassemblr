---
lane: merge
after: V_*
---

# M3_vars_merge - apply local/parameter rename maps

The `V_###` batches renamed the remaining `iVar2`, `local_44`, `uStack_40`, `argN`
tokens in the readable C (the ones that survived M1 and M2). Apply them and
regenerate the readable tree.

Owns: `orchestration/types/merged/**`, `decomp/readable/**`,
`orchestration/done/M3_vars_merge.md`. `tools/typedb/apply.py --merge` already
merges V answers into `merged/locals.json`; `tools/readable_c.py` already applies
that map. Only fix those tools if a real answer exposes a bug.

## 1. Validate

```powershell
python tools/typedb/apply.py --validate
```

Errors to expect from real V answers: a token that is not declared in the function,
a new name that collides with another local, a C keyword, or a function address that
is not in `locals.json`. Reject/fix the answer; never let two variables share a name.
Warnings on `param_N` vs `argN` are expected where M1 already renamed the parameter;
resolve them in the answer, not by editing the map by hand.

## 2. Merge and regenerate

```powershell
python tools/typedb/apply.py --merge
python tools/merge_names.py --check
python tools/merge_names.py
```

`merge_names.py` re-renders `decomp/readable/` from the Ghidra pseudocode and applies
`readable_c.rewrite`, which reads `orchestration/types/merged/locals.json` and renames
exactly the listed tokens per function. It also keeps the M1 summaries and typed
signatures - do not regenerate with `readable_c.py` alone, or the documentation block
is lost.

Verify:

* every function in `merged/locals.json` exists in the readable tree;
* the renamed tokens no longer appear as declarations in that function and the new
  name does appear;
* a function with both field and local maps reads like
  `u32 count = party->memberCount;` instead of `uVar2 = self->f_1c4;`;
* no readable file fails strict UTF-8 and `decomp/readable/` still has the same
  number of files as before (minus none).

## 3. Keep the build green

```powershell
python tools/build.py
python tests/run_all.py
python tools/verify_project.py
```

Types and local names are a read-only view; the retail build must still bit-match.

## 4. Progress

`python tools/progress.py` must show the three readability rows from
`orchestration/types/merged/report.json`:

* **Types** - structs/fields named;
* **Globals named**;
* **Locals named**.

If a row is missing, the merge report was not written; rerun `apply.py --merge`.

## 5. Report

`orchestration/done/M3_vars_merge.md`: functions with V answers, tokens renamed,
before/after sample of one function (field + global + local names together),
remaining placeholder count, test results. List the functions whose answers were
rejected and why. Note honestly that names remain static-analysis hypotheses.

Never modify `..\3DS_Translate`, `asm/`, `original/`, or the retail image.
All text/JSON writes are UTF-8.
