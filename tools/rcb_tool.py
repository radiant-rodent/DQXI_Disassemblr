#!/usr/bin/env python3
"""Read the collision files of a level (``3d/bg/<level>/<level>_chit.rcb`` etc., magic ``rcbl``).

Layout found so far (docs/COLLISION.md): 0x54-byte header (+0x18 bounding box, +0x30 section count, +0x34 u16 name count, +0x48 string
table), then sections whose 16-byte header ``ffff00NN  00040002  vertex_offset  triangle_offset`` points at a vertex array (12 bytes per
vertex: x y z floats) and a triangle array (8 bytes per triangle: u16 a, b, c, attribute). Names of the shapes are in the string table.

    python -m tools.rcb_tool <file.rcb> [out.obj]
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path


def bg_name(level: str) -> str:
    """The background pack a level uses: its own, or the ``a`` variant (``b002_105c`` uses ``b002_105a``)."""
    from pathlib import Path as _P

    bg = _P(__file__).resolve().parents[1] / "game_data" / "packs" / "3d" / "bg"
    return level if (bg / level).is_dir() else level[:-1] + "a"


def names(d: bytes) -> list[str]:
    st = struct.unpack_from("<I", d, 0x48)[0]
    n = struct.unpack_from("<H", d, 0x36)[0]
    out = []
    for o in struct.unpack_from(f"<{n}I", d, st):
        out.append(d[o:d.index(b"\0", o)].decode("latin1"))
    return out


def sections(d: bytes) -> list[dict]:
    """One 96-byte record per shape from 0x54: ``ffff00NN`` (NN = name index), ``(vertex count << 16) | triangle count``, vertex offset,
    triangle offset, then 80 bytes of per-shape data (bounding values, not decoded)."""
    count = struct.unpack_from("<I", d, 0x30)[0]
    label = names(d)
    out = []
    for i in range(count):
        o = 0x54 + 96 * i
        a, b, va, ia = struct.unpack_from("<4I", d, o)
        nv, nt = b >> 16, b & 0xFFFF
        verts = [struct.unpack_from("<3f", d, va + 12 * k) for k in range(nv)]
        tris = [struct.unpack_from("<4H", d, ia + 8 * k) for k in range(nt)]
        idx = a & 0xFFFF
        out.append({"header": o, "code": idx, "name": label[idx] if idx < len(label) else "", "vertices": verts,
                    "triangles": tris, "extra": d[o + 16:o + 96]})
    return out


def to_obj(secs: list[dict]) -> str:
    lines, base = [], 1
    for n, s in enumerate(secs):
        lines.append(f"o {n}_{s['name'] or s['code']}")
        lines += [f"v {x:.4f} {y:.4f} {z:.4f}" for x, y, z in s["vertices"]]
        for a, b, c, _attr in s["triangles"]:
            if max(a, b, c) < len(s["vertices"]):
                lines.append(f"f {a + base} {b + base} {c + base}")
        base += len(s["vertices"])
    return "\n".join(lines) + "\n"


def translate_shape(data: bytearray, index: int, dx: float = 0.0, dy: float = 0.0, dz: float = 0.0) -> None:
    """Move one collision shape: its vertices and its stored bounds (sphere centre, box min/max, oriented-box centre).

    The bounds matter: the game culls a shape by them, so a moved wall whose old bounds stay behind collides nowhere
    (proven in the emulator, docs/COLLISION.md). Layout of the 80 per-shape bytes after the 16-byte header, as floats:
    0-2 sphere centre, 3 radius, 4-6 box min, 7-9 box max, 10-13 orientation, 14-16 box centre, 17-19 half extents.
    """
    sec = sections(bytes(data))[index]
    va = struct.unpack_from("<I", data, sec["header"] + 8)[0]
    delta = (dx, dy, dz)
    for k in range(len(sec["vertices"])):
        for axis in range(3):
            o = va + 12 * k + 4 * axis
            struct.pack_into("<f", data, o, struct.unpack_from("<f", data, o)[0] + delta[axis])
    base = sec["header"] + 16
    for first in (0, 4, 7, 14):
        for axis in range(3):
            o = base + 4 * (first + axis)
            struct.pack_into("<f", data, o, struct.unpack_from("<f", data, o)[0] + delta[axis])


def drop_shape(data: bytearray, index: int) -> None:
    """Remove one collision shape by setting its triangle count to 0 (emulator-proven: the wall stops blocking, other shapes keep working)."""
    sec = sections(bytes(data))[index]
    o = sec["header"] + 4
    struct.pack_into("<I", data, o, struct.unpack_from("<I", data, o)[0] & 0xFFFF0000)


def add_mesh(data: bytes, verts: list, tris: list, name_index: int = 0, attribute: int = 0) -> bytes:
    """Return a new file with one collision shape built from a triangle list (the file grows; see add_box for what moves)."""
    count = struct.unpack_from("<I", data, 0x30)[0]
    names_n = struct.unpack_from("<H", data, 0x36)[0]
    table = struct.unpack_from("<I", data, 0x48)[0]
    first_data = 0x54 + 96 * count
    new_data = bytearray()
    for v in verts:
        new_data += struct.pack("<3f", *v)
    tri_off_rel = len(new_data)
    for a, b, c in tris:
        new_data += struct.pack("<4H", a, b, c, attribute)
    new_data += bytes((-len(new_data)) % 4)
    added = 96 + len(new_data)
    out = bytearray(data[:0x54])
    for i in range(count):
        rec = bytearray(data[0x54 + 96 * i:0x54 + 96 * (i + 1)])
        va, ia = struct.unpack_from("<2I", rec, 8)
        struct.pack_into("<2I", rec, 8, va + 96, ia + 96)
        out += rec
    lo = tuple(min(v[i] for v in verts) for i in range(3))
    hi = tuple(max(v[i] for v in verts) for i in range(3))
    centre = tuple((lo[i] + hi[i]) / 2 for i in range(3))
    half = tuple((hi[i] - lo[i]) / 2 for i in range(3))
    radius = sum(h * h for h in half) ** 0.5
    new_va = table + 96
    rec = struct.pack("<4I", 0xFFFF0000 | name_index, (len(verts) << 16) | len(tris), new_va, new_va + tri_off_rel)
    rec += struct.pack("<20f", *centre, radius, *lo, *hi, 0.0, 0.0, 0.0, 1.0, *centre, *half)
    out += rec
    out += data[first_data:table]
    out += new_data
    tail = bytearray(data[table:])
    for n in range(names_n):
        struct.pack_into("<I", tail, 4 * n, struct.unpack_from("<I", tail, 4 * n)[0] + added)
    out += tail
    struct.pack_into("<I", out, 0x04, len(out))
    struct.pack_into("<I", out, 0x30, count + 1)
    struct.pack_into("<2I", out, 0x48, table + added, table + added)
    box = list(struct.unpack_from("<6f", out, 0x18))
    for i in range(3):
        box[i] = min(box[i], lo[i])
        box[3 + i] = max(box[3 + i], hi[i])
    struct.pack_into("<6f", out, 0x18, *box)
    return bytes(out)


def add_box(data: bytes, lo: tuple, hi: tuple, name_index: int = 0, attribute: int = 0) -> bytes:
    """One axis-aligned collision box (12 triangles); emulator-proven (docs/COLLISION.md)."""
    verts = [(x, y, z) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
    tris = [(0, 1, 2), (1, 3, 2), (4, 6, 5), (5, 6, 7), (0, 4, 1), (1, 4, 5), (2, 3, 6), (3, 7, 6), (0, 2, 4), (2, 6, 4), (1, 5, 3), (3, 5, 7)]
    return add_mesh(data, verts, tris, name_index, attribute)


def from_obj(data: bytes, obj, drop_existing: bool = True) -> bytes:
    """Replace a level's collision with the geometry of an OBJ (every face becomes solid); the old shapes are emptied first."""
    from tools.model_import import read_obj

    from pathlib import Path as _P
    verts, _uvs, _normals, tris = read_obj(_P(obj))
    out = bytearray(data)
    if drop_existing:
        for i in range(len(sections(bytes(out)))):
            drop_shape(out, i)
    return add_mesh(bytes(out), verts, [tuple(c[0] for c in t) for t in tris])


def main() -> int:
    path = Path(sys.argv[1])
    d = path.read_bytes()
    secs = sections(d)
    print(f"{path.name}: {len(secs)} sections, {sum(len(s['vertices']) for s in secs)} vertices, {sum(len(s['triangles']) for s in secs)} triangles")
    xs = [v for s in secs for v in s["vertices"]]
    if xs:
        print("extent", [round(min(v[i] for v in xs), 2) for i in range(3)], [round(max(v[i] for v in xs), 2) for i in range(3)])
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(to_obj(secs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
