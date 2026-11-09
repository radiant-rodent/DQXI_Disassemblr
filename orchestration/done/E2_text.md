# E2_text — game text / dialogue editor (resumed)

**Status:** complete for the data + editor path (tests green, GUI checked on screen and by
screenshot). No hardware/emulator boot and no manual click-through of every button.

## What existed when this session started

The previous worker had only left the old **read-only translation-database browser**
(`viewer_rs/src/data/dialogues.rs` → `DialogueDb`, `viewer_rs/src/ui/panels/dialogues.rs`): it
opened `..\3DS_Translate\workspace\project.db` with `SQLITE_OPEN_READ_ONLY` and
showed Japanese/English rows plus the PC text. There was **no** `tools/text_tool.py`, no per-bank
text export, no editable path and no done report. `docs/EDITING.md` had no text section.

## What was done

### 1. Where the player-visible text lives

All dialogue/message/UI text is UTF-16LE string blocks inside **BXON** files that are members of
the RomFS PACKs. The BXON root type (header bytes 0x0C..0x20) identifies the bank family; the
record shape differs per family:

| root type | banks | structure |
|---|---:|---|
| `CharacterIEData` | 108 | `root[]` (24 B) → talks (16 B) → variants (12 B) → 28-byte line records (`+0x10` speaker, `+0x14` text) |
| `TextBlock` | 463 | `root[]` {line count, relptr → 28-byte line records, flags} |
| `TalkPartyContent2` | 31 | `root[]` {string count, relptr → string pointers, flags} |
| `BattleText` | 3 | string records |
| `UIText` / `UIMessage` / service / credit / story banks | 187 | root record arrays whose words point at strings or at one nested record level holding them |

**792 banks, 68,316 strings.** `CharacterIEData`/`TextBlock` layouts were verified against the
reference translation tool (`dq11tool/ietalk.py` is read-only in `..\3DS_Translate`)
and against the retail files by making every location round-trip.

### 2. Encoding and control codes

Worked out from the reference `textcodec.py`/`gamefont.py` and re-checked against all 68k
strings:

- `U+0001 base U+0002 reading U+0003` → `{ruby:base|reading}`
- `U+0004 + slot` → message arguments. Slot 1 is the hero/acting character (`{PLAYER}`), 2/3 are
  the battle attacker/target (`{NAME}`, `{TARGET}`), 4 the third combo member (`{PARTY3}`),
  5/6/7 item or skill names (`{ITEM}`, `{ITEM2}`, `{ITEM3}`), 8..F numbers
  (`{NUMBER}`..`{NUMBER8}`). Slots are re-used for different things per message (slot 5 is a skill
  name in one line and a suffix in another), so only 1..3 have a stable meaning. Native
  `SetMessageArg*` functions are the runtime setters.
- `U+000D` → `{CR}` (wait for a button; **not** a line break)
- `U+001F` → `{PAGE}` (another message box; used by NPC talk, split at export)
- `U+0004 0x64 / 0x66` → `{FMT:64}` / `{FMT:66}`. These bracket small-print notes but their
  renderer effect is **not decoded** - named honestly instead of guessed.
- other C0 → `{cXX}`; literal braces → `{{` / `}}`.
- There are **no inline colour codes** in this game. A scan of every string found exactly one
  control byte outside the set above (a TAB in `b_170_cs_090/cs_text.bxon`); colour comes from
  the BFLYT window/pane.

### 3. `tools/text_tool.py`

Commands: `banks`, `export`, `import`, `save-mod`, `verify`, `tags`.

- `export` writes `game_assets/text/index.json` (792 bank metas + family counts),
  one editable JSON per bank under `game_assets/text/banks/<key>.json` (id, offset, role,
  speaker, location, tagged text), `text.csv` (UTF-8 BOM, spreadsheet-friendly) and `INDEX.md`.
  The key of an entry is its **byte offset in the BXON**, which is how the rebuild finds it.
- `import --bank KEY --json FILE` rebuilds one bank; `save-mod` also stages the containing
  `mod/romfs/<pack>.pack` through the existing `tools/export_mod.stage_member` path.
