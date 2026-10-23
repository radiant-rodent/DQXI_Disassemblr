"""Replace one embedded BCH model texture in place (same file size).

DQXI BCH textures are ETC1 (4bpp) or ETC1A4 (8bpp). This tool re-encodes a PNG
to the same format/dimensions and overwrites the base mip level at the texture's
existing data address, leaving headers, mip chains, materials and geometry
untouched. Use ``tools/patch_asset.py`` afterwards to put the BCH back into its
PACK and rebuild the ROM.

Example:
    python tools/bch_texture_patch.py --list game_data/.../b001_101a.bch
    python tools/bch_texture_patch.py --bch in.bch --texture ko_b001_wall01 \
        --png wall.png --out out.bch
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.etc1_encode import encode_etc1
from tools.model_tool import BchParser


def texture_infos(data: bytes) -> list[dict]:
    b = BchParser(data)
    tree, count, _vals = struct.unpack_from("<3I", data, b.hdr_off + 3 * 12)
    if count <= 0 or tree == 0 or b.hdr_off + tree + count * 4 > len(data):
        return []
    ptrs = struct.unpack_from(f"<{count}I", data, b.hdr_off + tree)
    out = []
    for ptr in ptrs:
        if b.hdr_off + ptr + 32 > len(data):
            continue
        words = struct.unpack_from("<8I", data, b.hdr_off + ptr)
        name = b.get_string(words[7]) or f"texture_{len(out)}"
        cmd = words[0]
        if b.cmd_off + cmd + 4 > len(data):
            continue
        dim = struct.unpack_from("<I", data, b.cmd_off + cmd)[0]
        # DIM stores height in the low half and width in the high half.
        width, height = (dim >> 16) & 0xFFFF, dim & 0xFFFF
        if not (0 < width <= 2048 and 0 < height <= 2048):
            continue
        fmt = words[6] & 0xFF
        addr = 0
        # The format/address registers are encoded in the command stream. The
        # value precedes the register word on the 3DS PICA command stream.
        block = struct.unpack_from("<10I", data, b.cmd_off + cmd)
        for i, cw in enumerate(block):
            reg = cw & 0xFFFF
            if reg in (0x8E, 0x9E, 0xA6) and i > 0:
                fmt = block[i - 1]
            elif reg in (0x85, 0x95, 0x9D) and i > 0:
                addr = block[i - 1]
        if fmt not in (10, 11, 12, 13):
            continue
        base_size = width * height if fmt in (11, 13) else width * height // 2
        out.append({
            "name": name,
            "width": width,
            "height": height,
            "fmt": fmt,
            "addr": addr,
            "offset": b.data_off + addr,
            "base_size": base_size,
        })
    # available space = distance to the next texture payload
    ordered = sorted(out, key=lambda t: t["addr"])
    for i, t in enumerate(ordered):
        end = b.data_off + b.data_len
        if i + 1 < len(ordered):
            end = b.data_off + ordered[i + 1]["addr"]
        t["available"] = max(0, end - t["offset"])
    return out


def replace_texture(data: bytes, texture: str, png: Path) -> bytes:
    matches = [t for t in texture_infos(data) if t["name"].lower() == texture.lower()]
    if not matches:
        names = ", ".join(t["name"] for t in texture_infos(data))
        raise SystemExit(f"texture {texture!r} not found; available: {names}")
    info = matches[0]
    img = Image.open(png).convert("RGBA")
    if img.size != (info["width"], info["height"]):
        img = img.resize((info["width"], info["height"]), Image.Resampling.LANCZOS)
    alpha = info["fmt"] in (11, 13)
    encoded = encode_etc1(np.asarray(img, dtype=np.uint8), alpha=alpha)
    if len(encoded) > info["available"]:
        raise SystemExit(
            f"encoded base level is {len(encoded)} bytes but only "
            f"{info['available']} bytes are available before the next texture"
        )
    out = bytearray(data)
    out[info["offset"]:info["offset"] + len(encoded)] = encoded
    return bytes(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bch", type=Path, help="source BCH file")
    ap.add_argument("--list", action="store_true", help="list embedded textures and exit")
    ap.add_argument("--texture", help="texture name to replace")
    ap.add_argument("--png", type=Path, help="replacement PNG")
    ap.add_argument("--out", type=Path, help="output BCH (default: <bch>.patched.bch)")
    args = ap.parse_args()

    if args.list:
        if not args.bch:
            ap.error("--list requires --bch")
        data = args.bch.read_bytes()
        for t in texture_infos(data):
            print(f"{t['name']:32s} {t['width']:4d}x{t['height']:<4d} fmt={t['fmt']:2d} "
                  f"offset=0x{t['offset']:X} base={t['base_size']} available={t['available']}")
        return 0

    if not (args.bch and args.texture and args.png):
        ap.error("--bch, --texture and --png are required unless --list is used")
    data = args.bch.read_bytes()
    out = replace_texture(data, args.texture, args.png)
    dest = args.out or args.bch.with_suffix(".patched.bch")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(out)
    print(f"wrote {dest} ({len(out)} bytes, unchanged={len(out) == len(data)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
