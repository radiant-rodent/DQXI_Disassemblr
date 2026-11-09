# Rebuild everything from your own ROM

This repository contains **no game data**. It holds the project's own work: function
names, signatures, summaries, parameter names, struct/global/local types, the
tools that apply them, and the docs. With your own decrypted dump of
*Dragon Quest XI: Echoes of an Elusive Age* (3DS, `CTR-P-BTZJ`, title id
`0004000000199200`) you can regenerate the full disassembly and the named,
readable C.

## What is where

| Path | What it is |
|---|---|
| `symbols.json`, `symbols_recovered.json` | address → name/type/size/description for every known symbol |
| `decomp/ghidra/functions_merged.jsonl` | one row per function: name, signature, summary, confidence, param names, evidence |
| `decomp/ghidra/functions_index.json`, `functions.jsonl` | the function catalogue (no C bodies) |
| `orchestration/naming/out/`, `orchestration/naming/refine/out/` | the raw naming proposals (first pass + refine passes); `tools/merge_names.py` rebuilds everything from these |
| `orchestration/types/out/`, `orchestration/types/merged/` | struct field, global and local-variable names/types; `tools/typedb/apply.py` merges them |
| `include/`, `src/` | recovered headers and hand-written C |
| `backup/rom_hashes.sha256` | SHA-256 of each container part of the reference dump, so you can check your ROM is the same revision |

Not in the repo (all generated from the ROM): `asm/`, `decomp/readable/`, the raw
Ghidra `.c` export, `original/`, `game_data/`, `game_assets/`, `build/`, `out/`.

## Steps

1. Dump the cartridge **decrypted** (GodMode9 → *Dump cart* → `.3ds`).
2. Install Python 3.12 and run `pip install capstone numpy pillow`. Install Ghidra 12.1.x with JDK 21,
   and the ARM toolchain (`powershell -File tools\setup_arm_toolchain.ps1`).
3. Run:

   ```powershell
   powershell -ExecutionPolicy Bypass -File backup\restore_from_rom.ps1 -Rom D:\path\DQXI.3ds
   ```

   The script unpacks the ROM, checks its hashes against `backup/rom_hashes.sha256`,
   rebuilds `asm/` and proves it bit-matches `code.bin`, runs the Ghidra export, puts the
   committed catalogue back, then applies the names (`merge_names.py --refine`) and the types
   (`typedb` + `readable_c.py`). The result is `decomp/readable/`: one named, commented `.c` file per function.
4. Optional: the editable assets and the editor data (~10 GB):
   `powershell -File tools\regen_all.ps1 -SkipGhidra`. That script still looks for the ROM at
   `..\3DS_Translate\DQXI.3ds`, so copy your dump there or edit `$Rom`.

## How this repo is kept up to date

`backup/sync_from_workspace.py` copies an **allowlist** of files from the working folder
into this clone, then commits and pushes. It aborts the whole run if a file has a
game-format extension or magic bytes, sits under a generated folder, or is larger than 45 MB.
Files that are still being written get held back until the next run.

```powershell
python backup\sync_from_workspace.py --dry-run   # preview
python backup\sync_from_workspace.py             # commit + push
```
