---
lane: emu
---
Hook this project up to the EXISTING emulator harness of the translation project. Do not write a
new harness and do not copy its code.

The user built the harness in `..\3DS_Translate\emutest\` (`az.py`, `azctl.py`,
`scenario.py`, `walkto.py`, `menutour.py`, `gdb.py`, ...) with Azahar in `_emutest\azahar\`;
read `..\3DS_Translate\docs\AGENT_GUIDE.md` first. `az.py` already takes its paths from
environment variables: `DQ11_EMUTEST` (emulator data root containing `azahar/`, `saves/`) and
`DQ11_ROM`. Use exactly that mechanism.

Owns: `tools/emu/` (wrapper only), `third_party/azahar/` / emulator data root, `.gitignore`,
`docs/TESTING_EMULATOR.md`.

1. A previous worker (interrupted) copied `az.py`/`azctl.py` into `tools/emu/` and Azahar into
   `third_party/azahar/` (391 MB). Delete the copied `az.py`/`azctl.py`. Keep a separate emulator
   data root for this project (so our runs never touch the translation project's `_emutest/`
   config, saves or logs): lay it out the way `az.py` expects (`<root>/azahar/azahar.exe`,
   `<root>/azahar/user/`, `<root>/saves/`) — move the existing `third_party/azahar` copy into it
   rather than copying again — and set it up with `emutest/setup_azahar.py`'s logic by calling it
   with the env var set, not by reimplementing it.
2. `tools/emu/__init__.py` / `__main__.py`: set `DQ11_EMUTEST` (+ `DQ11_ROM` when given), put
   `..\3DS_Translate\emutest` on `sys.path`, and re-export/call the user's modules.
   Only add small DQXI_Disassemblr-specific glue there (e.g. "boot a mod folder via
   `load/mods/<TitleID>/`", "boot `build/*.3ds` and report title-screen/crash/hang with a
   screenshot"). If something the project needs is missing from the user's harness, add it in
   the wrapper and list it in your report as a suggested addition for the translation project —
   never edit 3DS_Translate.
3. Prove: `python -m tools.emu boot build/DQXI.3ds --seconds 60 --shot out/emu/boot.png` reaches
   the title screen. Close Azahar afterwards.
4. `docs/TESTING_EMULATOR.md`: how it works (one harness, lives in the translation project),
   commands that worked.
