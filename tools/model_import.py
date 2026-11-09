#!/usr/bin/env python3
"""Import an OBJ mesh into a retail BCH by replacing one draw call's geometry (docs/MODEL_IMPORT.md).

The new vertices keep the draw's vertex layout: each OBJ position is written as three floats at the start of a vertex record whose
remaining attributes (normal, UV, colour, ...) are copied from the **nearest original vertex** of that draw, so the draw keeps its material
and texture and the result stays in the format the engine expects. Triangles come from the OBJ faces (polygons are fanned). Positions must
be in the same model space as the exported OBJ of the BCH.

    python -m tools.model_import model.bch room.obj --draw 0 --out new.bch
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.bch_writer import grow_draw
from tools.model_tool import BchParser


def read_obj(path: Path, group: str | None = None):
    """Positions, texture coordinates, normals and triangles (each corner is a (v, vt, vn) index triple, -1 when absent)."""
    verts, uvs, normals, tris = [], [], [], []
    current = ""
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "v" and len(parts) >= 4:
            verts.append((float(parts[1]), float(parts[2]), float(parts[3])))
        elif parts[0] == "vt" and len(parts) >= 3:
            uvs.append((float(parts[1]), float(parts[2])))
        elif parts[0] == "vn" and len(parts) >= 4:
            normals.append((float(parts[1]), float(parts[2]), float(parts[3])))
        elif parts[0] in ("o", "g") and len(parts) >= 2:
            current = parts[1]
        elif parts[0] == "f" and len(parts) >= 4 and (group is None or current == group):
            corners = []
            for tok in parts[1:]:
                f = tok.split("/")

                def idx(text, count):
                    if not text:
                        return -1
                    i = int(text)
                    return i - 1 if i > 0 else count + i

                corners.append((idx(f[0], len(verts)), idx(f[1] if len(f) > 1 else "", len(uvs)), idx(f[2] if len(f) > 2 else "", len(normals))))
            for k in range(1, len(corners) - 1):
                tris.append((corners[0], corners[k], corners[k + 1]))
    return verts, uvs, normals, tris


def encode(rec: bytearray, attr: dict, values: tuple) -> None:
    """Write one attribute (floats, or scaled shorts / bytes, as the draw stores it) into a vertex record."""
    fmt, elems, scale, off = attr["format"], attr["elements"], attr["scale"] or 1.0, attr["offset"]
    for e in range(elems):
        v = values[e] if e < len(values) else 0.0
        if fmt == 3:
            struct.pack_into("<f", rec, off + 4 * e, v)
        elif fmt == 2:
            struct.pack_into("<h", rec, off + 2 * e, max(-32768, min(32767, round(v / scale))))
        elif fmt == 1:
            rec[off + e] = max(0, min(255, round(v / scale)))
        else:
            struct.pack_into("<b", rec, off + e, max(-128, min(127, round(v / scale))))


def import_obj(bch: bytes, draw: int, obj: Path, source: Path | None = None, group: str | None = None) -> tuple[bytes, dict]:
    verts, uvs, normals, tris = read_obj(obj, group)
    if not verts or not tris:
        raise ValueError("the OBJ has no vertices or faces")
    parser = BchParser(bch, source_path=source)
    meshes = [m for model in parser.parse_models("import", dedupe=False) for m in model.meshes if m.positions and m.indices]
    mesh = meshes[draw]
    stride = mesh.stride
    original = [bch[mesh.vbo_abs + i * stride: mesh.vbo_abs + (i + 1) * stride] for i in range(mesh.vertex_count)]
    layout = {a["name"]: a for a in mesh.layout}
    # one vertex per distinct (position, uv, normal) corner
    table: dict[tuple, int] = {}
    out = bytearray()
    indices: list[int] = []
    for tri in tris:
        for corner in tri:
            if corner not in table:
                x, y, z = verts[corner[0]]
                best, best_d = 0, 1e30
                for j, (ox, oy, oz) in enumerate(mesh.positions):
                    d = (ox - x) ** 2 + (oy - y) ** 2 + (oz - z) ** 2
                    if d < best_d:
                        best, best_d = j, d
                rec = bytearray(original[best])
                struct.pack_into("<3f", rec, 0, x, y, z)
                if corner[1] >= 0 and 4 in layout:
                    encode(rec, layout[4], uvs[corner[1]])
                if corner[2] >= 0 and 1 in layout:
                    nl = layout[1]
                    nv = normals[corner[2]]
                    # signed-byte normals store a unit vector as n * 127 (the uniform that would say so is not recovered, scale reads 1.0)
                    encode(rec, nl, tuple(c * 127 for c in nv) if nl["format"] == 0 and nl["scale"] == 1.0 else nv)
                table[corner] = len(table)
                out += rec
            indices.append(table[corner])
    if len(table) > 65535:
        raise ValueError("a draw can address at most 65,535 vertices (16-bit indices)")
    info = {"vertices": len(table), "triangles": len(tris), "stride": stride, "uv": 4 in layout and bool(uvs), "normals": 1 in layout and bool(normals)}
    return grow_draw(bch, draw, bytes(out), indices), info


def groups(obj: Path) -> list[str]:
    names = []
    for line in obj.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] in ("o", "g") and parts[1] not in names:
            names.append(parts[1])
    return names


def import_scene(bch: bytes, obj: Path, source: Path | None = None) -> tuple[bytes, list[dict]]:
    """Replace several draws at once: every ``o draw<N>`` (or ``o <N>_name``) group of the OBJ replaces draw N."""
    import re

    out, infos = bch, []
    for name in groups(obj):
        m = re.match(r"(?:draw)?(\d+)", name)
        if not m:
            continue
        out, info = import_obj(out, int(m.group(1)), obj, source, group=name)
        infos.append(dict(info, draw=int(m.group(1)), group=name))
    if not infos:
        raise ValueError("no object group named draw<N> / <N>_name in the OBJ")
    return out, infos


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("bch", type=Path)
    ap.add_argument("obj", type=Path)
    ap.add_argument("--draw", type=int, default=None, help="replace this draw with the whole OBJ; omit to map `o draw<N>` groups to draws")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.draw is None:
        data, info = import_scene(a.bch.read_bytes(), a.obj, a.bch)
    else:
        data, info = import_obj(a.bch.read_bytes(), a.draw, a.obj, a.bch)
    a.out.write_bytes(data)
    print(f"wrote {a.out} ({len(data):,} bytes): {info}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
