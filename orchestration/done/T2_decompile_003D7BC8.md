# T2_decompile_003D7BC8 - the one function Ghidra could not decompile

**Status: done.** `0x003D7BC8` (`maybe_Ui_DiveForm_UpdateCommandList`) now has hand-written C in
`decomp/ghidra/recovered/FUN_003D7BC8_003d7bc8.c`. Coverage is 18,749 / 18,787 decompiled,
38 covered by a containing function, **0 unrecovered**.

## What the function is

Slot 14 of the dive-form handler table at `0x0072C4C8` (the pointer sits at `0x0072C538`; the table
is an array of `{fn, 0}` pairs, so `(0x0072C538 - 0x0072C4C8) / 8 = 14`). It runs once per frame
while the dive form is up:

```
flags = self->f_3770
if (flags & 4)            -> Ui_DiveForm_PopPane(self+0x134); return
if ((flags & 0x142) == 0) -> if (!(flags & 1)) return;
                             Ui_ListWindow_MoveSelection(self+0x5A8, stick x, y, z); return
commandId = func_00654098(self+0x5A8)          // u16 getter on the command list window
<inlined Game_GetWork()>                        // lazy construction of the global work
if (!(work->bitmap[commandId>>5] & (1 << (commandId & 0x1F)))) return
render->f_10 = 1; render->f_14 = commandId; self->f_3778 = 1;
render->f_10 = 1; render->f_49 = 1;
maybe_Ui_DiveForm_PopPanesToHandler(self)
```

The prologue is instruction-for-instruction the same as `maybe_Ui_DiveForm_OnTextInput`
(`0x003D84DC`) and `maybe_Ui_DiveForm_UpdateSelectionVisual` (`0x003D8184`), which is what fixes the
class. The `(flags & 0x142)` test is written as `bic r0,r1,#0xfe00; bics r0,r0,#0xbd` because
`0x142` is not encodable as an ARM modified immediate - the net mask is `0x01FF & 0xFF42 = 0x0142`.

## Why Ghidra failed

Verified facts:

1. **Nothing calls it.** `decomp/xref.json` lists 0 callers; a scan of `asm/text/*.s` finds no
   `bl`/`b` to `0x003D7BC8`. The only reference in the whole image is the data word at
   `0x0072C538` (`asm/rodata/rodata_00725000.s:7507`). Ghidra's auto-analysis therefore had no call
   site to seed a function from, and the seed list entry stayed `missing_function`.
2. **The failure point is `createFunction`, not the decompiler.** `tools/ghidra_scripts/
   DiagnoseMissing.java` is the only writer of `status: unrecovered`, and it reaches that line only
   when `fm.getFunctionContaining(start)` is null, `fm.getFunctionAt(start)` is null, and
   `createFunction(start, null)` returns null after `disassemble(start)`.
3. **The bytes are clean.** All 124 instructions in `0x003D7BC8..0x003D7DB4` decode as valid ARMv6;
   `asm/text/text_003C0048.s` contains no `.short`/`.word`/`.byte` directive in the range. The nine
   words at `0x003D7DB8..0x003D7DD8` are the literal pool, not code. There is **no jump table** and
   **no fall-through** into the next function: the last code instruction is the unconditional
   `b #0x2b1b2c` at `0x003D7DB4`, and the next prologue is at `0x003D7DDC`.

Inference (not proven - I could not run Ghidra, see BLOCKED):

4. The whole sibling family defeats Ghidra's flow analysis. `0x003D7B6C`, `0x003D8184` and
   `0x003D84DC` all decompile to `halt_baddata()` stubs, and `Game_GetWork` (`0x006F20C0`) - which
   contains the same inlined lazy-init block - is truncated at its first `blx std_ConstructArray`
   because Ghidra has `0x00100050` marked `noreturn` (see `orchestration/naming/FACTS.md`). In
   `0x003D7BC8` the `bic`/`bics` idiom guards the only path to the rest of the body, so the body
   Ghidra could compute is the 9-instruction prologue plus the early return; combined with the
   `noreturn` `std_ConstructArray` call, `createFunction` produced no usable body and returned null.
   The task brief suggested "a `muls` followed by a `nop`" as the cause - `muls r4,r0,r4` at
   `0x003D7C5C` is followed by `nop` at `0x003D7C60` and `beq` at `0x003D7C64`, but that is a normal
   flag-setting multiply with a scheduling NOP and it decodes fine, so I do not believe it is the
   cause.

