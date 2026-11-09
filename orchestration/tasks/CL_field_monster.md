---
lane: editor
---
Make a placed monster start a battle on touch.

Context: `tools/custom_room.py` can place any model of a region's `npc_list` in the custom room as an actor (docs/CUSTOM_ROOM.md, `cr_24056`: a dragon stands in the room and talks on A) but no battle starts. The record class word (`+0x5C`, 0x300) is the same as the priest's, so a field monster must differ elsewhere: compare the actor records of a level with visible field monsters (a field area such as `a_010_*`) with an NPC record, look at `+0x54` / `+0x58` / `+0x60` and the area script (`StartBattle`-style natives, `GetActorRegionCharacterID`), then set the same values on a duplicated active-layer record.
Done when: walking into the placed monster in the custom room starts a battle in the emulator (screenshot of the battle screen, events.jsonl), written down in docs/CUSTOM_ROOM.md and exposed in the Level Editor's actor Inspector (monster / NPC switch).
Owns: tools/custom_room.py, tools/level_records.py, docs/CUSTOM_ROOM.md.
