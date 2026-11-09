# X2_playtest — one-click Export & Play in DQXI Studio

**Status: completed (Play clicked in the real GUI; no real 3DS/2DS — see §8).**

Resumed lane. There was no earlier X2 work on disk: no `viewer_rs/src/ui/panels/playtest.rs`, no
registration in `app.rs`/`panels/mod.rs`, no `orchestration/done/X2_playtest.md`, no X2 log entry.
The dependencies did exist and were used unchanged: `tools/export_mod.py` (X1), `tools/emu/`
(A_emu_harness/A_emu_dedupe) and `docs/TESTING_EMULATOR.md`.

---

## 1. What the panel does

New section **Export & Play** in the sidebar, plus **Export** and **Play** buttons in the top bar.
The panel is a driver for the already-validated tools; it does not reimplement the exporter or
the emulator.

### Export tab

- **Target**: Luma LayeredFS folder (default), rebuilt `.3ds` image, or installable CIA.
- **Output folder** (default `out/`), shown as the resolved absolute path.
- **Save state** picker listing `third_party/emutest/saves/*` (plus "clean boot").
- **Options**: title-screen smoke test; deep asset validators; `.3ds` → `romfs.bin` only.
- **Emulator**: Vulkan/OpenGL/software and a real-seconds timeout.
- **Export …**, **▶ Play**, **Run checks**, **Stop emulator**.
- Live log of the exact `python …` command, streamed line by line (no frozen window).
- Pre-flight result table (OK / WARN / ERROR), the boot verdict (title/crash/hang, game time,
  basis) and the title-screen screenshot from the smoke test.

### Play

1. Runs the same pre-flight checks; any error stops before writing.
2. Always exports the **Luma** target (`Azahar`'s LayeredFS needs that layout). The target combo
   is still used by Export.
3. Runs `python -m tools.emu boot build/DQXI.3ds --mod out/luma --seconds N --shot … --gpu …`.
   - smoke test on: boots, auto-presses START at the end of the opening movie, waits for the
     title menu, screenshots it, writes the harness JSON and closes the emulator;
   - smoke test off: same command with `--keep-open`, leaving Azahar at the title screen for
     interactive play. **Stop emulator** closes the `ctl` session *and* any leftover
     `azahar.exe` from this project's own `third_party/emutest` (path-matched, same rule the
     harness uses), because one fixed RPC port/user dir means a stale instance would make the
     next Play fail.
   - a selected save is passed as `--save`.

### Changes tab

Every payload file in `mod/` compared with the retail bytes (`game_data/romfs/<path>`, or
`original/exefs/code.decompressed.bin` for `code/code.bin`): MODIFIED / ADDED / identical / CODE,
sizes, retail size, note. **Revert** asks once, deletes the override, prunes empty directories and
rescans. `mod.json` is metadata and is not offered as an override.

### Settings tab

- **SD card root** + **Copy to SD**: removes the previous `<SD>/luma/titles/<TitleID>` and copies
  the freshly exported folder there (so no stale override survives). Refuses a missing path and
  refuses to copy into the project folder.
- Read-only list of project/mod/output/ROM/emulator/save/screenshot paths.
- Explains the smoke/keep-open behavior and why "save states" are portable game saves, not
  Azahar UI snapshots.

Settings are persisted in `editor_projects/playtest_settings.json` (created on first change).

---

## 2. Pre-flight validation (blocks export)

Always (fast):

| Check | Failure is |
|---|---|
| `mod.json` parses (if present) | ERROR; missing file is only WARN |
| every `mod/romfs/<path>` exists in the retail RomFS | **ERROR** — LayeredFS cannot add files |
| every changed file really differs (identical = warning) | WARN |
| every changed `PACK`/`PACA` parses with `tools/pack.py` | **ERROR** |
| `mod/code/code.bin` is exactly 7,090,176 bytes | **ERROR** |
| `tools/check_armv6k.py` finds no ARMv7/VFPv3 instruction in changed code | **ERROR** (Azahar would run it; real hardware would fault) |

Optional **Deep asset validators**: `tools/verify_assets.py --sample 20` (~15 s) and
`tools/verify_model_textures.py` (~72 s on this machine).

After writing, the panel also checks `out/EXPORT_REPORT.json`'s `ok` flag, so a successful exit
code with an invalid report is still reported as a failure. The CIA target is passed through to the
same exporter; `tools/ctr_cia.py` (landed by X4_cia during this session) builds and re-verifies a
fakesigned archive. I ran the exact command the panel uses on an empty mod in a temp folder:
`python tools/export_mod.py --target cia --mod <tmp>/mod --out <tmp>/out` -> exit 0,
`DQXI_modded.cia` 2,685,129,728 B + `README.txt`, both validated. I did not click the CIA combo in
the GUI (the panel would run that same command and show the log).

