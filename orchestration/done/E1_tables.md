# E1_tables — schema-driven BXON table editor (resumed)

**Status:** complete (data + editor paths tested; GUI not clicked through by hand)

## What was already there when this session started

The previous worker had built most of the feature: `tools/table_edit.py`, a
`tools/table_schemas.json` with 7 exact schemas plus the `player_param_*` pattern (36 named
tables), the Table editor panel (`viewer_rs/src/ui/panels/tables.rs`) with grouped/filterable
list, spreadsheet grid, reference dropdowns, tooltips, dirty highlighting, undo/redo and
**Save to mod**, and most of `docs/EDITING.md`. Two things were broken or missing:

1. `tests/test_asset_roundtrip.py` called `Table.value()`, `Table.set()` and `Table.address()`,
   but `tools/table_edit.py` no longer exposed them - both table tests errored.
2. The required "every table round-trips byte-identically" test did not exist, and the schemas
   still had no skills, encounters, equipment stats or stat-growth coverage.

## What this session did

### 1. Table inventory

`game_assets/tables/packs` holds **5,929** converted tables in 12 families:
2d 181, 3d 1,019, battlecmn 23, divecmn 8, fieldcmn 55, gamecmn 140, level2d 2,392,
level3d 1,196, param 600, script 56, syscmn 63, ui 196. Before: 36 had field names.
Now: **42** (13 explicit entries + the 29 matched by `syscmn/player_param_*.json`).

### 2. Schemas extended (all values checked across every record)

Added to `syscmn/item.json` (equipment lives in the item table):

- `upgrade_level` u8 @0x10 - proven: every equipment group of four rows is 0,1,2,3 and its
  stats rise with it (stone sword attack 8/10/14/21; leather armour defence 11/12/14/17).
- `attack` u16 @0x2A - proven against known weapons: stone sword 8, copper sword 13,
  iron sword 20, steel sword 35, hero's sword 109 (max 353).
- `defence` u8 @0x2C - proven against known armour: leather 11..17, cape 60, general's cape 86
  (max 188).

New tables:

- `gamecmn/encount_table.json` (encounters, 3,545 x 96): 11 monster slots, each with
  `monster_NN` (u16, `id - name` dropdown into `enemy_base`, 65535 = empty), `level_NN`
  (u8, 1..8) and `count_NN` (u8, 1..8), plus `encounter_id` (sequential/unique) and
  `battle_zone`. Verified every non-empty slot is a real enemy row; row 0 slot 1 is
  monster 3 (Slime) and the row reads as a plausible early-game group.
- `gamecmn/passive_skill.json` (skills, 232 x 16): `name`, `description`, `effect_id`
  (35-value enum decoded from the row's own text: 0 max HP, 2 strength, 3 defence,
  7 attack power, 20 zone rate, ...), `equipment_requirement`, `effect_value`, `effect_flag`,
  `cost`.
- `gamecmn/battle_act_text.json` (937 skill/action names): `name` = `かえん斬り`,
  `メタル斬り`, `ドラゴン斬り`, ... (row index is the action id).
- `gamecmn/scenario_battle.json` (312 scripted battles): read-only `monster_count` and the
  editable `battle_zone` @0x26, confirmed by the reference workspace's
  `dq11tool/battleparam.py`.
- `gamecmn/res_motion_equip.json` (equipment motion prefixes): `hnd`, `swd`, `2swd`, `dgr`,
  `axe`, `stk`, `boo`, `tsw`, `clw`, `spr`, `whp`, `rod`.
- `syscmn/player_rate_param.json` (party stats, 31 x 52): 48 one-byte growth multipliers
  (100 = normal, 50/75/125/150 on specialised characters); the stat order is not decoded, so
  the fields keep their byte index (`stat_rate_00..2f`).

Fixed three pre-existing schemas that did not match the data (caught by the new range test):

- `enemy_base.variant` was read as u16; it is a u8 at +0x14 (values 0..7 = a..h), with a
  separate 0..2 byte at +0x15.
- `enemy_battle` tuning floats can be negative (-12.0 saw a range violation); range is now
  -1000..1000.
- `spell.effect_percent` is signed with a -1 sentinel (was u32 4294967295); now s32 with
  range -1..255.

### 3. `id` fields that are really row numbers

`enemy_base` (and the encounter/shop families generally) are keyed by row index, not by a
column. A schema can now say `"id": "__row__"`. Python `Table.id_of` and Rust
`TableDoc::id_of` / `reference_options` map that to the row, so the encounter dropdown shows
`3 — スライム` while the encoder still stores the row number. This also fixed the old
fallback that picked the first numeric column (`family_id`) for tables with no id.

### 4. Editor hardening

