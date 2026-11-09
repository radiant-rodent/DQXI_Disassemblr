# T1_trivial_wrappers — name tiny wrappers, getters and constant-returners by script

**Status:** completed (resumed run; the tool, the batch and the merge were finished here)
**Owned outputs:** `tools/trivial_names.py` (new), `tests/test_trivial_names.py` (new),
`orchestration/naming/refine/out/R_T01.json` (18 entries), this report, one `AGENT_LOG.md` entry,
a result section in `docs/WORKFLOW_FINDINGS.md`
**Tooling:** `python tools/trivial_names.py --check` → `OK`; `python tests/test_trivial_names.py` → 39 tests OK;
`python tools/merge_names.py --check` → 0 bad entries; `python tools/build.py` → bit-match PASS

## Result in one paragraph

The tool works and is honest, but the premise of the task does not hold for this binary: the retail
executable has **no** tiny getter/setter/constant-returner functions left at a Ghidra function start.
A whole-binary byte scan found 496 `ldr r0,[r0,#N]; bx lr`, 94 `ldrb…`, 489 `str r1,[r0,#N]; bx lr`,
382 `strb…` and 2,321 `mov r0,#imm; bx lr` sequences, and **not one of them begins a function** — the
compiler inlined every one of them. What is left at function granularity is a different class: pure
forwarders (18 named here) and a large family of deleting-destructor thunks (247, deliberately left
alone). So the batch is 18 entries, all rule 4, and the report's main value is the measured census
that says where the remaining trivial work actually is.

## What I did

1. Wrote `tools/trivial_names.py`: a self-contained ARM/Thumb decoder (no capstone, no Ghidra C),
   a cross-check against `asm/text/*.s`, the six rules from the brief, a validator and a batch writer.
   It reads `decomp/ghidra/functions.jsonl`, `decomp/readable/functions/*.c`,
   `orchestration/naming/refine/scores.jsonl` (vtable groups) and `original/exefs/code.decompressed.bin`.
   Runtime about 30 s for the whole binary.
2. Ran it: 5,175 unnamed candidates, 18 proposals, all rule 4.
3. Hand-checked all 18 against `asm/text` (0 false positives) and 30 sampled rejections (0 false
   negatives for the implemented rules).
4. Merged through the normal path (`merge_names.py`, then `build.py`).
5. Wrote `tests/test_trivial_names.py`: 39 tests — synthetic ARM and Thumb sequences for every rule,
   9 rejection cases, the 20 real functions below, and a validation pass over the batch file.

## Per-rule counts

| rule | shape | proposals |
|---|---|---|
| 1 | field getter `ldr/ldrb/ldrh/ldrsh r0,[r0,#N]` | **0** |
| 2 | field setter `str r1,[r0,#N]` | **0** |
| 3 | constant return `mov/mvn/movw+movt/ldr literal` | **0** |
| 4 | pure forwarder (one callee) | **18** |
| 5 | empty stub `bx lr` / `pop {pc}` | **0** |
| 6 | accessor + field (`bl <singleton>; ldr r0,[r0,#N]`) | **0** |

Why rules 1-3 and 5 are empty is the finding, not a bug: see the census below.

## The census that kills the premise

