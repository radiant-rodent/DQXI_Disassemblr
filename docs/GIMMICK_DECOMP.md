# Gimmicks (chests, search spots, doors): functions read so far

Notes from the decompilation (`decomp/readable/functions`, `decomp/functions`, `asm/text`) and what each step means for the level data. Addresses are the game's code addresses.

| function / address | what it does (evidence) |
|---|---|
| `GetGimmickActorID` 0x154DD4 -> `Event_GetOrAddActorSlot` 0x24B338 | takes a scene **object id** (compared as a **byte**: `slot+6 == actorId`), looks it up with `Container_ValidateHandle` / `maybe_Field_Scene_FindObjectValueById`, and returns the **slot index** in the event's 0x10-byte slot vector (`EventState+0x430..0x434`), appending a slot when the object exists, **-1** when the id is unknown. So scripts' `GetGimmickActorID(75)` is "the object whose id is 75", and the number it returns is an index into the event's actor table, not the id. |
| `GetActorRegionCharacterID` 0x160990 | `slot[index].u16 at +4` of the same 0x10-byte slot vector (the region-character id of that actor; see LEVEL_FORMAT.md, actor id -> model). |
| `GetGimmickItemNum` / `Script_Native_GetGimmickItemID` 0x154EAC / 0x6F77B0 | slot index -> object (`func_0044C6DC` / `0x44C3D0` RTTI-cast thunks) -> accessor `0x64E14C(obj, slot)`; the accessor at `0x64E18C` is `ldrh r0,[obj + slot*2 + 0x200 + 0xC8]`, i.e. **the item ids are a u16 array at `object+0x2C8` (three slots)**, and `0x64E158` returns a float / `+0x2E8` (gold-like field). The asm listing near 0x64E14C is mis-aligned (Thumb/ARM mix); the loads above are the readable part. |
| `Field_ActorGimmick_InitFromRecord` 0x2BE834 | initialises a 3D gimmick actor from a level record: `self+0x258 = record[0x19]` (the u32 at record +0x64), transform from `record[8..13]` (+0x20..+0x34), bytes at +0x56 / +0x57 / +0x5A, u16 at +0x5E (!= 0xFFFF -> resolves a model through the data manager), float at +0x44 (balloon range). That is the layout of the **100-byte records** (`+0x230`, type 0x2CB; transform at +0x34 in the exported scene), not the 108-byte `+0x240` records. |
| `Field_Gimmick_InitFromRecord` 0x2BE0E4 | the **2D (sprite)** gimmick initialiser (tile fields +0x22 / +0x24, `Gfx_SpriteActor_*`); not the 3D path. |
| `Field_Scene_SpawnObjectsFromTable` 0x336BE4 / `Field_Scene_AddActorObject` 0x6C2B18 | 2D scene object table spawner (sprite objects); not the 3D level arrays. |
| `Event_Sequence_DispatchCommands` 0x1AF6B8 | the **level ingest loop**: for each container array it only keeps records whose layer mask byte (record +0x5F for 100-byte actors) matches the current layer and pushes them onto script-context lists; objects are created later. |
| `Field_LoadNpcTables` 0x184EF8 | loads `npc_list.bxon`, `npc_ie.bxon`, `book_ie.bxon` from the area pack into the NPC container (`FieldNpcTables+8/+0x10/+0x14`). |
| `Field_RegisterActorClass_NPC3DActor` 0x67EDF4 | registers NPC3DActor / PlayerActor / AnimalActor / EnemyActor / SpiritActor / EmbarkartionActor classes. |
| `script/common.TrgRCommand(type)` | maps the interaction type to the event: 0 ItemBox, 1 SlotMachine, 2 Door, 3 KeyedDoor, 4 EventDoor, 5/6 one-way doors, 7 Storage, 8 Breakable, 10 talk, 12 RoadBlocked, 13 Signboard, 14 GlitterPoint, 15 BookShelf, 16 TreeGuidance, 17 Pitfall, 18 MiniGameBoot, ... 24 Mimic, 25 SavePoint, 32 LevelGimmick. `RCommand_ItemBox` = `EventItemBox(GetTargetActorID())`. |
| `script/base.GimmickItemGetDetail` | reads `GetGimmickItemID(target, 0..2)`, `GetGimmickItemNum`, `GetGimmickGetGold`, `GetGimmickGetCasinoCoin` (65535 = none) and calls `AutoAddItemInParty`. |

## Probe technique (works)

* The probe's text log (`events.jsonl`) records every message shown. To run test code in a real scene without walking: edit `script/b002` (`tools/script_build.py pack --tier source --area b002`), make `OnBeginScene` take the love-letter branch (`local is_has_loveletter = true;`) and put the test in the body of `IE_Z_A_030_M02_0155_A030_F05` (an existing event, which is safe at scene start; adding a **new** `StartEvent` in `OnBeginScene` leaves the screen black).
* Area scripts cannot call functions that live in `script/base` (e.g. `GimmickItemGet`): referencing them leaves the scene black. Call the natives instead (`GetGimmickActorID`, `GetGimmickItemID`, `SetMessageArgNum(9, n)`, `ScriptMessage(22)` prints "<n> gold obtained" which shows any number in the text log).

## PROVEN (emulator, Player save, church -> house route, test event in `script/b002`)

* The u16 at **+0x64 of a 108-byte `+0x240` gimmick record is a row index into `fieldcmn/fixed_drop_param.bxon`** (774 rows of 8 bytes: u16 item id, u16 count, 2 zero words; `0xFFFF` = no fixed item, the spot then uses the glitter tables). House record `0x65 = 101` -> row 101 = item 125 x1; the game's `GetGimmickItemID` for that object returned **125**. Patching the record to row 12 made the game return **1481** = row 12's item. The u16 above it (+0x66, e.g. 0x346) is the object's gimmick id.
* Object ids visible to `GetGimmickActorID` are bytes: the house exposes objects 0, 70, 71, 72; the Heliodor street exposes 1 and 70..98. Object 70 of the house is the record at +0x240 index 0.
* So a chest's contents are edited either by changing the record's row index or by editing the row in `fixed_drop_param` (the Tables editor can do that).
