#!/usr/bin/env python3
"""Decode DQXI level packs into an editable scene description.

The game stores a level as:

  level3d/<id>.pack  -> level3d.bxon   (CLevel3DBin: scene/collision data)
  3d/bg/<id>.pack    -> <id>.bch       (environment mesh)
  level2d/<id>.pack  -> level2d.bxon   (2D map/minimap data)

The BXON schema is not stored in the file.  ``bxon_struct`` recovers the object
graph; this tool additionally identifies the fixed-size placement records that
carry a position, scale/rotation and a type/hash.  It writes a stable JSON scene
that an editor can load, and a patch command that writes edited floats back into
the original BXON without changing its size or pointer graph.

Usage:
    python tools/map_tool.py list
    python tools/map_tool.py export --limit 10
    python tools/map_tool.py export --all
    python tools/map_tool.py patch PROJECT.json
"""
from __future__ import annotations

import argparse
import json
import math
import struct
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.bxon_struct import StructDecoder

DATA_DIR = PROJECT_ROOT / "game_data"
OUT_DIR = PROJECT_ROOT / "game_assets" / "maps"


def f32(data: bytes, off: int) -> float:
    return struct.unpack_from("<f", data, off)[0]


def u32(data: bytes, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]


def plausible(v: float) -> bool:
    return math.isfinite(v) and abs(v) < 1e7


_GLITTER: list[int] | None = None


def _glitter_item(row: int) -> int:
    """fieldcmn/glitter_drop_param: u16 item id per 4-byte row (0xFFFF = drawn from the area's material table)."""
    global _GLITTER
    if _GLITTER is None:
        try:
            raw = (DATA_DIR / "packs" / "fieldcmn" / "glitter_drop_param.bxon").read_bytes()
            _GLITTER = [int.from_bytes(raw[0x2C + 4 * i:0x2E + 4 * i], "little") for i in range(u32(raw, 0x20))]
        except OSError:
            _GLITTER = []
    return _GLITTER[row] if row < len(_GLITTER) else 0xFFFF