## Branch targets

| Target | Reached from | Meaning |
|---|---|---|
| `0x003D7BEC` | `0x003D7BDC beq` | bit 2 of `+0x3770` clear - continue |
| `0x003D7BE8` | `0x003D7D68 beq`, `0x003D7D9C beq` | common epilogue `pop {r4..ip,pc}` - return |
| `0x003D7D98` | `0x003D7C08 beq` | `(flags & 0x142) == 0` - stick-only path |
| `0x003D7D4C` | `0x003D7C2C beq` | `*0x007BE31C == 0` - work already built |
| `0x003D7D48` | `0x003D7C64 beq` | `work == 0` - store the null pointer, skip construction |

## Callees

| Address | Name used | Role |
|---|---|---|
| `0x006D89DC` | `Ui_DiveForm_PopPane` | pops one page from the stack at `self+0x134` |
| `0x00654098` | `func_00654098` | u16 getter: `*(u16*)(w + (s8)(*(u16*)(w->f_38+0xC)) * 0x10 + 0x7C)` on the widget at `self+0x5A8`; sibling of `0x00654058` (u8 at +0x80) and `0x00654078` (u8 at +0x81). Not an entry point, so it has no name |
| `0x0011FE8C` | `func_0011FE8C` | `min(next_pow2(a), b)` - popcount fast path, then a clz walk. `(0x2FB28, 0x10) -> 0x10` |
| `0x0011CFAC` | `func_0011CFAC` | `__aeabi_uidiv` (unsigned divide) |
| `0x00116AE0` | `func_00116AE0` | `__aeabi_memclr` (zero-fill) |
| `0x00100050` | `std_ConstructArray` | runs a ctor once per element |
| `0x0019244C` | `func_0019244C` | PartyMember ctor (31 x `0x12EC`) |
| `0x001939C0` | `SaveData_PartyContainer_Ctor` | SaveWork ctor at `work+0x24A98`; returns the SaveWork base |
| `0x00105570` | `maybe_Os_ClearThreeWords` | zeroes 3 words, returns the pointer |
| `0x00105534` | `func_00105534` | clears 255 x `0x18` entries (fields +0, +4, +8, +0x10) |
| `0x0010F300` | `func_0010F300` | `{0, 0, 0.0f}` init |
| `0x002B1B2C` | `Ui_ListWindow_MoveSelection` | tail call; reads r1/r2 only, r3 (stick z) is dead |
| `0x003D6C18` | `maybe_Ui_DiveForm_PopPanesToHandler` | tail call |

## Literal pool (`0x003D7DB8..0x003D7DD8`)

| Pool | Value | Meaning |
|---|---|---|
| `0x003D7DB8` | `0x007BE31C` | GameWork "not yet constructed" flag (1 in `.data`) |
| `0x003D7DBC` | `0x007BE320` | `GameWork*` singleton |
| `0x003D7DC0` | `0x00804160` | static GameWork storage, `0x2FB28` bytes |
| `0x003D7DC4` | `0x0002FB28` | GameWork size |
| `0x003D7DC8` | `0x00764B84` | base-class tag written first |
| `0x003D7DCC` | `0x000012EC` | PartyMember stride |
| `0x003D7DD0` | `0x0019244C` | PartyMember ctor |
| `0x003D7DD4` | `0x00105570` | `0x18`-byte entry ctor |
| `0x003D7DD8` | `0x007829B8` | final class tag written last |

## How the inlined `Game_GetWork` was validated

