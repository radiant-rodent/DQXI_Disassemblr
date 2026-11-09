# Rules for every worker (read first)

You are a worker on the Dragon Quest XI (Nintendo 3DS) decompilation + editor project in
`.` (Windows; bash and PowerShell available; Python 3.12, Rust/cargo,
Node installed). The orchestrator is not available to answer questions: decide sensibly and record
your decisions in your report.

1. Read `README.md`, `orchestration/PLAN.md` and the docs your task names before changing anything.
2. Only edit the files/directories your task says you own. If you must touch a shared file
   (e.g. `viewer_rs/src/app.rs`, `viewer_rs/src/ui/panels/mod.rs`), make the smallest possible
   additive change (register your module), never rewrite other code.
3. **Never create, edit or delete anything outside `.`** except
   scratch files in your temp folder — not WSL distros (`\\wsl$`, `\\wsl.localhost`), Docker,
   program installs, system or user config, PATH, or the orchestration scripts
   (`orchestration/*.py`). If your shell or a tool is broken, do NOT try to repair the machine:
   write what is broken under `## BLOCKED` in your report and stop.
   Never modify anything in `..\3DS_Translate` (read-only source of the ROM `DQXI.3ds`
   and earlier reverse-engineering notes).
4. Never download or install software, and never enter passwords/keys. If a required tool
   (Ghidra, an emulator, devkitARM...) is missing, search the disk for it (C:\, C:\Program Files,
   %USERPROFILE%, %LOCALAPPDATA%); if not found, write what is missing to your report under
   `## BLOCKED` and finish the parts you can.
5. The bit-matching rebuild must stay green: before finishing, run `python tests/run_all.py`
   (or the subset your task names; **naming, typing and refine batches (N_, R_, R2_, G_, S_, V_)
   skip the full test run** - they only write one JSON file and the dispatcher validates it;
   a full run costs 3-6 minutes and several workers ran it at once) and `python tools/verify_project.py` if they exist, and paste
   the result summary into your report. Do not "fix" a failing check by weakening it.
6. Long commands (>10 min) — run them, wait, check output. Don't give up on slowness.
7. Everything a modder sees must be human readable: real names, comments explaining *why*,
   no `param_1`/`FUN_xxxx` left where you know better.
8. Anything exported for the game must keep running on a real 3DS/2DS: no emulator-only hacks,
   respect 3DS memory limits, keep file formats valid for the original engine.
9. Append one entry to `AGENT_LOG.md` (follow the existing entry format, agent_id = your task id).
10. **Existing knowledge — use it before reinventing anything.** `..\3DS_Translate` is
    a working English translation of this same game (read-only for you). It contains:
    - `docs/AGENT_GUIDE.md` — emulator testing, crash debugging, memory/UI-heap limits, message
      window limits, engine patches, and "Real 3DS: only ARMv6K / VFPv2 instructions in code
      caves". Read the sections relevant to your task.
    - `dq11tool/` — proven tools: `ctr/build.py` (.3ds), `ctr/cia.py` (CIA builder), `blz.py`,
      `patchfile.py`, text codec/font/word wrap, LayeredFS export.
    - `_emutest/azahar/azahar.exe` (Azahar emulator, portable, with `scripting/AzaharRPC.py`) and
      `emutest/` scripts (`az.py`, `azctl.py` input/screenshots/save states, `scenario.py`,
      `walkto.py`, `battlego.py`, `menutour.py`, `memreport.py`, `gdb.py`).
    You may READ and IMPORT from it (import its modules; don't copy them — one harness, not two),
    and run its Azahar only through `tools/emu/`, which uses this project's own emulator data root
    (see docs/TESTING_EMULATOR.md). Never write into 3DS_Translate. Never run `azahar.exe --help` (it opens a dialog on the user's screen).
    Emulator runs must not steal focus or block the desktop longer than needed; close Azahar after.
11. Never name a file or folder under `tools/` after a Python standard-library module (`types`,
    `json`, `re`, `io`, `ast`, `test`, ...): scripts run as `python tools/x.py` would import yours
    instead and every tool breaks (this happened with `tools/types/`; it is now `tools/typedb/`).
12. Write every text/JSON file as UTF-8 (`encoding="utf-8"` in Python; never the Windows default
    cp1252 — one stray cp1252 byte made a whole naming batch unreadable). Re-read what you wrote
    with a strict UTF-8 decode before finishing.
12b. Scratch output goes to `out/scratch/<task id>/`, never the repository root. On Windows shells
    `%TEMP%` and `C:\Users\...` written from bash become literal file names in the root, and `> nul`
    creates a file named `nul` — use `/dev/null` in bash.
13. Finish by writing `orchestration/done/<task id>.md`: what you did, files changed, test
    results, open problems, and suggested follow-up tasks. Be honest — say what is NOT verified.
14. **Speed rules (measured on 88 worker runs: 86% of the time is model turns, 55 minutes went into
    whole-tree searches).** Never walk or grep the whole `asm/`, `decomp/` or `include/` trees
    (`os.walk`, `grep -r`, `Get-ChildItem -Recurse`, `Select-String -Recurse`): each takes 1-6 minutes.
    `python tools/fn.py 0xADDR` gives the dossier of a function in half a second (current name, doc,
    callers and callees with names, vtable neighbours, body; `--asm 40` adds assembly, `--find TEXT`
    searches names). Read several functions per call, decide per function, write results in chunks,
    and do not write your own caller-search scripts.
