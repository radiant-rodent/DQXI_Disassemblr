# A_emu_dedupe — one emulator harness, no copies

**Status: complete.** `tools/emu/` now imports the user's harness from
`..\3DS_Translate\emutest\` (`az.py`, `azctl.py`, `setup_azahar.py`) unchanged. The
three copied modules are deleted; only the project-specific additions remain, in
`tools/emu/extras.py`. Retail and LayeredFS boots still reach the title screen.

---

## What changed

| file / path | change |
|---|---|
| `tools/emu/az.py` (28,011 B) | **deleted** (adapted copy of `emutest/az.py`) |
| `tools/emu/azctl.py` (8,000 B) | **deleted** (adapted copy of `emutest/azctl.py`) |
| `tools/emu/setup_azahar.py` (4,600 B) | **deleted** (re-implementation of `emutest/setup_azahar.py`) |
| `tools/emu/extras.py` | **new** (27.6 KB): env/data-root wiring, harness import, LayeredFS mod install, framebuffer stats, UTF-16 RAM scan, title evidence, `setup`/`ctl` glue |
| `tools/emu/__main__.py` | rewritten to use the harness (`boot` verdict, screenshot + JSON report, CLI) |
| `tools/emu/__init__.py` | rewritten to export `make_emu`/`new_movie`/`load`/paths (no copied classes) |
| `third_party/azahar/` → `third_party/emutest/azahar/` | **moved** (rename, instant); `saves/` and `runs/` moved up into `third_party/emutest/` so the layout is exactly what `az.py` expects |
| `.gitignore` | `/third_party/azahar/` → `/third_party/emutest/` |
| `docs/TESTING_EMULATOR.md` | rewritten: one harness, data root, env vars, verified results |
| `orchestration/done/A_emu_dedupe.md` | this report |
| `AGENT_LOG.md` | one entry appended |

Nothing in `..\3DS_Translate` was modified: `git status --porcelain` there is empty,
and `az.py` / `azctl.py` / `setup_azahar.py` still hash to the values they had before this task
(`B44807C2…`, `591E9308…`, `21897CCD…`). One `__pycache__/setup_azahar.cpython-312.pyc` that our
first setup run wrote there was removed, and `sys.dont_write_bytecode` is now set around every
import of the harness so it cannot happen again.

## Data root (what `az.py` expects, unchanged code)

```
third_party/emutest/                <- DQ11_EMUTEST
  azahar/azahar.exe                 portable Azahar (ONE copy, not copied again)
  azahar/user/                      config, sdmc, shaders, logs
  azahar/user/load/mods/<TitleID>/  installed LayeredFS mod (ours)
  saves/                            game-save snapshots
  runs/                             screenshots, JSON reports, ctl session state
  code_jp.bin                       extracted by the user's setup for armdis.py
