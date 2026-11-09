# Demo: "Cellar below the church" (`tools/custom_room.py`)

The acceptance scenario from `CUSTOM_LEVEL_PLAN.md`, assembled from the proven pieces:

```
python tools/custom_room.py build [--mod DIR] [--item N] [--line TEXT]     # default DIR = build/custom_room/mod
```

| Piece | How | State |
|---|---|---|
| Entrance | the church (`b002_101a`) exit now leads to map id 114 (`b002_106a`); a village well exit works the same way (any exit record) | emulator: the door leads into the room |
| Room | the house `b002_105a` cloned into slot `b002_106a` (`new_map.clone`), all 27 draws replaced by `tools/assets/custom_room/full_room.obj`, checker texture over the wood texture | emulator: custom checkerboard room with the house props |
| Collision | `rcb_tool.from_obj` on `open_walls.obj` | proven earlier (docs/COLLISION.md); not re-checked here |
| Monster | the house's class-0x300 actor gets a monster row (`m...`) of Heliodor's `npc_list` | a monster-shaped actor is in the room; **battle on touch not tested** |
| Chest | `fieldcmn/fixed_drop_param` row 101 = item `--item` (default 2) | edit path proven (docs/GIMMICK_DECOMP.md); **chest not opened in this run** |
| NPC dialogue | all text lines of NPC id 46 in `param/region/r021/npc_ie` replaced by `--line` | text path proven (docs/DIALOGUE_FORMAT.md); **A-on-NPC in this room not tested** |

Screenshots of the run: `docs/images/custom_room_demo.png` (first frame: the hero arrives in the room; later frames:
the camera sits behind the front wall, so the hero is hidden). Probe: `out/emu/probe/cr_21164`.

