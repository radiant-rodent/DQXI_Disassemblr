#!/usr/bin/env python3
"""Emulator proof for the 2D tile and collision editing (Level Editor 2D view: Tiles / Collision tools).

Boots the 2D-mode test save (``user_citra_2d``, Cobblestone church b011_105a) and walks the hero down the aisle.

    python -m tools.emu.edit2d_probe baseline      nothing changed: the hero walks down the aisle
    python -m tools.emu.edit2d_probe edit          * three ground cells in the aisle get other tiles: two get a NEW chip
                                                     (a wall tile upside down: the chip table grows, map2d.add_chips),
                                                     one an existing chip (map2d.apply_chp)
                                                   * the walk grid gets a blocked row right below the hero
                                                     (map2d.apply_dmap): he must not get past it

Both use the functions the editor's Save to mod uses. Output: out/emu/probe/<name>/ (field.png, act*.png).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools import map2d  # noqa: E402
from tools.emu import level_probe as LP  # noqa: E402

BG = "b011_105a"
LEVELS = ("b011_105a", "b011_105d")   # the church's story states share the map
BLOCK_ROW = 8                          # grid row right below the hero's start


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    stamp = int(time.time()) % 100000
    members = []
    if mode == "edit":
        raw = (map2d.BG / BG / f"{BG}.chp").read_bytes()
        cm = map2d.ChipMap(raw)
        cols = cm.base_cols
        # a clearly visible, non-symmetric ground tile, placed upside down: an orientation the map has no chip for
        from PIL import Image, ImageStat
        sheet = map2d.sheets(BG)[f"{BG}_rgb_daytime"].convert("RGB")
        window_id = None
        for cid in sorted(set(cm.base)):
            if cid == 0xFFFF or cid >= len(cm.chips):
                continue
            c = cm.chips[cid]
            tile = sheet.crop((c[0] * 16, c[1] * 16, c[0] * 16 + 16, c[1] * 16 + 16))
            bright = sum(ImageStat.Stat(tile).mean) / 3
            other = 4 if (c[5] & 0x0E) != 4 else 0
            exists = any(k[0] == c[0] and k[1] == c[1] and (k[5] & 0x1E) == other for k in cm.chips)
            top, bottom = tile.crop((0, 0, 16, 8)), tile.crop((0, 8, 16, 16)).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            uneven = sum(abs(x - y) for x, y in zip(ImageStat.Stat(top).mean, ImageStat.Stat(bottom).mean))
            if bright > 110 and uneven > 40 and not exists:
                window_id, wall = cid, c
                break
        assert window_id is not None, "no suitable tile"
        new_chip = [wall[0], wall[1], 0, 0, 4 if (wall[5] & 0x0E) != 4 else 0]
        new_id = len(cm.chips)
        tiles = [{"index": 15 * cols + 17, "value": new_id}, {"index": 15 * cols + 18, "value": new_id},
                 {"index": 16 * cols + 17, "value": window_id}]
        members.append((f"2d/bg/{BG}.pack", f"{BG}.chp", map2d.apply_chp(raw, tiles, [new_chip])))
        print("tiles:", tiles, "new chip", new_chip, "chips", len(cm.chips), "->", new_id + 1)
        for level in LEVELS:
            grid = map2d.collision(level)[0]
            dm = (map2d.DATA / "level2d" / level / "leveldmap.bxon").read_bytes()
            cells = [{"offset": grid["offset"] + 2 * (BLOCK_ROW * grid["w"] + c), "value": 1} for c in range(grid["w"])]
            members.append((f"level2d/{level}.pack", "leveldmap.bxon", map2d.apply_dmap(dm, cells)))
        print("collision: row", BLOCK_ROW, "blocked in", LEVELS)
    name = f"e2d_{mode}_{stamp}"
    mod = LP.build_mod_members(name, members)
    # close the priest's welcome, then walk down the aisle twice
    actions = [("B", 4, 1.0), ("B", 4, 1.0), ("B", 4, 1.0), ("B", 4, 1.5), ("DOWN", 50, 1.5), ("DOWN", 50, 1.5)]   # the 2D mode moves with the D-pad
    report = LP.run_probe(name, mod, attempts=2, save="user_citra_2d", actions=actions)
    print(json.dumps({k: report.get(k) for k in ("name", "action_shots", "crash", "ok")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