- The rebuild reuses the proven `tools/bxon.Bxon.rebuild` (same-size write, relocation and
  repointing) after proving each raw string survives its legacy writer. **Only pointer positions
  found by the structural walk are trusted**: BXON also has integer fields whose values happen to
  look like string pointers (shop_msg probe: `Bxon` alone would also "repoint" such a field when a
  string grows, corrupting the table). Strings with no trusted pointer can only be edited
  same-size; otherwise the tool refuses instead of writing a guess.
- Growth: a longer string is moved to free space or appended and its real pointers repointed; the
  old block remains as unused padding (BXON has no compaction). The PACK/RomFS layer already
  handles grown members.
- Unknown tags are an error, never literal text. `verify` re-encodes every string of every bank
  and demands a byte-identical file.

### 4. Editor panel (DQXI Studio → Dialogues → “Game text”)

New default tab; the old “Dialogue database (3DS)” and “PC text (official English)” tabs are
untouched.

- Browse by **category, scene, bank key and speaker/role**; bank list shows kind, string count,
  speaker count, font and box width.
- Full-text search in the current bank (text, speaker, location) and across **every bank** with a
  background `SearchWorker` (its own loaded `TextIndex`, so 68k strings never block the UI).
  Clicking a hit jumps to bank + entry.
- Edit box with a tag palette (`{PLAYER}`, `{NAME}`, `{TARGET}`, `{ITEM}`, `{NUMBER}`, `{CR}`,
  `{PAGE}`, `{ruby:|}`) that inserts at the text cursor, plus a full argument-slot reference.
- **Preview** uses the game's own BFFNT font (`game_data/romfs/font/3D14.bffnt` for dialogue,
  `3D12` for menus): every character is advanced by its `CWDH` width, the box is the dialogue
  window's 321 px × 3 lines (bank default, editable), `{PAGE}` starts another simulated box and
  variable arguments are drawn as chips. Glyph shapes come from the system font (the BFFNT
  bitmap sheets are not decoded), but the *layout* is the game's.
- **Warnings**: missing glyphs (with code points), a line wider than the box (with px), more
  lines than the box shows, and >255 UTF-16 units for dialogue (the game copies a message into a
  255-unit buffer; longer text is cut off and the box stays blank).
- **Save to mod** validates tags, writes `build/text_edits/<bank>.json`, then runs
  `python tools/text_tool.py save-mod` on a thread (status/spinner, no UI freeze) and stages
  `mod/romfs/<pack>.pack`. **Revert** restores the exported bank.

### 5. Rust data layer

`viewer_rs/src/data/dialogues.rs` gained:

- a tag codec matching Python (`pieces`, `encode_tagged`, `plain_text`, `tags_of`);
- a **BFFNT parser** (FINF header, CWDH width chain, CMAP direct/table/scan) with per-glyph
  advance and missing-glyph detection. The CWDH `endIndex`/`next` offsets were initially wrong
  (read at +12/+16 instead of +10/+12), which made every font silently fail to parse; caught by
  the screenshot (“0 game fonts”) and fixed, now guarded by a test that requires 3D14 to parse;
- a lazy `TextIndex` over `game_assets/text` (index + fonts up front, bank files on first use,
  full-text search, bank-document builder for the save path).

## Files changed

- `tools/text_tool.py` — new: export/import/save-mod/verify/codec/structure walkers.
- `tests/test_text.py` — new: 10 tests (codec, braces, unknown tags, speakers, nested banks,
  JSON round trip, a grown NPC line, longer nested text, missing offsets, all banks
  byte-identical).
- `viewer_rs/src/data/dialogues.rs` — BFFNT parser, tag codec, `TextIndex`, `TextEntry`,
  `TextBankDoc`, measure/warnings helpers; 6 tests.
- `viewer_rs/src/ui/panels/dialogues.rs` — new Game text tab (filters, search, editor, preview,
  save), while keeping the old tabs; 4 panel tests.
- `docs/EDITING.md` — new “Text and dialogue” section, inventory row, test commands, corrected
  “Not possible yet” note.
- `game_assets/text/` — generated: `index.json`, `INDEX.md`, `text.csv`, 792 bank JSONs (~38 MB).
- `AGENT_LOG.md` — Entry 68.

