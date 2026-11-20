#!/usr/bin/env python3
"""Emulator proof for 2D-mode level edits (Level Editor 2D view, tools/map2d.py).

Boots the 2D-mode test save (``user_citra_2d``, starts in the Cobblestone church) with a staged
``level2d/<level>.pack`` whose ``level2d.bxon`` was changed by ``map2d.apply_level2d`` (the same function the
editor's Save to mod uses), and takes screenshots once the field is live.

    python -m tools.emu.map2d_probe baseline                       # no change: what does the 2D church look like?
    python -m tools.emu.map2d_probe edit b011_105a a.json [b011_105d d.json]   # stage level2d sections and look

Output: out/emu/probe/<name>/ (report.json, field.png, act*.png).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.emu import level_probe as LP  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("baseline")
    b.add_argument("--save", default="user_citra_2d")
    e = sub.add_parser("edit")
    e.add_argument("pairs", nargs="+", help="level section.json [level section.json ...]")
    e.add_argument("--save", default="user_citra_2d")
    e.add_argument("--name")
    a = ap.parse_args()
    # a few B presses close the priest's welcome / save menu, then a still frame
    actions = [("B", 4, 1.0), ("B", 4, 1.0), ("B", 4, 1.0), ("B", 4, 2.0)]
    stamp = int(time.time()) % 100000
    if a.cmd == "baseline":
        name = f"m2d_base_{stamp}"
        mod = LP.build_mod_members(name, [])
    else:
        from tools import map2d

        members = []
        for level, section_path in zip(a.pairs[::2], a.pairs[1::2]):
            section = json.loads(Path(section_path).read_text(encoding="utf-8"))
            src = ROOT / "game_data" / "packs" / "level2d" / level / "level2d.bxon"
            patched, notes = map2d.apply_level2d(src.read_bytes(), section)
            members.append((f"level2d/{level}.pack", "level2d.bxon", patched))
            print(level, "; ".join(notes))
        name = a.name or f"m2d_{a.pairs[0]}_{stamp}"
        mod = LP.build_mod_members(name, members)
    report = LP.run_probe(name, mod, attempts=2, save=a.save, actions=actions)
    print(json.dumps({k: report.get(k) for k in ("name", "screenshot", "action_shots", "crash", "attempts", "ok")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
