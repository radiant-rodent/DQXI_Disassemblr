# CL2_collision - marked done by the orchestrator (2026-11-05), implemented in the editor sessions

Evidence (written by those sessions, not re-run here): docs/COLLISION.md has `PROVEN` sections for moving a collision shape (Heliodor church `b002_101a_chit.rcb`: the player is blocked), removing one and adding one (file grows); `tools/rcb_tool.py` decodes and writes the data and builds collision from an OBJ (`from_obj`, used by tools/custom_room.py); the Level Editor Inspector has a Collision group (pick a shape, X/Y/Z offset, saved into editor_projects/<level>.json).
Open (from the docs): actors outside the generated collision's bounding box are not created, so a custom room needs the donor's footprint or collision covering every actor (docs/CUSTOM_ROOM.md, 'Bisect result').
