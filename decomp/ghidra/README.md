# Readable Native Decompilation (Ghidra)

This directory is the human-readable native-code view. It is generated from the retail
executable with Ghidra's ARMv6 decompiler, not from the old register-level pseudo-C.

| Metric | Value |
|---|---:|
| Entry points | 18,787 |
| Decompiled | 18,748 |
| Covered by a containing function | 38 |
| Unrecovered | 1 |

## Subsystems

| Directory | Functions |
|---|---:|
| `General_Procedures` | 18,518 |
| `Actors_and_Entities` | 115 |
| `UI_and_Message` | 33 |
| `Save_and_Persistence` | 31 |
| `Battle` | 29 |
| `Field_and_World` | 23 |
| `Camera` | 14 |
| `Audio` | 9 |
| `Kernel_and_System` | 7 |
| `IO_and_Files` | 4 |
| `Memory_and_Heaps` | 2 |
| `Input` | 2 |

## How to read a function

1. Search `functions_index.json` or the `by_subsystem` tree by name or address.
2. Open the `.c` file. Ghidra names unknown callees `FUN_<address>`; use the index to resolve them.
3. `dqxi_types.h` supplies the decompiler's `undefined*` types. Real struct recovery is an
   ongoing task; see the function comments and cross-references before assuming a layout.
4. Signatures and address metadata are in `functions.jsonl`; `functions.h` contains prototypes.

## Reproduce

```powershell
analyzeHeadless decomp/ghidra_project DQXI -process code.decompressed.bin -noanalysis \
  -scriptPath tools/ghidra_scripts \
  -postScript ExportDQXI.java . .\decomp\ghidra
python tools/organize_ghidra.py
```

## Known limitation

A small set of entry points could not be turned into Ghidra functions because the retail
binary contains overlapping/jump-table code. They are listed in `functions.jsonl` with
`status` = `missing_function`; the original annotated assembly remains the ground truth
for those addresses.
