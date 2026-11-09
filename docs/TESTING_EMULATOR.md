# Testing in the emulator (Azahar)

This project does **not** ship its own emulator harness. It uses the user's proven harness from
`..\3DS_Translate\emutest\` (`az.py`, `azctl.py`, `setup_azahar.py`, …), imported
unchanged, with this project's own emulator data root and ROM. There is exactly one copy of the
harness code and exactly one portable Azahar install for our runs.

```
..\3DS_Translate\emutest\   harness code (read-only for us, never edited)
third_party\emutest\                    THIS project's data root (gitignored, machine-local)
  azahar\                                 portable Azahar (one copy, ~320 MB)
  azahar\user\                            its config, sdmc, shaders and logs
  saves\                                  game-save snapshots ("save states")
  runs\                                   screenshots, JSON reports, ctl session state
  code_jp.bin                             decompressed JP .code extracted by setup (armdis.py)
```

`tools/emu/` is only the glue:

| file | what it is |
|---|---|
| `extras.py` | the additions: env/data-root wiring, LayeredFS mod install, framebuffer stats, UTF-16 RAM scan, title-screen evidence, `setup`/`ctl` glue |
| `__main__.py` | the `boot` verdict (title / crash / hang + screenshot + JSON report) and the CLI |
| `__init__.py` | public API (`make_emu`, `new_movie`, `load`, paths) |

`az.py` reads its paths from the environment, which is how the same code serves both projects:

| variable | value for this project |
|---|---|
| `DQ11_EMUTEST` | `third_party\emutest` (data root; `azahar/`, `saves/`, `runs/`) |
| `DQ11_ROM` | `build\DQXI.3ds` (default when not set) |
| `DQXI_EMUTEST_SRC` | where the harness code lives, if not the default above |
| `AZ_SETTINGS` | per-run qt-config overrides, e.g. `graphics_api=1` (the harness's own variable) |

> Emulator testing is only a fast smoke test. Anything you ship for a real 3DS/2DS must also be
> valid on hardware: no emulator-only formats, ARMv6K/VFPv2 only in code caves, and the Old 3DS
> memory budget (this profile is set to Old 3DS on purpose).

---

## 1. Setup (once per machine)

```powershell
python -m tools.emu setup            # adopt the existing install + run the user's setup
python -m tools.emu setup --check    # report paths/state, change nothing
python -m tools.emu info             # paths + installed mod/ROM status
```

`setup` does three things and nothing else:

1. **Migrates the old layout** if needed: moves `third_party/azahar` to
   `third_party/emutest/azahar` and its `saves/`/`runs/` up one level, because that is where
   `az.py` expects them (rename on the same volume — instant, never a second copy of the 320 MB
   emulator).
2. **On a fresh machine only**, copies a single Azahar install into `third_party/emutest/azahar`
   (excluding any other project's `user/` so its profile can never leak into our runs).
3. Runs the translation project's own `emutest/setup_azahar.py` with `DQ11_EMUTEST`/`DQ11_ROM`
   pointing here. That script applies `az.SETTINGS`, writes the default `user/config/qt-config.ini`
   if missing (the window opens without focus for a few seconds) and extracts
   `third_party/emutest/code_jp.bin` from the ROM for `armdis.py`.

The emulator itself is not reimplemented or reconfigured by our code: the test profile is
`az.SETTINGS` and any change belongs upstream.

### Test profile (from `az.SETTINGS`)

| setting | value | why |
|---|---|---|
| `graphics_api` | 2 (Vulkan) | fast; use `--gpu opengl` for known Azahar Vulkan bugs (2way weapon shops, some 2way battles) |
| `resolution_factor` | 1 | native 400x240 + 320x240, screenshots are 1:1 |
| `async_shader_compilation` | false | deterministic movie replays |
| `frame_limit` | 0 | unlimited, ~10–20x real time |
| `is_new_3ds` | false | Old 3DS, the stricter memory budget a real 2DS must meet |
| `enable_rpc_server` | true | memory reads, screenshots, clock |
| `output_type` | 1 | no audio |
| `init_clock` | 1 | fixed clock (movie clock is deterministic) |
| `confirmClose` / `firstStart` / `saveStateWarning` | false | no dialogs |

Per-run overrides: `--gpu opengl`, `--extra "resolution_factor=2"`, or the harness's
`AZ_SETTINGS="graphics_api=1"`.

---

## 2. Boot a ROM: `python -m tools.emu boot`

```powershell
# Retail-identical rebuild: boot and wait for the title menu
python -m tools.emu boot build/DQXI.3ds --seconds 120 --shot out/title.png

