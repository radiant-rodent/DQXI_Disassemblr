---
lane: docs
after: M1_merge_names, E4_assets
---
Write the documentation a newcomer needs to start modding immediately.

Owns: `docs/` (all), `README.md`.
1. Rewrite README.md as a front door: what this is, screenshot list, 3 quick paths (play with a
   mod / edit data in DQXI Studio / read & change native code), link to progress page.
2. `docs/FIRST_MOD.md`: "first mod in 10 minutes" — change an item price and a line of dialogue,
   Play in emulator, export for real 3DS (Luma) — every step verified by actually running the
   commands/tools (headless where needed) and pasting real output.
3. `docs/PROJECT_TOUR.md`: folder map, engine subsystems (from the merged names: which
   subsystem lives where, main loop, scene/state machine, battle flow, script VM bindings, file
   system/packs, rendering), with links into `decomp/readable/`.
4. Check every doc for stale commands/paths (run them). Mark anything not verified.
