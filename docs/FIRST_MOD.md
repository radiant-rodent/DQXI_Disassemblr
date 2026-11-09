# Your first mod in 10 minutes

This walkthrough changes **one item price** and **one line of message text**, exports a Luma3DS
SD-card folder, and boots it in the project's Azahar emulator. Every command below was run on this
machine on 2026-10-26; the output is pasted verbatim (paths shortened where noted).

You need:

- the generated project (`game_data/`, `game_assets/`, `original/`, `build/DQXI.3ds`); if any are
  missing, follow [GETTING_STARTED.md](GETTING_STARTED.md) first;
- Python 3.12 with the packages the tools import (`Pillow`, `numpy`, `capstone`); the extraction and
  conversion steps install/use them, so they are already present in a generated tree;
- for the emulator step: `python -m tools.emu setup --check` must exit 0
  (see [TESTING_EMULATOR.md](TESTING_EMULATOR.md));
- for a real console: a 3DS/2DS with Luma3DS and an SD card.

> **Run commands from the repository root.** The guides use `python -m tools.<name>`; the
> equivalent `python tools/<name>.py` works too.

Time budget: about 4–5 minutes of command time (the 792-bank text scan is the slow part), then
1–2 minutes of emulator boot. The rest is the game's own opening movie.

---

## 0. Check the baseline (30 seconds)

```powershell
python -m tools.verify_project
```

The last lines must say:

```text
[PASS] editor binary: ...\viewer_rs\target\release\viewer_rs.exe
[PASS] C source replacement: ...
OVERALL: PASS -> audit/PROJECT_VERIFICATION.json
```

If this fails, stop here and fix the data tree first
([GETTING_STARTED.md](GETTING_STARTED.md)); an edit made on a broken baseline is not a mod you can
trust.

---

## 1. Change an item price

The item table is `syscmn/item.json` — a BXON table inside `syscmn.pack`. `Medicinal herb` is row 0
and costs 8 gold.

```powershell
python -m tools.table_edit list syscmn/item.json --grep "Medicinal herb"
```

```text
#0     Medicinal herb                            description=仲間ひとりの
ＨＰを３０～回復
使ったらなくなる  icon=i_use_001  id=2332  buy_price=8  sell_price=4  group=39  field_model=65535  battle_model=65535  model_variant=0  upgrade_level=0  attack=0  defence=0
```

Read the field, then write a new value into a **copy**:

```powershell
python -m tools.table_edit get syscmn/item.json "Medicinal herb" buy_price
python -m tools.table_edit set syscmn/item.json "Medicinal herb" buy_price 5 --out build/first_mod/item.bxon
```

```text
8
Medicinal herb: buy_price 8 -> 5  (build\first_mod\item.bxon, same size)
put it back with: python tools/table_edit.py save-mod syscmn/item.json --patched build\first_mod\item.bxon
```

(The tool prints the equivalent direct-file form in its hint; both forms work. The rest of this
guide uses the `-m` form.)

Stage the edited table back into its pack, in the mod workspace:

```powershell
python -m tools.table_edit save-mod syscmn/item.json --patched build/first_mod/item.bxon
```

```text
syscmn.pack rebuilt with item.bxon: 303,280 bytes (retail 303,536) -> mod\romfs\syscmn.pack
export it with: python tools/export_mod.py --target luma   (see docs/REBUILD.md)
```

`mod/romfs/syscmn.pack` is now a complete replacement pack. The table edit is **same-size** (the
value is a `u32`); the pack shrank only because it was recompressed, which the exporter handles.

> **In DQXI Studio:** *Tables* → `syscmn` → `item` → click the `buy_price` cell of row 0, type `5`,
> **Enter**, then **Save to mod**.

---

## 2. Change a line of message text

All player-visible text is in BXON text banks under `game_assets/text/banks/`. For this first mod,
change the prompt the game shows after loading a save: *"Do you want to see the story so far?"*
(`ui/title/title_msg`, entry 22). It is one entry in one bank, so a typo cannot break anything else.

```powershell
python -m tools.text_tool banks --grep title_msg
```

```text
ui/title/title_msg                                   UIMessage               64 strings  [Menu messages]

1 bank(s) shown, 792 text banks in total
  UIMessage                   1
```

It lists the exported bank index; if `game_assets/text/index.json` is missing, run
`python -m tools.text_tool export` once first.

Copy the editable bank, then open the copy in Notepad:

```powershell
python -c "import shutil, os; os.makedirs('build/first_mod', exist_ok=True); shutil.copy2('game_assets/text/banks/ui/title/title_msg.json', 'build/first_mod/title_msg.json')"
notepad build/first_mod/title_msg.json
```