# Boot retail + a Luma/Azahar LayeredFS folder
python -m tools.emu boot build/DQXI.3ds --mod out/luma --seconds 120 --shot out/mod-title.png

# Debug without the automatic START press (stays on the opening movie / logo)
python -m tools.emu boot build/DQXI.3ds --no-start --seconds 30
```

Output and exit codes:

| outcome | printed line | exit |
|---|---|---|
| title menu is live | `title-screen reached at game t=... (basis)` | 0 |
| guest fault / emulator exit | `CRASH: <first log line>` | 1 |
| frozen clock, or no title within `--seconds` | `HANG: <why>` | 2 |
| bad path / no save / emulator missing | `ERROR: ...` | 3 |

A screenshot is written even on crash/hang, plus a `.json` report next to it (game seconds,
real seconds, title-string addresses, framebuffer statistics, emulation speed). The emulator is
always closed afterwards (add `--keep-open` to leave it running for inspection).

What "title-screen reached" actually proves:

* The retail opening movie ends on a logo card at ~430 emulated seconds. `boot` plays a small
  input movie that presses **START at 430s** (a second press at 520s is only a fallback), which
  opens the title menu.
* The menu strings from `ui/title.pack:title_text.bxon` (Japanese: `冒険の書をつくる`,
  `ふっかつのじゅもん`, `プレゼントコード入力`, `冒険をする`, `中断した冒険をする`) are
  normally already in guest RAM from boot (resource cache at ~0x31E/0x320), so their mere
  presence is **not** used. The detector requires at least **two** of them to appear in the
  *dynamic* UI heap (`>= 0x33000000` on this Old-3DS profile), i.e. copied into live title pane
  buffers. That happens only when the menu is built.
* Fallback for translated builds (menu strings replaced by English): after the START press, two
  samples ~1 s apart must both show the title's full-screen warm parchment background
  (`--no-start` disables this too). This is a visual heuristic, not language-independent proof;
  when it wins the race against the RAM scan, `boot` re-checks for the menu strings and the
  report's `basis` says which proof was used (`menu strings in the UI heap` or
  `title background (visual fallback; no live menu strings found)`).

Exact successful run (retail rebuild, `SHA-256 0f04b51b…`):

```text
$ python -m tools.emu boot build/DQXI.3ds --seconds 120 --shot third_party/emutest/runs/boot/dedupe-retail.png
title-screen reached at game t=511.9s (39.4s real; menu strings in the UI heap)
  title text '\u5192\u967a\u306e\u66f8\u3092\u3064\u304f\u308b' in UI heap at 0x33DA0E40
  ...
