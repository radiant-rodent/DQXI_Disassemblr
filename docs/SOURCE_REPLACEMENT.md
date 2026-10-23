# Source Replacement

The project now has a working, bit-verified source-replacement loop for native code.

## Verified proof

`src/replacements/InitBss.c` is a naked C function containing the exact ARM sequence for the CRT
BSS clear. `src/replacements/GetTalkPartyNoIndex.c` is ordinary higher-level C; the build tool links
it at its real address with a `--defsym` for its callee so the `bl` displacement is exact.
Both compile with the xPack ARM GNU toolchain and produce retail bytes at `0x00100024` and
`0x00158874`.

```powershell
python tools/setup_arm_toolchain.ps1   # one-time
python tools/build_c_replacement.py    # compiles + compares
python tools/build.py                  # overlays all verified C replacements
```

Expected:

- `ALL REPLACEMENTS BIT-MATCH`
- `code.bin` SHA-256 `dfcd1b7ad170eab3932abfaa702b694e6673dc0a8744bfc070765cc8c8cc24d8`
- compressed `.code` SHA-256 `ea3d2c02780e7d7406137cc5099e2ccdf9da4a90f48f35f97d59f0a08c298a2f`

`tools/build.py` reads `build/replacement_report.json` and overlays every `ok` replacement at its
address, so a new function needs no manual `build.py` integration.

## How to add the next function

1. Add an entry to `REPLACEMENTS` in `tools/build_c_replacement.py`:
   ```python
   {"name": "MyFunc", "address": 0x..., "size": ..., "source": "src/replacements/MyFunc.c", "output": "myfunc.bin"}
   ```
2. Write the C. For exact instruction reproduction, use `__attribute__((naked))` with the target
   ARM/Thumb sequence; for higher-level C, compile and compare, then adjust types/optimization.
   If the function calls another fixed address, add `"link_text": True` and
   `"defsyms": {"callee": 0x...}` so the relocation resolves to the retail target.
3. Run `python tools/build_c_replacement.py`.
4. Run `python tools/build.py`; it overlays every verified blob automatically and must still
   produce both bit-matching hashes.

## Current scope

`InitBss` (36 bytes), `GetTalkPartyNoIndex` (16 bytes), `GetTalkPartyPageSize` (16 bytes), and `GetTalkPartyYesIndex` (16 bytes) are replaced today. The remaining 18,783
entry points still come from `asm/` plus the Ghidra/clean-C reference trees. This is the correct
incremental path: never let a C edit silently corrupt the retail build.

## Why this matters

This is a real edit/build/verify loop, not a documentation-only promise. A casual developer can
open a small C function, change it, compile it, and see the byte diff immediately. Functions that
are too complex to reproduce instruction-for-instruction can stay in `src/` as readable models
until their replacement is ready.

