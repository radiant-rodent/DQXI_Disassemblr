#!/usr/bin/env python3
"""Apply same-size numeric edits to a BXON table.

BXON does not store its schema, so a full JSON→BXON writer is not safe yet. This
tool provides the honest intermediate: edit the exact scalar at a known offset
(from the structural JSON), keep the object graph and size unchanged, and emit a
patched binary that can be put back into its PACK.

Project format:

    {
      "source": "game_data/packs/gamecmn/foo.bxon",
      "edits": [
        {"offset": "0x1234", "type": "u32", "value": 42},
        {"offset": "0x1238", "type": "f32", "value": 1.5}
      ]
    }

Usage:
    python tools/bxon_patch.py project.json --out patched.bxon
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    spec = json.loads(args.project.read_text(encoding="utf-8"))
    src = (PROJECT_ROOT / spec["source"]) if not Path(spec["source"]).is_absolute() else Path(spec["source"])
    raw = bytearray(src.read_bytes())
    if raw[:4] != b"BXON":
        print(f"not BXON: {src}", file=sys.stderr)
        return 1
    for edit in spec.get("edits", []):
        off = int(edit["offset"], 16) if isinstance(edit["offset"], str) else int(edit["offset"])
        typ = edit.get("type", "u32")
        value = edit["value"]
        fmt = {"u8": "<B", "u16": "<H", "u32": "<I", "s32": "<i", "f32": "<f"}.get(typ)
        if fmt is None:
            print(f"unsupported type {typ}", file=sys.stderr)
            return 2
        size = struct.calcsize(fmt)
        if off < 0 or off + size > len(raw):
            print(f"edit 0x{off:X} outside {len(raw)} bytes", file=sys.stderr)
            return 3
        struct.pack_into(fmt, raw, off, value)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(bytes(raw))
    print(f"Wrote {args.out} ({len(raw)} bytes, {len(spec.get('edits', []))} edits)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