screenshot: third_party\emutest\runs\boot\dedupe-retail.png
exit 0
```

The Japanese strings are escaped only when the console code page cannot print them; the JSON
report always keeps the real characters.

### Mod folder layouts accepted by `--mod`

`install_mod()` normalises all of these:

| you pass | it reads |
|---|---|
| `out/luma` | `out/luma/titles/0004000000199200/` |
| `out/luma/titles/0004000000199200` | `romfs/` + `code.bin` |
| any folder with `romfs/` and/or `exefs/` | that folder |
| `.../romfs` | its parent |

It copies RomFS files to `third_party/emutest/azahar/user/load/mods/0004000000199200/romfs/`
and a `code.bin` to `.../exefs/code.bin` (Azahar's LayeredFS). When a mod is installed, the
Azahar log contains a line such as:

```text
LayeredFS replacement file in use for /3d/motion/npc001_001_003_csl.pack
```

Which is the direct proof that the overlay is active. Omitting `--mod` (or running `boot`
again without it) removes the previous mod, so a retail boot is always clean.

**Code patches:** Azahar needs a decompressed `exefs/code.bin`. A Luma `code.ips`/`code.bps`
is rejected with an explanatory error — export a rebuilt `code.bin` instead (the exporter in
`tools/export_mod.py` already does this for LayeredFS).

---

## 3. Drive a session: `python -m tools.emu ctl`

One emulator session stays alive between commands (PID in
`third_party/emutest/runs/ctl/session.json`):

```powershell
python -m tools.emu ctl start --rom build/DQXI.3ds
python -m tools.emu ctl start --rom build/DQXI.3ds --mod out/luma --save mysave
python -m tools.emu ctl status
python -m tools.emu ctl frames
python -m tools.emu ctl shot before
python -m tools.emu ctl read 0x10002000 8
python -m tools.emu ctl title          # scan for the title menu (same detector as boot)
python -m tools.emu ctl wait 3
python -m tools.emu ctl press A
python -m tools.emu ctl hold DOWN 0.5
python -m tools.emu ctl walk U 1.5
python -m tools.emu ctl mash A 10
python -m tools.emu ctl save my-save  # snapshot the in-game save
python -m tools.emu ctl stop
```

`start/press/hold/walk/wait/mash/shot/speed/movie` are the harness's (`azctl` mechanics: attach
to the running session by PID, live input through the RPC mailbox). `read/write/frames/title/
save/load` and `status --title` are this project's additions on top of the same `Session` class.

`press`/`hold`/`walk`/`mash` need a **test build** with the translation project's RPC input hook
(mailbox at `0x839F00`). The retail ROM has no hook: `ctl status` reports `hook alive: False`,
and the reliable way to send input to it is an input movie (`.ctm`), e.g.
`ctl start --movie path\to\input.ctm`. Build one with the harness's movie class:

```python
from tools.emu import make_emu, new_movie
m = new_movie().press("START", at=430).press("A", at=445)
with make_emu("build/DQXI.3ds", movie=m) as emu:
    emu.wait_game(460)
    emu.shot("title.png")
