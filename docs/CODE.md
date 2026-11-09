# Reading and changing native code

## The four trees

| Tree | Status | Use it for |
|---|---|---|
| `asm/` | complete, bit-matching | the canonical instruction stream and the safe fallback |
| `decomp/readable/` | **the human-facing source**: 18,737 `.c` files with names, summaries and evidence | reading the engine, finding a function to change |
| `decomp/ghidra/` | raw Ghidra export (one `.c` per entry point) + the function catalogue | tracing decompiler output, regenerating the readable tree |
| `decomp/functions/` | legacy register-level pseudo-C | comparison only; not the readable source |

The assembly tree reassembles to the retail `code.bin` with 0 differences:

```powershell
python -m tools.build
```

```
  [PASS] Reconstructed code.bin bit-matches original uncompressed code.bin (0 differences)!
```

That check is the gate for every native-code change in this project. Do not weaken it.

## The readable tree

`decomp/readable/functions/` (18,151 files) and `decomp/readable/recovered/` (586) are generated
from the raw Ghidra export plus the merged naming proposals. Every file starts with a doc comment:

```c
/*
 * Battle_Update - Main per-frame battle update: clears finished command objects, runs the
 * queued action processing, executes the AI pass …, and advances the phase/action counters.
 * Recovered: N_039, confidence 0.55, address 0x0016E3E0 (arm, 636 bytes).
 * Signature: void Battle_Update(BattleManager* self)
 * Evidence: …
 */
```

- **`maybe_` prefix = confidence below 0.50.** Read the evidence, not the name, until the body
  agrees.
- 18,787 entry points, 18,748 decompiled, **8,492 named (45.2%)**, 8,074 documented. Live numbers
  are on the [progress page](../progress/progress.html).
- `symbols.json` is the address → name/signature/summary/confidence catalogue (18,804 entries);
  `symbols_recovered.json` is the function subset with mode and size.
- `decomp/ghidra/functions_index.json` and `functions_merged.jsonl` are what DQXI Studio's Code
  section and most tooling read.

The readable tree is regenerated with:

```powershell
python -m tools.merge_names           # validate proposals -> symbols -> decomp/readable
python -m tools.merge_names --check   # validate only
python -m tools.readable_c            # rewrite decomp/readable from the existing catalogue
```

`readable_c.py` also prints the noise counts (`--stats`) that the merge reports: placeholder
types, unresolved callees and pointer-arithmetic fields should go *down*, not up, after a naming
batch.

## Finding your way around

1. **Know the area.** [Project tour §3](PROJECT_TOUR.md#3-which-subsystem-is-which) maps name
   prefixes (`Ui_`, `Battle_`, `Field_`, `Script_`, `Fs_`, …) and address ranges to subsystems.
2. **Search the catalogue.** `symbols.json` is plain JSON (address → name, signature, summary,
   confidence); DQXI Studio's **Search** section queries it together with assets and text.
3. **Open the file** under `decomp/readable/functions/` or `recovered/`. The header names the
   callees; follow those links rather than jumping into disassembly first.
4. **Check the bytes** when the C looks wrong. `python -m tools.disasm --help` prints the
   instruction listing; `asm/` has the commented, address-labelled source of the same range.
5. **Structs are hypotheses.** `include/recovered_types.h` declares 992 opaque types with no field
   layouts yet. `include/dqxi.h` adds presentation typedefs. A field offset is only real when call
   sites agree on it.

## Raw Ghidra export

The decompiler ran on a raw ARMv6 import:

- binary: `original/exefs/code.decompressed.bin`
- base: `0x00100000`
- language: `ARM:LE:32:v6`, `BinaryLoader`
- function seeds: `decomp/function_seed.tsv` (18,787 entry points with ARM/Thumb mode)
- project: `decomp/ghidra_project/DQXI`

`tools/ghidra_scripts/ExportDQXI.java` creates missing functions, sets Thumb mode where needed,
decompiles, and writes one `.c` per function. `tools/ghidra_scripts/DiagnoseMissing.java` recovers
entry points that overlap an existing body. Coverage details (18,748 decompiled, 38 covered by a
containing function, 1 unresolved at `0x003D7BC8`) are in `decomp/ghidra/COVERAGE.md`, regenerated
by `python -m tools.organize_ghidra`.

`python -m tools.check_ghidra_c --sample 100` compiles a random sample against the presentation
header. Failures are expected and useful: they expose decompiler artifacts (undeclared `DAT_`
globals, mismatched signatures, vector helpers). This is a reading tree, not a buildable target
yet; functions move from reading to buildable one at a time (below).

## Changing a function

Two paths, both under the bit-matching gate:

1. **Verified C replacement (recommended).** Write the function in clean C under
   `src/replacements/`, compile it with the ARMv6K toolchain and assert the bytes are identical to
   retail, then let `tools.build` splice the fragment into the assembly. Four functions are
   verified this way today (`InitBss`, `GetTalkPartyNoIndex`, `GetTalkPartyPageSize`,
   `GetTalkPartyYesIndex`). Step-by-step: [SOURCE_REPLACEMENT.md](SOURCE_REPLACEMENT.md).
2. **Assembly edit.** Change `asm/` directly and run `python -m tools.build`. This is the
   byte-exact path the emulator/IPS proofs use. For anything exported, keep the code
   ARMv6K/VFPv2-only: `python -m tools.check_armv6k` scans the changed words and the exporter
   refuses a patch that would crash on real hardware.

`src/` also holds 19 hand-oriented subsystem models (memory, save, UI, battle, field, audio,
graphics, kernel, input). They are readable explanations, not yet the canonical build source; see
`src/README.md`.