def collect_records(node, path="root"):
    """Yield (path, record) for every structural record with an offset and size."""
    if isinstance(node, dict):
        if "$offset" in node and "$size" in node:
            yield path, node
        for k, v in node.items():
            if k.startswith("$"):
                continue
            yield from collect_records(v, f"{path}/{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from collect_records(v, f"{path}[{i}]")


def candidate_objects(struct: dict, raw: bytes) -> list[dict]:
    """Extract transform-like records from the structural graph.

    The two recurring shapes are:
      * 68 bytes: position xyz, duplicate xyz, zero block, size xyz, type marker
      * 120 bytes: position xyz, ..., scale xyz, ..., rotation xyz/radians, flags
    Both are exposed with their exact byte offsets so edits are reversible.
    """
    out = []
    for path, rec in collect_records(struct.get("root")):
        size = rec.get("$size")
        off = int(rec["$offset"], 16)
        if size == 100 and "/+0x1F0/items" in path:
            # field actor (NPC or monster): confirmed in the emulator, docs/LEVEL_FORMAT.md
            px, py, pz = (f32(raw, off + 0x20 + i * 4) for i in range(3))
            rx, ry, rz = (f32(raw, off + 0x2C + i * 4) for i in range(3))
            if all(plausible(v) for v in (px, py, pz)):
                if not all(plausible(v) for v in (rx, ry, rz)):
                    rx = ry = rz = 0.0
                entity = u32(raw, off + 0x5C)
                out.append({
                    "kind": "actor",
                    "shape": 100,
                    "path": path,
                    "record_offset": f"0x{off:X}",
                    "position": [px, py, pz],
                    "scale": [1.0, 1.0, 1.0],
                    "rotation": [rx, ry, rz],
                    "field_offsets": {
                        "position": [f"0x{off + 0x20:X}", f"0x{off + 0x24:X}", f"0x{off + 0x28:X}"],
                        "rotation": [f"0x{off + 0x2C:X}", f"0x{off + 0x30:X}", f"0x{off + 0x34:X}"],
                    },
                    "props": [
                        {"name": "entity id", "offset": f"0x{off + 0x5C:X}", "type": "u16", "value": entity & 0xFFFF,
                         "editable": True, "hint": "which character or monster this is; scripts call GetActorID(id)"},
                        {"name": "entity class", "offset": f"0x{off + 0x5E:X}", "type": "u16", "value": entity >> 16,
                         "editable": True, "hint": "0x300 usual, 0x100 / 0x200 variants (unknown meaning)"},
                        {"name": "flags 54", "offset": f"0x{off + 0x54:X}", "type": "u32", "value": u32(raw, off + 0x54),
                         "editable": False, "hint": "unknown"},
                        {"name": "flags 58", "offset": f"0x{off + 0x58:X}", "type": "u32", "value": u32(raw, off + 0x58),
                         "editable": False, "hint": "unknown"},
                        {"name": "key 60", "offset": f"0x{off + 0x60:X}", "type": "u32", "value": u32(raw, off + 0x60),
                         "editable": False, "hint": "unknown"},
                    ],
                })
            continue
        if size == 108 and "/+0x240/items" in path:
            # gimmick (chest / search spot / door ...): docs/GIMMICK_DECOMP.md. +0x64 low u16 = row of fixed_drop_param
            kinds = {0: "item box", 1: "slot machine", 2: "door", 3: "keyed door", 4: "event door", 5: "one-way door", 6: "one-way door", 7: "storage", 8: "breakable"}
            px, py, pz = (f32(raw, off + 0x48 + i * 4) for i in range(3))
            if all(plausible(v) for v in (px, py, pz)):
                kind = raw[off + 0x62]
                out.append({
                    "kind": "gimmick",
                    "shape": 108,
                    "path": path,
                    "record_offset": f"0x{off:X}",
                    "position": [px, py, pz],
                    "scale": [1.0, 1.0, 1.0],
                    "rotation": [0.0, 0.0, 0.0],
                    "field_offsets": {"position": [f"0x{off + 0x48:X}", f"0x{off + 0x4C:X}", f"0x{off + 0x50:X}"]},
                    "props": [
                        {"name": "drop row", "offset": f"0x{off + 0x64:X}", "type": "u16", "value": int.from_bytes(raw[off + 0x64:off + 0x66], "little"),
                         "editable": True, "hint": "row of fieldcmn/fixed_drop_param (item + count the spot gives); 65535 = none / glitter"},
                        {"name": "gimmick id", "offset": f"0x{off + 0x66:X}", "type": "u16", "value": int.from_bytes(raw[off + 0x66:off + 0x68], "little"),
                         "editable": False, "hint": "per-level counter"},
                        {"name": "interaction kind", "offset": f"0x{off + 0x62:X}", "type": "u8", "value": kind,
                         "editable": False, "hint": kinds.get(kind, "script RCommand type (docs/GIMMICK_DECOMP.md)")},
                        {"name": "object type", "offset": f"0x{off + 0x60:X}", "type": "u16", "value": int.from_bytes(raw[off + 0x60:off + 0x62], "little"),
                         "editable": False, "hint": "0x2CF / 0x2D0"},
                    ],
                })
            continue
        if size == 100 and "/+0x230/items" in path:
            # treasure chest: the drop row at +0x2E is the one the level's 2D chest record carries (level2d +0x110;
            # b011_001a 38 / 39 / 683 and d007_001a 11 / 15 / 253 / 254 in both files), position at +0x34
            px, py, pz = (f32(raw, off + 0x34 + i * 4) for i in range(3))
            if all(plausible(v) for v in (px, py, pz)):
                out.append({
                    "kind": "gimmick",
                    "label": "Treasure chest",
                    "shape": 100,
                    "path": path,
                    "record_offset": f"0x{off:X}",
                    "position": [px, py, pz],
                    "scale": [1.0, 1.0, 1.0],
                    "rotation": [0.0, 0.0, 0.0],
                    "field_offsets": {"position": [f"0x{off + 0x34:X}", f"0x{off + 0x38:X}", f"0x{off + 0x3C:X}"]},
                    "props": [
                        {"name": "drop row", "offset": f"0x{off + 0x2E:X}", "type": "u16", "value": int.from_bytes(raw[off + 0x2E:off + 0x30], "little"),
                         "editable": True, "hint": "row of fieldcmn/fixed_drop_param (item + count in the chest); same row as the 2D chest"},
                        {"name": "word 2C", "offset": f"0x{off + 0x2C:X}", "type": "u16", "value": int.from_bytes(raw[off + 0x2C:off + 0x2E], "little"),
                         "editable": False, "hint": "unknown (0x40FF on most chests)"},
                        {"name": "object type", "offset": f"0x{off + 0x30:X}", "type": "u16", "value": int.from_bytes(raw[off + 0x30:off + 0x32], "little"),
                         "editable": False, "hint": "0x2CB = treasure chest"},
                    ],
                })
            continue
        if size == 88 and "/+0x2E0/items" in path:
            # Tockle spot (stray spirit generator). Emulator 2026-11-16: copied into the Heliodor church it is drawn as a coloured Tockle, not as a sparkle; the classes are GmSpiritGenerator* / StraySpirit*, and the ids 0..462 fit fieldcmn/spirit_generator_table (464 rows). It was first taken for a sparkly spot. Real 3D sparkly spots (GmBeeGlitterPoint3DActor / RCommand GlitterPoint) are NOT decoded yet.
            # id at +0x50, equal to the id of the
            # level's 2D record (level2d +0x280; d007_001a 400..408 in both), position at +0x08
            px, py, pz = (f32(raw, off + 0x08 + i * 4) for i in range(3))
            if all(plausible(v) for v in (px, py, pz)):
                out.append({
                    "kind": "gimmick",
                    "label": "Tockle spot",
                    "shape": 88,
                    "path": path,
                    "record_offset": f"0x{off:X}",
                    "position": [px, py, pz],
                    "scale": [1.0, 1.0, 1.0],
                    "rotation": [0.0, 0.0, 0.0],
                    # the spot's position is stored twice: in the record and in its point list (count at +0x00,
                    # pointer at +0x04 -> 16-byte points; one point equal to the record position in all 421 spots).
                    # The game shows the spot at the POINT (emulator 2026-11-16), so both are written.
                    "field_offsets": {"position": [f"0x{off + 0x08:X}", f"0x{off + 0x0C:X}", f"0x{off + 0x10:X}"],
                                      **({"position_shadow": [f"0x{off + 4 + u32(raw, off + 4) + i * 4:X}" for i in range(3)]}
                                         if u32(raw, off) >= 1 and off + 4 + u32(raw, off + 4) + 12 <= len(raw) else {})},
                    "props": [
                        {"name": "spirit row", "offset": f"0x{off + 0x50:X}", "type": "u16", "value": int.from_bytes(raw[off + 0x50:off + 0x52], "little"),
                         "editable": True, "hint": "row of fieldcmn/spirit_generator_table (which Tockle appears here); not decoded further"},
                        {"name": "word 44", "offset": f"0x{off + 0x44:X}", "type": "u32", "value": u32(raw, off + 0x44),
                         "editable": False, "hint": "120 / 180 / 240 in d007_001a's three story groups (unknown)"},
                    ],
                })
            continue
        if size == 104 and "/+0x218/items" in path:
            # roaming symbol (candidate monster, dungeon levels, docs/CUSTOM_ROOM.md): position at +0x20, the word at +0x5C = (u16 type, u16 group)
            px, py, pz = (f32(raw, off + 0x20 + i * 4) for i in range(3))
            if all(plausible(v) for v in (px, py, pz)):
                out.append({
                    "kind": "symbol",
                    "shape": 104,
                    "path": path,
                    "record_offset": f"0x{off:X}",
                    "position": [px, py, pz],
                    "scale": [1.0, 1.0, 1.0],
                    "rotation": [0.0, 0.0, 0.0],
                    "field_offsets": {"position": [f"0x{off + 0x20:X}", f"0x{off + 0x24:X}", f"0x{off + 0x28:X}"]},
                    "props": [
                        {"name": "type", "offset": f"0x{off + 0x5C:X}", "type": "u16", "value": int.from_bytes(raw[off + 0x5C:off + 0x5E], "little"),
                         "editable": False, "hint": "2 on every record seen"},
                        {"name": "group", "offset": f"0x{off + 0x5E:X}", "type": "u16", "value": int.from_bytes(raw[off + 0x5E:off + 0x60], "little"),
                         "editable": True, "hint": "candidate monster / encounter id (0x8F..0xDC in d001_001a); not proven"},
                        {"name": "flags 54", "offset": f"0x{off + 0x54:X}", "type": "u32", "value": u32(raw, off + 0x54),
                         "editable": False, "hint": "0x1010000 / 0x1010001"},
                        {"name": "key 64", "offset": f"0x{off + 0x64:X}", "type": "u32", "value": u32(raw, off + 0x64),
                         "editable": False, "hint": "0x0A...... like the actor key"},
                    ],
                })
            continue
        if size == 24 and "/+0x298/items" in path:
            # sparkly spot (GmGlitterPoint3DActor): position, radius (1.0 in all), u16 row of fieldcmn/glitter_drop_param
            # at +0x10 (the item it gives), u16 gimmick id at +0x12 (1023 = none), key at +0x14. 377 in the game.
            px, py, pz = (f32(raw, off + i * 4) for i in range(3))
            if all(plausible(v) for v in (px, py, pz)):
                row = int.from_bytes(raw[off + 0x10:off + 0x12], "little")
                out.append({
                    "kind": "gimmick",
                    "label": "Sparkly spot",
                    "shape": 24,
                    "path": path,
                    "record_offset": f"0x{off:X}",
                    "position": [px, py, pz],
                    "scale": [1.0, 1.0, 1.0],
                    "rotation": [0.0, 0.0, 0.0],
                    "field_offsets": {"position": [f"0x{off:X}", f"0x{off + 4:X}", f"0x{off + 8:X}"]},
                    "props": [
                        {"name": "glitter row", "offset": f"0x{off + 0x10:X}", "type": "u16", "value": row,
                         "editable": True, "hint": "row of fieldcmn/glitter_drop_param: the item the spot gives (65535 in the table = random materials of the area)"},
                        {"name": "glitter item", "offset": "", "type": "u16", "value": _glitter_item(row),
                         "editable": False, "hint": "item of that row in the game's table (65535 = random materials)"},
                        {"name": "gimmick id", "offset": f"0x{off + 0x12:X}", "type": "u16", "value": int.from_bytes(raw[off + 0x12:off + 0x14], "little"),
                         "editable": False, "hint": "1023 = none"},
                    ],
                })
            continue
        if size == 24 and "/+0x68/items" in path:
            # map-jump table entry: low half of the word at +0x0C = destination map id (row of syscmn/level_map),
            # high half = locator / kind (docs/LEVEL_FORMAT.md, Warps). It has no position of its own.
            if u32(raw, off + 0x08) == 0xFFFFFFFF:
                word = u32(raw, off + 0x0C)
                out.append({
                    "kind": "exit",
                    "shape": 24,
                    "path": path,
                    "record_offset": f"0x{off:X}",
                    "position": [0.0, 0.0, 0.0],
                    "scale": [1.0, 1.0, 1.0],
                    "rotation": [0.0, 0.0, 0.0],
                    "field_offsets": {},
                    "props": [
                        {"name": "destination map", "offset": f"0x{off + 0x0C:X}", "type": "u16", "value": word & 0xFFFF,
                         "editable": True, "hint": "row of syscmn/level_map: the level this exit leads to"},
                        {"name": "locator", "offset": f"0x{off + 0x0E:X}", "type": "u16", "value": word >> 16,
                         "editable": True, "hint": "where the player arrives / exit kind (high half of the word)"},
                        {"name": "word 10", "offset": f"0x{off + 0x10:X}", "type": "u32", "value": u32(raw, off + 0x10),
                         "editable": False, "hint": "unknown (0x30001FF on most exits)"},
                        {"name": "word 14", "offset": f"0x{off + 0x14:X}", "type": "u32", "value": u32(raw, off + 0x14),
                         "editable": False, "hint": "unknown (looks like a hash / id)"},
                    ],
                })
            continue
        if size == 48 and "/+0x1B8/items" in path:
            # door / exit trigger volume (candidate, docs/LEVEL_FORMAT.md, Warps): map id in the low half of +0x28
            tag = int.from_bytes(raw[off + 0x2A:off + 0x2C], "little")  # (`struct` is a parameter here)
            dest = int.from_bytes(raw[off + 0x28:off + 0x2A], "little")
            px, py, pz = (f32(raw, off + 0x10 + i * 4) for i in range(3))
            if tag == 0x4003 and 0x100 <= dest < 0x1000 and all(plausible(v) for v in (px, py, pz)):
                ry = f32(raw, off + 0x20)
                out.append({
                    "kind": "trigger",
                    "shape": 48,
                    "path": path,
                    "record_offset": f"0x{off:X}",
                    "position": [px, py, pz],
                    "scale": [1.0, 1.0, 1.0],
                    "rotation": [0.0, ry if plausible(ry) else 0.0, 0.0],
                    "field_offsets": {
                        "position": [f"0x{off + 0x10:X}", f"0x{off + 0x14:X}", f"0x{off + 0x18:X}"],
                        "rotation": [f"0x{off + 0x1C:X}", f"0x{off + 0x20:X}", f"0x{off + 0x24:X}"],
                    },
                    "props": [
                        {"name": "trigger id", "offset": f"0x{off + 0x28:X}", "type": "u16", "value": dest,
                         "editable": True,
                         "hint": "level-local trigger id (not a map id); see docs/LEVEL_FORMAT.md, Warps"},
                        {"name": "tag", "offset": f"0x{off + 0x2A:X}", "type": "u16", "value": tag,
                         "editable": False, "hint": "0x4003 on every trigger seen"},
                        {"name": "word 08", "offset": f"0x{off + 0x08:X}", "type": "u32", "value": u32(raw, off + 0x08),
                         "editable": False, "hint": "unknown"},
                        {"name": "word 0C", "offset": f"0x{off + 0x0C:X}", "type": "u32", "value": u32(raw, off + 0x0C),
                         "editable": False, "hint": "unknown"},
                        {"name": "word 2C", "offset": f"0x{off + 0x2C:X}", "type": "u32", "value": u32(raw, off + 0x2C),
                         "editable": False, "hint": "unknown (looks like a hash)"},
                    ],
                })
            continue
        if size == 68:
            px, py, pz = (f32(raw, off + i * 4) for i in range(3))
            sx, sy, sz = (f32(raw, off + 0x30 + i * 4) for i in range(3))
            kind = u32(raw, off + 0x3C)
            if all(plausible(v) for v in (px, py, pz, sx, sy, sz)):
                out.append({
                    "kind": "placement",
                    "shape": 68,
                    "path": path,
                    "record_offset": f"0x{off:X}",
                    "position": [px, py, pz],
                    "scale": [sx, sy, sz],
                    "rotation": [0.0, 0.0, 0.0],
                    "type": f"0x{kind:08X}",
                    "field_offsets": {
                        "position": [f"0x{off + 0x00:X}", f"0x{off + 0x04:X}", f"0x{off + 0x08:X}"],
                        "position_shadow": [f"0x{off + 0x0C:X}", f"0x{off + 0x10:X}", f"0x{off + 0x14:X}"],
                        "scale": [f"0x{off + 0x30:X}", f"0x{off + 0x34:X}", f"0x{off + 0x38:X}"],
                    },
                })
        elif size == 120:
            px, py, pz = (f32(raw, off + i * 4) for i in range(3))
            sx, sy, sz = (f32(raw, off + 0x18 + i * 4) for i in range(3))
            rx, ry, rz = (f32(raw, off + 0x60 + i * 4) for i in range(3))
            if all(plausible(v) for v in (px, py, pz, sx, sy, sz)):
                if not all(plausible(v) for v in (rx, ry, rz)):
                    rx = ry = rz = 0.0
                out.append({
                    "kind": "transform",
                    "shape": 120,
                    "path": path,
                    "record_offset": f"0x{off:X}",
                    "position": [px, py, pz],
                    "scale": [sx, sy, sz],
                    "rotation": [rx, ry, rz],
                    "field_offsets": {
                        "position": [f"0x{off + 0x00:X}", f"0x{off + 0x04:X}", f"0x{off + 0x08:X}"],
                        "scale": [f"0x{off + 0x18:X}", f"0x{off + 0x1C:X}", f"0x{off + 0x20:X}"],
                        "rotation": [f"0x{off + 0x60:X}", f"0x{off + 0x64:X}", f"0x{off + 0x68:X}"],
                    },
                })
    # Stable ordering by source offset.
    out.sort(key=lambda x: int(x["record_offset"], 16))
    # chests and sparkly spots were added later: they get ids of their own so the numbered ids of the other
    # records (which saved editor projects refer to) stay what they were
    i = 0
    for obj in out:
        if obj.get("label") in ("Treasure chest", "Tockle spot", "Sparkly spot"):
            obj["id"] = f"g_{obj['record_offset']}"
        else:
            obj["id"] = f"{i:03d}_{obj['record_offset']}"
            i += 1
    return out


def map_ids() -> list[str]:
    root = DATA_DIR / "packs" / "level3d"
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir() and (p / "level3d.bxon").is_file())


