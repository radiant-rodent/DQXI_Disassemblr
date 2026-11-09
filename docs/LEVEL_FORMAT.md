# level3d.bxon: what is known (work in progress, task CL1)

Status: **partly decoded**. This page records only what has evidence behind it, and how the rest will be found.

## Container

Every one of the 1,196 levels is the same BXON type, `Level3DBin` (type hash `0x43E8AB3A`; neither the name nor
the hash appears in `code.bin`, so the engine reaches fields by fixed offset, not by name).

```
root (1 record, 64 bytes)
 +0x00  array[40]   (814 levels)          +0x38  array[16]  (822 levels)   <- one entry per "layer"
 +0x0C  array[12]   (157 levels)                   +0x04  array[1092]       <- the CONTAINER (5,873 across all levels)
 +0x14  array[12]   (220 levels)
```

The container is a 1,092-byte record made almost entirely of array descriptors (count, pointer) at fixed
offsets. 300 distinct array paths exist in the whole game (`build/level_array_inventory.json`,
`python tools/level_inventory.py`). The ones present in most levels:

| container offset | element | levels | records | first reading |
|---|---|---|---|---|
| +0x188 | 96 B | 797 | 3,179 | a wrapper that owns a 68-byte record (+0x00), a 4-byte array (+0x18), sometimes 36 B (+0x08) |
| +0x188 / +0x00 | 68 B | 752 | 2,988 | position (+0x00), a duplicate position (+0x0C), size (+0x30), type word at +0x3C (`0x40404003` is the common value) |
| +0x1B8 | 48 B | 807 | 3,487 | owns a 4-byte array |
| +0x68 | 24 B | 777 | 1,777 | small records |
| +0x1F0 | 100 B | 516 | 6,124 | **actor placements** (see below) |
| +0x230, +0x290 | 100 B / 68 B | 304 / 307 | | other placement-like records |
| +0x240 | 108 B | 296 | 1,277 | placement-like |
| +0x248 | 120 B | 178 | 512 | transform: position (+0x00), scale (+0x18), rotation (+0x60) |
| +0x3B8 | 32 B | 222 | 8,454 | many small float points (x, y, z, flag) |
| +0x3C8 | 48 B | 223 | 7,015 | many instances: position, scale, orientation |

## Evidence so far

* **100-byte actor placement (container +0x1F0).** The engine spawns objects from these through
  `Field_ActorGimmick_InitFromRecord` / `Field_SpawnObjectRecordB` (decomp/readable/functions): position at
  record +0x20 / +0x24 / +0x28, Euler rotation at +0x2C..+0x34 (only Y is normally used), a talk-balloon height at
  +0x44 (non-zero enables a balloon lookup), flag bytes at +0x56, +0x57, +0x5A, +0x5E (0xFFFF = none). In
  `b001_101a` the four records at 0x2060, 0x2A84, 0x2AE8 and 0x3040 have sensible positions and facings (1.57, 3.14,
  -1.57 rad) and look like the town's people; their +0x5C words (`0x300_00E0`, `0x300_006C`, `0x300_006D`) differ per
  character and are probably a model / character id.
* **Scripts address actors by number**: `GetActorID(n)` (7,391 uses, e.g. `GetActorID(15)`, `(16)`, `(9)`) and gimmicks by
  `GetGimmickActorID(n)` (1,455 uses, e.g. door 75..79). The number is a field of these records; which one is not yet pinned.
* **Warps** are triggers that fire `TrgMapJumpEvent(map_id, locator, jump_type, fade_time)`; `map_id` is the row index of
  `syscmn/level_map.json`. Which level record carries the trigger is **not found yet**.
* Pointer scheme and growth: `tools/level_records.py` (arrays are rewritten at the end of the file; 3,789 / 3,789 operations verified).
* The decompiled spawner `Field_Scene_InitObjectTable` builds the runtime table from a *descriptor* at work+0xE50/0xE54, so
  the BXON is converted to an in-memory descriptor first; the loader that does that is the next function to read.

## Confirmed in the emulator

Method: `tools/emu/level_probe.py` stages edited level files as a LayeredFS mod, boots Azahar with the 3D save
(`user_citra_3d`, the church in Cobblestone, `b011_*` levels) and screenshots the field (`out/emu/probe/<name>/field.png`).

| change | result | meaning |
|---|---|---|
| +π to the float at +0x30 of every 100-byte record at container +0x1F0, in all 52 `b011` levels | the priest in the church turned his back to the camera (`out/emu/probe/actors_turn_b011/field.png`) | **+0x1F0[100] are NPC placements and +0x30 is their facing (rotation about the vertical axis)**; the Cobblestone scene is built from the `b011_*` level3d files; a patched level reaches the game through the normal pack/LayeredFS path |

