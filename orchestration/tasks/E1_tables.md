---
lane: editor
after: P0_regen
---
Make game data tables (BXON: items, equipment, monsters, spells/skills, shops, encounters, stats,
experience curves...) fully editable in DQXI Studio with real field names.

Owns: `viewer_rs/src/ui/panels/tables.rs`, `viewer_rs/src/data/tables.rs`, `tools/table_schemas.json`,
`tools/table_edit.py`, `tools/bxon*.py`, `docs/EDITING.md` (tables section).

1. Read docs/EDITING.md, tools/table_edit.py, tools/bxon_struct.py, table_schemas.json,
   the tables panel. List every table family in `game_assets/tables/` and how many have schemas.
2. Extend schemas for the most modding-relevant families first (items, equipment, monsters,
   spells/skills, shops, encounters, party growth): field names, types, enums (cross-reference ids
   to names using the game's text/message data and `tools/monster_names.json`), ranges.
   Verify each schema by checking values across many records make sense.
3. UI: table list grouped by category with search; spreadsheet grid; id fields shown as
   "id — name" dropdowns; per-field tooltips; modified cells highlighted; undo/redo; validation
   (range/type) before save; "Save to mod" writes the patched BXON into the mod workspace
   (`mod/romfs/...`, create the convention if missing and document it) without touching `original/`.
4. Round-trip test: unmodified load → save must be byte-identical for every table (add a test in
   `tests/`); a modified value must re-parse to the new value.
5. `cargo build --release` and `cargo test` in viewer_rs must pass. Update docs.