def find_background(map_id: str) -> str | None:
    p = DATA_DIR / "packs" / "3d" / "bg" / map_id / f"{map_id}.bch"
    if p.is_file():
        return str(p.relative_to(PROJECT_ROOT))
    # Campaign/cutscene variants are separate; the base map is the editor target.
    matches = sorted((DATA_DIR / "packs" / "3d" / "bg").glob(f"{map_id}*/*.bch"))
    return str(matches[0].relative_to(PROJECT_ROOT)) if matches else None


def decode_map(map_id: str) -> dict:
    src = DATA_DIR / "packs" / "level3d" / map_id / "level3d.bxon"
    raw = src.read_bytes()
    struct_data = StructDecoder(raw).decode()
    scene = {
        "format": "DQXI_LEVEL3D",
        "id": map_id,
        "source": str(src.relative_to(PROJECT_ROOT)),
        "background_bch": find_background(map_id),
        "level2d_source": str((DATA_DIR / "packs" / "level2d" / map_id / "level2d.bxon").relative_to(PROJECT_ROOT))
        if (DATA_DIR / "packs" / "level2d" / map_id / "level2d.bxon").is_file() else None,
        "size": len(raw),
        "objects": candidate_objects(struct_data, raw),
        "structure": struct_data,
    }
    return scene