```

`extras.py` sets `DQ11_EMUTEST` to that root and `DQ11_ROM` to `build/DQXI.3ds` **before**
importing `az`, so the harness code is untouched and our runs never read or write the translation
project's `_emutest/`. `DQXI_EMUTEST_SRC` overrides the harness location.

`python -m tools.emu setup` migrates the old layout if it finds it, installs one emulator copy
only on a fresh machine, then calls the user's `setup_azahar.main()` with the env vars set (the
profile, `qt-config.ini` generation and `code_jp.bin` extraction are all theirs). A side effect
worth knowing: our root now has `code_jp.bin` (7,090,176 bytes, SHA-256 `DFCD1B7A…`, identical to
`original/exefs/code.decompressed.bin`), so `emutest/armdis.py` can be pointed at our ROM.

## Real addition vs. identical copy

Diffed each copied file against its original (`git diff --no-index`): `az.py` was 371 → 646
lines, `azctl.py` 123 → 209 lines. Most of that was re-wording/re-wrapping; the **functional**
additions were:

| addition | was a real addition? | where it lives now |
|---|---|---|
| LayeredFS mod install (`resolve_mod`, `install_mod`, `mod=`, Luma layouts, `code.bin`→`exefs/code.bin`, reject `code.ips`/`code.bps`) | yes (harness has none; its `build_test.py` writes the mod dir itself) | `extras.py` |
| framebuffer stats (`screen_rgb`, `screen_stats`) | yes | `extras.py` (`_Evidence`) |
| UTF-16 guest-RAM scan (`find_utf16_many/all/find_utf16`) | yes | `extras.py` (`_Evidence`) |
| title-screen evidence (`TITLE_TEXTS`, `TITLE_SCAN`, `title_evidence`, visual fallback) | yes | `extras.py` (`_Evidence`) |
| save guards (`EmuError` instead of silently missing save; `FileNotFoundError` on export) | yes, small | `extras.py` (`Emu.__init__/start`, `ctl start`) |
| `EmuError`, ROM/emulator presence checks | yes, small | `extras.py` |
| `ctl read/write/frames/title/save/load`, `status --title`, session state cleanup | yes | `extras.py` (`ctl_main`) |
| `boot` (START at 430 s, title/crash/hang verdict, screenshot + JSON) | yes (project-specific, never a copy) | `__main__.py` |
| `wait_real`, `require_hook`, `perf_reset` re-order, `shot()` makedirs, `dqxi-dis` movie header tag | **dropped**: unused, cosmetic, or already in the harness | — |
| `Movie` container format, `SETTINGS`, `CRASH_RE`, `Azahar.attach/stop/log/crashed/game_time/wait_game/press/hold/stick/walk/shot`, `azctl.Session/alive/crashed/press/hold/walk/wait/mash/shot/boot` | **identical copies** (no change kept) | now imported from `emutest` |

`Emu` is a subclass of the harness's `az.Azahar` that only adds `mod=` plus the pre-launch
`install_mod`; `Session` is a subclass of `azctl.Session` that only adds the evidence mixin. No
harness logic was re-implemented.

## Verification (final tree)

```text
python tools/verify_project.py
OVERALL: PASS -> audit/PROJECT_VERIFICATION.json

python tests/run_all.py
Tier 1: Feature Coverage       70/70 PASS
Tier 2: Boundary & Corner Cases 70/70 PASS
Tier 3: Pairwise Combinations   14/14 PASS
Tier 4: Real-World Scenarios    62/62 PASS
TOTALS                        216/216 SUCCESS (exit 0)
```

Emulator proof (the exact CLI from the task still works):

```text
python -m tools.emu boot build/DQXI.3ds --seconds 120 --shot ...dedupe-retail-final.png
title-screen reached at game t=511.9s (39.4s real; menu strings in the UI heap)
  title text '冒険の書をつくる' in UI heap at 0x33DA0E40  ... (5 strings)
screenshot: third_party\emutest\runs\boot\dedupe-retail-final.png   exit 0

