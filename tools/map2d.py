#!/usr/bin/env python3
"""2D-mode maps and sprites: decode, render and export for the Level Editor's 2D view.

The 3DS version has a full second set of maps for the 2D mode (the 16-bit style view chosen at the priest).
They are separate from the 3D data and were never exported before:

``2d/bg/<level>/<level>.bch``  textures only (no meshes, so the model converter skipped them):
    ``<level>_rgb_<time>`` = the opaque ground tile sheet, ``<level>_rgba_<time>`` = the overlay sheet with alpha,
    for time = daytime / evening / night / morning (a 16x16 placeholder when the map has no such variant).

``2d/bg/<level>/<level>.chp``  "CHIP" container (parser: symbols.json, Field2D CHIP loader). Header at +0: magic,
    file size, BOM, u16 section count at +0xC, section table (absolute u32 offsets) at +0x18. Each section =
    0x28-byte header {u16 header size, u16 flags, u32 payload size, char name[0x20]} + payload. Sections: Header,
    Areas, AnimRGBA, AnimData, CharacterDepth, Name, BlockData00 (itself holding BlockInfo, Layers, ChipInfos,
    Indices, Geography). Decoded here (verified by rendering b001_101a, b002_101a, b011_001a):

    BlockInfo (u16 words) w[2], w[3] = map size in pixels; base grid = 16 px cells, w[20] columns,
              rows = w[18] - w[14] + 1; overlay grid = 8 px cells starting at cell (w[13], w[15]),
              w[21] columns, rows = w[19] - w[15] + 1.
    ChipInfos 6-byte records: u8 column, u8 row of the tile in its sheet, u8 ?, u8 attributes (collision kind),
              u8 ?, u8 flags.  Base cells use 16x16 tiles of the rgb sheet, overlay cells 8x8 tiles of the rgba sheet.
    Indices   u16 chip ids, one block per layer: one or two 16 px base layers (rgb sheet; the first is complete and
              chip 0 is a real tile, the map's most common ground; a second one, in 28 of 485 maps such as Mount
              Zellanda, uses 0xFFFF = empty), then the 8 px overlay layers (rgba sheet, 0xFFFF = empty).
    Layers    u32 start offset of every layer in Indices. Entries past the data / out of order are junk, and
              m014_002a's list stops early, so ChipMap also cuts blocks by their length.

``level2d/<level>/level2d.bxon``  the 2D objects. Same container idea as level3d (docs/LEVEL_FORMAT.md):
    root +0x34 = array of 16-byte entries, each +0x04 -> 804-byte container(s) whose fields are record arrays.
    Coordinates are in 8 px units (the priest of b002_101a stands behind the altar at (41, 37)).
        +0xD8 / +0xE0 / +0xF8  60-byte actors: u16 entity id +0x20, x +0x22, y +0x24, u16 +0x26 (facing / flags)
        +0xC0  36-byte triggers: x +0x10, y +0x12, width +0x14, height +0x16 (cells)
        +0x50  28-byte exits: u32 +0x10 = (locator << 16) | destination map id (same word as the 3D exit)
        +0x178 20-byte points: x +0x04, y +0x06
        +0x300 20-byte points: x +0x02, y +0x04
    An actor id is a row of the region's ``npc_list`` (like 3D): word 10 indexes ``gamecmn/res_model2d``'s names,
    the low byte of word 12 is the variant letter -> ``2d/model/<name><variant>.bch`` (2,975 of 2,980 rows resolve).

        gimmicks (chest, pot, door, drawer, signboard, book, bookshelf, sparkly spot): see GIMMICKS below
``level2d/<level>/leveldmap.bxon``  the walk grids (2D collision), see ``collision``.

``2d/model/<name>/<name>.bch``  one sprite sheet per character (e.g. a0001a: 128x32, eight 16x32 frames).

Outputs (``python tools/map2d.py export``):
    game_assets/textures/2d_maps/<level>_<time>.png    rendered maps (also listed in the Textures panel, pack "2d_maps")
    (sprite sheets: game_assets/textures/2d_sprites/, written by tools/export_bch_assets.py)
    game_assets/maps/<level>/scene2d.json              2D objects and walk grids for the Level Editor's 2D view
    game_assets/maps2d/<level>/                        chipmap.json, indices.bin, tile sheets: the editable tile map
    game_assets/maps/sprites2d.json                    region -> actor id -> sprite name

    python tools/map2d.py render b011_001a out.png [--time night]
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATA = ROOT / "game_data" / "packs"
BG = DATA / "2d" / "bg"
MODELS2D = DATA / "2d" / "model"
OUT_MAPS = ROOT / "game_assets" / "textures" / "2d_maps"
SCENES = ROOT / "game_assets" / "maps"
OUT_TILES = ROOT / "game_assets" / "maps2d"  # per background: chipmap.json, indices.bin, rgb_<time>.png, rgba_<time>.png
TIMES = ("daytime", "evening", "night", "morning")

ACTOR_ARRAYS = ("+0xD8", "+0xE0", "+0xF8")

# 2D gimmicks (interactable objects). array -> (record size, label, sprite-type offset, x offset, y offset, drop-row offset).
# The sprite type is an index into gamecmn/res_model2d's names (g0030 = chest ...), like an actor's npc_list word 10.
# A drop row is a row of fieldcmn/fixed_drop_param, the same number the level's 3D record carries (b011_001a: chests 38,
# 39, 683 in both level2d +0x110 and level3d +0x230; pots 48 in +0x120 and 3D +0x240). Sparkle ids are rows of
# equal to the 3D +0x2E0 ids (d007_001a: 400..408 in both). The 3D record is a TOCKLE spot (emulator 2026-11-16: drawn
# as a coloured Tockle; class GmSpiritGenerator2DGlitter in 2D), not a sparkly spot as first assumed; the item shown
# from glitter_drop_param for these ids is therefore unproven. The real sparkly spot is level2d +0x168 (28 bytes,
# glitter row at +0x12) = level3d +0x298 (24 bytes, row at +0x10); the 3D one is emulator-proven (sparkle + item).
GIMMICKS = {
    "+0x110": (28, "Treasure chest", 0x0A, 0x0E, 0x10, 0x0C),
    "+0x120": (28, "Pot", 0x0A, 0x0C, 0x0E, 0x12),
    "+0x128": (48, "Door", 0x1A, 0x1C, 0x1E, None),
    "+0x130": (48, "Double door", 0x1A, 0x1C, 0x1E, None),
    "+0x138": (48, "Gate", 0x1A, 0x1C, 0x1E, None),
    "+0x140": (28, "Dresser", 0x0A, 0x0E, 0x10, 0x0C),
    "+0x148": (28, "Wardrobe", 0x0A, 0x0E, 0x10, 0x0C),
    "+0x150": (28, "Drawer", 0x0A, 0x0E, 0x10, 0x0C),
    "+0x158": (36, "Signboard", 0x12, 0x14, 0x16, None),
    "+0x160": (28, "Object", 0x0A, 0x0C, 0x0E, None),
    "+0x168": (28, "Sparkly spot", None, 0x0A, 0x0C, None),   # w, h at +0x0E / +0x10, glitter row at +0x12
    "+0x170": (36, "Bookshelf", None, 0x14, 0x16, None),
    "+0x280": (40, "Tockle spot", None, 0x12, 0x14, None),
}
DOOR_ARRAYS = ("+0x128", "+0x130", "+0x138")
OBJECT_NAMES = {"g0055": "Book", "g0050": "Signboard", "g0561": "Ornate chest"}

# editable u16 fields per record kind: name -> offset inside the record
FIELDS = {
    "actor": {"entity_id": 0x20, "x": 0x22, "y": 0x24},
    "trigger": {"x": 0x10, "y": 0x12, "w": 0x14, "h": 0x16},
    "point178": {"x": 0x04, "y": 0x06},
    "point300": {"x": 0x02, "y": 0x04},
}


# --------------------------------------------------------------------------- CHIP container
def chp_sections(d: bytes) -> dict[str, tuple[int, int, int]]:
    """name -> (payload offset, payload size, flags); children of BlockData00 as 'BlockData00/<name>'."""
    out: dict[str, tuple[int, int, int]] = {}

    def header(at: int):
        hs, fl, ps = struct.unpack_from("<HHI", d, at)
        name = d[at + 8:at + 0x28].split(b"\0")[0].decode("ascii", "replace")
        return hs, fl, ps, name

    count = struct.unpack_from("<H", d, 0xC)[0]
    for i in range(count):
        at = struct.unpack_from("<I", d, 0x18 + 4 * i)[0]
        hs, fl, ps, name = header(at)
        out[name] = (at + hs, ps, fl)
        if name.startswith("BlockData"):
            # a nested CHIP-like block: its own section table at +0xC/+0x18 relative to the payload
            base = at + hs
            sub = struct.unpack_from("<H", d, base + 0xC)[0]
            for k in range(sub):
                rel = struct.unpack_from("<I", d, base + 0x18 + 4 * k)[0]
                h2, f2, p2, n2 = header(base + rel)
                out[f"{name}/{n2}"] = (base + rel + h2, p2, f2)
    return out


class ChipMap:
    def __init__(self, data: bytes):
        s = chp_sections(data)
        bi_off = s["BlockData00/BlockInfo"][0]
        w = struct.unpack_from("<24H", data, bi_off)
        self.width, self.height = w[2], w[3]
        self.base_cols = w[20]
        self.base_rows = w[18] - w[14] + 1
        self.ov_x, self.ov_y = w[13], w[15]
        self.ov_cols = w[21]
        self.ov_rows = w[19] - w[15] + 1
        co, cn, _ = s["BlockData00/ChipInfos"]
        self.chips = [data[co + 6 * i:co + 6 * i + 6] for i in range(cn // 6)]
        io, isz, _ = s["BlockData00/Indices"]
        ids = struct.unpack_from(f"<{isz // 2}H", data, io)
        base = self.base_cols * self.base_rows
        size = self.ov_cols * self.ov_rows
        # Layers = u32 start offsets (in ids) of each layer; trailing entries past the data or out of order are junk
        # (b002_101a's 4th entry, d017_003a's last two) and m014_002a's list stops early, so every block is then cut
        # into base-sized (16 px) and overlay-sized (8 px) layers by its length.
        lo, lsz, _ = s["BlockData00/Layers"]
        starts: list[int] = []
        for o in struct.unpack_from(f"<{lsz // 4}I", data, lo):
            if o >= len(ids) or (starts and o <= starts[-1]):
                break
            starts.append(o)
        if not starts or starts[0] != 0:
            starts = [0, base]
        self.base_layers: list[tuple] = []
        self.overlays: list[tuple] = []
        self.layer_starts: list[tuple[str, int]] = []  # ("base" | "overlay", first index in Indices), draw order
        self.ids = ids
        for a, b in zip(starts, starts[1:] + [len(ids)]):
            # base layers come first; a block may hold several layers when the offset list is short
            if not self.overlays and b - a >= base and (b - a == base or (size and (b - a - base) % size == 0)):
                self.base_layers.append(ids[a:a + base])
                self.layer_starts.append(("base", a))
                a += base
            while size and b - a >= size:
                self.overlays.append(ids[a:a + size])
                self.layer_starts.append(("overlay", a))
                a += size
        if not self.base_layers:
            self.base_layers = [ids[:base]]
            self.layer_starts.insert(0, ("base", 0))
        self.base = self.base_layers[0]

    def info(self) -> dict:
        return {
            "width": self.width,
            "height": self.height,
            "base_grid": [self.base_cols, self.base_rows, 16],
            "overlay_grid": [self.ov_x, self.ov_y, self.ov_cols, self.ov_rows, 8],
            "overlay_layers": len(self.overlays),
            "chips": len(self.chips),
        }


def transform(tile, flags: int):
    """ChipInfo byte 5 bits 0x0E pick one of the 8 tile orientations (0x10 marks overlay chips). Not independent flip
    bits: a lookup.

        0 none   2 rotate 90 ccw   4 rotate 180   6 rotate 90 cw
        8 mirror 10 vertical flip  12 transpose   14 anti-diagonal flip (transverse)

    Derived from the b002_101a carpet, where sheet tile (4,2) is the corner (dark seam top + left) and (5,2) the edge
    (seam top) and the seam must face outwards (user check): flag 2 edge -> seam left and corner -> bottom+left,
    4 corner -> bottom+right, 6 corner -> top+right, 10 edge -> bottom, 14 edge -> right. Flag 8 alone is the mirror
    (mirrored overlay chips list their sheet columns in swapped pairs, b002_101a chips 71/72 = columns 45/44; the
    church windows only come out symmetric with it). No "three independent bits" encoding satisfies all of these;
    flag 12 was settled by matching tile edges against unflagged neighbours across 81 maps (transpose 4, mirror 1).
    Earlier guesses (rot270 / transverse for bit 0x02, mirror-then-rotate) each left some carpet sides wrong."""
    from PIL import Image

    op = {
        2: Image.Transpose.ROTATE_90,
        4: Image.Transpose.ROTATE_180,
        6: Image.Transpose.ROTATE_270,
        8: Image.Transpose.FLIP_LEFT_RIGHT,
        10: Image.Transpose.FLIP_TOP_BOTTOM,
        12: Image.Transpose.TRANSPOSE,
        14: Image.Transpose.TRANSVERSE,
    }.get(flags & 0x0E)
    return tile.transpose(op) if op is not None else tile


def sheets(level: str) -> dict[str, "object"]:
    from tools.model_tool import BchParser

    path = BG / level / f"{level}.bch"
    return dict(BchParser(path.read_bytes(), source_path=path).extract_textures())


def render(level: str, time: str = "daytime", tex: dict | None = None):
    from PIL import Image

    cm = ChipMap((BG / level / f"{level}.chp").read_bytes())
    tex = tex or sheets(level)
    rgb = tex.get(f"{level}_rgb_{time}")
    rgba = tex.get(f"{level}_rgba_{time}")
    if rgb is None or rgb.width <= 16:  # placeholder: this time of day uses the daytime sheets
        rgb = tex.get(f"{level}_rgb_daytime")
        rgba = tex.get(f"{level}_rgba_daytime")
    img = Image.new("RGBA", (cm.width, cm.height), (0, 0, 0, 255))
    cache: dict[tuple, object] = {}

    def tile(sheet, chip: int, size: int):
        key = (id(sheet), chip, size)
        if key not in cache:
            e = cm.chips[chip] if chip < len(cm.chips) else b"\0" * 6
            t = sheet.crop((e[0] * size, e[1] * size, e[0] * size + size, e[1] * size + size))
            cache[key] = transform(t, e[5])
        return cache[key]

    if rgb is not None:
        for layer in cm.base_layers:
            for i, c in enumerate(layer):
                if c != 0xFFFF:  # chip 0 is a real tile (usually the plain ground), not "empty"
                    img.paste(tile(rgb, c, 16), ((i % cm.base_cols) * 16, (i // cm.base_cols) * 16))
    if rgba is not None:
        for layer in cm.overlays:
            for i, c in enumerate(layer):
                if c != 0xFFFF:
                    img.alpha_composite(tile(rgba, c, 8), ((cm.ov_x + i % cm.ov_cols) * 8, (cm.ov_y + i // cm.ov_cols) * 8))
    return img, cm


# --------------------------------------------------------------------------- level2d objects
def _items(node):
    if not isinstance(node, dict) or "$array" not in node:
        return []
    items = node["items"]
    return items if isinstance(items, list) else [items]


def objects(level: str) -> list[dict]:
    from tools.bxon_struct import decode_file

    path = DATA / "level2d" / level / "level2d.bxon"
    if not path.is_file():
        return []
    raw = path.read_bytes()
    root = decode_file(path)["root"]
    out: list[dict] = []
    names, have, glitter = _gimmick_tables()
    for gi, entry in enumerate(_items(root.get("+0x34"))):
        for container in _items(entry.get("+0x04")):
            for key, node in container.items():
                if not isinstance(node, dict) or "$array" not in node:
                    continue
                es, base = node["element_size"], int(node["$array"], 16)
                for i in range(node["count"]):
                    at = base + i * es
                    rec = raw[at:at + es]
                    obj = {"group": gi, "array": key, "index": i, "record_offset": hex(at), "size": es}
                    layout = None
                    if key in ACTOR_ARRAYS and es == 60:
                        ident, x, y, word = struct.unpack_from("<4H", rec, 0x20)
                        obj.update(kind="actor", x=x, y=y, entity_id=ident, facing=word)
                        layout = "actor"
                    elif key == "+0xC0" and es == 36:
                        x, y, w, h = struct.unpack_from("<4H", rec, 0x10)
                        obj.update(kind="trigger", x=x, y=y, w=w, h=h)
                        layout = "trigger"
                    elif key == "+0x50" and es == 28:
                        word = struct.unpack_from("<I", rec, 0x10)[0]
                        obj.update(kind="exit", destination_map=word & 0xFFFF, locator=word >> 16)
                    elif key == "+0x178" and es == 20:
                        x, y = struct.unpack_from("<HH", rec, 4)
                        obj.update(kind="point", x=x, y=y)
                        layout = "point178"
                    elif key == "+0x300" and es == 20:
                        x, y = struct.unpack_from("<HH", rec, 2)
                        obj.update(kind="point", x=x, y=y)
                        layout = "point300"
                    elif key in GIMMICKS and es == GIMMICKS[key][0]:
                        _size, label, t_off, x_off, y_off, d_off = GIMMICKS[key]
                        x, y = struct.unpack_from("<H", rec, x_off)[0], struct.unpack_from("<H", rec, y_off)[0]
                        obj.update(kind="gimmick", label=label, x=x, y=y)
                        fields = {"x": x_off, "y": y_off}
                        if t_off is not None:
                            t = struct.unpack_from("<H", rec, t_off)[0]
                            stem = names[t] if t < len(names) else ""
                            obj["sprite"] = next((stem + v for v in "abcdefghijklmnopqrstuvwxyz" if stem and stem + v in have), "")
                            if key in DOOR_ARRAYS and stem:
                                # the door's look is the high byte of the u16 at +0x18 (the low byte is its gimmick id):
                                # 0 = a, 4 = e (iron cell door), 14 = o (red), 15 = p (blue) ... Proven in the emulator
                                # 2026-11-19: four doors copied into the 2D church drew g0010e, e, o and p for the
                                # bytes 0x04, 0x04, 0x0E, 0x0F; the +0x22 "door style" word did not change the sprite.
                                look = stem + chr(ord("a") + rec[0x19]) if rec[0x19] < 26 else ""
                                if look in have:
                                    obj["sprite"] = look
                                obj["look"] = rec[0x19]
                            obj["sprite_type"] = stem
                            if stem in OBJECT_NAMES:
                                obj["label"] = OBJECT_NAMES[stem]
                        if d_off is not None:
                            obj["drop_row"] = struct.unpack_from("<H", rec, d_off)[0]
                            fields["drop_row"] = d_off
                        if key == "+0x280":
                            obj["spirit_row"] = struct.unpack_from("<H", rec, 0x1C)[0]
                        if key == "+0x168":
                            # the real sparkly spot (GmGlitterPoint2DActor): same glitter row as the level's 3D +0x298
                            # record (235 matches over 130 levels)
                            row = struct.unpack_from("<H", rec, 0x12)[0]
                            obj["glitter_row"] = row
                            item = glitter[row] if row < len(glitter) else 0xFFFF
                            obj["glitter_item"] = None if item == 0xFFFF else item
                        obj["fields"] = fields
                    else:
                        continue
                    if layout:
                        obj["fields"] = FIELDS[layout]
                    out.append(obj)
    return out


def glitter_rows() -> list[int]:
    """fieldcmn/glitter_drop_param: u16 item id per row (0xFFFF = drawn from the area's material table)."""
    raw = (DATA / "fieldcmn" / "glitter_drop_param.bxon").read_bytes()
    count = struct.unpack_from("<I", raw, 0x20)[0]
    return [struct.unpack_from("<H", raw, 0x2C + 4 * i)[0] for i in range(count)]


# --------------------------------------------------------------------------- collision (leveldmap.bxon)
def collision(level: str) -> list[dict]:
    """The walk grids of ``level2d/<level>/leveldmap.bxon`` (LevelDMapBin).

    root -> array of 60-byte entries: u32 cell count +0x00, -> cells +0x04 (2 bytes per cell), -> 12-byte 3D positions
    of the cell corners +0x08 ((w+1)*(h+1) of them: the same grid is what maps a 2D cell to its 3D place), and the
    rectangle x, y, w, h in 8 px cells at +0x30. Cell byte 0 is a flag set: 1 = blocked (b002_105a: the outer walls,
    the divider, the bed and the door gap of the house match the picture exactly); 2..128 are other marks (stairs,
    counters ...; not decoded). Byte 1 is 0xFF or a small number (a zone id: the bed is 4). Levels with bridges or
    several floors have several grids. Not emulator-tested.
    """
    path = DATA / "level2d" / level / "leveldmap.bxon"
    if not path.is_file():
        return []
    d = path.read_bytes()
    out = []
    try:
        count = struct.unpack_from("<I", d, 0x3C)[0]
        base = 0x40 + struct.unpack_from("<I", d, 0x40)[0]
        for e in range(count):
            at = base + 60 * e
            n = struct.unpack_from("<I", d, at)[0]
            x, y, w, h = struct.unpack_from("<4H", d, at + 0x30)
            if not n or w * h != n:
                continue
            ref = at + 4 + struct.unpack_from("<I", d, at + 4)[0]
            cells = d[ref:ref + 2 * n]
            out.append({"index": e, "x": x, "y": y, "w": w, "h": h, "offset": ref,
                        "flags": cells[0::2].hex(), "zones": cells[1::2].hex()})
    except struct.error:
        return []
    return out


def apply_dmap(raw: bytes, cells: list[dict]) -> bytes:
    """Collision edits: [{"offset": file offset of the cell's flag byte, "value": 0..255}]."""
    data = bytearray(raw)
    for c in cells:
        off, value = int(c["offset"]), int(c["value"])
        if not 0 <= off < len(data) or not 0 <= value <= 0xFF:
            raise ValueError(f"collision edit {c} is outside leveldmap.bxon")
        data[off] = value
    return bytes(data)


def add_chips(raw: bytes, chips: list[list[int]]) -> bytes:
    """Append chips ([sheet column, sheet row, attribute, animation, flags]) to the map's ChipInfos.

    A section is {u16 header size, u16 padding after the payload, u32 payload size, name} + payload + padding, and the
    parser walks from one section to the next by those three numbers (Gfx_ParseChipFile). ChipInfos sits inside the
    nested BlockData00 container, so growing it by 6 bytes per chip means: new payload size and padding in its
    header, the sections behind it (Indices, Geography) move, their entries in the nested offset table and the
    nested container's size grow, and so do BlockData00's payload size and the file size in the outer header.
    Checked by re-reading every map with three chips added (`python tools/map2d.py selftest-chips`); not yet tested
    in the emulator.
    """
    if not chips:
        return raw
    d = bytearray(raw)
    count = struct.unpack_from("<H", d, 0xC)[0]
    outer = [struct.unpack_from("<I", d, 0x18 + 4 * i)[0] for i in range(count)]
    block_at = None
    for i, at in enumerate(outer):
        name = bytes(d[at + 8:at + 0x28]).split(b"\0")[0]
        if name == b"BlockData00":  # the block the editor shows; maps with stairs / floors have further blocks
            block_at = at
    if block_at is None:
        raise ValueError("no BlockData section")
    bhs = struct.unpack_from("<H", d, block_at)[0]
    base = block_at + bhs  # nested container
    ncount = struct.unpack_from("<H", d, base + 0xC)[0]
    nested = [struct.unpack_from("<I", d, base + 0x18 + 4 * k)[0] for k in range(ncount)]
    target = None
    for k, rel in enumerate(nested):
        name = bytes(d[base + rel + 8:base + rel + 0x28]).split(b"\0")[0]
        if name == b"ChipInfos":
            target = k
    if target is None:
        raise ValueError("no ChipInfos section")
    at = base + nested[target]
    hs, pad, size = struct.unpack_from("<HHI", d, at)
    add = b"".join(bytes([c[0] & 0xFF, c[1] & 0xFF, 0, c[2] & 0xFF, c[3] & 0xFF, c[4] & 0xFF]) for c in chips)
    new_size = size + len(add)
    new_pad = (-new_size) % 4
    delta = (new_size + new_pad) - (size + pad)
    end = at + hs + size
    d[end:end + pad] = add + bytes(new_pad)
    struct.pack_into("<HHI", d, at, hs, new_pad, new_size)
    for k, rel in enumerate(nested):
        if rel > nested[target]:
            struct.pack_into("<I", d, base + 0x18 + 4 * k, rel + delta)
    struct.pack_into("<I", d, base + 4, struct.unpack_from("<I", d, base + 4)[0] + delta)
    struct.pack_into("<I", d, block_at + 4, struct.unpack_from("<I", d, block_at + 4)[0] + delta)
    for i, o in enumerate(outer):
        if o > block_at:
            struct.pack_into("<I", d, 0x18 + 4 * i, o + delta)
    struct.pack_into("<I", d, 4, struct.unpack_from("<I", d, 4)[0] + delta)
    return bytes(d)


def selftest_chips() -> int:
    """Every map: three chips added must leave the layers and the old chips as they were."""
    bad = 0
    levels = sorted(q.name for q in BG.iterdir() if (q / f"{q.name}.chp").is_file())
    for level in levels:
        raw = (BG / level / f"{level}.chp").read_bytes()
        try:
            before = ChipMap(raw)
            out = add_chips(raw, [[1, 2, 0, 0, 4], [3, 4, 0, 0, 0x18], [0, 0, 7, 0, 2]])
            after = ChipMap(out)
            ok = (after.ids == before.ids and after.chips[:len(before.chips)] == before.chips and len(after.chips) == len(before.chips) + 3
                  and after.layer_starts == before.layer_starts and struct.unpack_from("<I", out, 4)[0] == len(out)
                  and bytes(after.chips[-1]) == bytes([0, 0, 0, 7, 0, 2]) and chp_sections(out).keys() == chp_sections(raw).keys())
            if add_chips(raw, []) != raw:
                ok = False
        except Exception as exc:
            ok = False
            print(f"  {level}: {type(exc).__name__}: {exc}")
        if not ok:
            bad += 1
            print(f"  {level}: wrong after adding chips")
    print(f"{len(levels)} maps, {bad} problem(s)")
    return 1 if bad else 0


def apply_chp(raw: bytes, tiles: list[dict], new_chips: list[list[int]] | None = None) -> bytes:
    """Tile edits: [{"index": position in the CHIP's Indices section (u16 units), "value": chip id or 65535}].
    `new_chips` are appended to ChipInfos first (`add_chips`); the tile writes themselves are same-size. A chip id
    must exist (after the new ones were added)."""
    raw = add_chips(raw, new_chips or [])
    s = chp_sections(raw)
    io, isz, _ = s["BlockData00/Indices"]
    chips = s["BlockData00/ChipInfos"][1] // 6
    data = bytearray(raw)
    for t in tiles:
        i, value = int(t["index"]), int(t["value"])
        if not 0 <= i < isz // 2:
            raise ValueError(f"tile index {i} is outside the map ({isz // 2} cells)")
        if value != 0xFFFF and not 0 <= value < chips:
            raise ValueError(f"chip {value} does not exist ({chips} chips)")
        struct.pack_into("<H", data, io + 2 * i, value)
    return bytes(data)


_TABLES = None


def _gimmick_tables():
    global _TABLES
    if _TABLES is None:
        have = set()
        for base in (MODELS2D, ROOT / "game_assets" / "textures" / "2d_sprites"):
            if base.is_dir():
                have |= {q.stem if q.is_file() else q.name for q in base.iterdir()}
        _TABLES = (sprite_names(), have, glitter_rows())
    return _TABLES


# --------------------------------------------------------------------------- writing (Level Editor "Save to mod")
def apply_level2d(raw: bytes, section: dict) -> tuple[bytes, list[str]]:
    """Apply the editor's 2D changes to a level2d.bxon.

    ``section`` (the ``level2d`` part of ``editor_projects/<level>.json``)::

        {"edits": [{"offset": "0xE1E", "value": 40}],                    u16 writes into retail records
         "ops":   [{"op": "duplicate", "offset": "0xDFC", "set": {"34": 40, "36": 37}},   copy; fields by offset in the record
                   {"op": "delete", "offset": "0x11B8"}]}

    Byte edits go first (a copied array carries them along), then the operations through tools/level_records' ``Level``
    (append-only, nothing existing moves; offsets are those of the retail file). Deleting the only record of an
    array sets the array's count to 0, which the record tool itself refuses. Move, duplicate and this delete are emulator-proven
    (tools/emu/map2d_probe.py, Cobblestone church b011_105a in 2D mode, docs/EDITOR_TODO.md item 12).
    """
    from tools import level_records as lr

    notes: list[str] = []
    data = bytearray(raw)
    for e in section.get("edits") or []:
        off = int(str(e["offset"]), 16)
        if off + 2 > len(data):
            raise ValueError(f"2D edit offset 0x{off:X} is outside the {len(data)}-byte level2d.bxon")
        value = int(e["value"])
        if not 0 <= value <= 0xFFFF:
            raise ValueError(f"2D edit at 0x{off:X}: {value} does not fit a u16")
        struct.pack_into("<H", data, off, value)
    ops = section.get("ops") or []
    if not ops:
        return bytes(data), notes
    level = lr.Level(bytes(data))
    for op in ops:
        off = int(str(op["offset"]), 16)
        if op["op"] == "duplicate":
            element = level.duplicate(off)
            for rel, value in (op.get("set") or {}).items():
                struct.pack_into("<H", level.raw, element + int(rel), int(value) & 0xFFFF)
            level.refresh()
        elif op["op"] == "delete":
            arr, _index = level.unit_for(off)
            if arr.count <= 1:
                struct.pack_into("<I", level.raw, arr.desc, 0)
                notes.append(f"0x{off:X} was the only record of its array: the array count was set to 0 (emulator-proven)")
                level.refresh()
            else:
                level.delete(off)
        else:
            raise ValueError(f"unknown 2D operation {op['op']!r}")
    out = level.finish()
    notes.append(f"{len(ops)} 2D record operation(s); level2d.bxon grew by {len(out) - len(raw):,} bytes")
    return out, notes


# --------------------------------------------------------------------------- sprites
def sprite_names() -> list[str]:
    raw = (DATA / "gamecmn" / "res_model2d.bxon").read_bytes()
    first = raw.find(b"p0001")
    return [m.group().decode() for m in re.finditer(rb"[a-z]{1,4}\d{3,5}[a-z]?", raw[max(first - 4, 0):])]


def npc_sprites() -> dict[str, list[str]]:
    """region index (as in entity_models.json level_regions) -> sprite name per actor id ('' = none)."""
    names = sprite_names()
    have = {p.name for p in MODELS2D.iterdir()} if MODELS2D.is_dir() else set()
    out: dict[str, list[str]] = {}
    for path in sorted((DATA / "param" / "region").glob("r*/npc_list.bxon")):
        number = int(path.parent.name[1:])
        raw = path.read_bytes()
        rows = []
        for k in range((len(raw) - 0x2C) // 26):
            w = struct.unpack_from("<13H", raw, 0x2C + k * 26)
            name = ""
            if w[10] < len(names):
                stem = names[w[10]]
                for variant in ("abcdefghij"[(w[12] & 0xFF) % 10], "a"):
                    if stem + variant in have:
                        name = stem + variant
                        break
            rows.append(name)
        out[str(number - 1)] = rows
    return out


def _export_level(level: str) -> dict:
    result = {"level": level}
    try:
        tex = sheets(level)
        for time in TIMES:
            sheet = tex.get(f"{level}_rgb_{time}")
            if time != "daytime" and (sheet is None or sheet.width <= 16):
                continue
            img, cm = render(level, time, tex)
            img.save(OUT_MAPS / f"{level}_{time}.png")
            meta = {"width": img.width, "height": img.height, "format_name": f"2D map ({time})"}
            (OUT_MAPS / f"{level}_{time}.meta.json").write_text(json.dumps(meta), encoding="utf-8")
            result.setdefault("times", []).append(time)
            result["info"] = cm.info()
            # for the tile editor: the two sheets of this time of day
            out = OUT_TILES / level
            out.mkdir(parents=True, exist_ok=True)
            for kind in ("rgb", "rgba"):
                src = tex.get(f"{level}_{kind}_{time}")
                if src is not None:
                    src.convert("RGBA").save(out / f"{kind}_{time}.png")
        if "info" in result:
            out = OUT_TILES / level
            (out / "indices.bin").write_bytes(struct.pack(f"<{len(cm.ids)}H", *cm.ids))
            meta = {
                "format": "DQXI_CHIPMAP", "level": level, "width": cm.width, "height": cm.height,
                "base": [cm.base_cols, cm.base_rows], "overlay": [cm.ov_x, cm.ov_y, cm.ov_cols, cm.ov_rows],
                "layers": [{"kind": k, "start": a} for k, a in cm.layer_starts],
                # per chip: sheet column, sheet row, attribute, animation, flags (orientation in bits 0x0E, 0x10 = overlay chip)
                "chips": [[c[0], c[1], c[3], c[4], c[5]] for c in cm.chips],
            }
            (out / "chipmap.json").write_text(json.dumps(meta, separators=(",", ":")), encoding="utf-8")
    except Exception as exc:  # reported, the export goes on
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def export(workers: int) -> int:
    OUT_MAPS.mkdir(parents=True, exist_ok=True)
    levels = sorted(p.name for p in BG.iterdir() if (p / f"{p.name}.chp").is_file())
    maps: dict[str, dict] = {}
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for r in pool.map(_export_level, levels, chunksize=4):
            maps[r["level"]] = r
            if "error" in r:
                print(f"  {r['level']}: {r['error']}")
    print(f"rendered {sum('times' in r for r in maps.values())}/{len(levels)} 2D maps (sprite sheets: tools/export_bch_assets.py)")

    table = npc_sprites()
    (SCENES / "sprites2d.json").write_text(json.dumps({"format": "DQXI_SPRITES2D", "npc_sprites": table}), encoding="utf-8")

    # 2D scene per decoded level; b/c/d variants without a 2D map of their own use the a map (like the 3D room)
    written = 0
    for scene_dir in sorted(p for p in SCENES.iterdir() if (p / "scene.json").is_file()):
        level = scene_dir.name
        bg = level if level in maps and "times" in maps[level] else None
        if bg is None:
            for letter in "abcd":
                sib = level[:-1] + letter
                if sib in maps and "times" in maps[sib]:
                    bg = sib
                    break
        objs = objects(level)
        if bg is None and not objs:
            continue
        doc = {
            "format": "DQXI_LEVEL2D",
            "id": level,
            "background": bg,
            "times": maps[bg]["times"] if bg else [],
            "map": maps[bg]["info"] if bg else None,
            "unit": 8,
            "source": f"game_data/packs/level2d/{level}/level2d.bxon",
            "collision": collision(level),
            "objects": objs,
        }
        (scene_dir / "scene2d.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
        written += 1
    print(f"wrote {written} scene2d.json files and game_assets/maps/sprites2d.json")
    return 0


def refresh_objects() -> int:
    """Rewrite only the "objects" of every existing scene2d.json (after a change in objects()), keeping maps and walk grids."""
    n = 0
    for path in sorted(SCENES.glob("*/scene2d.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["objects"] = objects(path.parent.name)
        path.write_text(json.dumps(doc, indent=1), encoding="utf-8")
        n += 1
    print(f"refreshed the objects of {n} scene2d.json files")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("--workers", type=int, default=8)
    r = sub.add_parser("render")
    r.add_argument("level")
    r.add_argument("out")
    r.add_argument("--time", default="daytime", choices=TIMES)
    o = sub.add_parser("objects")
    o.add_argument("level")
    sub.add_parser("selftest-chips")
    sub.add_parser("refresh-objects")
    a = ap.parse_args()
    if a.cmd == "refresh-objects":
        return refresh_objects()
    if a.cmd == "export":
        return export(a.workers)
    if a.cmd == "render":
        img, cm = render(a.level, a.time)
        img.save(a.out)
        print(a.out, cm.info())
        return 0
    if a.cmd == "selftest-chips":
        return selftest_chips()
    if a.cmd == "objects":
        for obj in objects(a.level):
            print(obj)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
