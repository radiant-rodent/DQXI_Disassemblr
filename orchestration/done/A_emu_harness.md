# A_emu_harness — portable Azahar emulator harness

**Status: complete (with the limitations listed at the end).**

The resumed lane started from nothing: no `tools/emu/`, no `third_party/azahar/`, no
`docs/TESTING_EMULATOR.md`, no done report, and the previous worker's log contains only usage-limit
errors and a few reads before it stopped. Everything below was built and tested in this run.

## What was built

### 1. Portable emulator copy — `third_party/azahar/`

Copied `..\3DS_Translate\_emutest\azahar` (AzaharPlus `cf90688`, MSYS2 build,
~318 MB) **without** its `user/` folder, then:

* created an empty `third_party/azahar/user/`;
* ran the emulator once (no focus, no ROM) so it wrote its own `user/config/qt-config.ini`;
* applied the test profile via `tools/emu/az.py:SETTINGS` (Vulkan, native resolution,
  Old 3DS memory budget, unlimited speed, RPC on, no audio, fixed clock, synchronous shaders);
* created `user/load/mods/`, `saves/`, `runs/`;
* wrote `user/DQXI_EMU_PROFILE.txt` as a profile marker.

Nothing in `..\3DS_Translate` was modified. `third_party/azahar/` is in the new
`.gitignore` (the workspace is not currently a git repo, but the rule is recorded).

### 2. `tools/emu/` package

| File | Purpose |
|---|---|
| `az.py` | adapted from the translation project's `emutest/az.py` (credited in header). Paths now point at this project; adds LayeredFS mod installation, framebuffer statistics, UTF-16 RAM scanning, title-screen evidence and game-save snapshots. |
| `azctl.py` | adapted `emutest/azctl.py`; session commands `start/press/hold/walk/wait/mash/shot/status/title/read/write/save/load/frames/seq/stop` and the old `boot` sequence. |
| `setup_azahar.py` | equivalent of the translation project's setup, but our paths; idempotent, `--check`, `--source`. |
| `__main__.py` | `python -m tools.emu setup|boot|ctl|info`. |
| `__init__.py` | public API (`Azahar`, `Movie`, save/mod helpers). |

Implemented harness features:

* launch a given `.3ds`, or retail + a LayeredFS mod folder via
  `user/load/mods/0004000000199200/{romfs,exefs/code.bin}`;
* Windows `SW_SHOWNOACTIVATE` launch (no focus stealing, never minimized);
* RPC connect/attach to title id `0004000000199200`;
* input movies (`.ctm`, deterministic, works on retail) and the translation project's live RPC
  input hook (`press/hold/walk`);
* wait on emulated time, screenshots (both screens), raw framebuffer stats;
* memory read and write, UTF-16 string scans;
* game-save snapshot/install (`save`/`load`);
* crash detection from the Azahar log (ignoring `ReadBlock` lines produced by our own scans),
  emulator-exit detection, frozen-clock hang detection;
