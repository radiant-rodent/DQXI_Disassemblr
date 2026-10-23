#!/usr/bin/env python3
"""Structural BXON decoder.

``tools.bxon`` exposes the string pool used by the translation project.  This
module walks the whole serialized object graph instead: root arrays, nested
arrays, numeric fields, float fields, string references, and raw blocks.  It is
read-only and never guesses that an arbitrary integer is a pointer unless the
self-relative target is an actual allocation marker.

The schema is embedded in the binary only as array counts and element sizes, so
field names are path-based.  Numeric fields are emitted with both integer and
float views; map/table editors can then expose meaningful names on top.

Usage:
    python tools/bxon_struct.py FILE [--out OUT.json]
"""
from __future__ import annotations

import argparse
import json
import math
import struct
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.bxon import Bxon, valid_text

MARK = b"&&&&"


def _is_string_block(payload: bytes) -> bool:
    body = payload.rstrip(b"@")
    if len(body) % 2:
        body += b"@"
    if len(body) < 2 or body[-2:] != b"\0\0" or len(payload) - len(body) > 4:
        return False
    content = body[:-2]
    if not content or len(content) % 2:
        return False
    if b"\0\0" in content:
        return False
    try:
        s = content.decode("utf-16-le")
    except UnicodeDecodeError:
        return False
    return valid_text(s)


class Block:
    __slots__ = ("start", "marker", "end", "payload")

    def __init__(self, start: int, marker: int, end: int, data: bytes):
        self.start = start
        self.marker = marker
        self.end = end
        self.payload = data[start:end]

    @property
    def size(self) -> int:
        return len(self.payload)

    def u32(self, off: int) -> int | None:
        if off < 0 or off + 4 > len(self.payload) or off & 3:
            return None
        return struct.unpack_from("<I", self.payload, off)[0]

    def f32(self, off: int) -> float | None:
        v = self.u32(off)
        if v is None:
            return None
        f = struct.unpack("<f", struct.pack("<I", v))[0]
        return f if math.isfinite(f) else None


class StructDecoder:
    def __init__(self, data: bytes):
        if data[:4] != b"BXON":
            raise ValueError("not BXON")
        self.data = data
        self.type_name = data[0x0C:0x20].split(b"\0", 1)[0].decode("ascii", "replace")
        self.version = struct.unpack_from("<I", data, 4)[0]
        self.type_hash = struct.unpack_from("<I", data, 8)[0]
        self.blocks: dict[int, Block] = {}
        self._find_blocks()
        self._seen: set[tuple[int, int, int]] = set()
        self._max_depth = 32

    def _find_blocks(self):
        starts = []
        pos = self.data.find(MARK, 0x20)
        while pos != -1:
            if pos % 4 == 0 and pos + 4 <= len(self.data):
                starts.append(pos + 4)
            pos = self.data.find(MARK, pos + 4)
        for i, s in enumerate(starts):
            end = (starts[i + 1] - 4) if i + 1 < len(starts) else len(self.data)
            self.blocks[s] = Block(s, s - 4, end, self.data)

    def _u32(self, addr: int) -> int | None:
        if addr < 0 or addr + 4 > len(self.data) or addr & 3:
            return None
        return struct.unpack_from("<I", self.data, addr)[0]

    def _target(self, field: int, value: int) -> int | None:
        if value == 0:
            return None
        target = (field + value) & 0xFFFFFFFF
        return target if target in self.blocks else None

    def _array_descriptor(self, base: int, off: int) -> tuple[int, int, int] | None:
        """Return (target, count, element_size) if this field pair is an array descriptor."""
        count = self._u32(base + off)
        ptr = self._u32(base + off + 4)
        if count is None or ptr is None or count == 0 or count > 1_000_000:
            return None
        target = self._target(base + off + 4, ptr)
        if target is None:
            return None
        block = self.blocks[target]
        size = block.size
        if size <= 0 or size % count:
            return None
        esize = size // count
        if esize <= 0 or esize & 3:
            return None
        # A string block is almost never a valid array, and an array with an
        # element size of 1-3 bytes does not fit BXON's 4-byte scalar layout.
        if _is_string_block(block.payload):
            return None
        return target, count, esize

    def _decode_block(self, addr: int, count: int, esize: int, depth: int) -> object:
        key = (addr, count, esize)
        if key in self._seen:
            return {"$ref": f"0x{addr:X}", "$count": count, "$size": esize}
        if depth > self._max_depth:
            return {"$ref": f"0x{addr:X}", "$count": count, "$size": esize, "$truncated": True}
        self._seen.add(key)
        block = self.blocks.get(addr)
        if block is not None and _is_string_block(block.payload):
            body = block.payload.rstrip(b"@")
            if len(body) % 2:
                body += b"@"
            return body[:-2].decode("utf-16-le", "replace")
        if count == 1:
            return self._decode_record(addr, esize, depth + 1)
        return [self._decode_record(addr + i * esize, esize, depth + 1) for i in range(count)]

    def _decode_record(self, base: int, size: int, depth: int) -> dict:
        out: dict[str, object] = {"$offset": f"0x{base:X}", "$size": size}
        off = 0
        while off + 4 <= size:
            arr = self._array_descriptor(base, off) if off + 8 <= size else None
            if arr is not None:
                target, count, esize = arr
                out[f"+0x{off:02X}"] = {
                    "$array": f"0x{target:X}",
                    "count": count,
                    "element_size": esize,
                    "items": self._decode_block(target, count, esize, depth + 1),
                }
                off += 8
                continue
            v = self._u32(base + off)
            if v is None:
                break
            field_addr = base + off
            target = self._target(field_addr, v)
            if target is not None:
                tblock = self.blocks[target]
                if _is_string_block(tblock.payload):
                    body = tblock.payload.rstrip(b"@")
                    if len(body) % 2:
                        body += b"@"
                    out[f"+0x{off:02X}"] = {
                        "$string": body[:-2].decode("utf-16-le", "replace"),
                        "$offset": f"0x{target:X}",
                    }
                else:
                    # Unknown single allocation: expose its shape, not a
                    # potentially huge guessed object.
                    out[f"+0x{off:02X}"] = {
                        "$ref": f"0x{target:X}",
                        "$size": tblock.size,
                        "$preview": tblock.payload[:32].hex(),
                    }
            else:
                f = struct.unpack("<f", struct.pack("<I", v))[0]
                if not math.isfinite(f):
                    f = None
                entry = {"u32": v}
                if f is not None and abs(f) > 1e-8 and abs(f) < 1e12:
                    entry["f32"] = f
                # Mark very small integer ranges that are typically enums/flags.
                if v < 0x10000:
                    entry["u16"] = v & 0xFFFF
                out[f"+0x{off:02X}"] = entry
            off += 4
        return out

    def decode(self) -> dict:
        # Root descriptor at 0x20.
        root_count = struct.unpack_from("<I", self.data, 0x20)[0]
        root_ptr = struct.unpack_from("<I", self.data, 0x24)[0]
        root_addr = self._target(0x24, root_ptr)
        result = {
            "format": "BXON",
            "type": self.type_name,
            "version": self.version,
            "type_hash": f"0x{self.type_hash:08X}",
            "raw_size": len(self.data),
            "blocks": len(self.blocks),
            "root": None,
        }
        if root_addr is not None:
            block = self.blocks[root_addr]
            esize = block.size // root_count if root_count and block.size % root_count == 0 else block.size
            result["root"] = self._decode_block(root_addr, root_count or 1, esize, 0)
        return result


def decode_file(path: Path) -> dict:
    return StructDecoder(path.read_bytes()).decode()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("file", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    result = decode_file(args.file)
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