Open: open the chest and talk to the NPC in the room (walking paths), a monster battle test, hero visibility
(the room's front face blocks the camera: model the room without it), adding NPCs / chests / monsters instead of
re-using the house's, and doing all of it from the Level Editor save paths.

## Walk tests so far (probes `cr_21343`, `cr_21425`)

* The hero arrives at the top of the room (frame 2 of each probe) and the checkerboard, the house props and the
  monster-model actor are visible; the room loads and the church exit works.
* Walking down into the room moves the hero out of the camera's view: the house's fixed low camera frames a smaller
  room than this 10 x 8 one, and the hero disappears behind the near edge of the floor. An invisible front wall was
  added to the collision (`open_walls.obj`) so the hero cannot leave through the open front, but the view stayed the same.
  Next: model a smaller room (about the house's size) so the camera follows the hero, then repeat the NPC / chest / monster walks.
* No custom NPC line was seen in these runs (the hero never stood next to the NPC with the camera showing it).

## Hero visible now (probe `cr_21523`)

With the invisible collision wall moved to z = 1.2 (the front half of the room is out of the camera's view anyway) the hero stays in the part of the
room the house camera frames: he walks across the checkerboard, his companion follows, and he stops at the right wall (x about 4.8). Pressing A there
(facing the chest position x = 4.5, z = -2 / -1) produced no item message: the house's two gimmick records have never been proven to be openable
chests (docs/LEVEL_FORMAT.md, "Chest test"), so the chest still needs a level with a known visible chest (a gimmick actor) rather than the house.
Next: use a donor level with a real chest and an NPC next to the arrival point, or add the chest/NPC through the Level Editor's Duplicate.

## NPC walk (probe `cr_21615`)

The hero walked to the left wall of the room (visible, with his companion and a pot); the house's NPC (entity id 46, expected at x = -2.5, z = 0.45)
was **not visible** in the camera's strip and pressing A produced no dialogue. Either the NPC is below the visible strip, or the house NPC is only
spawned under a story condition (layer / flag). So the custom line is still unproven in this room. Next: add an NPC with the editor's Duplicate near the
arrival point (docs/LEVEL_FORMAT.md: an appended NPC record is emulator-proven) and put the room's camera-visible area under it.

## NPC still absent (probes `cr_21709`, `cr_21791`)

The builder now also (1) duplicates the house NPC to (-1.5, 0, -2.0) with entity id 46 (`level_records.apply_ops`) and (2) gives the slot's
`level_map` row the house's parameters (row 113 copied over row 114, keeping the slot's own name), as in the earlier `newmap_test`. Neither made an NPC
appear in the room: only the hero and his companion are visible. Open question: what spawns actors in a cloned slot (layer masks / scenario flags of
the house's records, or the slot's `level2d`); next step: dump the actor layer bytes (+0x5F) of the house records and compare with a level whose NPCs do show.

## Bisect of the missing NPC (probes `cr_21924`, `cr_22004`)

`CR_SKIP=monster,dup,text,chest,lm python tools/custom_room.py build` switches each edit off (monster row, duplicate NPC, npc_ie text, chest row, level_map
row copy). With **every edit off** (a plain clone of the house with only the custom room model and collision) the room still shows no NPC next to the hero
and A presses give no dialogue, so none of the level / table / text edits is the cause. Possibly the small figure in the wide view (x about 2 to 3, z about -1.5, the
position of the house's actor 005) is an actor and only the camera strip hides the rest; this is not settled. Next (task CL_cloned_slot_actors): walk to that
figure and press A from several sides, and compare with the same walk in the real house (map id 113).

## Correction: the actors are probably there (probe `hc_22092`, real house, map id 113)

Entering the **real** house through the same church exit and walking the same way shows the same view: the hero disappears behind the house's front wall, and
the house's NPCs show only as small figures in the back half (one by the bed, one at the partition). The custom room shows the same small figures in the same
places, so "no NPC in the clone" was a camera artefact, not a missing actor. The talk path itself is established by two things: `RCommand_talk` calls
`IEMessageSetup(GetActorRegionCharacterID(target))` (script/common) and an edited `npc_ie` line is emulator-proven through that call
(docs/DIALOGUE_FORMAT.md). What is still untested is the physical A press on an NPC, because the camera hides the hero; the fix is a room modelled so the
camera follows the hero (the real house has the same problem), or testing in a street level.

## Church as the donor: the camera follows the hero, but no actors (probe `cr_22218`)

`CR_DONOR=church python tools/custom_room.py build` clones the Heliodor church instead of the house (its camera follows the hero; draws are counted
automatically, the first texture of the model is replaced). Result (`docs/images/custom_room_church_clone.png`): the hero and his companion are visible the whole
time, the room is a plain wooden floor with walls, and **neither the priest nor the NPC (id 182) appears** although the church level's actor records were cloned
unchanged. In the real church they are there. So actors of a cloned slot do not spawn, while props (pot, chest model) of the house clone did; this correction
**reverses** the "probably a camera artefact" note above for the NPC case: the church clone has a good camera and still no actors. Still open: what spawns
NPC actors (not gimmick props) in a level; next to try: copy more of the donor row (`level_map` columns beyond the first 28 bytes?), the donor's `level2d`
entries, or the area script's per-map-id calls (`b002` script runs `SetLevelGroupEnable` / `OnSetupScene` by map id: the slot's id 114 matches none of them).

## Bisect result: actors DO spawn in a clone; the generated collision is what removes them (probes `cr_22336`, `cr_22406`, `cr_22460`)

Church donor, all other edits off (`CR_SKIP=monster,dup,text,chest`), four variants of `CR_PLAIN`:

| Variant | Model | Collision | Result |
|---|---|---|---|
| `1` bare clone | church | church | the clone is the church: priest present, praying menu appears on A (`cr_22336`) |
| `model` | church | generated walls (`from_obj`) | church interior, the hero walks down the aisle (`cr_22406`) |
| `coll` | custom room | church | custom room **with the priest standing south of it and his dialogue working on A**, the NPC figure at the back (`cr_22460`, `docs/images/custom_room_church_donor_collision.png`) |
| default | custom room | generated walls | no priest, no NPC (`cr_22218`) |

So actor spawning in a cloned slot works. With the generated collision the actors vanish. `from_obj` empties every shape of the donor's `_chit.rcb` and
rewrites the header bounds to the room, so the likely cause is that **actors outside the collision's bounding box (or without floor shapes under them) are not
activated**: the priest stands at the lectern (z about -4.7), just outside the room's bounds (z -4 .. 4). Workaround and plan: keep the donor's collision and model the room
inside the donor's footprint (the church: x -4..5, z -5..5), or extend the generated collision to cover every actor position plus a floor shape. The
"camera artefact" notes above are superseded by this table.

## PROVEN: pressing A on an NPC works in the custom room (probe `cr_22574`, `docs/images/custom_room_priest_talk.png`)

`CR_DONOR=church CR_PLAIN=coll python tools/custom_room.py build` (room model generated for the church's footprint by `room_obj`, the donor's collision kept): the church door
leads into the wooden room, the hero and his companion walk in it with the camera following, the priest (an actor of the cloned level) stands at the room's south edge and
**pressing A next to him opens his prayer menu and dialogue** ("頼もしき神のしもべよ..."). So an actor of a cloned slot spawns, is solid and talkable.
The priest uses the church bank, not `npc_ie`; the custom line of NPC 182 (`--line`) still has to be walked to (position x -3.5, z -1.5 in donor coordinates).

## Walking to NPC 182 (probes `cr_22672`, `cr_22758`)

Down the nave then left (`D:1.7`, `L:0.9`, optionally `R:0.12` to turn back) put the hero just outside the room's left wall (the donor collision lets him stand about 0.7 left of the
model's wall, the model sits slightly inside the church's collision) next to a stationary figure that stays at the wall while the companion follows the hero, i.e. very likely NPC 182
at x about -3.5. Pressing A there produced no `npc_ie` line yet (hero facing / distance not right). Blind walking is too imprecise: next try a position-aware probe (read the hero's
coordinates from RAM, `tools/emu/level_probe.py` RAM scan) or place the NPC with the editor's Duplicate right at the arrival point in front of the hero.

## PROVEN: an edited text line shows when pressing A on an NPC in the custom room (probe `cr_22955`, `docs/images/custom_room_edited_line.png`)

Same setup as the priest test (`CR_DONOR=church CR_PLAIN=coll`), plus the church bank `ui/common_3d/church_msg` with the priest's "頼もしき神のしもべよ ... ご用じゃな？" lines replaced by `ZZ`
(`text_tool.rebuild_bank` + `stage_member`): walking into the room and pressing A on the priest types `Z`, `ZZ` into the message window (log frames 5204-5205). So the whole
chain **entrance -> cloned room with custom model -> actor of the cloned level -> A -> edited text** works in the emulator. The same message path serves `npc_ie`, so an `npc_ie` line follows once an
ordinary NPC (not the priest) stands in front of the hero: the duplicate-NPC position of `DUP_POS` is not right yet (the NPC did not show in `cr_22855`).

## Duplicate NPC next to the arrival point (probe `cr_23064`)

The hero arrives at the lectern, 1 to 1.5 units from the priest (priest at (0, 0.5, -5.5) in donor coordinates). The extra NPC (`DUP_POS` = (-1.3, 0, -4.3), entity id 182, `npc_ie` lines replaced) cannot be told apart from the
companion in the camera strip (both are green-clad), and pressing A after a short step left gave no `npc_ie` text. Next step to settle it: give the duplicate an unmistakable model
(entity id of a monster-model row, or a distinct NPC) or read the actor list from RAM, instead of guessing from the picture.

## The duplicated actor does not spawn in the clone (probe `cr_23159`)

With `CR_DUPID=223` the duplicate gets a monster row (a large, unmistakable model) at (-1.3, 0, -4.3): the picture is identical to the run without it, so **an appended
actor record does not spawn in the cloned room**, although the original records do (the priest) and an appended NPC is emulator-proven in the real church (docs/LEVEL_FORMAT.md).
Open: why a record appended by `level_records.apply_ops` is ignored here (the clone's `level3d` pack was rebuilt by `stage_member` over the clone; check that the staged
`level3d.bxon` really is the edited file and that the array's count was updated; compare with the church probe `dup_actors.py`).

Check: the staged `level3d/b002_106a.pack` is 6,008 bytes against 5,704 for the church's own pack, so the duplicate record (+304 bytes) **is** in the clone; the game just does not
show it. Remaining suspects: a spawn limit or per-level actor count stored elsewhere (the `level3d` header or `level2d`), or the actor's layer / event keys (`key 60`) copied from the original
record. Next probe: duplicate in the REAL church with the same position to confirm the duplicate shows there today (regression check), then in the clone.

## Cause found: duplicate a record of the ACTIVE layer (probes `cd_23513`, `cr_23573`, `cr_23649`)

The Heliodor church has two priest records, `0xFAC` and `0x152C`, in different layer containers; only one layer is active in the Player save. Duplicating `0xFAC`, or the NPC `0x1010`,
produces nothing visible, in the real church as well (`cd_23272`, `cd_23330`, `cd_23389`); duplicating **`0x152C`** puts a second priest next to the first
(`docs/images/church_duplicate_priest.png`, `cd_23513`). So the earlier "appended actors do not spawn in a clone" was wrong: the records I copied belonged to an inactive layer. The builder now
duplicates `0x152C` and gives the copy entity id 182 (`tools/custom_room.py`, `CR_DONOR=church`). In the clone the new actor shows its blue talk marker at the hero's right
(`cr_23573`); its body sits behind the room's front wall in the camera view, and pressing A after a short step right produced no `npc_ie` text yet (`cr_23649`).
Editor consequence: the Level Editor's Duplicate should tell the user which layer a record belongs to (the layer-mask byte `+0x5F` and its container) and preferably duplicate into the active layer; add to ED_scene_records.

## PROVEN (probe `cr_23952`, `docs/images/custom_room_npc_line.png`): an NPC added to the cloned room says the custom line

`CR_DONOR=church CR_PLAIN=coll CR_SKIP=monster python tools/custom_room.py build` + walk `D:1.5 x3` (out of the church), `D:0.25` (into the new NPC, turning to face him), A: the message window types
**「ようこそ　ちかしつへ！」**, the line the builder wrote into `param/region/r021/npc_ie` for entity id 182 (log frames 6946-6954, and again at 7083 for the second A press).
The NPC is a duplicate of the active-layer priest record `0x152C` (entity id 182, position (0, 0.5, -3.0)), standing in front of the hero in the custom wooden room that is reached through the church door.
Chain proven end to end in the emulator: **entrance (exit re-pointed) -> cloned level slot with a custom model -> an NPC added by the record tools -> A -> a line from the edited NPC dialogue bank**.
Still open: the chest (needs a donor with a real chest) and the monster fight; doing all of it from the Level Editor rather than the script.

## PROVEN: a monster model placed in the custom room (probe `cr_24056`, `docs/images/custom_room_monster.png`)

`CR_DUPID=223` (a row of Heliodor's `npc_list` whose model is a large dragon) on the duplicated active-layer record: the dragon stands in the custom room, far too big for it, and pressing A
opens its talk message ("「……。", the NPC-class actor's default line). It does **not** start a battle. (Correction: the priest record `0x152C` has entity class **0x300**, not 0x200, so the class word alone does not make an actor fight; a field monster needs something else in its record, e.g. an encounter / group reference in the words at +0x54 / +0x58 / +0x60, not decoded yet.)
Next: choose a small monster row, and test a real field-monster record (class 0x300 with a monster id and its encounter) for battle on touch. The monster's size comes from its model: the Level Editor has no per-actor scale for actors yet.

## Where field monsters are NOT (survey of all `scene.json` actors)

Of the actors whose `npc_list` model is a monster (`m` + digits) there are 133 in the whole game, and their (class, flags 54, flags 58) values are the same as the NPCs' (class 768 with 0x10000 / 0xFF0000 for 71 of
them, 2,116 NPCs share it). So these actor records are static, talkable monsters (town monsters, bosses in cutscene maps), not roaming battle symbols. Field monsters that start a battle on touch must live in a
different record kind (the editor's other arrays: placements `+0x188`, triggers `+0x1B8`, or an encounter array not decoded yet) or be spawned by the area script from `encount` tables. Next step for CL_field_monster:
open an outdoor field level (`a_*`, `b001_*`) in the editor, list every record kind that has a monster-like count, and compare with the encounter tables (`divecmn` / `monster_param`).

Survey of record kinds (exported levels only: towns `b*`, caves / dungeons `c*`, `d*`; the open-field areas `a_*` are not exported by `tools/map_tool.py` yet): actors 517, placements 774, triggers 808, exits 778,
gimmicks 296, transforms 180. Dungeon levels such as `d001_001a` have many placements (21) and triggers (7) but no actors, so roaming monsters in dungeons are probably the
**placement** records (68- / 120-byte, no typed properties decoded yet: `scene.json` gives them only a position and scale). Next for CL_field_monster: decode the placement record (compare `d001_001a` placements
with the monsters the same dungeon shows in game; vary a field of one placement in the emulator), and export the `a_*` field areas so their records can be inspected.

Field maps are the `w001`..`w002` levels (7 packs); `tools/map_tool.py` exports them with **no decoded records at all** (`game_assets/maps/w001_001a/scene.json` has 0 objects), so roaming field monsters are not in a record kind the
tools know yet. Together with the dungeon survey above: decode the unknown record arrays of a `w*` level first (compare `level_inventory.py` shapes), then the placements of a dungeon.

## Lead: the 104-byte records at container `+0x218` are probably the roaming monsters (dungeon `d001_001a`)

Container fields of a dungeon level (`level_records.Level.arrays`): `+0x230` 100-byte records (4, positions like 4.2 on one axis, tail word `0x40404003`), **`+0x218` 104-byte records (2 + 3 + 3 per container; positions
spread over the dungeon, e.g. (-50.5, ?, 5.5), (-66.5, ?, -30.0))** and `+0x248` 120-byte records (the placement kind). A 104-byte record: position at `+0x20`, then words `0x1010001 / 0x1010000`,
`0x4000ff00`, **`0x00D90002` / `0x008F0002` / `0x00DB0002` (an id in the upper half, 2 in the lower)**, `0x40030000`, a key `0x0A00....`. The ids differ per record and per dungeon, the position set is
far larger than the town NPC set: these are the best candidates for the monster symbols. Nothing here is proven; the editor does not show them (kind missing in `map_tool.candidate_objects`).
Next: add the 104-byte shape to `map_tool` (kind `symbol`, id from the word above) so the Level Editor lists and moves them, then in the emulator change one record's id word in `d001_001a` (reachable from the
Player save through the Heliodor area?) and see which monster appears.

## Probe harness for the symbol test (`tools/emu/dungeon_probe.py`, run `dun_24496`)

The church exit can be re-pointed to the dungeon `d001_001a` (level_map row 641): the hero arrives in the cave (corridor with torches and water, `out/emu/probe/dun_24496`), again with the camera hiding him behind the near wall.
`GROUP=<n> POS=x,y,z` in the script writes the group word into all 8 symbols and moves the first symbol to the given position. Next: read the 25 locator records (`+0x3b8`, 32 bytes) of the
dungeon to place a symbol right at the arrival point, then vary `GROUP` and see whether the monster that appears changes.

## SOLVED: the "layer" is the display mode, not a save layer (decompilation, `Event_Sequence_DispatchCommands` 0x1AF6B8)

The level loader starts with `mode = 1` (normal 3D view) and `mode = 2` when the script context's display mode is 3 (the game's **2D mode**, toggled in the priest's menu). For every record of
every container array it keeps the record only if `(record mask byte & mode) != 0`, then pushes it onto the script-context list. For 100-byte actors the mask is the **high byte of the class word at `+0x5E`**:
class `0x100` = created only in 3D, `0x200` = only in 2D mode, `0x300` = both. That is why:

* the house NPC (class 0x200, id 46) and the church NPC 006 (class 0x200, id 182) never appeared in 3D, in the real levels or in the clone;
* a duplicate of the priest record `0x152C` (class 0x300) works, a duplicate of `0x1010` (class 0x200) does not (`cd_23272` vs `cd_23513`);
* the "layer key" (top byte of `key 60`, 0x0A / 0x0B) is NOT the cause (it only distinguishes the two priest records).

So an NPC that should show in the normal game needs class 0x300 (or 0x100); **to make an NPC appear in 3D set its `entity class` to 768**. The Level Editor now says this in the actor Inspector
("Created only in the 2D mode (it will NOT appear in 3D)") and its Scene dock filters actors by 3D / 2D mode. The earlier "inactive layer" explanation above is superseded.

## Correction of the correction: TWO rules decide whether an actor is created (probes `cls_24932`, `cls_24978`)

1. **Display mode** (decompiled, `Event_Sequence_DispatchCommands`): the high byte of the class word (`0x100` 3D, `0x200` 2D mode, `0x300` both) is a mask against the current mode.
2. **Level group**: the top byte of the record's `key 60` word (0x0A = 10, 0x0B = 11 in the church) is a *level group id*; the area script (`b002` `OnSetupScene`) calls `SetLevelGroupEnable(10, ...)` / `(11, ...)` by quest state,
   and a record of a disabled group is not created.

Evidence: in the Player save the visible church priest is record `0x152C` (class 0x300, group 11). Copies of `0xFAC` (class 0x300, group **10**) and of the NPC `0x1010` (class 0x200, group **10**) are invisible; setting
`0x1010`'s class to 0x300 (this probe) still shows nothing, so for that record the group, not the mask, hides it. The "SOLVED: display mode" section above is therefore only half the story, and the earlier "layer" hint was half
right: it is a **level group**. To make a duplicate show, copy a record of an enabled group (11 in this save) and use class 0x300. The editor's actor Inspector now shows both facts.

## Chest attempts in the house clone with the donor collision (probes `cr_25156`, `cr_25228`)

With the house's own collision kept (`CR_PLAIN=coll`) the hero is visible and walks on the room's front part next to the house's wardrobe; the blue-white object at the back right (the house gimmick at x = 4.5) is
a book / shelf-like prop. Pressing A after walking right and up gave no item message. So the house's two "gimmick" records are still not shown to be chests, and the chest part of the demo needs a donor level with a
visibly proven chest (an item box with `interaction kind` 0 whose chest model is visible); candidates: levels with `gimmick` records of kind 0 near the entrance (use the Level Editor's Gimmicks group to find one).

## Chest via a test event in the clone: no message yet (probes `crc_27406`, `crc_27488`, `crc_27570`, script `tools/emu/custom_room_chest_probe.py`)

The proven chest read (docs/GIMMICK_DECOMP.md) runs `GimmickItemGet(GetGimmickActorID(i))` from the area script's love-letter event. The probe adds that event to `script/b002` for map id 114 (the cloned house with its
`fixed_drop_param` row 101 set to item 2) and also sweeps `i` = 0..39: the room loads and the hero is in it, but **no item message appears** within 14 A presses (about 30 s of game time). Either the
event does not fire in the clone (the church scene consumes it first, or `OnBeginScene` is not run for the slot), `GetGimmickActorID` finds no gimmick object in the clone (its object / actor ids are tied to the donor level's name), or the
house gimmicks are not chests. Next: put a `ScriptMessage` marker at the start of the event body to see whether it fires in the room, then move the same event into the church (map 109, which the Player save always loads) to test the chest read on a level that
certainly has chests (a donor with a visible item box).

Update (probes `crc_27826`, `crc_27908`): the event **does fire in the clone**. With `IEMessageSetup(182); MessageLoop(-1); MessageEnd();` in front of the chest loop the room shows NPC 182's retail lines
(「これ　すげえよなあ。…」, frames 4324-4442; `ScriptMessage(16)` as a marker shows nothing, so it is not a usable marker). The chest loop after it (`GimmickItemGet(GetGimmickActorID(i))`, i = 0..39) still produced
**no item message** within 40 A presses. So in the clone `GetGimmickActorID` finds no gimmick object (or the house's gimmick records are no chests). Next: run the same loop in the real house (map 113) and in a level with a known chest
(first check `GetGimmickActorID` there), then compare the gimmick object / actor ids between donor and clone.

## Chest result: the house gimmicks are not chests (probe `crc_28049`, `tools/emu/custom_room_chest_real_house.py`)

The same event in the REAL house (map id 113, no clone, `CR_*` off) shows NPC 182's lines and then opens nothing: `GimmickItemGet(GetGimmickActorID(i))` for i = 0..39 gives no item message in the house either.
So the clone is not the problem; the house's two gimmick records (`drop row` 101 and none) are not item boxes. The chest read that IS proven (docs/GIMMICK_DECOMP.md) was done in the Heliodor street (`b002_001a`, map id 108, 12 gimmicks).
Plan for the chest: clone the street (or another level whose gimmicks include `interaction kind` 0 = item box) instead of the house, set one item box's drop row, and run the same event there; or, simpler, keep the house room and **add** a gimmick record of kind 0
by duplicating one from the street (record-level work not done yet).