```

`ctl start --boot 1` reproduces the old title → Continue → field sequence; it also needs the
input hook. For a plain retail smoke test use `python -m tools.emu boot`.

### Memory reads/writes

`ctl read ADDR SIZE` prints hex, ASCII and u32 columns. Reads cover the whole guest map
(32 KiB RPC chunks); `find_utf16_all()` and `find_utf16_many()` on the emulator object scan
guest RAM for UTF-16LE strings (see `tools/emu/extras.py`).

Writes work in normal `.bss`/`.data` (e.g. `0x839F00`), but **writes to the `0x08000000`
linear-heap alias are silently dropped by Azahar** (they read back unchanged). Do not build a
test on RAM pokes there; use game saves and input instead. This is an Azahar RPC limitation, not
a harness bug.

---

## 4. Saves ("save states")

Game saves are the portable way to resume at a scene — copy them into
`third_party/emutest/saves/<name>/` and pass `--save <name>` (or `ctl start --save`):

```powershell
python -m tools.emu boot build/DQXI.3ds --save user_citra --seconds 150
python -m tools.emu ctl start --save user_citra
```

`ctl save NAME` snapshots the current save out of the emulated SD card; `ctl load NAME` installs
one for the next start. No save is installed by default (`--save` omitted clears it), so boots
are reproducible. `--save` with a name that does not exist is an error (exit 3), not a silent
clean boot.

**Emulator save states are deliberately not used.** Azahar's save states require a UI hotkey
(which would mean driving the emulator window — forbidden here), are tied to the exact Azahar
version and contain the old code/heap. The harness's own guide reached the same conclusion:
game saves are portable, emulator states are not. If you need a state, save the game in-game and
use `ctl save`.

---

## 5. Crashes and hangs

**Start-up flakes.** On this host Azahar occasionally exits a few seconds into a boot (the log
stops at ~3 s with no guest fault). A retail boot is the control; simply retry once. On 2026-10-26
an identical mod boot failed twice this way and succeeded on the third attempt. The proof suite
retries for the same reason.

* `Azahar.crashed()` (the harness's) scans the tail of
  `third_party/emutest/azahar/user/log/azahar_log.txt` for guest faults (`Data/Prefetch Abort`,
  `Unmapped Read/Write`, `Undefined instruction`, `svcBreak`, `ARM11 caught`, …). Lines
  containing `ReadBlock` are **ignored**: they are RPC reads of unmapped addresses from our own
  scans, not game crashes.
* `CRASH` also fires when the emulator process exits on its own.
* `HANG` fires when the HID clock (`0x10002000`) has not advanced for `--hang-seconds`
  (default 30 s real) or when `--seconds` expires without a title screen.
* The log is read only from its tail — a crash loop can grow it by MB/s.

The harness never minimizes the window (the renderer stops) and never activates it
(`SW_SHOWNOACTIVATE`). Do not run `azahar.exe --help`; it opens a dialog on the user's desktop.

---

## 6. Self-checks (what was verified)

```powershell
python -m tools.emu setup --check                          # exit 0 (present)
python -m tools.emu info
python -m tools.emu boot build/DQXI.3ds --seconds 120 --shot third_party/emutest/runs/boot/dedupe-retail.png   # exit 0
python -m tools.emu boot build/DQXI.3ds --mod <mod> --seconds 120 --shot third_party/emutest/runs/boot/dedupe-mod.png  # exit 0 + LayeredFS log line
python -m tools.emu boot build/DQXI.3ds --no-start --seconds 15   # exit 2 (HANG/timeout)
python -m tools.emu boot does-not-exist.3ds                       # exit 3
python -m tools.emu ctl start --rom build/DQXI.3ds
python -m tools.emu ctl status
python -m tools.emu ctl frames
python -m tools.emu ctl shot dedupe-ctl
python -m tools.emu ctl read 0x10002000 8
python -m tools.emu ctl stop
```

Results of the last run (2026-10-25, after the wrapper replaced the copied harness):

* retail: title at game t=511.9 s (39.4 s real), exit 0;
* mod: title at game t=474.8 s (43.7 s real), exit 0, log shows the LayeredFS replacement for
  `/3d/motion/npc001_001_003_csl.pack`;
* `--no-start --seconds 15`: HANG, exit 2; missing ROM: exit 3;
* `ctl start/status/frames/shot/read/stop`: exit 0, `hook alive: False` on retail (expected);
* no `azahar.exe` process left after each command.

The retail baseline used for the proof is `build/DQXI.3ds`
(`0f04b51bc6dc145106fb7bc957fa41991cd02d89e0af2c8775db9d12a37a9b74`, identical to the
retail cartridge dump).

---

## 7. Limitations / honest notes

* Title detection is calibrated for the **retail Japanese** title data on the Old-3DS profile.
  A translation that replaces the menu strings is covered by the parchment fallback; a mod that
  changes the title background too would need a new detector.
* The automatic START timing assumes the retail opening movie (~430 emulated seconds). A mod
  that changes the boot movie may need `--no-start` plus an explicit input movie.
* Save-state snapshots are **game saves**, not emulator states (see §4).
* Writes into the `0x08000000` linear heap alias do not stick (see §3).
* Vulkan has known Azahar-side bugs in this game (2way weapon shops, some 2way battles). Retry
  with `--gpu opengl` before blaming a mod; the translation project's guide documents the same.
* The harness is imported from the translation project at a fixed path. If that checkout moves,
  set `DQXI_EMUTEST_SRC`; if it is missing, every command stops with an `ERROR` naming the
  variable. Nothing is ever written into `..\3DS_Translate`.
* This is test tooling only. It does not change the ROM, the export format, or anything shipped
  to hardware.

