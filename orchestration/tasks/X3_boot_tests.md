---
lane: emu
after: A_emu_harness, A_emu_dedupe, X1_export, E1_tables, E2_text, E3_scripts
---
Prove that edits made with the project's tools actually run in the game (emulator), and enforce
the real-hardware rules.

Owns: new `tests/emu/` (opt-in, not part of the default run_all), `tools/emu/` (additions only),
`docs/EXPORT.md` (results section).

Using `tools/emu/` and the translation project's `emutest/scenario.py` / `walkto.py` /
`menutour.py` approach (read AGENT_GUIDE.md "Scenario tests" and "Saves"):
1. Empty mod (luma + 3ds targets): boots to title and into a new game / a save state.
2. Table edit (e.g. a shop price or an item's stat via `tools/table_edit.py`): visible in game
   (menu or shop screenshot, or memory read).
3. Text edit (one dialogue line via `tools/text_tool.py`): shown in a message window (screenshot
   + the text log technique from AGENT_GUIDE).
4. Script edit (assembly tier and source tier, `tools/script_build.py`): changed behaviour observed.
5. Native code edit via `code.ips`: a trivial safe change observed.
6. Add `tools/check_armv6k.py` (port the idea of `emutest/armv6check.py`): scan any changed native
   code for instructions a real 3DS (ARM11 MPCore, ARMv6K, VFPv2) cannot execute; make
   `tools/export_mod.py` run it and refuse exports that fail.
Record every result with screenshots in `docs/EXPORT.md` → "Verified in emulator". Remaining
real-hardware-only risks go in a short checklist for the user to run on their 3DS.
