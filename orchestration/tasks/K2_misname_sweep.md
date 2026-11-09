---
lane: argon
after: K1_core_helpers
---

# K2_misname_sweep - find whole families of wrong names with scripts, then fix them

Hand checks showed the first-pass names fail in **families**: one misunderstood callee and every
caller inherits a wrong subsystem (e.g. 14 shop/inventory functions named `Text_Line*`, battle
message queue calls named "effect"/"packet", item walks named "CharSet"). Find the remaining
families systematically and fix them in one overlay.

Owns ONLY: `orchestration/naming/refine/out/R_S02.json`, `tools/research/misname_sweep.py`
(new), `orchestration/naming/FACTS.md` (append), `orchestration/done/K2_misname_sweep.md`,
`AGENT_LOG.md`. Scratch in `out/scratch/K2/`.

## Method

1. Read `orchestration/naming/FACTS.md` and `orchestration/done/R_S01.md` (the first sweep and
   its generator `tools/research/sweep_text_item_misnames.py`).
2. Write `tools/research/misname_sweep.py`: for each fact that pins a helper's meaning (e.g.
   `Item_LookupRecord` = items, `func_0035EB98` = party member, the battle message spawn,
   `Ui_TextFormat_ReleaseSlot` = message args, battle RNG `func_001CA474(+0x4218)`), list the
   functions that call it whose current name's subsystem contradicts it. Print a ranked table
   (function, current name, the fact it contradicts, caller count). Expect false positives
   (a Text function may legitimately format an item name): you judge each one.
3. Fix the true misnames in `R_S02.json` (same entry format as R_S01: address, name, signature,
   summary, confidence, evidence, previous_name, previous_confidence, change="corrected").
   Use `maybe_` below 0.5. Never touch addresses that a later R_ batch output already corrected
   unless you are sure; say so in evidence.
4. Add any newly verified fact to FACTS.md.

## Done when

- `python tools/merge_names.py --check` shows 0 bad entries; merge; `python tools/build.py`
  prints the bit-match PASS.
- Report: the families found (with counts), how many renamed, and the sweep's remaining
  candidates you rejected and why (short).