Find `"id": 22` (the entry is also labelled `"row[22].1[2]"`) and change its `"text"` to:

```json
"text": "FIRST MOD OK!\nThe dialogue line is editable."
```

`\n` is a line break in JSON; the game will draw it as a second line inside the message window.

Keep the quotes and the comma. Do not touch the `offset` field — that is how the rebuilder finds
the string. Save the file, then build and stage the bank:

```powershell
python -m tools.text_tool save-mod --bank ui/title/title_msg --json build/first_mod/title_msg.json
```

```text
ui/title/title_msg: 64 strings, 9,682 -> 9,780 bytes
staged title_msg.bxon into ui/title.pack: 1,120,444 bytes (retail 1,121,612)
  -> mod\romfs\ui\title.pack
export it with: python tools/export_mod.py --target luma
```

Both edits are now staged:

```text
mod/romfs/syscmn.pack      the item table
mod/romfs/ui/title.pack    the message bank
```

> **In DQXI Studio:** *Dialogues* → category **Menu messages** → bank `ui/title/title_msg` → select
> `row[22].1[2]`, edit, **Save to mod**. The preview measures the line with the game's own font and
> warns about missing glyphs or an overlong message.

> **NPC dialogue** works exactly the same way. The NPC banks are
> `game_assets/text/banks/param/region/<area>/npc_ie.json`; edit a line, run
> `python -m tools.text_tool save-mod --bank param/region/<area>/npc_ie --json <edited.json>`, and
> the containing `param/region/<area>.pack` is staged. Dialogue lines are limited by the game's
> 255-UTF-16-unit message buffer; keep English edits ASCII (the Japanese font has no `é`/`ñ`/`♥`).

---

## 3. Export for the emulator and for a real 3DS (Luma)

One command produces the SD-card layout and validates every changed pack:

```powershell
python -m tools.export_mod --target luma
```

```text
==============================================================================
 DQXI 3DS mod export
==============================================================================
  note: mod/mod.json is missing; export still works, metadata is empty
Mod: (unnamed)  by (unknown)
Title ID: 0004000000199200
RomFS changes: 2 file(s)
Exporting Luma3DS LayeredFS folder ...
  -> .\out\luma\titles\0004000000199200 (validated)
Report: .\out\EXPORT_REPORT.json
==============================================================================
 EXPORT OK
==============================================================================
```

The `mod.json is missing` line is only a metadata warning; copy `mod/mod.example.json` to
`mod/mod.json` and fill in your name if you want the export report to say who made the mod.

### Play it in the emulator

```powershell
python -m tools.emu boot build/DQXI.3ds --mod out/luma --seconds 150 --shot docs/images/first-mod/boot-title.png
```

Real output from this machine:

```text
ROM:    .\build\DQXI.3ds
mod:    out/luma
output: .\docs\images\first-mod\boot-title.png
emulator started (pid 19656); waiting up to 150s real (game runs ~10-20x)
  t=61.3s real=14.6s screen 400x480 mean=28.7 nonblack=47%
  t=137.0s real=25.2s screen 400x480 mean=95.5 nonblack=47%
  t=279.9s real=35.3s screen 400x480 mean=61.3 nonblack=47%
  t=352.6s real=45.4s screen 400x480 mean=48.3 nonblack=47%
title-screen reached at game t=478.8s (54.6s real; menu strings in the UI heap)
  title text '\u5192\u967a\u306e\u66f8\u3092\u3064\u304f\u308b' in UI heap at 0x33DA0E40
  title text '\u3075\u3063\u304b\u3064\u306e\u3058\u3085\u3082\u3093' in UI heap at 0x33DA0E20
  title text '\u30d7\u30ec\u30bc\u30f3\u30c8\u30b3\u30fc\u30c9\u5165\u529b' in UI heap at 0x33DA0E00
  title text '\u5192\u967a\u3092\u3059\u308b' in UI heap at 0x33D89370
  title text '\u4e2d\u65ad\u3057\u305f\u5192\u967a\u3092\u3059\u308b' in UI heap at 0x33DA0720
screenshot: .\docs\images\first-mod\boot-title.png
```

The game runs 10–20× real time, so the opening movie (~7 game-minutes) takes 40–100 real seconds
depending on how loaded the machine is. That proves the mod is active (Azahar loaded the LayeredFS
overlay) and did not break the boot. The emulator's own log has the direct proof:

```text
LayeredFS replacement file in use for /syscmn.pack
LayeredFS replacement file in use for /ui/title.pack
```

To **play** instead of just checking the title, use the Studio's **Export & Play** panel with the
smoke test off (it adds `--keep-open`), or run the same command with `--keep-open` and drive the
window yourself. Load a save; the recap question now shows your two lines
(`FIRST MOD OK!` / `The dialogue line is editable.`).

