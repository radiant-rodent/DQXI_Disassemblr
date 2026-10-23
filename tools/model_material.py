"""Edit a BCH material's diffuse RGBA in place (same file size).

Material parameters are fixed-size. This tool only rewrites the 4-byte
`DiffuseColor` value at material +0xA0, leaving textures, shaders, command
buffers and geometry untouched. Use `tools/bch_texture_patch.py` for textures and
`tools/model_patch.py` for positions/topology.
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.model_tool import BchParser

DIFFUSE_OFFSET = 0xA0


def material_entries(bch: bytes) -> list[int]:
    parser = BchParser(bch)
    rel = parser._relocated()
    tree, count, _ = struct.unpack_from("<3I", bch, parser.hdr_off + 12)
    if count <= 0 or count > 4096 or parser.hdr_off + tree + count * 4 > len(rel):
        return []
    return list(struct.unpack_from(f"<{count}I", rel, parser.hdr_off + tree))


def set_diffuse(bch: bytes, index: int, rgba: tuple[int, int, int, int]) -> bytes:
    entries = material_entries(bch)
    if not 0 <= index < len(entries):
        raise ValueError(f"material index {index} out of range (0..{len(entries) - 1})")
    ptr = entries[index]
    if ptr + DIFFUSE_OFFSET + 4 > len(bch):
        raise ValueError("material entry is outside the BCH")
    out = bytearray(bch)
    out[ptr + DIFFUSE_OFFSET:ptr + DIFFUSE_OFFSET + 4] = bytes(rgba)
    return bytes(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("bch", type=Path)
    ap.add_argument("--material", type=int, required=True)
    ap.add_argument("--rgba", required=True, help="R,G,B,A (0..255)")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    rgba = tuple(int(x) for x in args.rgba.split(","))
    if len(rgba) != 4 or any(not 0 <= x <= 255 for x in rgba):
        ap.error("--rgba must be four values in 0..255")
    raw = args.bch.read_bytes()
    out = set_diffuse(raw, args.material, rgba)  # type: ignore[arg-type]
    if len(out) != len(raw):
        raise SystemExit("internal error: size changed")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(out)
    print(f"wrote {args.out}: material {args.material} diffuse={rgba} (same size)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
