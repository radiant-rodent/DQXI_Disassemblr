#!/usr/bin/env python3
"""Perturb-and-observe for level data: patch level3d.bxon files, boot Azahar, load the test save, look.

The level format has no names in the binary, so what a record word does is found by changing it and
watching the game (docs/LEVEL_FORMAT.md).  This stages edited level files as a LayeredFS mod, plays the
proven "Cobblestone" save (the field scene of the emulator cases) and reports

  * which level packs the game actually opened (Azahar logs every replaced file it serves),
  * a screenshot of the field once it is live,
  * whether the game kept running (clock advances, no crash).

    python -m tools.emu.level_probe identity b011_001a b011_001b        # copy levels unchanged: which ones load?
    python -m tools.emu.level_probe patch b011_001a 0x2060=u32:0x03000010 0x2064=f32:1.5
    python -m tools.emu.level_probe patch b011_001a --from-json edits.json --name try1

A patch word is ``<file offset>=<u32|f32|u8|u16>:<value>``; offsets are those printed by
``tools/map_tool.py`` / ``tools/level_inventory.py`` (file offsets in level3d.bxon).
Output goes to ``out/emu/probe/<name>/`` (report.json, screenshots, the mod folder).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import struct
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "out" / "emu" / "probe"
LEVELS = ROOT / "game_data" / "packs" / "level3d"


def parse_patch(text: str) -> tuple[int, bytes]:
    m = re.fullmatch(r"(0x[0-9a-fA-F]+|\d+)=(u32|f32|u16|u8):(.+)", text)
    if not m:
        raise SystemExit(f"bad patch {text!r}: use <offset>=<u32|f32|u16|u8>:<value>")
    off = int(m.group(1), 0)
    kind, val = m.group(2), m.group(3)
    if kind == "f32":
        return off, struct.pack("<f", float(val))
    number = int(val, 0)
    return off, number.to_bytes({"u32": 4, "u16": 2, "u8": 1}[kind], "little")


def patched(level: str, patches: list[tuple[int, bytes]]) -> bytes:
    raw = bytearray((LEVELS / level / "level3d.bxon").read_bytes())
    for off, data in patches:
        if off + len(data) > len(raw):
            raise SystemExit(f"offset 0x{off:X} is outside {level} ({len(raw)} bytes)")
        raw[off : off + len(data)] = data
    return bytes(raw)


def build_mod(name: str, levels: dict[str, bytes]) -> Path:
    from tests.emu import runner as R
    from tools.export_mod import stage_member

    out = OUT / name
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    ws = R.workspace("probe_" + name, R.build_test_code(textlog=True), True)
    for level, data in levels.items():
        edited = out / "edited" / f"{level}.bxon"
        edited.parent.mkdir(parents=True, exist_ok=True)
        edited.write_bytes(data)
        stage_member(f"level3d/{level}.pack", "level3d.bxon", edited, ws, work_dir=out / "staged")
    R.export(ws, out / "export", "bin")
    return out / "export" / "luma"


def build_mod_members(name: str, members: list[tuple[str, str, bytes]]) -> Path:
    """Stage arbitrary pack members: (pack path like ``3d/bg/b002_105a.pack``, member name, new bytes)."""
    from tests.emu import runner as R
    from tools.export_mod import stage_member

    out = OUT / name
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    ws = R.workspace("probe_" + name, R.build_test_code(textlog=True), True)
    for n, (pack, member, data) in enumerate(members):
        edited = out / "edited" / f"{n}_{member}"
        edited.parent.mkdir(parents=True, exist_ok=True)
        edited.write_bytes(data)
        stage_member(pack, member, edited, ws, work_dir=out / "staged")
    R.export(ws, out / "export", "bin")
    return out / "export" / "luma"


def signatures(levels: list[str], width: int = 40) -> dict[str, bytes]:
    """A short byte string per level that appears in no other candidate: found in RAM = that level is loaded."""
    files = {lv: (LEVELS / lv / "level3d.bxon").read_bytes() for lv in levels}
    out: dict[str, bytes] = {}
    for lv, raw in files.items():
        others = [f for k, f in files.items() if k != lv]
        for off in range(0x40, max(0x41, len(raw) - width), 8):
            win = raw[off : off + width]
            if sum(1 for b in win if b) < width // 2 or len(set(win)) < 10:
                continue
            if any(win in f for f in others):
                continue
            out[lv] = win
            break
    return out


def scan_ram(emu, needles: dict[str, bytes], ranges=((0x08000000, 0x10000000), (0x14000000, 0x18000000)),
             chunk: int = 0x8000) -> dict[str, list[int]]:
    found: dict[str, list[int]] = {k: [] for k in needles}
    width = max(len(n) for n in needles.values())
    for start, end in ranges:
        a = start
        while a < end:
            data = emu.read(a, chunk + width)
            if data:
                for k, n in needles.items():
                    i = data.find(n)
                    while i >= 0:
                        if i < chunk:
                            found[k].append(a + i)
                        i = data.find(n, i + 1)
            a += chunk
    return {k: v for k, v in found.items() if v}


def _skip_to_title(run, timeout: float) -> tuple[bool, str | None]:
    """Reach the title menu by pressing A to skip the opening movies (instead of waiting ~430 game seconds).

    A is pressed every couple of seconds until the title menu's text is live; it stops the moment the title
    is up, so the following "Continue" tap in the load script is the only A that reaches the menu.
    """
    t0 = time.time()
    while time.time() - t0 < timeout:
        if run.emu.proc.poll() is not None:
            return False, f"emulator exited ({run.emu.proc.returncode})"
        if run.emu.title_evidence():
            return True, None
        try:
            run.tap("A", settle=1.5)
        except Exception:
            time.sleep(1.5)
    return False, "title screen not reached"


def _load_field_fast(run, rec, shot_name: str) -> dict:
    """Title -> Continue -> slot 1 -> field with short settles; each wait ends as soon as its text shows."""
    def wait(pred, limit):
        t0 = time.time()
        while time.time() - t0 < limit and not pred():
            time.sleep(0.5)

    run.tap("A", settle=1.0)             # Continue
    time.sleep(2.5)                      # save-slot list
    run.tap("A", settle=1.0)             # slot 1
    if rec is not None:
        wait(lambda: rec.find("あらすじ"), 150)
    else:
        time.sleep(25)
    run.tap("B", settle=1.0)             # "no" to the story recap
    if rec is not None:
        wait(lambda: any(e.get("name") == "txt_place" for e in rec.events), 150)
    else:
        time.sleep(25)
    time.sleep(2.0)
    path = run.shot(shot_name)
    return {"screenshot": str(path), "game_time": round(run.emu.game_time(), 1)}


def run_probe(name: str, mod: Path, attempts: int = 3, save: str | None = None,
              scan: list[str] | None = None, actions: list[tuple[str, int, float]] | None = None,
              ram_regex: bytes | None = None, hook=None) -> dict:
    from tests.emu import runner as R

    extras, _textlog = R.load_emu_modules()
    out = OUT / name
    report: dict = {"name": name, "attempts": []}
    for attempt in range(attempts):
        try:
            if not R._wait_emulator_free(900):
                report["attempts"].append("RPC port stayed busy")
                break
            with R.Run(extras, mod, save=save or R.SAVE_2D, out=out) as run:
                titled, why = _skip_to_title(run, 600)
                if not titled:
                    report["attempts"].append({"attempt": attempt + 1, "error": why})
                    continue
                rec = None
                try:
                    rec = run.start_textlog()
                except Exception as exc:
                    report["textlog"] = f"unavailable: {exc}"
                # Run the scripted load in a worker and watch the guest: a crashed emulator must be
                # closed at once (it otherwise freezes with its window open until every RPC retry times out).
                import threading
                result: dict = {}

                def work():
                    try:
                        result.update(_load_field_fast(run, rec, "field.png"))
                    except Exception as exc:          # the emulator was closed under it
                        result["load_error"] = str(exc)[:200]

                worker = threading.Thread(target=work, daemon=True)
                worker.start()
                while worker.is_alive():
                    worker.join(1.0)
                    crash = None
                    try:
                        crash = run.emu.crashed()
                    except Exception:
                        pass
                    if crash:
                        report["crash"] = crash
                        report["crashed_at_game_time"] = round(run.emu.game_time(), 1)
                        try:
                            run.emu.stop()
                        except Exception:
                            pass
                        R.kill_test_emulators(extras)
                        break
                worker.join(5.0)
                report.update(result)
                # optional button presses after the field is live: (button, frames held, seconds to settle);
                # a screenshot after each one: act0.png, act1.png ...
                if hook:
                    hook(run, 'loaded')
                if actions and not report.get("crash"):
                    shots = []
                    for n, (button, frames, settle) in enumerate(actions):
                        if button.startswith("WALK:"):
                            # circle pad: WALK:D / U / L / R / UL ... for `frames` seconds (game moves with the stick)
                            run.emu.walk(button[5:], float(frames))
                            time.sleep(settle)
                        else:
                            run.tap(button, frames=frames, settle=settle)
                        if run.emu.crashed():
                            report["crash"] = run.emu.crashed()
                            break
                        shots.append(str(run.shot(f"act{n}.png")))
                        if hook:
                            hook(run, f'act{n}')
                    report["action_shots"] = shots
                if report.get("crash"):
                    report["ok"] = False
                    (out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
                    return report
                if scan:
                    sigs = signatures(scan)
                    report["signatures"] = {k: v.hex() for k, v in sigs.items()}
                    report["levels_in_ram"] = {k: [f"0x{a:08X}" for a in v[:4]] for k, v in scan_ram(run.emu, sigs).items()}
                if ram_regex and not report.get("crash"):
                    import re
                    rx = re.compile(ram_regex)
                    names: set[str] = set()
                    t_scan = time.time()
                    for start, end in ((0x08000000, 0x10000000), (0x14000000, 0x18000000)):
                        a = start
                        while a < end:
                            data = run.emu.read(a, 0x10040)
                            if data:
                                for m in rx.findall(data):
                                    names.add(m.decode("ascii", "replace"))
                            a += 0x10000
                    report["ram_names"] = sorted(names)
                    report["ram_scan_seconds"] = round(time.time() - t_scan, 1)
                t0 = run.emu.game_time()
                time.sleep(3.0)
                report["clock_advanced"] = run.emu.game_time() > t0 + 0.5
                report["crash"] = run.emu.crashed()
                run.shot("after.png")
            report["ok"] = report.get("clock_advanced", False) and not report.get("crash")
            break
        except RuntimeError as exc:
            report["attempts"].append({"attempt": attempt + 1, "error": str(exc)})
            time.sleep(5)
    (out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    ident = sub.add_parser("identity", help="stage unchanged copies; shows which levels the scene loads")
    ident.add_argument("levels", nargs="+")
    ident.add_argument("--name", default="identity")
    ident.add_argument("--save", default="user_citra_2d", help="user_citra_2d (default) or user_citra_3d")
    pat = sub.add_parser("patch", help="patch words of one level and look at the result")
    pat.add_argument("level")
    pat.add_argument("patches", nargs="*")
    pat.add_argument("--from-json", type=Path, help='[{"offset": "0x..", "type": "u32", "value": 5}, ...]')
    pat.add_argument("--name", default=None)
    pat.add_argument("--save", default="user_citra_2d", help="user_citra_2d (default) or user_citra_3d")
    pat.add_argument("--scan", nargs="*", default=None, help="levels to look for in RAM after the field loads")
    args = ap.parse_args()

    if args.cmd == "identity":
        levels = {lv: (LEVELS / lv / "level3d.bxon").read_bytes() for lv in args.levels}
        name = args.name
    else:
        edits = [parse_patch(p) for p in args.patches]
        if args.from_json:
            for e in json.loads(args.from_json.read_text(encoding="utf-8")):
                edits.append(parse_patch(f"{e['offset']}={e['type']}:{e['value']}"))
        levels = {args.level: patched(args.level, edits)}
        name = args.name or f"{args.level}_{len(edits)}edits"
    mod = build_mod(name, levels)
    scan = list(levels) if args.cmd == "identity" else args.scan
    report = run_probe(name, mod, save=args.save, scan=scan)
    print(json.dumps({k: v for k, v in report.items() if k != "attempts" or v}, indent=1, ensure_ascii=False))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
