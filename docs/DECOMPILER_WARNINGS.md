# Ghidra warnings in the readable C: what causes them (2026-11-10/11)

Counted over `decomp/readable/functions` (17,994 files) and checked against the real bytes in
`original/exefs/code.decompressed.bin` (capstone, ARM and Thumb).

| Warning in the C | Count | What it really is | State |
|---|---:|---|---|
| `Subroutine does not return` | 1,978 in 1,732 files | Ghidra marked an ordinary helper "noreturn" (`std_ConstructArray`, a `strlen16`, a guard check, `std_memmove`, ...). Every top callee has a `pop {..pc}` / `bx lr`. In most callers the call is the last statement, so only the final `return;` was dropped; in about 45 functions real code after the call was lost (see the re-export below). | re-export done in `out/ghidra_v2/` (not swapped in); until then the readable C carries a NOTE |
| `Removing unreachable block` | 4,394 in 419 files | Decompiler notes about code it proves dead. The re-export did NOT change it (4,438 after). Separate cause, not analysed yet. | unchanged |
| `Bad instruction - Truncating control flow` / `Control flow encountered bad instruction data` / `halt_baddata()` | 1,076 / 693; 657 functions | Code or a literal pool decoded in the wrong ARM/Thumb mode, or a function end Ghidra ran past. The re-export did NOT change it (669 -> 672 functions). | unchanged, needs its own investigation |
| `Could not recover jumptable ... Too many branches` + `Treating indirect jump as call` | 991 each, 930 files | **Cosmetic in 922 cases.** No switch: an indirect tail call, usually a virtual call as the last statement (`ldr r2,[r0]; ldr r2,[r2,#0x84]; bx r2`). Ghidra's C for it is correct. About 19 are real switch tables or oddities. | 922 rewritten to one comment in the readable C; the raw export still has them |
| `Restarted to delay deadcode elimination`, `Heritage AFTER dead removal`, `Type propagation algorithm not settling`, `Globals starting with '_' overlap ...` | 252 / 233 / 91 / 229 | Decompiler-internal notes about hard functions. Harmless. | left as is |

## Why the noreturn warnings happened

`tools/ghidra_scripts/ExportDQXI.java` runs Ghidra without analysis (`-noanalysis`) and only created functions at the
seed list (`decomp/function_seed.tsv`). Helpers reached only through `bl`/`blx`, or whose mode differs from the caller's
(ARM code calling Thumb helpers with `blx`), never became functions in the right mode; Ghidra decoded them wrongly and
marked them noreturn. The same missing context turns a final `bx rX` into an "indirect jump".

## What was changed

1. `tools/readable_c.py` (`clean_decompiler_warnings`, end of `rewrite`): decodes the bytes behind each warning.
   Jump-table warnings on `bx rX` / `ldr pc,[rX,#n]` / `mov pc,rX` become "tail call through a function pointer / vtable
   slot (not a switch)" (922 rewritten, 19 kept). "Subroutine does not return" on a callee that really returns becomes a
   NOTE (1,791 rewritten, 23 kept).
2. `tools/ghidra_scripts/ExportDQXI.java`: after the seeds, creates a function at every call target that is missing, in the
   mode the call implies (`bl` keeps the caller's mode, `blx` immediate switches it), and clears NoReturn on functions whose
   body contains a return.

## Re-export test (Ghidra 12.1.4 at `%LOCALAPPDATA%\Programs\opencode-tools\ghidra_12.1.4_PUBLIC`)

Run on a COPY of the project, read-only, into `out/ghidra_v2/` (project copy in `out/ghidra_v2/project`, output in
`out/ghidra_v2/export`, log in `out/ghidra_v2/run.out`). `decomp/ghidra`, the readable tree and the running work were not
touched. About 10 minutes. The script created 93 call-target functions and cleared NoReturn on 9.

| | before | after |
|---|---:|---:|
| `Subroutine does not return` | 1,818 | 21 |
| functions with that warning | 1,581 | 21 |
| `Removing unreachable block` | 4,191 | 4,438 |
| `halt_baddata()` functions | 669 | 672 |
| `Could not recover jumptable` | 946 | 1,000 |

Of the 18,159 functions present in both: 16,153 identical, 1,560 only lost the noreturn warning (mostly gaining the final
`return;`), 44 grew by more than 10% (about 12,000 lines in total; e.g. `Field_InitActorGlobalState_7A70F8` 10 -> 305 lines,
0x00661974 379 -> 744), 5 shrank (0x00417EE0 83 -> 12, 0x002134DC 48 -> 36, ...). The list is in
`out/ghidra_v2/changed_functions.tsv`.

Correction to an earlier note in this file's first draft: the cut-off is mostly NOT lost code. The first example checked,
`Actor2D_InitFromRecord`, really ends with the call; only `return;` was missing.

## Not done: swapping the new export in

Replacing the raw files in `decomp/ghidra/functions` would change the readable C of about 1,600 functions and the local
variable tokens in some of them; V_ batches and the merged name/type maps are keyed on the current tokens, so do it between
rounds, not while V_ workers run. Suggested: after the V_ batches and M3 are merged, copy over only the 49 functions in
`changed_functions.tsv` (real code changes), re-run `tools/organize_ghidra.py` and `tools/merge_names.py`, then spot-check.
The remaining causes (unreachable blocks, bad instructions) still need their own look.