def export_maps(limit: int | None, only: str | None) -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ids = map_ids()
    if only:
        ids = [i for i in ids if i == only]
    if limit:
        ids = ids[:limit]
    print(f"Decoding {len(ids)} level packs into {OUT_DIR}...")
    rows = []
    started = time.time()
    for i, map_id in enumerate(ids, 1):
        try:
            scene = decode_map(map_id)
            target = OUT_DIR / map_id
            target.mkdir(parents=True, exist_ok=True)
            structure = scene.pop("structure")
            (target / "scene.json").write_text(json.dumps(scene, indent=2, ensure_ascii=False), encoding="utf-8")
            (target / "structure.json").write_text(json.dumps(structure, indent=2), encoding="utf-8")
            # Keep the exact source BXONs next to the editable scene so a map is
            # self-contained: 3D placements, 2D map, and the dense map grid.
            source_bxon = DATA_DIR / "packs" / "level3d" / map_id / "level3d.bxon"
            if source_bxon.is_file():
                (target / "level3d.source.bxon").write_bytes(source_bxon.read_bytes())
            for member in ("level2d.bxon", "leveldmap.bxon"):
                p = DATA_DIR / "packs" / "level2d" / map_id / member
                if p.is_file():
                    (target / member).write_bytes(p.read_bytes())
            rows.append({"map": map_id, "objects": len(scene["objects"]), "background": scene["background_bch"]})
        except Exception as exc:
            print(f"  [ERROR] {map_id}: {exc}")
        if i % 50 == 0 or i == len(ids):
            print(f"  {i}/{len(ids)} maps ({i / max(time.time() - started, 1e-6):.1f}/s)")
    (OUT_DIR / "maps_summary.json").write_text(json.dumps({
        "maps": len(rows),
        "objects": sum(r["objects"] for r in rows),
        "rows": rows,
    }, indent=2), encoding="utf-8")
    print(f"Exported {len(rows)} maps with {sum(r['objects'] for r in rows)} candidate objects")
    return 0