| every actor: X position (+0x20) +2.0 **and** the word at +0x5C set to `0x0300006C`, all 52 `b011` levels | the church's people turned into giant purple spiders (monsters) standing about two units to one side; the dialogue box scene changed (`out/emu/probe/actors_moveandmodel_b011/field.png`) | **+0x20 is the X position; +0x5C chooses what the actor is** (model and entity). Id 0x6C (108) is a monster, so NPCs and field monsters share this record and the id picks which |

`+0x5C` across all 1,196 levels: `(class << 16) | id`. Classes seen: `0x300` (3,968 records), `0x100` (1,076), `0x200` (1,067), `0x301` (14).
The low ids with the most uses are 15 (76), 16 (74), 25, 32, 35, 29 ... and the scripts call `GetActorID(15)` / `GetActorID(16)` for
"man" / "woman" in `a_010`, so the id is also the number scripts use to find the actor. `0x100` and `0x200` appear in near-equal counts only in `b`
levels (possibly day / night or story-state variants). Other words: `+0x58` is mostly `0x00FF0000` (4,083), `0x00FF0200` (557), `0x00070000`;
`+0x54` mostly `0x00010000`; the byte at `+0x5A` is the 0xFF "none" marker the spawner tests.

### The editor's save path, end to end

`python`-built project files in the editor's format (typed `u16` edits of `entity id` / `entity class` for every actor, 52 `b011` levels,
1,316 edits) were staged with `tools/asset_replace.py replace --family map --stage` (what **Save to mod** runs), exported as a LayeredFS mod and
booted: the church is full of Jargons (`out/emu/probe/savepath_b011_108/field.png`). So the project file -> typed edits -> pack -> game route works.

### Changing the number of records

| level file change (all 52 `b011` levels, 3D save) | result |
|---|---|
| unreferenced block appended at the end | loads, game runs |
| actor array moved to the end, same record count | loads, game runs |
| **one NPC record appended inside its own array** (`+0x1F0`, copy moved 1.5 units) | **loads: a second priest stands next to the first** (`out/emu/probe/dup_own_plain_b011/field.png`) |
| a whole layer container (1,092 bytes) duplicated (what the first version did for one-NPC arrays) | **crash** while the field loads: `unmapped Write32 0x00717330 @ 0x000FE734, PC 0x001AFC90` |

