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
    for i, obj in enumerate(out):
        obj["id"] = f"{i:03d}_{obj['record_offset']}"
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


def patch_project(project_path: Path) -> int:
    project = json.loads(project_path.read_text(encoding="utf-8"))
    map_id = project["map"]
    src = DATA_DIR / "packs" / "level3d" / map_id / "level3d.bxon"
    raw = bytearray(src.read_bytes())
    edits = project.get("edits", [])
    for edit in edits:
        off = int(edit["offset"], 16)
        value = float(edit["value"])
        struct.pack_into("<f", raw, off, value)
    out = OUT_DIR / map_id / "level3d.patched.bxon"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(bytes(raw))
    print(f"Wrote {out} ({len(edits)} float edits, size unchanged={len(raw) == src.stat().st_size})")
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
    p_patch.add_argument("project", type=Path)
    args = ap.parse_args()
    if args.command == "list":
        for map_id in map_ids():
            print(map_id)
        return 0
    if args.command == "export":
        return export_maps(args.limit, args.only)
    if args.command == "patch":
        return patch_project(args.project)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