def export_donors() -> int:
    """`game_assets/maps/donors.json`: one record of every kind of object, each from the first level that has it and
    whose record sits directly in a layer container. The Level Editor's Add menu copies such a record into a level
    that has none of the kind (tools/level_records.py `import`)."""
    from tools import level_records

    def title(obj: dict) -> str | None:
        props = {p["name"]: p["value"] for p in obj.get("props", [])}
        if obj["kind"] == "gimmick":
            if obj.get("label"):
                return obj["label"]
            return {0: "Pot / search spot", 1: "Slot machine", 2: "Door", 3: "Keyed door", 4: "Event door",
                    5: "One-way door (open side)", 6: "One-way door (closed side)"}.get(props.get("interaction kind"))
        return {"actor": "Character (NPC)", "trigger": "Trigger", "symbol": "Roaming monster (symbol)"}.get(obj["kind"])

    wanted = ["Character (NPC)", "Treasure chest", "Pot / search spot", "Sparkly spot", "Tockle spot", "Door", "Keyed door", "Event door",
              "One-way door (open side)", "One-way door (closed side)", "Slot machine", "Trigger", "Roaming monster (symbol)"]
    found: dict[str, dict] = {}
    for map_id in map_ids():
        if len(found) == len(wanted):
            break
        scene_path = OUT_DIR / map_id / "scene.json"
        if not scene_path.is_file():
            continue
        scene = json.loads(scene_path.read_text(encoding="utf-8"))
        level = None
        for obj in scene.get("objects", []):
            name = title(obj)
            if name is None or name in found or name not in wanted:
                continue
            if level is None:
                level = level_records.Level((DATA_DIR / "packs" / "level3d" / map_id / "level3d.bxon").read_bytes())
            try:
                arr, _ = level.unit_for(int(obj["record_offset"], 16))
            except level_records.RecordError:
                continue
            if arr.parent is None or arr.parent.esize <= level_records.MAX_WRAPPER * 2:
                continue
            found[name] = {"title": name, "level": map_id, "object": obj}
    out = [found[n] for n in wanted if n in found]
    (OUT_DIR / "donors.json").write_text(json.dumps({"format": "DQXI_DONORS", "donors": out}, ensure_ascii=False), encoding="utf-8")
    print(f"{len(out)} kinds of object -> {OUT_DIR / 'donors.json'}: " + ", ".join(f"{d['title']} ({d['level']})" for d in out))
    return 0