* clean shutdown of the portable process (never touches the user's own Azahar).

### 3. `python -m tools.emu boot`

`boot` automatically sends START at emulated second 430 (retail opening movie length) and reports:

* `title-screen reached` (exit 0),
* `CRASH: <first fault line>` (exit 1),
* `HANG: <why>` (exit 2),
* `ERROR: ...` (exit 3).

It always writes a screenshot and a JSON report. Title detection is **not** based on the title
strings merely existing in RAM — they are present from boot (resource cache at ~0x31E/0x320).
It requires at least two title-menu strings in the *dynamic* UI heap (`>= 0x33000000` on the
Old-3DS profile), i.e. copied into live pane buffers. A parchment-background visual fallback
covers translated menu strings.

### 4. Documentation

`docs/TESTING_EMULATOR.md`: setup, profile, boot, mod layouts, `ctl` commands, memory caveats,
saves, crash/hang semantics, exact verified commands, limitations.

## Exact commands that worked (copy-paste)

```powershell
# one-time setup (already done on this machine)
python -m tools.emu setup
python -m tools.emu setup --check
python -m tools.emu info

# retail-identical rebuild -> title screen (exit 0)
python -m tools.emu boot build/DQXI.3ds --seconds 120 --shot third_party/azahar/runs/boot/retail-title.png

# retail + LayeredFS mod (test folder with one RomFS file)
python -m tools.emu boot build/DQXI.3ds --mod %LOCALAPPDATA%\Temp\opencode\dqxi_testmod --seconds 120 --shot third_party/azahar/runs/boot/retail-mod.png

# timeout path (exit 2) and missing-ROM path (exit 3)
python -m tools.emu boot build/DQXI.3ds --no-start --seconds 15
python -m tools.emu boot does-not-exist.3ds

# step-by-step session on retail
python -m tools.emu ctl start --rom build/DQXI.3ds
python -m tools.emu ctl status
python -m tools.emu ctl frames
python -m tools.emu ctl shot ctl-boot
python -m tools.emu ctl read 0x10002000 8
python -m tools.emu ctl stop
```

Observed results (three retail runs and the mod run all reached the title in 37–41 s real;
the final re-run after the last code edit used the same command with `retail-final.png`):

```text
title-screen reached at game t=444.6s (37.0s real; menu strings in the UI heap)
  title text '冒険の書をつくる' in UI heap at 0x33DA0E40
  title text 'ふっかつのじゅもん' in UI heap at 0x33DA0E20
  title text 'プレゼントコード入力' in UI heap at 0x33DA0E00
  title text '冒険をする' in UI heap at 0x33D89370
  title text '中断した冒険をする' in UI heap at 0x33DA0720
screenshot: third_party/azahar/runs/boot/retail-title.png
```

The mod boot also reached the title (game t=444.6s, 37s real) and Azahar's log confirmed the
overlay:

```text
Service.FS <Info> core/file_sys/layered_fs.cpp: operator(): LayeredFS replacement file in use
for /3d/motion/npc001_001_003_csl.pack
```

Proof images kept in `third_party/azahar/runs/boot/` (`retail-title.png`, `retail-final.png`,
`retail-mod.png`, `timeout.png`) — machine-local and gitignored. The JSON reports next to them
contain the timings, title addresses and framebuffer statistics.

## Files changed / created

* `tools/emu/__init__.py` (new)
* `tools/emu/az.py` (new)
* `tools/emu/azctl.py` (new)
* `tools/emu/setup_azahar.py` (new)
* `tools/emu/__main__.py` (new)
* `third_party/azahar/` (new local emulator copy + user/saves/runs; **not committed**)
* `docs/TESTING_EMULATOR.md` (new)
* `.gitignore` (new; ignores `third_party/azahar/` and the package cache)
* `orchestration/done/A_emu_harness.md` (this report)
* `AGENT_LOG.md` (one entry appended)

No shared project file (`viewer_rs/src/app.rs`, `ui/panels/mod.rs`, etc.) was touched.

## Test results

```text
python tools/verify_project.py
OVERALL: PASS -> audit/PROJECT_VERIFICATION.json
```

```text
python tests/run_all.py
Tier 1: Feature Coverage           70/70  PASS
Tier 2: Boundary & Corner Cases    70/70  PASS
Tier 3: Pairwise Combinations      14/14  PASS
Tier 4: Real-World Scenarios       62/62  PASS
TOTALS                            216/216 SUCCESS (exit 0)
```

Also checked:

* `boot` exit codes 0 (title), 2 (timeout/hang), 3 (missing ROM).
* `ctl start/status/frames/shot/read/stop` on the retail ROM; `hook alive: False` is expected
  (retail has no input hook).
* game-save `export_save`/`install_save` round-trip with a marker file.
* crash-regex unit check: guest fault lines match, `ReadBlock` lines are ignored.
* no `azahar.exe` left running after each test; no dialog ever opened.

## Decisions taken (orchestrator not available)

1. **Title detection uses live pane copies, not resource presence.** The first working version
   reported the title at game t=48.8s while the opening movie was playing, because the title
   text table is preloaded. Fixed by requiring copies in the dynamic UI heap at `0x33…`.
2. **`boot` sends START at 430 emulated seconds.** Without input the retail game waits on the
   opening-movie logo card forever, so "title-screen reached" would never be true. The movie
   clock is deterministic; a second press at 520s is only a fallback.
3. **`--seconds` is wall-clock seconds**, not game seconds, because it controls how long the
   operator waits. The JSON report records both clocks.
4. **"Save/load state" implemented as portable game-save snapshots**, not Azahar emulator save
   states. Emulator states need a UI hotkey (forbidden window driving), are tied to one Azahar
   build and contain stale code/heap — the translation project's guide says the same.
5. **RAM writes to the `0x08000000` linear-heap alias are documented as unreliable.** Azahar's
   RPC returns success but reads back unchanged; writes in `.bss`/`.data` work. Reads are
   unaffected, so the harness's scanning/detection is safe.
6. Mod paths are normalised from `out/luma`, `out/luma/titles/<TitleID>`, any `romfs/` root and
   `.../romfs`; a Luma `code.ips` is rejected with an explanation (Azahar needs `exefs/code.bin`).

## Open problems / NOT verified

* **No crashing ROM was available**, so the crash branch was only unit-checked against known
  log signatures, not observed live. The hang branch was exercised only via the `--seconds`
  timeout, not a genuinely frozen guest clock.
* **No real 3DS/2DS hardware test.** This is emulator tooling only; the profile targets an Old
  3DS memory budget, but hardware compatibility of future mods remains the exporter's job.
* **`ctl press/hold/walk` cannot drive the retail ROM** because it has no input hook; on retail
  use input movies. Porting `testhook.py`/scenario text logging is future work.
* **Title detection is calibrated to the retail Japanese title data on the Old-3DS map.** The
  visual fallback is a heuristic for translated builds. A mod that changes both the menu text
  and the title background would need a new detector.
* **No portable game saves are shipped.** `third_party/azahar/saves/` is empty; the harness can
  snapshot saves once a session writes one. Copying the translation project's saves may mix in
  its translated data and was deliberately not done.
* **Emulator save states are not supported** (see decision 4).
* **First-run shader compilation** adds real time (the tests still reached the title in ~37–41s
  real at unlimited speed). Subsequent runs reuse `user/shaders/`.
* The test mod used for the LayeredFS proof was a 128-byte byte-identical RomFS file; it proves
  the mount and the log line, not a visibly changed asset.

## Suggested follow-up tasks

1. **X2_playtest** — wire the editor's "Play" button to `python -m tools.emu boot` (export mod →
   `--mod`, stream the title/crash result into the UI). Everything needed is in `tools/emu`.
2. **X3_boot_tests** — a small matrix runner: `build/DQXI.3ds`, `build/DQXI_patched.3ds`, and
   each Luma export under `out/`, asserting exit 0 and keeping the screenshots/JSON. This would
   also give the crash/hang branches real coverage once a deliberately broken build exists.
3. **Visibly provable LayeredFS test** — replace a small texture or a title menu string with a
   recognisable marker, then assert on the screenshot (would validate screenshot-diff helpers).
4. **Port the test-only input hook / text log** into this project's export pipeline if future
   lanes need live `press`/`walk` or scenario text recording; until then, movies are enough for
   boot smoke tests.
5. **Copy two known-good game saves** (a fresh-start save and one at Cobblestone) into
   `third_party/azahar/saves/` after checking they are not tied to translated code, so later
   lanes can boot into the field instead of the title.
