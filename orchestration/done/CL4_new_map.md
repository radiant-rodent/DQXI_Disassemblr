# CL4_new_map - marked done by the orchestrator (2026-11-05), implemented in the editor sessions

Evidence (not re-run here): tools/new_map.py clones a level into a spare slot (level_map row claimed, level pack files, RomFS entries); docs/CUSTOM_ROOM.md: the church exit re-pointed to map id 114 leads into the cloned room in the emulator (probes cr_*), and the Level Editor's 'Clone level into slot' window (with an optional --bch model) does it from the UI.
Limit: it claims a spare level_map row; growing the table is not done.