## Test results (all run in this session)

| Command | Result |
|---|---|
| `python tools/text_tool.py verify` | **792 banks, 68,316 strings re-encoded, 0 failures** |
| `python -m unittest tests.test_text -v` | **10/10 OK** (19.5 s) |
| `python tests/run_all.py` | **216/216 PASS** (Tier 1 70, Tier 2 70, Tier 3 14, Tier 4 62), 105 s |
| `cargo test` (viewer_rs) | **48 passed, 1 ignored, 0 failed** (6 data + 4 panel text tests added) |
| `cargo build --release` | **OK** (pre-existing warnings only) |
| `python tools/verify_project.py` | **OVERALL: PASS** (incl. release editor binary) |
| live app | started on Dialogues; 792 banks / 5 fonts loaded; speaker/location rows and the 321 px preview with `{PLAYER}` chip render as intended (screenshot inspected) |
| save path | same-size `shop_msg` edit staged through the exact `save-mod` call the button makes; `mod/romfs/ui/common_3d.pack` written, then removed to keep the workspace clean |

## Open problems / not verified

- **No hardware or emulator boot.** The save path reuses the proven PACK/RomFS patch layer
  (`export_mod.stage_member`), but a text-edited bank has not been booted in the game. The
  message-buffer limit is a documented engine fact, not something this task tested in-game.
- **No manual click-through.** The window was started and screenshotted; the tags palette, Save
  button and Revert were not clicked by hand. Save was exercised through the same Python entry
  point (`text_tool.py save-mod`) with the same JSON the panel writes.
- **564 of 68,316 strings (0.8%) have no structural location** (`text@0x…`, still editable).
  559 are NPC animal/floating lines such as `ヒヒーン` in a fifth-level structure I did not
  decode; 5 are in `script_message`.
- **`{FMT:64}` / `{FMT:66}`** are kept as readable-but-undecoded formatting switches. Naming them
  `{COLOR:…}` or “small text” would be a guess.
- **Party-chat speaker names are empty**: `talk_content.bxon` carries the utterances, the
  chapter's `talk_party.bxon` holds ids/flags (no strings), and the id→character mapping was not
  decoded.
- **Non-dialogue box widths/line counts are defaults** (3D12, 300 px, 2 lines), not read from the
  BFLYT panes. Dialogue uses the verified 321 px × 3 lines. The box width is editable per bank.
- The preview uses the system font's glyph shapes with BFFNT advances; the reference project's
  translated-font Latin width fixes (`fontimport`) are not applied, so menu Latin widths are the
  Japanese font's widths.
- **Missing glyphs are only warned about**, not added to the font. The Japanese BFFNTs have no
  accented Latin or `♥`/arrows.
- `text.csv` is export-only; import reads the per-bank JSON (documented).
- The search worker keeps a second copy of the 68k entries in memory (~30 MB); acceptable here
  but worth sharing if the index grows.
- Generated `game_assets/text` is ~38 MB and must be regenerated (`export`, ~15 s) after a fresh
  checkout; the viewer tells the user when `index.json` is missing.

## Suggested follow-ups

1. Decode the two formatting switches: find the message renderer's U+0004 handler near
   `Message_SetArg`/`0x006D3EA0` and switch on the slot byte; 0x64/0x66 are the only high values
   used and always wrap a note.
2. Find the fifth-level array that references the 559 unlocated NPC lines (the pointers sit in
   12-byte records `{flags, text, …}` outside the talk tree) and add it to the CharacterIEData
   walker.
3. Map `talk_party.bxon` ids to party members so party chat gets speaker names, like NPC lines.
4. Read the real textbox width/line count per bank from the BFLYT panes (the reference
   `gamefont.py` already has the geometry table) instead of the 3D12/300/2 default.
5. Decode the BFFNT A4/A8 sheets and draw the actual glyph bitmaps in the preview instead of the
   system font (the reference `metrics.sheet_png` shows the tiling).
6. Add text-family counts to `tools/progress.py`/README so the 792 banks show on the progress page.
7. Boot an edited bank on hardware/emulator (Luma LayeredFS) and verify a replaced NPC line and a
   grown string in-game.
