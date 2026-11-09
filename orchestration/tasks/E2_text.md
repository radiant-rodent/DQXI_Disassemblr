---
lane: editor
after: E1_tables
---
Add a game text / dialogue editor to DQXI Studio.

Owns: `viewer_rs/src/ui/panels/dialogues.rs`, `viewer_rs/src/data/dialogues.rs`, new
`tools/text_tool.py`, `docs/EDITING.md` (text section).

1. Find where all player-visible text lives (message tables in packs, script strings, UI layouts)
   and its encoding/control codes (colour, player name, waits, choices). Use the existing
   dialogues panel and any notes in `..\3DS_Translate` (read-only; that project
   translated the game, so its tools/notes on text format and font are the best reference).
2. `tools/text_tool.py export|import`: dump every text bank to editable JSON/CSV (id, speaker,
   context, text with control codes as readable tags like `{PLAYER}` `{COLOR:red}`), and rebuild
   banks from edits — unchanged input must rebuild byte-identical (add a test).
3. Editor panel: browse by bank/scene/speaker, full-text search, edit with tag palette, live
   preview rendered with the game's BFFNT font glyph widths and the textbox width; warn on
   missing glyphs and overflowing lines; save into the mod workspace (`mod/romfs/...`).
4. cargo build/test green; tests green; docs updated.
