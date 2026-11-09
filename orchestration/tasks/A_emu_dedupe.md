---
lane: emu
---
Remove the duplicated emulator harness: `tools/emu/` must USE the user's harness in
`..\3DS_Translate\emutest\`, not copies of it.

Context: task A_emu_harness (report `orchestration/done/A_emu_harness.md`, read it) built a working
setup — retail rebuild and a LayeredFS mod both reach the title screen — but did it by copying
and adapting `emutest/az.py`, `azctl.py` and `setup_azahar.py` into `tools/emu/`. The user built
that harness and wants exactly one. `az.py` already reads its paths from env vars
`DQ11_EMUTEST` (data root containing `azahar/`, `saves/`) and `DQ11_ROM`.

Owns: `tools/emu/`, `third_party/azahar/` layout, `docs/TESTING_EMULATOR.md`.

1. Diff each copied file against its original in `3DS_Translate\emutest\`. Keep only the
   additions (LayeredFS mod install, framebuffer stats, UTF-16 RAM scan, title-screen
   evidence, save snapshots, boot command) in a small module, e.g. `tools/emu/extras.py`, that
   imports the user's `az`/`azctl` (put `..\3DS_Translate\emutest` on `sys.path`,
   set `DQ11_EMUTEST` to this project's data root before import). Delete the copies.
2. Keep this project's separate emulator data root (our runs must not touch the translation
   project's `_emutest/`); adjust its layout to what `az.py` expects instead of changing paths in
   code. Do not copy Azahar again.
3. Same CLI as before: `python -m tools.emu boot build/DQXI.3ds --seconds 120 --shot ...` must
   still reach the title screen, with and without `--mod`. Close Azahar afterwards.
4. Report: what was a real addition vs. an identical copy, and a short list "suggested additions
   for the translation harness" (never edit 3DS_Translate). Update docs/TESTING_EMULATOR.md.