The faulting loop is the level-ingest function at 0x001AF6B8 (`asm/text/text_00180048.s`, labelled `Event_Sequence_DispatchCommands`
in the naming batch but it walks the root layer list and pushes each container's records into per-kind lists in the level object): a
duplicated container breaks its layer bookkeeping. Appending *records* inside their arrays is fine.

Raw level files are not found in guest RAM after loading (the engine converts them), so a RAM scan cannot identify the loaded level:
use visible perturbations instead.

## Actor record (container +0x1F0, 100 bytes), as the editor exposes it

| offset | field | status |
|---|---|---|
| +0x20 / +0x24 / +0x28 | position X / Y / Z | X confirmed in the emulator; Y and Z follow from the engine's spawner |
| +0x2C / +0x30 / +0x34 | rotation (Euler); +0x30 is the facing | +0x30 confirmed (priest turned around) |
| +0x5C (u16) | entity id (character / monster); scripts call `GetActorID(id)` | confirmed: 0x6C made spiders |
| +0x5E (u16) | entity class (0x300 usual; 0x100 / 0x200 variants) | meaning unknown |
| +0x54, +0x58, +0x60 (u32) | flags / key | unknown, shown read-only |

**Entity ids.** For class `0x300` the id is a row of `gamecmn/enemy_base` (1,043 rows): row 108 has `model = m043a`, which the model
index names "Jargon" (the purple monster that replaced the church's NPCs in the emulator test). `python -m tools.entity_table` writes
`game_assets/maps/entity_models.json` (id, model, English and Japanese name); the editor uses it to label actors, show the model, and
offer a searchable monster picker. NPC classes (`0x100`, `0x200`) are rows of the region character tables
(`param/region/<r>/npc_list`, 26-byte rows; the word at +0x0E carries ids such as 15 and 16) and are not resolved to models yet.

`python tools/map_tool.py export --all` writes these as `kind: "actor"` with `props`; the editor saves edits as typed project edits
(`{"offset", "type": "u16", "value"}`) and a duplicate carries its props in `set.props`.

## Warps (work in progress, task CL0)

> Correction: the `+0x1B8` trigger records' `+0x28` word is a level-local trigger id, not a `level_map` row. Each trigger can own a child array of event words (e.g. `0x202f2de`, `0x1004ff2`); the village numbering only looked like map ids by coincidence. The editor no longer resolves destinations from it.

`python tools/map_tool.py export --all` now writes the `+0x1B8[48]` records as `kind: "trigger"` (destination map id as an editable property) and
`python -m tools.entity_table` adds `maps` (level name per map id) to `game_assets/maps/entity_models.json`; the editor shows them in a **Triggers**
group with the destination level name and an **Open level** button.

**Established**
- Map ids are the row index of `syscmn/level_map.json` (2,284 rows, 28 bytes each, the name string is at +0 as a self-relative pointer):
  256 = `b011_001a`, 257 = `b011_002a`, 263 = `b011_105a`, 272 = `b011_001b`, 288 = `b011_001c`, 294 = `b011_001d`. The letter suffixes are
  variants of the same place.
- In the village level `b011_001a` two arrays carry map ids:
  * container `+0x68`, 24-byte records (15 of them): the word at +0x0C ends in `0x101, 0x103, 0x104 ... 0x10F` (the 15 house interiors, maps 257-271);
  * container `+0x1B8`, 48-byte records (29 of them): position (x, y, z at +0x10..+0x18), facing (+0x20), a type tag `0x4003` at +0x2A and a map id
    in the low half of the word at +0x28 (`0x0101`, `0x0107`, `0x010E` ...). These look like door trigger volumes.
  Neither is confirmed in the game yet.
- Script side: a trigger runs `TrgMapJumpEvent(map_id, locator, jump_type, fade_time)` in the area script, which may rewrite the arguments and then
  `StartEventArg(MapJumpEvent, ...)`. `MapJumpEvent` is in `script/base`: it fades out (jump type 0 = fade + door sound, 1 = fade, 2 = trip door ...),
  calls `SendTrgMapJump(map_id)` and ends with `LoadField(map_id, locator, 255)`.

**Tried in the emulator (3D save, Cobblestone church, `out/emu/probe/`)**
| test | result |
|---|---|
| all `+0x1B8` destinations set to 0x10B, then walk out of the church | the player could not be walked out of the nave (the hook supports the circle pad, but the scene kept the player in place / in menus); inconclusive |
| a function added to the b011 area script, started from `OnBeginScene`, calling `MapJumpEvent(257 / 256, locator 0 / 39, 0, 30)` after 240 frames | the scene fades to black and stays black; no crash, no log error. So a script can reach `LoadField`, but the target scene did not appear |

**Walking out of the church (probe `WALK:<dir>`):** the circle pad works. After ten B presses (cancel the priest's save menu) the player is free: walking
south in 1 s steps moves the player down the nave, the camera cuts to an outside view of the church near the entrance, and walking north brings it back
(`out/emu/probe/walk_church/sheet.png`). Eight seconds south did not reach the street: the player stops at the entrance area and no door fired. All
saves in `third_party/emutest/saves` (`user_citra`, `user_citra_2d`, `user_citra_3d`) start in this church. A save made **outdoors** would remove the problem.

**Open**
- Why `LoadField` does not finish when started this way (invalid locator, called from the scene-begin thread, the church's opening event still running,
  or the map needs a `SendTrgMapJump` precondition). Next: start the same call from a talk event (press A on the priest) or from a save made outdoors,
  and find which locator ids a level defines (the locator arrays) so arrivals can be chosen correctly.
- Which of `+0x68` / `+0x1B8` the engine uses for the trigger itself. Test from a free-roaming outdoor save: set one trigger's `+0x28` and walk into it.

## How the rest will be found

Reading code alone is slow here (no names in the binary). The fast method is **perturb and observe**:

1. take a small level the player can reach quickly in Azahar (`tests/emu`, harness from `3DS_Translate/emutest`);
2. change exactly one word of one record (a model id, a facing, a flag, a type) with `tools/level_records.py`-style patches;
3. boot, screenshot, compare. Record the result per word in `tools/level_schema.json` (name, type, evidence).

Order: actor placement (position, facing, model/character id, script id, behaviour) -> chest -> map-jump trigger -> locator -> gimmick
-> encounter zone -> collision. Each step gives something the editor can show and edit.

## Next concrete steps

1. Find the loader that turns the BXON into the descriptor (callers of `Field_Scene_InitObjectTable`; the type hash is not a code literal,
   so search for the container offsets used as `+0x1F0`, `+0x188`, `+0x248` in functions that take the BXON root).
2. Perturb-and-observe on `b001_101a` records at 0x2060 / 0x2A84 / 0x2AE8 / 0x3040 (the people): +0x5C, +0x60, +0x58, then +0x44.
3. Turn confirmed fields into `tools/level_schema.json` and make `tools/map_tool.py` export named kinds instead of
   `placement` / `transform`.

## NPC ids (open, task CL-NPC)

Village actors (`b011_001a`) carry `+0x5C` words of the form `(class<<24)|id` with classes 1/2/3 and ids 0x11..0x2F, 0x82..0x8A, 0xD5 (`0x3000015`, `0x1000011`, ...). `param/region/r001/npc_list` (`RegionCharacterPara`, 26-byte rows, 0x14 word `0xFFFF00xx`) and `npc_ie` (`CharacterIEData`, 24-byte rows) are the candidate lookups; the id-to-row mapping is not decoded yet. Until it is, NPC actors have no model in the editor.

Findings so far (NPC ids): `npc_list` of region r001 has 244 rows of 13 u16 words; words 7 and 10 carry the per-row values (e.g. row 21 = 0x1E9 / 0x7D, row 4 = 0x1A / 0x1D), the rest is 0xFFFF filler. NPC models are the `chaNNNNN` set (1,663 entries, e.g. `cha01000a` = The Luminary, ids from 01000 up), so the lookup is probably actor id -> row -> character id -> `chaNNNNN`, but neither the row selection nor the character-id scale is confirmed. Needs an emulator perturbation (swap an NPC id in the village and see which model appears), the same method that resolved monsters.

Emulator result (NPC ids): setting every class 1/2/3 actor in all 52 `b011_*` levels to `0x03000082` (Cobblestone church save, game kept running, no crash) removed the red-hatted priest behind the altar and put a blue slime-like figure there instead (`out/emu/probe/actors_npcswap_b011/field.png` vs `out/emu/probe/turn.png`). So the `+0x5C` NPC word does choose the character, and id 0x82 is a slime-type NPC. The id -> model table is still not decoded; the next experiment is a sweep of ids and recording which `chaNNNNN` model each shows.

Entity word caveat (user report, b002_001a): class `0x300` is NOT "monster". Towns use it for NPCs too (b002_001a: 58 x 0x300, 23 x 0x100, 14 x 0x200), so resolving every 0x300 id as an `enemy_base` row put monsters where NPCs stand. The editor now resolves monsters only in levels with no class 0x100/0x200 actors; in NPC levels actors show their id only. Dungeon levels with only class-0x300 actors (b001_*, all verified monsters) still resolve. A real discriminator (probably the level kind or the +0x50/+0x58 words) is still unknown; `b004_001c`-style levels with only class 0x300 are unchecked.

NPC lookup, ruled out so far: treating `npc_list` words 7 / 10 (+1000 or as-is) as a `chaNNNNN` model id matches an existing model for only 40 of 244 rows (word 10) and 15 of 244 (word 7), so neither is a direct model number. `Field_LoadNpcTables` (0x184EF8) only loads npc_list/npc_ie/book_ie; the spawn code that indexes them by actor id has not been found in `decomp/`. Next: find the reader of the table handle at `FieldNpcTables+8` (stride 0x1A rows), or sweep ids in the emulator.

Lead (actor classes): `Field_RegisterActorClass_NPC3DActor` (0x67EDF4) registers six actor classes: NPC3DActor, NPC3DPlayerActor, NPC3DAnimalActor, NPC3DEnemyActor, NPC3DSpiritActor, NPC3DEmbarkartionActor. The record's class half (0x100/0x200/0x300) probably selects among families like these rather than "NPC vs monster", which would explain why towns use 0x300 for NPCs. The mapping from class value to class name, and where the id is then resolved (`npc_list` for NPC-like actors, `enemy_base` for enemy-like ones), is the next thing to read in `Field_Scene_SpawnObjectsFromTable` (0x336BE4) / `Field_Scene_AddActorObject`.

Contradiction to settle (NPC vs monster ids): in the church (`b011`), setting `+0x5C` to `0x0300006C` did make the people into Jargons, so a class-0x300 id resolves through `gamecmn/enemy_base` there. But the 0x300 ids in town levels (`b011_001a`: 0x15 = Medislime, 0x29 = Hardclaw, ...; `b002_001a`: 58 of them) read as monsters when looked up that way, while the user says those spots hold NPCs in the game. Either those levels list entities for every story phase / spawn group (so many are not visible at once) or another selector decides. Only a probe inside such a level settles it: save the game inside the `b002_001a` castle town and perturb its records. The same save would test warps. (`out/emu/probe/*` screenshots only cover the church.)

## Heliodor probes (the "Player" save)

The user's save lives in `%APPDATA%\AzaharPlus\sdmc\Nintendo 3DS\0000...\0000...\title\00040000\00199200\data\00000001` (Data0 = "Player2" Cobblestone, Data1 = "Player" + Erik, Lv 6, Heliodor, Data2 = "PLPM"). It is installed as `third_party/emutest/saves/user_heliodor` (Data1 copied over Data0, because the probe loads slot 1). "Continue" always lands in the church; leaving it loads the town. `tools/emu/level_probe.py` now skips the intros by pressing A (about one minute per run instead of several) and the actions list can press B and `WALK:D` to leave the church.

Result: with every NPC-class (1/2/3) actor of all 39 `b002_*` levels set to `0x03000082` (Cyclops, enemy_base row 130), the church priest changed (a different, white-haired priest with a blue icon above him) and the Heliodor street seen after walking out showed no Cyclops (`out/emu/probe/actors_npcswap_b0020082/`). So the visible town NPCs near the church are not driven by the `b002_001a` actor records, or the 0x300 ids there are not enemy_base rows. Next: identify which level is the Heliodor street the player loads into (the probe's `scan` option reads the loaded level out of RAM) and perturb that one.

**Heliodor result (corrected, user-reported):** the first run walked too far, into a wall, so nothing showed. With shorter steps (`out/emu/probe/actors_npcswap_b0020082/top.png`) setting every NPC-class actor of all `b002_*` levels to `0x03000082` turned the church priest into a woman and filled the Heliodor street with the same woman in a white/red dress (no Cyclops). So in a town a class-`0x300` id selects an NPC *character* (id 0x82 = that woman), not an `enemy_base` monster row: the id is resolved per region through the NPC tables (`param/region/rNNN/npc_list`, `npc_ie`), which also explains `0x0300006C` giving a monster in Cobblestone (that region's table maps it to a monster model). The editor's `enemy_base` lookup is therefore only valid where the level really spawns enemies; `npc_list` row semantics (row index is not simply the id: r002 row 130 is empty) remain to be decoded.

NPC id -> model data points (Heliodor save, church scene, RAM scan of `cha\d{5}` strings after loading; `tools/emu/level_probe.py` `ram_regex`): `0x11`->cha13102c, `0x15`->cha05431a, `0x20`->cha01406a, `0x29`->cha04401a, `0x6C`->cha01404a, `0x82`->cha15101a. None of these numbers (or their parts) occur in `npc_list`, `res_model3d` (a plain list of 526 `chaNNNNN` names), the level files, or any other table searched, so the id -> model step is computed elsewhere (probably from the NPC table plus code). The sweep is 70 s per id; a full 214-id sweep is possible unattended but not done.

## How an NPC id becomes a model (findings so far)

* The level ingest loop (`Event_Sequence_DispatchCommands`, 0x1AF6B8) does not create actors: for each container array it only keeps the records whose layer flag (the byte at record +0x5F for the 100-byte actor array) matches and pushes them onto script-context lists. The NPC objects are created afterwards by the level script through natives, which read `+0x5C`.
* `param/region/*/npc_list` is not the model source: for the ids tested (0x11, 0x15, 0x20, 0x29, 0x6C, 0x82) its rows are empty or hold values unrelated to the loaded models. `npc_ie` is a tree of (count, self-relative offset) pairs, not a flat model table. `res_model3d` is only the list of 526 `chaNNNNN` names.
* Model names are built at runtime (no `cha%` format string in code.bin; formats like `%s%s%02d`, `%s_%02d%s` exist), and the same id gives different characters in different areas (0x6C: a monster in the Cobblestone church, `cha01404a` in the Heliodor church).
* Fallback that does not need the mechanism: `tmp npc_bits.py` style binary-coded sweep (7 emulator runs for all 109 id pairs of `b002`; run 0 done: 24 character models loaded in one run). It would have to be repeated per area.
* Next static step: the Squirrel natives that create NPCs (`decomp/native_names.json`, `NPCTalkSetup`, `GetNPCActorPlayerID`, ...) and the scripts that call them for a level.

## SOLVED: actor id -> model (all NPCs and monsters)

An actor record's `+0x5C` word is `(class << 24) | id`. The **id is a row of the level's region table** and the model comes from that row:

1. The level's row in `syscmn/level_map.bxon` (28-byte rows, name pointer at +0) holds the **region** in the low byte of the word at +4 (b001/b002 = 20, b011 = 0 ...). The region's table is `param/region/r<region+1>/npc_list.bxon` (`RegionCharacterPara`, 26-byte rows = 13 u16; scripts reach it through `GetActorRegionCharacterID`, e.g. `IsRegion(20)` in the b002 script is `r021`).
2. Row `id`, **word 7** = index into the model name list of `gamecmn/res_model3d.bxon` (all names in file order: 526 `chaNNNNN`, then `ani`, `m###` monsters, ...); the low byte of **word 9** is the variant (0 = a, 1 = b, 2 = c ...). Row 17 of r021: word7 489 = `cha13102`, variant 2 = `cha13102c`.
3. Verified against the emulator RAM scan for ids 0x11, 0x15, 0x20, 0x29, 0x6C, 0x82 in Heliodor (all six match) and by Cobblestone r001 row 108 -> `m090` (a monster). `gamecmn/enemy_base` is NOT how actors resolve; the earlier `enemy_base` reading was wrong.

`python -m tools.entity_table` now writes `level_regions` and `npc_tables` into `game_assets/maps/entity_models.json`; the Level Editor draws each actor's real model from it and the Entity group has a character picker for the level's region. The class byte (1/2/3) does not change the lookup (not yet understood; probably behaviour type). Words 0-6, 8, 10-12 of a row are not decoded.

## Level exits (the map-jump table, +0x68)

The 24-byte records of the container array at `+0x68` are the level's **map-jump table**: the word at `+0x0C` is `(locator << 16) | destination map id`, where the map id is a row of `syscmn/level_map` (b002_001a -> `f001_003a`, `b003_001a`, `b002_101a`..`b002_105a` ...; b001_101a -> `b001_102a` x2 and `d001_001a`; b011_002a -> `b011_001a`, `d017_001a`, `b011_109a`, `b011_110a`). `+0x08` is `0xFFFFFFFF`, `+0x10` is usually `0x030001FF`, `+0x14` is an id/hash. These are the arguments the scripts' `TrgMapJumpEvent(map_id, locator, jump_type, fade_time)` receives (`a_010` etc. only remap a few of them), so editing a record's destination changes where the exit leads. **Not yet proven in the emulator** (the `+0x1B8` trigger volumes are what fire them; how a trigger picks its entry is still open).

The editor lists them under **Exits** (`tools/map_tool.py` kind `exit`, no position, not drawn in the viewport); the Inspector shows the destination level with **Open level** and a searchable picker that rewrites the destination map id.

**Proven in the emulator (Player save, Heliodor church):** with the destination of every `+0x68` record of all 39 `b002_*` levels set to map 256 (`b011_001a`, the Cobblestone village; `locator` bits unchanged), walking out of the church door loaded the Cobblestone village (houses, an old woman, a dog, the water wheel) instead of Heliodor, with no crash (`out/emu/probe/exitswap_b002_256/m.png`, script `tools/emu/` pattern: `exit_swap.py` in the session scratchpad: set the low 16 bits of the word at +0x0C of each 24-byte record). So **the map-jump table decides where a level's exits lead, and its destination is editable.** Open: the locator half decides where the player arrives (kept as is here); which trigger fires which entry; a map id with no level pack of its own (a new level) has not been tried.

## New map ids (registration, CL task)

`syscmn/level_map.bxon` has **2284 rows** (28 bytes each, name pointer at +0): 830 have an empty name (ids 1454 and up are free) and 258 named rows (the `z###` ids from 0) have no `level3d` pack at all. So a new level can take a free row: write its name string, point the row's name at it, then add the level's packs (`level3d/<name>`, `3d/bg/<name>`, `level2d/<name>`) and aim an exit's destination map id at the row. Not tried yet. A quick first experiment: clone a small existing level (a house) under a free id and point an exit at it.

## Gimmicks (chests / search spots), array +0x240, 108-byte records (decoded from data, not yet proven in the game)

The scripts treat chests and search spots as *gimmicks* (`GimmickItemGetDetail`: `GetGimmickItemID(target, 0..2)`, `GetGimmickItemNum`, `GetGimmickGetGold`, `GetGimmickGetCasinoCoin`; an item id of 65535 means empty). The container array at `+0x240` has 108-byte records:

| offset | meaning (evidence) |
|---|---|
| +0x18 / +0x3C | two size triples (2.1, 2.0, 2.1) and (4.2, 2.0, 4.2): the interaction box and a larger trigger box |
| +0x48 | position x, y, z (church `b002_105a`: (4.5, 0, -2) and (4.5, 0, -1) next to the priest) |
| +0x60 | u16 `0x2D0` / `0x2CF` + u16 `0x0100`: gimmick type (+ count?) |
| +0x64 | u16 **item id** (0xFFFF = none; Heliodor `b002_001a` search spots hold items 79 Cherry blossom petal, 80 Buzzberries, 96 Purple eye, 98 Pale pearl) and u16 gimmick id (0x353..0x35F, consecutive per level) |
| +0x68 | u32 key/hash (`0x53B6`, `0x52F6` ...) |

Heliodor `b002_001a` has 12 such records, `b002_105a` (the church) 2. Test attempt: set the item of both church gimmicks to 0 (Medicinal herb), walk right/down from the Player save start and press A (`tools/emu/` probe pattern); no item message appeared, because the hero did not stand at the spot facing it (positions need a careful walk path); inconclusive, so the item field is **not proven**. Second item slots, the count and gold fields are still unidentified.

## Collision (see docs/COLLISION.md)

`CL2_collision` remains open. Candidates by element size in the container: `+0x178` (204 B), `+0x100` (60 B), `+0x1C8` (40 B), `+0x3B8` (32 B), `+0x3C8` (48 B, position + second position + a type/hash word `0x40400300`), `+0x2A0`/`+0x270` (72 B). None identified.

Gimmick test, more attempts (church `b002_105a`, item set to 0, Player save): (1) gimmick moved onto the hero's start position: A talked to the priest, no item; (2) gimmick placed 3 units south of the start and the hero walked down the nave (about 3.5 units per second of circle-pad time): A did nothing. Both inconclusive. Likely reason: searching a gimmick needs an interaction target (an actor / visible object linked by the gimmick id) in front of the player, which the church's two gimmicks may not have. Next: test a gimmick that has a visible object, i.e. one in the Heliodor street (`b002_001a`, 12 records) next to a known spot, or find the actor that points at the gimmick id.

Update: collision lives in `3d/bg/<level>/<level>_chit.rcb` / `_yhit.rcb` / `_vhit.rcb` (magic `rcbl`), not in level3d.bxon; the candidate level3d arrays above are probably not collision. See docs/COLLISION.md.

> Correction: the church of the Player save is `b002_101a` (area id 109), not `b002_105a` (a house). The gimmick test attempts above edited the house and are void; redo them on `b002_101a`.

Collision update: editing `3d/bg/<level>/<level>_chit.rcb` (count at +0x30 = 0) removes the walls in the emulator (proven on `b002_101a`); see docs/COLLISION.md.

Chest test, setup findings: the church level `b002_101a` has **no gimmick array** (no chests there). Editing the save (area id 0x6FC4 = 108, position 0x658C, facing 0x6598, CRC32 rewritten) does **not** move the hero: "Continue" always loads at the church (the priest's welcome-back dialogue appears), so the street gimmicks (12 in `b002_001a`) can only be reached by walking out of the church (exit word `0x6006C` = map 108, locator 6). Open: where locator 6 puts the hero in `b002_001a` (the 0x3b8 / 0xc8 arrays hold positions but the locator index is not decoded), then a path to the nearest gimmick; or move a gimmick onto the arrival spot.

**Second exit proof (church -> house):** with the church (`b002_101a`) exit word changed to destination map 113 (`b002_105a`, a house) and the locator kept (6), walking out of the church door lands the hero **inside the house** (door at the top, wooden divider, red carpet, bed; `out/emu/probe/house_60550/m.png`). So an exit can lead to any existing level and locator 6 of the house puts the hero just inside its door. The same route (`tools/emu` probe pattern, script `house_test.py` in the session scratchpad) was used to try the house's two gimmicks (`+0x240` records at (4.5, 0, -2) and (4.5, 0, -1), items set to 1): walking right and down from the door and pressing A produced no item message. The camera sits behind the house's front wall, so the hero is hidden and the position of the spot relative to the hero cannot be checked; the gimmick **item field is still not proven**. Next: a level with an open view (the Heliodor street) or lowering the walls with the collision / model tools to see the hero.

Chest test, house, huge interaction boxes: with both gimmicks of the house `b002_105a` given item 1 and both size triples at +0x18 / +0x3C set to (60, 4, 60), pressing A after arriving through the church exit still produced no item message. So (a) these records are not triggered just by standing near them and pressing A, or (b) their item is only read by a script that targets a gimmick *actor* (`GetTargetActorID` -> `GetGimmickItemID(target, n)`), i.e. the visible chest / pot object is an actor whose gimmick id points at the record. The house's only actors are two NPCs (`cha02101a` at (2.5, 0, -1.5) and `cha14102a` at (-2.48, 0, 0.45)), so the house gimmicks may be something else (a bed, shelf or pot search spot). Next: find an actor whose record carries a gimmick id (the actor record's unknown words +0x54/+0x58/+0x60) in a level with a visible treasure chest, e.g. by diffing a level that has a chest model, and test its item.

## Gimmick records, what the data says (chest work, still no in-game proof of the item field)

* **Kind byte.** In the 108-byte records at `+0x240` the byte at `+0x62` is the script **RCommand type** (`TrgRCommand` in `script/common`: 0 ItemBox, 1 SlotMachine, 2 Door, 3 KeyedDoor, 4 EventDoor, 5 OnewayOpenSideDoor, 6 OnewayCloseSideDoor, 7 Storage, 8 Breakable, 10 talk, 12 RoadBlocked, 13 Signboard, 14 GlitterPoint, 15 BookShelf, ...). Counts over all 1,196 levels (`+0x60` word): `0x10002D0` (kind 0, item box) 367, kind 1..6 `0x101..0x106 02D0` 18 / 39 / 39 / 20 / 61 / 59 (one-way doors are the most common doors), `0x2CF` (a second family, no kind byte set) 615, `0x2D0` 35.
* **Pairs.** The records come in pairs one unit apart (e.g. `b011_001b`: (5.8, 1, -38.0) item `0x3A`, (5.8, 1, -36.8) item `0xFFFF`), only one of a pair carries an item id (`+0x64` low u16, `0xFFFF` = empty). The u16 above it (`0x353`, `0x355`, ...) counts up per level.
* **Object families by container array and type word** (the u16 type at the position shown): `0x230` (100 B, type `0x2CB`, a 4.2 m box at +0x18, position at +0x34, id word at +0x60; 511 over all levels), `0x240` (108 B, `0x2CF` / `0x2D0`), `0x248` (120 B, `0x2CC`, 1.5 x 3 x 1 box: doors), `0x250` (124 B, `0x2CD`), `0x258` (140 B, `0x2D3`), `0x260` (124 B, `0x2CE`), `0x268` / `0x270` (72 B, `0x2D1` / `0x2D2`). `fieldcmn/res_gimmick3d_bounds.bxon` lists bounds for the types `0x2CC, 0x2CD, 0x2CE, 0x2D1, 0x2D2` (model-backed gimmicks); `0x2CF` / `0x2D0` are not in it (invisible trigger zones).
* **Scripts** compare `GetActorLevelGimmickID(target)` with small per-map numbers (map 256 id 75, map 108 id 1 / 0 ...), which look like the record index inside its array.
* **Observation limits.** The text log (`events.jsonl` of a probe) records every message shown on screen; a successful chest would appear there as an item-found message. In the house test (item set, boxes widened to 60 m, gimmick moved to the arrival spot) no such message appeared, so either the hero was not facing a gimmick actor, or the actor is only created under a condition (layer / story flag) not met in this setup. A reliable test needs a chest whose place in the world is known (an open street, the hero visible).

## PROVEN: deleting actor records

Emulator (Heliodor church `b002_101a`): `level_records.apply_ops` with delete ops on the two priest records (`0xFAC`, in an array of two, and `0x152C`, the only element of its array): the game loads normally and the church has no priest (empty lectern, no welcome-back dialogue, `out/emu/probe/del_45244`). A record that is the only element of its array cannot be removed from the array, so `apply_ops` sets its **layer-mask byte (+0x5F, the high byte of the class word) to 0**, which the level ingest loop treats as "not in this layer" (docs/GIMMICK_DECOMP.md, `Event_Sequence_DispatchCommands`); zeroing that byte alone was also proven (`mask_45164`).

## PROVEN: a new map id (re-pointed level_map row) and correction of the row count

`syscmn/level_map.bxon` has **1,454 real rows** (28 bytes each, ids 0..1453); what I earlier counted as rows 1454+ is the **string pool** (names such as `z001_001a`). About 258 rows carry names of maps that have no `level3d` pack (the `z###` ids, e.g. row 14 `z006_002a`); they are free to re-use. Emulator: copying row 113 (`b002_105a`, the house) over row 14 with its name pointer re-aimed at the house's name string, and pointing the church exit at map id 14, **the church door loads the house** (`out/emu/probe/newmap_45341`, script `newmap_test.py` in the session scratchpad: write the row, `stage_member('syscmn.pack', 'level_map.bxon', ...)`). So a map id can be added without growing the table.

Clone with its own content: `level3d/<name>.pack` and `level2d/<name>.pack` use name-independent member names (`level3d.bxon`, `level2d.bxon`, `leveldmap.bxon`), so copying the file under the row's own name (e.g. `z006_002a`) is enough for them. The `3d/bg/<name>.pack` members are named after the level (`<name>.bch`, `_chit.rcb`, `_yhit.rcb`) and the PACK table of contents stores a hash per member, so renaming them needs the pack hash (not decoded, `0x243F17B7` for `b002_105a.bch` is not a plain CRC32); until then a clone shares the background of an existing level only through its row name. Next: decode the PACK name hash, then clone the three packs under `z006_002a` and edit them independently.

## PROVEN: taking over a level slot with new content; the PACK name hash

* **Name hash:** a PACK member is looked up by the **64-bit FNV-1** hash of its name (`h = (h * 0x100000001B3) ^ byte`, start `0xCBF29CE484222325`, no final mix), stored after the offset table at `0x18 + 4 * count` as 8 bytes per member in member order. Verified for the three members of `3d/bg/b002_105a.pack` (`b002_105a.bch` = `0xAB65FF7E384C0930`, ...). Member names are NUL-padded in the entry header.
* **Tool:** `tools/new_map.py` (`clone(src, dst, mod_dir)`): copies `level3d/<src>.pack` and `level2d/<src>.pack` unchanged (their members are name independent) and renames the members of `3d/bg/<src>.pack` (`<src>.bch`, `_chit.rcb`, `_yhit.rcb`) to `<dst>` with new hashes (same name length required).
* **Emulator (Player save):** `clone('b002_105a', 'b002_106a')` writes the three packs over the existing `b002_106a` packs; the church exit pointed at map id 114 (`b002_106a`, row 114) now loads the **house** there (`out/emu/probe/take_45539`). So a whole level (3D data, 2D map, background, collision) can be replaced by edited clones.
* **Limit:** Luma LayeredFS only replaces RomFS paths that already exist (`export_mod` refuses added files on `--target luma`); a level with a brand-new pack name needs a rebuilt ROM (`--target 3ds` / `cia`). The practical route is to take over an existing, unused level slot.

## PROVEN: reshaping a cloned level's geometry (same vertex count)

`tools/model_patch.apply_positions` on `b002_105a.bch` with every vertex's x multiplied by 1.8 (3,197 vertices, 27 meshes from the exported OBJ), written into the cloned slot `b002_106a` (`new_map.clone` then `patch_asset.rebuild_pack` on the renamed member) and entered through the church exit to map 114: the room is visibly wider, doorway, rugs and bed stretched (`out/emu/probe/take_45730`). So a cloned level's background model can be reshaped in the game today with same-count vertex edits (move / scale / reshape an existing room). Collision (`_chit.rcb`, `tools/rcb_tool.py`) must be edited to match. **Not yet:** more vertices than the original (a real BCH writer, task `CL3_model_import`), new materials / textures.

Note (new_map): `tools/new_map.py` now renames members through `tools/pack.py` (a fresh layout with new entry names and FNV-1 64 hashes), so compressed (PACA) background packs such as the church's work too; checked by parsing the output and in the emulator (cloned house in `b002_106a`, no crash). A drop-down inside an egui menu closes the menu, which was found by clicking in the real app, so the clone action lives in a window.
