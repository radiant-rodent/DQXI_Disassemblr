#!/usr/bin/env python3
"""tools/recover_native_names.py - names native functions from the script binding tables.

The engine registers its Squirrel natives through tables of
`[u32 function pointer][NUL-terminated name, padded to 4]` entries. The first
recovery pass (tools/recover_func_names.py) read one fixed range; this scans the
whole executable, keeps entries whose pointer is a decompiled function start and
whose name is unambiguous (one name per function, one function per name), and
renames still-unnamed functions in decomp/ghidra/functions_merged.jsonl.

Writes decomp/native_names.json (address -> name, every table entry found).
Rerun tools/readable_c.py afterwards so the readable view uses the names.
"""
from __future__ import annotations

import collections
import json
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 0x00100000
CODE = ROOT / "original/exefs/code.decompressed.bin"
INDEX = ROOT / "decomp/ghidra/functions_merged.jsonl"
OUT = ROOT / "decomp/native_names.json"
UNNAMED = re.compile(r"^(func_|FUN_)")


def scan(code: bytes, starts: set[int]) -> dict[int, str]:
    hits: dict[int, set[str]] = collections.defaultdict(set)
    i, end = 0, len(code) - 8
    while i < end:
        target = struct.unpack_from("<I", code, i)[0] & ~1
        if target in starts:
            k = code.find(b"\0", i + 4, i + 68)
            name = code[i + 4:k]
            if k - (i + 4) >= 3 and re.fullmatch(rb"[A-Za-z_][A-Za-z0-9_]*", name):
                hits[target].add(name.decode())
                i = (k + 4) & ~3
                continue
        i += 4
    single = {a: next(iter(n)) for a, n in hits.items() if len(n) == 1}
    per_name = collections.Counter(single.values())
    return {a: n for a, n in single.items() if per_name[n] == 1}


def main() -> int:
    rows = [json.loads(line) for line in INDEX.read_text(encoding="utf-8").splitlines() if line.strip()]
    starts = {int(r["address"], 16) for r in rows}
    names = scan(CODE.read_bytes(), starts)
    taken = {r["name"] for r in rows}
    renamed = 0
    for row in rows:
        new = names.get(int(row["address"], 16))
        if new and UNNAMED.match(row["name"]) and new not in taken:
            old = row["name"]
            row["name"] = new
            if row.get("signature"):
                row["signature"] = row["signature"].replace(old, new)
            taken.add(new)
            renamed += 1
    INDEX.write_text("".join(json.dumps(r, separators=(",", ":")) + "\n" for r in rows), encoding="utf-8")
    OUT.write_text(json.dumps({f"0x{a:08X}": n for a, n in sorted(names.items())}, indent=1), encoding="utf-8")
    named = sum(1 for r in rows if not UNNAMED.match(r["name"]))
    print(f"{len(names)} binding-table names; renamed {renamed} unnamed functions; "
          f"{named} of {len(rows)} functions now named")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
