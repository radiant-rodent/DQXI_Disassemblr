"""Command line for this project's Azahar test harness.

    python -m tools.emu setup [--source PATH] [--check]
    python -m tools.emu boot build/DQXI.3ds [--mod out/luma] [--seconds N] [--shot out.png]
    python -m tools.emu ctl start|press|hold|walk|shot|status|stop|...   (see extras.py)
    python -m tools.emu info

The harness itself is the translation project's ``emutest`` package (one copy, imported
unchanged).  Everything here is the project-specific glue: the environment/data root, the
LayeredFS mod install, the title/crash/hang verdict and the screenshot report.

``boot`` reports exactly one outcome:

    title-screen reached     exit 0
    CRASH: <log line>        exit 1
    HANG: <why>              exit 2
    ERROR: <message>         exit 3

The screenshot is written even on crash/hang.  The emulator is always closed afterwards unless
``--keep-open`` is passed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

from . import extras  # noqa: E402  (the package is ours; the harness is imported lazily)


def _gpu_settings(gpu: str) -> dict:
    return {"graphics_api": {"software": "0", "opengl": "1", "vulkan": "2"}[gpu.lower()]}


def _default_shot(tag: str) -> str:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    return os.path.join(extras.RUNS, "boot", f"{tag}-{stamp}.png")


def cmd_boot(a) -> int:
    rom = os.path.abspath(a.rom or extras.DEFAULT_ROM)
    shot = os.path.abspath(a.shot or _default_shot(os.path.splitext(os.path.basename(rom))[0]))
    workdir = os.path.dirname(shot) or os.path.join(extras.RUNS, "boot")
    settings = _gpu_settings(a.gpu)
    if a.extra:
        settings.update(kv.split("=", 1) for kv in a.extra.split(",") if "=" in kv)

    print(f"ROM:    {rom}")
    print(f"mod:    {a.mod or '(none - retail boot)'}")
    print(f"output: {shot}")
    if not os.path.isfile(rom):
        print(f"ERROR: ROM not found: {rom}", file=sys.stderr)
        return 3

    emu = extras.make_emu(rom, mod=a.mod, save=a.save, workdir=workdir, settings=settings)
    # The retail opening movie ends at ~430 emulated seconds on the logo card; one START press
    # opens the title menu.  (The movie clock is deterministic, unlike real time.)  A second,
    # late press is a fallback for a mod that delays the movie; title detection stops the run
    # before it matters when the first one worked.
    if not a.no_start:
        movie = extras.new_movie()
        for t in (430, 520):
            movie.press("START", at=t)
        emu.movie = movie
    outcome, detail, basis, evidence = None, "", None, None
    t_start = time.time()
    try:
        emu.start()
        print(f"emulator started (pid {emu.proc.pid}); waiting up to {a.seconds:g}s real "
              f"(game runs ~10-20x)")
        visual_hits = 0
        last_gt = emu.game_time()
        last_progress = time.time()
        next_scan = time.time() + 5.0
        next_visual = time.time() + 7.0
        next_report = time.time() + 10.0

        while time.time() - t_start < a.seconds:
            crash = emu.crashed()
            if crash:
                outcome, detail = "crash", crash
                break

            gt = emu.game_time()
            if gt > last_gt + 0.05:
                last_gt = gt
                last_progress = time.time()

            if time.time() >= next_report:
                stats = emu.screen_stats()
                frame = ""
                if stats:
                    frame = (f" screen {stats['width']}x{stats['height']} "
                             f"mean={stats['mean']:.1f} nonblack={stats['nonblack']:.0%}")
                print(f"  t={gt:.1f}s real={time.time() - t_start:.1f}s{frame}")
                next_report = time.time() + 10.0

            if time.time() >= next_scan:
                evidence = emu.title_evidence()
                if evidence:
                    outcome, basis = "title", "menu strings in the UI heap"
                    break
                next_scan = time.time() + 3.0

            # Visual fallback for translated builds (menu strings may be English): only after
            # the automatic START press could have opened the menu, and only if two samples
            # ~1 s apart both show the parchment title background.
            if not a.no_start and gt > 430 and time.time() >= next_visual:
                if emu.title_screen_visual():
                    visual_hits += 1
                    if visual_hits >= 2:
                        # The visual check can win the race against the periodic RAM scan
                        # (the parchment appears a little before the pane buffers hold the
                        # menu text).  Confirm with the stronger detector so the report says
                        # which proof was actually used.
                        evidence = emu.title_evidence()
                        outcome = "title"
                        basis = ("menu strings in the UI heap" if evidence
                                 else "title background (visual fallback; no live menu "
                                      "strings found)")
                        break
                else:
                    visual_hits = 0
                next_visual = time.time() + 1.0

            if time.time() - last_progress > a.hang_seconds:
                outcome = "hang"
                detail = (f"game clock stopped at {gt:.1f}s for "
                          f"{time.time() - last_progress:.0f}s real")
                break

            time.sleep(0.1)

        if outcome is None:
            outcome = "hang"
            detail = f"no title screen within {a.seconds:g}s real (game clock {emu.game_time():.1f}s)"

        ok_shot = emu.shot(shot)
        stats = emu.screen_stats()
        game_time = emu.game_time()
        perf = emu.perf()
    finally:
        if not a.keep_open:
            emu.stop()
        else:
            print("emulator left running (pid %s); close it with "
                  "`python -m tools.emu ctl stop` or Task Manager" % emu.proc.pid)

    result = {
        "rom": rom, "mod": a.mod, "outcome": outcome, "detail": detail, "basis": basis,
        "game_seconds": round(game_time, 2), "real_seconds": round(time.time() - t_start, 1),
        "screenshot": shot if ok_shot else None,
        "title_strings": evidence,
        "screen": stats,
        "emulation_speed": (perf or {}).get("emulation_speed"),
    }
    report = os.path.splitext(shot)[0] + ".json"
    try:
        with open(report, "w", encoding="utf-8") as fp:
            json.dump(result, fp, ensure_ascii=False, indent=2)
    except OSError:
        pass

    if outcome == "title":
        print(f"title-screen reached at game t={game_time:.1f}s "
              f"({time.time() - t_start:.1f}s real; {basis})")
        if evidence:
            for text, addrs in evidence.items():
                print(f"  title text {extras.printable(text)!r} "
                      f"in UI heap at 0x{addrs[0]:08X}")
        print(f"screenshot: {shot}")
        return 0
    if outcome == "crash":
        print(f"CRASH: {detail}")
        print(f"screenshot: {shot}")
        return 1
    print(f"HANG: {detail}")
    print(f"screenshot: {shot}")
    return 2


def cmd_info(_a) -> int:
    print("harness: ", extras.HARNESS)
    print("data root:", extras.DATA_ROOT)
    print("emulator:", extras.EXE, "(present)" if os.path.isfile(extras.EXE) else "(MISSING)")
    print("user:    ", extras.USER)
    print("saves:   ", extras.SAVES)
    print("runs:    ", extras.RUNS)
    print("mods:    ", extras.MODS, "(installed)" if extras.mod_installed() else "(empty)")
    print("ROM:     ", extras.DEFAULT_ROM,
          "(present)" if os.path.isfile(extras.DEFAULT_ROM) else "(MISSING)")
    return 0 if os.path.isfile(extras.EXE) else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.emu", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("setup", help="prepare this project's emulator data root")
    s.add_argument("--source")
    s.add_argument("--check", action="store_true")
    s.set_defaults(fn=lambda a: extras.setup_main(
        (["--source", a.source] if a.source else []) + (["--check"] if a.check else [])))

    b = sub.add_parser("boot", help="boot a ROM and report title / crash / hang")
    b.add_argument("rom", nargs="?", default=extras.DEFAULT_ROM)
    b.add_argument("--mod", help="Luma/Azahar LayeredFS folder (out/luma, out/luma/titles/TID, ...)")
    b.add_argument("--seconds", type=float, default=90.0, help="max real seconds (default 90)")
    b.add_argument("--hang-seconds", type=float, default=30.0,
                   help="real seconds with a frozen game clock before reporting HANG")
    b.add_argument("--shot", help="screenshot path (default third_party/emutest/runs/boot/...)")
    b.add_argument("--save", help="game-save name to install (default: clean sdmc)")
    b.add_argument("--gpu", choices=("vulkan", "opengl", "software"), default="opengl")  # Vulkan crashes this machine's driver at boot
    b.add_argument("--extra", help="extra qt-config overrides, e.g. resolution_factor=2")
    b.add_argument("--no-start", action="store_true",
                   help="do not send the automatic START press (stay on the boot logo/movie)")
    b.add_argument("--keep-open", action="store_true", help="leave the emulator running")
    b.set_defaults(fn=cmd_boot)

    c = sub.add_parser("ctl", help="step-by-step session control (see tools/emu/extras.py)")
    c.add_argument("args", nargs=argparse.REMAINDER)
    c.set_defaults(fn=lambda a: extras.ctl_main(a.args))

    i = sub.add_parser("info", help="show paths and what is installed")
    i.set_defaults(fn=cmd_info)

    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except (RuntimeError, OSError) as e:   # EmuError, the user's runtime errors, bad paths
        print(f"ERROR: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