The block at `0x003D7C1C..0x003D7D48` is an inlined copy of `Game_GetWork` (`0x006F20C0`). I checked
it against both the canonical assembly (`asm/text/text_006C0048.s`, `0x006F20C0..0x006F21FC`) and
the already-accepted readable C (`decomp/readable/functions/Game_GetWork_006f20c0.c`): same nine
literals, same call order, same `func_0011FE8C` / `func_0011CFAC` / `func_00116AE0` /
`std_ConstructArray` sequence. The buffer arithmetic also closes exactly: `0x00804160 + 0x2FB28 =
0x00833C88`, and the last field written is at `work+0x2FB23`.

## Files changed

| File | Change |
|---|---|
| `decomp/ghidra/recovered/FUN_003D7BC8_003d7bc8.c` | **new** - hand-written C, 126 lines, CRLF, UTF-8 |
| `decomp/ghidra/missing_result.jsonl` | one row: `unrecovered` -> `recovered`, `name`/`file` added |
| `decomp/ghidra/COVERAGE.md` | Decompiled 18,749, Unrecovered 0 |
| `decomp/ghidra/functions_merged.jsonl` | **derived catalog, one row** - `status: ok` + `file` so `tools/progress.py` reports the new count |
| `decomp/ghidra/functions_index.json` | **derived catalog, one row + two counters** - `decompiled_count` 18,749, `failed_count` 0 |
| `orchestration/done/T2_decompile_003D7BC8.md` | this report |
| `AGENT_LOG.md` | one appended entry |

The two derived catalogs are normally produced by `tools/organize_ghidra.py` (which applies
`missing_result.jsonl`) followed by `tools/merge_names.py`. I edited only the `003d7bc8` row and the
two aggregate counters, so the result is byte-identical to what that regen produces from the updated
`missing_result.jsonl`. Both edits survive a `merge_names.py` run (`merge_jsonl` / `merge_index` only
touch name/signature/summary/confidence/batch). I did **not** run `organize_ghidra.py` because it
rebuilds `functions_merged.jsonl` from `functions.jsonl` and would drop the 18,327 naming proposals
until `merge_names.py` runs again - and seven other workers were writing to those files at the time.

## Test results

- `python3 tools/merge_names.py --check` -> **0 bad proposal entries, 0 unknown addresses**,
  18,327 proposals from 307 batches, all UTF-8. (Full output: 0 bad entries; 22 addresses
  reformatted; 55 name clashes resolved by confidence.)
- `python3 tools/progress.py` -> **exit 0**. Output:
  `progress: native named 77.0% (14,471/18,787), documented 74.8%, assets 85.5%, editor 93.8%,`
  `types 2.53% (globals 83.5%, classes 0.1%, fields 0.0%, locals 0.0%, batches 58/341),`
  `tasks 392/706 done -> progress`. It is a pure-Python generator and does not touch the
  bit-matching build.
- `python3 tools/verify_project.py` -> **not run**. It shells out to the Windows toolchain
  (`tools/verify_model_textures.py`, the ROM hash check) and takes many minutes; this task changed
  no build input. The one check that reads my data is
  `check("native decompiled", dec.get("decompiled_count", 0) >= 18748, ...)`, which now reads
  18,749 and still passes.
- `python tests/run_all.py` -> **not run**, per rule 5: this is a decompilation-documentation task
  that writes one C file and one JSON row; it changes nothing the bit-matching rebuild consumes.
- Strict UTF-8 re-read of every file I wrote: passed.

## Open problems / not verified

- **`work+0x273FC` bitmap is unnamed.** The function tests bit `commandId` there and only proceeds
  when it is set, so it is an "is this command available" test, but no other recovered function
  reads that offset (`grep -l 0x273fc decomp/readable/functions/*.c` -> no hits) and I could not
  identify its owner. Marked `TODO` in the C.
