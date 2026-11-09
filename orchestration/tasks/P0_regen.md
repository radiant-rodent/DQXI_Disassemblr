---
lane: regen
---
Regenerate all generated project data (it has been deleted) and prove the pipeline is intact.

Owns: `original/`, `build/`, `decomp/`, `game_assets/`, `game_data/`, `audit/`,
`orchestration/naming/`, new `tools/regen_all.ps1`, new `tools/make_naming_batches.py`.

Steps:
1. Read README.md, docs/REBUILD.md, docs/CODE.md, docs/ASSETS.md and the top of each tool you run.
   Work out the documented command order (extract_rom.py → build/verify → extract_game_data /
   convert_assets / disasm_scripts / map_tool export --all / organize_* ...).
2. Extract `..\3DS_Translate\DQXI.3ds` into `original/` (never modify the source).
3. Rebuild and run the bit-match verification for code.bin and the full .3ds.
4. Ghidra export into `decomp/ghidra/` (README "Re-running the decompiler"). Search the disk for
   `analyzeHeadless.bat` and a JDK. If absent: BLOCKED for this sub-step only; continue. If absent, also
   check whether `decomp/functions` (legacy pseudo-C via tools/decompile_native.py) can be regenerated.
5. Run `tools/readable_c.py` → `decomp/readable/`, `tools/recover_native_names.py`, and every asset
   conversion so `game_assets/*` matches the counts in README.md.
6. Run `python tests/run_all.py` and `python tools/verify_project.py`; fix real breakages in tools
   (not in the checks).
7. Write `tools/make_naming_batches.py`: list every still-unnamed function, group by subsystem and
   call-graph locality into batches of ~150, write `orchestration/naming/batches/N_###.txt`
   (address, size, current readable-C file path per line), and write `orchestration/tasks/N_###.md`
   per batch from the template `orchestration/naming/TEMPLATE.md` (replace `{{BATCH}}`). Run it.
8. Put the working commands, in order, into `tools/regen_all.ps1`. Report counts, test output, blockers.