Shape census over all 18,159 functions whose Ghidra mode is `ok` (decoded from the bytes, not from
Ghidra's C):

| shape | unnamed functions at a function start |
|---|---|
| getter (`ldr/ldrb/ldrh/ldrsh r0,[r0,#N]` then return) | 0 |
| setter (`str/strb r1,[r0,#N]` then return) | 0 |
| constant return (`mov r0,#K` then return) | 1 |
| constant from a literal pool | 13 — all load `0x7BE2D0`, a data pointer, so rejected |
| pure forwarder | 13 (plus 5 found after the merge, 18 total) |
| accessor + field | 1 |
| empty stub | 175 — but every one is a `blx lr` / `b` misdecode, not a real no-op |

The same shapes exist in the binary in the thousands (numbers in the first paragraph) but always
*inside* a larger function, where the compiler inlined them. Naming them would mean naming inlined
code, which is not a function and has no name to give.

## What was left alone, and why

At generation time, of 5,175 unnamed candidates:

| reason | count |
|---|---|
| decoded, but no rule matched exactly | 2,113 |
| no return within the 64-byte scan window (real code, too big for a stub) | 2,557 |
| `asm/text` and the byte decode disagree on some instruction | 487 |
| proposed | 18 |

The 2,113 "no rule" bucket is dominated by one pattern: **247 × `push {r4,lr}; bl X; pop {r4,lr};
b 0x0010F6CC`**, the deleting-destructor thunk (call the class destructor, then tail-call the shared
deallocator). Rule 4 requires exactly one callee, and `0x0010F6CC` has no confident name, so these
were left alone rather than guessed. They are the single biggest trivial win left (see follow-ups).
The rest of the bucket is ordinary code: virtual calls through a vtable slot (`ldr r2,[r1,#N]; blx r2`),
constructors (one call plus several stores), and functions that call two or three helpers.

The 487 disagreements are the two disassembler traps documented in the tool's docstring:
`0x00102B90` (the sweep prints Thumb `ands r0,r2`, the bytes are ARM `push {r4,lr}`) and
`0x00115410` (Ghidra says Thumb, the bytes are ARM `ldr fp,[pc,#0x514]`). The tool decodes the bytes
itself and requires `asm/text` to agree on size and mnemonic for every instruction up to the return;
when it cannot confirm a mode it refuses the function instead of guessing. 4 of the 30 sampled
rejections were these traps.

## The 18 proposals (all rule 4, all hand-verified)

| address | name | confidence |
|---|---|---|
| 0x00101AA0 | `maybe_Thunk_Call00100F04` | 0.45 |
| 0x0014DBAC | `Camera_GetHeadingAngleThunk` | 0.5 |
| 0x0022213C | `maybe_Thunk_Call006C47BC` | 0.45 |
| 0x00222B48 | `maybe_Thunk_Call006C47BC2` | 0.45 |
| 0x0022411C | `maybe_Thunk_Call00574428` | 0.45 |
| 0x002BDFEC | `maybe_Thunk_Call00180910` | 0.45 |
| 0x002BFA68 | `Actor_TrySelectIdleAnimationThunk` | 0.5 |
| 0x002D1588 | `maybe_Thunk_Call006C8108` | 0.45 |
| 0x002D1804 | `maybe_Thunk_Call006C81082` | 0.45 |
| 0x002D1F1C | `maybe_Thunk_Call006C81083` | 0.45 |
| 0x0042164C | `maybe_Thunk_Call0010EBE4` | 0.45 |
| 0x00440308 | `maybe_Thunk_Call001CEE24` | 0.45 |
| 0x00479288 | `Ui_Object_DtorBaseThunk` | 0.5 |
| 0x0047E4CC | `Sound_PlaySeByIdThunk` | 0.5 |
| 0x005248B0 | `Fx_ApplyParticleStateThunk` | 0.5 |
| 0x005248C0 | `Fx_ApplyParticleStateThunk2` | 0.5 |
| 0x0060E5A8 | `Ui_Bar_StartFadeInThunk` | 0.5 |
| 0x0063E064 | `maybe_Thunk_Call00713C7C` | 0.45 |

Seven got a confident name (the callee already had one); eleven kept `maybe_` because the callee is
still unnamed, and are named after the callee's address.

## Hand checks

* **False positives: 0 / 18.** Every proposal was read back against `asm/text` and the raw bytes.
  The tool's own cross-check already refuses any function where the two disassemblers disagree, so
  the residual risk is a case where both are wrong in the same direction; none was found.
* **False negatives: 0 / 30** for the implemented rules. 30 rejections sampled at random (seed 7)
  were read by hand: 4 mode traps, 6 virtual calls through a vtable slot, 5 constructors or
  multi-store functions, 12 functions with two or more callees, 3 VFP-returning wrappers. None of
  them is a one-callee forwarder, a single-field getter/setter or a constant returner. The one
  systematic gap is the 247 destructor thunks, which are a *new* rule, not a miss of the existing ones.

## Decisions (recorded because the brief left them open)

* `<ADDR>` in `Thunk_<ADDR>` is the **callee's** address (`maybe_Thunk_Call<CALLEE>`), matching the
  convention already in the repo (`maybe_Thunk_Call63B368`). It is more informative than the
  function's own address, which is already in the filename.
* Getter/setter confidence is 0.5: the shape is certain, the field's meaning is not. A class prefix
  is used only when 3+ confidently named functions in the same vtable group share a prefix of at
  least two components; otherwise the prefix is `Obj`.
* Rule 5 requires a real return (`bx`/`pop {pc}`), not a branch. `push {r4,lr}; b somewhere` is a
  tail call, and is exactly what a wrong-mode decode of a normal function looks like.
* `0` becomes `ReturnsZero`, not `ReturnsFalse` (the type is unknown).
* Duplicate names get a numeric suffix (`…Thunk2`), and the summary says so.
* `--report` writes nothing: the merged batch file is the record of what was applied, and a report
  must not overwrite it.

## Verification

```
python tests/test_trivial_names.py        Ran 39 tests ... OK
python tools/trivial_names.py --check     R_T01.json: 18 entries / 4 pure forwarder 18 / OK
python tools/merge_names.py --check       unknown addresses 0, batches missing none,
                                          refine batches missing none, 0 bad entries
python tools/build.py                     [PASS] code.bin bit-matches (0 differences)
                                          [PASS] ExeFS .code bit-matches (0 differences)
                                          ALL ARTIFACTS VERIFIED SUCCESSFULLY (Exit Code 0)
```

Named share: **13,207 / 18,787 = 70.30 %** before this batch, **13,325 / 18,787 = 70.93 %** after
(`merge_names.py --check`). The difference is shared with batches that merged concurrently; this
batch's own contribution is 18 renamed functions, 7 of which now count as named (confidence 0.5) and
11 of which stay `maybe_` (0.45). `maybe_` count 5,496 → 5,462.

## Not verified

* No emulator or runtime test: these are name-only changes, and the build is bit-identical, so the
  game cannot behave differently.
* The 11 `maybe_Thunk_Call…` names say "this forwards to that address", not what the callee does.
  They are placeholders that become real names when the callee is named.
* The claim that `0x0010F6CC` is a shared deallocator is inferred from 247 identical call sites, not
  decoded. That is why the destructor thunks were left alone.

## Follow-ups

1. **Rule 7: deleting-destructor thunk.** `push {r4,lr}; bl <dtor>; pop {r4,lr}; b <dealloc>` with a
   confidently named destructor → `<Class>_DeleteThunk` (or `maybe_…` when the destructor is unnamed).
   247 functions, the largest trivial class left. It needs `0x0010F6CC` named first, or a rule that
   accepts an unnamed shared deallocator.
2. **Name `0x0010F6CC`.** 247 call sites, one argument (the object), no return value used. A single
   dossier settles it and unblocks follow-up 1.
3. **Do not re-run this tool after a merge.** It is a one-shot generator: after the merge the 7
   confident names are applied, so a re-run proposes only the 11 `maybe_` ones again (same names,
   `previous_name` now equal to the new name). The batch file in the repo is the merged 18-entry one.
4. **The 487 asm/text disagreements are a data-quality bug worth its own task**: two functions are
   decoded in the wrong mode by the sweep and about 150 by Ghidra in the other direction. A tool that
   re-derives the mode from the bytes for every function would fix `tools/fn.py` output for all of them.
