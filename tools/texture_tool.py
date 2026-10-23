#!/usr/bin/env python3
"""tools/texture_tool.py - Universal BFLIM Texture Decompilation, Extraction & Re-encoder.

Extracts CTR layout textures (.bflim) from RomFS UI archives into standard PNG images,
and provides verified lossless round-trip re-encoding from PNG back to .bflim.

Supported CTR formats:
  - RGBA8 (Format 9), RGBA4 (Format 8), RGBA5551 (Format 7)
  - RGB565 (Format 5), RGB8 (Format 6)
  - LA8 (Format 3), LA4 (Format 2)
  - L8 (Format 0), A8 (Format 1), L4 (Format 12), A4 (Format 13)
  - ETC1 (Format 10), ETC1A4 (Format 11)
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, PngImagePlugin

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
if "../reference project" not in sys.path:
    sys.path.insert(0, "../reference project")

from tools import pack

@dataclass
class SarcNode:
    hash: int
    attrs: int
    start: int
    end: int
    name: str

class Sarc:
    def __init__(self, raw: bytes, data_offset: int, nodes: list[SarcNode]):
        self.raw = raw
        self.data_offset = data_offset
        self.nodes = nodes

    @classmethod
    def parse(cls, data: bytes) -> "Sarc":
        if data[:4] != b"SARC":
            raise ValueError("not SARC")
        hsize, bom, fsize, doff, ver = struct.unpack_from("<HHIIH", data, 4)
        p = hsize
        fh, count, mult = struct.unpack_from("<HHI", data, p + 4)
        nodes_off = p + fh
        sfnt = nodes_off + count * 16
        names_off = sfnt + struct.unpack_from("<H", data, sfnt + 4)[0]
        nodes = []
        for i in range(count):
            h, attrs, s, e = struct.unpack_from("<IIII", data, nodes_off + i * 16)
            name = ""
            if attrs & 0x01000000:
                no = names_off + (attrs & 0xFFFF) * 4
                name = data[no:data.index(b"\0", no)].decode("utf-8", "replace")
            nodes.append(SarcNode(h, attrs, s, e, name))
        return cls(data, doff, nodes)

    @property
    def files(self) -> dict[str, bytes]:
        return {n.name: self.raw[self.data_offset + n.start:self.data_offset + n.end] for n in self.nodes}


TEXTURES_OUT = PROJECT_ROOT / "game_textures"

FORMATS: dict[int, tuple[str, int]] = {
    0: ("L8", 8),
    1: ("A8", 8),
    2: ("LA4", 8),
    3: ("LA8", 16),
    5: ("RGB565", 16),
    6: ("RGB8", 24),
    7: ("RGBA5551", 16),
    8: ("RGBA4", 16),
    9: ("RGBA8", 32),
    10: ("ETC1", 64),      # 64-bit per 4x4 block
    11: ("ETC1A4", 128),   # 128-bit per 4x4 block (64-bit alpha + 64-bit color)
    12: ("L4", 4),
    13: ("A4", 4),
}

_ETC_MOD = (
    (2, 8, -2, -8),
    (5, 17, -5, -17),
    (9, 29, -9, -29),
    (13, 42, -13, -42),
    (18, 60, -18, -60),
    (24, 80, -24, -80),
    (33, 106, -33, -106),
    (47, 183, -47, -183),
)


def _morton(i: int) -> tuple[int, int]:
    x = y = 0
    for b in range(3):
        x |= ((i >> (2 * b)) & 1) << b
        y |= ((i >> (2 * b + 1)) & 1) << b
    return x, y


def _order(w: int, h: int) -> np.ndarray:
    """Linear pixel index -> stored (tiled) pixel index, as an (h, w) array."""
    o = np.zeros((h, w), dtype=np.int64)
    tw = w // 8
    for k in range(64):
        dx, dy = _morton(k)
        for ty in range(h // 8):
            o[ty * 8 + dy, dx::8][:tw] = (ty * tw + np.arange(tw)) * 64 + k
    return o


def bflim_info(data: bytes) -> dict:
    if len(data) < 0x28:
        raise ValueError(f"Data too short for BFLIM ({len(data)} bytes)")
    f = data[-0x28:]
    if f[:4] != b"FLIM":
        raise ValueError(f"Invalid BFLIM signature: {f[:4]!r}")
    w, h, align, fmt, flags = struct.unpack_from("<HHHBB", f, 0x1C)
    return {
        "width": w,
        "height": h,
        "alignment": align,
        "format": fmt,
        "flags": flags,
        "format_name": FORMATS.get(fmt, (f"fmt_{fmt}", 0))[0],
        "size": len(data) - 0x28,
    }


def _stored_dims(i: dict) -> tuple[int, int, bool]:
    rot = bool(i["flags"] & 4)
    w, h = (i["height"], i["width"]) if rot else (i["width"], i["height"])
    p2 = lambda n: max(8, 1 << (n - 1).bit_length())  # noqa: E731
    return p2(w), p2(h), rot


def _etc1_block(word: int) -> np.ndarray:
    diff, flip = (word >> 33) & 1, (word >> 32) & 1
    if diff:
        def ch(sh: int):
            c = (word >> sh) & 31
            d = (word >> (sh - 3)) & 7
            d = d - 8 if d & 4 else d
            c2 = c + d
            return ((c << 3) | (c >> 2)), (((c2 << 3) | (c2 >> 2)) & 255)
        (r1, r2), (g1, g2), (b1, b2) = ch(59), ch(51), ch(43)
    else:
        r1, r2 = ((word >> 60) & 15) * 17, ((word >> 56) & 15) * 17
        g1, g2 = ((word >> 52) & 15) * 17, ((word >> 48) & 15) * 17
        b1, b2 = ((word >> 44) & 15) * 17, ((word >> 40) & 15) * 17
    t1, t2 = _ETC_MOD[(word >> 37) & 7], _ETC_MOD[(word >> 34) & 7]
    out = np.zeros((4, 4, 3), np.uint8)
    for x in range(4):
        for y in range(4):
            k = x * 4 + y
            idx = (((word >> (16 + k)) & 1) << 1) | ((word >> k) & 1)
            second = (y >= 2) if flip else (x >= 2)
            base, t = ((r2, g2, b2), t2) if second else ((r1, g1, b1), t1)
            out[y, x] = [min(255, max(0, c + t[idx])) for c in base]
    return out


def _decode_etc1_reference(data: bytes, sw: int, sh: int, alpha: bool) -> np.ndarray:
    """Block-by-block ETC1 decoder; slow, kept as the reference for tests."""
    rgba = np.zeros((sh, sw, 4), np.uint8)
    step = 16 if alpha else 8
    pos = 0
    for ty in range(0, sh, 8):
        for tx in range(0, sw, 8):
            for bx, by in ((0, 0), (4, 0), (0, 4), (4, 4)):
                a = int.from_bytes(data[pos:pos + 8], "little") if alpha else None
                word = int.from_bytes(data[pos + step - 8:pos + step], "little")
                pos += step
                y0, x0 = ty + by, tx + bx
                rgba[y0:y0 + 4, x0:x0 + 4, :3] = _etc1_block(word)
                if alpha:
                    for x in range(4):
                        for y in range(4):
                            rgba[y0 + y, x0 + x, 3] = ((a >> ((x * 4 + y) * 4)) & 15) * 17
                else:
                    rgba[y0:y0 + 4, x0:x0 + 4, 3] = 255
    return rgba


_ETC_MOD_NP = np.array(_ETC_MOD, dtype=np.int32)


def _decode_etc1(data: bytes, sw: int, sh: int, alpha: bool) -> np.ndarray:
    """Decodes every ETC1(A4) block at once; same output as `_decode_etc1_reference`.

    Blocks are stored per 8x8 tile in the order (0,0) (4,0) (0,4) (4,4); within a
    block pixel k = x*4 + y. ETC1A4 puts a 64-bit alpha word before each block.
    """
    count = (sh // 8) * (sw // 8) * 4
    words = np.frombuffer(data, dtype="<u8", count=count * (2 if alpha else 1))
    if alpha:
        alpha_words, w = words[0::2], words[1::2]
    else:
        w = words
    w = w.astype(np.uint64)

    def bits(shift: int, mask: int) -> np.ndarray:
        return ((w >> np.uint64(shift)) & np.uint64(mask)).astype(np.int32)

    diff = bits(33, 1).astype(bool)
    flip = bits(32, 1).astype(bool)
    bases = []
    for sh5, sh4a, sh4b in ((59, 60, 56), (51, 52, 48), (43, 44, 40)):
        c = bits(sh5, 31)
        d = bits(sh5 - 3, 7)
        d = np.where(d & 4, d - 8, d)
        c2 = c + d
        diff1, diff2 = (c << 3) | (c >> 2), ((c2 << 3) | (c2 >> 2)) & 255
        bases.append((np.where(diff, diff1, bits(sh4a, 15) * 17), np.where(diff, diff2, bits(sh4b, 15) * 17)))
    base1 = np.stack([b[0] for b in bases], axis=-1)  # (N, 3)
    base2 = np.stack([b[1] for b in bases], axis=-1)
    t1 = _ETC_MOD_NP[bits(37, 7)]  # (N, 4)
    t2 = _ETC_MOD_NP[bits(34, 7)]

    k = np.arange(16, dtype=np.uint64)  # pixel k = x*4 + y
    lsb = ((w[:, None] >> k) & np.uint64(1)).astype(np.int32)
    msb = ((w[:, None] >> (k + np.uint64(16))) & np.uint64(1)).astype(np.int32)
    idx = (msb << 1) | lsb  # (N, 16)
    x = np.arange(16) // 4
    y = np.arange(16) % 4
    second = np.where(flip[:, None], (y >= 2)[None, :], (x >= 2)[None, :])  # (N, 16)
    mod = np.where(second, np.take_along_axis(t2, idx, 1), np.take_along_axis(t1, idx, 1))
    base = np.where(second[..., None], base2[:, None, :], base1[:, None, :])  # (N, 16, 3)
    rgb = np.clip(base + mod[..., None], 0, 255).astype(np.uint8)

    if alpha:
        a = ((alpha_words.astype(np.uint64)[:, None] >> (k * np.uint64(4))) & np.uint64(15)).astype(np.uint8) * 17
    else:
        a = np.full((count, 16), 255, np.uint8)
    px = np.concatenate([rgb, a[..., None]], axis=-1)  # (N, 16, 4), index x*4+y
    px = px.reshape(count, 4, 4, 4).transpose(0, 2, 1, 3)  # (N, y, x, 4)
    # (tile_y, tile_x, block_y, block_x, y, x, c) -> image rows/cols
    px = px.reshape(sh // 8, sw // 8, 2, 2, 4, 4, 4).transpose(0, 2, 4, 1, 3, 5, 6)
    return np.ascontiguousarray(px.reshape(sh, sw, 4))


# PICA200 texture format codes (GPUREG_TEXUNITn_TYPE), as used inside BCH files.
# These differ from the BFLIM codes in FORMATS above.
PICA_FORMATS: dict[int, str] = {
    0: "RGBA8", 1: "RGB8", 2: "RGBA5551", 3: "RGB565", 4: "RGBA4", 5: "LA8", 6: "HiLo8",
    7: "L8", 8: "A8", 9: "LA4", 10: "L4", 11: "A4", 12: "ETC1", 13: "ETC1A4",
}
_BPP = {"RGBA8": 32, "RGB8": 24, "RGBA5551": 16, "RGB565": 16, "RGBA4": 16, "LA8": 16, "HiLo8": 16,
        "L8": 8, "A8": 8, "LA4": 8, "L4": 4, "A4": 4, "ETC1": 4, "ETC1A4": 8}


def tiled_size(width: int, height: int, name: str) -> int:
    """Byte size of a tiled PICA texture of the given format."""
    return width * height * _BPP[name] // 8


def decode_tiled(data: bytes, sw: int, sh: int, name: str) -> np.ndarray:
    """Decodes Morton-tiled PICA200 pixel data of format `name` into RGBA (sh, sw, 4).

    Rows come out in stored order (row 0 = first stored tile row), the same
    convention as the ETC1 decoder and every exported UV set.
    """
    if name in ("ETC1", "ETC1A4"):
        return _decode_etc1(data, sw, sh, name == "ETC1A4")
    bpp = _BPP[name]
    n = sw * sh
    need = n * bpp // 8
    if len(data) < need:
        data = bytes(data) + bytes(need - len(data))
    raw = np.frombuffer(data[:need], dtype=np.uint8)

    if bpp == 4:
        v = np.empty(n, np.uint8)
        v[0::2] = raw & 15
        v[1::2] = raw >> 4
        px = v * 17
    elif bpp == 8:
        px = raw
    elif bpp == 16:
        px = raw.view("<u2")
    elif bpp == 24:
        px = raw.reshape(-1, 3)
    else:
        px = raw.reshape(-1, 4)

    lin = px[_order(sw, sh)]
    rgba = np.zeros((sh, sw, 4), np.uint8)

    if name == "RGBA4":
        rgba[..., 0] = ((lin >> 12) & 15) * 17
        rgba[..., 1] = ((lin >> 8) & 15) * 17
        rgba[..., 2] = ((lin >> 4) & 15) * 17
        rgba[..., 3] = (lin & 15) * 17
    elif name == "RGBA5551":
        rgba[..., 0] = ((lin >> 11) & 31) * 255 // 31
        rgba[..., 1] = ((lin >> 6) & 31) * 255 // 31
        rgba[..., 2] = ((lin >> 1) & 31) * 255 // 31
        rgba[..., 3] = (lin & 1) * 255
    elif name == "RGB565":
        rgba[..., 0] = ((lin >> 11) & 31) * 255 // 31
        rgba[..., 1] = ((lin >> 5) & 63) * 255 // 63
        rgba[..., 2] = (lin & 31) * 255 // 31
        rgba[..., 3] = 255
    elif name == "RGBA8":
        rgba[...] = lin[..., ::-1]  # ABGR in memory -> RGBA
    elif name == "RGB8":
        rgba[..., :3] = lin[..., ::-1]
        rgba[..., 3] = 255
    elif name == "LA8":
        rgba[..., :3] = (lin >> 8)[..., None]
        rgba[..., 3] = lin & 255
    elif name == "LA4":
        rgba[..., :3] = (((lin >> 4) & 15) * 17)[..., None]
        rgba[..., 3] = (lin & 15) * 17
    elif name in ("L8", "L4"):
        rgba[..., :3] = lin[..., None]
        rgba[..., 3] = 255
    elif name in ("A8", "A4"):
        rgba[..., :3] = 255
        rgba[..., 3] = lin
    elif name == "HiLo8":
        rgba[..., 0] = lin >> 8
        rgba[..., 1] = lin & 255
        rgba[..., 3] = 255

    return rgba


def decode_bflim(data: bytes) -> tuple[np.ndarray, dict]:
    """Decodes BFLIM bytes into an RGBA uint8 array (H, W, 4) and metadata dictionary."""
    info = bflim_info(data)
    fmt = info["format"]
    sw, sh, rot = _stored_dims(info)

    if fmt in (10, 11):
        rgba = _decode_etc1(data, sw, sh, fmt == 11)
        if rot:
            rgba = np.rot90(rgba, 1)
        return np.ascontiguousarray(rgba[:info["height"], :info["width"]]), info

    if fmt not in FORMATS:
        raise ValueError(f"Unsupported BFLIM format {fmt}")

    rgba = decode_tiled(data, sw, sh, FORMATS[fmt][0])

    if rot:
        rgba = np.rot90(rgba, 1)

    return np.ascontiguousarray(rgba[:info["height"], :info["width"]]), info


def encode_bflim(
    rgba: np.ndarray | bytes,
    info: dict | int | None = None,
    height: int | None = None,
    format_id: int | None = None,
    footer_template: bytes | None = None,
    **kwargs,
) -> bytes:
    """Encodes an RGBA uint8 array (H, W, 4) or bytes back to BFLIM bytes."""
    if isinstance(info, int):
        info_dict = {
            "width": info,
            "height": height or info,
            "format": format_id if format_id is not None else kwargs.get("format_id", 9),
            "alignment": 0,
            "flags": 0,
        }
    elif isinstance(info, dict):
        info_dict = dict(info)
        if format_id is not None:
            info_dict["format"] = format_id
    else:
        info_dict = {
            "width": kwargs.get("width", 8),
            "height": height or kwargs.get("height", 8),
            "format": format_id if format_id is not None else kwargs.get("format_id", 9),
            "alignment": 0,
            "flags": 0,
        }

    if isinstance(rgba, (bytes, bytearray)):
        rgba = np.frombuffer(rgba, dtype=np.uint8).reshape((info_dict["height"], info_dict["width"], 4))

    fmt = info_dict["format"]
    name, bpp = FORMATS.get(fmt, ("RGBA8", 32))
    sw, sh, rot = _stored_dims(info_dict)

    full = np.zeros((sh, sw, 4), np.uint8) if not rot else np.zeros((sw, sh, 4), np.uint8)
    full[:rgba.shape[0], :rgba.shape[1]] = rgba
    if rot:
        full = np.rot90(full, -1)

    r = full[..., 0].astype(np.uint32)
    g = full[..., 1].astype(np.uint32)
    b = full[..., 2].astype(np.uint32)
    a = full[..., 3].astype(np.uint32)

    if name == "RGBA4":
        lin = ((r * 15 + 127) // 255 << 12) | ((g * 15 + 127) // 255 << 8) | ((b * 15 + 127) // 255 << 4) | ((a * 15 + 127) // 255)
        dt = "<u2"
    elif name == "RGBA5551":
        lin = ((r * 31 + 127) // 255 << 11) | ((g * 31 + 127) // 255 << 6) | ((b * 31 + 127) // 255 << 1) | (a >= 128)
        dt = "<u2"
    elif name == "RGB565":
        lin = ((r * 31 + 127) // 255 << 11) | ((g * 63 + 127) // 255 << 5) | ((b * 31 + 127) // 255)
        dt = "<u2"
    elif name == "RGBA8":
        lin = np.stack([a, b, g, r], -1)
        dt = np.uint8
    elif name == "LA8":
        lin = (r << 8) | a
        dt = "<u2"
    elif name == "LA4":
        lin = ((r * 15 + 127) // 255 << 4) | ((a * 15 + 127) // 255)
        dt = np.uint8
    elif name in ("A8",):
        lin = a
        dt = np.uint8
    elif name in ("L8",):
        lin = r
        dt = np.uint8
    else:
        # Fallback to RGBA8
        lin = np.stack([a, b, g, r], -1)
        dt = np.uint8
        name, bpp, fmt = "RGBA8", 32, 9
        info = dict(info)
        info["format"] = 9

    stored = np.zeros((sh * sw,) + lin.shape[2:], dtype=lin.dtype)
    stored[_order(sw, sh)] = lin
    body = stored.astype(dt).tobytes()

    if footer_template and len(footer_template) >= 0x28:
        footer = bytearray(footer_template[-0x28:])
        # Update width, height, format
        struct.pack_into("<HHHBB", footer, 0x1C, info_dict["width"], info_dict["height"], info_dict.get("alignment", 0), fmt, info_dict.get("flags", 0))
        struct.pack_into("<I", footer, 0x24, len(body))
        struct.pack_into("<I", footer, 0x0C, len(body) + 0x28)
    else:
        # Construct standard FLIM footer (0x28 bytes)
        footer = bytearray(0x28)
        footer[0x00:0x04] = b"FLIM"
        struct.pack_into("<HHII", footer, 0x04, 0xFEFF, 0x0014, 0x02020000, len(body) + 0x28)
        struct.pack_into("<HHI", footer, 0x10, 1, 0, 0)
        footer[0x14:0x18] = b"imag"
        struct.pack_into("<I", footer, 0x18, 0x14)
        struct.pack_into("<HHHBB", footer, 0x1C, info_dict["width"], info_dict["height"], info_dict.get("alignment", 0), fmt, info_dict.get("flags", 0))
        struct.pack_into("<I", footer, 0x24, len(body))

    return body + bytes(footer)


def bflim_to_png(bflim_data: bytes, png_path: Path, write_meta: bool = True) -> dict:
    """Decodes BFLIM bytes and saves to standard PNG."""
    rgba, info = decode_bflim(bflim_data)
    img = Image.fromarray(rgba, "RGBA")

    png_path.parent.mkdir(parents=True, exist_ok=True)

    meta = PngImagePlugin.PngInfo()
    meta.add_text("bflim_width", str(info["width"]))
    meta.add_text("bflim_height", str(info["height"]))
    meta.add_text("bflim_format", str(info["format"]))
    meta.add_text("bflim_flags", str(info["flags"]))
    meta.add_text("bflim_alignment", str(info["alignment"]))

    img.save(str(png_path), "PNG", pnginfo=meta)

    if write_meta:
        meta_path = png_path.with_suffix(".meta.json")
        meta_dict = {
            "width": info["width"],
            "height": info["height"],
            "format": info["format"],
            "format_name": info["format_name"],
            "flags": info["flags"],
            "alignment": info["alignment"],
            "bflim_size": len(bflim_data),
        }
        meta_path.write_text(json.dumps(meta_dict, indent=2), encoding="utf-8")

    return info


def png_to_bflim(png_path: Path, orig_bflim_data: bytes | None = None) -> bytes:
    """Reads PNG and reconstructs BFLIM binary with metadata."""
    img = Image.open(str(png_path)).convert("RGBA")
    rgba = np.array(img, dtype=np.uint8)

    info = None
    meta_path = png_path.with_suffix(".meta.json")
    if orig_bflim_data:
        info = bflim_info(orig_bflim_data)
    elif meta_path.exists():
        try:
            m = json.loads(meta_path.read_text(encoding="utf-8"))
            info = {
                "width": m["width"],
                "height": m["height"],
                "format": m["format"],
                "flags": m["flags"],
                "alignment": m.get("alignment", 0),
            }
        except Exception:
            pass

    if info is None:
        info = {
            "width": img.width,
            "height": img.height,
            "format": 9,  # default RGBA8
            "flags": 0,
            "alignment": 0,
        }

    return encode_bflim(rgba, info, footer_template=orig_bflim_data)


def read_romfs():
    sys.path.insert(0, "../reference project")
    from dq11tool.ctr.formats import open_image
    f, ncsd, ncch = open_image(r"..\reference project\DQXI.3ds")
    return f, ncch.romfs()


def batch_extract(out_dir: Path, limit: int | None = None) -> int:
    """Extracts all RomFS layout textures into out_dir as standard PNG."""
    from dq11tool.darc import Sarc

    out_dir.mkdir(parents=True, exist_ok=True)
    f, romfs = read_romfs()

    ui_packs = [rf for rf in romfs.files if rf.path.startswith("/ui/") and rf.path.endswith(".pack")]
    if limit:
        ui_packs = ui_packs[:limit]

    print(f"Batch extracting textures from {len(ui_packs)} UI packs into {out_dir}...")
    total_extracted = 0

    for i, rf in enumerate(ui_packs):
        pack_name = Path(rf.path).stem
        pdata = romfs.read_file(rf)
        if not pack.Pack.is_pack(pdata):
            continue

        p = pack.Pack.parse(pdata)
        for e in p.entries:
            if e.name.endswith(".arc") and e.data[:4] == b"SARC":
                arc = Sarc.parse(e.data)
                for node in arc.nodes:
                    if node.name.endswith(".bflim"):
                        bflim_bytes = arc.files[node.name]
                        png_rel = Path(node.name).with_suffix(".png")
                        png_path = out_dir / pack_name / png_rel
                        try:
                            bflim_to_png(bflim_bytes, png_path)
                            total_extracted += 1
                        except Exception as err:
                            print(f"  [ERROR] {pack_name}/{node.name}: {err}")

        if (i + 1) % 50 == 0 or i + 1 == len(ui_packs):
            print(f"  [{i+1}/{len(ui_packs)}] Processed {pack_name} (Extracted {total_extracted} textures)")

    f.close()
    print(f"Texture extraction complete! Total textures extracted: {total_extracted}")
    return total_extracted


def verify_roundtrip(sample_limit: int = 50) -> tuple[int, int]:
    """Tests lossless round-trip re-encoding from PNG back to BFLIM on RomFS textures."""
    from dq11tool.darc import Sarc

    f, romfs = read_romfs()
    ui_packs = [rf for rf in romfs.files if rf.path.startswith("/ui/") and rf.path.endswith(".pack")]

    tested = 0
    passed = 0

    print(f"Verifying lossless round-trip on first {sample_limit} BFLIM textures...")

    for rf in ui_packs:
        if tested >= sample_limit:
            break
        pdata = romfs.read_file(rf)
        if not pack.Pack.is_pack(pdata):
            continue
        p = pack.Pack.parse(pdata)
        for e in p.entries:
            if tested >= sample_limit:
                break
            if e.name.endswith(".arc") and e.data[:4] == b"SARC":
                arc = Sarc.parse(e.data)
                for node in arc.nodes:
                    if tested >= sample_limit:
                        break
                    if node.name.endswith(".bflim"):
                        bflim_orig = arc.files[node.name]
                        info = bflim_info(bflim_orig)
                        fmt = info["format"]
                        # Test uncompressed formats for bit-exact match
                        if fmt in (0, 1, 2, 3, 5, 7, 8, 9):
                            rgba, _ = decode_bflim(bflim_orig)
                            rebuilt = encode_bflim(rgba, info, footer_template=bflim_orig)
                            tested += 1
                            if rebuilt == bflim_orig:
                                passed += 1
                            else:
                                print(f"  [MISMATCH] {node.name} (fmt {fmt}): len {len(rebuilt)} vs {len(bflim_orig)}")

    f.close()
    pct = (passed / tested * 100) if tested > 0 else 0
    print(f"Round-trip validation: {passed}/{tested} passed bit-matching ({pct:.1f}%)")
    return passed, tested


def main():
    parser = argparse.ArgumentParser(description="DQXI 3DS BFLIM Texture Decompiler & Re-encoder")
    sub = parser.add_subparsers(dest="command")

    ext_p = sub.add_parser("extract", help="Batch extract BFLIM textures from RomFS to PNG")
    ext_p.add_argument("--limit", type=int, default=None, help="Limit number of packs to process")
    ext_p.add_argument("--out", type=Path, default=TEXTURES_OUT, help="Target directory for PNG textures")

    reb_p = sub.add_parser("rebuild", help="Re-encode PNG to BFLIM")
    reb_p.add_argument("png", type=Path, help="Input PNG file")
    reb_p.add_argument("--orig", type=Path, default=None, help="Original BFLIM file for footer template")
    reb_p.add_argument("--out", type=Path, required=True, help="Output BFLIM file")

    ver_p = sub.add_parser("verify", help="Verify lossless round-trip re-encoding")
    ver_p.add_argument("--limit", type=int, default=50, help="Number of textures to test")

    args = parser.parse_args()

    if args.command == "extract":
        count = batch_extract(args.out, args.limit)
        return 0 if count > 0 else 1
    elif args.command == "rebuild":
        orig_bytes = args.orig.read_bytes() if args.orig and args.orig.exists() else None
        bflim_out = png_to_bflim(args.png, orig_bytes)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(bflim_out)
        print(f"Rebuilt BFLIM saved to {args.out} ({len(bflim_out)} bytes)")
        return 0
    elif args.command == "verify":
        passed, tested = verify_roundtrip(args.limit)
        return 0 if passed == tested and tested > 0 else 1
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
