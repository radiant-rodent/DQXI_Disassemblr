---
lane: export
---
Find out why the game can't use a grown item table, and make adding items work.

## What the orchestrator proved in the emulator (2026-10-26)

- Same-size edits to `syscmn/item.json` work: the herb's new price 1,234,567 shows in the shop
  (`out/emu/x3/table/run/shop_list.png`).
- `tools/bxon_grow.py` output is structurally sound as far as checked: the BXON header row count
  goes 0xB3B → 0xB3C, the three data pointers after it move by exactly one row (88 bytes), every
  row pointer is verified, and **no** pointer after the array points back into the rows.
- Yet with the table grown by one row (appended at the end, fresh unique id 4000 — retail ids are
  unique, max 3118), the shop's goods list renders **empty** and the owned-count shows `555`
  (`out/emu/x3/table_grow/run/shop_list.png`). This happens **even when the shop lists only
  retail rows** — so growing the table at all breaks item lookups, not just the new row.
- The literal 2875/0xB3B appears in no relevant function in `decomp/readable/`.
- The 71 placeholder rows (`id == 0`, e.g. rows 1365–1368, 2690–2874) are a possible way to add
  items without growing the table.

## Task

Owns: `tools/bxon_grow.py`, `tools/table_edit.py`, `tests/emu/drive.py` (`case_table_grow`),
`docs/EDITING.md` (tables section).

1. Find the code that loads `item.bxon` (start from the BXON loader and the item lookup the shop
   uses — names in `decomp/readable/`, e.g. search `ItemParam`, shop/goods functions). Find what
   depends on the row count or file size: a buffer sized to the retail file, a count cached
   elsewhere (save data / other tables / a hash index built from a different file), or a second
   header field (`0x38`/`0x3C` words) `bxon_grow` doesn't update.
2. Fix `bxon_grow` (or document the needed native patch) so `python tests/emu/run_cases.py
   table_grow` passes: the new row's price `1987654` is live in the shop and nothing crashes.
3. If growth needs a native code change, implement it as a `mod/code` patch that passes
   `tools/check_armv6k.py`, or fall back to **reusing placeholder rows**: add
   `table_edit.py add-item` that claims an `id == 0` row, assigns a fresh unique id and copies a
   template row's fields; prove that path in the emulator instead.
4. Document the supported way to add items in `docs/EDITING.md`.

## Update — orchestrator, later on 2026-10-26 (root cause found, partly fixed)

- **Root cause of the empty list:** `Pack_LoadMasterTables` (0x00120464,
  `decomp/readable/recovered/`) attaches `item.bxon` and `item_kana_order.bxon` only if their BXON
  header count (+0x20) equals the word at **0x00120778** (`0xB3B`). A grown table was silently
  dropped.
- **Implemented:** `tools/bxon_grow.py: grow_items()` grows item.bxon, appends the row to
  item_kana_order.bxon (trailing u16 array) and patches the count word; `tests/emu/fixtures.py:
  stage_item_grow()`; `tools/export_mod.py: stage_member` now builds on the mod's existing copy of
  a pack so two members of one pack can both be edited (this also fixes a modder-facing bug).
- **Result in the emulator:** the shop list renders again (retail goods visible), but the new row
  is blank and the owned count reads 555 — tried ids 4000 and 2700 (unused, in range).
- **Remaining:** `battlecmn/battle_item.bxon` also has 2875 rows; `0xB3B` occurs **36 times** in
  code.bin (0x14f8d0, 0x154be0, 0x154fc0, 0x1561a0, 0x158178, 0x159e20, 0x15b970, 0x18d0c8,
  0x21bffc, 0x2bb750, 0x2c38f8…). Classify each (bound check vs array size vs unrelated), check
  whether the bag/inventory array is in the save layout, and only then patch.
- **Recommended path first:** reusing the 71 `id == 0` placeholder rows avoids all of this. Do
  step 3 (placeholder `add-item`) before attempting full growth.

## Update — placeholder path DONE (orchestrator, 2026-10-26)

`tools/bxon_grow.py: claim_placeholder()` + `python tools/table_edit.py add-item <table> --copy ROW
--out F` add items via `id == 0` rows; emulator case `item_new` PASSES (new row first in the shop,
unique price 1357924 on screen, owned 0, no crash). Documented in docs/EDITING.md "Adding a new
item". Also fixed: `table_edit set/add-item --base` passed the path as the table name. What remains
for this task is only true row growth (the 36 `0xB3B` sites, battle_item.bxon, save layout).

## Closed — orchestrator, 2026-10-26 (all 36 `0xB3B` sites classified)

`tools/research/item_count_sites.py` (pc-relative LDR scan over `original/exefs/code.decompressed.bin`):

- 1 table attach check: `Pack_LoadMasterTables` (header count must equal 2875).
- 27 **row-index bound checks** `cmp idx, #0xB3B; bhs fail`: `Item_LookupRecord`, `AddItemInPlayer`,
  `ChangeEquipedItem`, `GetItemNumInParty`, `AutoAdd/AutoRemoveItemInParty`, `GetCountEquipedItem`,
  `ChangeEquipedAddItem`, `Item_CountEquipped`, `Ui_EquipRow_Update`, `Ui_RecordDetailWindow_UpdateText`,
  text-arg/charset builders (`maybe_Text_*`, `maybe_Ui_TextArg_NextEntry`), `maybe_Data_*`,
  `maybe_Item_FindRewardEntry`, and 8 `Script_Bind_*` item natives. Items are addressed by **row
  index**, not the `id` field — why an appended row (index 2875) renders blank.
- 3 loops over all items reading save data: `maybe_Item_CountStorableItems`,
  `maybe_Item_CountOwnedTypesFromBitmask`, `maybe_Item_ValidateAndCompactStorage` — they use a
  per-item bitmask at party `+0x4B30`, memset to `0x168` bytes (= 2880 bits).
- 1 UI default (`maybe_Ui_Window_CtorWithIconTable` stores 0xB3B as "no item").

**Verdict:** true growth would need all 36 patched *and* the save bitmask relocated (> 2880 rows
breaks existing saves). Not worth it: 189 placeholder rows (`add-item`) cover modding needs.
Documented in docs/EDITING.md. Task closed; `case_table_grow` stays as an expected-fail research case.
