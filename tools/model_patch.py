#!/usr/bin/env python3
"""Apply edited OBJ vertex positions or triangle indices back into an original BCH.

This is a **same-size** patch. It keeps the BCH command stream, materials, textures,
normals, UVs and every buffer offset intact. Position edits replace the three floats
at each vertex; index edits replace the triangle list, provided the edited OBJ keeps
the original index count (and u8 indices stay below 255).

Workflow:
  1. Export the model to OBJ with `tools/model_tool.py convert`.
  2. Edit positions/topology in Blender/any OBJ editor, keeping counts/order.
  3. Run this tool with `--indices` for topology or without it for positions.
  4. Rebuild the PACK/ROM with the patched BCH.

Usage:
    python tools/model_patch.py ORIGINAL.bch EDITED.obj --out patched.bch
    python tools/model_patch.py ORIGINAL.bch EDITED.obj --indices --out patched.bch
    python tools/model_patch.py ORIGINAL.bch --dump-json positions.json
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.model_tool import BchParser


def obj_positions(path: Path) -> list[tuple[float, float, float]]:
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("v "):
            parts = line.split()
            if len(parts) >= 4:
                out.append((float(parts[1]), float(parts[2]), float(parts[3])))
    return out


def obj_indices(path: Path) -> list[list[int]]:
    groups: list[list[int]] = []
    current: list[int] | None = None
    v_count = 0
    v_start = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("v "):
            v_count += 1
        elif line.startswith("o ") or line.startswith("g "):
            current = []
            groups.append(current)
            v_start = v_count
        elif line.startswith("f "):
            if current is None:
                current = []
                groups.append(current)
                v_start = 0
            idx = []
            for token in line.split()[1:]:
                first = token.split("/")[0]
                if not first:
                    continue
                i = int(first)
                idx.append(i - 1 - v_start if i > 0 else v_count + i - v_start)
            for k in range(1, len(idx) - 1):
                current.extend((idx[0], idx[k], idx[k + 1]))
    return groups


def _geometry_key(mesh) -> tuple:
    return (
        tuple(round(c, 4) for p in mesh.positions for c in p),
        tuple(mesh.indices),
    )


def unplace(m: list[float], p: tuple[float, float, float]) -> tuple[float, float, float]:
    """Inverse of bone placement: model-space point -> bone-local point.

    `m` is a row-vector affine matrix (p' = p * R + t) as stored by
    BchParser._apply_bone_placement.
    """
    a, b, c, d, e, f, g, h, i = m[:9]
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    if abs(det) < 1e-12:
        raise ValueError("bone matrix is not invertible")
    inv = (
        (e * i - f * h) / det, (c * h - b * i) / det, (b * f - c * e) / det,
        (f * g - d * i) / det, (a * i - c * g) / det, (c * d - a * f) / det,
        (d * h - e * g) / det, (b * g - a * h) / det, (a * e - b * d) / det,
    )
    x, y, z = p[0] - m[9], p[1] - m[10], p[2] - m[11]
    return (
        x * inv[0] + y * inv[3] + z * inv[6],
        x * inv[1] + y * inv[4] + z * inv[7],
        x * inv[2] + y * inv[5] + z * inv[8],
    )


def apply_positions(
    bch: bytes, positions: list[tuple[float, float, float]], source_path: Path | None = None
) -> tuple[bytes, dict]:
    """Writes edited model-space positions back into the BCH.

    Pass the BCH path as `source_path` when the OBJ came from the normal export,
    so bone-placed draws (faces, props on bones) are mapped back to bone space.
    """
    parser = BchParser(bch, source_path=source_path)
    models = parser.parse_models("patched", dedupe=False)
    meshes = [m for model in models for m in model.meshes if m.positions and m.indices]
    groups: dict[tuple, list] = {}
    order: list[tuple] = []
    for mesh in meshes:
        key = (
            tuple(round(c, 4) for p in mesh.positions for c in p),
            tuple(mesh.indices),
        )
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(mesh)
    total = sum(len(groups[key][0].positions) for key in order)
    if total != len(positions):
        raise ValueError(f"vertex count mismatch: BCH has {total}, OBJ has {len(positions)}")
    out = bytearray(bch)
    cursor = 0
    patched = 0
    for key in order:
        group = groups[key]
        source = group[0].positions
        count = len(source)
        block = positions[cursor:cursor + count]
        cursor += count
        for mesh in group:
            if mesh.vbo_abs <= 0 or mesh.stride < 12:
                raise ValueError("model has no writable VBO metadata")
            for i, (x, y, z) in enumerate(block):
                ox, oy, oz = source[i]
                patched += 1
                if (x, y, z) == (ox, oy, oz):
                    continue  # untouched vertex: keep the original bytes
                mx, my, mz = mesh.positions[i]
                target = (mx + (x - ox), my + (y - oy), mz + (z - oz))
                if mesh.placement is not None:
                    target = unplace(mesh.placement[i], target)
                off = mesh.vbo_abs + i * mesh.stride
                if off + 12 > len(out):
                    raise ValueError(f"vertex {patched} lies outside the BCH")
                struct.pack_into("<3f", out, off, *target)
    return bytes(out), {"vertices": patched, "meshes": len(meshes)}


def apply_indices(bch: bytes, groups: list[list[int]], source_path: Path | None = None) -> tuple[bytes, dict]:
    parser = BchParser(bch, source_path=source_path)
    models = parser.parse_models("patched", dedupe=False)
    meshes = [m for model in models for m in model.meshes if m.positions and m.indices]
    unique: dict[tuple, list] = {}
    order: list[tuple] = []
    for mesh in meshes:
        key = _geometry_key(mesh)
        if key not in unique:
            unique[key] = []
            order.append(key)
        unique[key].append(mesh)
    if len(groups) != len(order):
        raise ValueError(f"mesh count mismatch: BCH has {len(order)} unique meshes, OBJ has {len(groups)}")
    out = bytearray(bch)
    patched = 0
    for key, block in zip(order, groups):
        source = unique[key][0]
        if len(block) != len(source.indices):
            raise ValueError(
                f"index count mismatch for {source.name}: BCH {len(source.indices)}, OBJ {len(block)}"
            )
        for mesh in unique[key]:
            if mesh.ibo_abs <= 0:
                raise ValueError("model has no writable IBO metadata")
            fmt = "<B" if mesh.index_size == 1 else "<H"
            limit = 255 if mesh.index_size == 1 else 65535
            for i, value in enumerate(block):
                if value < 0 or value > limit:
                    raise ValueError(f"index {value} does not fit in {mesh.index_size * 8} bits")
                off = mesh.ibo_abs + i * mesh.index_size
                if off + mesh.index_size > len(out):
                    raise ValueError("index lies outside the BCH")
                struct.pack_into(fmt, out, off, value)
                patched += 1
    return bytes(out), {"indices": patched, "meshes": len(meshes)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("bch", type=Path)
    ap.add_argument("obj", type=Path, nargs="?")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--dump-json", type=Path)
    ap.add_argument("--indices", action="store_true", help="patch triangle indices instead of positions")
    args = ap.parse_args()
    raw = args.bch.read_bytes()
    if args.dump_json:
        parser = BchParser(raw, source_path=args.bch)
        models = parser.parse_models(args.bch.stem)
        data = [
            {
                "mesh": m.name,
                "vbo_abs": m.vbo_abs,
                "stride": m.stride,
                "positions": m.positions,
            }
            for model in models
            for m in model.meshes
        ]
        args.dump_json.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"Wrote {args.dump_json} ({sum(len(m['positions']) for m in data)} vertices)")
        return 0
    if not args.obj or not args.out:
        ap.error("OBJ and --out are required unless --dump-json is used")
    if args.indices:
        patched, report = apply_indices(raw, obj_indices(args.obj), source_path=args.bch)
        detail = f"{report['indices']} indices in {report['meshes']} meshes"
    else:
        patched, report = apply_positions(raw, obj_positions(args.obj), source_path=args.bch)
        detail = f"{report['vertices']} vertices in {report['meshes']} meshes"
    if len(patched) != len(raw):
        raise ValueError("patched BCH changed size")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(patched)
    print(f"Wrote {args.out}: {detail} (same size)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