- **`0x00764B84` / `0x007829B8` are opaque class tags.** Both words are `0x00000000` in the retail
  image and nothing else references them, so they behave as unique per-class tags rather than as
  real vtables. The base-then-derived write order is the normal C++ constructor pattern.
- **`SaveData_PartyContainer_Ctor` (`0x001939C0`) is probably misnamed.** It is called on
  `work+0x24A98` (the SaveWork) and its first action is `bl 0x0010998C`, which loads a vtable and
  falls into `SaveData_ResetSaveWork` (`0x00109990`). The existing name is kept because renaming is
  a naming-batch decision, not this task's.
- **`Ui_ListWindow_MoveSelection` is called with three stick bytes but only reads two.** `r3` is
  loaded from `self+0x3774` and never read by the callee (verified: the only `r3` write in
  `0x002B1B2C..0x002B1CC8` is `mov r3, r0` at `0x002B1C3C`). Either the callee's real signature has
  a fourth parameter that this build ignores, or the compiler passed a dead register. Recorded as
  written, not "fixed".
- **`func_00105534(entries)` is emitted twice** with the same argument. That is what the compiler
  produced; I kept both calls.
- **No runtime test.** Nothing here was exercised in Azahar; the C is a reading of the disassembly,
  not a recompiled function.
- **`COVERAGE.md` percentage.** The brief said "18,749 / 99.79 %", but 18,749 / 18,787 = 99.7977 %,
  so I wrote **99.80 %**. 99.79 % is the figure for 18,748.
- **The naming catalog disagrees with this file's name.** `orchestration/naming/refine/scores.jsonl`
  carries `maybe_Ui_DiveForm_UpdateSelectionVisualB` at confidence **0.34** for `0x003D7BC8`
  (batches `R_056` -> `R2_042` -> `R3_068`), and that is the name `functions_merged.jsonl` now
  shows. It was guessed from the neighbours before any body existed - the score record has
  `score: 0`, `callers_conf: 0`, `callees_conf: 0`, `vtable_siblings: 0`, `strings: 0` and
  `readable: decomp/ghidra/functions_index.json`, i.e. no decompiled body. The body recovered
  here does not match `UpdateSelectionVisual`: it reads the command id from the command-list
  window, tests that command against the availability bitmap at `work+0x273FC`, and only then
  dispatches. `maybe_Ui_DiveForm_UpdateCommandList` (the name in the brief and in the C header)
  describes what the code does. I did **not** edit the naming batch - that is a naming decision,
  not this task's - so the two names differ until a naming batch picks this up (follow-up 5).

## Suggested follow-up tasks

1. **`T2b_name_work_bitmap`** - identify the owner of the u32 bitmap at `work+0x273FC` (only
   `0x003D7BC8` and its inlined copies read it) and give it a real name; then replace the `TODO` in
   the recovered C.
2. **`T2c_fix_ghidra_noreturn`** - clear the `noreturn` flag on `0x00100050` (`std_ConstructArray`)
   and `0x00100B74` (`wcslen`) in the Ghidra project and re-export. That single fix would un-truncate
   `Game_GetWork` and a large number of other functions, and would probably let Ghidra create
   `0x003D7BC8` on its own.
3. **`T2d_rename_savework_ctor`** - `0x001939C0` is called on the SaveWork and starts with
   `SaveData_ResetSaveWork`; `SaveData_PartyContainer_Ctor` is likely wrong.
4. **`T2e_diveform_layout`** - the `UiDiveForm` field map in the header of the new C file
   (`+0x134` page stack, `+0x5A8` command list, `+0x3770` flags, `+0x37D4` render object) is
   consistent across six functions now; it is worth promoting into `include/recovered_types.h`.
5. **`T2f_rename_003d7bc8`** - re-score `0x003D7BC8` now that a body exists. The current catalog
   name `maybe_Ui_DiveForm_UpdateSelectionVisualB` (0.34) was guessed from neighbours with no
   body; `maybe_Ui_DiveForm_UpdateCommandList` fits the recovered code. One refine-batch entry.
