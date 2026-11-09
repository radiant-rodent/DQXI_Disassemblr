---
lane: editor
after: E2_text
---
Make Squirrel game scripts (events, cutscenes, quests) editable and recompilable from DQXI Studio.

Owns: `viewer_rs/src/ui/panels/scripts.rs`, `viewer_rs/src/data/scripts.rs`, `tools/sqbin.py`,
`tools/squirrel_decompile.py`, `tools/disasm_scripts.py`, new `tools/script_build.py`, docs.

1. Read audit/SCRIPT_DECOMPILE.md and the script tools. Measure: how many of the 769 CNUT scripts
   decompile to `.nut` source that recompiles (with the matching Squirrel version/bytecode format)
   to identical bytecode. Find whether a Squirrel compiler for this exact version exists in
   `third_party/`; if not, write a Python assembler from the readable disassembly to CNUT.
2. Two editing levels: (a) readable `.nut` source when it round-trips, (b) annotated assembly
   (always works). `tools/script_build.py` builds either back to CNUT and repacks into the pack
   file in the mod workspace. Round-trip test over all scripts (identical bytes when unchanged).
3. Panel: script tree by area/event, syntax-highlighted editor, list of native calls with their
   names/summaries (from symbols + `orchestration/naming/out`), cross-references (who calls this
   script function), compile button with error list, save to mod workspace.
4. cargo build/test green; tests green; docs updated.