def write_edit(raw: bytearray, off: int, edit: dict) -> None:
    """One edit of a project file: a float by default, or ``"type"``: u8 / u16 / u32 / f32."""
    kind = edit.get("type", "f32")
    value = edit["value"]
    if kind == "f32":
        struct.pack_into("<f", raw, off, float(value))
    elif kind in ("u8", "u16", "u32"):
        size = {"u8": 1, "u16": 2, "u32": 4}[kind]
        number = int(value)
        if not 0 <= number < (1 << (8 * size)):
            raise ValueError(f"offset 0x{off:X}: {number} does not fit {kind}")
        raw[off:off + size] = number.to_bytes(size, "little")
    else:
        raise ValueError(f"unknown edit type {kind!r}")


def patch_project(project_path: Path) -> int:
    project = json.loads(project_path.read_text(encoding="utf-8"))
    map_id = project["map"]
    src = DATA_DIR / "packs" / "level3d" / map_id / "level3d.bxon"
    raw = bytearray(src.read_bytes())
    edits = project.get("edits", [])
    for edit in edits:
        off = int(edit["offset"], 16)
        write_edit(raw, off, edit)
    data = bytes(raw)
    ops = project.get("ops") or []
    if ops:
        from tools import level_records

        data, _ = level_records.apply_ops(data, ops)
    out = OUT_DIR / map_id / "level3d.patched.bxon"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    print(f"Wrote {out} ({len(edits)} float edits, {len(ops)} record ops, size unchanged={len(data) == src.stat().st_size})")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    p_list = sub.add_parser("list")
    p_exp = sub.add_parser("export")
    p_exp.add_argument("--limit", type=int)
    p_exp.add_argument("--only")
    p_exp.add_argument("--all", action="store_true")
    p_patch = sub.add_parser("patch")
    sub.add_parser("donors")
    p_patch.add_argument("project", type=Path)
    args = ap.parse_args()
    if args.command == "list":
        for map_id in map_ids():
            print(map_id)
        return 0
    if args.command == "donors":
        return export_donors()
    if args.command == "export":
        return export_maps(args.limit, args.only)
    if args.command == "patch":
        return patch_project(args.project)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