- Added `TableDoc::validation_error()` and call it at the start of **Save to mod**; a dirty cell
  outside its declared range now aborts the save instead of being written.
- Table list opens sorted by category, so the 5,929-table list is grouped by family.
- Restored `Table.value()/set()/address()` in `tools/table_edit.py` (validate before write,
  exact byte address) so the existing editor tests pass again.

### 5. Round-trip test (new)

`tests/test_tables.py` (8 tests):

- every one of the 5,929 tables loads and saves byte-identically, with evenly spaced rows and
  no row past EOF, and survives a word write/restore cycle through the same writer the grid uses;
- every named numeric field in all 42 named tables rewrites its own value byte-identically
  (235,769 writes);
- a real edit (`buy_price` 8 -> 5) keeps the file size and re-parses to 5; bad range/text is
  refused;
- all declared schema ranges hold for every record of every named table (this is what found
  the three broken ranges above);
- targeted checks: known weapon/armour stats, encounter slots are real monster rows, passive
  skill effect text, skill-name table.

`docs/EDITING.md` is updated: the 42-table list, the new families, the equipment/encounter
explanation, `__row__`, `mod/romfs/` creation, and the new test command.

## Files changed

- `tools/table_schemas.json` - 6 new tables, item equipment fields, 3 range/type fixes,
  `enemy_base.id = "__row__"`.
- `tools/table_edit.py` - `value()` / `set()` / `address()` helpers, `__row__` id handling.
- `viewer_rs/src/data/tables.rs` - row-keyed reference ids, `validation_error()`, 5 new tests
  (four data tests + dropdown-name test).
- `viewer_rs/src/ui/panels/tables.rs` - save validation gate, category-first default sort.
- `tests/test_tables.py` - new round-trip/schema suite.
- `docs/EDITING.md` - tables section.
- `AGENT_LOG.md` - Entry 57 (the earlier E1_tables work is Entry 50).

## Test results (all run in this session)

| Command | Result |
|---|---|
| `python tests/run_all.py` | **216/216 pass** (Tier 1 70, Tier 2 70, Tier 3 14, Tier 4 62), 108.6 s |
| `python -m unittest tests.test_tables -v` | **8/8 OK** (8.3 s) |
| `python tools/table_edit.py verify` | **42 tables, 235,769 field writes, 0 failures** |
| `cargo test` (viewer_rs) | **38 passed, 1 ignored, 0 failed** |
| `cargo build --release` (viewer_rs) | **OK** (warnings only, pre-existing dead-code) |
| `python tools/verify_project.py` | **OVERALL: PASS** |
| Tier 4 scenario 10 (table editor) | **13/13 OK** |
| live `table_edit.py set` + `save-mod` | herb 8 -> 5 landed in `mod/romfs/syscmn.pack`; no loose `.bxon` in `mod/romfs/`; demo pack removed afterwards |

## Open problems / not verified

- **No manual GUI pass.** The Table editor was compiled and its data layer is unit-tested, but
  nobody clicked the grid, dropdowns or Save button in a running window. `Save to mod` was
  exercised through the same Python entry point the button calls.
- **Encounter slot layout is inferred structurally.** The 11 slot starts (six 10-byte records
  then five 6-byte records) came from the fixed marker bytes and were validated by every slot
  being a valid enemy id with level/count 1..8. The spare bytes after level/count (spawn flags /
  weights?) and the exact meaning of `battle_zone` (17 values) are not decoded.
- **`scenario_battle` monster lists are read-only**: they are nested arrays and a length change
  would need a BXON re-serialiser, which the editor does not have.
- **`gamecmn/skill_param.json` (active skill power, 202 x 776) is still unnamed.** It is an
  all-float parameter blob with no strings; only its action-name table is named. Same for
  `gamecmn/recipe.json` (nested arrays) and `gamecmn/enemy_category.json`.
- **`player_rate_param` stat order** is not decoded; the 48 multipliers are exposed by byte
  index, not as HP/MP/strength/....
- No console or emulator boot test; tables keep their byte length, so the PACK/RomFS argument is
  the same one proven by the existing patched-ROM tests.

## Suggested follow-ups

1. Decode the four spare bytes of each 10-byte encounter slot (spawn weight/flag) and the
   `battle_zone` value list; then the encounter editor can explain what each slot does.
2. Add a semantic BXON writer so nested-array tables (`scenario_battle` monster lists,
   `recipe` ingredients, `player_spell` learnsets) can be edited, not just scalar fields.
3. Name `gamecmn/skill_param.json` by matching its row ids against `battle_act_text` and the
   `skill`/spell data; the 776-byte row needs the battle code to confirm the float meanings.
4. Give the effect byte in `passive_skill` (0..10 on equipment passives) a name by comparing it
   with the equipment category in `res_motion_equip`.
