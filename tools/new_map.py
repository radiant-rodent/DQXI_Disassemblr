#!/usr/bin/env python3
"""Clone a level under another level_map name so it can be edited on its own (docs/LEVEL_FORMAT.md, new map ids).

A PACK member is found by a 64-bit FNV-1 hash of its name (``h = (h * 0x100000001B3) ^ byte`` from ``0xCBF29CE484222325``; found by
matching the three members of ``3d/bg/b002_105a.pack``); the hash table follows the offset table at 0x18 + 4 * count. The bg pack's members are
named after the level, so cloning renames the member names (same length: the names are NUL padded in a fixed field) and rewrites the hashes.
level3d / level2d packs use name-independent member names and are copied as they are.

    python -m tools.new_map b002_105a z006_002a <mod dir> [--bch model.bch]      # writes <mod>/romfs/{level3d,level2d,3d/bg}/z006_002a.pack
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def fnv1_64(name: str) -> int:
    h = 0xCBF29CE484222325
    for c in name.encode():
        h = ((h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF) ^ c
    return h


def rename_members(pack: bytes, old: str, new: str) -> bytes:
    """Rename the members of a PACK / PACA (compressed packs are decompressed, renamed and recompressed) and rewrite their hashes."""
    if len(old) != len(new):
        raise ValueError("the new level name must have the same length as the old one")
    from tools import pack as packlib

    p = packlib.Pack.parse(pack)
    hashes = b""
    for e in p.entries:
        e.name = e.name.replace(old, new)
        raw = bytearray(e.raw_header)
        end = raw.index(0, 8) if 0 in raw[8:] else len(raw)
        raw[8:end] = e.name.encode()
        e.raw_header = bytes(raw)
        hashes += struct.pack("<Q", fnv1_64(e.name))
    p.hashes = hashes
    p.raw = b""      # force a fresh layout: the in-place path would keep the old names and hashes
    p.orig = b""
    return p.build()


def clone(src: str, dst: str, mod: Path, bch: Path | None = None) -> list[Path]:
    """Write the three packs of ``src`` under ``dst`` into ``mod``; ``bch`` (an imported / edited model) replaces the background model."""
    out = []
    romfs = ROOT / "game_data" / "romfs"
    for rel, rename in ((f"level3d/{src}.pack", False), (f"level2d/{src}.pack", False), (f"3d/bg/{src}.pack", True)):
        source = romfs / rel
        if not source.is_file():
            continue
        data = source.read_bytes()
        if rename:
            data = rename_members(data, src, dst)
        target = mod / "romfs" / rel.replace(src, dst)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        if rename and bch is not None:
            from tools.patch_asset import rebuild_pack

            rebuild_pack(target, f"{dst}.bch", bch, target)
        out.append(target)
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    model = None
    if "--bch" in args:
        i = args.index("--bch")
        model = Path(args[i + 1])
        del args[i:i + 2]
    for p in clone(args[0], args[1], Path(args[2]), model):
        print(p)
