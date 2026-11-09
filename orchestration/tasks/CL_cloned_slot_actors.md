---
lane: editor
---
Find out why NPC / monster actors do not appear in a cloned level slot, and fix it in `tools/custom_room.py`.

Context: `tools/custom_room.py build` clones the house `b002_105a` into slot `b002_106a` (level_map row 114) with a custom room model, collision, chest row and NPC lines; the room loads and the hero walks in it (docs/CUSTOM_ROOM.md, probes `cr_21523`, `cr_21791`). The house's own NPC records and an extra duplicated NPC (entity id 46 at (-1.5, 0, -2.0)) do **not** show in the room, although appended NPC records are emulator-proven in the real church. Layer mask / class / flags of the house actors equal those of the church actors, and copying level_map row 113 onto row 114 did not help.

Look at: what loads actor models for a level (`Field_LoadNpcIeResources` and the model load list; is it keyed by the level name or map id of the level_map row, or by `level2d` / `leveldmap`?), the actor spawn loop (`Event_Sequence_DispatchCommands`, docs/GIMMICK_DECOMP.md), and whether the slot needs its own entries in other tables (`syscmn/level_map` columns, `gamecmn` lists). Compare a slot whose row is the house itself (map id 113) with the clone.

Done when: an NPC placed in the cloned room appears and answers A with the edited text (emulator probe, events.jsonl), written down in docs/CUSTOM_ROOM.md.
Owns: tools/custom_room.py, tools/new_map.py, docs/CUSTOM_ROOM.md.