If the first boot prints `CRASH: emulator exited` before the title, **run it again once**. Azahar on
this host occasionally exits during start-up (the project's emulator suite retries for the same
reason, see [tests/emu/README.md](../tests/emu/README.md)); a retail boot is the control. The run
above reached the title on its second attempt; the first hung while the E2E suite was writing a
4 GiB image on the same machine. If another worker or another Azahar instance is already running,
the fixed RPC port (`45987`) makes the launch fail; wait for it to exit or set `DQ11_EMUTEST` to
the isolated root `build/emu_test/root` (this is what the run above used while the main root was
busy — the screenshot and packs are identical).

### Put it on a real 3DS / 2DS

1. Copy the **contents** of `out/luma` to the SD-card root, so you end up with
   `SD:/luma/titles/0004000000199200/romfs/syscmn.pack` and `…/ui/title.pack`.
2. Power on holding **SELECT** to open the Luma3DS configuration.
3. Enable **Enable game patching**, press **START**.
4. Launch Dragon Quest XI and load a save.

Unplug the SD card or delete `SD:/luma/titles/0004000000199200` to remove the mod. This project
does not modify `original/` or the cartridge dump; the mod exists only as files under `out/luma`.

> The `out/luma` folder is the **recommended** hardware target because it is small and reversible.
> A rebuilt `.3ds` / `.cia` is available too (`python -m tools.export_mod --target 3ds` / `cia`),
> but those are fakesigned and need CFW with signature patches; see [EXPORT.md](EXPORT.md).

---

## 4. What this proved (and what it did not)

The project's own emulator proof suite exercises the same code paths with assertions, not just a
successful boot. On 2026-10-26:

```text
$ python tests/emu/run_cases.py text
=== text ====================================================================
   shot recap
   shot field
  -> PASS
    [ok] edited line found in the live UI heap (marker; screenshot written)
    [ok] no crash

$ python tests/emu/run_cases.py table
=== table ===================================================================
   shot shop_list
  -> PASS
    [ok] the edited price 1234567 is a live pane string in the shop
    [ok] shop goods list screenshot written
    [ok] no crash
```

The suite uses its own unmistakable markers (`X3 TEXT EDIT OK 2468` and `1234567`) so it can find
them in guest RAM; your edit follows the same tool path. The screenshots are
[the edited message](images/first-mod/dialogue.png) and
[the edited price in the shop](images/emu/table_shop_list.png).

Not proved here:

- **Physical hardware.** No 3DS/2DS was available. The Luma folder layout, title ID, hash checks and
  file formats are the ones the console expects, but only a console run proves your SD card and CFW
  setup.
- **Your own save.** The text proof loads the project's `user_citra` save; the exact message you see
  after loading *your* save depends on which bank and line you edited.
- **Size-changing edits.** This walkthrough changes values and text of the same size or smaller.
  Adding records, objects or vertices is still limited; see
  [EDITING.md § Not possible yet](EDITING.md#not-possible-yet).

---

## Undo / start over

```powershell
python -c "import shutil; shutil.rmtree('mod/romfs', ignore_errors=True)"
python -m tools.export_mod --target luma
```

An empty `mod/romfs` exports a Luma folder with no overrides; the console is back to retail. The
generated `game_assets/` copies are untouched by this guide (the table and bank were edited through
copies in `build/first_mod/`; only the staged packs in `mod/` changed).

---

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `file not found: game_assets/tables/...` | The conversion step was skipped; run `python -m tools.convert_assets --tables` (or `--all`). |
| `romfs.bin` / `DQXI.3ds` missing | Extract the retail dump first: [GETTING_STARTED.md](GETTING_STARTED.md). |
| Emulator: `CRASH: emulator exited` immediately | Start-up flake on this host; rerun once. Retail boot is the control. |
| Emulator: `HANG` after 150 s | The opening movie can be slow on first shader compile; raise `--seconds` or use `--gpu opengl`. |
| Text shows boxes/missing glyphs | The Japanese font lacks accented Latin and many symbols; keep the line ASCII. |
| Price did not change in a shop | Only shops that stock the herb show it; the table value is global. Check the staged pack is in `out/luma/.../romfs/syscmn.pack`. |
| `EXPORT ERROR: new file` | Luma can only **replace** existing RomFS paths. Put the asset in the pack that already holds it; see [EXPORT.md](EXPORT.md). |

Next: [EDITING.md](EDITING.md) for every asset family, [EXPORT.md](EXPORT.md) for `.3ds`/`.cia`,
[PROJECT_TOUR.md](PROJECT_TOUR.md) to read the engine, and
[the progress page](../progress/progress.html) for what is still missing.
