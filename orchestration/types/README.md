# Type / field / global / local recovery (S0_types_plan)

This directory is the data side of readability pass 2. Pass 1 (`M1_merge_names`) named the
functions; this pass names the **data** those functions operate on.

```
tools/typedb/struct_db.py   ->  structs.json          candidate classes, fields, vtables, sizes
tools/typedb/inventory.py   ->  globals.json          every real data object the code touches
                                locals.json           every local/parameter of every function
tools/typedb/make_batches.py->  batches/{S,G,V}_###.json + orchestration/tasks/{S,G,V}_###.md
S_/G_/V_ workers            ->  out/{S,G,V}_###.json  names + types + confidence + evidence
tools/typedb/apply.py       ->  include/dqxi/*.h      real C structs, extern globals
                                merged/*.json         rename maps for readable_c.py
tools/readable_c.py         ->  decomp/readable/      unit->targetUnit, g_titleState, locals
```

Tasks: `S_###` (classes+fields, ~15 related classes), `G_###` (~80 globals grouped by
subsystem and address), `V_###` (~150 functions, same grouping as the `N_###` batches).
S and G run after `M1_merge_names`; V runs after `M2_types_merge` because it renames tokens in
the typed readable view. `M2_types_merge` and `M3_vars_merge` are the merge tasks.

## Commands

```powershell
python tools/typedb/struct_db.py                 # rebuild structs.json (~2 min)
python tools/typedb/inventory.py                 # rebuild globals.json + locals.json (~4 min)
python tools/typedb/make_batches.py              # regenerate batches + task files
python tools/typedb/apply.py --validate          # check worker answers, no writes to headers
python tools/typedb/apply.py --merge             # write include/dqxi/*.h + merged maps
python tools/typedb/apply.py --merge --demo      # hand-applied sample -> merged_demo/
python tools/readable_c.py                       # regenerate decomp/readable (uses merged/)
```

## Evidence rules

* Nothing here invents a name. `structs.json` records the byte offsets, widths, vtable slots,
  constructor stores, allocation sizes and readable-C lines that prove a layout exists.
* `globals.json` resolves each Ghidra `g_XXXXXXXX` **literal-pool slot** through the retail image
  to the real data address; a literal whose value is not a data address is a number, not a global.
* A worker answer is merged only when its offset/address/token exists in the evidence and its
  type is a real C type. Bad answers are rejected per item with a message in `merged/report.json`.
* Low confidence (< 0.5) is written into the name (`maybe_...`, `maybe_g_...`) and into the
  trailing comment of the generated struct field.

## Current numbers (2026-10-26)

| Item | Count |
|---|---:|
| candidate classes | 1,930 (1,649 with field evidence) |
| field accesses clustered | 26,097 |
| resolved globals | 4,490 |
| functions / variables | 18,737 / 170,492 |
| batches | 151 S, 58 G, 132 V |

`merged_demo/` and `samples/` are the hand-applied illustration for the S0 report; they never
feed the real readable tree.
