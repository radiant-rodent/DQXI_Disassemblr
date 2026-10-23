#!/usr/bin/env python3
"""Rebuild the CTR RomFS IVFC SHA-256 hash tree.

RomFS layout (3dbrew):
  0x0000  IVFC header
  0x0060  master hashes (0x20 per Level-1 block)
  0x1000  Level 3 data (the actual RomFS)
  ...     Level 1 hashes (one SHA-256 per Level-2 block)
  ...     Level 2 hashes (one SHA-256 per Level-3 block)

The header stores the three level sizes and block sizes.  The physical starts are
derived from those sizes:
  data_start = align(0x60 + master_size, block_size)
  level1_start = align(data_start + data_size, block_size)
  level2_start = align(level1_start + level1_size, block_size)

For DQXI the sizes are:
  level0 (Level-1 hashes) = 0x279E0
  level1 (Level-2 hashes) = 0x13CE340
  level2 (data)           = 0x9E719FB4
  master                  = 0x500

After a data edit, this tool recomputes Level 2, then Level 1, then the master
hashes.  Run it on a copy of ``romfs.bin`` before repacking.  When the data region
grows (a file appended at its end), call ``resize_data`` first: it updates the
header sizes/offsets and moves the hash levels behind the new data end.

Usage:
    python tools/romfs_hash.py build/patched/romfs.bin
    python tools/romfs_hash.py --verify build/patched/romfs.bin
"""
from __future__ import annotations

import argparse
import hashlib
import struct
import sys
from pathlib import Path

BLOCK = 0x1000
SHA = 32
MASTER_OFF = 0x60
CHUNK = 16 * 1024 * 1024


def align(x: int, a: int) -> int:
    return (x + a - 1) // a * a


def parse_header(data: bytes) -> dict:
    if data[:4] != b"IVFC" or struct.unpack_from("<I", data, 4)[0] != 0x10000:
        raise ValueError("not an IVFC RomFS header")
    master_size = struct.unpack_from("<I", data, 8)[0]
    levels = []
    for i in range(3):
        off, size, log2 = struct.unpack_from("<QQI", data, 0x0C + i * 0x18)
        levels.append({"offset": off, "size": size, "block": 1 << log2})
    block = levels[2]["block"]
    data_start = align(0x60 + master_size, block)
    level1_start = align(data_start + levels[2]["size"], block)
    level2_start = align(level1_start + levels[0]["size"], block)
    return {
        "master_size": master_size,
        "block": block,
        "levels": levels,
        "data_start": data_start,
        "level1_start": level1_start,  # hashes of level2 blocks
        "level2_start": level2_start,  # hashes of level3/data blocks
        "level0_size": levels[0]["size"],
        "level1_size": levels[1]["size"],
        "data_size": levels[2]["size"],
    }


def total_size(info: dict) -> int:
    """Size of the whole RomFS image: the data plus both hash levels."""
    return align(info["level2_start"] + info["level1_size"], info["block"])


def resized_header(head: bytes, new_data_size: int) -> bytes:
    """The IVFC header for the same image with a level-3 data size of `new_data_size`."""
    head = bytearray(head[:MASTER_OFF])
    info = parse_header(bytes(head))
    block = info["block"]
    log2 = block.bit_length() - 1
    data_hashes = (new_data_size + block - 1) // block * SHA       # level 2
    level1 = (data_hashes + block - 1) // block * SHA               # level 1
    master = (level1 + block - 1) // block * SHA
    if align(MASTER_OFF + master, block) != info["data_start"]:
        raise ValueError("master hash table no longer fits in front of the data region")
    # logical offsets of the three levels, as in the retail header
    offsets = [0, align(level1, block)]
    offsets.append(align(offsets[1] + data_hashes, block))
    struct.pack_into("<I", head, 8, master)
    for i, size in enumerate((level1, data_hashes, new_data_size)):
        struct.pack_into("<QQI", head, 0x0C + i * 0x18, offsets[i], size, log2)
    return bytes(head)


