# X5b layout add-pane — done by orchestrator (2026-10-26)

- `tools/layout_tool.py`: `add_pane(doc, source, new_name)` + CLI `add-pane IN --copy P --name N --out OUT
  [--base BFLYT]`. The copy (+ its `usd1`) is inserted after the source's whole `pas1`..`pae1` child
  block, so it is a sibling; children are not copied (name clash). No pane count exists in BFLYT;
  `build_bflyt` recomputes section count / file size. Groups, `cnt1`, animations don't list it.
- `layout_tool.complete(doc, original)`: guard for a JSON without `raw_sections` (would have built a
  header-only file); `asset_replace.replace_layout` uses it. All 4,394 shipped JSONs have raw sections.
- Tests: `test_added_pane_is_a_sibling_and_leaves_the_rest_alone`, `test_exported_json_without_raw_sections_rebuilds_identically`,
  `test_longer_text_grows_the_pane` (replaces the stale "text that does not fit is refused").
- Manual: battle_2d_lw add txt_state2 → asset_replace OK, 3,652 → 3,844 bytes.
- NOT verified: the added pane in the emulator / on hardware.
