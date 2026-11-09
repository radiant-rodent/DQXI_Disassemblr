# Ghidra Export Coverage

- Entry points: **18,787**
- Decompiled: **18,749** (99.80%)
- Covered by a containing decompiled function: **38**
- Unrecovered: **0**

The missing list is retained in `functions.jsonl`. Entries with `covered_by` are addresses
inside a larger recovered function (jump-table/label entry points); the containing function
covers their code. `unrecovered` entries need a second pass.