python -m tools.emu boot build/DQXI.3ds --mod <tmp mod> --seconds 90 --shot ...dedupe-mod-final.png
title-screen reached at game t=474.8s (43.7s real; menu strings in the UI heap)     exit 0
Azahar log: "LayeredFS replacement file in use for /3d/motion/npc001_001_003_csl.pack"
```

(Detection time varies by a few seconds between runs because the RAM scan is periodic; one earlier
run was caught by the visual fallback, which now re-checks the RAM strings and labels the report
honestly instead of saying "menu strings translated".)

Other branches and self-checks:

* `--no-start --seconds 15` → `HANG`, exit 2; missing ROM → exit 3; `--save` that does not exist
  → exit 3; `ctl status` with no session → exit 3.
* `ctl start/status/frames/shot/read/stop` on retail: exit 0, PID attach works,
  `hook alive: False` (expected on retail), image in `runs/ctl/`.
* `setup --check` exit 0; `setup` exit 0 (runs the user's script; `code_jp.bin` hash matches).
* No `azahar.exe` process left after any command (checked after boot, ctl and setup).
* Scripted self-check (`%TEMP%\opencode\check_emu_extras.py`): legacy-layout migration is a
  rename and idempotent; `resolve_mod` handles `out/luma`, `titles/<TID>`, `romfs` root and
  `exefs` root and rejects a foreign `titles/`; `install_mod` copies 2 files and removes them
  with `None`; a `code.ips` mod is rejected before anything is copied; `printable()` escapes
  Japanese on a cp1252 console instead of crashing.
* The title screenshot was inspected: top screen shows the Japanese title menu.

## Decisions taken (orchestrator not available)

1. **Data root is `third_party/emutest/`,** i.e. the emulator lives at
   `third_party/emutest/azahar` and saves/runs are siblings. The emulator was **moved**, never
   copied again; `setup` still knows how to migrate the old `third_party/azahar` layout.
2. **The wrapper owns only glue.** `Emu`/`Session` subclass the harness classes; no `az`/`azctl`
   logic was rewritten. `setup` calls the harness's own setup instead of re-implementing it.
3. **`sys.dont_write_bytecode` around harness imports.** Importing from the read-only checkout
   otherwise creates `__pycache__` there (it happened once during testing); the stray `.pyc` was
   deleted and re-runs write nothing.
4. **`printable()`:** the title strings are Japanese; printing them on a cp1252 console raised
   `UnicodeEncodeError` and turned a successful boot into exit 1. Console output is escaped when
   needed; the JSON report keeps the real characters.
5. **LayeredFS patch validation happens before any copy,** so a rejected `code.ips`/`code.bps`
   never leaves a half-installed mod behind.
6. **Visual title fallback re-checks the RAM evidence** and the report's `basis` states which
   proof was used; the old text claimed "menu strings translated" even on the Japanese retail ROM.
7. Plot/CLI compatibility kept: `boot`, `ctl …`, `info`, `setup --check`; `--gpu`, `--extra`,
   `--save`, `--no-start`, `--keep-open` unchanged.

## Suggested additions for the translation harness (never edited)

1. `Azahar(..., mod=...)` + a `install_mod`/`resolve_mod` helper (Luma layout normalisation,
   `code.bin` → `exefs/code.bin`, early rejection of `code.ips`). Their `build_test.py` writes
   `user/load/mods/...` directly; the resolution rules would remove duplication across scripts.
2. `screen_stats()` (mean/non-black of `screenshot_raw()`) — a cheap liveness and
   "title background is up" check that does not need the vision model.
3. A reusable read-only UTF-16 range scanner (`find_utf16_all`, 32 KiB chunks + overlap). They
   have `watchrun.py u16:TEXT` (halting watchpoint) and one-off scans; a non-halting scan fits
   `report.py`/`scenario.py`.
4. `ctl read/write/frames/save/load/title` and `status --title` in `azctl.py`; today memory and
   save snapshots need ad-hoc scripts.
5. `setup_azahar.py --check` (report missing paths, change nothing) and a friendlier
   `EmuError`/`ensure_installed` instead of `FileNotFoundError` from the INI/executable.
6. `setup_azahar.py` currently `copytree`s the whole source tree; if the source is another data
   root it copies that project's `user/` profile verbatim. Excluding `user/` would make it safe.

## Open problems / NOT verified

* **No crashing ROM** was available, so the CRASH branch (exit 1) is still only unit-checked via
  the log regex, not observed live; HANG was exercised only through `--seconds`, not a genuinely
  frozen guest clock.
* **The fresh-machine install path was not exercised**: the emulator already existed, so
  `setup` took the "adopt/migrate" branch. The migration function itself is covered by the
  scripted self-check with a fake tree, but the 320 MB `copytree` from another checkout was not
  run in this task (by design — "do not copy Azahar again").
* **No real 3DS/2DS test** (emulator tooling only; profile is Old-3DS on purpose).
* The LayeredFS proof still uses a **byte-identical** 128-byte RomFS file
  (`3d/motion/npc001_001_003_csl.pack`): it proves the mount and the switch, not a visible asset
  change. X3_boot_tests should replace this with a visible edit.
* The title detector remains calibrated to retail Japanese data on the Old-3DS map; a mod that
  changes both menu text and title background needs a new detector.
* `ctl press/hold/walk` still cannot drive retail (no test input hook); use input movies.

## Suggested follow-up tasks

1. **X2_playtest** — call `tools.emu.make_emu(...)` (mod export → `--mod`, stream title/crash
   into the UI). The API is `make_emu(rom, mod=...)`; no harness import needed.
2. **X3_boot_tests** — boot matrix (`build/DQXI.3ds`, `DQXI_patched.3ds`, each `out/` export) with
   screenshot assertions; use `extras.install_mod` and the JSON reports.
3. **Visible LayeredFS test** — replace one title menu string or a texture, then assert on the
   screenshot/title evidence; this would also give the crash branch real coverage with a
   deliberately broken build.
4. Add two known-good game saves to `third_party/emutest/saves/` (after checking they do not
   carry translated data) so lanes can boot into the field.
5. If later lanes need live input on retail, port the translation project's test input hook into
   this project's export pipeline (never edit `emutest`).