def resize_data(path: Path, new_data_size: int) -> dict:
    """Sets the level-3 data size to `new_data_size` and relocates the hash levels.

    The bytes of the data region up to min(old, new) size are kept; anything
    between the old data end and the new one is zero-filled, and the hash levels
    are zeroed at their new place (run ``rebuild`` afterwards).
    """
    with open(path, "r+b") as f:
        head = f.read(MASTER_OFF)
        info = parse_header(head)
        head = resized_header(head, new_data_size)
        new_info = parse_header(head)

        keep = info["data_start"] + min(info["data_size"], new_data_size)
        new_total = total_size(new_info)
        f.seek(0)
        f.write(head)
        f.seek(MASTER_OFF)
        f.write(bytes(info["data_start"] - MASTER_OFF))
        f.truncate(keep)
        f.seek(keep)
        zeros = bytes(CHUNK)
        left = new_total - keep
        while left > 0:
            f.write(zeros[:min(left, CHUNK)])
            left -= CHUNK
    return new_info


def _hash_blocks(f, start: int, count: int, block: int) -> bytes:
    """SHA-256 of `count` consecutive blocks at `start` (zero-padded past EOF)."""
    out = bytearray()
    f.seek(start)
    per_read = max(1, CHUNK // block)
    left = count
    while left > 0:
        n = min(left, per_read)
        buf = f.read(n * block)
        if len(buf) < n * block:
            buf += bytes(n * block - len(buf))
        for i in range(n):
            out += hashlib.sha256(buf[i * block:(i + 1) * block]).digest()
        left -= n
    return bytes(out)


def _counts(info: dict) -> tuple[int, int, int]:
    block = info["block"]
    return ((info["data_size"] + block - 1) // block,
            (info["level1_size"] + block - 1) // block,
            (info["level0_size"] + block - 1) // block)


def rebuild(path: Path) -> dict:
    with open(path, "rb") as f:
        info = parse_header(f.read(MASTER_OFF))
    block = info["block"]
    data_start = info["data_start"]
    l1_start = info["level1_start"]
    l2_start = info["level2_start"]
    l2_blocks, l1_blocks, master_blocks = _counts(info)

    with open(path, "r+b") as f:
        # Level 2: hash every data block.
        h = _hash_blocks(f, data_start, l2_blocks, block)
        f.seek(l2_start)
        f.write(h)
        # Level 1: hash every Level-2 block (now updated).
        h = _hash_blocks(f, l2_start, l1_blocks, block)
        f.seek(l1_start)
        f.write(h)
        # Master: hash every Level-1 block.
        h = _hash_blocks(f, l1_start, master_blocks, block)
        f.seek(MASTER_OFF)
        f.write(h)
    return {
        "path": str(path),
        "data_blocks": l2_blocks,
        "level1_blocks": l1_blocks,
        "master_blocks": master_blocks,
        "master_size": info["master_size"],
        "data_size": info["data_size"],
        "romfs_size": total_size(info),
        "data_start": f"0x{data_start:X}",
        "level1_start": f"0x{l1_start:X}",
        "level2_start": f"0x{l2_start:X}",
    }


def _count_bad(f, start: int, count: int, block: int, table_off: int) -> int:
    got = _hash_blocks(f, start, count, block)
    f.seek(table_off)
    want = f.read(count * SHA)
    return sum(got[i * SHA:(i + 1) * SHA] != want[i * SHA:(i + 1) * SHA] for i in range(count))


def verify(path: Path) -> dict:
    with open(path, "rb") as f:
        info = parse_header(f.read(MASTER_OFF))
        block = info["block"]
        l2_blocks, l1_blocks, master_blocks = _counts(info)
        bad_l2 = _count_bad(f, info["data_start"], l2_blocks, block, info["level2_start"])
        bad_l1 = _count_bad(f, info["level2_start"], l1_blocks, block, info["level1_start"])
        bad_master = _count_bad(f, info["level1_start"], master_blocks, block, MASTER_OFF)
        f.seek(0, 2)
        size_ok = f.tell() >= total_size(info)
    return {
        "path": str(path),
        "data_blocks": l2_blocks,
        "level1_blocks": l1_blocks,
        "master_blocks": master_blocks,
        "bad_level2": bad_l2,
        "bad_level1": bad_l1,
        "bad_master": bad_master,
        "size_ok": size_ok,
        "ok": bad_l2 == bad_l1 == bad_master == 0 and size_ok,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("romfs", type=Path)
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()
    if args.verify:
        result = verify(args.romfs)
        print(result)
        return 0 if result["ok"] else 1
    result = rebuild(args.romfs)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
