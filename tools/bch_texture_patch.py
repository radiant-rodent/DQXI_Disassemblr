"""Replace one embedded BCH model texture in place (same file size).

DQXI BCH textures use the whole PICA200 format set: ETC1/ETC1A4 for most
diffuse maps, but also RGB565, RGBA4, RGBA8, L8, A8, L4, A4 and HiLo8. This
tool re-encodes a PNG to the *original* format/dimensions and overwrites the
base mip level at the texture's existing data address, leaving headers, mip
chains, materials and geometry untouched. Use ``tools/patch_asset.py`` (or
``tools/asset_replace.py replace --family model-texture``) afterwards to put
the BCH back into its PACK and rebuild the ROM.

ETC1 and 4-bit masks are lossy/quantised by definition; the tool reports that
instead of pretending the image survived exactly.

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

from tools import texture_tool
from tools.etc1_encode import encode_etc1
from tools.model_tool import BchParser


def _stored_dims(width: int, height: int) -> tuple[int, int]:
    p2 = lambda n: max(8, 1 << (n - 1).bit_length())  # noqa: E731
    return p2(width), p2(height)


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
        name_fmt = texture_tool.PICA_FORMATS.get(fmt)
        if name_fmt is None:
            continue
        sw, sh = _stored_dims(width, height)
        out.append({
            "name": name,
            "width": width,
            "height": height,
            "stored_width": sw,
            "stored_height": sh,
            "fmt": fmt,
            "format_name": name_fmt,
            "addr": addr,
            "offset": b.data_off + addr,
            "base_size": sw * sh * texture_tool._BPP[name_fmt] // 8,
        })
    # available space = distance to the next texture payload
    ordered = sorted(out, key=lambda t: t["addr"])
    for i, t in enumerate(ordered):
        end = b.data_off + b.data_len
        if i + 1 < len(ordered):
            end = b.data_off + ordered[i + 1]["addr"]
        t["available"] = max(0, end - t["offset"])
        t["mip_levels"] = _mip_levels(t)
    return out


def _mip_levels(info: dict) -> int:
    """How many mip levels actually fit between this texture and the next one.

    PICA mips stop at 8x8, and the available space is an upper bound (the last
    texture runs to the end of the data section), so this is deliberately
    conservative: it only reports a level when its bytes fit.
    """
    bpp = texture_tool._BPP[info["format_name"]]
    base = info["base_size"]
    remaining = info["available"] - base
    if remaining <= 0:
        return 1
    w, h = info["stored_width"], info["stored_height"]
    levels = 1
    while remaining > 0 and (w > 8 or h > 8):
        w, h = max(8, w // 2), max(8, h // 2)
        size = w * h * bpp // 8
        if size > remaining:
            break
        remaining -= size
        levels += 1
    return levels


def encode_for_info(info: dict, img: Image.Image) -> tuple[bytes, list[str]]:
    """Encodes an RGBA image to the texture's original PICA format."""
    warnings: list[str] = []
    fmt = info["format_name"]
    rgba = np.asarray(img.convert("RGBA"), dtype=np.uint8)
    sw, sh = info["stored_width"], info["stored_height"]
    if rgba.shape[1] < sw or rgba.shape[0] < sh:
        padded = np.zeros((sh, sw, 4), np.uint8)
        padded[: rgba.shape[0], : rgba.shape[1]] = rgba
        rgba = padded
    if fmt in ("ETC1", "ETC1A4"):
        encoded = encode_etc1(rgba, alpha=fmt == "ETC1A4")
    else:
        encoded = texture_tool.encode_tiled(rgba, sw, sh, fmt)
    if fmt in ("ETC1", "ETC1A4"):
        warnings.append(f"{fmt} is lossy; the replacement is re-encoded at 4 bits per pixel")
    elif fmt in ("L4", "A4", "LA4", "RGBA4", "RGBA5551", "RGB565"):
        warnings.append(f"{fmt} stores fewer bits than the PNG; colours are quantised")
    if info["mip_levels"] > 1:
        warnings.append(
            f"{info['mip_levels']} mip levels share this payload; only the base level is replaced "
            "and the retail mip chain stays (distant views may show the old image)"
        )
    if info["width"] > 2048 or info["height"] > 2048:
        raise SystemExit("texture exceeds the 3DS 2048 px maximum")
    return encoded, warnings


def replace_texture(data: bytes, texture: str, png: Path, allow_resize: bool = False) -> bytes:
    matches = [t for t in texture_infos(data) if t["name"].lower() == texture.lower()]
    if not matches:
        names = ", ".join(t["name"] for t in texture_infos(data))
        raise SystemExit(f"texture {texture!r} not found; available: {names}")
    info = matches[0]
    img = Image.open(png).convert("RGBA")
    if img.size != (info["width"], info["height"]):
        if not allow_resize:
            raise SystemExit(
                f"{png.name} is {img.width}x{img.height} but {texture} is "
                f"{info['width']}x{info['height']}; export the texture, keep its size, "
                "or pass --resize to scale it (nearest-neighbour is safer for pixel art)"
            )
        img = img.resize((info["width"], info["height"]), Image.Resampling.LANCZOS)
    encoded, _warnings = encode_for_info(info, img)
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
    ap.add_argument("--resize", action="store_true", help="scale a differently sized PNG instead of refusing")
    args = ap.parse_args()

    if args.list:
        if not args.bch:
            ap.error("--list requires --bch")
        data = args.bch.read_bytes()
        for t in texture_infos(data):
            print(f"{t['name']:32s} {t['width']:4d}x{t['height']:<4d} {t['format_name']:<8s} "
                  f"offset=0x{t['offset']:X} base={t['base_size']} available={t['available']}")
        return 0

    if not (args.bch and args.texture and args.png):
        ap.error("--bch, --texture and --png are required unless --list is used")
    data = args.bch.read_bytes()
    info = next((t for t in texture_infos(data) if t["name"].lower() == args.texture.lower()), None)
    if info is None:
        ap.error(f"texture {args.texture!r} not found; run --list")
    img = Image.open(args.png).convert("RGBA")
    if img.size != (info["width"], info["height"]) and not args.resize:
        ap.error(
            f"{args.png.name} is {img.width}x{img.height} but the texture is "
            f"{info['width']}x{info['height']} (pass --resize to scale)"
        )
    out = replace_texture(data, args.texture, args.png, allow_resize=args.resize)
    dest = args.out or args.bch.with_suffix(".patched.bch")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(out)
    _, warnings = encode_for_info(info, img)
    print(f"wrote {dest} ({len(out)} bytes, unchanged={len(out) == len(data)}, {info['format_name']})")
    for warning in warnings:
        print(f"  warning: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
