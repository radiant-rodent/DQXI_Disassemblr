# Plan: build a custom level, with NPCs, monsters, dialogue and items, inside the editor

## The target scenario (the acceptance test)

> A player walks into a village, climbs down the well, finds a tunnel in the wall and walks through
> it into **a room you built**: your own walls, floor and props, an NPC you placed who talks in
> your own words, a chest holding a new item, a monster you defined that attacks you when you step
> on a marked tile. You can walk back out the same way. All of it made in DQXI Studio, exported as
> a mod, and played in Azahar (and on a real 3DS).

The goal is done when `python tests/emu/run_cases.py custom_room` plays that scenario from a mod built
**only through the editor's own save paths**, and the whole thing can be authored in the editor with
no hand-edited files.

## What is known today (2026-11-02)

| Piece | State | Evidence |
|---|---|---|
| Edit NPC / book dialogue lines | works | `docs/EDITING.md` (text banks), emulator-proven for a book message |
| New items | works, capped | 189 placeholder rows; engine hard-codes 2,875 items (`code.bin`, save data) |
| Edit tables (monsters, encounters, shops) | works, no growth | `docs/EDITING.md` |
| Edit scripts (Squirrel) | works, limited compiler | emulator-proven: new function at scene load, shop menu |
| Reshape an existing model | works, same vertex/index counts only | `docs/ASSETS.md` (`model_patch`) |
| Level records: move / duplicate / delete | works, 3,789/3,789 verified, **not game-tested** | `tools/level_records.py`, `docs/EDITING.md` |
| Warps | **traced, not reproduced** | see below |
| New geometry | missing | there is no BCH writer, only a patcher |
| Collision / walkable area | **unknown** | no decoder |
| New map entry | **unknown**, probably capped | see below |
| What each level record *is* (NPC, chest, trigger, locator, collision) | **unknown** | `map_tool` finds floats by plausibility |
| Place NPC / monster / chest in a level | missing | follows from the record schema |

### How a warp works (traced from `a_010/script.nut`)

A trigger in the level fires `TrgMapJumpEvent(map_id, locator, jump_type, fade_time)` in the area
script. The script may rewrite `map_id` / `locator` (it does, per scenario flag) and then runs
`StartEventArg(MapJumpEvent, map_id, locator, jump_type, fade_time)`. Natives seen:
`GetMapJumpEvent`, `GetMapJumpLocatorID`, `SetMapJumpLocatorID`, `ActorGetJumpMapID`,
`ActorGetJumpLocatorID`, `OnInnMapJumpEvent`, `TrgFloorMapJumpEvent`.

`map_id` is a number (15, 17, 256, 720 ...). The map registry is `syscmn/level_map.json`
(`LevelMapCommonParam`, 28-byte rows, ~2,286 rows). Row 0's name string is `z001_001a`; the row index
is the map id, and the row names the level pack. A new map therefore needs a row, and like the item
table this is probably capped by constants in `code.bin` (task `CL4`).

## Work packages

Dependencies are in each task file (`after:`). Run them with
`python orchestration/dispatch.py --only "CL*" --jobs 4` (the dispatcher is started by you, as before).

```
CL1 level format ─┬─ CL0 warps ─────────────┐
                  ├─ CL2 collision ─────────┤
                  ├─ CL5 NPC placement ─────┤
                  └─ CL6 monsters ──────────┤
CL3 model import ─── CL4 new map ───────────┼─ CL9 events (script builder) ─ CL10 editor ─ CL11 end to end
CL7 dialogue authoring ─────────────────────┤
CL8 item authoring ─────────────────────────┘
```

| Id | Delivers | Proof |
|---|---|---|
| **CL1** level format | named schema of `level3d.bxon`: which arrays are actors, triggers, locators, chests, gimmicks; field meanings; `tools/level_schema.json`; the editor shows named kinds | decode all 1,196 levels with 0 unknown shapes in the covered kinds; round-trip test |
| **CL0** warps | `docs/WARPS.md`, `tools/warp_tool.py` (list / retarget a warp), Warp nodes in the editor | emulator: a retargeted door lands in another map |
| **CL2** collision | decoder + writer for the walkable/solid data, viewer overlay | emulator: a moved wall blocks the player |
| **CL3** model import | a BCH writer that takes new geometry (any vertex count), materials and textures; OBJ/glTF import in the Models panel | emulator: a bigger room renders without corruption |
| **CL4** new map | how to add a map id (claim a row or grow the table), the level pack files, RomFS entries; "New level" wizard | emulator: boots into the new map id |
| **CL5** NPC placement | place / define an NPC (model, talk bank, patrol) from the editor | emulator: NPC stands there and talks |
| **CL6** monsters | place encounter zones, define a monster from an existing model + stats + skills | emulator: battle starts and ends |
| **CL7** dialogue authoring | new talk entries / banks, branching text, speaker names, in the editor | emulator: new conversation plays |
| **CL8** item authoring | new items with name, description, icon, shop and chest placement | emulator: item in a chest and in the bag |
| **CL9** events | event / script builder (talk, give item, set flag, warp, shop, battle) generating Squirrel | emulator: scripted event runs |
| **CL10** editor | everything above as palettes, inspectors, a map graph, "Play this level" | `docs/EDITOR_TODO.md` empties |
| **CL11** end to end | the acceptance scenario, as an emulator case and a walkthrough doc | `tests/emu/run_cases.py custom_room` |

## Rules for every package

- Use what exists first: `tools/level_records.py`, `tools/bxon_struct.py`, `tools/asset_replace.py`,
  `tools/script_build.py`, `tools/text_tool.py`, the harness in `../3DS_Translate/emutest`.
- Everything exported must stay valid on a real 3DS (see `orchestration/WORKER_RULES.md`).
- A package is done when its proof passes **in the emulator**, not when the tool runs.
- Anything found to be impossible (hard engine limits) is written down with the evidence and a
  workaround, as was done for the item table.