---

## 3. Files changed

**New**

- `viewer_rs/src/ui/panels/playtest.rs` — the panel, background job runner, validators, change
  scanner/revert, SD copy, settings persistence, streaming log, screenshot view, and 11 unit tests.

**Minimal registrations / small shared edits**

- `viewer_rs/src/ui/panels/mod.rs` — `pub mod playtest`, `Panels::playtest`, F5 refresh arm.
- `viewer_rs/src/app.rs` — `Section::Playtest` (+ title, icon, `DQXI_START_SECTION=playtest`,
  central/refresh/status arms), the top-bar **Export**/**Play** buttons, and a bounded width for
  the header search field (it previously expanded to infinity and pushed the new buttons off the
  window; 420 px keeps every header action visible at the 1120 px minimum width).
- `docs/EDITOR.md` — new "Export & Play" section (targets, Play modes, checks, Changes, SD copy,
  limits). Only additive.
- `AGENT_LOG.md` — one entry, `agent_id = X2_playtest`.

No Python tool, test, game data, asset, ROM, `original/` file or `3DS_Translate` file was changed.
`mod/` was left empty (the honest retail baseline); the test files created while exercising
Changes/Revert were deleted through the panel itself.

---

## 4. Decisions recorded

1. **Play always exports Luma.** A `.3ds` image is not what Azahar's LayeredFS consumes, and
   booting a different artifact than the user picked would be confusing. The UI says so in the
   Settings tab and in the Play tooltip.
2. **Validation is a hard gate, not advice.** A path that does not exist in the retail RomFS is
   an error because both Luma and the RomFS rebuilder only replace existing files.
3. **ARMv6K check is mandatory for native code.** It is the one check the emulator cannot make.
4. **Revert deletes the override** (with a one-click confirmation) instead of trying to restore
   bytes: `mod/` holds replacements; the retail copy is never touched.
5. **Copy to SD replaces the title folder.** Stale files in a LayeredFS title folder silently
   apply; deleting the old copy is safer than merging.
6. **Stop emulator also path-kills a leftover project Azahar.** Observed during this task: the
   harness can lose a boot process (its `boot` returned "emulator exited during boot" while a
   real `azahar.exe` from `third_party/emutest` stayed alive), and the next Play then failed
   because the RPC port/user dir was in use. The kill is limited to this project's emulator path.
7. **Settings live in `editor_projects/playtest_settings.json`**, next to the user's editor
   projects, not in `build/` (scratch) or `mod/` (shipped payload).

---

## 5. Actual Play run (clicked in the GUI, final debug build)

Launched `viewer_rs.exe` with `DQXI_START_SECTION=playtest`, moved the pointer to the top-bar
**▶ Play** button and clicked it with real `WM_LBUTTONDOWN`/`UP` events (a small PowerShell
window driver, not a hidden code path). The panel then ran the checks, exported Luma and booted
Azahar. Result:

```text
Play OK: title screen reached and the emulator was closed. Screenshot below.
Last boot  TITLE  game t=433.8s, 46.6s real  menu strings in the UI heap
...
$ python -u -m tools.emu boot C:\...\build\DQXI.3ds --mod C:\...\out\luma
    --seconds 120 --shot C:\...\third_party\emutest\runs\playtest\play-1792961998.png --gpu vulkan
...
emulator started (pid 7348); waiting up to 120s real (game runs ~10-20x)
  t=75.6s real=14.0s screen 400x480 mean=48.8 nonblack=47%
  t=181.0s real=24.4s screen 400x480 mean=67.5 nonblack=50%
  t=310.8s real=34.4s screen 400x480 mean=16.1 nonblack=46%
  t=390.6s real=44.5s screen 400x480 mean=64.0 nonblack=47%
title-screen reached at game t=433.8s (46.6s real; menu strings in the UI heap)
  title text '\u5192\u967a\u306e\u66f8\u3092\u3064\u304f\u308b' in UI heap at 0x33DA0E40
  ...
screenshot: ...\third_party\emutest\runs\playtest\play-1792961998.png
```

The panel displayed the screenshot of the live title menu (冒険の書をつくる / ふっかつのじゅもん /
プレゼントコード入力 on the parchment background). The emulator process was gone afterwards.

Evidence files (machine-local):

- `third_party/emutest/runs/playtest/play-1792961998.json` — `outcome: title`,
  `basis: menu strings in the UI heap`, `game_seconds: 433.82`, `real_seconds: 46.6`,
  `screen: 400x480 mean 104.2 nonblack 89.8%`, `emulation_speed: 31.7x`;
- `third_party/emutest/runs/playtest/play-1792961998.png` — the screenshot shown in the panel;
- panel screenshots used during the click-through are in
  `%TEMP%\opencode\x2_*.png` (checks blocked, changes/revert, settings, final Play).

A second click of Play immediately afterwards failed with `ERROR: emulator exited during boot`
because another worker's Azahar was running at the same time (the process had
`runs/boot/input.ctm` on its command line, not ours). After that instance exited, the next click
succeeded as pasted above. This is the shared-harness single-instance limitation, not a panel
logic bug; **Stop emulator** now cleans up a leftover project Azahar to recover from it.

---

## 6. Tests / verification (final state)

```text
cargo build                     -> Finished dev profile, exit 0
cargo build --release           -> Finished release profile, exit 0
                                   viewer_rs\target\release\viewer_rs.exe 12,086,784 B 22:24
cargo test                      -> test result: ok. 70 passed; 0 failed; 1 ignored
                                   (11 of them are the new playtest unit tests)
python tests/run_all.py         -> TOTALS 223 / 223 pass, 0 fail, 0 skip -> SUCCESS (235.05 s)
python tools/verify_project.py  -> OVERALL: PASS -> audit/PROJECT_VERIFICATION.json
python tools/verify.py          -> Manifest 16/16 PASS + bit-matching repacked ROM PASS
python tools/export_mod.py --target cia --mod <tmp>/mod --out <tmp>/out
                                -> EXPORT OK, 2,685,129,728 B DQXI_modded.cia + README.txt, validated
```

One intermediate `run_all.py` run showed 7 failures in scenario 9 (`mod export`) because another
worker was rewriting `tools/export_mod.py`/the scenario at that moment: the staged
`mod/romfs/syscmn.pack` vanished from that test's temp directory. Re-running the scenario alone
(`python -m unittest tests.tier4_real_world.test_scenario_9_mod_export -v`) gave **23/23 OK in
215 s**, and the final full run above is **223/223**. No check was weakened.

The new unit tests cover: streaming file comparison, modified/identical/added classification,
native `code/code.bin` classification, export-report title ID, settings round-trip, forward-slash
paths, log-line trimming, human labels, validation (added path = ERROR, replacement = OK, bad
`mod.json` = ERROR), revert deleting the override, and Copy-to-SD replacing an old copy.

---

## 7. Open problems / not verified

1. **No real 3DS/2DS.** Hardware export validity was verified by the existing exporter/tests;
   this task only adds the UI. Luma patch loading on a console is still untested.
2. **Copy to SD was unit-tested, not tried on a real SD card** (none attached). The code copies
   only `<SD>/luma/titles/<TitleID>`, after deleting the previous copy.
3. **Interactive mode (smoke test off) was not run end-to-end.** It is the same harness command
   with `--keep-open`, which the docs already verify, but I only exercised the smoke path.
4. **Save-state selection was not booted.** The picker lists the four real save folders
   (`cobblestone_start`, `user_citra`, `user_citra_2d`, `user_citra_3d`); the `--save` argument
   path is the harness's tested one, but no run was made with a selected save.
5. **Title detection inherits the harness limits**: calibrated for the retail Japanese title
   data (parchment fallback for translated menus); a mod that changes the boot movie or the whole
   title background may need `--no-start` plus a custom input movie, which the panel does not
   expose.
6. **Shared emulator is single-instance.** Concurrent workers' Azahar runs (or a user's own
   instance on the same RPC port/user dir) can make Play report `emulator exited during boot`.
   Stop emulator mitigates a leftover *project* instance; it does not coordinate with another
   process.
7. **CIA export through the panel UI was not clicked** (the backend command was: see §2). X4_cia
   landed the installable CIA (`tools/ctr_cia.py`, fakesigned) while this task was in progress; the
   panel passes `--target cia` to the exporter unchanged. Installing on a real console is still
   unverified (`docs/EXPORT.md` §7).
8. **Settings file is created on first change**, not on first open; a fresh checkout has no
   `editor_projects/playtest_settings.json` until a setting is touched (defaults are used).
9. `Play` needs `python` on `PATH`, `build/DQXI.3ds` and the project Azahar under
   `third_party/emutest/`; the panel names the missing path rather than guessing.

---

## 8. Suggested follow-ups

1. Add a **"boot with selected save + drive to the field"** preset once X3_boot_tests has a stable
   title→Continue→field sequence; the panel currently stops at the title screen.
2. Add an **input-movie picker** (`--no-start --movie …`) for mods that change the opening.
3. Test **Copy to SD on real hardware** and record the exact Luma menu path (SELECT at boot →
   "Enable game patching").
4. Consider a **single-instance guard**: if a project `azahar.exe` is already running, ask before
   killing it instead of relying on the harness's unconditional path-matched kill.
5. Click the **CIA target in the panel** once and confirm the summary/README appear; the underlying
   command already builds and validates the archive (2,685,129,728 B) and scenario 9 covers it.
