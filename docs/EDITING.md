# Editing game assets: one page per kind of change

Every asset family has an editable copy under `game_assets/` and a tool that writes your edit
back into the original game file. You never edit `game_data/` or `original/` by hand.

The general loop is always the same:

1. Find the asset in the viewer (`run_viewer_rs.bat`); its detail panel shows the source file.
2. Edit the standard-format copy (PNG, glTF/OBJ, JSON, WAV, text).
3. Run the write-back tool; it produces a patched game file (most tools keep it **the same
   size**, see the table).
4. Put the patched file back into its pack and a copy of the ROM:
   `python -m tools.patch_asset --pack <pack> --member <file> --replacement <patched>`
   (maps use `python -m tools.patch_game --map <map>`).

The pack and RomFS layer no longer limits size: a member that grows or shrinks makes the PACK
lay its members out afresh, and a PACK that no longer fits its RomFS slot is appended at the end
of the RomFS data with its hash tree and the cartridge layout updated (see
[REBUILD.md](REBUILD.md#files-that-grow)). Compressed packs (`PACA`, e.g. `syscmn.pack` with the
item tables, many map packs) work too: the tools decompress, patch and recompress them.
Files may grow: longer dialogue (`text_grow`) and longer or new table text plus claimed item
rows (`item_new`) are boot-tested in Azahar. New layout panes can be copied from an existing
pane (`layout_tool add-pane`), and an image may be stored at a different size
(`texture_tool --allow-resize`; pane UVs stay retail, so the game scales it) — both are
code-read only, not emulator-proven. Still fixed-size: mesh vertex counts and the item row
count (2875 rows, see [Adding a new item](#adding-a-new-item)).

An unchanged pack must rebuild byte-for-byte; check that promise over any tree with
`python -m tools.pack --limit 200` (or no `--limit` for every pack under `game_data/romfs`).

| You want to change | Edit this | Write back with | Limits | Proven by test |
|---|---|---|---|---|
| A UI image | `game_assets/textures/**.png` | Studio **Replace texture**, or `tools/asset_replace.py replace --family texture` | keep the dimensions; the original pixel format is restored; 2048 px max | `test_every_bflim_format_reencodes_identically`, `test_uncompressed_png_export_replace_is_byte_identical` |
| A model's texture | PNG next to the model | `tools/asset_replace.py replace --family model-texture` | same size; ETC1 is lossy | `test_etc1_texture_encoder_and_bch_replacement`, `test_uncompressed_bch_texture_replacement_is_identical` |
| A model's shape | `.obj` next to the model (Blender) | Studio **Replace model**, or `tools/asset_replace.py replace --family model` | keep vertex/index counts | `test_model_position_patch_roundtrip`, `test_bone_placed_position_patch_lands_where_edited` |
| A model's triangles | `.obj` faces | `--indices` on the same command | keep index count | `test_model_index_patch_roundtrip` |
| A material colour | material index | `tools/model_material.py` | diffuse RGBA | `test_material_diffuse_patch` |
| A menu/screen layout | `game_assets/layouts/**.json` | Studio **Replace layout**, or `tools/asset_replace.py replace --family layout` | pane values, longer text, copied panes (`layout_tool add-pane`) | `test_bflyt_json_rebuild_is_identical`, `test_pane_transform_edit_lands_in_the_binary`, `test_longer_text_grows_the_pane`, `test_added_pane_is_a_sibling_and_leaves_the_rest_alone` |
| A script | `game_assets/scripts/packs/script/<area>/script.decompiled.nut` (readable) or `script.nut` (annotated assembly) | Scripts editor **Save to mod**, or `tools/script_build.py pack` | source compiler covers the decompiler's language subset; assembly listing is bit-exact | `tests/test_script_build.py`, `python -m tools.script_build verify` |
| An item price or model | row + field name, e.g. `"Medicinal herb" buy_price`, or the **Table editor** grid | `tools/table_edit.py set` / table editor **Save to mod** | named fields only (see `tools/table_schemas.json`); unnamed tables are edited by offset | `test_a_modified_value_reparses_to_the_new_value`, `test_every_named_field_round_trips_byte_identically` |
| A dialogue / message line | Game text tab, or `game_assets/text/banks/**.json` | `tools/text_tool.py save-mod` | 255-unit message buffer; missing glyphs are warnings | `test_all_banks_rebuild_byte_identically` |
| Any other table value | offsets from `game_assets/tables/**.json`, or the grid's raw columns | `tools/bxon_patch.py` | same-size values; strings via `Bxon.build_from_json` | `test_table_json_builder_roundtrip`, `test_table_string_roundtrip` |
| Music / sound | `game_assets/audio/**.wav` | Studio **Replace stream**, or `tools/asset_replace.py replace --family audio` | DSP-ADPCM (retail) or PCM16; original channel layout | `test_exported_wav_reencodes_to_the_same_stream_geometry` |
| Object placement in a level | Level Editor (`run_editor.bat`) | **Save to mod** (or Export BXON + `tools/patch_game.py`) | transforms of recovered records | `test_map_noop_patch_roundtrip`, `editor_float_patch_is_bounded_and_exact`, `test_unchanged_project_keeps_level3d_bytes` |
| Native code | `src/replacements/*.c` | `tools/build.py` | function must fit its original size | `tests/test_source_replacement.py` |

## Replacing assets in DQXI Studio

Every asset panel (Textures, Models, Audio, UI layouts) has the same two controls:

- **Export…** copies the editable standard-format file (and its `.meta.json` where present) to
  `build/exports/`. Open that copy in your paint program, Blender or audio editor.
- **Replace + preview** imports the edited file, encodes it back into the **retail 3DS format**,
  shows what the console will actually read (the decoded BFLIM/BCSTM/BCH result, not your PNG/WAV),
  and prints every hardware limit it hits. **Replace + save to mod** additionally stages the
  containing PACK (or the loose BCSTM) in `mod/romfs/` for `tools/export_mod.py`.

The panels never guess silently: a differently sized PNG is **refused** unless you tick
*Scale a differently sized PNG*, and the reason is shown. Repeated replacements refresh the preview
even though the encoded file keeps the same name.

### What each encoder preserves

| Family | Encoded back to | Checks and warnings |
|---|---|---|
| Textures | the BFLIM's original format: RGBA8/RGB8/RGBA5551/RGB565/RGBA4/LA8/LA4/L8/A8/L4/A4, ETC1, ETC1A4 | dimensions, power-of-two padding, 2048 px maximum, VRAM estimate, mip levels (base level only is replaced), lossy ETC1/4-bit formats |
| Model texture | the embedded texture's PICA format (ETC1/ETC1A4/RGB565/RGBA4/L8/LA8/L4/A4/…) | same dimensions, same file size, mip chain stays retail, lossy formats |
| Model geometry | same-size vertex positions or triangle indices in the BCH | vertex/index count and order must not change; bone-placed parts are converted back to bone space |
| Audio | DSP-ADPCM inside the original BCSTM layout (or PCM16 if you choose it) | channel count must match, sample rate is resampled with a warning, loop point/rate are kept, DSP-ADPCM is lossy |
| Layout | BFLYT/BFLAN sections | pane translate/rotate/scale/size, text of any length, new panes copied from existing ones; the archive and pack are rebuilt at the new size |
| Level | same-size float edits in `level3d.bxon` | each offset is range-checked; unchanged projects are byte-identical |

### Command line equivalent

The panels call one tool, so a scripted edit uses the same encoder:

```powershell
python -m tools.asset_replace inspect --family texture --asset arcs/ui/battle_2d/battle_2d/timg/icon_target_2d.png
python -m tools.asset_replace export  --family texture --asset ... --out build/exports
python -m tools.asset_replace replace --family texture --asset ... --file my_icon.png --preview --stage

python -m tools.asset_replace replace --family model  --asset 3d/model/ani00000a_h/ani00000a_h.bch --file edited.obj
python -m tools.asset_replace replace --family model-texture --asset ... --texture ko_b001_wall01 --file wall.png
python -m tools.asset_replace replace --family audio  --asset romfs/sound/str/BGM_B01.dspadpcm.wav --file new.wav --codec dspadpcm
python -m tools.asset_replace replace --family layout --asset arcs/ui/battle_2d/battle_2d/blyt/battle_2d_lw.bflyt.json --file edited.json
python -m tools.asset_replace replace --family map    --asset b001_101a --file editor_projects/b001_101a.json --stage
```

`--preview` writes the decoded result under `build/asset_edits/`; `--stage` writes the changed PACK
into `mod/romfs/` (texture/layout/model/map) or the changed BCSTM itself (audio). The tool prints a
final JSON object, which is what the panels parse. `tools/asset_replace.py` reuses the proven
converters (`texture_tool`, `sarc_tool`, `bch_texture_patch`, `model_patch`, `bcstm_encode`,
`layout_tool`, `patch_game`); it is not a second implementation.

**Layout preview.** The UI layouts panel draws the layout the way the console composes it: pane
hierarchy and anchors, rotation/scale, alpha and the visible flag, each picture's material texture
with its own UVs and vertex colours, window frames, and part panes (embedded sub-layouts) on the
real 400x240 / 320x240 screen. Text is drawn with the game's own BFFNT glyphs (exported by
`python tools/font_tool.py export` to `game_assets/fonts/`; the editor falls back to its own font
when they are missing) at the pane's font size, spacing and alignment. Panes animated in at
runtime are hidden until you tick *Hidden panes*. Not modelled: TEV colour combiners, X/Y
rotation and animations.

**Adding a pane to a layout.** Copy an existing pane under a new name, then edit the copy in the
JSON (move it, change its text) and replace the layout as usual:

```
python tools/layout_tool.py add-pane game_assets/layouts/arcs/ui/battle_2d/battle_2d/blyt/battle_2d_lw.bflyt.json --copy txt_state --name txt_state2 --out edited.json
python -m tools.asset_replace replace --family layout --asset arcs/ui/battle_2d/battle_2d/blyt/battle_2d_lw.bflyt.json --file edited.json
```

The copy is the source pane's next sibling (same parent), keeps its material, and gets no
children (the game finds panes by name, so copied children would clash). No group or animation
lists it, so it is static and always visible. Not yet boot-tested in the emulator.

### Hardware limits the encoder reports

- **Texture size**: the PICA200 accepts at most **2048 x 2048** for a texture. UI atlases are often
  ETC1 (4 bpp) and 256-1024 px; a PNG that would need more VRAM than the map budget is flagged.
- **Power of two**: BFLIM/BCH store power-of-two dimensions, padded at the edge. A non-power-of-two
  texture is padded, so UVs outside `0..1` show the padding. Keep UI dimensions power-of-two.
- **Mip chains**: only the **base** mip is replaced. Higher mips stay retail; a heavily zoomed-out
  model may still show the old image. This is a deliberate same-size limitation.
- **ETC1 / ETC1A4 / 4-bit formats** are lossy; the preview shows the quantised result.
- **Audio**: DSP-ADPCM is 4-bit lossy but keeps the retail streaming size (roughly 1/4 of PCM16).
  A replacement longer than the original enlarges the BCSTM; a Luma LayeredFS file handles that,
  but a strict RomFS same-slot patch does not (use `tools/export_mod.py` for grow-on-3DS builds).
- **DSP-ADPCM encoding time**: the encoder is greedy and takes about 0.5 s per second of stereo
  audio; a five-minute track can take a few minutes. The panel keeps the window responsive and says
  when it is running. Long tracks are not truncated or downsampled silently.

## Finding your way

- **Names:** model and area lists show in-game names (`w1603b` = Flametang boomerang,
  `b001` = Heliodor Castle). They come from the game's own tables; see
  [ASSETS.md](ASSETS.md#in-game-names).
- **What a file is:** `game_assets/<family>/` mirrors `game_data/`, so the path tells you the
  source pack. Model folders hold `.gltf` (use this in Blender), `.obj`, and their PNGs.
- **Faces:** characters' faces are baked from three textures; pick other expressions in the
  viewer or with `tools/face_expressions.py`.
- **Checking your work:** `python tests/run_all.py`, `python -m unittest tests.test_tables`,
  `python -m unittest tests.test_text`, `python -m unittest tests.test_script_build`,
  `python -m tools.verify_project` and `python -m tools.audit_model_textures` should all stay green.

## Renaming table text

Item, monster and skill names and descriptions are editable in DQXI Studio's table editor (double-
click the cell) and from the command line:

```
python tools/table_edit.py set syscmn/item.json 0 name "ちょうやくそう" --out item.bxon
```

The new string is appended to the end of the `.bxon` and only that row's pointer moves, so other
rows that share the old string are untouched and the file grows by a few bytes. Type `
` for a
line break. Furigana markup in the original is not rebuilt; write the plain text. Undo in the editor
drops the appended bytes again. The emulator test `item_new` proves a renamed row shows in the shop.

## Not possible yet

- New meshes or extra vertices: model replacement is same-size (positions or indices).
- Layout panes of a brand-new kind or with children: `add-pane` copies one pane without its
  children. Texture size changes are possible with `texture_tool --allow-resize`, but the
  pane's size and UVs stay as they were.
- More than 2875 items: use the placeholder rows (`table_edit.py add-item`).
- Importing **glTF** geometry back into a BCH: the glTF is the visual/Blender export; geometry
  write-back uses the OBJ (same vertex order as the BCH). glTF files are still exported for
  materials, textures and Blender inspection.
- Editing asset-id strings in tables (icon, model, motion, sound and effect codes): they stay
  read-only, because a code that names a missing asset crashes the game. Display text (item, monster
  and skill names and descriptions) **is** editable; see below.
- Not every table has field names yet. 42 of the 5,929 tables are named (see
  [Tables](#tables)); the rest are still fully editable through raw, typed columns, and naming
  one is a matter of adding an entry to `tools/table_schemas.json`.
- Scripts are editable as readable Squirrel source **and** as an annotated assembly listing (see
  [Scripts](#scripts-events-cutscenes-quests)). The readable path compiles the game's language
  subset; it cannot yet invent new closure captures/genrators/classes, and a from-scratch source
  compile is semantically equal but not byte-equal to retail (the original register allocation and
  debug line table are not recoverable). Use the assembly listing when you need byte-exact output.

## Tables

Every number the game balances with lives in a **BXON** parameter table: item prices, monster
levels, spell power, shop stock, the experience curve. They are all editable, and the same-size
patch rule applies - a saved table keeps its byte length, so it drops straight back into its
PACK and the ROM stays valid.

### Two ways in

1. **The Table editor** (DQXI Studio, `run_editor.bat` or `run_viewer_rs.bat` + Ctrl+7).
   Pick a family in the left list. Tables with field names show a spreadsheet with real column
   headers; the rest show numbered raw columns. Click a cell, type, press Enter. `id` columns open
   an **id - name** dropdown (item names, model codes), `enum` columns a small picker, and every
   header has a tooltip with the offset, the accepted range and the evidence for the name.
   Modified cells are highlighted, Undo/Redo (Ctrl+Z / Ctrl+Y) work per table, **Revert** restores
   the file on disk, and **Save to mod** writes the patch.
2. **The command line**, for scripted edits:

```powershell
python -m tools.table_edit tables                      # families and named-table counts
python -m tools.table_edit fields syscmn/item.json     # columns, types, ranges, evidence
python -m tools.table_edit list syscmn/item.json --grep "Medicinal herb"
python -m tools.table_edit get  syscmn/item.json "Medicinal herb" buy_price
python -m tools.table_edit set  syscmn/item.json "Medicinal herb" buy_price 5 --out build/item.bxon
python -m tools.table_edit save-mod syscmn/item.json --patched build/item.bxon
python -m tools.table_edit verify                      # every named field round-trips
```

### What "Save to mod" writes

`mod/romfs/<pack>.pack` - the whole RomFS pack rebuilt with the edited member, which is the
layout a Luma3DS **LayeredFS** mod expects (`mod/romfs/` is created on the first save). A loose
`.bxon` is never written into `mod/romfs/`,
and `game_data/` and `original/` are never touched. The intermediate patched table goes to
`build/table_edits/<family>/<table>.bxon`, and the staged pack is the same one
`tools/export_mod.py --stage-table` produces. From there:

```powershell
python -m tools.export_mod --target luma --mod mod --out build/mod_export
```

### Which tables have field names

| Family | Table | What is named |
|---|---|---|
| Items | `syscmn/item.json` | name, description, icon, **id**, buy/sell price, display group, field/battle model, model variant |
| Equipment | `syscmn/item.json` | forge **upgrade_level** (+0..+3), **attack**, **defence** - the same rows as items |
| Equipment | `gamecmn/res_motion_equip.json` | animation prefixes (`hnd`, `swd`, `2swd`, `dgr`, `axe`, `stk`, `boo`, `tsw`, `clw`, `spr`, `whp`, `rod`) |
| Monsters | `gamecmn/enemy_base.json` | name, family, level, model code, variant, scale |
| Monsters | `gamecmn/enemy_battle.json` | 32 resistance bytes, motion/effect/sound ids, three tuning floats |
| Spells | `gamecmn/spell.json` | spell family/index, asset code, cast time, power, power ratio, effect % |
| Skills | `gamecmn/battle_act_text.json` | the 937 action/skill names (`かえん斬り`, `メタル斬り`, ...) |
| Skills | `gamecmn/passive_skill.json` | name, description, effect stat (enum: max HP, strength, defence, ...), equipment requirement, magnitude, panel cost |
| Shops | `fieldcmn/shop.json` | 24 item slots (id - name dropdowns), shop name text id |
| Encounters | `gamecmn/encount_table.json` | 11 monster slots per group (**id - name** dropdowns) with level/count, encounter id, battle zone |
| Encounters | `gamecmn/scenario_battle.json` | battle zone of every scripted fight (its monster list is read-only) |
| Party growth | `syscmn/player_param_*.json` (29 files) | **exp_total** (the level curve), HP, MP, eight further stat columns |
| Party growth | `syscmn/player_rate_param.json` | 48 per-character stat growth multipliers (100 = normal, 125/150 = boosted) |
| Party growth | `gamecmn/password_exp_table.json` | rank, experience threshold |
| Reference | `gamecmn/res_model3d.json` | model code, id (the lookup the model columns point at) |

Equipment is not a separate table: weapons, armour and accessories are rows of
`syscmn/item.json`, which is why the model columns, the prices and the attack/defence
values sit in the same record. The four rows that share a weapon or armour name are the
forge's +0, +1, +2 and +3 variants; `upgrade_level` identifies them.

The encounter table is the field spawn table: slot 1 of row 0 is monster id 3 (Slime), and
every non-65535 slot value is a row of `gamecmn/enemy_base.json`, so the editor shows the
monster's name in the dropdown. `scenario_battle` is the other half - the fixed battles
scripts start by id; only its battle background is a scalar, the monster list is nested data.

Every field in `tools/table_schemas.json` carries a `why` (the evidence that identifies it) and a
`confidence`:

- **proven** - checked across many records or against an independent table (item prices against
  the sell/2 rule, monster model codes against `tools/monster_names.json`, shop slots against the
  item ids, model columns through `res_model3d`).
- **inferred** - consistent with the data but not confirmed (the exact meaning of the eight
  remaining level-curve stat columns, the 32 resistance slots' element order, the tuning floats).
  These are named like `stat_08` / `resist_0c` / `float_2c` so nobody mistakes a guess for a fact.

### Adding a name

```json
"syscmn/my_table.json": {
  "title": "My table", "category": "Mine", "type": "MyParam",
  "row_size": 24, "pack": "syscmn.pack", "label": "name", "id": "id",
  "fields": [
    {"name": "name", "offset": 0, "type": "string", "read_only": true, "confidence": "proven",
     "why": "the string the menu prints"}
  ]
}
```

`count` repeats one entry (`"count": 24` for a slot array, numbered `_01.._24`, or `_00.._1f` for
`u8`). `ref` turns a field into an `id - name` dropdown fed by another entry here. `"id": "__row__"`
means the table is keyed by its row index (the monster, shop and encounter tables are addressed
that way by the engine), so the dropdown stores the row number and shows that row's `label`. A
wildcard key under `patterns` covers a whole family (`syscmn/player_param_*.json`). Then run
`python -m tools.table_edit verify`, `python -m unittest tests.test_tables` and
`cd viewer_rs; cargo test`: the round-trip tests rewrite every named field with its own value and
fail if a single byte moves.

### Adding a new item

Use an unused row instead of growing the table. The item table has placeholder rows (`id == 0`).
In DQXI Studio: open any cell of the item you want to copy, then press **Add entry (copy row N)**
in the table toolbar; the status line names the new row (one Ctrl+Z undoes it). From the command
line, `add-item` does the same: it turns the first free row into a copy of an existing item with a
fresh, unused id, then you change its fields as usual:

```powershell
python tools/table_edit.py add-item syscmn/item.json --copy 0 --out build/my_item.bxon
python tools/table_edit.py set syscmn/item.json 1365 buy_price 120 --base build/my_item.bxon --out build/my_item.bxon
python tools/table_edit.py save-mod syscmn/item.json --patched build/my_item.bxon
```

`add-item` prints which row it claimed (use that number in `set`). The new item starts with the
copied item's name, description and icon; a shop record must list its row to sell it. Proven in
Azahar: `python tests/emu/run_cases.py item_new` puts the new row first in a shop and finds its
unique price on screen.

**Why not just add rows?** The engine only accepts an item table whose row count equals a
constant in `code.bin` (`Pack_LoadMasterTables`, word at `0x00120778` = 2875), checks
`item_kana_order.bxon` against the same number, and has a third 2875-row table
(`battlecmn/battle_item.bxon`) plus the value 2875 in 36 places in the code. Those 36 are the
real limit: an item is addressed by its **row index**, not its `id`, and every item function
(`Item_LookupRecord`, `AddItemInPlayer`, `GetItemNumInParty`, the script binds ...) rejects an
index `>= 2875`. Worse, the save data keeps a one-bit-per-item "seen" mask at party `+0x4B30`
that is exactly `0x168` bytes (2880 bits), so more than 2880 items would overwrite the next save
field and break existing saves. Growing the table is therefore not supported
(`tools/bxon_grow.py grow_items` stays as a research tool; its new row renders blank). The 189
placeholder rows are the way to add items. The placeholder path needs none of that.

### Safety inside the 3DS

A number edit never changes a file's length; a text edit or claimed row appends a few bytes,
and `save-mod` / Save to mod rebuild the PACK and the RomFS hash tree around the new size. The editor also refuses values the field cannot hold (`u8` above 255, a price outside
`schema.range`) instead of silently wrapping - a wrapped `u8` is exactly the sort of corruption
that crashes the game on real hardware.


## Text and dialogue

All player-visible dialogue and messages are UTF-16LE strings inside BXON files that are members
of the RomFS PACKs. They are not one format: the BXON root type says what a bank is, and the
string records differ between families. `tools/text_tool.py export` classifies every bank
(792 banks, 68,316 strings in the retail game) and writes an editable copy of each:

| Family | Banks | What it is | Record |
|---|---:|---|---|
| NPC dialogue (`CharacterIEData`) | 108 | `npc_ie.bxon`, `book_ie.bxon`, `ie.bxon` - every NPC/book talk | talks → variants → 28-byte lines (speaker + text) |
| Script messages (`TextBlock`) | 463 | `script_message.bxon`, every cutscene `cs_text.bxon` | blocks of 28-byte lines |
| Party chat (`TalkPartyContent2`) | 31 | `talk_content.bxon` per chapter | utterance → string array |
| Battle text (`BattleText`) | 3 | battle messages and action names | string records |
| UI text / messages (`UIText`, `UIMessage`, shop/church/inn/bank/casino/save-point messages, credits, story guide) | 187 | menus, help, services, staff roll, story recaps | string records, sometimes one level nested |

Text that lives in a **layout pane** (BFLYT) is edited by the Layouts section, and numeric/name
columns of parameter tables by the Table editor. This tool deliberately only rewrites BXON string
blocks, so it cannot damage a table's numeric layout.

### The text format

Every bank string is tagged so the control codes stay visible and editable:

| Raw game code | Tag | Meaning |
|---|---|---|
| U+0001 base U+0002 reading U+0003 | `{ruby:base|reading}` | furigana above the base text |
| U+0004 + slot 1 | `{PLAYER}` | hero's name (in battle: the acting character's name) |
| U+0004 + slot 2 / 3 / 4 | `{NAME}` `{TARGET}` `{PARTY3}` | battle names (attacker, target, third combo member) |
| U+0004 + slot 5 / 6 / 7 | `{ITEM}` `{ITEM2}` `{ITEM3}` | item or skill names ("received X and Y") |
| U+0004 + slot 8..F | `{NUMBER}`..`{NUMBER8}` | numbers: damage, EXP, gold, level, stat values |
| U+000D | `{CR}` | wait for the player to press a button (does **not** break the line) |
| U+001F | `{PAGE}` | start another message box (used by NPC talk; the tool splits the record on export) |
| U+0004 + 0x64 / 0x66 | `{FMT:64}` `{FMT:66}` | formatting switches that bracket small-print notes; their renderer effect is **not** decoded |
| other C0 | `{cXX}` | any remaining control code |
| literal brace | `{{` / `}}` | an actual `{` or `}` |

There are **no inline colour codes** in this game's text: colour comes from the window/layout.
The argument slots are reused for different things in different messages (slot 5 is a skill name
in one line and a suffix in another), so only 1..3 have a stable meaning; the editor names them
and the preview draws each as a chip. `python -m tools.text_tool tags` prints the same table.

### The editor (DQXI Studio → Dialogues → "Game text")

- **Browse** by category, bank key, speaker and role. NPC banks list `talk[i]/variant[j]/line[k]`
  for every line and the speaker's own name string as a separate `speaker` row, so both are
  editable.
- **Search** this bank (text, speaker, location) or **every bank** with the top search box; a
  background worker searches all 68k lines without freezing the window. Click a hit to jump to it.
- **Edit** in the text box; the palette inserts `{PLAYER}`, `{ITEM}`, `{CR}`, `{PAGE}`,
  `{ruby:|}`, ... at the cursor. Unknown tags are refused on save (a typo must not become
  literal text).
- **Preview** is measured with the game's own BFFNT font: each character's advance width comes
  from `game_data/romfs/font/3D14.bffnt` (dialogue) or `3D12` (menus), and the box is the
  dialogue window's 321 px text area (350 px frame minus 10 px margins), three lines. `{PAGE}`
  starts a second simulated message box. The box width is editable per bank (some UI panes are
  narrower), the zoom only affects the drawing, not the measurement.
- **Warnings**: missing glyphs, a line wider than the box, more than three lines in a message,
  and - for dialogue - more than 255 UTF-16 units (the game copies a message into a 255-unit
  buffer; a longer one is cut off and the box shows nothing).
- **Save to mod** writes `build/text_edits/<bank>.json`, rebuilds the bank and stages
  `mod/romfs/<pack>.pack` for LayeredFS. Revert restores the bank as exported.

The game's Japanese fonts have no accented Latin (`é`, `ñ`, `ö`, ...) and no `♥`/arrow glyphs, so
an English edit that uses them shows a missing-glyph warning. That is a warning, not a block: the
reference translation project adds those glyphs to the font at export time, which this editor does
not do yet.

### Command line

```powershell
python -m tools.text_tool export                     # all banks -> game_assets/text (+ text.csv)
python -m tools.text_tool banks --grep npc           # list banks
python -m tools.text_tool tags                       # the tag vocabulary
python -m tools.text_tool import --bank param/region/r001/npc_ie --json edited.json
python -m tools.text_tool save-mod --bank ui/common_3d/shop_msg --json edited.json
python -m tools.text_tool verify                     # every bank must rebuild byte-identically
```

`text.csv` (UTF-8 with BOM) holds the same rows for spreadsheet editing. The JSON key is the
string's **offset inside the BXON**; keep it when you edit, because that is how the rebuild finds
the block. Unchanged text rebuilds the file byte for byte (proven for all 792 banks by
`verify` and `tests/test_text.py`). Longer text is moved to free space or appended, and every
reference found by the structural walk is repointed: the old block stays in the file as unused
padding, and the PACK/RomFS layer relocates the grown file (see
[REBUILD.md](REBUILD.md#files-that-grow)). The message itself is still limited by the game's
255-unit buffer.

Text banks are generated output: run `export` after a fresh checkout (it takes ~15 s and writes
38 MB) or after editing a bank by hand. The viewer says so when `game_assets/text/index.json` is
missing.

### Tests

```powershell
python -m unittest tests.test_text -v   # codec, speakers, nested records, byte-identical rebuild
cd viewer_rs; cargo test text_tests     # BFFNT metrics, tag codec, exported bank files
```

## Scripts (events, cutscenes, quests)

All 769 Squirrel scripts - map events, cutscenes, quest logic, battle setup - live in
`romfs/script/<area>.pack`, one `script.cnut` per pack. They are editable and recompilable in
DQXI Studio (Scripts section) and from the command line.

### Two representations, one pack

| View | File | What it is |
|---|---|---|
| Readable source | `game_assets/scripts/packs/script/<area>/script.decompiled.nut` | The game's own Squirrel 2.2 bytecode decompiled to source; 8,960 functions, 100% structured (no ASM fallback) |
| Annotated assembly | `game_assets/scripts/packs/script/<area>/script.nut` | The disassembly with literals, line table, local slots and jump targets; always bit-exact |

The editor switches between the two with the **Squirrel source / Assembly listing** toggle.
Both are editable; **Compile** (Ctrl+B) builds a `.cnut` and lists errors, **Save to mod**
(Ctrl+S) compiles and rebuilds `mod/romfs/script/<area>.pack` for LayeredFS export.

The source build is incremental: functions whose syntax tree is unchanged are copied
**byte for byte** from the retail script, and only edited functions are compiled. Child
functions are matched by their unique name, so inserting a function does not recompile the
ones after it. That is why saving a script you only looked at produces the retail bytes
exactly. The assembly tier is the
other way round: `sqbin` re-assembles the whole listing and always reproduces the retail bytes.

### The Scripts panel

- Tree by category (Scenarios, Cutscenes, Boss battles, Dungeons, Fields, Tickington, ...) and
  PACK area; the title is the human-readable area name, with the raw pack id beside it.
- Syntax-highlighted editor with line-accurate compiler errors. Click an error to jump to the line.
- **Functions** tab: every event/function in the pack, with parameters. Click to jump.
- **Natives** tab: every native engine function this script calls, with the real registered name,
  address and the summary recovered by the naming passes (`symbols.json` +
  `orchestration/naming/out`).
- **Callers** tab: call sites of the selected function in this script, plus cross-pack callers
  from the generated index.
- The tree and the tabs use `game_assets/scripts/script_index.json`; regenerate it after adding or
  renaming scripts with `python -m tools.script_build index`.

### Command line

```powershell
python -m tools.script_build compile script.decompiled.nut --area a_010 -o build/a_010.cnut
python -m tools.script_build pack    script.decompiled.nut --area a_010 --mod mod
python -m tools.script_build pack    script.nut            --area a_010 --tier asm --mod mod
python -m tools.script_build index                      # editor metadata (functions/natives/xrefs)
python -m tools.script_build verify                     # all 769 scripts, writes audit/SCRIPT_BUILD.md
```

`--tier auto` (the default in the CLI; the editor passes the selected view explicitly) detects the
listing by its `[   0] OPCODE` lines. `--no-reuse` compiles every function from scratch.

### What is proven

`python -m tools.script_build verify` measures the whole corpus in about two minutes:

| Metric | Result |
|---|---|
| Assembly listing rebuilds identical bytes | **769 / 769** |
| Readable source parses and compiles to a valid CNUT | **769 / 769** |
| Unchanged source rebuilds identical bytes | **769 / 769** |
| Compiled source decompiles back to the same program (AST) | **769 / 769** ([audit/SCRIPT_BUILD.md](../audit/SCRIPT_BUILD.md)) |
| From-scratch source compile is byte-identical to retail | 0 / 769 (register allocation and debug line table differ) |

So: an untouched script is bit-identical; an edited one is a valid script that means the same
thing as the edited source, but not necessarily the same register numbers the original compiler
chose. When byte-exact output matters (for example a timing-sensitive cutscene), edit the assembly
listing instead. There is **no** Squirrel compiler for this exact 2.2 bytecode format in
`third_party/` or on the reference workspace - the only Squirrel sources there are 3.2, which emit
different opcodes and a different container - so this is a purpose-built compiler/assembler.

### What a compiled script must satisfy (frame rules)

This VM sizes a call frame from the function's `stacksize` (`stackbase + stacksize`) and never
bounds-checks a register operand. A script that names a register outside its frame does not get a
script error: the pack loads and the scene crashes. Every build is therefore validated
(`script_build.validate_nut`) *before* anything is written, and the pack is refused with the
function, instruction and rule named if:

- a register operand, or any argument slot of a call, is at or above `stacksize`;
- a `CALL` result register is `0xFF`. Stock Squirrel emits that byte when a result is discarded,
  but this VM reads it **unsigned** (255, not -1) and stores the closure/native result — and a
  resumed callee's value — at `STK(stackbase + 255)`, far past the frame. The compiler now puts a
  discarded result in the lowest free temporary (never a live local, never `fn`, so the decompiler
  reads the call as a finished statement); retail has **0 of 190,229** `CALL`s with `0xFF`. This
  was the crash the boot tests found: adding a function and starting it from `OnBeginScene`. See
  the `E3b_script_compiler_fix` done report;
- a literal index, `CLOSURE` prototype index, jump target, local-variable slot or line entry is
  outside its table.

All 8,960 retail functions satisfy these rules, and so does the whole corpus recompiled from
scratch (`verify` still reports 769/769 on both tiers). If some future construct cannot be made
safe, the build stops with `refusing to write a script the VM cannot run: ...` and suggests the
assembly listing for that edit instead.

### The language subset

The compiler handles what the decompiler emits: `local`, assignment and `<-`, `if`/`else`,
`while`, `for`, ternary, `&& || !`, arithmetic/comparison/bitwise operators, `++`/`--`, table and
array literals, closures and table methods, `delegate`, `vargc`/`vargv`. The shipped corpus uses no
`class`, `yield`, `foreach`, `try`/`throw` or closure captures, so those are rejected with a line
number rather than mis-compiled. `$rN` (an unnamed VM register) is always an error.

### Limits and honest gaps

- **Hardware boot: not done.** The save path reuses the same PACK/RomFS layer as tables and text,
  and the unchanged pack rebuild is byte-identical to retail. Both build tiers have booted in
  Azahar and changed behaviour there (source tier: a book message; assembly tier: the shop menu;
  plus the scene-load case in `tests/emu`), but no edited script has run on a physical console.
- The readable compiler is **not** a general Squirrel compiler: edits that need new outer-variable
  captures, generators or classes must use the assembly listing.
- Error messages carry the source line; code generation failures also name the function.
- The tree labels come from `tools/organize_scripts.py` plus explicit names for the system packs.
  A few dozen packs (53) are only known by their code name (`p001`, `f010`, ...); the description
  says so instead of inventing a location.
- Native summaries are joined by address from the naming batches. 460 native script callables are
  known; most still read "Native gameplay engine function" until that address is named.

### Tests

```powershell
python -m unittest tests.test_script_build -v   # both tiers, edits, pack staging, errors
python -m tools.script_build verify             # whole-corpus round-trip measurement
python -m tests.emu --case script_load         # emulator: new function started at scene load
python tests/emu/run_cases.py script_load      # the same edit inside the 8-case proof suite
```

The scene-load case is the regression test for the crash this section's frame rules describe:
it adds a function, starts it from `OnBeginScene`, and asserts that the game reaches the field
and that the event's shop menu is live (labels in the dynamic UI heap), with no crash.

## Example: make Medicinal herbs cheaper

In the editor: Table editor (Ctrl+7) → `syscmn` → `item` → Grid → click the `buy_price` cell of
row 0, type `5`, Enter → **Save to mod**.

Or on the command line:

```powershell
python -m tools.table_edit list syscmn/item.json --grep "Medicinal herb"
python -m tools.table_edit set  syscmn/item.json "Medicinal herb" buy_price 5 --out build/item.bxon
python -m tools.table_edit save-mod syscmn/item.json --patched build/item.bxon
python -m tools.export_mod --target luma --mod mod --out build/mod_export
```



## Level records: duplicate and delete

In the Level Editor, select a node and press **Ctrl+D** to copy it or **Delete** to remove it (or use the toolbar buttons). A copy
shows as `(new)` and can be moved like any node; a deleted node is struck out and can be restored. **Save to mod** writes
`editor_projects/<level>.json` with `edits` (moved values) and `ops` (copies and deletes) and rebuilds `mod/romfs/level3d/<level>.pack`.

How it is written (`tools/level_records.py`): the array that holds the record is copied to the end of `level3d.bxon` with the record
added or removed, the array's count and pointer are rewritten, and a copy deep-copies its child arrays. Nothing else moves.

**Proven in the emulator (Azahar, 3D save, Cobblestone church):**
- an NPC record appended to its own array (the 100-byte records at container +0x1F0) loads and a second figure appears next to the
  original (`out/emu/probe/dup_own_plain_b011/field.png`); moving, turning and re-typing records also works.
- a level file with an extra unreferenced block, or with its actor array moved to the end, loads normally.

**Crashes the game:** duplicating a whole layer *container* (the 1,092-byte record that holds all arrays of a layer). An earlier
version of the tool did that for one-NPC arrays; it now refuses (`refusing to duplicate a whole layer container`).

**Also proven:** the editor's save path for typed property edits (entity id / class) through `asset_replace --stage` and LayeredFS (`out/emu/probe/savepath_b011_108`).

**Not proven yet:** deleting records, duplicating 68- and 120-byte placements, and scripts that address records by index (a delete
shifts the index of later records in that array).

```powershell
python -m tools.level_records --selftest                    # structural checks over every level
python -m unittest tests.test_level_records
python -m tools.emu.level_probe patch ...                   # the emulator check
```
