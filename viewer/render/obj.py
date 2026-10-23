"""Wavefront OBJ / MTL loading."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class Mesh:
    name: str
    verts: np.ndarray                 # (N, 3) float32
    faces: np.ndarray                 # (M, 3) int32
    normals: np.ndarray | None = None  # (N, 3) float32, optional
    color: tuple[float, float, float] = (0.78, 0.78, 0.80)
    material: str = "default_mat"
    parts: int = 1                    # number of "o"/"g" mesh groups in the source
    _center: np.ndarray | None = field(default=None, repr=False)
    _size: np.ndarray | None = field(default=None, repr=False)
    _face_normals: np.ndarray | None = field(default=None, repr=False)
    _finite: np.ndarray | None = field(default=None, repr=False)
    _robust: tuple[np.ndarray, np.ndarray] | None = field(default=None, repr=False)

    # -- geometry helpers ---------------------------------------------------
    def finite_mask(self) -> np.ndarray:
        """Boolean mask of vertices free of NaN/Inf components."""
        if self._finite is None:
            if len(self.verts):
                self._finite = np.isfinite(self.verts).all(axis=1)
            else:
                self._finite = np.zeros(0, dtype=bool)
        return self._finite

    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        """Raw axis-aligned bounds over finite vertices (may include stray points)."""
        if len(self.verts) == 0:
            z = np.zeros(3, dtype=np.float32)
            return z, z
        v = self.verts[self.finite_mask()]
        if len(v) == 0:
            z = np.zeros(3, dtype=np.float32)
            return z, z
        return v.min(axis=0), v.max(axis=0)

    def robust_bounds(self) -> tuple[np.ndarray, np.ndarray]:
        """Bounds used for framing: stray far-out vertices are clipped away.

        Some exported environment meshes carry a handful of corrupt vertices
        (values around 1e30 or non-finite), which would otherwise blow up the
        camera framing and the reported dimensions.
        """
        if self._robust is not None:
            return self._robust
        v = self.verts[self.finite_mask()]
        if len(v) == 0:
            z = np.zeros(3, dtype=np.float32)
            self._robust = (z, z)
            return self._robust
        wide = v.astype(np.float64)          # avoid float32 overflow on junk values
        lo, hi = wide.min(axis=0), wide.max(axis=0)
        if len(wide) >= 64:
            clipped = None
            for pct in (2.0, 5.0, 10.0):
                plo = np.percentile(wide, pct, axis=0)
                phi = np.percentile(wide, 100.0 - pct, axis=0)
                if not (np.isfinite(plo).all() and np.isfinite(phi).all()):
                    continue
                clipped = (plo, phi)
                if float(np.max(phi - plo)) <= 1e6:
                    break
            if clipped is not None:
                plo, phi = clipped
                if np.any((hi - lo) > (phi - plo) * 8.0 + 1e-6):
                    lo, hi = plo, phi
        self._robust = (lo.astype(np.float32), hi.astype(np.float32))
        return self._robust

    def nonfinite_count(self) -> int:
        return int(len(self.verts) - int(self.finite_mask().sum()))

    def outlier_count(self) -> int:
        """Finite vertices that sit outside the robust bounding box."""
        mask = self.finite_mask()
        v = self.verts[mask]
        if len(v) == 0:
            return 0
        lo, hi = self.robust_bounds()
        inside = ((v >= lo) & (v <= hi)).all(axis=1)
        return int(len(v) - int(inside.sum()))

    @property
    def center(self) -> np.ndarray:
        if self._center is None:
            lo, hi = self.robust_bounds()
            self._center = (lo + hi) * 0.5
        return self._center

    @property
    def size(self) -> np.ndarray:
        if self._size is None:
            lo, hi = self.robust_bounds()
            self._size = hi - lo
        return self._size

    @property
    def radius(self) -> float:
        size = self.size
        span = float(max(size)) if len(size) else 0.0
        if not math.isfinite(span) or span <= 0.0:
            return 1.0
        return span * 0.5 + 1e-6

    def face_normals(self) -> np.ndarray:
        if self._face_normals is None:
            a = self.verts[self.faces[:, 0]]
            b = self.verts[self.faces[:, 1]]
            c = self.verts[self.faces[:, 2]]
            with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
                n = np.cross(b - a, c - a)
                lens = np.linalg.norm(n, axis=1, keepdims=True)
                n = n / np.where(lens > 1e-12, lens, 1.0)
            # corrupt vertices can overflow to NaN/Inf - keep the shading sane
            self._face_normals = np.nan_to_num(n, nan=0.0, posinf=0.0, neginf=0.0
                                               ).astype(np.float32)
        return self._face_normals

    def stats(self) -> dict:
        lo, hi = self.robust_bounds()
        return {
            "vertices": int(len(self.verts)),
            "triangles": int(len(self.faces)),
            "parts": int(self.parts),
            "dims": self.size,
            "center": self.center,
            "radius": self.radius,
            "bounds": (lo, hi),
            "nonfinite": self.nonfinite_count(),
            "outliers": self.outlier_count(),
        }


def _parse_vec3(parts: list[str]) -> tuple[float, float, float]:
    return (float(parts[0]), float(parts[1]), float(parts[2]))


def load_mtl(path: Path | None) -> dict[str, tuple[float, float, float]]:
    """Map material name -> diffuse colour."""
    materials: dict[str, tuple[float, float, float]] = {}
    if not path or not path.exists():
        return materials
    current = None
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            bits = line.split()
            if not bits:
                continue
            if bits[0] == "newmtl" and len(bits) > 1:
                current = bits[1]
                materials[current] = (0.78, 0.78, 0.80)
            elif bits[0] == "Kd" and current and len(bits) >= 4:
                materials[current] = (float(bits[1]), float(bits[2]), float(bits[3]))
            elif bits[0] == "map_Kd" and current and len(bits) >= 2:
                tex_file = path.parent / bits[1]
                if tex_file.exists():
                    try:
                        from PIL import Image
                        with Image.open(tex_file) as im:
                            im_small = im.resize((1, 1)).convert("RGB")
                            r, g, b = im_small.getpixel((0, 0))
                            materials[current] = (r / 255.0, g / 255.0, b / 255.0)
                    except Exception:
                        pass
    except Exception:
        pass
    return materials


def load_obj(path: Path | str, mtl_path: Path | None = None) -> Mesh:
    """Parse a Wavefront OBJ (triangulating polygons, ignoring texture coords)."""
    path = Path(path)
    verts: list[tuple[float, float, float]] = []
    normals: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    current_mat = "default_mat"
    used_mat = None
    index_map: dict[tuple, int] = {}
    parts = 0

    def resolve(token: str, v_count: int) -> int:
        """Resolve OBJ index (1-based, negative allowed) to 0-based."""
        return int(token) - 1 if int(token) > 0 else v_count + int(token)

    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line or line[0] == "#":
                continue
            bits = line.split()
            if not bits:
                continue
            tag = bits[0]
            if tag == "v" and len(bits) >= 4:
                verts.append(_parse_vec3(bits[1:4]))
            elif tag == "vn" and len(bits) >= 4:
                normals.append(_parse_vec3(bits[1:4]))
            elif tag == "usemtl" and len(bits) >= 2:
                current_mat = bits[1]
                if used_mat is None:
                    used_mat = current_mat
            elif tag == "f" and len(bits) >= 4:
                v_count = len(verts)
                idx = []
                for token in bits[1:]:
                    vpart = token.split("/")[0]
                    if vpart:
                        idx.append(resolve(vpart, v_count))
                for i in range(1, len(idx) - 1):
                    a, b, c = idx[0], idx[i], idx[i + 1]
                    if a == b or b == c or a == c:
                        continue
                    faces.append((a, b, c))
            elif tag in ("o", "g"):
                index_map.clear()
                parts += 1

    v = np.asarray(verts, dtype=np.float32) if verts else np.zeros((0, 3), np.float32)
    f = np.asarray(faces, dtype=np.int32) if faces else np.zeros((0, 3), np.int32)
    if len(v) == 0:
        raise ValueError(f"no vertices in {path}")

    # drop degenerate faces referencing out-of-range indices
    if len(f):
        mask = (f >= 0).all(axis=1) & (f < len(v)).all(axis=1)
        f = f[mask]

    n = np.asarray(normals, dtype=np.float32) if normals else None
    materials = load_mtl(mtl_path if mtl_path else path.with_suffix(".mtl"))
    color = materials.get(used_mat or current_mat, (0.78, 0.78, 0.80))

    return Mesh(name=path.stem, verts=v, faces=f, normals=n, color=color,
                material=used_mat or current_mat, parts=max(1, parts))
